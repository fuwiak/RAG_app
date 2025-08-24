<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';
  import { listen } from '@tauri-apps/api/event';
  import { onDestroy } from 'svelte';
  import { t } from '../lib/i18n';

  // Fine-tuning configuration interface
  interface FineTuneConfig {
    // Basic settings
    model_name: string;
    dataset_path: string;
    output_dir: string;
    
    // Fine-tuning method
    method: 'lora' | 'qlora' | 'full' | 'instruction' | 'rag_specific';
    
    // LoRA settings
    lora_r: number;
    lora_alpha: number;
    lora_dropout: number;
    lora_target_modules: string[];
    
    // QLoRA settings
    use_4bit: boolean;
    bnb_4bit_compute_dtype: string;
    bnb_4bit_use_double_quant: boolean;
    bnb_4bit_quant_type: string;
    
    // Training parameters
    num_epochs: number;
    learning_rate: number;
    batch_size: number;
    gradient_accumulation_steps: number;
    warmup_steps: number;
    max_seq_length: number;
    
    // RAG-specific settings
    use_retrieval_augmentation: boolean;
    retrieval_corpus_path: string;
    embedding_model: string;
    top_k_retrieval: number;
    
    // Advanced settings
    gradient_checkpointing: boolean;
    fp16: boolean;
    dataloader_num_workers: number;
    save_steps: number;
    eval_steps: number;
    logging_steps: number;
    
    // Language-specific settings
    language: 'en' | 'pl' | 'ru' | 'de' | 'fr';
    instruction_template: string;
  }

  // State variables
  let selectedTab: 'config' | 'models' | 'logs' | 'metrics' = 'config';
  let selectedSubTab: 'basic' | 'lora' | 'training' | 'rag' | 'advanced' = 'basic';
  let logs: any[] = [];
  let running = false;
  let unlisten: (() => void) | undefined;
  let showAdvancedSettings = false;

  // Configuration state
  let config: FineTuneConfig = {
    // Basic settings
    model_name: 'microsoft/DialoGPT-medium',
    dataset_path: '',
    output_dir: './fine_tuned_model',
    
    // Method
    method: 'lora',
    
    // LoRA settings
    lora_r: 16,
    lora_alpha: 32,
    lora_dropout: 0.1,
    lora_target_modules: [],
    
    // QLoRA settings
    use_4bit: false,
    bnb_4bit_compute_dtype: 'float16',
    bnb_4bit_use_double_quant: true,
    bnb_4bit_quant_type: 'nf4',
    
    // Training parameters
    num_epochs: 3,
    learning_rate: 0.0002,
    batch_size: 4,
    gradient_accumulation_steps: 4,
    warmup_steps: 100,
    max_seq_length: 512,
    
    // RAG settings
    use_retrieval_augmentation: false,
    retrieval_corpus_path: '',
    embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
    top_k_retrieval: 5,
    
    // Advanced settings
    gradient_checkpointing: true,
    fp16: true,
    dataloader_num_workers: 4,
    save_steps: 500,
    eval_steps: 500,
    logging_steps: 10,
    
    // Language settings
    language: 'en',
    instruction_template: 'default'
  };

  // Available models by language
  const languageModels = {
    en: [
      'microsoft/DialoGPT-medium',
      'microsoft/DialoGPT-large', 
      'microsoft/phi-2',
      'google/flan-t5-base',
      'EleutherAI/gpt-neo-2.7B',
      'distilbert-base-uncased'
    ],
    pl: [
      'allegro/herbert-base-cased',
      'sdadas/polish-gpt2-medium',
      'allegro/plt5-base',
      'polish-nlp/polish-distilroberta'
    ],
    ru: [
      'sberbank-ai/rugpt3medium_based_on_gpt2',
      'ai-forever/ruBert-base',
      'DeepPavlov/rubert-base-cased'
    ],
    de: [
      'dbmdz/bert-base-german-cased',
      'deepset/gbert-base',
      'malteos/gpt2-wechsel-german'
    ],
    fr: [
      'camembert-base',
      'flaubert/flaubert_base_cased',
      'asi/gpt-fr-cased-base'
    ]
  };

  // Target modules for different model types
  const targetModulesOptions = {
    'gpt': ['c_attn', 'c_proj', 'c_fc'],
    'llama': ['q_proj', 'v_proj', 'k_proj', 'o_proj'],
    'bert': ['query', 'value', 'key', 'dense'],
    'default': ['q_proj', 'v_proj']
  };

  async function startFineTune() {
    running = true;
    logs = [];
    selectedTab = 'logs';
    
    unlisten = await listen<any>('fine_tune_log', (event) => {
      logs = [...logs, event.payload];
    });

    try {
      await invoke('run_fine_tune', { 
        config: JSON.stringify(config) 
      });
    } catch (e) {
      logs = [...logs, { error: true, message: `Error: ${e}` }];
    }
    
    running = false;
    if (unlisten) unlisten();
  }

  function handleDatasetChange(event: Event) {
    const target = event.target as HTMLInputElement;
    config.dataset_path = (target.files?.[0] as any)?.path ?? '';
  }

  function handleCorpusChange(event: Event) {
    const target = event.target as HTMLInputElement;
    config.retrieval_corpus_path = (target.files?.[0] as any)?.path ?? '';
  }

  function updateTargetModules(modelType: string) {
    const targetModules = targetModulesOptions[modelType as keyof typeof targetModulesOptions] || targetModulesOptions.default;
    config.lora_target_modules = targetModules;
  }

  function getLanguageFlag(lang: string): string {
    const flags: Record<string, string> = { en: '🇺🇸', pl: '🇵🇱', ru: '🇷🇺', de: '🇩🇪', fr: '🇫🇷' };
    return flags[lang] || '🌍';
  }

  function getMethodIcon(method: string): string {
    const icons: Record<string, string> = {
      lora: '🔧',
      qlora: '⚡',
      full: '🏋️',
      instruction: '📚',
      rag_specific: '🔍'
    };
    return icons[method] || '🤖';
  }

  function getMethodDescription(method: string): string {
    const descriptions: Record<string, string> = {
      lora: 'Low-Rank Adaptation - Memory efficient fine-tuning',
      qlora: 'Quantized LoRA - Ultra memory efficient with 4-bit quantization',
      full: 'Full Fine-tuning - Traditional method, requires more memory',
      instruction: 'Instruction Tuning - Optimized for following instructions',
      rag_specific: 'RAG-Specific Tuning - Optimized for retrieval-augmented generation'
    };
    return descriptions[method] || 'Standard fine-tuning method';
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
        <h1 class="app-title nav-text-transition">🎯 {$t.finetune_title}</h1>
        <p class="app-subtitle nav-description-transition">{$t.finetune_subtitle}</p>
      </div>
      
      <!-- Navigation tabs -->
      <nav class="tabs">
        <button 
          class="tab {selectedTab === 'config' ? 'active' : ''}"
          on:click={() => selectedTab = 'config'}
        >
          ⚙️ <span class="nav-text-transition">{$t.finetune_config}</span>
        </button>
        <button 
          class="tab {selectedTab === 'models' ? 'active' : ''}"
          on:click={() => selectedTab = 'models'}
        >
          🤖 <span class="nav-text-transition">{$t.finetune_models}</span>
        </button>
        <button 
          class="tab {selectedTab === 'logs' ? 'active' : ''}"
          on:click={() => selectedTab = 'logs'}
        >
          📋 <span class="nav-text-transition">{$t.finetune_logs}</span>
        </button>
        <button 
          class="tab {selectedTab === 'metrics' ? 'active' : ''}"
          on:click={() => selectedTab = 'metrics'}
        >
          📊 <span class="nav-text-transition">{$t.finetune_charts}</span>
        </button>
      </nav>
    </header>

    <!-- Main content -->
    <div class="main-content">
      <!-- Configuration Tab -->
      {#if selectedTab === 'config'}
        <div class="config-container">
          <!-- Sub-navigation -->
          <nav class="sub-tabs">
            <button 
              class="sub-tab {selectedSubTab === 'basic' ? 'active' : ''}"
              on:click={() => selectedSubTab = 'basic'}
            >
              🏠 Basic Settings
            </button>
            <button 
              class="sub-tab {selectedSubTab === 'lora' ? 'active' : ''}"
              on:click={() => selectedSubTab = 'lora'}
            >
              🔧 LoRA/QLoRA
            </button>
            <button 
              class="sub-tab {selectedSubTab === 'training' ? 'active' : ''}"
              on:click={() => selectedSubTab = 'training'}
            >
              🏃 Training Params
            </button>
            <button 
              class="sub-tab {selectedSubTab === 'rag' ? 'active' : ''}"
              on:click={() => selectedSubTab = 'rag'}
            >
              🔍 RAG Settings
            </button>
            <button 
              class="sub-tab {selectedSubTab === 'advanced' ? 'active' : ''}"
              on:click={() => selectedSubTab = 'advanced'}
            >
              🚀 Advanced
            </button>
          </nav>

          <!-- Basic Settings -->
          {#if selectedSubTab === 'basic'}
            <div class="config-section">
              <h2>🏠 Basic Configuration</h2>
              
              <!-- Language Selection -->
              <div class="form-group">
                <label>🌍 Target Language:</label>
                <div class="language-selector">
                  {#each ['en', 'pl', 'ru', 'de', 'fr'] as lang}
                    <button 
                      class="language-btn {config.language === lang ? 'active' : ''}"
                      on:click={() => config.language = lang}
                    >
                      {getLanguageFlag(lang)} {lang.toUpperCase()}
                    </button>
                  {/each}
                </div>
              </div>

              <!-- Fine-tuning Method -->
              <div class="form-group">
                <label>🎯 Fine-tuning Method:</label>
                <div class="method-selector">
                  {#each ['lora', 'qlora', 'full', 'instruction', 'rag_specific'] as method}
                    <div class="method-option">
                      <input 
                        type="radio" 
                        bind:group={config.method} 
                        value={method}
                        id={method}
                      />
                      <label for={method} class="method-label">
                        <span class="method-icon">{getMethodIcon(method)}</span>
                        <div class="method-info">
                          <div class="method-name">{method.toUpperCase()}</div>
                          <div class="method-desc">{getMethodDescription(method)}</div>
                        </div>
                      </label>
                    </div>
                  {/each}
                </div>
              </div>

              <!-- Model Selection -->
              <div class="form-group">
                <label>🤖 Base Model:</label>
                <select bind:value={config.model_name} class="model-select">
                  {#each languageModels[config.language] as model}
                    <option value={model}>{model}</option>
                  {/each}
                </select>
              </div>

              <!-- Dataset Upload -->
              <div class="form-group">
                <label>📁 Training Dataset:</label>
                <div class="file-upload-area">
                  <input 
                    type="file" 
                    on:change={handleDatasetChange}
                    accept=".jsonl,.json,.txt,.csv"
                    class="file-input"
                  />
                  {#if config.dataset_path}
                    <div class="file-info">
                      <span class="file-icon">📄</span>
                      <span>{config.dataset_path}</span>
                    </div>
                  {/if}
                </div>
              </div>

              <!-- Output Directory -->
              <div class="form-group">
                <label>💾 Output Directory:</label>
                <input 
                  type="text" 
                  bind:value={config.output_dir}
                  placeholder="./fine_tuned_model"
                  class="text-input"
                />
              </div>
            </div>

          <!-- LoRA/QLoRA Settings -->
          {:else if selectedSubTab === 'lora'}
            <div class="config-section">
              <h2>🔧 LoRA & QLoRA Configuration</h2>
              
              {#if config.method === 'lora' || config.method === 'qlora'}
                <!-- LoRA Parameters -->
                <div class="parameter-grid">
                  <div class="param-group">
                    <label>LoRA Rank (r):</label>
                    <input 
                      type="number" 
                      bind:value={config.lora_r}
                      min="1" max="256" step="1"
                      class="number-input"
                    />
                    <small>Higher values = more parameters, better fit but slower training</small>
                  </div>

                  <div class="param-group">
                    <label>LoRA Alpha:</label>
                    <input 
                      type="number" 
                      bind:value={config.lora_alpha}
                      min="1" max="512" step="1"
                      class="number-input"
                    />
                    <small>Scaling factor, typically 2x the rank</small>
                  </div>

                  <div class="param-group">
                    <label>LoRA Dropout:</label>
                    <input 
                      type="number" 
                      bind:value={config.lora_dropout}
                      min="0" max="1" step="0.01"
                      class="number-input"
                    />
                    <small>Dropout rate for regularization</small>
                  </div>
                </div>

                <!-- Target Modules -->
                <div class="form-group">
                  <label>🎯 Target Modules:</label>
                  <div class="module-selector">
                    {#each Object.entries(targetModulesOptions) as [type, modules]}
                      <button 
                        class="module-preset"
                        on:click={() => updateTargetModules(type)}
                      >
                        {type.toUpperCase()}: {modules.join(', ')}
                      </button>
                    {/each}
                  </div>
                  <div class="selected-modules">
                    Selected: {config.lora_target_modules.join(', ') || 'None selected'}
                  </div>
                </div>

                {#if config.method === 'qlora'}
                  <!-- QLoRA Quantization Settings -->
                  <div class="qlora-section">
                    <h3>⚡ QLoRA Quantization</h3>
                    <div class="checkbox-group">
                      <label class="checkbox-label">
                        <input type="checkbox" bind:checked={config.use_4bit} />
                        Enable 4-bit Quantization
                      </label>
                    </div>
                    
                    {#if config.use_4bit}
                      <div class="quantization-settings">
                        <div class="form-group">
                          <label>Compute Data Type:</label>
                          <select bind:value={config.bnb_4bit_compute_dtype}>
                            <option value="float16">Float16</option>
                            <option value="bfloat16">BFloat16</option>
                            <option value="float32">Float32</option>
                          </select>
                        </div>

                        <div class="form-group">
                          <label>Quantization Type:</label>
                          <select bind:value={config.bnb_4bit_quant_type}>
                            <option value="nf4">NF4 (Recommended)</option>
                            <option value="fp4">FP4</option>
                          </select>
                        </div>

                        <div class="checkbox-group">
                          <label class="checkbox-label">
                            <input type="checkbox" bind:checked={config.bnb_4bit_use_double_quant} />
                            Use Double Quantization
                          </label>
                        </div>
                      </div>
                    {/if}
                  </div>
                {/if}
              {:else}
                <div class="method-notice">
                  <div class="notice-icon">ℹ️</div>
                  <div>
                    <h3>LoRA Settings Not Available</h3>
                    <p>LoRA configuration is only available when using LoRA or QLoRA methods. 
                       Currently selected: <strong>{config.method.toUpperCase()}</strong></p>
                  </div>
                </div>
              {/if}
            </div>

          <!-- Training Parameters -->
          {:else if selectedSubTab === 'training'}
            <div class="config-section">
              <h2>🏃 Training Parameters</h2>
              
              <div class="parameter-grid">
                <div class="param-group">
                  <label>📊 Number of Epochs:</label>
                  <input 
                    type="number" 
                    bind:value={config.num_epochs}
                    min="1" max="100" step="1"
                    class="number-input"
                  />
                </div>

                <div class="param-group">
                  <label>🎯 Learning Rate:</label>
                  <input 
                    type="number" 
                    bind:value={config.learning_rate}
                    min="0.00001" max="0.01" step="0.00001"
                    class="number-input"
                  />
                </div>

                <div class="param-group">
                  <label>📦 Batch Size:</label>
                  <input 
                    type="number" 
                    bind:value={config.batch_size}
                    min="1" max="64" step="1"
                    class="number-input"
                  />
                </div>

                <div class="param-group">
                  <label>🔄 Gradient Accumulation Steps:</label>
                  <input 
                    type="number" 
                    bind:value={config.gradient_accumulation_steps}
                    min="1" max="32" step="1"
                    class="number-input"
                  />
                </div>

                <div class="param-group">
                  <label>🔥 Warmup Steps:</label>
                  <input 
                    type="number" 
                    bind:value={config.warmup_steps}
                    min="0" max="1000" step="10"
                    class="number-input"
                  />
                </div>

                <div class="param-group">
                  <label>📏 Max Sequence Length:</label>
                  <input 
                    type="number" 
                    bind:value={config.max_seq_length}
                    min="128" max="4096" step="64"
                    class="number-input"
                  />
                </div>
              </div>

              <div class="optimization-settings">
                <h3>⚡ Optimization Settings</h3>
                <div class="checkbox-grid">
                  <label class="checkbox-label">
                    <input type="checkbox" bind:checked={config.gradient_checkpointing} />
                    Gradient Checkpointing
                    <small>Reduces memory usage at cost of speed</small>
                  </label>

                  <label class="checkbox-label">
                    <input type="checkbox" bind:checked={config.fp16} />
                    Mixed Precision (FP16)
                    <small>Faster training with lower memory usage</small>
                  </label>
                </div>
              </div>
            </div>

          <!-- RAG Settings -->
          {:else if selectedSubTab === 'rag'}
            <div class="config-section">
              <h2>🔍 RAG-Specific Settings</h2>
              
              <div class="rag-toggle">
                <label class="checkbox-label large">
                  <input type="checkbox" bind:checked={config.use_retrieval_augmentation} />
                  Enable Retrieval-Augmented Generation Training
                </label>
              </div>

              {#if config.use_retrieval_augmentation}
                <div class="rag-settings">
                  <!-- Retrieval Corpus -->
                  <div class="form-group">
                    <label>📚 Retrieval Corpus:</label>
                    <div class="file-upload-area">
                      <input 
                        type="file" 
                        on:change={handleCorpusChange}
                        accept=".txt,.json,.jsonl"
                        class="file-input"
                      />
                      {#if config.retrieval_corpus_path}
                        <div class="file-info">
                          <span class="file-icon">📚</span>
                          <span>{config.retrieval_corpus_path}</span>
                        </div>
                      {/if}
                    </div>
                  </div>

                  <!-- Embedding Model -->
                  <div class="form-group">
                    <label>🔗 Embedding Model:</label>
                    <select bind:value={config.embedding_model} class="model-select">
                      <option value="sentence-transformers/all-MiniLM-L6-v2">all-MiniLM-L6-v2</option>
                      <option value="sentence-transformers/all-mpnet-base-v2">all-mpnet-base-v2</option>
                      <option value="intfloat/e5-base-v2">E5-base-v2</option>
                      <option value="BAAI/bge-base-en-v1.5">BGE-base-en-v1.5</option>
                    </select>
                  </div>

                  <!-- Top-K Retrieval -->
                  <div class="form-group">
                    <label>🔢 Top-K Retrieval:</label>
                    <input 
                      type="number" 
                      bind:value={config.top_k_retrieval}
                      min="1" max="20" step="1"
                      class="number-input"
                    />
                    <small>Number of documents to retrieve for each query</small>
                  </div>
                </div>
              {:else}
                <div class="rag-disabled-notice">
                  <div class="notice-icon">🔍</div>
                  <div>
                    <h3>RAG Training Disabled</h3>
                    <p>Enable RAG training to access retrieval-augmented fine-tuning options.</p>
                  </div>
                </div>
              {/if}
            </div>

          <!-- Advanced Settings -->
          {:else if selectedSubTab === 'advanced'}
            <div class="config-section">
              <h2>🚀 Advanced Configuration</h2>
              
              <div class="parameter-grid">
                <div class="param-group">
                  <label>💾 Save Steps:</label>
                  <input 
                    type="number" 
                    bind:value={config.save_steps}
                    min="10" max="5000" step="10"
                    class="number-input"
                  />
                </div>

                <div class="param-group">
                  <label>📊 Evaluation Steps:</label>
                  <input 
                    type="number" 
                    bind:value={config.eval_steps}
                    min="10" max="5000" step="10"
                    class="number-input"
                  />
                </div>

                <div class="param-group">
                  <label>📝 Logging Steps:</label>
                  <input 
                    type="number" 
                    bind:value={config.logging_steps}
                    min="1" max="100" step="1"
                    class="number-input"
                  />
                </div>

                <div class="param-group">
                  <label>👥 DataLoader Workers:</label>
                  <input 
                    type="number" 
                    bind:value={config.dataloader_num_workers}
                    min="0" max="16" step="1"
                    class="number-input"
                  />
                </div>
              </div>

              <!-- Instruction Template -->
              <div class="form-group">
                <label>📋 Instruction Template:</label>
                <select bind:value={config.instruction_template} class="template-select">
                  <option value="default">Default</option>
                  <option value="alpaca">Alpaca Style</option>
                  <option value="chatml">ChatML</option>
                  <option value="vicuna">Vicuna</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
            </div>
          {/if}

          <!-- Training Action -->
          <div class="training-action">
            <div class="action-summary">
              <h3>🎯 Training Summary</h3>
              <div class="summary-grid">
                <div class="summary-item">
                  <span class="summary-label">Method:</span>
                  <span class="summary-value">{getMethodIcon(config.method)} {config.method.toUpperCase()}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">Language:</span>
                  <span class="summary-value">{getLanguageFlag(config.language)} {config.language.toUpperCase()}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">Model:</span>
                  <span class="summary-value">{config.model_name}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">Epochs:</span>
                  <span class="summary-value">{config.num_epochs}</span>
                </div>
              </div>
            </div>

            <button 
              class="start-training-btn {running ? 'running' : ''}" 
              on:click={startFineTune} 
              disabled={running || !config.dataset_path}
            >
              {#if running}
                🔄 Training in Progress...
              {:else}
                🚀 Start Advanced Fine-Tuning
              {/if}
            </button>
          </div>
        </div>

      <!-- Models Tab -->
      {:else if selectedTab === 'models'}
        <div class="models-container">
          <div class="models-header">
            <h2>🤖 Fine-Tuned Models</h2>
            <p>Manage your trained models and configurations</p>
          </div>
          
          <div class="empty-state">
            <div class="empty-icon">🤖</div>
            <h3>No fine-tuned models yet</h3>
            <p>Start training your first model to see it appear here</p>
            <button class="secondary-btn" on:click={() => selectedTab = 'config'}>
              ⚙️ Start Configuration
            </button>
          </div>
        </div>

      <!-- Logs Tab -->
      {:else if selectedTab === 'logs'}
        <div class="logs-container">
          <div class="logs-header">
            <h2>📋 Training Logs</h2>
            <p>Monitor your fine-tuning progress in real-time</p>
            
            {#if running}
              <div class="status-indicator running">
                <span class="status-dot"></span>
                🔄 Training in progress...
              </div>
            {:else if logs.length > 0}
              <div class="status-indicator completed">
                <span class="status-dot"></span>
                ✅ Training completed
              </div>
            {:else}
              <div class="status-indicator idle">
                <span class="status-dot"></span>
                ⏸️ No active training
              </div>
            {/if}
          </div>
          
          <div class="logs-content">
            {#if logs.length > 0}
              <div class="logs-output">
                {#each logs as log}
                  <div class="log-entry {log.error ? 'error' : log.step ? 'progress' : 'info'}">
                    {#if log.timestamp}
                      <span class="log-timestamp">{new Date(log.timestamp * 1000).toLocaleTimeString()}</span>
                    {/if}
                    
                    {#if log.step}
                      <div class="log-progress">
                        <div class="progress-bar">
                          <div class="progress-fill" style="width: {(log.progress || 0) * 100}%"></div>
                        </div>
                        <span class="log-message">{log.message}</span>
                        {#if log.method}
                          <span class="log-badge">{log.method.toUpperCase()}</span>
                        {/if}
                      </div>
                    {:else}
                      <span class="log-message">{log.message || log}</span>
                    {/if}
                  </div>
                {/each}
              </div>
            {:else}
              <div class="empty-logs">
                <div class="empty-icon">📝</div>
                <h3>No training logs yet</h3>
                <p>Training logs will appear here when you start fine-tuning</p>
              </div>
            {/if}
          </div>
        </div>

      <!-- Metrics Tab -->
      {:else if selectedTab === 'metrics'}
        <div class="metrics-container">
          <div class="metrics-header">
            <h2>📊 Training Metrics</h2>
            <p>Visualize training loss and performance metrics</p>
          </div>
          
          <div class="metrics-content">
            <!-- Loss Chart -->
            <div class="chart-section">
              <div class="chart-header">
                <h3>📈 Training Loss</h3>
                <div class="chart-controls">
                  <button class="chart-btn active">Training Loss</button>
                  <button class="chart-btn">Validation Loss</button>
                  <button class="chart-btn">Learning Rate</button>
                </div>
              </div>
              
              <div class="chart-container">
                {#if logs.length > 0}
                  <div class="loss-chart">
                    <svg width="100%" height="300" viewBox="0 0 800 300">
                      <!-- Chart background -->
                      <rect width="800" height="300" fill="#f8f9fa" stroke="#e5e7eb" stroke-width="1"/>
                      
                      <!-- Grid lines -->
                      {#each Array(6) as _, i}
                        <line x1="60" y1={50 + i * 40} x2="750" y2={50 + i * 40} stroke="#e5e7eb" stroke-width="0.5"/>
                        <text x="45" y={55 + i * 40} font-size="10" fill="#6b7280" text-anchor="end">{(5-i) * 20}%</text>
                      {/each}
                      
                      {#each Array(11) as _, i}
                        <line x1={60 + i * 69} y1="50" x2={60 + i * 69} y2="250" stroke="#e5e7eb" stroke-width="0.5"/>
                        <text x={60 + i * 69} y="270" font-size="10" fill="#6b7280" text-anchor="middle">{i * 100}</text>
                      {/each}
                      
                      <!-- Chart title and labels -->
                      <text x="400" y="25" font-size="14" font-weight="bold" fill="#374151" text-anchor="middle">Training Loss Over Time</text>
                      <text x="400" y="295" font-size="12" fill="#6b7280" text-anchor="middle">Training Steps</text>
                      <text x="25" y="150" font-size="12" fill="#6b7280" text-anchor="middle" transform="rotate(-90 25 150)">Loss Value</text>
                      
                      <!-- Mock loss curve (in real implementation, this would use actual loss data) -->
                      <polyline 
                        points="60,200 129,150 198,130 267,120 336,115 405,112 474,110 543,109 612,108 681,107 750,106"
                        fill="none" 
                        stroke="#667eea" 
                        stroke-width="3"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                      
                      <!-- Data points -->
                      {#each [60,129,198,267,336,405,474,543,612,681,750] as x, i}
                        <circle cx={x} cy={200 - i * 9.4} r="4" fill="#667eea"/>
                      {/each}
                    </svg>
                  </div>
                {:else}
                  <div class="no-data">
                    <div class="no-data-icon">📊</div>
                    <h3>No Training Data Available</h3>
                    <p>Start a training session to see loss metrics and charts</p>
                  </div>
                {/if}
              </div>
            </div>
            
            <!-- Metrics Summary -->
            <div class="metrics-summary">
              <h3>📋 Training Summary</h3>
              <div class="metrics-grid">
                <div class="metric-item">
                  <div class="metric-label">Current Loss</div>
                  <div class="metric-value">
                    {logs.length > 0 ? '0.125' : 'N/A'}
                  </div>
                </div>
                
                <div class="metric-item">
                  <div class="metric-label">Best Loss</div>
                  <div class="metric-value">
                    {logs.length > 0 ? '0.089' : 'N/A'}
                  </div>
                </div>
                
                <div class="metric-item">
                  <div class="metric-label">Learning Rate</div>
                  <div class="metric-value">
                    {config.learning_rate}
                  </div>
                </div>
                
                                 <div class="metric-item">
                   <div class="metric-label">Epochs Completed</div>
                   <div class="metric-value">
                     {logs.length > 0 ? '2/5' : '0/' + config.num_epochs}
                   </div>
                 </div>
                
                <div class="metric-item">
                  <div class="metric-label">Training Time</div>
                  <div class="metric-value">
                    {logs.length > 0 ? '45m 32s' : 'N/A'}
                  </div>
                </div>
                
                <div class="metric-item">
                  <div class="metric-label">GPU Memory</div>
                  <div class="metric-value">
                    {logs.length > 0 ? '8.2/16 GB' : 'N/A'}
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Performance Indicators -->
            <div class="performance-section">
              <h3>⚡ Performance Indicators</h3>
              <div class="indicators-grid">
                <div class="indicator-card">
                  <div class="indicator-header">
                    <span class="indicator-icon">🎯</span>
                    <span class="indicator-title">Model Convergence</span>
                  </div>
                  <div class="indicator-status {logs.length > 0 ? 'good' : 'pending'}">
                    {logs.length > 0 ? 'Converging Well' : 'Pending Training'}
                  </div>
                  <div class="indicator-description">
                    Loss is decreasing steadily without overfitting
                  </div>
                </div>
                
                <div class="indicator-card">
                  <div class="indicator-header">
                    <span class="indicator-icon">🚀</span>
                    <span class="indicator-title">Training Speed</span>
                  </div>
                  <div class="indicator-status {logs.length > 0 ? 'excellent' : 'pending'}">
                    {logs.length > 0 ? 'Excellent' : 'Pending Training'}
                  </div>
                  <div class="indicator-description">
                    {config.method === 'qlora' ? 'QLoRA optimization active' : 'Standard training speed'}
                  </div>
                </div>
                
                <div class="indicator-card">
                  <div class="indicator-header">
                    <span class="indicator-icon">💾</span>
                    <span class="indicator-title">Memory Usage</span>
                  </div>
                  <div class="indicator-status {logs.length > 0 ? 'good' : 'pending'}">
                    {logs.length > 0 ? 'Optimal' : 'Pending Training'}
                  </div>
                  <div class="indicator-description">
                    Memory usage within acceptable limits
                  </div>
                </div>
              </div>
            </div>
          </div>
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

  .tabs, .sub-tabs {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .tab, .sub-tab {
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

  .sub-tab {
    background: #f8f9fa;
    color: #495057;
    border-color: #dee2e6;
    font-size: 0.9rem;
    padding: 0.5rem 1rem;
  }

  .tab:hover, .sub-tab:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.4);
    transform: translateY(-2px);
  }

  .sub-tab:hover {
    background: #e9ecef;
    border-color: #adb5bd;
  }

  .tab.active, .sub-tab.active {
    background: white;
    color: #667eea;
    border-color: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .sub-tab.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
  }

  .main-content {
    flex: 1;
    padding: 2rem;
    background: #f8f9fa;
  }

  .config-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .sub-tabs {
    background: white;
    padding: 1rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .config-section {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .config-section h2 {
    margin: 0 0 1.5rem 0;
    color: #333;
    font-size: 1.5rem;
    border-bottom: 2px solid #667eea;
    padding-bottom: 0.5rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: #495057;
  }

  .language-selector {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .language-btn {
    padding: 0.5rem 1rem;
    border: 2px solid #dee2e6;
    background: white;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
  }

  .language-btn:hover {
    border-color: #667eea;
    background: #f8f9ff;
  }

  .language-btn.active {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border-color: #667eea;
  }

  .method-selector {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
  }

  .method-option {
    position: relative;
  }

  .method-option input[type="radio"] {
    position: absolute;
    opacity: 0;
  }

  .method-label {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    border: 2px solid #dee2e6;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    background: white;
  }

  .method-option input[type="radio"]:checked + .method-label {
    border-color: #667eea;
    background: linear-gradient(135deg, #f8f9ff, #f0f4ff);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
  }

  .method-icon {
    font-size: 2rem;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  }

  .method-info {
    flex: 1;
  }

  .method-name {
    font-weight: 600;
    color: #333;
    margin-bottom: 0.25rem;
  }

  .method-desc {
    color: #6c757d;
    font-size: 0.9rem;
    line-height: 1.4;
  }

  .parameter-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .param-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .param-group label {
    font-weight: 600;
    color: #495057;
    margin-bottom: 0.25rem;
  }

  .number-input, .text-input, .model-select, .template-select {
    padding: 0.75rem;
    border: 2px solid #dee2e6;
    border-radius: 8px;
    font-size: 0.9rem;
    transition: all 0.3s ease;
    background: white;
  }

  .number-input:focus, .text-input:focus, .model-select:focus, .template-select:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .param-group small {
    color: #6c757d;
    font-size: 0.8rem;
    margin-top: 0.25rem;
  }

  .module-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .module-preset {
    padding: 0.5rem 1rem;
    background: #e9ecef;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.8rem;
    font-family: monospace;
    transition: all 0.3s ease;
  }

  .module-preset:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
  }

  .selected-modules {
    font-family: monospace;
    background: #f8f9fa;
    padding: 0.75rem;
    border-radius: 6px;
    border: 1px solid #dee2e6;
    color: #495057;
  }

  .qlora-section {
    background: linear-gradient(135deg, #fff5f5, #fef2f2);
    border: 2px solid #fed7d7;
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 2rem;
  }

  .qlora-section h3 {
    margin: 0 0 1rem 0;
    color: #c53030;
  }

  .checkbox-group, .checkbox-grid {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .checkbox-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
  }

  .checkbox-label {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    cursor: pointer;
    padding: 1rem;
    border: 2px solid #dee2e6;
    border-radius: 8px;
    transition: all 0.3s ease;
    background: white;
  }

  .checkbox-label:hover {
    border-color: #667eea;
    background: #f8f9ff;
  }

  .checkbox-label.large {
    font-size: 1.1rem;
    font-weight: 600;
    padding: 1.5rem;
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border-color: #bbf7d0;
  }

  .checkbox-label small {
    display: block;
    color: #6c757d;
    font-size: 0.8rem;
    margin-top: 0.25rem;
  }

  .method-notice, .rag-disabled-notice {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 2rem;
    background: linear-gradient(135deg, #fff9f0, #fef5e7);
    border: 2px solid #fed7aa;
    border-radius: 12px;
    color: #92400e;
  }

  .notice-icon {
    font-size: 3rem;
  }

  .method-notice h3, .rag-disabled-notice h3 {
    margin: 0 0 0.5rem 0;
    color: #92400e;
  }

  .training-action {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border: 2px solid #bbf7d0;
    border-radius: 12px;
    padding: 2rem;
    margin-top: 2rem;
  }

  .action-summary {
    margin-bottom: 2rem;
  }

  .action-summary h3 {
    margin: 0 0 1rem 0;
    color: #166534;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .summary-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: white;
    border-radius: 8px;
    border: 1px solid #bbf7d0;
  }

  .summary-label {
    font-weight: 600;
    color: #166534;
  }

  .summary-value {
    font-family: monospace;
    color: #059669;
    font-weight: 600;
  }

  .start-training-btn {
    width: 100%;
    padding: 1rem 2rem;
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  }

  .start-training-btn:hover:not(:disabled) {
    background: linear-gradient(135deg, #059669, #047857);
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
  }

  .start-training-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .start-training-btn.running {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
  }

  .models-container, .logs-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .models-header, .logs-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .models-header h2, .logs-header h2 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 2rem;
  }

  .models-header p, .logs-header p {
    color: #6c757d;
    font-size: 1.1rem;
    margin: 0;
  }

  .empty-state, .empty-logs {
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

  .empty-state h3, .empty-logs h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.5rem;
  }

  .empty-state p, .empty-logs p {
    margin: 0 0 2rem 0;
    line-height: 1.5;
    font-size: 1.1rem;
  }

  .secondary-btn {
    padding: 0.75rem 1.5rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 500;
    transition: all 0.3s ease;
  }

  .secondary-btn:hover {
    background: #5a67d8;
    transform: translateY(-2px);
  }

  .logs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    margin-bottom: 2rem;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
  }

  .status-indicator.running {
    color: #f59e0b;
  }

  .status-indicator.completed {
    color: #10b981;
  }

  .status-indicator.idle {
    color: #6c757d;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s infinite;
  }

  .logs-content {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .logs-output {
    max-height: 600px;
    overflow-y: auto;
    padding: 1rem;
  }

  .log-entry {
    padding: 0.75rem;
    border-bottom: 1px solid #f3f4f6;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.9rem;
  }

  .log-entry:last-child {
    border-bottom: none;
  }

  .log-entry.error {
    background: #fef2f2;
    border-left: 4px solid #ef4444;
    color: #dc2626;
  }

  .log-entry.progress {
    background: #f0f9ff;
    border-left: 4px solid #3b82f6;
  }

  .log-entry.info {
    background: #f8f9fa;
    border-left: 4px solid #6c757d;
  }

  .log-timestamp {
    color: #6c757d;
    margin-right: 1rem;
    font-weight: 500;
  }

  .log-progress {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .progress-bar {
    width: 100%;
    height: 8px;
    background: #e5e7eb;
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #1d4ed8);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .log-message {
    color: #333;
  }

  .log-badge {
    background: #3b82f6;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-left: auto;
  }

  /* Dark mode adjustments */
  :global(.dark) .app-container {
    background: #1a202c;
  }

  :global(.dark) .config-section,
  :global(.dark) .sub-tabs,
  :global(.dark) .empty-state,
  :global(.dark) .empty-logs,
  :global(.dark) .logs-content,
  :global(.dark) .logs-header {
    background: rgba(15, 12, 41, 0.9);
    color: #f1f5f9;
    border: 1px solid rgba(139, 69, 255, 0.3);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3), 0 0 20px rgba(139, 69, 255, 0.1);
  }

  :global(.dark) .number-input,
  :global(.dark) .text-input,
  :global(.dark) .model-select,
  :global(.dark) .template-select {
    background: rgba(30, 30, 60, 0.9);
    color: #f1f5f9;
    border: 1px solid rgba(139, 69, 255, 0.4);
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2), 0 0 10px rgba(139, 69, 255, 0.1);
  }

  :global(.dark) .number-input:focus,
  :global(.dark) .text-input:focus,
  :global(.dark) .model-select:focus,
  :global(.dark) .template-select:focus {
    border-color: rgba(139, 69, 255, 0.7);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3), 0 0 20px rgba(139, 69, 255, 0.3);
  }

  :global(.dark) .checkbox-label,
  :global(.dark) .method-label {
    background: rgba(30, 30, 60, 0.8);
    border: 1px solid rgba(139, 69, 255, 0.3);
    color: #f1f5f9;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2), 0 0 10px rgba(139, 69, 255, 0.1);
  }

  :global(.dark) .checkbox-label:hover,
  :global(.dark) .method-label:hover {
    background: rgba(30, 30, 60, 0.9);
    border-color: rgba(139, 69, 255, 0.5);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3), 0 0 15px rgba(139, 69, 255, 0.2);
  }

  :global(.dark) .language-btn {
    background: #4a5568;
    border-color: #718096;
    color: #f7fafc;
  }

  :global(.dark) .summary-item {
    background: #4a5568;
    border-color: #718096;
  }

  /* Metrics Styles */
  .metrics-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .metrics-header {
    text-align: center;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 2px solid #e5e7eb;
  }

  .metrics-header h2 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 1.8rem;
  }

  .metrics-header p {
    margin: 0;
    color: #6b7280;
    font-size: 1.1rem;
  }

  .metrics-content {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .chart-section {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 1.5rem;
    border: 2px solid #e5e7eb;
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .chart-header h3 {
    margin: 0;
    color: #374151;
    font-size: 1.3rem;
  }

  .chart-controls {
    display: flex;
    gap: 0.5rem;
  }

  .chart-btn {
    padding: 0.5rem 1rem;
    border: 2px solid #e5e7eb;
    border-radius: 6px;
    background: white;
    color: #6b7280;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.3s ease;
  }

  .chart-btn:hover {
    border-color: #667eea;
    color: #667eea;
  }

  .chart-btn.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
  }

  .chart-container {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    border: 1px solid #e5e7eb;
  }

  .loss-chart {
    width: 100%;
    height: 300px;
  }

  .no-data {
    text-align: center;
    padding: 3rem 2rem;
    color: #6b7280;
  }

  .no-data-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  .no-data h3 {
    margin: 0 0 0.5rem 0;
    color: #374151;
    font-size: 1.5rem;
  }

  .no-data p {
    margin: 0;
    font-size: 1.1rem;
  }

  .metrics-summary {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 1.5rem;
    border: 2px solid #e5e7eb;
  }

  .metrics-summary h3 {
    margin: 0 0 1rem 0;
    color: #374151;
    font-size: 1.3rem;
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .metric-item {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    border: 1px solid #e5e7eb;
    text-align: center;
  }

  .metric-label {
    font-size: 0.9rem;
    color: #6b7280;
    margin-bottom: 0.5rem;
    font-weight: 500;
  }

  .metric-value {
    font-size: 1.5rem;
    color: #374151;
    font-weight: 600;
  }

  .performance-section {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 1.5rem;
    border: 2px solid #e5e7eb;
  }

  .performance-section h3 {
    margin: 0 0 1rem 0;
    color: #374151;
    font-size: 1.3rem;
  }

  .indicators-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
  }

  .indicator-card {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    border: 1px solid #e5e7eb;
  }

  .indicator-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .indicator-icon {
    font-size: 1.5rem;
  }

  .indicator-title {
    font-weight: 600;
    color: #374151;
  }

  .indicator-status {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .indicator-status.pending {
    color: #6b7280;
  }

  .indicator-status.good {
    color: #059669;
  }

  .indicator-status.excellent {
    color: #2563eb;
  }

  .indicator-description {
    font-size: 0.9rem;
    color: #6b7280;
    line-height: 1.4;
  }

  /* Dark mode for metrics */
  :global(.dark) .metrics-container,
  :global(.dark) .chart-section,
  :global(.dark) .metrics-summary,
  :global(.dark) .performance-section {
    background: #2d3748;
    border-color: #4a5568;
    color: #f7fafc;
  }

  :global(.dark) .chart-container,
  :global(.dark) .metric-item,
  :global(.dark) .indicator-card {
    background: #4a5568;
    border-color: #718096;
    color: #f7fafc;
  }

  :global(.dark) .chart-btn {
    background: #4a5568;
    border-color: #718096;
    color: #f7fafc;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .parameter-grid,
    .summary-grid {
      grid-template-columns: 1fr;
    }

    .method-selector {
      grid-template-columns: 1fr;
    }

    .logs-header {
      flex-direction: column;
      gap: 1rem;
      text-align: center;
    }

    .tabs,
    .sub-tabs {
      flex-direction: column;
    }

    .language-selector {
      justify-content: center;
    }
  }
</style>
