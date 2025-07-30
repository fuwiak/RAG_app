<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';

  type Mode = 'base' | 'fine' | 'rag';
  let message = '';
  let mode: Mode = 'rag';
  let response = '';
  let retrieved = '';
  let loading = false;
  let selectedTab: 'chat' | 'settings' | 'history' = 'chat';
  let chatHistory: Array<{id: string, message: string, response: string, mode: Mode, timestamp: Date}> = [];
  let temperature = 0.7;
  let maxTokens = 150;

  interface ChatResult {
    message: {
      content: string;
    };
    sources: Array<{
      relevant_chunks: string[];
    }>;
  }

  async function send() {
    if (!message.trim()) return;
    loading = true;
    
    const currentMessage = message;
    const currentMode = mode;
    
    try {
      const res = await invoke<ChatResult>('chat_with_documents', { 
        query: currentMessage 
      });
      
      response = res.message.content;
      retrieved = res.sources.map((s: any) => s.relevant_chunks.join('\n')).join('\n');
      
      // Add to history
      chatHistory = [{
        id: Date.now().toString(),
        message: currentMessage,
        response: response,
        mode: currentMode,
        timestamp: new Date()
      }, ...chatHistory];
      
      // Clear input
      message = '';
      
    } catch (e) {
      response = `Error: ${e}`;
      retrieved = '';
    }
    loading = false;
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  function clearHistory() {
    chatHistory = [];
    response = '';
    retrieved = '';
  }

  function formatTime(date: Date): string {
    return date.toLocaleTimeString();
  }

  function getModeIcon(mode: Mode): string {
    switch (mode) {
      case 'base': return '🤖';
      case 'fine': return '🎯';
      case 'rag': return '📚';
    }
  }

  function getModeLabel(mode: Mode): string {
    switch (mode) {
      case 'base': return 'Base Model';
      case 'fine': return 'Fine-tuned Model';
      case 'rag': return 'RAG Enhanced';
    }
  }
</script>

<main>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <h1 class="app-title">🎮 Playground</h1>
        <p class="app-subtitle">Test and interact with your AI models</p>
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
          class="tab {selectedTab === 'settings' ? 'active' : ''}"
          on:click={() => selectedTab = 'settings'}
        >
          ⚙️ Settings
        </button>
        <button 
          class="tab {selectedTab === 'history' ? 'active' : ''}"
          on:click={() => selectedTab = 'history'}
        >
          📜 History ({chatHistory.length})
        </button>
      </nav>
    </header>

    <!-- Main content -->
    <div class="main-content">
      <!-- Chat Tab -->
      {#if selectedTab === 'chat'}
        <div class="chat-container">
          <!-- Model Selection Header -->
          <div class="model-selection">
            <h3>Select Model Mode</h3>
            <div class="mode-buttons">
              <button 
                class="mode-button {mode === 'base' ? 'active' : ''}" 
                on:click={() => mode = 'base'}
              >
                🤖 Base Model
                <small>Raw language model</small>
              </button>
              <button 
                class="mode-button {mode === 'fine' ? 'active' : ''}" 
                on:click={() => mode = 'fine'}
              >
                🎯 Fine-tuned
                <small>Your trained model</small>
              </button>
              <button 
                class="mode-button {mode === 'rag' ? 'active' : ''}" 
                on:click={() => mode = 'rag'}
              >
                📚 RAG Enhanced
                <small>Model + Knowledge Base</small>
              </button>
            </div>
          </div>

          <!-- Chat Interface -->
          <div class="chat-interface">
            <div class="chat-input-section">
              <div class="input-header">
                <span class="current-mode">
                  {getModeIcon(mode)} {getModeLabel(mode)}
                </span>
                <span class="input-hint">Press Enter to send, Shift+Enter for new line</span>
              </div>
              
              <div class="input-container">
                <textarea
                  bind:value={message}
                  placeholder="Ask me anything..."
                  class="chat-input"
                  rows="3"
                  on:keydown={handleKeyDown}
                  disabled={loading}
                ></textarea>
                <button 
                  class="send-button" 
                  on:click={send} 
                  disabled={loading || !message.trim()}
                >
                  {loading ? '🔄' : '🚀'}
                </button>
              </div>
            </div>

            <!-- Current Response -->
            {#if response || loading}
              <div class="response-section">
                <div class="response-header">
                  <h3>💬 Response</h3>
                  <span class="mode-badge mode-{mode}">
                    {getModeIcon(mode)} {getModeLabel(mode)}
                  </span>
                </div>
                
                <div class="response-content">
                  {#if loading}
                    <div class="loading-indicator">
                      <div class="loading-spinner"></div>
                      <p>Thinking...</p>
                    </div>
                  {:else}
                    <p class="response-text">{response}</p>
                  {/if}
                </div>
              </div>
            {/if}

            <!-- Retrieved Context (for RAG mode) -->
            {#if mode === 'rag' && retrieved && !loading}
              <div class="context-section">
                <div class="context-header">
                  <h3>📋 Retrieved Context</h3>
                  <span class="context-badge">Knowledge Base</span>
                </div>
                <div class="context-content">
                  <pre class="context-text">{retrieved}</pre>
                </div>
              </div>
            {/if}
          </div>
        </div>

      <!-- Settings Tab -->
      {:else if selectedTab === 'settings'}
        <div class="settings-container">
          <div class="config-header">
            <h2>⚙️ Model Settings</h2>
            <p>Configure your model parameters</p>
          </div>
          
          <div class="config-section">
            <h3>🎛️ Generation Parameters</h3>
            <div class="settings-grid">
              <div class="setting-item">
                <label for="temperature">Temperature: {temperature}</label>
                <input 
                  id="temperature"
                  type="range" 
                  min="0" 
                  max="2" 
                  step="0.1" 
                  bind:value={temperature}
                  class="slider"
                />
                <small>Controls randomness. Lower = more focused, Higher = more creative</small>
              </div>
              
              <div class="setting-item">
                <label for="max-tokens">Max Tokens: {maxTokens}</label>
                <input 
                  id="max-tokens"
                  type="range" 
                  min="50" 
                  max="500" 
                  step="10" 
                  bind:value={maxTokens}
                  class="slider"
                />
                <small>Maximum length of generated response</small>
              </div>
            </div>
          </div>

          <div class="config-section">
            <h3>🎯 Model Information</h3>
            <div class="model-info">
              <div class="info-item">
                <span class="info-label">Current Mode:</span>
                <span class="info-value">{getModeIcon(mode)} {getModeLabel(mode)}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Status:</span>
                <span class="info-value status-ready">✅ Ready</span>
              </div>
            </div>
          </div>
        </div>

      <!-- History Tab -->
      {:else if selectedTab === 'history'}
        <div class="history-container">
          <div class="history-header">
            <div class="config-header">
              <h2>📜 Chat History</h2>
              <p>Review your previous conversations</p>
            </div>
            
            {#if chatHistory.length > 0}
              <button class="clear-button" on:click={clearHistory}>
                🗑️ Clear History
              </button>
            {/if}
          </div>
          
          {#if chatHistory.length > 0}
            <div class="history-list">
              {#each chatHistory as chat}
                <div class="history-item">
                  <div class="history-item-header">
                    <span class="history-mode">{getModeIcon(chat.mode)} {getModeLabel(chat.mode)}</span>
                    <span class="history-time">{formatTime(chat.timestamp)}</span>
                  </div>
                  
                  <div class="history-message">
                    <h4>Question:</h4>
                    <p>{chat.message}</p>
                  </div>
                  
                  <div class="history-response">
                    <h4>Response:</h4>
                    <p>{chat.response}</p>
                  </div>
                </div>
              {/each}
  </div>
          {:else}
            <div class="empty-state">
              <div class="empty-icon">💬</div>
              <h3>No chat history yet</h3>
              <p>Start a conversation in the Chat tab to see your history here</p>
    </div>
  {/if}
    </div>
  {/if}
</div>
  </div>
</main>

<style>
  .app-container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
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
    font-weight: bold;
    margin: 0 0 0.5rem 0;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .app-subtitle {
    font-size: 1.2rem;
    margin: 0;
    opacity: 0.9;
  }

  .tabs {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .tab {
    background: rgba(255, 255, 255, 0.1);
    color: white;
    border: 2px solid rgba(255, 255, 255, 0.2);
    padding: 0.75rem 1.5rem;
    border-radius: 25px;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 500;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
  }

  .tab:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.4);
    transform: translateY(-2px);
  }

  .tab.active {
    background: white;
    color: #667eea;
    border-color: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .main-content {
    flex: 1;
    padding: 2rem;
    background: #f8f9fa;
  }

  .chat-container, .settings-container, .history-container {
    max-width: 900px;
    margin: 0 auto;
  }

  .model-selection {
    margin-bottom: 2rem;
    text-align: center;
  }

  .model-selection h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.3rem;
  }

  .mode-buttons {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .mode-button {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 1.5rem;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    background: white;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 1rem;
    font-weight: 500;
    text-align: center;
  }

  .mode-button:hover {
    border-color: #667eea;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
  }

  .mode-button.active {
    border-color: #667eea;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .mode-button small {
    margin-top: 0.5rem;
    opacity: 0.8;
    font-size: 0.9rem;
  }

  .chat-interface {
    background: white;
    border-radius: 12px;
    border: 1px solid #e0e0e0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    overflow: hidden;
  }

  .chat-input-section {
    padding: 1.5rem;
    border-bottom: 1px solid #e0e0e0;
  }

  .input-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .current-mode {
    font-weight: 600;
    color: #667eea;
  }

  .input-hint {
    font-size: 0.85rem;
    color: #666;
  }

  .input-container {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
  }

  .chat-input {
    flex: 1;
    padding: 1rem;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 1rem;
    font-family: inherit;
    resize: vertical;
    transition: border-color 0.3s ease;
  }

  .chat-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .send-button {
    padding: 1rem 1.5rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1.2rem;
    transition: all 0.3s ease;
  }

  .send-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .send-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .response-section, .context-section {
    padding: 1.5rem;
    border-bottom: 1px solid #e0e0e0;
  }

  .response-section:last-child, .context-section:last-child {
    border-bottom: none;
  }

  .response-header, .context-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .response-header h3, .context-header h3 {
    margin: 0;
    color: #333;
  }

  .mode-badge, .context-badge {
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.25rem 0.75rem;
    border-radius: 15px;
  }

  .mode-badge.mode-base {
    background: #e3f2fd;
    color: #1976d2;
  }

  .mode-badge.mode-fine {
    background: #f3e5f5;
    color: #7b1fa2;
  }

  .mode-badge.mode-rag {
    background: #e8f5e8;
    color: #388e3c;
  }

  .context-badge {
    background: #fff3e0;
    color: #f57c00;
  }

  .response-content {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1.5rem;
  }

  .loading-indicator {
    display: flex;
    align-items: center;
    gap: 1rem;
    color: #666;
  }

  .loading-spinner {
    width: 20px;
    height: 20px;
    border: 3px solid #e0e0e0;
    border-top: 3px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .response-text {
    margin: 0;
    line-height: 1.6;
    white-space: pre-wrap;
  }

  .context-content {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1rem;
  }

  .context-text {
    margin: 0;
    font-family: monospace;
    font-size: 0.9rem;
    line-height: 1.5;
    white-space: pre-wrap;
    color: #555;
  }

  /* Settings Styles */
  .config-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .config-header h2 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 1.8rem;
  }

  .config-header p {
    color: #666;
    margin: 0;
    font-size: 1.1rem;
  }

  .config-section {
    margin-bottom: 2rem;
    padding: 1.5rem;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    background: white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .config-section h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.3rem;
  }

  .settings-grid {
    display: grid;
    gap: 2rem;
  }

  .setting-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .setting-item label {
    font-weight: 600;
    color: #333;
  }

  .slider {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #e0e0e0;
    outline: none;
  }

  .slider::-webkit-slider-thumb {
    appearance: none;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #667eea;
    cursor: pointer;
  }

  .setting-item small {
    color: #666;
    font-size: 0.9rem;
  }

  .model-info {
    display: grid;
    gap: 1rem;
  }

  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: #f8f9fa;
    border-radius: 8px;
  }

  .info-label {
    font-weight: 500;
    color: #666;
  }

  .info-value {
    font-weight: 600;
    color: #333;
  }

  .status-ready {
    color: #388e3c !important;
  }

  /* History Styles */
  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 2rem;
  }

  .clear-button {
    background: #f44336;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.3s ease;
  }

  .clear-button:hover {
    background: #d32f2f;
    transform: translateY(-2px);
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .history-item {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .history-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e0e0e0;
  }

  .history-mode {
    font-weight: 600;
    color: #667eea;
  }

  .history-time {
    font-size: 0.9rem;
    color: #666;
  }

  .history-message, .history-response {
    margin-bottom: 1rem;
  }

  .history-message h4, .history-response h4 {
    margin: 0 0 0.5rem 0;
    color: #555;
    font-size: 0.9rem;
    font-weight: 500;
  }

  .history-message p, .history-response p {
    margin: 0;
    line-height: 1.5;
  }

  .history-message p {
    color: #333;
    font-weight: 500;
  }

  .history-response p {
    color: #666;
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
    font-size: 1.5rem;
  }

  .empty-state p {
    margin: 0;
    line-height: 1.5;
    font-size: 1.1rem;
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
    
    .mode-buttons {
      grid-template-columns: 1fr;
    }

    .input-container {
      flex-direction: column;
      align-items: stretch;
    }

    .input-header {
      flex-direction: column;
      gap: 0.5rem;
      align-items: flex-start;
    }

    .history-header {
      flex-direction: column;
      gap: 1rem;
      align-items: stretch;
    }

    .history-item-header {
      flex-direction: column;
      gap: 0.5rem;
      align-items: flex-start;
    }
  }
</style>
