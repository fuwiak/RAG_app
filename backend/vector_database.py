#!/usr/bin/env python3
"""
Advanced Vector Database Management
Supports both ChromaDB and FAISS with seamless switching and performance optimization
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass

# Vector database libraries
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

@dataclass
class VectorSearchResult:
    """Result from vector search"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    document_title: str = ""
    chunk_index: int = 0

@dataclass
class VectorDBConfig:
    """Configuration for vector database"""
    db_type: str = "chroma"  # "chroma" or "faiss"
    db_path: str = "./vector_db"
    collection_name: str = "rag_documents"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    index_type: str = "IndexFlatIP"  # For FAISS
    metric: str = "cosine"
    max_elements: int = 1000000

class VectorDatabase(ABC):
    """Abstract base class for vector databases"""
    
    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to the database"""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[VectorSearchResult]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID"""
        pass
    
    @abstractmethod
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        pass
    
    @abstractmethod
    def clear_collection(self) -> bool:
        """Clear all documents from collection"""
        pass

class ChromaVectorDB(VectorDatabase):
    """ChromaDB implementation"""
    
    def __init__(self, config: VectorDBConfig):
        if not CHROMA_AVAILABLE:
            raise ImportError("ChromaDB not available. Install with: pip install chromadb")
        
        self.config = config
        self.embedding_model = self._load_embedding_model()
        self.client = None
        self.collection = None
        self._initialize_db()
        
    def _load_embedding_model(self):
        """Load embedding model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("SentenceTransformers not available")
        return SentenceTransformer(self.config.embedding_model)
    
    def _initialize_db(self):
        """Initialize ChromaDB"""
        db_path = Path(self.config.db_path) / "chroma"
        db_path.mkdir(parents=True, exist_ok=True)
        
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(db_path),
            anonymized_telemetry=False
        )
        
        self.client = chromadb.Client(settings)
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(self.config.collection_name)
        except:
            self.collection = self.client.create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": self.config.metric}
            )
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to ChromaDB"""
        try:
            texts = [doc["content"] for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]
            ids = [doc["id"] for doc in documents]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            return True
        except Exception as e:
            logging.error(f"Error adding documents to ChromaDB: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[VectorSearchResult]:
        """Search in ChromaDB"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_dict
            )
            
            # Convert to VectorSearchResult
            search_results = []
            for i in range(len(results['ids'][0])):
                result = VectorSearchResult(
                    id=results['ids'][0][i],
                    content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i] or {},
                    score=1.0 - results['distances'][0][i],  # Convert distance to similarity
                    document_title=results['metadatas'][0][i].get('title', '') if results['metadatas'][0][i] else '',
                    chunk_index=results['metadatas'][0][i].get('chunk_index', 0) if results['metadatas'][0][i] else 0
                )
                search_results.append(result)
            
            return search_results
        except Exception as e:
            logging.error(f"Error searching ChromaDB: {e}")
            return []
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document from ChromaDB"""
        try:
            self.collection.delete(ids=[document_id])
            return True
        except Exception as e:
            logging.error(f"Error deleting document from ChromaDB: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get ChromaDB collection statistics"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "db_type": "chroma",
                "collection_name": self.config.collection_name,
                "embedding_model": self.config.embedding_model
            }
        except Exception as e:
            logging.error(f"Error getting ChromaDB stats: {e}")
            return {}
    
    def clear_collection(self) -> bool:
        """Clear ChromaDB collection"""
        try:
            self.client.delete_collection(self.config.collection_name)
            self.collection = self.client.create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": self.config.metric}
            )
            return True
        except Exception as e:
            logging.error(f"Error clearing ChromaDB collection: {e}")
            return False

