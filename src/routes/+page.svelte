<script lang="ts">
  import { onMount } from 'svelte';
  import { invoke } from '@tauri-apps/api/core';
  import { listen } from '@tauri-apps/api/event';

  let clipboardItems: string[] = [];
  let filteredItems: string[] = [];
  let searchQuery = '';
  let language: 'en' | 'ru' = 'en';

  const texts = {
    en: {
      title: 'Clipboard History',
      search: 'Search history...',
      empty: 'Clipboard history is empty or nothing found',
      copy: 'Copy'
    },
    ru: {
      title: 'История буфера обмена',
      search: 'Поиск в истории...',
      empty: 'История буфера обмена пуста или ничего не найдено',
      copy: 'Копировать'
    }
  } as const;

  function toggleLanguage() {
    language = language === 'en' ? 'ru' : 'en';
  }

  async function loadHistory() {
    try {
      clipboardItems = await invoke<string[]>('get_history');
      filterItems();
    } catch (error) {
      console.error('Ошибка загрузки истории:', error);
    }
  }

  function filterItems() {
    if (!searchQuery.trim()) {
      filteredItems = [...clipboardItems];
    } else {
      const query = searchQuery.toLowerCase();
      filteredItems = clipboardItems.filter(item => 
        item.toLowerCase().includes(query)
      );
    }
  }

  async function copyToClipboard(text: string) {
    try {
      await invoke('copy_to_clipboard', { text });
    } catch (error) {
      console.error('Ошибка копирования:', error);
    }
  }

  // Обработчик изменения поискового запроса
  function handleSearchInput() {
    filterItems();
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
  <div class="language-toggle">
    <button on:click={toggleLanguage}>
      {language === 'en' ? 'Русский' : 'English'}
    </button>
  </div>
  <h1>{texts[language].title}</h1>
  
  <div class="search-container">
    <input
      type="text"
      placeholder={texts[language].search}
      bind:value={searchQuery}
      on:input={handleSearchInput}
    />
  </div>
  
  <div class="history-container">
    {#if filteredItems.length === 0}
      <p>{texts[language].empty}</p>
    {:else}
      <ul>
        {#each filteredItems as item, i}
          <li>
            <div class="item-content">{item}</div>
            <button on:click={() => copyToClipboard(item)}>
              {texts[language].copy}
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
  
  .search-container {
    margin-bottom: 1rem;
  }
  
  input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
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

  .language-toggle {
    margin-bottom: 1rem;
  }
</style>
