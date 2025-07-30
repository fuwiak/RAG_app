#!/usr/bin/env python3
"""
Model Export and Deployment Module
Supports exporting to HuggingFace format, generating FastAPI endpoints, and Docker containerization
"""

import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import subprocess
import tempfile

# Import libraries with fallbacks
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from huggingface_hub import HfApi, create_repo
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False

@dataclass
class ExportConfig:
    """Configuration for model export"""
    model_path: str
    output_dir: str
    model_name: str
    export_format: str = "huggingface"  # "huggingface", "onnx", "torchscript"
    include_tokenizer: bool = True
    include_config: bool = True
    push_to_hub: bool = False
    hub_token: Optional[str] = None
    hub_repo_name: Optional[str] = None
    private_repo: bool = False
    model_description: str = ""
    model_tags: List[str] = None

@dataclass
class APIConfig:
    """Configuration for API endpoint generation"""
    model_path: str
    api_name: str = "rag_model_api"
    port: int = 8000
    host: str = "0.0.0.0"
    enable_cors: bool = True
    max_workers: int = 4
    enable_docs: bool = True
    auth_token: Optional[str] = None
    rate_limit: int = 100  # requests per minute
    max_tokens: int = 512
    temperature: float = 0.7

@dataclass
class DockerConfig:
    """Configuration for Docker containerization"""
    image_name: str = "rag-model-api"
    tag: str = "latest"
    base_image: str = "python:3.11-slim"
    port: int = 8000
    include_cuda: bool = False
    model_path: str = "./model"
    requirements_file: str = "./requirements.txt"

