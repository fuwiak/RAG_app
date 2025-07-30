<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';
  import { listen } from '@tauri-apps/api/event';
  import { onDestroy } from 'svelte';

  let datasetPath = '';
  let modelName = '';
  let logs: string[] = [];
  let running = false;
  let unlisten: (() => void) | undefined;

  async function startFineTune() {
    running = true;
    logs = [];
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

<div class="space-y-4">
  <h2 class="text-lg font-semibold">Fine-tune Model</h2>
  <div class="flex flex-col gap-2 max-w-sm">
    <input type="file" on:change={handleFileChange} class="border p-2 rounded" />
    <input type="text" placeholder="Model name" bind:value={modelName} class="border p-2 rounded" />
    <button class="bg-blue-600 text-white px-4 py-2 rounded" on:click={startFineTune} disabled={running}>Start</button>
  </div>
  <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded h-40 overflow-auto">{logs.join('\n')}</pre>
</div>
