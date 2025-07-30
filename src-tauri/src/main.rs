#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    collections::HashMap,
    path::PathBuf,
    sync::{Arc, Mutex},
};

use anyhow::Result;
use chrono::{DateTime, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Emitter, Manager};
use uuid::Uuid;

// ---------- Data Models ------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: String,
    pub title: String,
    pub content: String,
    pub file_path: Option<String>,
    pub file_type: String,
    pub content_hash: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentChunk {
    pub id: String,
    pub document_id: String,
    pub chunk_index: i32,
    pub content: String,
    pub embedding: Vec<f32>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub id: String,
    pub content: String,
    pub role: String, // "user" or "assistant"
    pub document_references: Vec<String>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SearchResult {
    pub document: Document,
    pub relevant_chunks: Vec<String>,
    pub similarity_score: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatResponse {
    pub message: ChatMessage,
    pub sources: Vec<SearchResult>,
}

// ---------- Helper Functions -------------------------------------------------------

fn app_data_dir(app: &AppHandle) -> Result<PathBuf> {
    let data_dir = app.path().app_data_dir()?;
    std::fs::create_dir_all(&data_dir)?;
    Ok(data_dir)
}

fn calculate_content_hash(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    hex::encode(hasher.finalize())
}

fn chunk_text(text: &str, chunk_size: usize, overlap: usize) -> Vec<String> {
    let words: Vec<&str> = text.split_whitespace().collect();
    if words.len() <= chunk_size {
        return vec![text.to_string()];
    }

    let mut chunks = Vec::new();
    let mut start = 0;

    while start < words.len() {
        let end = std::cmp::min(start + chunk_size, words.len());
        let chunk = words[start..end].join(" ");
        chunks.push(chunk);

        if end == words.len() {
            break;
        }

        start = end - overlap;
    }

    chunks
}

async fn extract_text_from_file(file_path: &str) -> Result<String> {
    let path = std::path::Path::new(file_path);
    let extension = path.extension()
        .and_then(|s| s.to_str())
        .unwrap_or("")
        .to_lowercase();

    match extension.as_str() {
        "txt" | "md" => {
            Ok(tokio::fs::read_to_string(file_path).await?)
        }
        "pdf" => {
            // Simple PDF text extraction
            match pdf_extract::extract_text(file_path) {
                Ok(text) => Ok(text),
                Err(_) => Ok("Could not extract text from PDF".to_string()),
            }
        }
        _ => Ok(format!("Unsupported file type: {}", extension)),
    }
}

// Mock embedding function - in production, use proper embedding models
fn generate_embedding(_text: &str) -> Vec<f32> {
    // This is a mock - in real implementation, you'd use:
    // - OpenAI embeddings API
    // - Local embedding models (sentence-transformers, etc.)
    // - Candle-based models
    (0..384).map(|i| (i as f32 * 0.001).sin()).collect()
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm_a == 0.0 || norm_b == 0.0 {
        0.0
    } else {
        dot_product / (norm_a * norm_b)
    }
}

// ---------- Database Functions -------------------------------------------------

fn init_db(conn: &Connection) -> Result<()> {
    // Documents table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            file_path TEXT,
            file_type TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )",
        [],
    )?;

    // Document chunks table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        )",
        [],
    )?;

    // Chat messages table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            role TEXT NOT NULL,
            document_references TEXT,
            created_at TEXT NOT NULL
        )",
        [],
    )?;

    // Create indexes for better performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id)", [])?;
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON chat_messages(created_at)", [])?;

    Ok(())
}

// ---------- Tauri Commands -----------------------------------------------------

#[tauri::command]
async fn upload_document(
    file_path: String,
    title: Option<String>,
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
    app: AppHandle,
) -> Result<Document, String> {
    let content = extract_text_from_file(&file_path)
        .await
        .map_err(|e| e.to_string())?;
    
    let file_name = std::path::Path::new(&file_path)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("Unknown")
        .to_string();
    
    let doc_title = title.unwrap_or(file_name);
    let content_hash = calculate_content_hash(&content);
    let now = Utc::now();

    // Extract file type before moving file_path
    let file_type = std::path::Path::new(&file_path)
        .extension()
        .and_then(|s| s.to_str())
        .unwrap_or("unknown")
        .to_string();

    let document = Document {
        id: Uuid::new_v4().to_string(),
        title: doc_title,
        content: content.clone(),
        file_path: Some(file_path),
        file_type,
        content_hash,
        created_at: now,
        updated_at: now,
    };

    // Save to database
    {
        let db = db_state.lock().map_err(|e| e.to_string())?;
        db.execute(
            "INSERT INTO documents (id, title, content, file_path, file_type, content_hash, created_at, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                document.id,
                document.title,
                document.content,
                document.file_path,
                document.file_type,
                document.content_hash,
                document.created_at.to_rfc3339(),
                document.updated_at.to_rfc3339(),
            ],
        ).map_err(|e| e.to_string())?;
    }

    // Process chunks in background
    let doc_id = document.id.clone();
    let db_clone = db_state.inner().clone();
    let app_clone = app.clone();
    
    tokio::spawn(async move {
        if let Err(e) = process_document_chunks(&doc_id, &content, &db_clone).await {
            eprintln!("Error processing chunks: {}", e);
        }
        let _ = app_clone.emit("document_processed", &doc_id);
    });

    Ok(document)
}

