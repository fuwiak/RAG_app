<script lang="ts">
  import RagPanel from './components/RagPanel.svelte';
  import FineTunePanel from './components/FineTunePanel.svelte';
  import PlaygroundPanel from './components/PlaygroundPanel.svelte';
  import { writable } from 'svelte/store';
  import { darkMode } from './lib/theme';

  type Panel = 'rag' | 'fine-tune' | 'playground';
  const panel = writable<Panel>('rag');
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-100">
  <header class="p-4 flex justify-between items-center border-b border-gray-200 dark:border-gray-700">
    <h1 class="text-xl font-bold">RAG App</h1>
    <div class="flex items-center gap-4">
      <nav class="flex gap-4">
        <button class="hover:underline" on:click={() => panel.set('rag')}>RAG</button>
        <button class="hover:underline" on:click={() => panel.set('fine-tune')}>Fine-tune</button>
        <button class="hover:underline" on:click={() => panel.set('playground')}>Playground</button>
      </nav>
      <label class="flex items-center gap-1 text-sm cursor-pointer">
        <input type="checkbox" bind:checked={$darkMode} class="form-checkbox" />
        Dark
      </label>
    </div>
  </header>
  <main class="p-4">
    {#if $panel === 'rag'}
      <RagPanel />
    {:else if $panel === 'fine-tune'}
      <FineTunePanel />
    {:else if $panel === 'playground'}
      <PlaygroundPanel />
    {/if}
  </main>
</div>
