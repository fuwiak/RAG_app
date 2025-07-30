<script lang="ts">
  import { onMount } from 'svelte';
  import { invoke } from '@tauri-apps/api/core';
  // Types
  interface Document {
    id: string;
    title: string;
    content: string;
    file_path?: string;
    file_type: string;
    content_hash: string;
    created_at: string;
    updated_at: string;
  }

  interface ChatMessage {
    id: string;
    content: string;
    role: string;
    document_references: string[];
    created_at: string;
  }

  interface SearchResult {
    document: Document;
    relevant_chunks: string[];
    similarity_score: number;
  }

  interface ChatResponse {
    message: ChatMessage;
    sources: SearchResult[];
  }

  // State
  let documents: Document[] = [];
  let chatMessages: ChatMessage[] = [];
  let currentMessage = '';
  let isLoading = false;
  let selectedTab: 'chat' | 'documents' | 'search' = 'chat';
  let searchQuery = '';
  let searchResults: SearchResult[] = [];
  let isDragOver = false;

  // Load data
  async function loadDocuments() {
    try {
      documents = await invoke<Document[]>('get_documents');
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  }

  async function loadChatHistory() {
    try {
      chatMessages = await invoke<ChatMessage[]>('get_chat_history');
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  }

  // Document upload
  let fileInput: HTMLInputElement;
  
  function triggerFileUpload() {
    fileInput?.click();
  }
  
  async function handleFileUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    
    if (file) {
      try {
        isLoading = true;
        // For demo purposes, we'll use the file name as the file path
        // In a real app, you'd upload the file to a server or save it locally
        const document = await invoke<Document>('upload_document', {
          filePath: file.name,
          title: file.name
        });
        
        documents = [document, ...documents];
        isLoading = false;
      } catch (error) {
        console.error('Error uploading document:', error);
        isLoading = false;
      }
    }
    
    // Reset the input
    target.value = '';
  }

  // File drop handling
  function handleDrop(event: DragEvent) {
    event.preventDefault();
    isDragOver = false;
    
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === 'application/pdf' || file.type === 'text/plain' || file.name.endsWith('.md')) {
        // Note: In a real implementation, you'd need to handle file path differently
        // This is a simplified example
        console.log('File dropped:', file.name);
      }
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    isDragOver = true;
  }

  function handleDragLeave() {
    isDragOver = false;
  }

  // Chat functionality
  async function sendMessage() {
    if (!currentMessage.trim() || isLoading) return;

    const userMessage = currentMessage;
    currentMessage = '';
    isLoading = true;

    // Add user message to chat immediately
    const tempUserMessage: ChatMessage = {
      id: 'temp-' + Date.now(),
      content: userMessage,
      role: 'user',
      document_references: [],
      created_at: new Date().toISOString()
    };
    chatMessages = [...chatMessages, tempUserMessage];

    try {
      const response = await invoke<ChatResponse>('chat_with_documents', {
        message: userMessage
      });

      // Replace temp message with actual response
      chatMessages = chatMessages.filter(m => m.id !== tempUserMessage.id);
      chatMessages = [...chatMessages, tempUserMessage, response.message];
      
      // Scroll to bottom
      setTimeout(() => {
        const chatContainer = document.querySelector('.chat-messages');
        if (chatContainer) {
          chatContainer.scrollTop = chatContainer.scrollHeight;
        }
      }, 100);

    } catch (error) {
      console.error('Error sending message:', error);
      chatMessages = chatMessages.filter(m => m.id !== tempUserMessage.id);
    } finally {
      isLoading = false;
    }
  }

  // Search functionality
  async function searchDocuments() {
    if (!searchQuery.trim()) {
      searchResults = [];
      return;
    }

    try {
      isLoading = true;
      searchResults = await invoke<SearchResult[]>('search_documents', {
        query: searchQuery
      });
    } catch (error) {
      console.error('Error searching documents:', error);
    } finally {
      isLoading = false;
    }
  }

  // Delete document
  async function deleteDocument(docId: string) {
    if (confirm('Are you sure you want to delete this document?')) {
      try {
        await invoke('delete_document', { documentId: docId });
        documents = documents.filter(doc => doc.id !== docId);
      } catch (error) {
        console.error('Error deleting document:', error);
      }
    }
  }

  // Format date
  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // Handle Enter key in chat input
  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  onMount(() => {
    loadDocuments();
    loadChatHistory();
  });
