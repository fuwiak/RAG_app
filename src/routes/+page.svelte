<script lang="ts">
  import { onMount } from 'svelte';
  import { invoke } from '@tauri-apps/api/core';
  import { listen } from '@tauri-apps/api/event';

  let clipboardItems: string[] = [];
  let filteredItems: string[] = [];
  let searchQuery = '';
  let language: 'en' | 'ru' = 'en';
  let savedItems: string[] = [];
  let savedInput = '';
  let terminalItems: string[] = [];
  let trainingLogs: string[] = [];

  const texts = {
    en: {
      historyTitle: 'RAG Documents',
      savedTitle: 'Saved Items',
      terminalTitle: 'Terminal History',
      search: 'Search history...',
      empty: 'No documents uploaded or nothing found',
      copy: 'Copy',
      add: 'Add',
      remove: 'Remove'
    },
    ru: {
      historyTitle: 'История буфера обмена',
      savedTitle: 'Сохранённое',
      terminalTitle: 'История терминала',
      search: 'Поиск в истории...',
      empty: 'История буфера обмена пуста или ничего не найдено',
      copy: 'Копировать',
      add: 'Добавить',
      remove: 'Удалить'
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

  async function loadSaved() {
    try {
      savedItems = await invoke<string[]>('get_saved');
    } catch (error) {
      console.error('Ошибка загрузки избранного:', error);
    }
  }

  async function addToSaved() {
    const text = savedInput.trim();
    if (!text) return;
    try {
      await invoke('add_saved', { text });
      savedInput = '';
      loadSaved();
    } catch (error) {
      console.error('Ошибка сохранения:', error);
    }
  }

  async function removeSavedItem(text: string) {
    try {
      await invoke('remove_saved', { text });
      loadSaved();
    } catch (error) {
      console.error('Ошибка удаления:', error);
    }
  }

  async function loadTerminalHistory() {
    try {
      terminalItems = await invoke<string[]>('get_terminal_history');
    } catch (error) {
      console.error('Ошибка загрузки истории терминала:', error);
    }
  }

  async function startFineTune() {
    try {
      await invoke('start_fine_tune', { config: 'default' });
    } catch (error) {
      console.error('Failed to start training:', error);
    }
  }

  // Обработчик изменения поискового запроса
  function handleSearchInput() {
    filterItems();
  }

  onMount(() => {
    // Загружаем историю сразу
    loadHistory();
    loadSaved();
    loadTerminalHistory();
    
    // Переменная для хранения функции отписки
    let cleanup: (() => void) | undefined;
    
    // Настраиваем слушатель
    listen('clipboard-changed', (event) => {
      loadHistory();
    }).then(unsubscribe => {
      cleanup = unsubscribe;
    });

    listen('training_progress', (event) => {
      trainingLogs = [...trainingLogs, String(event.payload)];
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
  <div class="containers">
    <div class="history-section">
      <h1>{texts[language].historyTitle}</h1>
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
    </div>

    <div class="saved-section">
      <h1>{texts[language].savedTitle}</h1>
      <div class="add-container">
        <input
          type="text"
          placeholder={texts[language].add}
          bind:value={savedInput}
        />
        <button on:click={addToSaved}>{texts[language].add}</button>
      </div>
      <div class="saved-container">
        {#if savedItems.length === 0}
          <p>{texts[language].empty}</p>
        {:else}
          <ul>
            {#each savedItems as item}
              <li>
                <div class="item-content">{item}</div>
                <button on:click={() => copyToClipboard(item)}>
                  {texts[language].copy}
                </button>
                <button on:click={() => removeSavedItem(item)}>
                  {texts[language].remove}
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
    <div class="terminal-section">
      <h1>{texts[language].terminalTitle}</h1>
      <div class="terminal-container">
        {#if terminalItems.length === 0}
          <p>{texts[language].empty}</p>
        {:else}
          <ul>
            {#each terminalItems as item}
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
    </div>
    <div class="training-section">
      <h1>Training Logs</h1>
      <button on:click={startFineTune}>Start Training</button>
      <div class="training-container">
        <ul>
          {#each trainingLogs as log}
            <li>{log}</li>
          {/each}
        </ul>
      </div>
    </div>
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

  .containers {
    display: flex;
    gap: 1rem;
  }

  .history-section,
  .saved-section,
  .terminal-section {
    flex: 1 1 33%;
    max-width: 33%;
  }

  .saved-container {
    margin-top: 1rem;
    max-height: 80vh;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 0.5rem;
  }

  .terminal-container {
    margin-top: 1rem;
    max-height: 80vh;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 0.5rem;
  }

  .training-section {
    flex: 1 1 100%;
    margin-top: 1rem;
  }

  .training-container {
    margin-top: 0.5rem;
    max-height: 40vh;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 0.5rem;
  }

  .add-container {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }
</style>
