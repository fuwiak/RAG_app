import { defineConfig } from "vite";
import { svelte }       from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: "dist",          // where prod files land
    emptyOutDir: true
  }
});

server: {
  port: 5173
}