</script>

<main>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <h1 class="app-title">RAG App</h1>
        <p class="app-subtitle">Retrieval-Augmented Generation Assistant</p>
      </div>
      
      <!-- Navigation tabs -->
      <nav class="tabs">
        <button 
          class="tab {selectedTab === 'chat' ? 'active' : ''}"
          on:click={() => selectedTab = 'chat'}
        >
          💬 Chat
        </button>
        <button 
          class="tab {selectedTab === 'documents' ? 'active' : ''}"
          on:click={() => selectedTab = 'documents'}
        >
          📄 Documents ({documents.length})
        </button>
        <button 
          class="tab {selectedTab === 'search' ? 'active' : ''}"
          on:click={() => selectedTab = 'search'}
        >
          🔍 Search
        </button>
      </nav>
    </header>

    <!-- Main content area -->
    <div class="main-content">
      
      <!-- Chat Tab -->
      {#if selectedTab === 'chat'}
        <div class="chat-container">
          {#if documents.length === 0}
                         <div class="empty-state">
               <div class="empty-icon">📚</div>
               <h3>No documents uploaded yet</h3>
               <p>Upload some documents to start chatting with your knowledge base.</p>
               <button class="primary-button" on:click={triggerFileUpload}>
                 📎 Upload Document
               </button>
             </div>
          {:else}
            <div class="chat-messages">
              {#if chatMessages.length === 0}
                <div class="chat-welcome">
                  <h3>Welcome to your RAG Assistant! 👋</h3>
                  <p>Ask questions about your uploaded documents and I'll help you find answers.</p>
                </div>
              {/if}
              
              {#each chatMessages as message}
                <div class="message {message.role}">
                  <div class="message-content">
                    <div class="message-text">{message.content}</div>
                    <div class="message-time">{formatDate(message.created_at)}</div>
                  </div>
                </div>
              {/each}
              
              {#if isLoading}
                <div class="message assistant loading">
                  <div class="message-content">
                    <div class="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              {/if}
            </div>
            
            <div class="chat-input-container">
              <div class="chat-input-wrapper">
                <textarea
                  bind:value={currentMessage}
                  placeholder="Ask a question about your documents..."
                  on:keydown={handleKeyDown}
                  disabled={isLoading}
                  rows="1"
                  class="chat-input"
                ></textarea>
                <button 
                  class="send-button" 
                  on:click={sendMessage}
                  disabled={!currentMessage.trim() || isLoading}
                >
                  🚀
                </button>
              </div>
            </div>
          {/if}
        </div>
      
      <!-- Documents Tab -->
      {:else if selectedTab === 'documents'}
        <div class="documents-container">
                     <div class="documents-header">
             <h2>Document Library</h2>
             <button class="primary-button" on:click={triggerFileUpload}>
               📎 Upload Document
             </button>
           </div>
          
          <!-- Upload area -->
                     <div 
             class="upload-area {isDragOver ? 'drag-over' : ''}"
             role="button"
             tabindex="0"
             aria-label="Drag and drop files here or click to upload"
             on:drop={handleDrop}
             on:dragover={handleDragOver}
             on:dragleave={handleDragLeave}
             on:click={triggerFileUpload}
             on:keydown={(e) => e.key === 'Enter' && triggerFileUpload()}
           >
            <div class="upload-content">
              <div class="upload-icon">📁</div>
              <p>Drag and drop documents here or click to upload</p>
              <p class="upload-formats">Supported: PDF, TXT, MD</p>
            </div>
          </div>
          
          <!-- Documents list -->
          {#if documents.length === 0}
            <div class="empty-state">
              <div class="empty-icon">📄</div>
              <h3>No documents yet</h3>
              <p>Upload your first document to get started.</p>
            </div>
          {:else}
            <div class="documents-grid">
              {#each documents as doc}
                <div class="document-card">
                  <div class="document-header">
                    <div class="document-icon">
                      {#if doc.file_type === 'pdf'}📕
                      {:else if doc.file_type === 'txt'}📝
                      {:else if doc.file_type === 'md'}📖
                      {:else}📄{/if}
                    </div>
                    <div class="document-info">
                      <h4 class="document-title">{doc.title}</h4>
                      <p class="document-meta">
                        {doc.file_type.toUpperCase()} • {formatDate(doc.created_at)}
                      </p>
                    </div>
                    <button 
                      class="delete-button"
                      on:click={() => deleteDocument(doc.id)}
                      title="Delete document"
                    >
                      ✕
                    </button>
                  </div>
                  <div class="document-preview">
                    {doc.content.substring(0, 150)}...
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      
      <!-- Search Tab -->
      {:else if selectedTab === 'search'}
        <div class="search-container">
          <div class="search-header">
            <h2>Search Documents</h2>
          </div>
          
          <div class="search-input-container">
            <input
              type="text"
              bind:value={searchQuery}
              placeholder="Search your documents..."
              class="search-input"
              on:input={searchDocuments}
            />
            <button class="search-button" on:click={searchDocuments}>
              🔍
            </button>
          </div>
          
          {#if searchResults.length > 0}
            <div class="search-results">
              <h3>Search Results ({searchResults.length})</h3>
              {#each searchResults as result}
                <div class="search-result">
                  <div class="result-header">
                    <h4>{result.document.title}</h4>
                    <div class="similarity-score">
                      {Math.round(result.similarity_score * 100)}% match
                    </div>
                  </div>
                  <div class="result-chunks">
                    {#each result.relevant_chunks as chunk}
                      <div class="chunk">{chunk}</div>
                    {/each}
                  </div>
                </div>
              {/each}
            </div>
          {:else if searchQuery && !isLoading}
            <div class="empty-state">
              <div class="empty-icon">🔍</div>
              <h3>No results found</h3>
              <p>Try adjusting your search terms.</p>
            </div>
          {/if}
        </div>
             {/if}
     </div>
   </div>
   
   <!-- Hidden file input -->
   <input
     type="file"
     bind:this={fileInput}
     on:change={handleFileUpload}
     accept=".pdf,.txt,.md"
     style="display: none;"
   />
 </main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
  }

  .app-container {
    max-width: 1200px;
    margin: 0 auto;
    min-height: 100vh;
    background: white;
    display: flex;
    flex-direction: column;
    box-shadow: 0 0 50px rgba(0,0,0,0.1);
  }

  .header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    text-align: center;
  }

  .header-content {
    margin-bottom: 2rem;
  }

  .app-title {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .app-subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    margin: 0;
  }

  .tabs {
    display: flex;
    justify-content: center;
    gap: 1rem;
  }

  .tab {
    padding: 0.75rem 1.5rem;
    background: rgba(255,255,255,0.1);
    color: white;
    border: 2px solid rgba(255,255,255,0.2);
    border-radius: 25px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 1rem;
    font-weight: 500;
  }

  .tab:hover {
    background: rgba(255,255,255,0.2);
    transform: translateY(-2px);
  }

  .tab.active {
    background: white;
    color: #667eea;
    border-color: white;
  }

  .main-content {
    flex: 1;
    padding: 2rem;
    overflow: hidden;
  }

  /* Chat Styles */
  .chat-container {
    height: calc(100vh - 200px);
    display: flex;
    flex-direction: column;
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    margin-bottom: 1rem;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    background: #fafafa;
  }

  .chat-welcome {
    text-align: center;
    padding: 2rem;
    color: #666;
  }

  .message {
    margin-bottom: 1rem;
    display: flex;
  }

  .message.user {
    justify-content: flex-end;
  }

  .message.assistant {
    justify-content: flex-start;
  }

  .message-content {
    max-width: 70%;
    padding: 1rem;
    border-radius: 18px;
    position: relative;
  }

  .message.user .message-content {
    background: #667eea;
    color: white;
  }

  .message.assistant .message-content {
    background: white;
    border: 1px solid #e0e0e0;
  }

  .message-text {
    line-height: 1.5;
    margin-bottom: 0.5rem;
  }

  .message-time {
    font-size: 0.8rem;
    opacity: 0.7;
  }

  .typing-indicator {
    display: flex;
    gap: 4px;
    align-items: center;
  }

  .typing-indicator span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #667eea;
    animation: typing 1.4s infinite ease-in-out;
  }

  .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
  .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

  @keyframes typing {
    0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
  }

  .chat-input-container {
    border-top: 1px solid #e0e0e0;
    padding-top: 1rem;
  }

  .chat-input-wrapper {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
  }

  .chat-input {
    flex: 1;
    padding: 1rem;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    resize: none;
    font-family: inherit;
    font-size: 1rem;
    line-height: 1.5;
    max-height: 120px;
  }

  .chat-input:focus {
    outline: none;
    border-color: #667eea;
  }

  .send-button {
    padding: 1rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-size: 1.2rem;
    transition: all 0.3s ease;
  }

  .send-button:hover:not(:disabled) {
    background: #5a67d8;
    transform: translateY(-2px);
  }

  .send-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Documents Styles */
  .documents-container {
    height: calc(100vh - 200px);
    overflow-y: auto;
  }

  .documents-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .documents-header h2 {
    margin: 0;
    color: #333;
  }

  .upload-area {
    border: 3px dashed #ccc;
    border-radius: 12px;
    padding: 3rem;
    text-align: center;
    margin-bottom: 2rem;
    transition: all 0.3s ease;
    cursor: pointer;
  }

  .upload-area:hover, .upload-area.drag-over {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.05);
  }

  .upload-content {
    color: #666;
  }

  .upload-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  .upload-formats {
    font-size: 0.9rem;
    opacity: 0.7;
    margin-top: 0.5rem;
  }

  .documents-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .document-card {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 1.5rem;
    background: white;
    transition: all 0.3s ease;
  }

  .document-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
  }

  .document-header {
    display: flex;
    align-items: flex-start;
    margin-bottom: 1rem;
  }

  .document-icon {
    font-size: 2rem;
    margin-right: 1rem;
  }

  .document-info {
    flex: 1;
  }

  .document-title {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 1.1rem;
  }

  .document-meta {
    margin: 0;
    color: #666;
    font-size: 0.9rem;
  }

  .delete-button {
    background: #ff4757;
    color: white;
    border: none;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.3s ease;
  }

  .delete-button:hover {
    background: #ff3742;
    transform: scale(1.1);
  }

  .document-preview {
    color: #666;
    font-size: 0.9rem;
    line-height: 1.4;
  }

  /* Search Styles */
  .search-container {
    height: calc(100vh - 200px);
    overflow-y: auto;
  }

  .search-header h2 {
    margin: 0 0 2rem 0;
    color: #333;
  }

  .search-input-container {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .search-input {
    flex: 1;
    padding: 1rem;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    font-size: 1rem;
  }

  .search-input:focus {
    outline: none;
    border-color: #667eea;
  }

  .search-button {
    padding: 1rem 1.5rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    font-size: 1.2rem;
  }

  .search-results h3 {
    color: #333;
    margin-bottom: 1.5rem;
  }

  .search-result {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    background: white;
  }

  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .result-header h4 {
    margin: 0;
    color: #333;
  }

  .similarity-score {
    background: #667eea;
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 15px;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .result-chunks {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .chunk {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #667eea;
    font-size: 0.9rem;
    line-height: 1.4;
  }

  /* Common Styles */
  .primary-button {
    background: #667eea;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 500;
    transition: all 0.3s ease;
  }

  .primary-button:hover {
    background: #5a67d8;
    transform: translateY(-2px);
  }

  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: #666;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .empty-state h3 {
    margin: 0 0 1rem 0;
    color: #333;
  }

  .empty-state p {
    margin: 0 0 2rem 0;
    line-height: 1.5;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .app-container {
      margin: 0;
      border-radius: 0;
    }
    
    .header {
      padding: 1.5rem;
    }
    
    .app-title {
      font-size: 2rem;
    }
    
    .tabs {
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .main-content {
      padding: 1rem;
    }
    
    .documents-grid {
      grid-template-columns: 1fr;
    }
    
    .message-content {
      max-width: 85%;
    }
  }
</style>
