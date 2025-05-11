<script lang="ts">
  import { onMount } from 'svelte';
  import { invoke } from '@tauri-apps/api/core';
  import { listen } from '@tauri-apps/api/event';

  let clipboardItems: string[] = [];

  async function loadHistory() {
    try {
      clipboardItems = await invoke<string[]>('get_history');
    } catch (error) {
      console.error('Ошибка загрузки истории:', error);
    }
  }

  async function copyToClipboard(text: string) {
    try {
      await invoke('copy_to_clipboard', { text });
    } catch (error) {
      console.error('Ошибка копирования:', error);
    }
  }

  onMount(() => {
    // Загружаем историю сразу
    loadHistory();
    
    // Переменная для хранения функции отписки
    let cleanup: (() => void) | undefined;
    
    // Настраиваем слушатель
    listen('clipboard-changed', (event) => {
      loadHistory();
    }).then(unsubscribe => {
      cleanup = unsubscribe;
    });
    
    // Возвращаем функцию очистки
    return () => cleanup && cleanup();
  });
</script>

<main>
  <h1>Clipboard History</h1>
  
  <div class="history-container">
    {#if clipboardItems.length === 0}
      <p>История буфера обмена пуста</p>
    {:else}
      <ul>
        {#each clipboardItems as item, i}
          <li>
            <div class="item-content">{item}</div>
            <button on:click={() => copyToClipboard(item)}>
              Копировать
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</main>

<style>
  main {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 1rem;
    max-width: 100%;
  }
  
  .history-container {
    margin-top: 1rem;
    max-height: 80vh;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 0.5rem;
  }
  
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  
  li {
    padding: 0.5rem;
    border-bottom: 1px solid #eee;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
  }
  
  .item-content {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  button {
    padding: 0.25rem 0.5rem;
    background: #0091ff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
  
  button:hover {
    background: #0070d1;
  }
</style>
