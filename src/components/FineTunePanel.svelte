<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';
  import { listen } from '@tauri-apps/api/event';
  import { onDestroy } from 'svelte';

  let datasetPath = '';
  let modelName = '';
  let logs: string[] = [];
  let running = false;
  let unlisten: (() => void) | undefined;
  let selectedTab: 'config' | 'logs' | 'models' = 'config';

  async function startFineTune() {
    running = true;
    logs = [];
    selectedTab = 'logs'; // Switch to logs tab when starting
    
    unlisten = await listen<string>('fine_tune_log', (event) => {
      logs = [...logs, event.payload];
    });

    try {
      await invoke('run_fine_tune', { config: JSON.stringify({ datasetPath, modelName }) });
    } catch (e) {
      logs = [...logs, `Error: ${e}`];
    }
    running = false;
    if (unlisten) unlisten();
  }

  function handleFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    datasetPath = (target.files?.[0] as any)?.path ?? '';
  }

  onDestroy(() => {
    if (unlisten) unlisten();
  });
</script>

<main>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <h1 class="app-title">🎯 Fine-tune</h1>
        <p class="app-subtitle">Train and customize your language models</p>
      </div>
      
      <!-- Navigation tabs -->
      <nav class="tabs">
        <button 
          class="tab {selectedTab === 'config' ? 'active' : ''}"
          on:click={() => selectedTab = 'config'}
        >
          ⚙️ Configuration
        </button>
        <button 
          class="tab {selectedTab === 'models' ? 'active' : ''}"
          on:click={() => selectedTab = 'models'}
        >
          🤖 Models
        </button>
        <button 
          class="tab {selectedTab === 'logs' ? 'active' : ''}"
          on:click={() => selectedTab = 'logs'}
        >
          📋 Training Logs
        </button>
      </nav>
    </header>

    <!-- Main content -->
    <div class="main-content">
      <!-- Configuration Tab -->
      {#if selectedTab === 'config'}
        <div class="config-container">
          <div class="config-header">
            <h2>⚙️ Fine-tuning Configuration</h2>
            <p>Configure your model training parameters</p>
          </div>
          
          <div class="config-section">
            <h3>📁 Dataset Configuration</h3>
            <div class="form-group">
              <label for="dataset-file">Training Dataset:</label>
              <input 
                id="dataset-file"
                type="file" 
                on:change={handleFileChange} 
                class="file-input"
                accept=".jsonl,.json,.txt,.csv"
              />
              {#if datasetPath}
                <div class="file-info">
                  <span class="file-icon">📄</span>
                  <span class="file-path">{datasetPath}</span>
                </div>
              {/if}
            </div>
          </div>

          <div class="config-section">
            <h3>🎯 Model Configuration</h3>
            <div class="form-group">
              <label for="model-name">Model Name:</label>
              <input 
                id="model-name"
                type="text" 
                placeholder="my-fine-tuned-model" 
                bind:value={modelName} 
                class="text-input"
              />
              <small>This will be the name of your trained model</small>
            </div>
          </div>

          <div class="config-actions">
            <button 
              class="primary-button {running ? 'loading' : ''}" 
              on:click={startFineTune} 
              disabled={running || !datasetPath || !modelName}
            >
              {running ? '🔄 Training...' : '🚀 Start Fine-tuning'}
            </button>
          </div>
        </div>

      <!-- Models Tab -->
      {:else if selectedTab === 'models'}
        <div class="models-container">
          <div class="config-header">
            <h2>🤖 Model Management</h2>
            <p>Manage your fine-tuned models</p>
          </div>
          
          <div class="empty-state">
            <div class="empty-icon">🤖</div>
            <h3>No models yet</h3>
            <p>Start by fine-tuning your first model in the Configuration tab</p>
          </div>
        </div>

      <!-- Logs Tab -->
      {:else if selectedTab === 'logs'}
        <div class="logs-container">
          <div class="config-header">
            <h2>📋 Training Logs</h2>
            <p>Monitor your training progress in real-time</p>
          </div>
          
          <div class="logs-section">
            <div class="logs-header">
              <h3>Training Output</h3>
              {#if running}
                <span class="status-indicator running">🔄 Training in progress...</span>
              {:else if logs.length > 0}
                <span class="status-indicator completed">✅ Training completed</span>
              {:else}
                <span class="status-indicator idle">⏸️ No training session</span>
              {/if}
            </div>
            
            <div class="logs-content">
              {#if logs.length > 0}
                <pre class="logs-output">{logs.join('\n')}</pre>
              {:else}
                <div class="empty-logs">
                  <div class="empty-icon">📝</div>
                  <p>Training logs will appear here when you start fine-tuning</p>
                </div>
              {/if}
            </div>
          </div>
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

  .config-container, .models-container, .logs-container {
    max-width: 800px;
    margin: 0 auto;
  }

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

  .form-group {
    margin-bottom: 1rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #333;
  }

  .file-input, .text-input {
    width: 100%;
    padding: 0.75rem;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.3s ease;
  }

  .file-input:focus, .text-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
    padding: 0.5rem;
    background: #f8f9fa;
    border-radius: 6px;
  }

  .file-icon {
    font-size: 1.2rem;
  }

  .file-path {
    font-family: monospace;
    font-size: 0.9rem;
    color: #666;
  }

  .form-group small {
    display: block;
    margin-top: 0.25rem;
    color: #666;
    font-size: 0.9rem;
  }

  .config-actions {
    text-align: center;
    margin-top: 2rem;
  }

  .primary-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 1rem 2rem;
    border-radius: 25px;
    cursor: pointer;
    font-size: 1.1rem;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .primary-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
  }

  .primary-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .primary-button.loading {
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  .logs-section {
    background: white;
    border-radius: 12px;
    border: 1px solid #e0e0e0;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .logs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    background: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
  }

  .logs-header h3 {
    margin: 0;
    color: #333;
  }

  .status-indicator {
    font-size: 0.9rem;
    font-weight: 500;
    padding: 0.25rem 0.75rem;
    border-radius: 15px;
  }

  .status-indicator.running {
    background: #e3f2fd;
    color: #1976d2;
  }

  .status-indicator.completed {
    background: #e8f5e8;
    color: #388e3c;
  }

  .status-indicator.idle {
    background: #f5f5f5;
    color: #666;
  }

  .logs-content {
    min-height: 400px;
  }

  .logs-output {
    padding: 1.5rem;
    margin: 0;
    background: #1e1e1e;
    color: #f0f0f0;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9rem;
    line-height: 1.5;
    overflow-x: auto;
    white-space: pre-wrap;
    min-height: 400px;
  }

  .empty-logs {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 400px;
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
    
    .config-section {
      padding: 1rem;
    }

    .logs-header {
      flex-direction: column;
      gap: 1rem;
      align-items: flex-start;
    }
  }
</style>
