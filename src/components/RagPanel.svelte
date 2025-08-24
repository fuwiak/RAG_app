<script lang="ts">
  import { onMount } from 'svelte';
  import { invoke } from '@tauri-apps/api/core';
  import { t } from '../lib/i18n';
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

  // Enhanced RAG Types
  interface EmbeddingModel {
    huggingface?: { model_name: string; api_key?: string };
    openai?: { api_key: string; model: string };
    groq?: { api_key: string; model: string };
    local?: { model_path: string };
    custom?: { name: string; api_url: string; api_key?: string; model: string };
  }

  type RAGMode = 'fine_tuned_only' | 'fine_tuned_rag' | 'base_rag';

  interface RAGConfig {
    embedding_model: EmbeddingModel;
    mode: RAGMode;
    chunk_size: number;
    chunk_overlap: number;
    top_k: number;
    similarity_threshold: number;
  }

  interface ProcessingResult {
    success: boolean;
    message: string;
    chunks_created: number;
    processing_time_ms: number;
  }

  interface RetrievalResult {
    chunk_id: string;
    content: string;
    document_title: string;
    similarity_score: number;
    source_info: string;
  }

  interface RAGResponse {
    answer: string;
    retrieved_context: RetrievalResult[];
    mode_used: RAGMode;
    processing_time_ms: number;
  }

  // State
  let documents: Document[] = [];
  let chatMessages: ChatMessage[] = [];
  let currentMessage = '';
  let isLoading = false;
  let selectedTab: 'chat' | 'documents' | 'search' | 'rag-config' | 'rag-test' = 'chat';
  let searchQuery = '';
  let searchResults: SearchResult[] = [];
  let isDragOver = false;

  // Enhanced RAG State
  let ragConfig: RAGConfig = {
    embedding_model: { 
      huggingface: { model_name: 'sentence-transformers/all-MiniLM-L6-v2', api_key: '' },
      openai: { api_key: '', model: 'text-embedding-ada-002' },
      groq: { api_key: '', model: 'text-embedding-ada-002' },
      local: { model_path: '' },
      custom: { name: '', api_url: '', api_key: '', model: '' }
    },
    mode: 'base_rag',
    chunk_size: 200,
    chunk_overlap: 50,
    top_k: 5,
    similarity_threshold: 0.3
  };
  let embeddingModelType: 'huggingface' | 'openai' | 'groq' | 'local' | 'custom' = 'huggingface';
  let testQuery = '';
  let testResult: RAGResponse | null = null;
  
  // API Key visibility states
  let showOpenAIKey = false;
  let showGroqKey = false;
  let showHFKey = false;
  let showCustomKey = false;
  
  // Embedding model search and selection
  let embeddingSearchQuery = '';
  let availableEmbeddings: string[] = [
    'sentence-transformers/all-MiniLM-L6-v2',
    'sentence-transformers/all-mpnet-base-v2',
    'sentence-transformers/distilbert-base-nli-stsb-mean-tokens',
    'sentence-transformers/paraphrase-MiniLM-L6-v2',
    'sentence-transformers/msmarco-distilbert-base-v4',
    'intfloat/e5-small-v2',
    'intfloat/e5-base-v2',
    'intfloat/e5-large-v2',
    'thenlper/gte-small',
    'thenlper/gte-base',
    'BAAI/bge-small-en-v1.5',
    'BAAI/bge-base-en-v1.5',
    'BAAI/bge-large-en-v1.5'
  ];
  let filteredEmbeddings: string[] = [...availableEmbeddings];
  let showEmbeddingDropdown = false;
  let isSearchingHF = false;

  // Language Models Management
  let selectedLanguage: 'en' | 'pl' | 'ru' | 'de' | 'fr' = 'en';
  let modelSearchQuery = '';
  let availableLanguageModels: Record<string, string[]> = {
    en: [
      'microsoft/DialoGPT-medium',
      'microsoft/DialoGPT-large',
      'facebook/blenderbot-400M-distill',
      'microsoft/phi-2',
      'google/flan-t5-base',
      'google/flan-t5-large',
      'EleutherAI/gpt-neo-2.7B',
      'microsoft/CodeBERT-base',
      'distilbert-base-uncased',
      'bert-base-uncased'
    ],
    pl: [
      'allegro/herbert-base-cased',
      'allegro/herbert-large-cased',
      'sdadas/polish-gpt2-medium',
      'sdadas/polish-roberta-base-v2',
      'allegro/plt5-base',
      'allegro/plt5-large',
      'clarin-pl/roberta-polish-kgr10',
      'polish-nlp/polish-distilroberta',
      'amu-cai/polish-bert-base-cased'
    ],
    ru: [
      'sberbank-ai/rugpt3large_based_on_gpt2',
      'sberbank-ai/rugpt3medium_based_on_gpt2',
      'ai-forever/ruBert-base',
      'ai-forever/ruRoberta-large',
      'cointegrated/rubert-tiny2',
      'DeepPavlov/rubert-base-cased',
      'ai-forever/ru-gpts-large',
      'sberbank-ai/sbert_large_nlu_ru'
    ],
    de: [
      'dbmdz/bert-base-german-cased',
      'dbmdz/bert-large-german-cased',
      'dbmdz/distilbert-base-german-cased',
      'german-nlp-group/electra-base-german-uncased',
      'deepset/gbert-base',
      'deepset/gbert-large',
      'malteos/gpt2-wechsel-german',
      'bert-base-german-dbmdz-cased'
    ],
    fr: [
      'camembert-base',
      'flaubert/flaubert_base_cased',
      'dbmdz/bert-base-french-europeana-cased',
      'lyon-nlp/mgpt-fr',
      'asi/gpt-fr-cased-base',
      'etalab-ia/camembert-base-wikipedia-4gb',
      'gilf/french-camembert-base'
    ]
  };
  let filteredLanguageModels: string[] = [...availableLanguageModels[selectedLanguage]];
  let showModelDropdown = false;
  let isSearchingModels = false;
  let selectedModel = '';
  let processingResults: ProcessingResult[] = [];
  let showAdvancedSettings = false;

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

  // Enhanced RAG Functions
  async function saveRAGConfig() {
    try {
      isLoading = true;
      
      // Update embedding model based on selected type
      ragConfig.embedding_model = {};
      if (embeddingModelType === 'huggingface') {
        ragConfig.embedding_model.huggingface = { 
          model_name: ragConfig.embedding_model.huggingface?.model_name || 'sentence-transformers/all-MiniLM-L6-v2',
          api_key: ragConfig.embedding_model.huggingface?.api_key || ''
        };
      } else if (embeddingModelType === 'openai') {
        ragConfig.embedding_model.openai = { 
          api_key: ragConfig.embedding_model.openai?.api_key || '',
          model: ragConfig.embedding_model.openai?.model || 'text-embedding-ada-002'
        };
      } else if (embeddingModelType === 'groq') {
        ragConfig.embedding_model.groq = { 
          api_key: ragConfig.embedding_model.groq?.api_key || '',
          model: ragConfig.embedding_model.groq?.model || 'text-embedding-ada-002'  
        };
      } else if (embeddingModelType === 'local') {
        ragConfig.embedding_model.local = { 
          model_path: ragConfig.embedding_model.local?.model_path || ''
        };
      } else if (embeddingModelType === 'custom') {
        ragConfig.embedding_model.custom = { 
          name: ragConfig.embedding_model.custom?.name || '',
          api_url: ragConfig.embedding_model.custom?.api_url || '',
          api_key: ragConfig.embedding_model.custom?.api_key || '',
          model: ragConfig.embedding_model.custom?.model || ''
        };
      }
      
      await invoke('set_rag_config', { config: ragConfig });
      
      // Show success notification
      processingResults = [{
        success: true,
        message: 'RAG configuration saved successfully',
        chunks_created: 0,
        processing_time_ms: 0
      }, ...processingResults.slice(0, 4)];
      
    } catch (error) {
      console.error('Error saving RAG config:', error);
      processingResults = [{
        success: false,
        message: `Failed to save configuration: ${error}`,
        chunks_created: 0,
        processing_time_ms: 0
      }, ...processingResults.slice(0, 4)];
    } finally {
      isLoading = false;
    }
  }
  
  async function loadRAGConfig() {
    try {
      const config = await invoke<RAGConfig>('get_rag_config');
      ragConfig = config;
      
      // Set embedding model type based on config
      if (config.embedding_model.huggingface) {
        embeddingModelType = 'huggingface';
        embeddingSearchQuery = config.embedding_model.huggingface.model_name;
      } else if (config.embedding_model.openai) {
        embeddingModelType = 'openai';
      } else if (config.embedding_model.groq) {
        embeddingModelType = 'groq';
      } else if (config.embedding_model.local) {
        embeddingModelType = 'local';
      } else if (config.embedding_model.custom) {
        embeddingModelType = 'custom';
      }
    } catch (error) {
      console.error('Error loading RAG config:', error);
    }
  }
  
  function resetRAGConfig() {
    ragConfig = {
      embedding_model: { 
        huggingface: { model_name: 'sentence-transformers/all-MiniLM-L6-v2', api_key: '' },
        openai: { api_key: '', model: 'text-embedding-ada-002' },
        groq: { api_key: '', model: 'text-embedding-ada-002' },
        local: { model_path: '' },
        custom: { name: '', api_url: '', api_key: '', model: '' }
      },
      mode: 'base_rag',
      chunk_size: 200,
      chunk_overlap: 50,
      top_k: 5,
      similarity_threshold: 0.3
    };
    embeddingModelType = 'huggingface';
    embeddingSearchQuery = 'sentence-transformers/all-MiniLM-L6-v2';
  }
  
  async function runRAGTest() {
    if (!testQuery.trim()) return;
    
    try {
      isLoading = true;
      testResult = null;
      
      const result = await invoke<RAGResponse>('test_rag_query', {
        query: testQuery,
        config: ragConfig
      });
      
      testResult = result;
    } catch (error) {
      console.error('Error running RAG test:', error);
      testResult = {
        answer: `Error running test: ${error}`,
        retrieved_context: [],
        mode_used: ragConfig.mode,
        processing_time_ms: 0
      };
    } finally {
      isLoading = false;
    }
  }
  
  // Enhanced document upload with RAG config
  async function uploadDocumentEnhanced(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    
    if (file) {
      try {
        isLoading = true;
        
        const result = await invoke<ProcessingResult>('process_document_enhanced', {
          filePath: file.name,
          title: file.name,
          config: ragConfig
        });
        
        // Add to processing results
        processingResults = [result, ...processingResults.slice(0, 4)];
        
        // Reload documents
        await loadDocuments();
        
      } catch (error) {
        console.error('Error uploading document:', error);
        processingResults = [{
          success: false,
          message: `Failed to process document: ${error}`,
          chunks_created: 0,
          processing_time_ms: 0
        }, ...processingResults.slice(0, 4)];
      } finally {
        isLoading = false;
      }
    }
    
    // Reset the input
    target.value = '';
  }

  // Enhanced embedding model functions
  function filterEmbeddings() {
    if (!embeddingSearchQuery.trim()) {
      filteredEmbeddings = [...availableEmbeddings];
    } else {
      filteredEmbeddings = availableEmbeddings.filter(model =>
        model.toLowerCase().includes(embeddingSearchQuery.toLowerCase())
      );
    }
  }

  async function searchHuggingFaceModels() {
    if (!embeddingSearchQuery.trim()) return;
    
    isSearchingHF = true;
    try {
      // Mock search for now - in real implementation, would call HF API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const mockResults = [
        `sentence-transformers/${embeddingSearchQuery}-v1`,
        `sentence-transformers/${embeddingSearchQuery}-base`,
        `intfloat/${embeddingSearchQuery}-small`,
        `thenlper/${embeddingSearchQuery}-large`
      ];
      
      // Add unique results to available embeddings
      mockResults.forEach(model => {
        if (!availableEmbeddings.includes(model)) {
          availableEmbeddings.push(model);
        }
      });
      
      filterEmbeddings();
    } catch (error) {
      console.error('Failed to search HuggingFace models:', error);
    } finally {
      isSearchingHF = false;
    }
  }

  function selectEmbedding(model: string) {
    ragConfig.embedding_model.huggingface!.model_name = model;
    embeddingSearchQuery = model;
    showEmbeddingDropdown = false;
  }

  function toggleKeyVisibility(provider: 'openai' | 'groq' | 'huggingface' | 'custom') {
    switch (provider) {
      case 'openai':
        showOpenAIKey = !showOpenAIKey;
        break;
      case 'groq':
        showGroqKey = !showGroqKey;
        break;
      case 'huggingface':
        showHFKey = !showHFKey;
        break;
      case 'custom':
        showCustomKey = !showCustomKey;
        break;
    }
  }

  // Language and Model Management Functions
  function switchLanguage(language: 'en' | 'pl' | 'ru' | 'de' | 'fr') {
    selectedLanguage = language;
    filteredLanguageModels = [...availableLanguageModels[language]];
    modelSearchQuery = '';
    selectedModel = filteredLanguageModels[0] || '';
    showModelDropdown = false;
  }

  function filterLanguageModels() {
    if (!modelSearchQuery.trim()) {
      filteredLanguageModels = [...availableLanguageModels[selectedLanguage]];
    } else {
      filteredLanguageModels = availableLanguageModels[selectedLanguage].filter(model =>
        model.toLowerCase().includes(modelSearchQuery.toLowerCase())
      );
    }
  }

  async function searchHuggingFaceLanguageModels() {
    if (!modelSearchQuery.trim()) return;
    
    isSearchingModels = true;
    try {
      // Mock search for language-specific models
      await new Promise(resolve => setTimeout(resolve, 1200));
      
      const languagePrefix = {
        en: 'english',
        pl: 'polish',
        ru: 'russian', 
        de: 'german',
        fr: 'french'
      }[selectedLanguage];
      
      const mockResults = [
        `${languagePrefix}-nlp/${modelSearchQuery}-base`,
        `${languagePrefix}-models/${modelSearchQuery}-large`,
        `huggingface/${languagePrefix}-${modelSearchQuery}`,
        `community/${languagePrefix}-${modelSearchQuery}-v2`
      ];
      
      // Add unique results to available models
      mockResults.forEach(model => {
        if (!availableLanguageModels[selectedLanguage].includes(model)) {
          availableLanguageModels[selectedLanguage].push(model);
        }
      });
      
      filterLanguageModels();
    } catch (error) {
      console.error('Failed to search HuggingFace language models:', error);
    } finally {
      isSearchingModels = false;
    }
  }

  function selectLanguageModel(model: string) {
    selectedModel = model;
    modelSearchQuery = model;
    showModelDropdown = false;
  }

  function getLanguageFlag(language: string): string {
    const flags = {
      en: '🇺🇸',
      pl: '🇵🇱', 
      ru: '🇷🇺',
      de: '🇩🇪',
      fr: '🇫🇷'
    };
    return flags[language as keyof typeof flags] || '🌍';
  }

  function getLanguageName(language: string): string {
    const names = {
      en: 'English',
      pl: 'Polish',
      ru: 'Russian',
      de: 'German',
      fr: 'French'
    };
    return names[language as keyof typeof names] || 'Unknown';
  }

  onMount(() => {
    loadDocuments();
    loadChatHistory();
    loadRAGConfig();
    
    // Initialize embedding search
    embeddingSearchQuery = ragConfig.embedding_model.huggingface?.model_name || 'sentence-transformers/all-MiniLM-L6-v2';
    filterEmbeddings();
    
    // Initialize model search
    selectedModel = filteredLanguageModels[0] || '';
    modelSearchQuery = selectedModel;
    
    // Close dropdowns when clicking outside
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest('.embedding-search-container')) {
        showEmbeddingDropdown = false;
      }
      if (!target.closest('.model-search-wrapper')) {
        showModelDropdown = false;
      }
    };
    
    document.addEventListener('click', handleClickOutside);
    
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  });
</script>