class ModelExporter:
    """Handles model export to various formats"""
    
    def __init__(self, config: ExportConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def export_to_huggingface(self) -> bool:
        """Export model to HuggingFace format"""
        try:
            if not TRANSFORMERS_AVAILABLE:
                self.logger.error("Transformers library not available")
                return False
                
            model_path = Path(self.config.model_path)
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Exporting model from {model_path} to {output_dir}")
            
            # Load model and tokenizer
            if model_path.is_dir():
                # Load from directory
                model = AutoModelForCausalLM.from_pretrained(model_path)
                tokenizer = AutoTokenizer.from_pretrained(model_path)
            else:
                # Load checkpoint
                self.logger.info("Loading checkpoint format model")
                model = torch.load(model_path, map_location='cpu')
                # Try to find tokenizer in parent directory
                tokenizer_path = model_path.parent / "tokenizer"
                if tokenizer_path.exists():
                    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
                else:
                    self.logger.warning("Tokenizer not found, using default")
                    tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
            
            # Save model in HuggingFace format
            model.save_pretrained(output_dir)
            if self.config.include_tokenizer:
                tokenizer.save_pretrained(output_dir)
            
            # Create model card
            self._create_model_card(output_dir)
            
            # Create README
            self._create_readme(output_dir)
            
            # Push to hub if requested
            if self.config.push_to_hub and self.config.hub_token:
                self._push_to_hub(output_dir)
            
            self.logger.info("Model export completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting model: {e}")
            return False
    
    def _create_model_card(self, output_dir: Path):
        """Create model card for HuggingFace"""
        model_card = {
            "license": "apache-2.0",
            "tags": self.config.model_tags or ["text-generation", "rag", "conversational"],
            "language": ["en"],
            "library_name": "transformers",
            "pipeline_tag": "text-generation",
            "model_name": self.config.model_name,
            "model_description": self.config.model_description or f"Fine-tuned model: {self.config.model_name}",
            "training_data": "Custom RAG dataset",
            "base_model": "microsoft/DialoGPT-medium",
            "fine_tuning_method": "LoRA/QLoRA",
            "metrics": {
                "perplexity": "To be evaluated",
                "bleu_score": "To be evaluated"
            }
        }
        
        # Save as config.json update
        config_path = output_dir / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            config.update(model_card)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        
        # Save as separate model card
        card_path = output_dir / "model_card.json"
        with open(card_path, 'w') as f:
            json.dump(model_card, f, indent=2)
    
    def _create_readme(self, output_dir: Path):
        """Create README.md for the model"""
        readme_content = f"""# {self.config.model_name}

## Model Description

{self.config.model_description or f"Fine-tuned conversational model: {self.config.model_name}"}

This model was fine-tuned using advanced techniques including LoRA (Low-Rank Adaptation) for efficient training and RAG (Retrieval-Augmented Generation) for enhanced knowledge integration.

## Tags

{', '.join(self.config.model_tags or ['text-generation', 'rag', 'conversational'])}

## Usage

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("{self.config.hub_repo_name or self.config.model_name}")
model = AutoModelForCausalLM.from_pretrained("{self.config.hub_repo_name or self.config.model_name}")

# Generate text
input_text = "Hello, how are you?"
inputs = tokenizer.encode(input_text, return_tensors="pt")

with torch.no_grad():
    outputs = model.generate(
        inputs,
        max_length=100,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )

response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(response)
```

## Training Details

- **Training Method**: LoRA/QLoRA Fine-tuning
- **Base Model**: microsoft/DialoGPT-medium
- **Training Data**: Custom RAG dataset
- **Training Framework**: PyTorch + Transformers + PEFT
- **Hardware**: GPU-optimized training

## Performance

- **Perplexity**: To be evaluated
- **BLEU Score**: To be evaluated
- **Response Quality**: Enhanced with RAG integration

## License

Apache 2.0

## Citation

```bibtex
@misc{{{self.config.model_name.replace('-', '_')},
  title={{{self.config.model_name}}},
  author={{RAG Application Team}},
  year={{2024}},
  url={{https://github.com/your-repo/rag-app}}
}}
```
"""
        
        readme_path = output_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(readme_content)
    
    def _push_to_hub(self, output_dir: Path):
        """Push model to HuggingFace Hub"""
        try:
            if not HF_HUB_AVAILABLE:
                self.logger.error("HuggingFace Hub library not available")
                return False
            
            api = HfApi(token=self.config.hub_token)
            
            # Create repository
            repo_url = create_repo(
                repo_id=self.config.hub_repo_name,
                token=self.config.hub_token,
                private=self.config.private_repo,
                exist_ok=True
            )
            
            # Upload files
            api.upload_folder(
                folder_path=str(output_dir),
                repo_id=self.config.hub_repo_name,
                token=self.config.hub_token
            )
            
            self.logger.info(f"Model pushed to HuggingFace Hub: {repo_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error pushing to hub: {e}")
            return False

class APIGenerator:
    """Generates FastAPI endpoint for model serving"""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def generate_api(self, output_dir: str) -> bool:
        """Generate FastAPI application"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate main API file
            self._generate_main_py(output_path)
            
            # Generate model handler
            self._generate_model_handler(output_path)
            
            # Generate requirements
            self._generate_requirements(output_path)
            
            # Generate startup script
            self._generate_startup_script(output_path)
            
            # Generate Docker files
            self._generate_docker_files(output_path)
            
            self.logger.info(f"API generated successfully in {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating API: {e}")
            return False
    
    def _generate_main_py(self, output_path: Path):
        """Generate main FastAPI application"""
        main_content = f'''#!/usr/bin/env python3
"""
RAG Model API Server
Auto-generated FastAPI application for serving fine-tuned models
"""

import os
import time
import logging
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from model_handler import ModelHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
request_times = {{}}
RATE_LIMIT = {self.config.rate_limit}  # requests per minute
RATE_WINDOW = 60  # seconds

# Security
security = HTTPBearer() if "{self.config.auth_token}" else None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Input message")
    temperature: float = Field({self.config.temperature}, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field({self.config.max_tokens}, ge=1, le=2048, description="Maximum tokens to generate")
    top_p: float = Field(0.9, ge=0.0, le=1.0, description="Top-p sampling")
    use_rag: bool = Field(True, description="Enable RAG retrieval")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Generated response")
    model: str = Field(..., description="Model used")
    timestamp: str = Field(..., description="Response timestamp")
    processing_time: float = Field(..., description="Processing time in seconds")
    tokens_used: int = Field(..., description="Tokens used in generation")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    retrieved_sources: Optional[List[Dict]] = Field(None, description="RAG sources used")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    uptime: str = Field(..., description="Service uptime")
    version: str = Field("1.0.0", description="API version")

# Global model handler
model_handler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global model_handler
    
    # Startup
    logger.info("Starting RAG Model API...")
    model_handler = ModelHandler("{self.config.model_path}")
    await model_handler.load_model()
    logger.info("Model loaded successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG Model API...")
    if model_handler:
        await model_handler.cleanup()

# Create FastAPI app
app = FastAPI(
    title="{self.config.api_name}",
    description="Auto-generated API for RAG fine-tuned model",
    version="1.0.0",
    docs_url="/docs" if {self.config.enable_docs} else None,
    redoc_url="/redoc" if {self.config.enable_docs} else None,
    lifespan=lifespan
)

# Add CORS middleware
if {self.config.enable_cors}:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def check_rate_limit(request: Request):
    """Check rate limiting"""
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip not in request_times:
        request_times[client_ip] = []
    
    # Remove old requests
    request_times[client_ip] = [
        req_time for req_time in request_times[client_ip]
        if current_time - req_time < RATE_WINDOW
    ]
    
    # Check rate limit
    if len(request_times[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    request_times[client_ip].append(current_time)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify authentication token"""
    if "{self.config.auth_token}" and credentials.credentials != "{self.config.auth_token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with health check"""
    return HealthResponse(
        status="healthy",
        model_loaded=model_handler is not None and model_handler.is_loaded(),
        uptime=str(datetime.now()),
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if model_handler and model_handler.is_loaded() else "unhealthy",
        model_loaded=model_handler is not None and model_handler.is_loaded(),
        uptime=str(datetime.now()),
        version="1.0.0"
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token) if security else None
):
    """Chat with the model"""
    # Rate limiting
    check_rate_limit(http_request)
    
    if not model_handler or not model_handler.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded"
        )
    
    try:
        start_time = time.time()
        
        # Generate response
        result = await model_handler.generate_response(
            message=request.message,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            use_rag=request.use_rag,
            conversation_id=request.conversation_id
        )
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            response=result["response"],
            model=result["model"],
            timestamp=datetime.now().isoformat(),
            processing_time=round(processing_time, 3),
            tokens_used=result.get("tokens_used", 0),
            conversation_id=result.get("conversation_id"),
            retrieved_sources=result.get("retrieved_sources")
        )
        
    except Exception as e:
        logger.error(f"Error generating response: {{e}}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {{str(e)}}"
        )

