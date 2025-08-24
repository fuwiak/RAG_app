<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';
  import { listen } from '@tauri-apps/api/event';
  import { onMount, onDestroy } from 'svelte';
  import { t } from '../lib/i18n';
  
  let selectedTab: 'overview' | 'system' | 'tokens' | 'logs' | 'metrics' = 'overview';
  
  // System Monitoring
  interface SystemStats {
    cpu_usage: number;
    memory_usage: number;
    memory_total: number;
    disk_usage: number;
    disk_total: number;
    gpu_usage?: number;
    gpu_memory?: number;
    network_rx: number;
    network_tx: number;
    temperature?: number;
  }
  
  // Token Usage
  interface TokenUsage {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cost_estimate: number;
    timestamp: string;
  }
  
  // Training Progress
  interface TrainingProgress {
    epoch: number;
    loss: number;
    accuracy: number;
    learning_rate: number;
    elapsed_time: number;
    estimated_remaining: number;
    status: 'idle' | 'training' | 'completed' | 'error';
  }
  
  // Logs
  interface LogEntry {
    id: string;
    timestamp: string;
    level: 'info' | 'warn' | 'error' | 'debug';
    component: string;
    message: string;
  }
  
  // State
  let systemStats: SystemStats = {
    cpu_usage: 0,
    memory_usage: 0,
    memory_total: 0,
    disk_usage: 0,
    disk_total: 0,
    network_rx: 0,
    network_tx: 0
  };
  
  let tokenUsage: TokenUsage[] = [];
  let totalTokensToday = { input: 0, output: 0, cost: 0 };
  let trainingProgress: TrainingProgress = {
    epoch: 0,
    loss: 0,
    accuracy: 0,
    learning_rate: 0,
    elapsed_time: 0,
    estimated_remaining: 0,
    status: 'idle'
  };
  
  let logs: LogEntry[] = [];
  let isMonitoring = false;
  let monitoringInterval: number;
  let unlistenSystem: (() => void) | undefined;
  let unlistenTraining: (() => void) | undefined;
  let unlistenTokens: (() => void) | undefined;
  let unlistenLogs: (() => void) | undefined;
  
  // Chart data for metrics visualization
  let cpuHistory: number[] = [];
  let memoryHistory: number[] = [];
  let tokenHistory: {time: string, tokens: number}[] = [];
  
  async function startMonitoring() {
    isMonitoring = true;
    
    // System stats listener
    unlistenSystem = await listen<SystemStats>('system_stats', (event) => {
      systemStats = event.payload;
      updateChartData();
    });
    
    // Training progress listener
    unlistenTraining = await listen<TrainingProgress>('training_progress', (event) => {
      trainingProgress = event.payload;
    });
    
    // Token usage listener
    unlistenTokens = await listen<TokenUsage>('token_usage', (event) => {
      tokenUsage = [event.payload, ...tokenUsage.slice(0, 99)]; // Keep last 100
      updateTokenTotals();
    });
    
    // Logs listener
    unlistenLogs = await listen<LogEntry>('log_entry', (event) => {
      logs = [event.payload, ...logs.slice(0, 499)]; // Keep last 500
    });
    
    // Start system monitoring
    try {
      await invoke('start_system_monitoring');
    } catch (error) {
      console.error('Failed to start system monitoring:', error);
    }
    
    // Periodic stats update
    monitoringInterval = setInterval(async () => {
      try {
        const stats = await invoke<SystemStats>('get_system_stats');
        systemStats = stats;
        updateChartData();
      } catch (error) {
        console.error('Failed to get system stats:', error);
      }
    }, 1000);
  }
  
  async function stopMonitoring() {
    isMonitoring = false;
    
    if (monitoringInterval) {
      clearInterval(monitoringInterval);
    }
    
    if (unlistenSystem) unlistenSystem();
    if (unlistenTraining) unlistenTraining();
    if (unlistenTokens) unlistenTokens();
    if (unlistenLogs) unlistenLogs();
    
    try {
      await invoke('stop_system_monitoring');
    } catch (error) {
      console.error('Failed to stop system monitoring:', error);
    }
  }
  
  function updateChartData() {
    cpuHistory = [...cpuHistory.slice(-29), systemStats.cpu_usage]; // Keep last 30 points
    memoryHistory = [...memoryHistory.slice(-29), systemStats.memory_usage];
  }
  
  function updateTokenTotals() {
    const today = new Date().toDateString();
    const todayUsage = tokenUsage.filter(usage => 
      new Date(usage.timestamp).toDateString() === today
    );
    
    totalTokensToday = todayUsage.reduce((acc, usage) => ({
      input: acc.input + usage.input_tokens,
      output: acc.output + usage.output_tokens,
      cost: acc.cost + usage.cost_estimate
    }), { input: 0, output: 0, cost: 0 });
  }
  
  async function clearLogs() {
    logs = [];
    try {
      await invoke('clear_logs');
    } catch (error) {
      console.error('Failed to clear logs:', error);
    }
  }
  
  async function exportLogs() {
    try {
      await invoke('export_logs');
      addLog('info', 'Monitor', 'Logs exported successfully');
    } catch (error) {
      addLog('error', 'Monitor', `Failed to export logs: ${error}`);
    }
  }
  
  function addLog(level: 'info' | 'warn' | 'error' | 'debug', component: string, message: string) {
    const logEntry: LogEntry = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      level,
      component,
      message
    };
    logs = [logEntry, ...logs.slice(0, 499)];
  }
  
  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
  
  function formatTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  
  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4
    }).format(amount);
  }
  
  function getLogIcon(level: string): string {
    switch (level) {
      case 'error': return '❌';
      case 'warn': return '⚠️';
      case 'info': return 'ℹ️';
      case 'debug': return '🔍';
      default: return '📝';
    }
  }
  
  function getStatusColor(status: string): string {
    switch (status) {
      case 'training': return '#3b82f6';
      case 'completed': return '#10b981';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  }
  
  onMount(() => {
    startMonitoring();
    addLog('info', 'Monitor', 'Monitoring system started');
  });
  
  onDestroy(() => {
    stopMonitoring();
  });
</script>

<main>
  <div class="app-container">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <h1 class="app-title nav-text-transition">📊 {$t.monitor_title}</h1>
        <p class="app-subtitle nav-description-transition">{$t.monitor_subtitle}</p>
      </div>
      
      <!-- Navigation tabs -->
      <nav class="tabs">
        <button 
          class="tab {selectedTab === 'overview' ? 'active' : ''}"
          on:click={() => selectedTab = 'overview'}
        >
          📋 <span class="nav-text-transition">{$t.monitor_overview}</span>
        </button>
        <button 
          class="tab {selectedTab === 'system' ? 'active' : ''}"
          on:click={() => selectedTab = 'system'}
        >
          🖥️ <span class="nav-text-transition">{$t.monitor_system}</span>
        </button>
        <button 
          class="tab {selectedTab === 'tokens' ? 'active' : ''}"
          on:click={() => selectedTab = 'tokens'}
        >
          🔢 <span class="nav-text-transition">{$t.monitor_tokens}</span>
        </button>
        <button 
          class="tab {selectedTab === 'metrics' ? 'active' : ''}"
          on:click={() => selectedTab = 'metrics'}
        >
          📈 <span class="nav-text-transition">{$t.monitor_metrics}</span>
        </button>
        <button 
          class="tab {selectedTab === 'logs' ? 'active' : ''}"
          on:click={() => selectedTab = 'logs'}
        >
          📝 <span class="nav-text-transition">{$t.monitor_logs} ({logs.length})</span>
        </button>
      </nav>
    </header>

    <!-- Main content -->
    <div class="main-content">
      <!-- Overview Tab -->
      {#if selectedTab === 'overview'}
        <div class="overview-container">
          <div class="overview-grid">
            <!-- System Status -->
            <div class="status-card">
              <div class="status-header">
                <h3>🖥️ System Status</h3>
                <span class="status-indicator {isMonitoring ? 'active' : 'inactive'}">
                  {isMonitoring ? '🟢 Active' : '🔴 Inactive'}
                </span>
              </div>
              <div class="status-metrics">
                <div class="metric">
                  <span class="metric-label">CPU</span>
                  <span class="metric-value">{systemStats.cpu_usage.toFixed(1)}%</span>
                  <div class="metric-bar">
                    <div class="metric-fill" style="width: {systemStats.cpu_usage}%"></div>
                  </div>
                </div>
                <div class="metric">
                  <span class="metric-label">Memory</span>
                  <span class="metric-value">{((systemStats.memory_usage / systemStats.memory_total) * 100).toFixed(1)}%</span>
                  <div class="metric-bar">
                    <div class="metric-fill" style="width: {(systemStats.memory_usage / systemStats.memory_total) * 100}%"></div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Training Status -->
            <div class="status-card">
              <div class="status-header">
                <h3>🎯 Training Status</h3>
                <span class="training-status" style="color: {getStatusColor(trainingProgress.status)}">
                  {trainingProgress.status.toUpperCase()}
                </span>
              </div>  
              <div class="training-info">
                {#if trainingProgress.status === 'training'}
                  <div class="training-metric">
                    <span>Epoch: {trainingProgress.epoch}</span>
                    <span>Loss: {trainingProgress.loss.toFixed(4)}</span>
                  </div>
                  <div class="training-metric">
                    <span>Accuracy: {(trainingProgress.accuracy * 100).toFixed(2)}%</span>
                    <span>ETA: {formatTime(trainingProgress.estimated_remaining)}</span>
                  </div>
                {:else}
                  <p class="no-training">No active training session</p>
                {/if}
              </div>
            </div>
            
            <!-- Token Usage Today -->
            <div class="status-card">
              <div class="status-header">
                <h3>🔢 Today's Usage</h3>
                <span class="cost-estimate">
                  {formatCurrency(totalTokensToday.cost)}
                </span>
              </div>
              <div class="token-stats">
                <div class="token-stat">
                  <span class="token-label">Input</span>
                  <span class="token-count">{totalTokensToday.input.toLocaleString()}</span>
                </div>
                <div class="token-stat">
                  <span class="token-label">Output</span>
                  <span class="token-count">{totalTokensToday.output.toLocaleString()}</span>
                </div>
              </div>
            </div>
            
            <!-- Recent Activity -->
            <div class="status-card activity-card">
              <div class="status-header">
                <h3>📈 Recent Activity</h3>
                <button class="refresh-btn" on:click={() => location.reload()}>🔄</button>
              </div>
              <div class="activity-list">
                {#each logs.slice(0, 5) as log}
                  <div class="activity-item">
                    <span class="activity-icon">{getLogIcon(log.level)}</span>
                    <span class="activity-text">{log.message}</span>
                    <span class="activity-time">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
        
      <!-- System Tab -->
      {:else if selectedTab === 'system'}
        <div class="system-container">
          <div class="system-grid">
            <div class="system-card">
              <h3>🖥️ CPU Usage</h3>
              <div class="chart-container">
                <div class="chart-header">
                  <span class="chart-value">{systemStats.cpu_usage.toFixed(1)}%</span>
                  <span class="chart-label">Current</span>
                </div>
                <div class="mini-chart">
                  {#each cpuHistory as point, i}
                    <div 
                      class="chart-bar" 
                      style="height: {point}%; left: {(i / cpuHistory.length) * 100}%"
                    ></div>
                  {/each}
                </div>
              </div>
            </div>
            
            <div class="system-card">
              <h3>💾 Memory Usage</h3>
              <div class="chart-container">
                <div class="chart-header">
                  <span class="chart-value">{formatBytes(systemStats.memory_usage)}</span>
                  <span class="chart-label">of {formatBytes(systemStats.memory_total)}</span>
                </div>
                <div class="memory-ring">
                  <svg viewBox="0 0 100 100" class="ring-chart">
                    <circle 
                      cx="50" cy="50" r="45" 
                      fill="none" 
                      stroke="#e5e7eb" 
                      stroke-width="8"
                    />
                    <circle 
                      cx="50" cy="50" r="45" 
                      fill="none" 
                      stroke="#3b82f6" 
                      stroke-width="8"
                      stroke-dasharray="{(systemStats.memory_usage / systemStats.memory_total) * 283} 283"
                      stroke-dashoffset="0"
                      transform="rotate(-90 50 50)"
                    />
                  </svg>
                  <div class="ring-center">
                    {((systemStats.memory_usage / systemStats.memory_total) * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>
            
            <div class="system-card">
              <h3>💿 Disk Usage</h3>
              <div class="disk-info">
                <div class="disk-bar">
                  <div 
                    class="disk-fill" 
                    style="width: {(systemStats.disk_usage / systemStats.disk_total) * 100}%"
                  ></div>
                </div>
                <div class="disk-stats">
                  <span>Used: {formatBytes(systemStats.disk_usage)}</span>
                  <span>Free: {formatBytes(systemStats.disk_total - systemStats.disk_usage)}</span>
                </div>
              </div>
            </div>
            
            <div class="system-card">
              <h3>🌐 Network</h3>
              <div class="network-stats">
                <div class="network-stat">
                  <span class="network-icon">📥</span>
                  <div class="network-info">
                    <span class="network-label">Download</span>
                    <span class="network-value">{formatBytes(systemStats.network_rx)}/s</span>
                  </div>
                </div>
                <div class="network-stat">
                  <span class="network-icon">📤</span>
                  <div class="network-info">
                    <span class="network-label">Upload</span>
                    <span class="network-value">{formatBytes(systemStats.network_tx)}/s</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
      <!-- Tokens Tab -->
      {:else if selectedTab === 'tokens'}
        <div class="tokens-container">
          <div class="tokens-summary">
            <div class="summary-card">
              <h3>📊 Usage Summary</h3>
              <div class="summary-stats">
                <div class="summary-stat">
                  <span class="stat-value">{totalTokensToday.input.toLocaleString()}</span>
                  <span class="stat-label">Input Tokens Today</span>
                </div>
                <div class="summary-stat">
                  <span class="stat-value">{totalTokensToday.output.toLocaleString()}</span>
                  <span class="stat-label">Output Tokens Today</span>
                </div>
                <div class="summary-stat">
                  <span class="stat-value">{formatCurrency(totalTokensToday.cost)}</span>
                  <span class="stat-label">Estimated Cost Today</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="tokens-history">
            <h3>📈 Token Usage History</h3>
            <div class="history-list">
              {#each tokenUsage.slice(0, 20) as usage}
                <div class="history-item">
                  <div class="history-time">
                    {new Date(usage.timestamp).toLocaleString()}
                  </div>
                  <div class="history-stats">
                    <span class="token-in">📥 {usage.input_tokens}</span>
                    <span class="token-out">📤 {usage.output_tokens}</span>
                    <span class="token-cost">{formatCurrency(usage.cost_estimate)}</span>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        </div>
        
      <!-- Metrics Tab -->
      {:else if selectedTab === 'metrics'}
        <div class="metrics-container">
          <div class="metrics-header">
            <h2>📈 Performance Metrics</h2>
            <p>Real-time visualization of system performance</p>
          </div>
          
          <div class="metrics-grid">
            <div class="metric-chart">
              <h3>CPU Usage Over Time</h3>
              <div class="line-chart">
                <svg viewBox="0 0 300 100" class="chart-svg">
                  {#each cpuHistory as point, i}
                    {#if i > 0}
                      <line
                        x1="{((i-1) / (cpuHistory.length-1)) * 280 + 10}"
                        y1="{90 - (cpuHistory[i-1] * 0.8)}"
                        x2="{(i / (cpuHistory.length-1)) * 280 + 10}"
                        y2="{90 - (point * 0.8)}"
                        stroke="#3b82f6"
                        stroke-width="2"
                      />
                    {/if}
                  {/each}
                </svg>
              </div>
            </div>
            
            <div class="metric-chart">
              <h3>Memory Usage Over Time</h3>
              <div class="line-chart">
                <svg viewBox="0 0 300 100" class="chart-svg">
                  {#each memoryHistory as point, i}
                    {#if i > 0}
                      <line
                        x1="{((i-1) / (memoryHistory.length-1)) * 280 + 10}"
                        y1="{90 - ((memoryHistory[i-1] / systemStats.memory_total) * 100 * 0.8)}"
                        x2="{(i / (memoryHistory.length-1)) * 280 + 10}"
                        y2="{90 - ((point / systemStats.memory_total) * 100 * 0.8)}"
                        stroke="#10b981"
                        stroke-width="2"
                      />
                    {/if}
                  {/each}
                </svg>
              </div>
            </div>
          </div>
        </div>
        
      <!-- Logs Tab -->
      {:else if selectedTab === 'logs'}
        <div class="logs-container">
          <div class="logs-header">
            <div class="logs-title">
              <h2>📝 System Logs</h2>
              <p>Real-time application logging</p>
            </div>
            <div class="logs-actions">
              <button class="action-button" on:click={clearLogs}>
                🗑️ Clear Logs
              </button>
              <button class="action-button" on:click={exportLogs}>
                💾 Export Logs
              </button>
            </div>
          </div>
          
          <div class="logs-list">
            {#each logs as log}
              <div class="log-entry log-{log.level}">
                <span class="log-icon">{getLogIcon(log.level)}</span>
                <span class="log-time">{new Date(log.timestamp).toLocaleTimeString()}</span>
                <span class="log-component">[{log.component}]</span>
                <span class="log-message">{log.message}</span>
              </div>
            {/each}
            
            {#if logs.length === 0}
              <div class="empty-logs">
                <div class="empty-icon">📝</div>
                <h3>No logs yet</h3>
                <p>System logs will appear here as the application runs</p>
              </div>
            {/if}
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

  /* Overview Styles */
  .overview-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
  }

  .status-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .status-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .status-header h3 {
    margin: 0;
    color: #333;
    font-size: 1.1rem;
  }

  .status-indicator {
    font-size: 0.9rem;
    font-weight: 600;
    padding: 0.25rem 0.75rem;
    border-radius: 15px;
  }

  .status-indicator.active {
    background: #d1fae5;
    color: #065f46;
  }

  .status-indicator.inactive {
    background: #fee2e2;
    color: #991b1b;
  }

  .status-metrics {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .metric {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .metric-label {
    font-size: 0.9rem;
    color: #666;
    font-weight: 500;
  }

  .metric-value {
    font-size: 1.2rem;
    font-weight: 600;
    color: #333;
  }

  .metric-bar {
    height: 8px;
    background: #e5e7eb;
    border-radius: 4px;
    overflow: hidden;
  }

  .metric-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #1d4ed8);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .training-status {
    font-size: 0.9rem;
    font-weight: 600;
    padding: 0.25rem 0.75rem;
    border-radius: 15px;
    background: rgba(0, 0, 0, 0.1);
  }

  .training-info {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .training-metric {
    display: flex;
    justify-content: space-between;
    font-size: 0.9rem;
  }

  .no-training {
    color: #666;
    font-style: italic;
    margin: 0;
  }

  .cost-estimate {
    font-size: 1.1rem;
    font-weight: 600;
    color: #059669;
  }

  .token-stats {
    display: flex;
    justify-content: space-between;
  }

  .token-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
  }

  .token-label {
    font-size: 0.8rem;
    color: #666;
    text-transform: uppercase;
    font-weight: 500;
  }

  .token-count {
    font-size: 1.1rem;
    font-weight: 600;
    color: #333;
  }

  .activity-card {
    grid-column: span 2;
  }

  .activity-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .activity-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem;
    background: #f8f9fa;
    border-radius: 8px;
  }

  .activity-icon {
    font-size: 1rem;
  }

  .activity-text {
    flex: 1;
    font-size: 0.9rem;
    color: #333;
  }

  .activity-time {
    font-size: 0.8rem;
    color: #666;
  }

  .refresh-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1rem;
    padding: 0.25rem;
    border-radius: 4px;
    transition: background 0.2s;
  }

  .refresh-btn:hover {
    background: rgba(0, 0, 0, 0.1);
  }

  /* System Styles */
  .system-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .system-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 2rem;
  }

  .system-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .system-card h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.1rem;
  }

  .chart-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .chart-header {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .chart-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: #333;
  }

  .chart-label {
    font-size: 0.9rem;
    color: #666;
  }

  .mini-chart {
    height: 60px;
    position: relative;
    background: #f8f9fa;
    border-radius: 8px;
    overflow: hidden;
  }

  .chart-bar {
    position: absolute;
    bottom: 0;
    width: calc(100% / 30);
    background: linear-gradient(180deg, #3b82f6, #1d4ed8);
    border-radius: 2px 2px 0 0;
    transition: height 0.3s ease;
  }

  .memory-ring {
    position: relative;
    width: 120px;
    height: 120px;
    margin: 0 auto;
  }

  .ring-chart {
    width: 100%;
    height: 100%;
  }

  .ring-center {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 1.2rem;
    font-weight: 600;
    color: #333;
  }

  .disk-info {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .disk-bar {
    height: 12px;
    background: #e5e7eb;
    border-radius: 6px;
    overflow: hidden;
  }

  .disk-fill {
    height: 100%;
    background: linear-gradient(90deg, #10b981, #059669);
    border-radius: 6px;
    transition: width 0.3s ease;
  }

  .disk-stats {
    display: flex;
    justify-content: space-between;
    font-size: 0.9rem;
    color: #666;
  }

  .network-stats {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .network-stat {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .network-icon {
    font-size: 1.5rem;
  }

  .network-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .network-label {
    font-size: 0.9rem;
    color: #666;
  }

  .network-value {
    font-size: 1.1rem;
    font-weight: 600;
    color: #333;
  }

  /* Tokens Styles */
  .tokens-container {
    max-width: 1000px;
    margin: 0 auto;
  }

  .tokens-summary {
    margin-bottom: 2rem;
  }

  .summary-card {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .summary-card h3 {
    margin: 0 0 1.5rem 0;
    color: #333;
    font-size: 1.3rem;
  }

  .summary-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 2rem;
  }

  .summary-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .stat-value {
    font-size: 2rem;
    font-weight: 600;
    color: #333;
  }

  .stat-label {
    font-size: 0.9rem;
    color: #666;
    text-transform: uppercase;
    font-weight: 500;
    text-align: center;
  }

  .tokens-history {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .tokens-history h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.2rem;
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-height: 500px;
    overflow-y: auto;
  }

  .history-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
  }

  .history-time {
    font-size: 0.9rem;
    color: #666;
    font-weight: 500;
  }

  .history-stats {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .token-in, .token-out {
    font-size: 0.9rem;
    color: #333;
  }

  .token-cost {
    font-size: 0.9rem;
    font-weight: 600;
    color: #059669;
  }

  /* Metrics Styles */
  .metrics-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .metrics-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .metrics-header h2 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 1.8rem;
  }

  .metrics-header p {
    color: #666;
    margin: 0;
    font-size: 1.1rem;
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
  }

  .metric-chart {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .metric-chart h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.1rem;
  }

  .line-chart {
    height: 200px;
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1rem;
  }

  .chart-svg {
    width: 100%;
    height: 100%;
  }

  /* Logs Styles */
  .logs-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .logs-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 2rem;
  }

  .logs-title h2 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 1.8rem;
  }

  .logs-title p {
    color: #666;
    margin: 0;
    font-size: 1.1rem;
  }

  .logs-actions {
    display: flex;
    gap: 1rem;
  }

  .action-button {
    background: #667eea;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.3s ease;
  }

  .action-button:hover {
    background: #5a67d8;
    transform: translateY(-2px);
  }

  .logs-list {
    background: white;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    max-height: 600px;
    overflow-y: auto;
  }

  .log-entry {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem 1.5rem;
    border-bottom: 1px solid #f3f4f6;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.9rem;
  }

  .log-entry:last-child {
    border-bottom: none;
  }

  .log-entry.log-error {
    background: #fef2f2;
    border-left: 4px solid #ef4444;
  }

  .log-entry.log-warn {
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
  }

  .log-entry.log-info {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
  }

  .log-entry.log-debug {
    background: #f0fdf4;
    border-left: 4px solid #10b981;
  }

  .log-icon {
    font-size: 1rem;
  }

  .log-time {
    color: #666;
    font-weight: 500;
    min-width: 80px;
  }

  .log-component {
    color: #3b82f6;
    font-weight: 600;
    min-width: 100px;
  }

  .log-message {
    flex: 1;
    color: #333;
  }

  .empty-logs {
    text-align: center;
    padding: 4rem 2rem;
    color: #666;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .empty-logs h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.5rem;
  }

  .empty-logs p {
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
    
    .overview-grid,
    .system-grid,
    .metrics-grid {
      grid-template-columns: 1fr;
    }

    .activity-card {
      grid-column: span 1;
    }
    
    .logs-header {
      flex-direction: column;
      gap: 1rem;
      align-items: stretch;
    }

    .logs-actions {
      flex-direction: column;
    }

    .summary-stats {
      grid-template-columns: 1fr;
    }

    .history-item {
      flex-direction: column;
      gap: 0.5rem;
      align-items: flex-start;
    }
  }
</style> 