<main>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <h1 class="app-title nav-text-transition">{$t.rag_title}</h1>
        <p class="app-subtitle nav-description-transition">{$t.rag_subtitle}</p>
      </div>
      
             <!-- Navigation tabs -->
       <nav class="tabs">
         <button 
           class="tab {selectedTab === 'chat' ? 'active' : ''}"
           on:click={() => selectedTab = 'chat'}
         >
           💬 <span class="nav-text-transition">{$t.tab_chat}</span>
         </button>
         <button 
           class="tab {selectedTab === 'documents' ? 'active' : ''}"
           on:click={() => selectedTab = 'documents'}
         >
           📄 <span class="nav-text-transition">{$t.tab_documents} ({documents.length})</span>
         </button>
         <button 
           class="tab {selectedTab === 'search' ? 'active' : ''}"
           on:click={() => selectedTab = 'search'}
         >
           🔍 <span class="nav-text-transition">{$t.tab_search}</span>
         </button>
         <button 
           class="tab {selectedTab === 'rag-config' ? 'active' : ''}"
           on:click={() => selectedTab = 'rag-config'}
         >
           ⚙️ <span class="nav-text-transition">{$t.tab_rag_config}</span>
         </button>
         <button 
           class="tab {selectedTab === 'rag-test' ? 'active' : ''}"
           on:click={() => selectedTab = 'rag-test'}
         >
           🧪 <span class="nav-text-transition">{$t.tab_rag_test}</span>
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
               <h3 class="nav-text-transition">{$t.documents_no_docs}</h3>
               <p class="nav-description-transition">{$t.documents_start_chatting}</p>
               <button class="primary-button" on:click={triggerFileUpload}>
                 📎 <span class="nav-text-transition">{$t.documents_upload}</span>
               </button>
             </div>
          {:else}
            <div class="chat-messages">
              {#if chatMessages.length === 0}
                <div class="chat-welcome">
                  <div class="welcome-animation">
                    <div class="floating-particles">
                      <div class="particle"></div>
                      <div class="particle"></div>
                      <div class="particle"></div>
                      <div class="particle"></div>
                      <div class="particle"></div>
                    </div>
                    <div class="welcome-avatar">🤖</div>
                  </div>
                  <h3 class="nav-text-transition welcome-title">{$t.chat_welcome_title}</h3>
                  <p class="nav-description-transition welcome-desc">{$t.chat_welcome_desc}</p>
                  <div class="welcome-suggestions">
                    <div class="suggestion-card" on:click={() => currentMessage = 'What are the main topics in my documents?'}>
                      <span class="suggestion-icon">📊</span>
                      <span class="nav-text-transition">{$t.summarize_topics}</span>
                    </div>
                    <div class="suggestion-card" on:click={() => currentMessage = 'Find key insights from the latest reports'}>
                      <span class="suggestion-icon">💡</span>
                      <span class="nav-text-transition">{$t.key_insights}</span>
                    </div>
                    <div class="suggestion-card" on:click={() => currentMessage = 'What are the important dates and deadlines?'}>
                      <span class="suggestion-icon">📅</span>
                      <span class="nav-text-transition">{$t.important_dates}</span>
                    </div>
                  </div>
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
                  placeholder={$t.chat_placeholder}
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
             <h2 class="nav-text-transition">{$t.documents_library}</h2>
             <button class="primary-button" on:click={triggerFileUpload}>
               📎 <span class="nav-text-transition">{$t.documents_upload}</span>
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
              <div class="upload-animation">
                <div class="upload-icon-animated">📁</div>
                <div class="upload-ripple"></div>
              </div>
              <h3 class="upload-title nav-text-transition">{$t.documents_drop_zone}</h3>
              <p class="upload-formats nav-description-transition">{$t.documents_supported}</p>
              <div class="upload-features">
                <div class="upload-feature">
                  <span class="feature-icon">⚡</span>
                  <span class="nav-text-transition">{$t.instant_processing}</span>
                </div>
                <div class="upload-feature">
                  <span class="feature-icon">🔒</span>
                  <span class="nav-text-transition">{$t.secure_private}</span>
                </div>
                <div class="upload-feature">
                  <span class="feature-icon">📊</span>
                  <span class="nav-text-transition">{$t.ai_powered_analysis}</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Documents list -->
          {#if documents.length === 0}
            <div class="empty-state">
              <div class="empty-icon">📄</div>
              <h3 class="nav-text-transition">{$t.documents_no_docs}</h3>
              <p class="nav-description-transition">{$t.documents_upload_first}</p>
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
            <h2 class="nav-text-transition">{$t.search_documents}</h2>
          </div>
          
          <div class="search-input-container">
            <input
              type="text"
              bind:value={searchQuery}
              placeholder={$t.search_placeholder}
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
       
       <!-- RAG Configuration Tab -->
       {:else if selectedTab === 'rag-config'}
         <div class="rag-config-container">
                     <div class="config-header">
            <h2 class="nav-text-transition">⚙️ {$t.config_title}</h2>
            <p class="nav-description-transition">{$t.config_subtitle}</p>
            
            <!-- Language Switcher -->
            <div class="language-switcher">
              <h4>🌍 Language Selection</h4>
              <div class="language-buttons">
                {#each ['en', 'pl', 'ru', 'de', 'fr'] as lang}
                  <button 
                    class="language-button {selectedLanguage === lang ? 'active' : ''}"
                                         on:click={() => switchLanguage(lang)}
                    title="{getLanguageName(lang)} Models"
                  >
                    <span class="flag">{getLanguageFlag(lang)}</span>
                    <span class="lang-code">{lang.toUpperCase()}</span>
                  </button>
                {/each}
              </div>
              <p class="language-info">
                Selected: {getLanguageFlag(selectedLanguage)} {getLanguageName(selectedLanguage)} 
                ({filteredLanguageModels.length} models available)
              </p>
            </div>
          </div>
           
                     <!-- Embedding Model Selection -->
          <div class="config-section">
            <h3>🤖 Embedding Model</h3>
            <div class="model-selector">
              <label class="radio-option">
                <input type="radio" bind:group={embeddingModelType} value="huggingface" />
                <span class="radio-label">
                  <strong>🤗 HuggingFace</strong>
                  <small>Use pre-trained models from HuggingFace Hub</small>
                </span>
              </label>
              
              {#if embeddingModelType === 'huggingface'}
                <div class="model-config">
                  <label>
                    Model Name:
                    <div class="embedding-search-container">
                      <input 
                        type="text" 
                        bind:value={embeddingSearchQuery}
                        on:input={filterEmbeddings}
                        on:focus={() => showEmbeddingDropdown = true}
                        placeholder="Search or enter model name..."
                        class="embedding-search-input"
                      />
                      <button 
                        type="button"
                        class="search-hf-button"
                        on:click={searchHuggingFaceModels}
                        disabled={isSearchingHF}
                        title="Search HuggingFace Hub"
                      >
                        {#if isSearchingHF}
                          🔄
                        {:else}
                          🔍
                        {/if}
                      </button>
                      
                      {#if showEmbeddingDropdown && filteredEmbeddings.length > 0}
                        <div class="embedding-dropdown">
                          {#each filteredEmbeddings.slice(0, 10) as model}
                            <button 
                              type="button"
                              class="embedding-option"
                              on:click={() => selectEmbedding(model)}
                            >
                              {model}
                            </button>
                          {/each}
                        </div>
                      {/if}
                    </div>
                  </label>
                  
                  <label>
                    API Key (optional):
                    <div class="api-key-container">
                      {#if showHFKey}
                        <input 
                          type="text"
                          bind:value={ragConfig.embedding_model.huggingface.api_key}
                          placeholder="hf_..."
                          class="api-key-input"
                        />
                      {:else}
                        <input 
                          type="password"
                          bind:value={ragConfig.embedding_model.huggingface.api_key}
                          placeholder="hf_..."
                          class="api-key-input"
                        />
                      {/if}
                      <button 
                        type="button"
                        class="toggle-key-button"
                        on:click={() => toggleKeyVisibility('huggingface')}
                        title={showHFKey ? 'Hide key' : 'Show key'}
                      >
                        {showHFKey ? '🙈' : '👁️'}
                      </button>
                    </div>
                    <small>Optional for private models or higher rate limits</small>
                  </label>
                </div>
              {/if}
               
               <label class="radio-option">
                 <input type="radio" bind:group={embeddingModelType} value="openai" />
                 <span class="radio-label">
                   <strong>🚀 OpenAI</strong>
                   <small>Use OpenAI's embedding models (requires API key)</small>
                 </span>
               </label>
               
                             {#if embeddingModelType === 'openai'}
                <div class="model-config">
                  <label>
                    API Key:
                    <div class="api-key-container">
                      {#if showOpenAIKey}
                        <input 
                          type="text"
                          bind:value={ragConfig.embedding_model.openai.api_key}
                          placeholder="sk-..."
                          class="api-key-input"
                        />
                      {:else}
                        <input 
                          type="password"
                          bind:value={ragConfig.embedding_model.openai.api_key}
                          placeholder="sk-..."
                          class="api-key-input"
                        />
                      {/if}
                      <button 
                        type="button"
                        class="toggle-key-button"
                        on:click={() => toggleKeyVisibility('openai')}
                        title={showOpenAIKey ? 'Hide key' : 'Show key'}
                      >
                        {showOpenAIKey ? '🙈' : '👁️'}
                      </button>
                    </div>
                  </label>
                  <label>
                    Model:
                    <select bind:value={ragConfig.embedding_model.openai.model}>
                      <option value="text-embedding-ada-002">text-embedding-ada-002</option>
                      <option value="text-embedding-3-small">text-embedding-3-small</option>
                      <option value="text-embedding-3-large">text-embedding-3-large</option>
                    </select>
                  </label>
                </div>
              {/if}
               
                             <label class="radio-option">
                <input type="radio" bind:group={embeddingModelType} value="groq" />
                <span class="radio-label">
                  <strong>⚡ Groq</strong>
                  <small>Ultra-fast AI inference with Groq's LPU™</small>
                </span>
              </label>
              
              {#if embeddingModelType === 'groq'}
                <div class="model-config">
                  <label>
                    API Key:
                    <div class="api-key-container">
                      {#if showGroqKey}
                        <input 
                          type="text"
                          bind:value={ragConfig.embedding_model.groq.api_key}
                          placeholder="gsk_..."
                          class="api-key-input"
                        />
                      {:else}
                        <input 
                          type="password"
                          bind:value={ragConfig.embedding_model.groq.api_key}
                          placeholder="gsk_..."
                          class="api-key-input"
                        />
                      {/if}
                      <button 
                        type="button"
                        class="toggle-key-button"
                        on:click={() => toggleKeyVisibility('groq')}
                        title={showGroqKey ? 'Hide key' : 'Show key'}
                      >
                        {showGroqKey ? '🙈' : '👁️'}
                      </button>
                    </div>
                  </label>
                  <label>
                    Model:
                    <select bind:value={ragConfig.embedding_model.groq.model}>
                      <option value="text-embedding-ada-002">text-embedding-ada-002</option>
                      <option value="llama-3.1-8b-instant">llama-3.1-8b-instant</option>
                      <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
                    </select>
                  </label>
                </div>
              {/if}
              
              <label class="radio-option">
                <input type="radio" bind:group={embeddingModelType} value="local" />
                <span class="radio-label">
                  <strong>💻 Local</strong>
                  <small>Use local embedding model (requires model file)</small>
                </span>
              </label>
              
              {#if embeddingModelType === 'local'}
                <div class="model-config">
                  <label>
                    Model Path:
                    <input 
                      type="text" 
                      bind:value={ragConfig.embedding_model.local.model_path}
                      placeholder="/path/to/model"
                    />
                  </label>
                </div>
              {/if}
              
              <label class="radio-option">
                <input type="radio" bind:group={embeddingModelType} value="custom" />
                <span class="radio-label">
                  <strong>🔧 Custom</strong>
                  <small>Use your own custom embedding API</small>
                </span>
              </label>
              
              {#if embeddingModelType === 'custom'}
                <div class="model-config">
                  <label>
                    Name:
                    <input 
                      type="text" 
                      bind:value={ragConfig.embedding_model.custom.name}
                      placeholder="My Custom Model"
                    />
                  </label>
                  <label>
                    API URL:
                    <input 
                      type="text" 
                      bind:value={ragConfig.embedding_model.custom.api_url}
                      placeholder="https://api.example.com/embeddings"
                    />
                  </label>
                  <label>
                    API Key (optional):
                    <div class="api-key-container">
                      {#if showCustomKey}
                        <input 
                          type="text"
                          bind:value={ragConfig.embedding_model.custom.api_key}
                          placeholder="your-api-key"
                          class="api-key-input"
                        />
                      {:else}
                        <input 
                          type="password"
                          bind:value={ragConfig.embedding_model.custom.api_key}
                          placeholder="your-api-key"
                          class="api-key-input"
                        />
                      {/if}
                      <button 
                        type="button"
                        class="toggle-key-button"
                        on:click={() => toggleKeyVisibility('custom')}
                        title={showCustomKey ? 'Hide key' : 'Show key'}
                      >
                        {showCustomKey ? '🙈' : '👁️'}
                      </button>
                    </div>
                  </label>
                  <label>
                    Model:
                    <input 
                      type="text" 
                      bind:value={ragConfig.embedding_model.custom.model}
                      placeholder="model-name"
                    />
                  </label>
                </div>
              {/if}
                        </div>
          </div>
          
          <!-- HuggingFace Language Models Selection -->
          <div class="config-section">
            <h3>🤗 HuggingFace Language Models</h3>
            <div class="model-search-container">
              <label>
                Search & Select Model:
                <div class="model-search-wrapper">
                  <input 
                    type="text" 
                    bind:value={modelSearchQuery}
                    on:input={filterLanguageModels}
                    on:focus={() => showModelDropdown = true}
                    placeholder="Search {getLanguageName(selectedLanguage)} models..."
                    class="model-search-input"
                  />
                  <button 
                    type="button"
                    class="search-models-button"
                    on:click={searchHuggingFaceLanguageModels}
                    disabled={isSearchingModels}
                    title="Search HuggingFace for {getLanguageName(selectedLanguage)} models"
                  >
                    {#if isSearchingModels}
                      🔄
                    {:else}
                      🔍
                    {/if}
                  </button>
                  
                  {#if showModelDropdown && filteredLanguageModels.length > 0}
                    <div class="model-dropdown">
                      <div class="dropdown-header">
                        {getLanguageFlag(selectedLanguage)} {getLanguageName(selectedLanguage)} Models ({filteredLanguageModels.length})
                      </div>
                      {#each filteredLanguageModels.slice(0, 12) as model}
                        <button 
                          type="button"
                          class="model-option {selectedModel === model ? 'selected' : ''}"
                          on:click={() => selectLanguageModel(model)}
                        >
                          <span class="model-name">{model}</span>
                          <span class="model-badge">HF</span>
                        </button>
                      {/each}
                      {#if filteredLanguageModels.length > 12}
                        <div class="more-models">
                          +{filteredLanguageModels.length - 12} more models...
                        </div>
                      {/if}
                    </div>
                  {/if}
                </div>
              </label>
              
              {#if selectedModel}
                <div class="selected-model-info">
                  <div class="model-preview">
                    <span class="model-icon">🤖</span>
                    <div class="model-details">
                      <div class="model-title">{selectedModel}</div>
                      <div class="model-meta">
                        {getLanguageFlag(selectedLanguage)} {getLanguageName(selectedLanguage)} • HuggingFace
                      </div>
                    </div>
                  </div>
                </div>
              {/if}
            </div>
          </div>
          
          <!-- RAG Mode Selection -->
           <div class="config-section">
             <h3>🎯 RAG Mode</h3>
             <div class="mode-selector">
               <label class="radio-option">
                 <input type="radio" bind:group={ragConfig.mode} value="fine_tuned_only" />
                 <span class="radio-label">
                   <strong>🎯 Fine-tuned Only</strong>
                   <small>Use only your fine-tuned model (no document retrieval)</small>
                 </span>
               </label>
               
               <label class="radio-option">
                 <input type="radio" bind:group={ragConfig.mode} value="fine_tuned_rag" />
                 <span class="radio-label">
                   <strong>🔗 Fine-tuned + RAG</strong>
                   <small>Combine fine-tuned model with document retrieval</small>
                 </span>
               </label>
               
               <label class="radio-option">
                 <input type="radio" bind:group={ragConfig.mode} value="base_rag" />
                 <span class="radio-label">
                   <strong>📚 Base + RAG</strong>
                   <small>Use base model enhanced with document retrieval</small>
                 </span>
               </label>
             </div>
           </div>
           
           <!-- Advanced Settings -->
           <div class="config-section">
             <div class="advanced-toggle">
               <button 
                 class="toggle-button" 
                 on:click={() => showAdvancedSettings = !showAdvancedSettings}
               >
                 🔧 Advanced Settings {showAdvancedSettings ? '▼' : '▶'}
               </button>
             </div>
             
             {#if showAdvancedSettings}
               <div class="advanced-settings">
                 <div class="setting-row">
                   <label>
                     Chunk Size:
                     <input 
                       type="number" 
                       bind:value={ragConfig.chunk_size}
                       min="50"
                       max="1000"
                     />
                     <small>Number of words per chunk</small>
                   </label>
                   
                   <label>
                     Chunk Overlap:
                     <input 
                       type="number" 
                       bind:value={ragConfig.chunk_overlap}
                       min="0"
                       max="200"
                     />
                     <small>Overlapping words between chunks</small>
                   </label>
                 </div>
                 
                 <div class="setting-row">
                   <label>
                     Top-K Results:
                     <input 
                       type="number" 
                       bind:value={ragConfig.top_k}
                       min="1"
                       max="20"
                     />
                     <small>Number of top results to retrieve</small>
                   </label>
                   
                   <label>
                     Similarity Threshold:
                     <input 
                       type="number" 
                       bind:value={ragConfig.similarity_threshold}
                       min="0"
                       max="1"
                       step="0.1"
                     />
                     <small>Minimum similarity score (0-1)</small>
                   </label>
                 </div>
               </div>
             {/if}
           </div>
           
           <!-- Save Configuration -->
           <div class="config-actions">
             <button class="primary-button" on:click={saveRAGConfig}>
               💾 Save Configuration
             </button>
             <button class="secondary-button" on:click={resetRAGConfig}>
               🔄 Reset to Defaults
             </button>
           </div>
           
           <!-- Processing Results -->
           {#if processingResults.length > 0}
             <div class="processing-results">
               <h3>📊 Recent Processing Results</h3>
               {#each processingResults as result}
                 <div class="result-card {result.success ? 'success' : 'error'}">
                   <div class="result-header">
                     <span class="status-icon">{result.success ? '✅' : '❌'}</span>
                     <span class="result-message">{result.message}</span>
                   </div>
                   {#if result.success}
                     <div class="result-details">
                       <span>📄 {result.chunks_created} chunks created</span>
                       <span>⏱️ {result.processing_time_ms}ms</span>
                     </div>
                   {/if}
                 </div>
               {/each}
             </div>
           {/if}
         </div>
       
       <!-- RAG Testing Tab -->
       {:else if selectedTab === 'rag-test'}
         <div class="rag-test-container">
           <div class="test-header">
             <h2 class="nav-text-transition">🧪 {$t.test_title}</h2>
             <p class="nav-description-transition">{$t.test_subtitle}</p>
           </div>
           
           <div class="test-input-section">
             <label for="test-query" class="nav-text-transition">{$t.test_query_label}</label>
             <textarea
               id="test-query"
               bind:value={testQuery}
               placeholder={$t.test_query_placeholder}
               rows="3"
               class="test-input"
             ></textarea>
             
             <div class="test-actions">
               <button 
                 class="primary-button" 
                 on:click={runRAGTest}
                 disabled={!testQuery.trim() || isLoading}
               >
                 {isLoading ? '🔄 Testing...' : '🚀 Run Test'}
               </button>
               
               <div class="test-mode-info">
                 <strong>Current Mode:</strong> 
                 <span class="mode-badge mode-{ragConfig.mode}">
                   {ragConfig.mode === 'fine_tuned_only' ? '🎯 Fine-tuned Only' : 
                    ragConfig.mode === 'fine_tuned_rag' ? '🔗 Fine-tuned + RAG' : 
                    '📚 Base + RAG'}
                 </span>
               </div>
             </div>
           </div>
           
           {#if testResult}
             <div class="test-results">
               <div class="result-section">
                 <h3>💬 Generated Response</h3>
                 <div class="response-box">
                   {testResult.answer}
                 </div>
                 
                 <div class="result-meta">
                   <span>⏱️ Processing time: {testResult.processing_time_ms}ms</span>
                   <span>🎯 Mode used: {testResult.mode_used}</span>
                 </div>
               </div>
               
               {#if testResult.retrieved_context.length > 0}
                 <div class="result-section">
                   <h3>📋 Retrieved Context ({testResult.retrieved_context.length} chunks)</h3>
                   <div class="context-list">
                     {#each testResult.retrieved_context as context, index}
                       <div class="context-item">
                         <div class="context-header">
                           <span class="context-index">#{index + 1}</span>
                           <span class="context-source">📄 {context.document_title}</span>
                           <span class="similarity-score">
                             🎯 {Math.round(context.similarity_score * 100)}% match
                           </span>
                         </div>
                         <div class="context-content">
                           {context.content}
                         </div>
                         <div class="context-source-info">
                           📍 Source: {context.source_info}
                         </div>
                       </div>
                     {/each}
                   </div>
                 </div>
               {:else}
                 <div class="result-section">
                   <h3>📋 Retrieved Context</h3>
                   <div class="no-context">
                     ℹ️ No relevant context found or RAG mode doesn't use retrieval
                   </div>
                 </div>
               {/if}
             </div>
           {/if}
           
           {#if documents.length === 0}
             <div class="test-notice">
               <div class="notice-icon">📚</div>
               <h3>No documents available for testing</h3>
               <p>Upload some documents first to test RAG functionality with retrieval.</p>
               <button class="primary-button" on:click={() => selectedTab = 'documents'}>
                 📎 Go to Documents
               </button>
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

     /* RAG Configuration Styles */
   .rag-config-container, .rag-test-container {
     height: calc(100vh - 200px);
     overflow-y: auto;
     padding: 1rem;
   }

   .config-header, .test-header {
     text-align: center;
     margin-bottom: 2rem;
   }

   .config-header h2, .test-header h2 {
     margin: 0 0 0.5rem 0;
     color: #333;
   }

   .config-header p, .test-header p {
     color: #666;
     margin: 0;
   }

   .config-section {
     margin-bottom: 2rem;
     padding: 1.5rem;
     border: 1px solid #e0e0e0;
     border-radius: 12px;
     background: white;
   }

   .config-section h3 {
     margin: 0 0 1rem 0;
     color: #333;
   }

   .model-selector, .mode-selector {
     display: flex;
     flex-direction: column;
     gap: 1rem;
   }

   .radio-option {
     display: flex;
     align-items: flex-start;
     gap: 0.75rem;
     cursor: pointer;
     padding: 1rem;
     border: 2px solid #e0e0e0;
     border-radius: 8px;
     transition: all 0.3s ease;
   }

   .radio-option:hover {
     border-color: #667eea;
     background: rgba(102, 126, 234, 0.05);
   }

   .radio-option input[type="radio"] {
     margin: 0;
   }

   .radio-label {
     flex: 1;
   }

   .radio-label strong {
     display: block;
     margin-bottom: 0.25rem;
     color: #333;
   }

   .radio-label small {
     color: #666;
     font-size: 0.9rem;
   }

   .model-config {
     margin-top: 1rem;
     padding: 1rem;
     background: #f8f9fa;
     border-radius: 8px;
   }

   .model-config label {
     display: block;
     margin-bottom: 0.75rem;
     font-weight: 500;
   }

   .model-config input, .model-config select {
     width: 100%;
     padding: 0.5rem;
     border: 1px solid #ddd;
     border-radius: 6px;
     margin-top: 0.25rem;
   }

   .advanced-toggle {
     margin-bottom: 1rem;
   }

   .toggle-button {
     background: #667eea;
     color: white;
     border: none;
     padding: 0.75rem 1rem;
     border-radius: 8px;
     cursor: pointer;
     font-size: 1rem;
   }

   .advanced-settings {
     margin-top: 1rem;
     padding: 1rem;
     background: #f8f9fa;
     border-radius: 8px;
   }

   .setting-row {
     display: grid;
     grid-template-columns: 1fr 1fr;
     gap: 1rem;
     margin-bottom: 1rem;
   }

   .setting-row label {
     display: flex;
     flex-direction: column;
     gap: 0.25rem;
   }

   .setting-row input {
     padding: 0.5rem;
     border: 1px solid #ddd;
     border-radius: 6px;
   }

   .setting-row small {
     color: #666;
     font-size: 0.85rem;
   }

   .config-actions {
     display: flex;
     gap: 1rem;
     justify-content: center;
     margin: 2rem 0;
   }

   .secondary-button {
     background: #6c757d;
     color: white;
     border: none;
     padding: 0.75rem 1.5rem;
     border-radius: 8px;
     cursor: pointer;
     font-size: 1rem;
   }

   .processing-results {
     margin-top: 2rem;
   }

   .result-card {
     margin-bottom: 1rem;
     padding: 1rem;
     border-radius: 8px;
     border-left: 4px solid;
   }

   .result-card.success {
     background: #d4edda;
     border-left-color: #28a745;
   }

   .result-card.error {
     background: #f8d7da;
     border-left-color: #dc3545;
   }

   .result-header {
     display: flex;
     align-items: center;
     gap: 0.5rem;
     margin-bottom: 0.5rem;
   }

   .result-details {
     display: flex;
     gap: 1rem;
     font-size: 0.9rem;
     color: #666;
   }

   /* RAG Testing Styles */
   .test-input-section {
     margin-bottom: 2rem;
     padding: 1.5rem;
     border: 1px solid #e0e0e0;
     border-radius: 12px;
     background: white;
   }

   .test-input {
     width: 100%;
     padding: 1rem;
     border: 2px solid #e0e0e0;
     border-radius: 8px;
     resize: vertical;
     font-family: inherit;
     margin-top: 0.5rem;
   }

   .test-actions {
     display: flex;
     justify-content: space-between;
     align-items: center;
     margin-top: 1rem;
   }

   .test-mode-info {
     font-size: 0.9rem;
   }

   .mode-badge {
     padding: 0.25rem 0.75rem;
     border-radius: 15px;
     font-size: 0.8rem;
     font-weight: 500;
   }

   .mode-fine_tuned_only {
     background: #e3f2fd;
     color: #1976d2;
   }

   .mode-fine_tuned_rag {
     background: #f3e5f5;
     color: #7b1fa2;
   }

   .mode-base_rag {
     background: #e8f5e8;
     color: #388e3c;
   }

   .test-results {
     margin-top: 2rem;
   }

   .result-section {
     margin-bottom: 2rem;
     padding: 1.5rem;
     border: 1px solid #e0e0e0;
     border-radius: 12px;
     background: white;
   }

   .result-section h3 {
     margin: 0 0 1rem 0;
     color: #333;
   }

   .response-box {
     padding: 1rem;
     background: #f8f9fa;
     border-radius: 8px;
     white-space: pre-wrap;
     line-height: 1.6;
     margin-bottom: 1rem;
   }

   .result-meta {
     display: flex;
     gap: 1rem;
     font-size: 0.9rem;
     color: #666;
   }

   .context-list {
     display: flex;
     flex-direction: column;
     gap: 1rem;
   }

   .context-item {
     padding: 1rem;
     border: 1px solid #e0e0e0;
     border-radius: 8px;
     background: #f8f9fa;
   }

   .context-header {
     display: flex;
     justify-content: space-between;
     align-items: center;
     margin-bottom: 0.75rem;
     font-size: 0.9rem;
   }

   .context-index {
     background: #667eea;
     color: white;
     padding: 0.25rem 0.5rem;
     border-radius: 12px;
     font-size: 0.8rem;
     font-weight: 500;
   }

   .context-content {
     margin-bottom: 0.75rem;
     line-height: 1.5;
   }

   .context-source-info {
     font-size: 0.85rem;
     color: #666;
   }

   .no-context {
     text-align: center;
     padding: 2rem;
     color: #666;
     font-style: italic;
   }

   .test-notice {
     text-align: center;
     padding: 3rem;
     color: #666;
   }

   .notice-icon {
     font-size: 4rem;
     margin-bottom: 1rem;
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
       flex-wrap: wrap;
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

     .setting-row {
       grid-template-columns: 1fr;
     }

     .test-actions {
       flex-direction: column;
       gap: 1rem;
       align-items: stretch;
     }

         .context-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.5rem;
    }
  }

  /* Enhanced Embedding Model Styles */
  .embedding-search-container {
    position: relative;
    display: flex;
    gap: 0.5rem;
  }

  .embedding-search-input {
    flex: 1;
    padding: 0.75rem;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    font-size: 0.9rem;
    transition: all 0.3s ease;
  }

  .embedding-search-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .search-hf-button {
    background: #667eea;
    color: white;
    border: none;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 50px;
  }

  .search-hf-button:hover:not(:disabled) {
    background: #5a67d8;
    transform: translateY(-2px);
  }

  .search-hf-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .embedding-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    max-height: 300px;
    overflow-y: auto;
    margin-top: 0.5rem;
  }

  .embedding-option {
    width: 100%;
    padding: 0.75rem 1rem;
    border: none;
    background: white;
    text-align: left;
    cursor: pointer;
    font-size: 0.9rem;
    font-family: 'Monaco', 'Menlo', monospace;
    transition: background 0.2s ease;
    border-bottom: 1px solid #f3f4f6;
  }

  .embedding-option:last-child {
    border-bottom: none;
  }

  .embedding-option:hover {
    background: #f8f9fa;
  }

  .embedding-option:focus {
    outline: none;
    background: #eff6ff;
    color: #1d4ed8;
  }

  .api-key-container {
    position: relative;
    display: flex;
    gap: 0.5rem;
  }

  .api-key-input {
    flex: 1;
    padding: 0.75rem;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    font-size: 0.9rem;
    font-family: 'Monaco', 'Menlo', monospace;
    transition: all 0.3s ease;
  }

  .api-key-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .toggle-key-button {
    background: #f3f4f6;
    border: 2px solid #e5e7eb;
    padding: 0.75rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 50px;
  }

  .toggle-key-button:hover {
    background: #e5e7eb;
    border-color: #d1d5db;
  }

  .toggle-key-button:active {
    transform: scale(0.95);
  }

  /* Dark mode adjustments for new elements */
  :global(.dark) .embedding-search-input,
  :global(.dark) .api-key-input {
    background: #374151;
    border-color: #4b5563;
    color: #f9fafb;
  }

  :global(.dark) .embedding-search-input:focus,
  :global(.dark) .api-key-input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
  }

  :global(.dark) .embedding-dropdown {
    background: #374151;
    border-color: #4b5563;
  }

  :global(.dark) .embedding-option {
    background: #374151;
    color: #f9fafb;
    border-bottom-color: #4b5563;
  }

  :global(.dark) .embedding-option:hover {
    background: #4b5563;
  }

  :global(.dark) .embedding-option:focus {
    background: #1e40af;
    color: #dbeafe;
  }

  :global(.dark) .toggle-key-button {
    background: #4b5563;
    border-color: #6b7280;
    color: #f9fafb;
  }

  :global(.dark) .toggle-key-button:hover {
    background: #6b7280;
    border-color: #9ca3af;
  }

  /* Language Switcher Styles */
  .language-switcher {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1.5rem 0;
    border: 2px solid #e0f2fe;
  }

  .language-switcher h4 {
    margin: 0 0 1rem 0;
    color: #1e40af;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .language-buttons {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }

  .language-button {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.75rem 1rem;
    background: white;
    border: 2px solid #e0f2fe;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.3s ease;
    min-width: 70px;
    gap: 0.25rem;
  }

  .language-button:hover {
    border-color: #0ea5e9;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(14, 165, 233, 0.2);
  }

  .language-button.active {
    background: linear-gradient(135deg, #0ea5e9, #0284c7);
    border-color: #0284c7;
    color: white;
    box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
  }

  .language-button .flag {
    font-size: 1.5rem;
    line-height: 1;
  }

  .language-button .lang-code {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .language-info {
    color: #1e40af;
    font-size: 0.9rem;
    margin: 0;
    font-weight: 500;
  }

  /* Model Search Styles */
  .model-search-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .model-search-wrapper {
    position: relative;
    display: flex;
    gap: 0.5rem;
  }

  .model-search-input {
    flex: 1;
    padding: 0.75rem;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    font-size: 0.9rem;
    transition: all 0.3s ease;
    background: white;
  }

  .model-search-input:focus {
    outline: none;
    border-color: #0ea5e9;
    box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1);
  }

  .search-models-button {
    background: #0ea5e9;
    color: white;
    border: none;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 50px;
  }

  .search-models-button:hover:not(:disabled) {
    background: #0284c7;
    transform: translateY(-2px);
  }

  .search-models-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .model-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    max-height: 400px;
    overflow-y: auto;
    margin-top: 0.5rem;
  }

  .dropdown-header {
    padding: 1rem;
    background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
    border-bottom: 2px solid #e0f2fe;
    font-weight: 600;
    color: #1e40af;
    font-size: 0.9rem;
    border-radius: 10px 10px 0 0;
  }

  .model-option {
    width: 100%;
    padding: 0.75rem 1rem;
    border: none;
    background: white;
    text-align: left;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s ease;
    border-bottom: 1px solid #f3f4f6;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .model-option:last-child {
    border-bottom: none;
    border-radius: 0 0 10px 10px;
  }

  .model-option:hover {
    background: #f0f9ff;
    padding-left: 1.25rem;
  }

  .model-option.selected {
    background: linear-gradient(135deg, #dbeafe, #bfdbfe);
    color: #1e40af;
    font-weight: 600;
  }

  .model-name {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.85rem;
  }

  .model-badge {
    background: #0ea5e9;
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
  }

  .more-models {
    padding: 0.75rem 1rem;
    color: #6b7280;
    font-style: italic;
    font-size: 0.85rem;
    text-align: center;
    border-top: 1px solid #f3f4f6;
  }

  .selected-model-info {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border: 2px solid #bbf7d0;
    border-radius: 12px;
    padding: 1rem;
  }

  .model-preview {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .model-icon {
    font-size: 2rem;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  }

  .model-details {
    flex: 1;
  }

  .model-title {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 1rem;
    font-weight: 600;
    color: #166534;
    margin-bottom: 0.25rem;
  }

  .model-meta {
    color: #059669;
    font-size: 0.85rem;
    font-weight: 500;
  }

  /* Dark mode adjustments for language components */
  :global(.dark) .language-switcher {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border-color: #475569;
  }

  :global(.dark) .language-switcher h4 {
    color: #60a5fa;
  }

  :global(.dark) .language-button {
    background: #374151;
    border-color: #4b5563;
    color: #f9fafb;
  }

  :global(.dark) .language-button:hover {
    border-color: #60a5fa;
    box-shadow: 0 4px 12px rgba(96, 165, 250, 0.2);
  }

  :global(.dark) .language-button.active {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    border-color: #2563eb;
  }

  :global(.dark) .language-info {
    color: #93c5fd;
  }

  :global(.dark) .model-search-input {
    background: #374151;
    border-color: #4b5563;
    color: #f9fafb;
  }

  :global(.dark) .model-search-input:focus {
    border-color: #60a5fa;
    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2);
  }

  :global(.dark) .model-dropdown {
    background: #374151;
    border-color: #4b5563;
  }

  :global(.dark) .dropdown-header {
    background: linear-gradient(135deg, #1e293b, #334155);
    border-bottom-color: #475569;
    color: #60a5fa;
  }

  :global(.dark) .model-option {
    background: #374151;
    color: #f9fafb;
    border-bottom-color: #4b5563;
  }

  :global(.dark) .model-option:hover {
    background: #4b5563;
  }

  :global(.dark) .model-option.selected {
    background: linear-gradient(135deg, #1e3a8a, #1d4ed8);
    color: #dbeafe;
  }

  :global(.dark) .selected-model-info {
    background: linear-gradient(135deg, #1a2e05, #166534);
    border-color: #15803d;
  }

  :global(.dark) .model-title {
    color: #bbf7d0;
  }

  :global(.dark) .model-meta {
    color: #86efac;
  }

  /* Modern Welcome Interface */
  .chat-welcome {
    text-align: center;
    padding: 3rem;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
    border-radius: 20px;
    margin: 2rem;
    position: relative;
    overflow: hidden;
  }

  .welcome-animation {
    position: relative;
    margin-bottom: 2rem;
  }

  .floating-particles {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 200px;
    height: 200px;
  }

  .particle {
    position: absolute;
    width: 8px;
    height: 8px;
    background: linear-gradient(45deg, #667eea, #764ba2);
    border-radius: 50%;
    animation: float 3s ease-in-out infinite;
  }

  .particle:nth-child(1) {
    top: 20%;
    left: 20%;
    animation-delay: 0s;
    background: linear-gradient(45deg, #f093fb, #f5576c);
  }

  .particle:nth-child(2) {
    top: 20%;
    right: 20%;
    animation-delay: 0.6s;
    background: linear-gradient(45deg, #4facfe, #00f2fe);
  }

  .particle:nth-child(3) {
    bottom: 20%;
    left: 20%;
    animation-delay: 1.2s;
    background: linear-gradient(45deg, #667eea, #764ba2);
  }

  .particle:nth-child(4) {
    bottom: 20%;
    right: 20%;
    animation-delay: 1.8s;
    background: linear-gradient(45deg, #f093fb, #f5576c);
  }

  .particle:nth-child(5) {
    top: 50%;
    left: 50%;
    animation-delay: 2.4s;
    background: linear-gradient(45deg, #4facfe, #00f2fe);
  }

  @keyframes float {
    0%, 100% {
      transform: translateY(0px) scale(1);
      opacity: 0.7;
    }
    50% {
      transform: translateY(-20px) scale(1.2);
      opacity: 1;
    }
  }

  .welcome-avatar {
    font-size: 4rem;
    margin-bottom: 1rem;
    animation: bounce 2s ease-in-out infinite;
    position: relative;
    z-index: 2;
  }

  @keyframes bounce {
    0%, 20%, 50%, 80%, 100% {
      transform: translateY(0);
    }
    40% {
      transform: translateY(-10px);
    }
    60% {
      transform: translateY(-5px);
    }
  }

  .welcome-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 1rem;
  }

  .welcome-desc {
    font-size: 1.1rem;
    color: #6b7280;
    margin-bottom: 2rem;
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
  }

  .welcome-suggestions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    max-width: 600px;
    margin: 0 auto;
  }

  .suggestion-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 1.5rem;
    background: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
    font-weight: 500;
  }

  .suggestion-card:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    background: rgba(255, 255, 255, 0.9);
  }

  .suggestion-icon {
    font-size: 1.5rem;
  }

  :global(.dark) .chat-welcome {
    background: linear-gradient(135deg, rgba(15, 12, 41, 0.95) 0%, rgba(30, 30, 60, 0.95) 100%);
    border: 1px solid rgba(139, 69, 255, 0.3);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 0 0 30px rgba(139, 69, 255, 0.2);
  }

  :global(.dark) .welcome-desc {
    color: #e2e8f0;
  }

  :global(.dark) .suggestion-card {
    background: rgba(30, 30, 60, 0.8);
    border: 1px solid rgba(139, 69, 255, 0.4);
    color: #f1f5f9;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3), 0 0 15px rgba(139, 69, 255, 0.2);
  }

  :global(.dark) .suggestion-card:hover {
    background: rgba(30, 30, 60, 0.95);
    border-color: rgba(139, 69, 255, 0.6);
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.4), 0 0 25px rgba(139, 69, 255, 0.4);
    transform: translateY(-2px) scale(1.02);
  }

  /* Enhanced Upload Area */
  .upload-area {
    border: 2px dashed rgba(102, 126, 234, 0.3);
    border-radius: 20px;
    padding: 3rem;
    margin: 2rem 0;
    text-align: center;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }

  .upload-area:hover {
    border-color: rgba(102, 126, 234, 0.6);
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
    transform: scale(1.02);
  }

  .upload-area.drag-over {
    border-color: #4facfe;
    background: linear-gradient(135deg, rgba(79, 172, 254, 0.15) 0%, rgba(0, 242, 254, 0.15) 100%);
    transform: scale(1.05);
    box-shadow: 0 20px 40px rgba(79, 172, 254, 0.2);
  }

  .upload-animation {
    position: relative;
    margin-bottom: 2rem;
  }

  .upload-icon-animated {
    font-size: 4rem;
    margin-bottom: 1rem;
    animation: uploadPulse 2s ease-in-out infinite;
    position: relative;
    z-index: 2;
  }

  .upload-ripple {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100px;
    height: 100px;
    border: 3px solid rgba(102, 126, 234, 0.3);
    border-radius: 50%;
    animation: ripple 2s ease-out infinite;
  }

  @keyframes uploadPulse {
    0%, 100% {
      transform: scale(1);
    }
    50% {
      transform: scale(1.1);
    }
  }

  @keyframes ripple {
    0% {
      transform: translate(-50%, -50%) scale(0.5);
      opacity: 1;
    }
    100% {
      transform: translate(-50%, -50%) scale(2);
      opacity: 0;
    }
  }

  .upload-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: #374151;
    margin-bottom: 0.5rem;
  }

  .upload-formats {
    color: #6b7280;
    margin-bottom: 2rem;
  }

  .upload-features {
    display: flex;
    justify-content: center;
    gap: 2rem;
    flex-wrap: wrap;
  }

  .upload-feature {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: rgba(255, 255, 255, 0.7);
    border-radius: 12px;
    font-size: 0.9rem;
    font-weight: 500;
    backdrop-filter: blur(5px);
  }

  .feature-icon {
    font-size: 1.2rem;
  }

  :global(.dark) .upload-area {
    background: linear-gradient(135deg, rgba(15, 12, 41, 0.9) 0%, rgba(30, 30, 60, 0.9) 100%);
    border: 2px dashed rgba(139, 69, 255, 0.4);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3), 0 0 30px rgba(139, 69, 255, 0.1);
  }

  :global(.dark) .upload-area:hover {
    border-color: rgba(139, 69, 255, 0.7);
    background: linear-gradient(135deg, rgba(15, 12, 41, 0.95) 0%, rgba(30, 30, 60, 0.95) 100%);
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4), 0 0 40px rgba(139, 69, 255, 0.3);
  }

  :global(.dark) .upload-area.drag-over {
    border-color: rgba(255, 20, 147, 0.8);
    background: linear-gradient(135deg, rgba(15, 12, 41, 0.98) 0%, rgba(30, 30, 60, 0.98) 100%);
    box-shadow: 0 30px 60px rgba(0, 0, 0, 0.5), 0 0 50px rgba(255, 20, 147, 0.4);
  }

  :global(.dark) .upload-title {
    color: #f1f5f9;
  }

  :global(.dark) .upload-formats {
    color: #cbd5e1;
  }

  :global(.dark) .upload-feature {
    background: rgba(30, 30, 60, 0.8);
    color: #f1f5f9;
    border: 1px solid rgba(139, 69, 255, 0.3);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2), 0 0 10px rgba(139, 69, 255, 0.1);
  }
</style>
