<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';
  import { onMount } from 'svelte';

  type Mode = 'base' | 'fine' | 'rag' | 'hybrid';
  
  interface SourceChunk {
    content: string;
    document_title: string;
    similarity_score: number;
    chunk_index: number;
    highlighted: boolean;
  }

  interface ChatMetrics {
    latency: number;
    tokens_input: number;
    tokens_output: number;
    sources_retrieved: number;
    response_length: number;
    timestamp: string;
  }

  interface ChatEntry {
    id: string;
    message: string;
    response: string;
    mode: Mode;
    timestamp: Date;
    sources: SourceChunk[];
    metrics: ChatMetrics;
    highlighted_response: string;
  }

  interface ChatResult {
    message: {
      content: string;
    };
    sources: Array<{
      relevant_chunks: string[];
      document_title?: string;
      similarity_score?: number;
      chunk_index?: number;
    }>;
    processing_time_ms?: number;
  }

  let message = '';
  let mode: Mode = 'hybrid';
  let response = '';
  let highlighted_response = '';
  let retrieved_sources: SourceChunk[] = [];
  let loading = false;
  let selectedTab: 'chat' | 'settings' | 'history' | 'metrics' = 'chat';
  let chatHistory: ChatEntry[] = [];
  
  // Settings
  let temperature = 0.7;
  let maxTokens = 150;
  let enableStreaming = true;
  let showSources = true;
  let highlightThreshold = 0.7;
  
  // Metrics
  let averageLatency = 0;
  let totalQueries = 0;
  let successRate = 100;
  let metricsHistory: ChatMetrics[] = [];

  async function send() {
    if (!message.trim()) return;
    
    loading = true;
    const startTime = performance.now();
    const currentMessage = message;
    const currentMode = mode;
    
    try {
      let result: ChatResult;
      
      // Different API calls based on mode
      switch (currentMode) {
        case 'base':
          result = await invoke<ChatResult>('chat_base_model', { 
            query: currentMessage,
            temperature,
            max_tokens: maxTokens
          });
          break;
        case 'fine':
          result = await invoke<ChatResult>('chat_fine_tuned', { 
            query: currentMessage,
            temperature,
            max_tokens: maxTokens
          });
          break;
        case 'rag':
          result = await invoke<ChatResult>('chat_with_documents', { 
            query: currentMessage 
          });
          break;
        case 'hybrid':
          result = await invoke<ChatResult>('chat_hybrid_mode', { 
            query: currentMessage,
            temperature,
            max_tokens: maxTokens,
            use_fine_tuned: true,
            use_rag: true
          });
          break;
        default:
          result = await invoke<ChatResult>('chat_with_documents', { 
            query: currentMessage 
          });
      }
      
      const endTime = performance.now();
      const latency = endTime - startTime;
      
      // Process response
      response = result.message.content;
      
      // Process sources
      retrieved_sources = result.sources?.map((source, index) => ({
        content: Array.isArray(source.relevant_chunks) ? source.relevant_chunks.join('\n') : source.relevant_chunks || '',
        document_title: source.document_title || `Source ${index + 1}`,
        similarity_score: source.similarity_score || 0.8,
        chunk_index: source.chunk_index || index,
        highlighted: false
      })) || [];
      
      // Highlight response with source context
      highlighted_response = highlightResponseWithSources(response, retrieved_sources);
      
      // Calculate metrics
      const metrics: ChatMetrics = {
        latency: Math.round(latency),
        tokens_input: estimateTokens(currentMessage),
        tokens_output: estimateTokens(response),
        sources_retrieved: retrieved_sources.length,
        response_length: response.length,
        timestamp: new Date().toISOString()
      };
      
      // Update global metrics
      updateGlobalMetrics(metrics);
      
      // Add to history
      const chatEntry: ChatEntry = {
        id: Date.now().toString(),
        message: currentMessage,
        response: response,
        mode: currentMode,
        timestamp: new Date(),
        sources: retrieved_sources,
        metrics: metrics,
        highlighted_response: highlighted_response
      };
      
      chatHistory = [chatEntry, ...chatHistory];
      
      // Clear input
      message = '';
      
    } catch (e) {
      response = `Error: ${e}`;
      highlighted_response = response;
      retrieved_sources = [];
      
      // Track error in metrics
      const errorMetrics: ChatMetrics = {
        latency: performance.now() - startTime,
        tokens_input: estimateTokens(currentMessage),
        tokens_output: 0,
        sources_retrieved: 0,
        response_length: 0,
        timestamp: new Date().toISOString()
      };
      updateGlobalMetrics(errorMetrics, true);
    }
    
    loading = false;
  }

  function highlightResponseWithSources(responseText: string, sources: SourceChunk[]): string {
    if (!showSources || sources.length === 0) return responseText;
    
    let highlighted = responseText;
    
    sources.forEach((source, index) => {
      if (source.similarity_score >= highlightThreshold) {
        // Find common phrases between source and response
        const sourceWords = source.content.toLowerCase().split(/\s+/);
        const responseWords = responseText.toLowerCase().split(/\s+/);
        
        // Simple keyword matching (can be improved with NLP)
        sourceWords.forEach(word => {
          if (word.length > 3 && responseWords.includes(word)) {
            const regex = new RegExp(`\\b${word}\\b`, 'gi');
            highlighted = highlighted.replace(regex, `<span class="highlighted-text" data-source="${index}" title="Source: ${source.document_title}">${word}</span>`);
            source.highlighted = true;
          }
        });
      }
    });
    
    return highlighted;
  }

  function estimateTokens(text: string): number {
    // Rough estimation: ~4 characters per token
    return Math.ceil(text.length / 4);
  }

  function updateGlobalMetrics(metrics: ChatMetrics, isError: boolean = false) {
    metricsHistory = [metrics, ...metricsHistory.slice(0, 99)]; // Keep last 100
    totalQueries++;
    
    if (!isError) {
      averageLatency = metricsHistory.reduce((sum, m) => sum + m.latency, 0) / metricsHistory.length;
      const successfulQueries = metricsHistory.filter(m => m.tokens_output > 0).length;
      successRate = Math.round((successfulQueries / totalQueries) * 100);
    }
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
    highlighted_response = '';
    retrieved_sources = [];
  }

  function clearMetrics() {
    metricsHistory = [];
    averageLatency = 0;
    totalQueries = 0;
    successRate = 100;
  }

  function formatTime(date: Date): string {
    return date.toLocaleTimeString();
  }

  function getModeIcon(mode: Mode): string {
    switch (mode) {
      case 'base': return '🤖';
      case 'fine': return '🎯';
      case 'rag': return '📚';
      case 'hybrid': return '🔄';
    }
  }

  function getModeLabel(mode: Mode): string {
    switch (mode) {
      case 'base': return 'Base Model';
      case 'fine': return 'Fine-tuned Model';
      case 'rag': return 'RAG Enhanced';
      case 'hybrid': return 'Hybrid (Fine-tuned + RAG)';
    }
  }

  function getModeDescription(mode: Mode): string {
    switch (mode) {
      case 'base': return 'Uses the original pre-trained model without any enhancements';
      case 'fine': return 'Uses your custom fine-tuned model for domain-specific responses';
      case 'rag': return 'Retrieves relevant documents and augments responses with context';
      case 'hybrid': return 'Combines fine-tuned model with RAG for best of both worlds';
    }
  }

  function highlightSource(sourceIndex: number) {
    if (retrieved_sources[sourceIndex]) {
      retrieved_sources[sourceIndex].highlighted = !retrieved_sources[sourceIndex].highlighted;
      retrieved_sources = [...retrieved_sources]; // Trigger reactivity
    }
  }

  function exportChat() {
    const exportData = {
      chat_history: chatHistory,
      metrics_summary: {
        total_queries: totalQueries,
        average_latency: averageLatency,
        success_rate: successRate
      },
      settings: {
        mode,
        temperature,
        maxTokens,
        enableStreaming,
        showSources
      },
      export_timestamp: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rag_chat_export_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
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
          class="tab {selectedTab === 'metrics' ? 'active' : ''}"
          on:click={() => selectedTab = 'metrics'}
        >
          📊 Metrics
        </button>
        <button 
          class="tab {selectedTab === 'history' ? 'active' : ''}"
          on:click={() => selectedTab = 'history'}
        >
          📝 History ({chatHistory.length})
        </button>
      </nav>
    </header>

    <!-- Main content -->
    <div class="main-content">
      <!-- Chat Tab -->
      {#if selectedTab === 'chat'}
        <div class="chat-container">
          <!-- Mode Selection -->
          <div class="mode-selection">
            <h3>🎯 Model Mode</h3>
            <div class="mode-grid">
              {#each (['base', 'fine', 'rag', 'hybrid'] as Mode[]) as modeOption}
                <button 
                  class="mode-card {mode === modeOption ? 'active' : ''}"
                  on:click={() => mode = modeOption}
                >
                  <div class="mode-icon">{getModeIcon(modeOption)}</div>
                  <div class="mode-info">
                    <div class="mode-name">{getModeLabel(modeOption)}</div>
                    <div class="mode-desc">{getModeDescription(modeOption)}</div>
                  </div>
                </button>
              {/each}
            </div>
          </div>

          <!-- Chat Interface -->
          <div class="chat-interface">
            <div class="chat-input-section">
              <div class="input-group">
                <textarea
                  bind:value={message}
                  on:keydown={handleKeyDown}
                  placeholder="Ask me anything..."
                  class="chat-input"
                  rows="3"
                ></textarea>
                <button 
                  class="send-button {loading ? 'loading' : ''}"
                  on:click={send}
                  disabled={loading || !message.trim()}
                >
                  {#if loading}
                    🔄 Processing...
                  {:else}
                    🚀 Send
                  {/if}
                </button>
              </div>
            </div>

            <!-- Response Section -->
            {#if response}
              <div class="response-section">
                <div class="response-header">
                  <h3>💬 Response</h3>
                  <div class="response-meta">
                    <span class="mode-badge">{getModeIcon(mode)} {getModeLabel(mode)}</span>
                    {#if chatHistory.length > 0}
                      <span class="latency-badge">⚡ {chatHistory[0].metrics.latency}ms</span>
                    {/if}
                  </div>
                </div>
                
                <div class="response-content">
                  {#if showSources && highlighted_response}
                    <div class="highlighted-response">
                      {@html highlighted_response}
                    </div>
                  {:else}
                    <div class="plain-response">{response}</div>
                  {/if}
                </div>
              </div>
            {/if}

            <!-- Sources Section -->
            {#if retrieved_sources.length > 0}
              <div class="sources-section">
                <div class="sources-header">
                  <h3>📚 Retrieved Sources</h3>
                  <span class="sources-count">{retrieved_sources.length} sources found</span>
                </div>
                
                <div class="sources-grid">
                  {#each retrieved_sources as source, index}
                    <div 
                      class="source-card {source.highlighted ? 'highlighted' : ''}"
                      on:click={() => highlightSource(index)}
                    >
                      <div class="source-header">
                        <span class="source-title">{source.document_title}</span>
                        <div class="source-meta">
                          <span class="similarity-score">
                            🎯 {(source.similarity_score * 100).toFixed(1)}%
                          </span>
                          <span class="chunk-index">📄 Chunk {source.chunk_index + 1}</span>
                        </div>
                      </div>
                      <div class="source-content">
                        {source.content.substring(0, 200)}...
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        </div>

      <!-- Settings Tab -->
      {:else if selectedTab === 'settings'}
        <div class="settings-container">
          <h2>⚙️ Playground Settings</h2>
          
          <div class="settings-grid">
            <!-- Generation Parameters -->
            <div class="setting-group">
              <h3>🎛️ Generation Parameters</h3>
              
              <div class="setting-item">
                <label>🌡️ Temperature: {temperature}</label>
                <input 
                  type="range" 
                  bind:value={temperature}
                  min="0" max="2" step="0.1"
                  class="slider"
                />
                <small>Controls randomness. Lower = more focused, Higher = more creative</small>
              </div>

              <div class="setting-item">
                <label>📏 Max Tokens: {maxTokens}</label>
                <input 
                  type="range" 
                  bind:value={maxTokens}
                  min="50" max="1000" step="10"
                  class="slider"
                />
                <small>Maximum length of generated response</small>
              </div>
            </div>

            <!-- Display Options -->
            <div class="setting-group">
              <h3>🎨 Display Options</h3>
              
              <div class="setting-item">
                <label class="checkbox-label">
                  <input type="checkbox" bind:checked={showSources} />
                  📚 Show Retrieved Sources
                </label>
                <small>Display source documents used for RAG responses</small>
              </div>

              <div class="setting-item">
                <label class="checkbox-label">
                  <input type="checkbox" bind:checked={enableStreaming} />
                  ⚡ Enable Streaming
                </label>
                <small>Stream responses as they're generated (when supported)</small>
              </div>

              <div class="setting-item">
                <label>🎯 Highlight Threshold: {highlightThreshold}</label>
                <input 
                  type="range" 
                  bind:value={highlightThreshold}
                  min="0.1" max="1" step="0.1"
                  class="slider"
                />
                <small>Minimum similarity score to highlight source matches</small>
              </div>
            </div>

            <!-- Model Information -->
            <div class="setting-group">
              <h3>🤖 Current Model Info</h3>
              <div class="model-info">
                <div class="info-item">
                  <span class="info-label">Mode:</span>
                  <span class="info-value">{getModeIcon(mode)} {getModeLabel(mode)}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Description:</span>
                  <span class="info-value">{getModeDescription(mode)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      <!-- Metrics Tab -->
      {:else if selectedTab === 'metrics'}
        <div class="metrics-container">
          <div class="metrics-header">
            <h2>📊 Performance Metrics</h2>
            <div class="metrics-actions">
              <button class="secondary-button" on:click={clearMetrics}>
                🗑️ Clear Metrics
              </button>
              <button class="primary-button" on:click={exportChat}>
                💾 Export Data
              </button>
            </div>
          </div>
          
          <!-- Key Metrics -->
          <div class="metrics-overview">
            <div class="metric-card">
              <div class="metric-icon">⚡</div>
              <div class="metric-info">
                <div class="metric-value">{averageLatency.toFixed(0)}ms</div>
                <div class="metric-label">Avg Latency</div>
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-icon">💬</div>
              <div class="metric-info">
                <div class="metric-value">{totalQueries}</div>
                <div class="metric-label">Total Queries</div>
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-icon">✅</div>
              <div class="metric-info">
                <div class="metric-value">{successRate}%</div>
                <div class="metric-label">Success Rate</div>
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-icon">📚</div>
              <div class="metric-info">
                <div class="metric-value">
                  {metricsHistory.length > 0 ? (metricsHistory.reduce((sum, m) => sum + m.sources_retrieved, 0) / metricsHistory.length).toFixed(1) : '0'}
                </div>
                <div class="metric-label">Avg Sources</div>
              </div>
            </div>
          </div>

          <!-- Detailed Metrics -->
          {#if metricsHistory.length > 0}
            <div class="metrics-details">
              <h3>📈 Recent Performance</h3>
              <div class="metrics-list">
                {#each metricsHistory.slice(0, 10) as metric, index}
                  <div class="metric-row">
                    <div class="metric-time">
                      {new Date(metric.timestamp).toLocaleTimeString()}
                    </div>
                    <div class="metric-latency">⚡ {metric.latency}ms</div>
                    <div class="metric-tokens">🔤 {metric.tokens_input}→{metric.tokens_output}</div>
                    <div class="metric-sources">📚 {metric.sources_retrieved}</div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </div>

      <!-- History Tab -->
      {:else if selectedTab === 'history'}
        <div class="history-container">
          <div class="history-header">
            <h2>📝 Chat History</h2>
            <div class="history-actions">
              <button class="secondary-button" on:click={clearHistory}>
                🗑️ Clear History
              </button>
              <button class="primary-button" on:click={exportChat}>
                💾 Export Chat
              </button>
            </div>
          </div>
          
          {#if chatHistory.length > 0}
            <div class="history-list">
              {#each chatHistory as chat}
                <div class="history-item">
                  <div class="history-meta">
                    <span class="history-time">{formatTime(chat.timestamp)}</span>
                    <span class="history-mode">{getModeIcon(chat.mode)} {getModeLabel(chat.mode)}</span>
                    <span class="history-latency">⚡ {chat.metrics.latency}ms</span>
                  </div>
                  
                  <div class="history-content">
                    <div class="history-query">
                      <strong>Q:</strong> {chat.message}
                    </div>
                    <div class="history-response">
                      <strong>A:</strong> {chat.response.substring(0, 200)}...
                    </div>
                    
                    {#if chat.sources.length > 0}
                      <div class="history-sources">
                        <strong>Sources ({chat.sources.length}):</strong>
                        {chat.sources.map(s => s.document_title).join(', ')}
                      </div>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="empty-history">
              <div class="empty-icon">📝</div>
              <h3>No chat history yet</h3>
              <p>Start a conversation to see your chat history here</p>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</main>

<style>
  .app-container {
    max-width: 1400px;
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

  /* Chat Interface */
  .chat-container {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .mode-selection {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .mode-selection h3 {
    margin: 0 0 1.5rem 0;
    color: #333;
    font-size: 1.3rem;
  }

  .mode-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
  }

  .mode-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    background: white;
  }

  .mode-card:hover {
    border-color: #667eea;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
  }

  .mode-card.active {
    border-color: #667eea;
    background: linear-gradient(135deg, #f8f9ff, #f0f4ff);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .mode-icon {
    font-size: 2rem;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  }

  .mode-info {
    flex: 1;
  }

  .mode-name {
    font-weight: 600;
    color: #333;
    margin-bottom: 0.25rem;
  }

  .mode-desc {
    color: #6c757d;
    font-size: 0.9rem;
    line-height: 1.4;
  }

  .chat-interface {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .chat-input-section {
    border-bottom: 2px solid #f3f4f6;
    padding-bottom: 2rem;
  }

  .input-group {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
  }

  .chat-input {
    flex: 1;
    padding: 1rem;
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    font-size: 1rem;
    resize: vertical;
    min-height: 80px;
    transition: all 0.3s ease;
    font-family: inherit;
  }

  .chat-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .send-button {
    padding: 1rem 2rem;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    white-space: nowrap;
  }

  .send-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
  }

  .send-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .send-button.loading {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
  }

  .response-section {
    border: 2px solid #e5f3ff;
    border-radius: 12px;
    padding: 1.5rem;
    background: linear-gradient(135deg, #f8fdff, #f0f9ff);
  }

  .response-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .response-header h3 {
    margin: 0;
    color: #1e40af;
  }

  .response-meta {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .mode-badge, .latency-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .mode-badge {
    background: #dbeafe;
    color: #1e40af;
  }

  .latency-badge {
    background: #d1fae5;
    color: #065f46;
  }

  .response-content {
    line-height: 1.6;
    color: #374151;
  }

  .highlighted-response {
    font-size: 1.1rem;
  }

  .highlighted-response :global(.highlighted-text) {
    background: linear-gradient(135deg, #fef3c7, #fde68a);
    padding: 0.1rem 0.2rem;
    border-radius: 4px;
    cursor: help;
    border-bottom: 2px solid #f59e0b;
  }

  .plain-response {
    font-size: 1.1rem;
  }

  .sources-section {
    border: 2px solid #e5f3e5;
    border-radius: 12px;
    padding: 1.5rem;
    background: linear-gradient(135deg, #f8fff8, #f0fdf0);
  }

  .sources-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .sources-header h3 {
    margin: 0;
    color: #166534;
  }

  .sources-count {
    color: #059669;
    font-weight: 600;
    font-size: 0.9rem;
  }

  .sources-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
  }

  .source-card {
    padding: 1rem;
    border: 2px solid #d1fae5;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    background: white;
  }

  .source-card:hover {
    border-color: #10b981;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
  }

  .source-card.highlighted {
    border-color: #f59e0b;
    background: linear-gradient(135deg, #fef3c7, #fde68a);
  }

  .source-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.5rem;
  }

  .source-title {
    font-weight: 600;
    color: #166534;
    font-size: 0.9rem;
  }

  .source-meta {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    align-items: flex-end;
  }

  .similarity-score, .chunk-index {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.1rem 0.4rem;
    border-radius: 10px;
  }

  .similarity-score {
    background: #dbeafe;
    color: #1e40af;
  }

  .chunk-index {
    background: #e5e7eb;
    color: #374151;
  }

  .source-content {
    color: #4b5563;
    font-size: 0.85rem;
    line-height: 1.5;
  }

  /* Settings Styles */
  .settings-container {
    max-width: 1000px;
    margin: 0 auto;
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .settings-container h2 {
    margin: 0 0 2rem 0;
    color: #333;
    font-size: 1.8rem;
    border-bottom: 2px solid #667eea;
    padding-bottom: 0.5rem;
  }

  .settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
  }

  .setting-group {
    border: 2px solid #f3f4f6;
    border-radius: 12px;
    padding: 1.5rem;
    background: #f8f9fa;
  }

  .setting-group h3 {
    margin: 0 0 1rem 0;
    color: #495057;
    font-size: 1.2rem;
  }

  .setting-item {
    margin-bottom: 1.5rem;
  }

  .setting-item:last-child {
    margin-bottom: 0;
  }

  .setting-item label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: #495057;
  }

  .slider {
    width: 100%;
    margin: 0.5rem 0;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
  }

  .setting-item small {
    color: #6c757d;
    font-size: 0.8rem;
    display: block;
    margin-top: 0.25rem;
  }

  .model-info {
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
  }

  .info-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #f3f4f6;
  }

  .info-item:last-child {
    margin-bottom: 0;
    border-bottom: none;
  }

  .info-label {
    font-weight: 600;
    color: #495057;
  }

  .info-value {
    color: #6c757d;
    text-align: right;
    max-width: 60%;
  }

  /* Metrics Styles */
  .metrics-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .metrics-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    margin-bottom: 2rem;
  }

  .metrics-header h2 {
    margin: 0;
    color: #333;
    font-size: 1.8rem;
  }

  .metrics-actions {
    display: flex;
    gap: 1rem;
  }

  .primary-button, .secondary-button {
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.3s ease;
    border: none;
  }

  .primary-button {
    background: #667eea;
    color: white;
  }

  .primary-button:hover {
    background: #5a67d8;
    transform: translateY(-2px);
  }

  .secondary-button {
    background: #e5e7eb;
    color: #374151;
  }

  .secondary-button:hover {
    background: #d1d5db;
    transform: translateY(-2px);
  }

  .metrics-overview {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .metric-card {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .metric-icon {
    font-size: 2.5rem;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  }

  .metric-info {
    flex: 1;
  }

  .metric-value {
    font-size: 2rem;
    font-weight: 600;
    color: #333;
    margin-bottom: 0.25rem;
  }

  .metric-label {
    color: #6c757d;
    font-size: 0.9rem;
    font-weight: 500;
  }

  .metrics-details {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .metrics-details h3 {
    margin: 0 0 1rem 0;
    color: #333;
  }

  .metrics-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .metric-row {
    display: grid;
    grid-template-columns: auto 1fr 1fr 1fr;
    gap: 1rem;
    padding: 0.75rem;
    background: #f8f9fa;
    border-radius: 6px;
    font-family: monospace;
    font-size: 0.9rem;
  }

  .metric-time {
    color: #6c757d;
    font-weight: 500;
  }

  .metric-latency {
    color: #059669;
  }

  .metric-tokens {
    color: #dc2626;
  }

  .metric-sources {
    color: #2563eb;
  }

  /* History Styles */
  .history-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    margin-bottom: 2rem;
  }

  .history-header h2 {
    margin: 0;
    color: #333;
    font-size: 1.8rem;
  }

  .history-actions {
    display: flex;
    gap: 1rem;
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .history-item {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .history-meta {
    display: flex;
    gap: 1rem;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #f3f4f6;
  }

  .history-time {
    color: #6c757d;
    font-weight: 500;
    font-size: 0.9rem;
  }

  .history-mode {
    background: #e5f3ff;
    color: #1e40af;
    padding: 0.25rem 0.75rem;
    border-radius: 15px;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .history-latency {
    background: #d1fae5;
    color: #065f46;
    padding: 0.25rem 0.75rem;
    border-radius: 15px;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .history-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .history-query {
    color: #374151;
    line-height: 1.5;
  }

  .history-response {
    color: #4b5563;
    line-height: 1.5;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 8px;
    border-left: 4px solid #667eea;
  }

  .history-sources {
    color: #059669;
    font-size: 0.9rem;
    background: #f0fdf4;
    padding: 0.75rem;
    border-radius: 6px;
    border-left: 4px solid #10b981;
  }

  .empty-history {
    text-align: center;
    padding: 4rem 2rem;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    color: #6c757d;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .empty-history h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.5rem;
  }

  .empty-history p {
    margin: 0;
    line-height: 1.5;
    font-size: 1.1rem;
  }

  /* Dark mode adjustments */
  :global(.dark) .app-container {
    background: #1a202c;
  }

  :global(.dark) .mode-selection,
  :global(.dark) .chat-interface,
  :global(.dark) .settings-container,
  :global(.dark) .metrics-header,
  :global(.dark) .metrics-details,
  :global(.dark) .history-header,
  :global(.dark) .history-item,
  :global(.dark) .empty-history {
    background: #2d3748;
    color: #f7fafc;
  }

  :global(.dark) .chat-input {
    background: #4a5568;
    border-color: #718096;
    color: #f7fafc;
  }

  :global(.dark) .mode-card,
  :global(.dark) .source-card {
    background: #4a5568;
    border-color: #718096;
    color: #f7fafc;
  }

  :global(.dark) .model-info {
    background: #4a5568;
    border-color: #718096;
  }

  :global(.dark) .setting-group {
    background: #4a5568;
    border-color: #718096;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .mode-grid {
      grid-template-columns: 1fr;
    }

    .input-group {
      flex-direction: column;
      align-items: stretch;
    }

    .response-header,
    .sources-header,
    .metrics-header,
    .history-header {
      flex-direction: column;
      gap: 1rem;
      text-align: center;
    }

    .metrics-overview {
      grid-template-columns: repeat(2, 1fr);
    }

    .metric-row {
      grid-template-columns: 1fr;
      text-align: center;
    }

    .settings-grid {
      grid-template-columns: 1fr;
    }

    .tabs {
      flex-direction: column;
      gap: 0.5rem;
    }
  }
</style>
