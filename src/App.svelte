<script lang="ts">
  import RagPanel from './components/RagPanel.svelte';
  import FineTunePanel from './components/FineTunePanel.svelte';
  import PlaygroundPanel from './components/PlaygroundPanel.svelte';
  import MonitorPanel from './components/MonitorPanel.svelte';
  import { writable } from 'svelte/store';
  import { darkMode } from './lib/theme';
  import { currentLanguage, t, type Language } from './lib/i18n';

  type Panel = 'rag' | 'fine-tune' | 'playground' | 'monitor';
  const panel = writable<Panel>('rag');

  function toggleLanguage() {
    // Add animation class
    if (typeof document !== 'undefined') {
      document.body.classList.add('language-switching');
      setTimeout(() => {
        document.body.classList.remove('language-switching');
      }, 500);
    }
    
    currentLanguage.update(lang => lang === 'en' ? 'ru' : 'en');
  }
</script>

<div class="app-layout min-h-screen {$darkMode ? 'dark' : ''}" class:dark={$darkMode}>
  <!-- Sidebar Navigation -->
  <nav class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">🤖</span>
        <span class="logo-text app-title-transition">{$t.app_title}</span>
      </div>
      
      <div class="header-controls">
        <!-- Language Toggle -->
        <button class="language-toggle" on:click={toggleLanguage} title="Switch Language">
          <span class="language-flag">{$currentLanguage === 'en' ? '🇺🇸' : '🇷🇺'}</span>
          <span class="language-code">{$currentLanguage.toUpperCase()}</span>
        </button>
        
        <!-- Dark Mode Toggle -->
        <label class="theme-toggle">
          <input type="checkbox" bind:checked={$darkMode} />
          <span class="theme-slider">
            <span class="theme-icon">{$darkMode ? '🌙' : '☀️'}</span>
          </span>
        </label>
      </div>
    </div>

    <div class="nav-menu">
      <button 
        class="nav-item {$panel === 'rag' ? 'active' : ''}" 
        on:click={() => panel.set('rag')}
      >
        <span class="nav-icon">📚</span>
        <span class="nav-text nav-text-transition">{$t.nav_rag}</span>
        <span class="nav-description nav-description-transition">{$t.nav_rag_description}</span>
      </button>
      
      <button 
        class="nav-item {$panel === 'fine-tune' ? 'active' : ''}" 
        on:click={() => panel.set('fine-tune')}
      >
        <span class="nav-icon">🎯</span>
        <span class="nav-text nav-text-transition">{$t.nav_finetune}</span>
        <span class="nav-description nav-description-transition">{$t.nav_finetune_description}</span>
      </button>
      
      <button 
        class="nav-item {$panel === 'playground' ? 'active' : ''}" 
        on:click={() => panel.set('playground')}
      >
        <span class="nav-icon">🎮</span>
        <span class="nav-text nav-text-transition">{$t.nav_playground}</span>
        <span class="nav-description nav-description-transition">{$t.nav_playground_description}</span>
      </button>
      
      <button 
        class="nav-item {$panel === 'monitor' ? 'active' : ''}" 
        on:click={() => panel.set('monitor')}
      >
        <span class="nav-icon">📊</span>
        <span class="nav-text nav-text-transition">{$t.nav_monitor}</span>
        <span class="nav-description nav-description-transition">{$t.nav_monitor_description}</span>
      </button>
    </div>

    <!-- Footer -->
    <div class="sidebar-footer">
      <div class="status-indicator">
        <span class="status-dot"></span>
        <span class="status-text nav-text-transition">{$t.status_ready}</span>
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
    background: linear-gradient(135deg, 
      #f093fb 0%, 
      #f5576c 25%, 
      #4facfe 50%, 
      #00f2fe 75%, 
      #667eea 100%);
    transition: all 0.4s ease;
    position: relative;
  }

  .app-layout::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 30% 80%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
    pointer-events: none;
    z-index: 1;
  }

  .app-layout.dark {
    background: linear-gradient(135deg, 
      #0f0c29 0%, 
      #24243e 25%, 
      #302b63 50%, 
      #24243e 75%, 
      #0f0c29 100%);
    position: relative;
  }

  .app-layout.dark::before {
    background: radial-gradient(circle at 30% 80%, rgba(139, 69, 255, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 20, 147, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(0, 191, 255, 0.1) 0%, transparent 70%);
  }

  /* Dark theme aurora effect */
  .app-layout.dark::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: 
      radial-gradient(ellipse 800px 600px at 50% 0%, rgba(139, 69, 255, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse 600px 400px at 0% 100%, rgba(255, 20, 147, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse 400px 300px at 100% 50%, rgba(0, 191, 255, 0.08) 0%, transparent 50%);
    pointer-events: none;
    z-index: 1;
    animation: darkAurora 20s ease-in-out infinite;
  }

  @keyframes darkAurora {
    0%, 100% {
      opacity: 0.3;
      transform: scale(1);
    }
    50% {
      opacity: 0.6;
      transform: scale(1.1);
    }
  }

  /* Sidebar Styles */
  .sidebar {
    width: 280px;
    background: linear-gradient(135deg, 
      #667eea 0%, 
      #764ba2 25%, 
      #f093fb 50%, 
      #f5576c 75%, 
      #4facfe 100%);
    color: white;
    display: flex;
    flex-direction: column;
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.2), 
                0 10px 20px rgba(0, 0, 0, 0.15),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
    position: relative;
    z-index: 100;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
  }

  .sidebar-header {
    padding: 2rem 1.5rem 1.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
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

  /* Language Toggle */
  .language-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: rgba(255, 255, 255, 0.15);
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 16px;
    color: white;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(15px);
    font-size: 0.85rem;
    font-weight: 600;
    position: relative;
    overflow: hidden;
  }

  .language-toggle:hover {
    background: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.5);
    transform: scale(1.08) rotate(2deg);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2), 0 0 20px rgba(255, 255, 255, 0.1);
  }

  .language-flag {
    font-size: 1.2rem;
    transition: transform 0.3s ease;
  }

  .language-toggle:hover .language-flag {
    transform: scale(1.1);
  }

  .language-code {
    transition: all 0.3s ease;
  }

  /* Translation Animations */
  .app-title-transition,
  .nav-text-transition,
  .nav-description-transition {
    transition: opacity 0.2s ease-in-out, transform 0.2s ease-in-out;
  }

  .app-title-transition {
    animation: fadeInSlide 0.4s ease-out;
  }

  .nav-text-transition {
    animation: fadeInSlide 0.3s ease-out;
  }

  .nav-description-transition {
    animation: fadeInSlide 0.4s ease-out 0.1s both;
  }

  @keyframes fadeInSlide {
    0% {
      opacity: 0;
      transform: translateY(-10px);
    }
    100% {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* Language switch animation trigger */
  :global(.language-switching) .app-title-transition,
  :global(.language-switching) .nav-text-transition,
  :global(.language-switching) .nav-description-transition {
    animation: languageSwitch 0.5s ease-in-out;
  }

  @keyframes languageSwitch {
    0% {
      opacity: 1;
      transform: translateY(0);
    }
    50% {
      opacity: 0;
      transform: translateY(-5px);
    }
    100% {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes activeGlow {
    0% {
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 
                  0 0 40px rgba(245, 87, 108, 0.3),
                  inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }
    100% {
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 
                  0 0 50px rgba(79, 172, 254, 0.4),
                  inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
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
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.95);
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    text-align: left;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(15px);
    border: 1px solid rgba(255, 255, 255, 0.1);
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
    background: rgba(255, 255, 255, 0.2);
    transform: translateX(12px) scale(1.02);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3), 0 0 30px rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.3);
  }

  .nav-item.active {
    background: rgba(255, 255, 255, 0.25);
    color: white;
    transform: translateX(12px) scale(1.02);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), 
                0 0 40px rgba(245, 87, 108, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.4);
    animation: activeGlow 2s ease-in-out infinite alternate;
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
    margin: 1rem !important;
    margin-left: 0 !important;
    padding: 0 !important;
    border-radius: 25px !important;
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.1), 
                0 8px 16px rgba(0, 0, 0, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    background: rgba(255, 255, 255, 0.85) !important;
    backdrop-filter: blur(20px) !important;
    transition: all 0.4s ease !important;
    overflow: hidden !important;
    position: relative !important;
    z-index: 2 !important;
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
    background: linear-gradient(135deg, 
      #1a1a2e 0%, 
      #16213e 25%, 
      #0f3460 50%, 
      #16213e 75%, 
      #1a1a2e 100%);
    border-right: 1px solid rgba(139, 69, 255, 0.3);
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4), 
                0 10px 20px rgba(0, 0, 0, 0.3),
                inset 0 1px 0 rgba(139, 69, 255, 0.2);
  }

  .app-layout.dark .content-wrapper :global(.app-container) {
    background: rgba(15, 12, 41, 0.95) !important;
    color: #f7fafc;
    border: 1px solid rgba(139, 69, 255, 0.2) !important;
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3), 
                0 8px 16px rgba(0, 0, 0, 0.2),
                inset 0 1px 0 rgba(139, 69, 255, 0.1) !important;
  }

  .app-layout.dark .content-wrapper :global(.header) {
    background: linear-gradient(135deg, 
      rgba(26, 26, 46, 0.95) 0%, 
      rgba(22, 33, 62, 0.95) 50%, 
      rgba(15, 52, 96, 0.95) 100%) !important;
    border-bottom: 1px solid rgba(139, 69, 255, 0.3) !important;
    backdrop-filter: blur(20px) !important;
  }

  .app-layout.dark .content-wrapper :global(.main-content) {
    background: linear-gradient(135deg, 
      rgba(15, 12, 41, 0.3) 0%, 
      rgba(36, 36, 62, 0.3) 50%, 
      rgba(48, 43, 99, 0.3) 100%) !important;
    backdrop-filter: blur(10px) !important;
  }

  .app-layout.dark .content-wrapper :global(.config-section),
  .app-layout.dark .content-wrapper :global(.chat-interface),
  .app-layout.dark .content-wrapper :global(.logs-section),
  .app-layout.dark .content-wrapper :global(.history-item),
  .app-layout.dark .content-wrapper :global(.response-section),
  .app-layout.dark .content-wrapper :global(.context-section) {
    background: rgba(26, 26, 46, 0.8) !important;
    border: 1px solid rgba(139, 69, 255, 0.2) !important;
    color: #f9fafb !important;
    backdrop-filter: blur(10px) !important;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2) !important;
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
    background: rgba(26, 26, 46, 0.9) !important;
    border: 1px solid rgba(139, 69, 255, 0.3) !important;
    color: #f9fafb !important;
    backdrop-filter: blur(10px) !important;
  }

  .app-layout.dark .content-wrapper :global(.text-input:focus),
  .app-layout.dark .content-wrapper :global(.file-input:focus),
  .app-layout.dark .content-wrapper :global(.chat-input:focus) {
    border-color: rgba(139, 69, 255, 0.6) !important;
    box-shadow: 0 0 20px rgba(139, 69, 255, 0.3) !important;
  }

  .app-layout.dark .content-wrapper :global(.response-content),
  .app-layout.dark .content-wrapper :global(.context-content),
  .app-layout.dark .content-wrapper :global(.file-info) {
    background: rgba(15, 12, 41, 0.8) !important;
    color: #e5e7eb !important;
    border: 1px solid rgba(139, 69, 255, 0.2) !important;
    backdrop-filter: blur(10px) !important;
  }

  /* Dark theme buttons and interactive elements */
  .app-layout.dark .content-wrapper :global(.primary-button),
  .app-layout.dark .content-wrapper :global(.send-button) {
    background: linear-gradient(135deg, #8b45ff 0%, #ff1493 100%) !important;
    border: none !important;
    box-shadow: 0 8px 25px rgba(139, 69, 255, 0.3) !important;
  }

  .app-layout.dark .content-wrapper :global(.primary-button:hover),
  .app-layout.dark .content-wrapper :global(.send-button:hover) {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 35px rgba(139, 69, 255, 0.4) !important;
  }

  /* Dark theme tabs */
  .app-layout.dark .content-wrapper :global(.tab) {
    background: rgba(26, 26, 46, 0.7) !important;
    border: 1px solid rgba(139, 69, 255, 0.2) !important;
    color: #e5e7eb !important;
  }

  .app-layout.dark .content-wrapper :global(.tab.active) {
    background: linear-gradient(135deg, rgba(139, 69, 255, 0.3) 0%, rgba(255, 20, 147, 0.3) 100%) !important;
    border-color: rgba(139, 69, 255, 0.5) !important;
    box-shadow: 0 0 20px rgba(139, 69, 255, 0.3) !important;
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
