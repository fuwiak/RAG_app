<script lang="ts">
  import { invoke } from '@tauri-apps/api/core';

  type Mode = 'base' | 'fine' | 'rag';
  let message = '';
  let mode: Mode = 'base';
  let response = '';
  let retrieved = '';
  let loading = false;

  async function send() {
    if (!message.trim()) return;
    loading = true;
    try {
      const res = await invoke<any>('chat_with_documents', { query: message });
      response = res.message.content;
      retrieved = res.sources.map((s: any) => s.relevant_chunks.join('\n')).join('\n');
    } catch (e) {
      response = 'Error';
    }
    loading = false;
  }
</script>

<div class="space-y-4 max-w-xl">
  <h2 class="text-lg font-semibold">Playground</h2>
  <div class="flex gap-2">
    <select bind:value={mode} class="border p-2 rounded">
      <option value="base">Model base</option>
      <option value="fine">Model po fine-tuningu</option>
      <option value="rag">Model + RAG</option>
    </select>
    <input class="flex-1 border p-2 rounded" placeholder="Ask something" bind:value={message} />
    <button on:click={send} class="bg-blue-600 text-white px-4 py-2 rounded" disabled={loading}>Send</button>
  </div>
  {#if response}
    <div class="bg-gray-100 dark:bg-gray-800 p-3 rounded">
      <h3 class="font-semibold mb-1">Response</h3>
      <p>{response}</p>
    </div>
  {/if}
  {#if mode === 'rag' && retrieved}
    <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded">
      <h3 class="font-semibold mb-1">Retrieved context</h3>
      <pre class="whitespace-pre-wrap">{retrieved}</pre>
    </div>
  {/if}
</div>