async fn process_document_chunks(
    document_id: &str,
    content: &str,
    db_state: &Arc<Mutex<Connection>>,
) -> Result<()> {
    let chunks = chunk_text(content, 200, 50); // 200 words per chunk, 50 word overlap
    
    for (index, chunk_content) in chunks.iter().enumerate() {
        let embedding = generate_embedding(chunk_content);
        let embedding_bytes: Vec<u8> = embedding.iter()
            .flat_map(|f| f.to_le_bytes().to_vec())
            .collect();

        let chunk = DocumentChunk {
            id: Uuid::new_v4().to_string(),
            document_id: document_id.to_string(),
            chunk_index: index as i32,
            content: chunk_content.clone(),
            embedding,
            created_at: Utc::now(),
        };

        let db = db_state.lock().map_err(|e| anyhow::anyhow!(e.to_string()))?;
        db.execute(
            "INSERT INTO document_chunks (id, document_id, chunk_index, content, embedding, created_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                chunk.id,
                chunk.document_id,
                chunk.chunk_index,
                chunk.content,
                embedding_bytes,
                chunk.created_at.to_rfc3339(),
            ],
        )?;
    }

    Ok(())
}

#[tauri::command]
fn get_documents(
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<Vec<Document>, String> {
    let db = db_state.lock().map_err(|e| e.to_string())?;
    let mut stmt = db
        .prepare("SELECT id, title, content, file_path, file_type, content_hash, created_at, updated_at FROM documents ORDER BY created_at DESC")
        .map_err(|e| e.to_string())?;

    let document_iter = stmt
        .query_map([], |row| {
            Ok(Document {
                id: row.get(0)?,
                title: row.get(1)?,
                content: row.get(2)?,
                file_path: row.get(3)?,
                file_type: row.get(4)?,
                content_hash: row.get(5)?,
                created_at: DateTime::parse_from_rfc3339(&row.get::<_, String>(6)?)
                    .unwrap()
                    .with_timezone(&Utc),
                updated_at: DateTime::parse_from_rfc3339(&row.get::<_, String>(7)?)
                    .unwrap()
                    .with_timezone(&Utc),
            })
        })
        .map_err(|e| e.to_string())?;

    let documents: Vec<Document> = document_iter
        .filter_map(Result::ok)
        .collect();

    Ok(documents)
}

#[tauri::command]
async fn search_documents(
    query: String,
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<Vec<SearchResult>, String> {
    let query_embedding = generate_embedding(&query);
    let mut results = Vec::new();

    let db = db_state.lock().map_err(|e| e.to_string())?;
    
    // Get all chunks with their embeddings
    let mut stmt = db
        .prepare("SELECT dc.document_id, dc.content, dc.embedding, d.id, d.title, d.content, d.file_path, d.file_type, d.content_hash, d.created_at, d.updated_at
                  FROM document_chunks dc
                  JOIN documents d ON dc.document_id = d.id")
        .map_err(|e| e.to_string())?;

    let chunk_iter = stmt
        .query_map([], |row| {
            let embedding_bytes: Vec<u8> = row.get(2)?;
            let embedding: Vec<f32> = embedding_bytes
                .chunks_exact(4)
                .map(|chunk| f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]))
                .collect();

            Ok((
                row.get::<_, String>(1)?, // chunk content
                embedding,
                Document {
                    id: row.get(3)?,
                    title: row.get(4)?,
                    content: row.get(5)?,
                    file_path: row.get(6)?,
                    file_type: row.get(7)?,
                    content_hash: row.get(8)?,
                    created_at: DateTime::parse_from_rfc3339(&row.get::<_, String>(9)?)
                        .unwrap()
                        .with_timezone(&Utc),
                    updated_at: DateTime::parse_from_rfc3339(&row.get::<_, String>(10)?)
                        .unwrap()
                        .with_timezone(&Utc),
                },
            ))
        })
        .map_err(|e| e.to_string())?;

    let mut doc_results: HashMap<String, (Document, Vec<String>, f32)> = HashMap::new();

    for chunk_result in chunk_iter {
        if let Ok((chunk_content, chunk_embedding, document)) = chunk_result {
            let similarity = cosine_similarity(&query_embedding, &chunk_embedding);
            
            if similarity > 0.3 { // Threshold for relevance
                doc_results
                    .entry(document.id.clone())
                    .and_modify(|(_, chunks, max_sim)| {
                        chunks.push(chunk_content.clone());
                        *max_sim = max_sim.max(similarity);
                    })
                    .or_insert((document, vec![chunk_content], similarity));
            }
        }
    }

    // Convert to SearchResult vector and sort by similarity
    for (_, (document, chunks, similarity)) in doc_results {
        results.push(SearchResult {
            document,
            relevant_chunks: chunks,
            similarity_score: similarity,
        });
    }

    results.sort_by(|a, b| b.similarity_score.partial_cmp(&a.similarity_score).unwrap());
    results.truncate(10); // Return top 10 results

    Ok(results)
}

#[tauri::command]
async fn chat_with_documents(
    message: String,
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<ChatResponse, String> {
    // First, search for relevant documents
    let search_results = search_documents(message.clone(), db_state.clone()).await?;
    
    // Save user message
    let user_msg = ChatMessage {
        id: Uuid::new_v4().to_string(),
        content: message.clone(),
        role: "user".to_string(),
        document_references: search_results.iter().map(|r| r.document.id.clone()).collect(),
        created_at: Utc::now(),
    };

    // Generate AI response (mock implementation)
    let context = search_results
        .iter()
        .flat_map(|r| r.relevant_chunks.iter())
        .cloned()
        .collect::<Vec<_>>()
        .join("\n\n");

    let ai_response = if context.is_empty() {
        "I don't have any relevant documents to answer your question. Please upload some documents first.".to_string()
    } else {
        format!(
            "Based on the uploaded documents, here's what I found:\n\n{}\n\nThis information comes from {} document(s) in your knowledge base.",
            context,
            search_results.len()
        )
    };

    let assistant_msg = ChatMessage {
        id: Uuid::new_v4().to_string(),
        content: ai_response,
        role: "assistant".to_string(),
        document_references: search_results.iter().map(|r| r.document.id.clone()).collect(),
        created_at: Utc::now(),
    };

    // Save both messages to database
    {
        let db = db_state.lock().map_err(|e| e.to_string())?;
        
        for msg in [&user_msg, &assistant_msg] {
            db.execute(
                "INSERT INTO chat_messages (id, content, role, document_references, created_at)
                 VALUES (?1, ?2, ?3, ?4, ?5)",
                params![
                    msg.id,
                    msg.content,
                    msg.role,
                    serde_json::to_string(&msg.document_references).unwrap_or_default(),
                    msg.created_at.to_rfc3339(),
                ],
            ).map_err(|e| e.to_string())?;
        }
    }

    Ok(ChatResponse {
        message: assistant_msg,
        sources: search_results,
    })
}

#[tauri::command]
fn get_chat_history(
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<Vec<ChatMessage>, String> {
    let db = db_state.lock().map_err(|e| e.to_string())?;
    let mut stmt = db
        .prepare("SELECT id, content, role, document_references, created_at FROM chat_messages ORDER BY created_at ASC")
        .map_err(|e| e.to_string())?;

    let message_iter = stmt
        .query_map([], |row| {
            let doc_refs_str: String = row.get(3)?;
            let document_references: Vec<String> = serde_json::from_str(&doc_refs_str)
                .unwrap_or_default();

            Ok(ChatMessage {
                id: row.get(0)?,
                content: row.get(1)?,
                role: row.get(2)?,
                document_references,
                created_at: DateTime::parse_from_rfc3339(&row.get::<_, String>(4)?)
                    .unwrap()
                    .with_timezone(&Utc),
            })
        })
        .map_err(|e| e.to_string())?;

    let messages: Vec<ChatMessage> = message_iter
        .filter_map(Result::ok)
        .collect();

    Ok(messages)
}

#[tauri::command]
fn delete_document(
    document_id: String,
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<(), String> {
    let db = db_state.lock().map_err(|e| e.to_string())?;
    
    // Delete document (chunks will be deleted automatically due to CASCADE)
    db.execute("DELETE FROM documents WHERE id = ?", params![document_id])
        .map_err(|e| e.to_string())?;

    Ok(())
}

// ---------- Main Application ---------------------------------------------------

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .setup(|app| {
            // Initialize database
            let data_dir = app_data_dir(&app.app_handle())?;
            let db_path = data_dir.join("rag_documents.db");
            let conn = Connection::open(db_path)?;
            
            init_db(&conn).expect("Failed to initialize database");
            
            let db = Arc::new(Mutex::new(conn));
            app.manage(db);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            upload_document,
            get_documents,
            search_documents,
            chat_with_documents,
            get_chat_history,
            delete_document,
        ])
        .run(tauri::generate_context!())
        .expect("Error running RAG application");
}
