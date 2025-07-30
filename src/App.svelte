<script lang="ts">
  import RagPanel from './components/RagPanel.svelte';
  import FineTunePanel from './components/FineTunePanel.svelte';
  import PlaygroundPanel from './components/PlaygroundPanel.svelte';
  import MonitorPanel from './components/MonitorPanel.svelte';
  import { writable } from 'svelte/store';
  import { darkMode } from './lib/theme';

  type Panel = 'rag' | 'fine-tune' | 'playground' | 'monitor';
  const panel = writable<Panel>('rag');
</script>

<div class="app-layout min-h-screen {$darkMode ? 'dark' : ''}" class:dark={$darkMode}>
  <!-- Sidebar Navigation -->
  <nav class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">🤖</span>
        <span class="logo-text">RAG App</span>
      </div>
      
      <!-- Dark Mode Toggle -->
      <label class="theme-toggle">
        <input type="checkbox" bind:checked={$darkMode} />
        <span class="theme-slider">
          <span class="theme-icon">{$darkMode ? '🌙' : '☀️'}</span>
        </span>
      </label>
    </div>

    <div class="nav-menu">
      <button 
        class="nav-item {$panel === 'rag' ? 'active' : ''}" 
        on:click={() => panel.set('rag')}
      >
        <span class="nav-icon">📚</span>
        <span class="nav-text">RAG</span>
        <span class="nav-description">Document Retrieval</span>
      </button>
      
      <button 
        class="nav-item {$panel === 'fine-tune' ? 'active' : ''}" 
        on:click={() => panel.set('fine-tune')}
      >
        <span class="nav-icon">🎯</span>
        <span class="nav-text">Fine-tune</span>
        <span class="nav-description">Model Training</span>
      </button>
      
      <button 
        class="nav-item {$panel === 'playground' ? 'active' : ''}" 
        on:click={() => panel.set('playground')}
      >
        <span class="nav-icon">🎮</span>
        <span class="nav-text">Playground</span>
        <span class="nav-description">Test Models</span>
      </button>
      
      <button 
        class="nav-item {$panel === 'monitor' ? 'active' : ''}" 
        on:click={() => panel.set('monitor')}
      >
        <span class="nav-icon">📊</span>
        <span class="nav-text">Monitor</span>
        <span class="nav-description">System & Metrics</span>
      </button>
    </div>

    <!-- Footer -->
    <div class="sidebar-footer">
      <div class="status-indicator">
        <span class="status-dot"></span>
        <span class="status-text">Ready</span>
      </div>
    </div>
  </nav>

  <!-- Main Content Area -->
  <main class="main-content">
    <div class="content-wrapper">
      {#if $panel === 'rag'}
        <RagPanel />
      {:else if $panel === 'fine-tune'}
        <FineTunePanel />
      {:else if $panel === 'playground'}
        <PlaygroundPanel />
      {:else if $panel === 'monitor'}
        <MonitorPanel />
      {/if}
    </div>
  </main>
</div>

<style>
  .app-layout {
    display: flex;
    height: 100vh;
    overflow: hidden;
    background: #f8f9fa;
    transition: background-color 0.3s ease;
  }

  .app-layout.dark {
    background: #1a202c;
  }

  /* Sidebar Styles */
  .sidebar {
    width: 280px;
    background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex;
    flex-direction: column;
    box-shadow: 4px 0 20px rgba(0, 0, 0, 0.1);
    position: relative;
    z-index: 10;
  }

  .sidebar-header {
    padding: 2rem 1.5rem 1.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .logo-icon {
    font-size: 2rem;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  }

  .logo-text {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  /* Theme Toggle */
  .theme-toggle {
    position: relative;
    cursor: pointer;
  }

  .theme-toggle input {
    display: none;
  }

  .theme-slider {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 28px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 20px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
  }

  .theme-toggle:hover .theme-slider {
    background: rgba(255, 255, 255, 0.3);
    border-color: rgba(255, 255, 255, 0.5);
    transform: scale(1.05);
  }

  .theme-icon {
    font-size: 1rem;
    transition: all 0.3s ease;
  }

  /* Navigation Menu */
  .nav-menu {
    flex: 1;
    padding: 1rem 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .nav-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 1.5rem 2rem;
    margin: 0 1rem;
    border: none;
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.9);
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: left;
    position: relative;
    overflow: hidden;
  }

  .nav-item::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .nav-item:hover::before {
    opacity: 1;
  }

  .nav-item:hover {
    background: rgba(255, 255, 255, 0.15);
    transform: translateX(8px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
  }

  .nav-item.active {
    background: rgba(255, 255, 255, 0.2);
    color: white;
    transform: translateX(8px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.3);
  }

  .nav-item.active::before {
    opacity: 1;
  }

  .nav-icon {
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  }

  .nav-text {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
    line-height: 1.2;
  }

  .nav-description {
    font-size: 0.85rem;
    opacity: 0.8;
    line-height: 1.3;
    font-weight: 400;
  }

  .nav-item.active .nav-description {
    opacity: 0.95;
  }

  /* Sidebar Footer */
  .sidebar-footer {
    padding: 1.5rem 2rem;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.9rem;
    opacity: 0.8;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    background: #4caf50;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .status-text {
    font-weight: 500;
  }

  /* Main Content */
  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: transparent;
    width: 100%;
  }

  .content-wrapper {
    flex: 1;
    overflow: auto;
    padding: 0;
    margin: 0;
    height: 100%;
    width: 100%;
    background: transparent;
  }

  /* Ensure panels take full space */
  .content-wrapper :global(.app-container) {
    height: 100vh;
    width: 100% !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    border: none !important;
    background: #ffffff;
    transition: background-color 0.3s ease;
  }

  /* Ensure main content areas take full width */
  .content-wrapper :global(.main-content) {
    padding: 2rem !important;
    max-width: none !important;
    margin: 0 !important;
  }

  .content-wrapper :global(.config-container),
  .content-wrapper :global(.models-container),
  .content-wrapper :global(.logs-container),
  .content-wrapper :global(.chat-container),
  .content-wrapper :global(.settings-container),
  .content-wrapper :global(.history-container) {
    max-width: none !important;
    width: 100% !important;
    margin: 0 !important;
  }

  /* Dark Mode Adjustments */
  .app-layout.dark .sidebar {
    background: linear-gradient(180deg, #1a202c 0%, #2d3748 100%);
  }

  .app-layout.dark .content-wrapper :global(.app-container) {
    background: #1a202c;
    color: #f7fafc;
  }

  .app-layout.dark .content-wrapper :global(.header) {
    background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%) !important;
  }

  .app-layout.dark .content-wrapper :global(.main-content) {
    background: #2d3748 !important;
  }

  .app-layout.dark .content-wrapper :global(.config-section),
  .app-layout.dark .content-wrapper :global(.chat-interface),
  .app-layout.dark .content-wrapper :global(.logs-section),
  .app-layout.dark .content-wrapper :global(.history-item),
  .app-layout.dark .content-wrapper :global(.response-section),
  .app-layout.dark .content-wrapper :global(.context-section) {
    background: #374151 !important;
    border-color: #4b5563 !important;
    color: #f9fafb !important;
  }

  .app-layout.dark .content-wrapper :global(.config-header h2),
  .app-layout.dark .content-wrapper :global(.config-header p),
  .app-layout.dark .content-wrapper :global(.config-section h3),
  .app-layout.dark .content-wrapper :global(.test-header h2),
  .app-layout.dark .content-wrapper :global(.test-header p) {
    color: #f9fafb !important;
  }

  .app-layout.dark .content-wrapper :global(.text-input),
  .app-layout.dark .content-wrapper :global(.file-input),
  .app-layout.dark .content-wrapper :global(.chat-input) {
    background: #4b5563 !important;
    border-color: #6b7280 !important;
    color: #f9fafb !important;
  }

  .app-layout.dark .content-wrapper :global(.response-content),
  .app-layout.dark .content-wrapper :global(.context-content),
  .app-layout.dark .content-wrapper :global(.file-info) {
    background: #4b5563 !important;
    color: #e5e7eb !important;
  }

  /* Responsive Design */
  @media (max-width: 1024px) {
    .sidebar {
      width: 240px;
    }
    
    .nav-item {
      padding: 1.25rem 1.5rem;
      margin: 0 0.75rem;
    }
    
    .sidebar-header {
      padding: 1.5rem 1.25rem;
    }
    
    .logo-text {
      font-size: 1.3rem;
    }
  }

  @media (max-width: 768px) {
    .app-layout {
      flex-direction: column;
    }
    
    .sidebar {
      width: 100%;
      height: auto;
      flex-direction: row;
      overflow-x: auto;
    }
    
    .sidebar-header {
      flex-shrink: 0;
      border-bottom: none;
      border-right: 1px solid rgba(255, 255, 255, 0.1);
      padding: 1rem;
    }
    
    .logo {
      flex-direction: column;
      gap: 0.25rem;
      text-align: center;
    }
    
    .logo-text {
      font-size: 0.9rem;
    }
    
    .logo-icon {
      font-size: 1.5rem;
    }
    
    .nav-menu {
      flex-direction: row;
      padding: 1rem;
      gap: 1rem;
      overflow-x: auto;
    }
    
    .nav-item {
      flex-shrink: 0;
      min-width: 120px;
      padding: 1rem;
      margin: 0;
      text-align: center;
      align-items: center;
    }
    
    .nav-item:hover,
    .nav-item.active {
      transform: translateY(-4px);
    }
    
    .nav-text {
      font-size: 1rem;
    }
    
    .nav-description {
      font-size: 0.75rem;
    }
    
    .sidebar-footer {
      flex-shrink: 0;
      border-top: none;
      border-left: 1px solid rgba(255, 255, 255, 0.1);
      padding: 1rem;
    }
    
    .main-content {
      height: calc(100vh - 120px);
    }
  }

  @media (max-width: 480px) {
    .sidebar-header {
      padding: 0.75rem;
    }
    
    .nav-menu {
      padding: 0.75rem;
      gap: 0.5rem;
    }
    
    .nav-item {
      min-width: 100px;
      padding: 0.75rem;
    }
    
    .nav-icon {
      font-size: 1.5rem;
    }
    
    .nav-text {
      font-size: 0.9rem;
    }
    
    .nav-description {
      display: none;
    }
  }
</style>