@app.get("/models")
async def list_models():
    """List available models"""
    if not model_handler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model handler not initialized"
        )
    
    return {{
        "models": model_handler.get_model_info(),
        "current_model": model_handler.get_current_model_name()
    }}

@app.post("/reload")
async def reload_model():
    """Reload the model"""
    if not model_handler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model handler not initialized"
        )
    
    try:
        await model_handler.reload_model()
        return {{"status": "Model reloaded successfully"}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reloading model: {{str(e)}}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="{self.config.host}",
        port={self.config.port},
        workers={self.config.max_workers},
        reload=False,
        log_level="info"
    )
'''
        
        main_path = output_path / "main.py"
        with open(main_path, 'w') as f:
            f.write(main_content)
    
    def _generate_model_handler(self, output_path: Path):
        """Generate model handler class"""
        handler_content = '''#!/usr/bin/env python3
"""
Model Handler for RAG Fine-tuned Models
Handles model loading, inference, and RAG integration
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import time
import uuid

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

class ModelHandler:
    """Handles model operations and inference"""
    
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = self.model_path.name
        self.loaded = False
        self.conversations = {}  # Store conversation context
        
    async def load_model(self):
        """Load the model and tokenizer"""
        try:
            if not TRANSFORMERS_AVAILABLE:
                raise ImportError("Transformers library not available")
            
            logger.info(f"Loading model from {self.model_path}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )
            
            # Create pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1
            )
            
            self.loaded = True
            logger.info(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.loaded = False
            raise
    
    async def generate_response(
        self,
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.9,
        use_rag: bool = True,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate response to user message"""
        if not self.loaded:
            raise RuntimeError("Model not loaded")
        
        try:
            # Create conversation ID if not provided
            if conversation_id is None:
                conversation_id = str(uuid.uuid4())
            
            # Get conversation context
            context = self._get_conversation_context(conversation_id)
            
            # Build prompt with context
            prompt = self._build_prompt(message, context, use_rag)
            
            # Generate response
            start_time = time.time()
            
            outputs = self.pipeline(
                prompt,
                max_length=len(prompt.split()) + max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                return_full_text=False
            )
            
            response = outputs[0]["generated_text"].strip()
            generation_time = time.time() - start_time
            
            # Update conversation context
            self._update_conversation(conversation_id, message, response)
            
            # Estimate tokens used
            tokens_used = len(self.tokenizer.encode(prompt + response))
            
            # Mock RAG sources (in real implementation, this would query vector DB)
            retrieved_sources = []
            if use_rag:
                retrieved_sources = [
                    {
                        "title": "Sample Document",
                        "content": "Sample retrieved content...",
                        "similarity": 0.85,
                        "chunk_id": "chunk_001"
                    }
                ]
            
            return {
                "response": response,
                "model": self.model_name,
                "conversation_id": conversation_id,
                "tokens_used": tokens_used,
                "generation_time": generation_time,
                "retrieved_sources": retrieved_sources if use_rag else None
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _build_prompt(self, message: str, context: List[Dict], use_rag: bool = True) -> str:
        """Build prompt with conversation context"""
        prompt_parts = []
        
        # Add RAG context if enabled
        if use_rag:
            prompt_parts.append("Context: You are a helpful AI assistant with access to relevant knowledge.")
            prompt_parts.append("")
        
        # Add conversation history
        for turn in context[-5:]:  # Last 5 turns
            prompt_parts.append(f"Human: {turn['human']}")
            prompt_parts.append(f"Assistant: {turn['assistant']}")
        
        # Add current message
        prompt_parts.append(f"Human: {message}")
        prompt_parts.append("Assistant:")
        
        return "\\n".join(prompt_parts)
    
    def _get_conversation_context(self, conversation_id: str) -> List[Dict]:
        """Get conversation context"""
        return self.conversations.get(conversation_id, [])
    
    def _update_conversation(self, conversation_id: str, human_message: str, assistant_response: str):
        """Update conversation context"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        self.conversations[conversation_id].append({
            "human": human_message,
            "assistant": assistant_response,
            "timestamp": time.time()
        })
        
        # Keep only last 20 turns to manage memory
        if len(self.conversations[conversation_id]) > 20:
            self.conversations[conversation_id] = self.conversations[conversation_id][-20:]
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.loaded
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": self.model_name,
            "path": str(self.model_path),
            "device": self.device,
            "loaded": self.loaded,
            "conversations_active": len(self.conversations)
        }
    
    def get_current_model_name(self) -> str:
        """Get current model name"""
        return self.model_name
    
    async def reload_model(self):
        """Reload the model"""
        logger.info("Reloading model...")
        await self.cleanup()
        await self.load_model()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        if self.pipeline:
            del self.pipeline
        
        self.loaded = False
        self.conversations.clear()
        
        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Model cleanup completed")
'''
        
        handler_path = output_path / "model_handler.py"
        with open(handler_path, 'w') as f:
            f.write(handler_content)
    
    def _generate_requirements(self, output_path: Path):
        """Generate requirements.txt"""
        requirements = [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "torch>=2.0.0",
            "transformers>=4.35.0",
            "accelerate>=0.24.0",
            "pydantic>=2.0.0",
            "python-multipart>=0.0.6",
            "jinja2>=3.1.2",
            "python-jose[cryptography]>=3.3.0",
            "passlib[bcrypt]>=1.7.4",
            "aiofiles>=23.2.1",
            "httpx>=0.25.0"
        ]
        
        req_path = output_path / "requirements.txt"
        with open(req_path, 'w') as f:
            f.write('\n'.join(requirements))
    
    def _generate_startup_script(self, output_path: Path):
        """Generate startup script"""
        script_content = f'''#!/bin/bash

# RAG Model API Startup Script
# Auto-generated startup script for the model API

echo "Starting RAG Model API..."

# Set environment variables
export PYTHONPATH="${{PYTHONPATH}}:$(pwd)"
export MODEL_PATH="{self.config.model_path}"
export API_HOST="{self.config.host}"
export API_PORT="{self.config.port}"

# Create logs directory
mkdir -p logs

# Start the API server
python main.py > logs/api.log 2>&1 &

# Get the PID
API_PID=$!
echo $API_PID > api.pid

echo "API started with PID: $API_PID"
echo "API running on http://{self.config.host}:{self.config.port}"
echo "Documentation available at http://{self.config.host}:{self.config.port}/docs"
echo "Log file: logs/api.log"

# Wait a moment and check if the process is still running
sleep 5
if kill -0 $API_PID 2>/dev/null; then
    echo "API is running successfully!"
else
    echo "ERROR: API failed to start. Check logs/api.log for details."
    exit 1
fi
'''
        
        script_path = output_path / "start_api.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        # Generate stop script
        stop_script = '''#!/bin/bash

# Stop RAG Model API

if [ -f api.pid ]; then
    PID=$(cat api.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping API (PID: $PID)..."
        kill $PID
        sleep 2
        if kill -0 $PID 2>/dev/null; then
            echo "Force killing API..."
            kill -9 $PID
        fi
        rm -f api.pid
        echo "API stopped."
    else
        echo "API is not running."
        rm -f api.pid
    fi
else
    echo "No PID file found. API may not be running."
fi
'''
        
        stop_path = output_path / "stop_api.sh"
        with open(stop_path, 'w') as f:
            f.write(stop_script)
        os.chmod(stop_path, 0o755)
    
    def _generate_docker_files(self, output_path: Path):
        """Generate Docker files"""
        docker_config = DockerConfig(
            image_name=self.config.api_name,
            port=self.config.port,
            model_path="./model"
        )
        
        docker_generator = DockerGenerator(docker_config)
        docker_generator.generate_dockerfile(output_path)
        docker_generator.generate_docker_compose(output_path)

class DockerGenerator:
    """Generates Docker files for model deployment"""
    
    def __init__(self, config: DockerConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def generate_dockerfile(self, output_path: Path):
        """Generate Dockerfile"""
        base_image = "nvidia/cuda:12.1-runtime-ubuntu22.04" if self.config.include_cuda else self.config.base_image
        
        dockerfile_content = f'''# Auto-generated Dockerfile for RAG Model API

FROM {base_image}

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-dev \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create model directory
RUN mkdir -p {self.config.model_path}

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_PATH={self.config.model_path}
ENV API_HOST=0.0.0.0
ENV API_PORT={self.config.port}

# Expose port
EXPOSE {self.config.port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:{self.config.port}/health || exit 1

# Run the application
CMD ["python3", "main.py"]
'''
        
        dockerfile_path = output_path / "Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
    
    def generate_docker_compose(self, output_path: Path):
        """Generate docker-compose.yml"""
        compose_content = f'''# Auto-generated Docker Compose for RAG Model API

version: '3.8'

services:
  rag-model-api:
    build: .
    image: {self.config.image_name}:{self.config.tag}
    container_name: rag-model-api
    ports:
      - "{self.config.port}:{self.config.port}"
    volumes:
      - ./model:/app{self.config.model_path}
      - ./logs:/app/logs
    environment:
      - MODEL_PATH={self.config.model_path}
      - API_HOST=0.0.0.0
      - API_PORT={self.config.port}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{self.config.port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
'''
        
        # Add GPU support if requested
        if self.config.include_cuda:
            compose_content += '''
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
'''
        
        compose_path = output_path / "docker-compose.yml"
        with open(compose_path, 'w') as f:
            f.write(compose_content)
        
        # Generate docker build and run scripts
        self._generate_docker_scripts(output_path)
    
    def _generate_docker_scripts(self, output_path: Path):
        """Generate Docker helper scripts"""
        
        # Build script
        build_script = f'''#!/bin/bash

# Build Docker image for RAG Model API

echo "Building Docker image: {self.config.image_name}:{self.config.tag}"

docker build -t {self.config.image_name}:{self.config.tag} .

if [ $? -eq 0 ]; then
    echo "Docker image built successfully!"
    echo "Image: {self.config.image_name}:{self.config.tag}"
else
    echo "ERROR: Docker build failed!"
    exit 1
fi
'''
        
        build_path = output_path / "docker-build.sh"
        with open(build_path, 'w') as f:
            f.write(build_script)
        os.chmod(build_path, 0o755)
        
        # Run script
        run_script = f'''#!/bin/bash

# Run Docker container for RAG Model API

echo "Starting RAG Model API container..."

# Create necessary directories
mkdir -p model logs

# Run container
docker run -d \\
  --name rag-model-api \\
  -p {self.config.port}:{self.config.port} \\
  -v $(pwd)/model:/app{self.config.model_path} \\
  -v $(pwd)/logs:/app/logs \\
  {self.config.image_name}:{self.config.tag}

if [ $? -eq 0 ]; then
    echo "Container started successfully!"
    echo "API available at: http://localhost:{self.config.port}"
    echo "Documentation: http://localhost:{self.config.port}/docs"
    echo "Container logs: docker logs rag-model-api"
else
    echo "ERROR: Failed to start container!"
    exit 1
fi
'''
        
        run_path = output_path / "docker-run.sh"
        with open(run_path, 'w') as f:
            f.write(run_script)
        os.chmod(run_path, 0o755)

def main():
    """Example usage"""
    logging.basicConfig(level=logging.INFO)
    
    # Example: Export model to HuggingFace format
    export_config = ExportConfig(
        model_path="./fine_tuned_model",
        output_dir="./exported_model",
        model_name="my-rag-model",
        model_description="Fine-tuned conversational model with RAG capabilities",
        model_tags=["conversational", "rag", "text-generation"],
        push_to_hub=False  # Set to True to push to HuggingFace Hub
    )
    
    exporter = ModelExporter(export_config)
    success = exporter.export_to_huggingface()
    print(f"Export successful: {success}")
    
    # Example: Generate API
    api_config = APIConfig(
        model_path="./exported_model",
        api_name="my-rag-api",
        port=8000
    )
    
    api_generator = APIGenerator(api_config)
    api_success = api_generator.generate_api("./api_deployment")
    print(f"API generation successful: {api_success}")

if __name__ == "__main__":
    main() 