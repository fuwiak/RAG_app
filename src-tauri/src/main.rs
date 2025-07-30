#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    collections::HashMap,
    path::PathBuf,
    sync::{Arc, Mutex},
    io::Read,
    time::{Duration, SystemTime, UNIX_EPOCH},
    thread,
};

use anyhow::Result;
use chrono::{DateTime, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Manager, Emitter};
use tokio::{io::{AsyncBufReadExt, BufReader}, process::Command};
use std::process::Stdio;
use uuid::Uuid;
use text_splitter::{TextSplitter, ChunkConfig};
use csv::Reader;
use docx_rs::read_docx;
use sysinfo::{System, SystemExt, CpuExt, DiskExt, NetworkExt, ProcessorExt};
use log::{info, warn, error, debug};

// ---------- System Monitoring Data Models ------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemStats {
    pub cpu_usage: f32,
    pub memory_usage: u64,
    pub memory_total: u64,
    pub disk_usage: u64,
    pub disk_total: u64,
    pub gpu_usage: Option<f32>,
    pub gpu_memory: Option<u64>,
    pub network_rx: u64,
    pub network_tx: u64,
    pub temperature: Option<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenUsage {
    pub input_tokens: u32,
    pub output_tokens: u32,
    pub total_tokens: u32,
    pub cost_estimate: f64,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingProgress {
    pub epoch: u32,
    pub loss: f64,
    pub accuracy: f64,
    pub learning_rate: f64,
    pub elapsed_time: u64,
    pub estimated_remaining: u64,
    pub status: String, // 'idle' | 'training' | 'completed' | 'error'
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub id: String,
    pub timestamp: String,
    pub level: String, // 'info' | 'warn' | 'error' | 'debug'
    pub component: String,
    pub message: String,
}

// ---------- Enhanced RAG Data Models -----------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EmbeddingModel {
    #[serde(rename = "huggingface")]
    HuggingFace { model_name: String },
    #[serde(rename = "openai")]
    OpenAI { api_key: String, model: String },
    #[serde(rename = "local")]
    Local { model_path: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RAGMode {
    #[serde(rename = "fine_tuned_only")]
    FineTunedOnly,
    #[serde(rename = "fine_tuned_rag")]
    FineTunedWithRAG,
    #[serde(rename = "base_rag")]
    BaseWithRAG,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RAGConfig {
    pub embedding_model: EmbeddingModel,
    pub mode: RAGMode,
    pub chunk_size: usize,
    pub chunk_overlap: usize,
    pub top_k: usize,
    pub similarity_threshold: f32,
}

impl Default for RAGConfig {
    fn default() -> Self {
        Self {
            embedding_model: EmbeddingModel::HuggingFace { 
                model_name: "sentence-transformers/all-MiniLM-L6-v2".to_string() 
            },
            mode: RAGMode::BaseWithRAG,
            chunk_size: 200,
            chunk_overlap: 50,
            top_k: 5,
            similarity_threshold: 0.3,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessingResult {
    pub success: bool,
    pub message: String,
    pub chunks_created: usize,
    pub processing_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrievalResult {
    pub chunk_id: String,
    pub content: String,
    pub document_title: String,
    pub similarity_score: f32,
    pub source_info: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RAGResponse {
    pub answer: String,
    pub retrieved_context: Vec<RetrievalResult>,
    pub mode_used: RAGMode,
    pub processing_time_ms: u64,
}

// ---------- Original Data Models ---------------------------------------------------

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

fn chunk_text_with_config(text: &str, config: &RAGConfig) -> Vec<String> {
    let splitter = TextSplitter::new(ChunkConfig::new(config.chunk_size)
        .with_overlap(config.chunk_overlap)
        .with_trim(true));
    
    splitter.chunks(text).map(|s| s.to_string()).collect()
}

fn chunk_text(text: &str, chunk_size: usize, overlap: usize) -> Vec<String> {
    let config = RAGConfig {
        chunk_size,
        chunk_overlap: overlap,
        ..Default::default()
    };
    chunk_text_with_config(text, &config)
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
        "docx" => {
            // Extract text from DOCX
            match extract_docx_text(file_path).await {
                Ok(text) => Ok(text),
                Err(e) => Ok(format!("Could not extract text from DOCX: {}", e)),
            }
        }
        "csv" => {
            // Extract text from CSV
            match extract_csv_text(file_path).await {
                Ok(text) => Ok(text),
                Err(e) => Ok(format!("Could not extract text from CSV: {}", e)),
            }
        }
        _ => Ok(format!("Unsupported file type: {}", extension)),
    }
}

async fn extract_docx_text(file_path: &str) -> Result<String> {
    let mut file = std::fs::File::open(file_path)?;
    let mut buffer = Vec::new();
    file.read_to_end(&mut buffer)?;
    
    match read_docx(&buffer) {
        Ok(docx) => {
            let mut text = String::new();
            for paragraph in docx.document.body.children {
                if let docx_rs::DocumentChild::Paragraph(p) = paragraph {
                    for child in p.children {
                        if let docx_rs::ParagraphChild::Run(run) = child {
                            for run_child in run.children {
                                if let docx_rs::RunChild::Text(t) = run_child {
                                    text.push_str(&t.text);
                                }
                            }
                        }
                    }
                    text.push('\n');
                }
            }
            Ok(text)
        }
        Err(e) => Err(anyhow::anyhow!("Failed to parse DOCX: {}", e))
    }
}

async fn extract_csv_text(file_path: &str) -> Result<String> {
    let mut reader = Reader::from_path(file_path)?;
    let mut text = String::new();
    
    // Add headers if available
    if let Ok(headers) = reader.headers() {
        text.push_str(&headers.iter().collect::<Vec<_>>().join(" | "));
        text.push('\n');
    }
    
    // Add data rows
    for result in reader.records() {
        let record = result?;
        text.push_str(&record.iter().collect::<Vec<_>>().join(" | "));
        text.push('\n');
    }
    
    Ok(text)
}

// Enhanced embedding generation with multiple model support
async fn generate_embedding_with_config(text: &str, config: &RAGConfig) -> Result<Vec<f32>> {
    match &config.embedding_model {
        EmbeddingModel::HuggingFace { model_name } => {
            generate_huggingface_embedding(text, model_name).await
        }
        EmbeddingModel::OpenAI { api_key, model } => {
            generate_openai_embedding(text, api_key, model).await
        }
        EmbeddingModel::Local { model_path } => {
            generate_local_embedding(text, model_path).await
        }
    }
}

async fn generate_huggingface_embedding(text: &str, model_name: &str) -> Result<Vec<f32>> {
    // For now, use a simple mock - in production, integrate with HuggingFace API
    // or load model locally using candle/tch
    println!("Generating HuggingFace embedding with model: {}", model_name);
    
    // Mock embedding that varies based on text content
    let hash = sha2::Sha256::digest(text.as_bytes());
    let mut embedding = Vec::with_capacity(384);
    
    for (i, &byte) in hash.as_slice().iter().take(24).cycle().take(384).enumerate() {
        let value = (byte as f32 / 255.0) * 2.0 - 1.0; // Normalize to [-1, 1]
        let modified = value * (i as f32 * 0.01).sin();
        embedding.push(modified);
    }
    
    Ok(normalize_vector(embedding))
}

async fn generate_openai_embedding(text: &str, api_key: &str, model: &str) -> Result<Vec<f32>> {
    let client = reqwest::Client::new();
    
    let request_body = serde_json::json!({
        "input": text,
        "model": model
    });
    
    let response = client
        .post("https://api.openai.com/v1/embeddings")
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .json(&request_body)
        .send()
        .await?;
    
    if response.status().is_success() {
        let response_json: serde_json::Value = response.json().await?;
        if let Some(data) = response_json["data"].as_array() {
            if let Some(embedding_data) = data.get(0) {
                if let Some(embedding_array) = embedding_data["embedding"].as_array() {
                    let embedding: Vec<f32> = embedding_array
                        .iter()
                        .filter_map(|v| v.as_f64().map(|f| f as f32))
                        .collect();
                    return Ok(embedding);
                }
            }
        }
    }
    
    Err(anyhow::anyhow!("Failed to get embedding from OpenAI API"))
}

async fn generate_local_embedding(text: &str, _model_path: &str) -> Result<Vec<f32>> {
    // For now, use a sophisticated mock - in production, load local model
    println!("Generating local embedding from model path");
    
    // Create a more sophisticated mock based on text characteristics
    let words: Vec<&str> = text.split_whitespace().collect();
    let mut embedding = Vec::with_capacity(384);
    
    for i in 0..384 {
        let mut value = 0.0;
        
        // Base value from text length
        value += (text.len() as f32 / 1000.0).sin();
        
        // Add word count influence
        value += (words.len() as f32 / 100.0).cos();
        
        // Add character frequency influence
        if i < 256 {
            let char_count = text.chars().filter(|&c| c as u8 == i as u8).count();
            value += (char_count as f32 / 10.0).sin();
        }
        
        // Add positional encoding
        value += ((i as f32) / 384.0 * std::f32::consts::PI).sin() * 0.1;
        
        embedding.push(value);
    }
    
    Ok(normalize_vector(embedding))
}

fn normalize_vector(mut vector: Vec<f32>) -> Vec<f32> {
    let magnitude: f32 = vector.iter().map(|x| x * x).sum::<f32>().sqrt();
    if magnitude > 0.0 {
        for value in &mut vector {
            *value /= magnitude;
        }
    }
    vector
}

// Backward compatibility function
fn generate_embedding(text: &str) -> Vec<f32> {
    let config = RAGConfig::default();
    // Use blocking call for backward compatibility
    tokio::runtime::Runtime::new()
        .unwrap()
        .block_on(generate_embedding_with_config(text, &config))
        .unwrap_or_else(|_| vec![0.0; 384])
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

// ---------- Enhanced RAG Commands ----------------------------------------------

#[tauri::command]
async fn set_rag_config(
    config: RAGConfig,
    app: AppHandle,
) -> Result<(), String> {
    // Store RAG config in app state
    app.manage(Arc::new(Mutex::new(config)));
    Ok(())
}

#[tauri::command]
async fn get_rag_config(
    app: AppHandle,
) -> Result<RAGConfig, String> {
    match app.try_state::<Arc<Mutex<RAGConfig>>>() {
        Some(config_state) => {
            let config = config_state.lock().map_err(|e| e.to_string())?;
            Ok(config.clone())
        }
        None => Ok(RAGConfig::default()),
    }
}

#[tauri::command]
async fn process_document_enhanced(
    file_path: String,
    title: Option<String>,
    config: RAGConfig,
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
    app: AppHandle,
) -> Result<ProcessingResult, String> {
    let start_time = std::time::Instant::now();
    
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

    // Process chunks with enhanced configuration
    let doc_id = document.id.clone();
    let db_clone = db_state.inner().clone();
    let app_clone = app.clone();
    let config_clone = config.clone();
    
    let chunks_created = tokio::spawn(async move {
        process_document_chunks_enhanced(&doc_id, &content, &db_clone, &config_clone).await
    }).await.map_err(|e| e.to_string())??;

    let processing_time = start_time.elapsed().as_millis() as u64;
    
    let _ = app_clone.emit("document_processed", &doc_id);

    Ok(ProcessingResult {
        success: true,
        message: format!("Successfully processed document: {}", document.title),
        chunks_created,
        processing_time_ms: processing_time,
    })
}

async fn process_document_chunks_enhanced(
    document_id: &str,
    content: &str,
    db_state: &Arc<Mutex<Connection>>,
    config: &RAGConfig,
) -> Result<usize> {
    let chunks = chunk_text_with_config(content, config);
    
    for (index, chunk_content) in chunks.iter().enumerate() {
        let embedding = generate_embedding_with_config(chunk_content, config).await?;
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

    Ok(chunks.len())
}

#[tauri::command]
async fn query_rag_enhanced(
    query: String,
    mode: RAGMode,
    config: RAGConfig,
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<RAGResponse, String> {
    let start_time = std::time::Instant::now();
    
    let retrieved_context = match mode {
        RAGMode::FineTunedOnly => {
            // Don't retrieve context for fine-tuned only mode
            Vec::new()
        }
        RAGMode::FineTunedWithRAG | RAGMode::BaseWithRAG => {
            // Retrieve context for RAG modes
            retrieve_context_enhanced(&query, &config, db_state).await?
        }
    };
    
    let answer = generate_answer_with_mode(&query, &retrieved_context, &mode).await;
    let processing_time = start_time.elapsed().as_millis() as u64;
    
    Ok(RAGResponse {
        answer,
        retrieved_context,
        mode_used: mode,
        processing_time_ms: processing_time,
    })
}

async fn retrieve_context_enhanced(
    query: &str,
    config: &RAGConfig,
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<Vec<RetrievalResult>, String> {
    let query_embedding = generate_embedding_with_config(query, config)
        .await
        .map_err(|e| e.to_string())?;
    
    let mut results = Vec::new();

    let db = db_state.lock().map_err(|e| e.to_string())?;
    
    let mut stmt = db
        .prepare("SELECT dc.id, dc.content, dc.embedding, d.title, d.file_path
                  FROM document_chunks dc
                  JOIN documents d ON dc.document_id = d.id")
        .map_err(|e| e.to_string())?;

    let chunk_iter = stmt
        .query_map([], |row| {
            let chunk_id: String = row.get(0)?;
            let content: String = row.get(1)?;
            let embedding_bytes: Vec<u8> = row.get(2)?;
            let doc_title: String = row.get(3)?;
            let file_path: Option<String> = row.get(4)?;
            
            let embedding: Vec<f32> = embedding_bytes
                .chunks_exact(4)
                .map(|chunk| f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]))
                .collect();

            Ok((chunk_id, content, embedding, doc_title, file_path))
        })
        .map_err(|e| e.to_string())?;

    for chunk_result in chunk_iter {
        if let Ok((chunk_id, content, chunk_embedding, doc_title, file_path)) = chunk_result {
            let similarity = cosine_similarity(&query_embedding, &chunk_embedding);
            
            if similarity > config.similarity_threshold {
                results.push(RetrievalResult {
                    chunk_id,
                    content,
                    document_title: doc_title,
                    similarity_score: similarity,
                    source_info: file_path.unwrap_or_else(|| "Unknown source".to_string()),
                });
            }
        }
    }

    // Sort by similarity and take top-k
    results.sort_by(|a, b| b.similarity_score.partial_cmp(&a.similarity_score).unwrap());
    results.truncate(config.top_k);

    Ok(results)
}

async fn generate_answer_with_mode(
    query: &str,
    context: &[RetrievalResult],
    mode: &RAGMode,
) -> String {
    match mode {
        RAGMode::FineTunedOnly => {
            format!("Fine-tuned model response to: {}\n\n[This would be the output from your fine-tuned model]", query)
        }
        RAGMode::FineTunedWithRAG => {
            if context.is_empty() {
                format!("Fine-tuned model response (no relevant context found): {}", query)
            } else {
                let context_text = context.iter()
                    .map(|r| format!("From {}: {}", r.document_title, r.content))
                    .collect::<Vec<_>>()
                    .join("\n\n");
                
                format!("Fine-tuned model response based on context:\n\nQuery: {}\n\nRelevant context:\n{}\n\n[This would be the enhanced fine-tuned model response using the retrieved context]", query, context_text)
            }
        }
        RAGMode::BaseWithRAG => {
            if context.is_empty() {
                format!("I don't have relevant information to answer: {}\n\nPlease upload relevant documents to help me provide a better response.", query)
            } else {
                let context_text = context.iter()
                    .map(|r| r.content.clone())
                    .collect::<Vec<_>>()
                    .join("\n\n");
                
                format!("Based on the documents in your knowledge base:\n\nQuery: {}\n\nAnswer: Based on the retrieved information, here's what I found:\n\n{}\n\nSources: {}", 
                    query, 
                    context_text,
                    context.iter().map(|r| r.document_title.clone()).collect::<Vec<_>>().join(", ")
                )
            }
        }
    }
}

#[tauri::command]
async fn test_rag_query(
    query: String,
    config: RAGConfig,
    db_state: tauri::State<'_, Arc<Mutex<Connection>>>,
) -> Result<RAGResponse, String> {
    // This is specifically for testing - always use BaseWithRAG mode
    query_rag_enhanced(query, RAGMode::BaseWithRAG, config, db_state).await
}

// ---------- Original Tauri Commands --------------------------------------------

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

#[tauri::command]
async fn run_fine_tune(config: String, app: AppHandle) -> Result<(), String> {
    let script_path = app
        .path_resolver()
        .resolve_resource("../backend/fine_tune.py")
        .ok_or("Script not found")?;

        let mut child = Command::new("python3")
        .arg(script_path)
        .arg(config)
            .stdout(Stdio::piped())
            .spawn()
        .map_err(|e| e.to_string())?;

        if let Some(stdout) = child.stdout.take() {
        let app_handle = app.clone();
        tauri::async_runtime::spawn(async move {
            let mut reader = BufReader::new(stdout).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                let _ = app_handle.emit("fine_tune_log", line);
            }
        });
    }

    child.wait().await.map_err(|e| e.to_string())?;
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
            
            // Initialize default RAG configuration
            let default_config = RAGConfig::default();
            app.manage(Arc::new(Mutex::new(default_config)));

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Original commands
            upload_document,
            get_documents,
            search_documents,
            chat_with_documents,
            get_chat_history,
            delete_document,
            // Enhanced RAG commands
            set_rag_config,
            get_rag_config,
            process_document_enhanced,
            query_rag_enhanced,
            test_rag_query,
            // Fine-tune command from remote
            run_fine_tune,
            // System monitoring commands
            start_system_monitoring,
            stop_system_monitoring,
            get_system_stats,
            log_token_usage,
            clear_logs,
            export_logs,
            // Model export and deployment commands
            export_model_to_huggingface,
            generate_fastapi_endpoint,
            generate_docker_deployment,
            // Additional RAG commands
            chat_base_model,
            chat_fine_tuned,
            chat_hybrid_mode,
        ])
        .run(tauri::generate_context!())
        .expect("Error running RAG application");
}

// ---------- System Monitoring Commands ---------------------------------------------

#[tauri::command]
async fn start_system_monitoring(app: AppHandle) -> Result<(), String> {
    info!("Starting system monitoring");
    Ok(())
}

#[tauri::command]
async fn stop_system_monitoring() -> Result<(), String> {
    info!("Stopping system monitoring");
    Ok(())
}

#[tauri::command]
async fn get_system_stats() -> Result<SystemStats, String> {
    // Mock implementation for now
    Ok(SystemStats {
        cpu_usage: 45.2,
        memory_usage: 8589934592, // 8GB
        memory_total: 17179869184, // 16GB
        disk_usage: 107374182400, // 100GB
        disk_total: 536870912000, // 500GB
        gpu_usage: Some(30.0),
        gpu_memory: Some(4294967296), // 4GB
        network_rx: 1048576, // 1MB/s
        network_tx: 524288,  // 512KB/s
        temperature: Some(65.0),
    })
}

#[tauri::command]
async fn log_token_usage(
    input_tokens: u32,
    output_tokens: u32,
    cost_estimate: f64,
    app: AppHandle
) -> Result<(), String> {
    let token_usage = TokenUsage {
        input_tokens,
        output_tokens,
        total_tokens: input_tokens + output_tokens,
        cost_estimate,
        timestamp: Utc::now().to_rfc3339(),
    };
    
    let _ = app.emit("token_usage", &token_usage);
    Ok(())
}

#[tauri::command]
async fn clear_logs() -> Result<(), String> {
    info!("Clearing logs");
    Ok(())
}

#[tauri::command]
async fn export_logs() -> Result<(), String> {
    info!("Exporting logs");
    Ok(())
}

// ---------- Model Export and Deployment Commands ----------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportConfig {
    pub model_path: String,
    pub output_dir: String,
    pub model_name: String,
    pub export_format: String,
    pub include_tokenizer: bool,
    pub push_to_hub: bool,
    pub hub_token: Option<String>,
    pub hub_repo_name: Option<String>,
    pub model_description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct APIConfig {
    pub model_path: String,
    pub api_name: String,
    pub port: u16,
    pub host: String,
    pub enable_cors: bool,
    pub max_workers: u8,
    pub auth_token: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DockerConfig {
    pub image_name: String,
    pub tag: String,
    pub base_image: String,
    pub port: u16,
    pub include_cuda: bool,
    pub model_path: String,
}

#[tauri::command]
async fn export_model_to_huggingface(config: ExportConfig) -> Result<String, String> {
    info!("Exporting model to HuggingFace format: {:?}", config);
    
    // Mock implementation - in real app, this would call the Python export script
    let output = format!(
        "Model '{}' exported successfully to HuggingFace format at '{}'",
        config.model_name, config.output_dir
    );
    
    if config.push_to_hub {
        return Ok(format!("{}\nModel pushed to HuggingFace Hub: {}", 
            output, config.hub_repo_name.unwrap_or("unknown".to_string())));
    }
    
    Ok(output)
}

#[tauri::command]
async fn generate_fastapi_endpoint(config: APIConfig, output_dir: String) -> Result<String, String> {
    info!("Generating FastAPI endpoint: {:?}", config);
    
    // Mock implementation - in real app, this would generate the API files
    Ok(format!(
        "FastAPI endpoint '{}' generated successfully at '{}'\nAPI will run on {}:{}",
        config.api_name, output_dir, config.host, config.port
    ))
}

#[tauri::command]
async fn generate_docker_deployment(config: DockerConfig, output_dir: String) -> Result<String, String> {
    info!("Generating Docker deployment: {:?}", config);
    
    // Mock implementation - in real app, this would generate Docker files
    Ok(format!(
        "Docker deployment '{}:{}' generated successfully at '{}'",
        config.image_name, config.tag, output_dir
    ))
}

// ---------- Additional Chat Commands ----------------------------------------------

#[tauri::command]
async fn chat_base_model(
    query: String, 
    temperature: f32, 
    max_tokens: u32
) -> Result<ChatResponse, String> {
    info!("Chat with base model: {}", query);
    
    // Mock implementation for base model chat
    let response = format!("Base model response to: {}", query);
    
    Ok(ChatResponse {
        message: ChatMessage {
            content: response,
            role: "assistant".to_string(),
        },
        sources: vec![],
    })
}

#[tauri::command]
async fn chat_fine_tuned(
    query: String, 
    temperature: f32, 
    max_tokens: u32
) -> Result<ChatResponse, String> {
    info!("Chat with fine-tuned model: {}", query);
    
    // Mock implementation for fine-tuned model chat
    let response = format!("Fine-tuned model response to: {}", query);
    
    Ok(ChatResponse {
        message: ChatMessage {
            content: response,
            role: "assistant".to_string(),
        },
        sources: vec![],
    })
}

#[tauri::command]
async fn chat_hybrid_mode(
    query: String,
    temperature: f32,
    max_tokens: u32,
    use_fine_tuned: bool,
    use_rag: bool,
) -> Result<ChatResponse, String> {
    info!("Chat with hybrid mode: query={}, fine_tuned={}, rag={}", 
          query, use_fine_tuned, use_rag);
    
    // Mock implementation for hybrid mode
    let mut response = String::new();
    
    if use_fine_tuned && use_rag {
        response = format!("Hybrid (Fine-tuned + RAG) response to: {}", query);
    } else if use_fine_tuned {
        response = format!("Fine-tuned model response to: {}", query);
    } else if use_rag {
        response = format!("RAG-enhanced response to: {}", query);
    } else {
        response = format!("Base model response to: {}", query);
    }
    
    // Mock retrieved sources for RAG
    let mut sources = vec![];
    if use_rag {
        sources.push(SearchResult {
            relevant_chunks: vec![format!("Retrieved context for: {}", query)],
        });
    }
    
    Ok(ChatResponse {
        message: ChatMessage {
            content: response,
            role: "assistant".to_string(),
        },
        sources,
    })
}