class FAISSVectorDB(VectorDatabase):
    """FAISS implementation"""
    
    def __init__(self, config: VectorDBConfig):
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")
        
        self.config = config
        self.embedding_model = self._load_embedding_model()
        self.index = None
        self.document_store = {}  # Store document metadata
        self.id_to_index = {}  # Map document IDs to FAISS indices
        self.index_to_id = {}  # Map FAISS indices to document IDs
        self._initialize_db()
    
    def _load_embedding_model(self):
        """Load embedding model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("SentenceTransformers not available")
        return SentenceTransformer(self.config.embedding_model)
    
    def _initialize_db(self):
        """Initialize FAISS index"""
        db_path = Path(self.config.db_path) / "faiss"
        db_path.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.index_path = db_path / "vector.index"
        self.metadata_path = db_path / "metadata.json"
        
        # Load existing index if available
        if self.index_path.exists():
            self._load_index()
        else:
            self._create_index()
    
    def _create_index(self):
        """Create new FAISS index"""
        if self.config.index_type == "IndexFlatIP":
            self.index = faiss.IndexFlatIP(self.config.dimension)
        elif self.config.index_type == "IndexFlatL2":
            self.index = faiss.IndexFlatL2(self.config.dimension)
        elif self.config.index_type == "IndexHNSWFlat":
            self.index = faiss.IndexHNSWFlat(self.config.dimension, 32)
        else:
            self.index = faiss.IndexFlatIP(self.config.dimension)
    
    def _load_index(self):
        """Load existing FAISS index"""
        try:
            self.index = faiss.read_index(str(self.index_path))
            
            # Load metadata
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r') as f:
                    data = json.load(f)
                    self.document_store = data.get('documents', {})
                    self.id_to_index = data.get('id_to_index', {})
                    self.index_to_id = data.get('index_to_id', {})
        except Exception as e:
            logging.error(f"Error loading FAISS index: {e}")
            self._create_index()
    
    def _save_index(self):
        """Save FAISS index and metadata"""
        try:
            faiss.write_index(self.index, str(self.index_path))
            
            metadata = {
                'documents': self.document_store,
                'id_to_index': self.id_to_index,
                'index_to_id': self.index_to_id
            }
            
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving FAISS index: {e}")
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to FAISS"""
        try:
            texts = [doc["content"] for doc in documents]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(texts)
            
            # Normalize embeddings for cosine similarity
            if self.config.index_type == "IndexFlatIP":
                faiss.normalize_L2(embeddings)
            
            # Get starting index
            start_index = self.index.ntotal
            
            # Add to index
            self.index.add(embeddings.astype('float32'))
            
            # Store metadata
            for i, doc in enumerate(documents):
                doc_id = doc["id"]
                faiss_index = start_index + i
                
                self.document_store[doc_id] = {
                    'content': doc["content"],
                    'metadata': doc.get("metadata", {}),
                    'faiss_index': faiss_index
                }
                
                self.id_to_index[doc_id] = faiss_index
                self.index_to_id[str(faiss_index)] = doc_id
            
            self._save_index()
            return True
        except Exception as e:
            logging.error(f"Error adding documents to FAISS: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[VectorSearchResult]:
        """Search in FAISS"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Normalize for cosine similarity
            if self.config.index_type == "IndexFlatIP":
                faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.index.search(query_embedding.astype('float32'), top_k)
            
            # Convert to VectorSearchResult
            search_results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # No more results
                    break
                
                doc_id = self.index_to_id.get(str(idx))
                if doc_id and doc_id in self.document_store:
                    doc_data = self.document_store[doc_id]
                    
                    # Apply filter if specified
                    if filter_dict:
                        metadata = doc_data.get('metadata', {})
                        if not all(metadata.get(k) == v for k, v in filter_dict.items()):
                            continue
                    
                    result = VectorSearchResult(
                        id=doc_id,
                        content=doc_data['content'],
                        metadata=doc_data.get('metadata', {}),
                        score=float(score),
                        document_title=doc_data.get('metadata', {}).get('title', ''),
                        chunk_index=doc_data.get('metadata', {}).get('chunk_index', 0)
                    )
                    search_results.append(result)
            
            return search_results
        except Exception as e:
            logging.error(f"Error searching FAISS: {e}")
            return []
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document from FAISS (rebuild index)"""
        try:
            if document_id not in self.document_store:
                return False
            
            # Remove from stores
            faiss_index = self.document_store[document_id]['faiss_index']
            del self.document_store[document_id]
            del self.id_to_index[document_id]
            del self.index_to_id[str(faiss_index)]
            
            # Rebuild index (FAISS doesn't support efficient deletion)
            self._rebuild_index()
            return True
        except Exception as e:
            logging.error(f"Error deleting document from FAISS: {e}")
            return False
    
    def _rebuild_index(self):
        """Rebuild FAISS index after deletion"""
        if not self.document_store:
            self._create_index()
            self._save_index()
            return
        
        # Create new index
        self._create_index()
        
        # Re-add all documents
        documents = []
        for doc_id, doc_data in self.document_store.items():
            documents.append({
                'id': doc_id,
                'content': doc_data['content'],
                'metadata': doc_data['metadata']
            })
        
        # Clear mappings
        self.id_to_index = {}
        self.index_to_id = {}
        
        # Re-add documents
        if documents:
            self.add_documents(documents)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get FAISS collection statistics"""
        return {
            "total_documents": len(self.document_store),
            "db_type": "faiss",
            "index_type": self.config.index_type,
            "dimension": self.config.dimension,
            "embedding_model": self.config.embedding_model
        }
    
    def clear_collection(self) -> bool:
        """Clear FAISS collection"""
        try:
            self._create_index()
            self.document_store = {}
            self.id_to_index = {}
            self.index_to_id = {}
            self._save_index()
            return True
        except Exception as e:
            logging.error(f"Error clearing FAISS collection: {e}")
            return False

class VectorDatabaseManager:
    """Manager for vector databases with automatic switching"""
    
    def __init__(self, config: VectorDBConfig):
        self.config = config
        self.db = self._create_database()
    
    def _create_database(self) -> VectorDatabase:
        """Create appropriate database instance"""
        if self.config.db_type.lower() == "chroma":
            if not CHROMA_AVAILABLE:
                logging.warning("ChromaDB not available, falling back to FAISS")
                self.config.db_type = "faiss"
                return FAISSVectorDB(self.config)
            return ChromaVectorDB(self.config)
        elif self.config.db_type.lower() == "faiss":
            if not FAISS_AVAILABLE:
                logging.warning("FAISS not available, falling back to ChromaDB")
                self.config.db_type = "chroma"
                return ChromaVectorDB(self.config)
            return FAISSVectorDB(self.config)
        else:
            raise ValueError(f"Unsupported database type: {self.config.db_type}")
    
    def switch_database(self, new_db_type: str) -> bool:
        """Switch to different database type"""
        try:
            # Export current data
            current_stats = self.db.get_collection_stats()
            
            # Create new database
            old_config = self.config
            self.config.db_type = new_db_type
            new_db = self._create_database()
            
            # Migration would go here if needed
            # For now, just switch
            self.db = new_db
            
            logging.info(f"Switched from {old_config.db_type} to {new_db_type}")
            return True
        except Exception as e:
            logging.error(f"Error switching database: {e}")
            return False
    
    def benchmark_databases(self, test_documents: List[Dict], test_queries: List[str]) -> Dict[str, Any]:
        """Benchmark different database implementations"""
        results = {}
        
        for db_type in ["chroma", "faiss"]:
            if (db_type == "chroma" and not CHROMA_AVAILABLE) or \
               (db_type == "faiss" and not FAISS_AVAILABLE):
                continue
            
            try:
                # Create test database
                test_config = VectorDBConfig(
                    db_type=db_type,
                    db_path=f"./test_db_{db_type}",
                    collection_name=f"test_{db_type}"
                )
                
                if db_type == "chroma":
                    test_db = ChromaVectorDB(test_config)
                else:
                    test_db = FAISSVectorDB(test_config)
                
                # Benchmark insertion
                start_time = time.time()
                test_db.add_documents(test_documents)
                insert_time = time.time() - start_time
                
                # Benchmark search
                search_times = []
                for query in test_queries:
                    start_time = time.time()
                    test_db.search(query, top_k=5)
                    search_times.append(time.time() - start_time)
                
                avg_search_time = sum(search_times) / len(search_times)
                
                results[db_type] = {
                    "insert_time": insert_time,
                    "avg_search_time": avg_search_time,
                    "total_documents": len(test_documents)
                }
                
                # Cleanup
                test_db.clear_collection()
                
            except Exception as e:
                results[db_type] = {"error": str(e)}
        
        return results
    
    # Delegate methods to current database
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        return self.db.add_documents(documents)
    
    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[VectorSearchResult]:
        return self.db.search(query, top_k, filter_dict)
    
    def delete_document(self, document_id: str) -> bool:
        return self.db.delete_document(document_id)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        return self.db.get_collection_stats()
    
    def clear_collection(self) -> bool:
        return self.db.clear_collection()

def main():
    """Example usage and testing"""
    # Example configuration
    config = VectorDBConfig(
        db_type="chroma",  # or "faiss"
        db_path="./vector_db",
        collection_name="rag_documents",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # Create manager
    manager = VectorDatabaseManager(config)
    
    # Example documents
    test_docs = [
        {
            "id": "doc1",
            "content": "Machine learning is a subset of artificial intelligence.",
            "metadata": {"title": "ML Basics", "chunk_index": 0}
        },
        {
            "id": "doc2", 
            "content": "Deep learning uses neural networks with multiple layers.",
            "metadata": {"title": "Deep Learning", "chunk_index": 0}
        }
    ]
    
    # Add documents
    manager.add_documents(test_docs)
    
    # Search
    results = manager.search("What is machine learning?", top_k=2)
    for result in results:
        print(f"Score: {result.score:.3f} - {result.content[:100]}...")
    
    # Get stats
    stats = manager.get_collection_stats()
    print(f"Database stats: {stats}")

if __name__ == "__main__":
    main() 