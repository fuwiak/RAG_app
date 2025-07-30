import { writable } from 'svelte/store';

export const darkMode = writable(false);

if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('darkMode');
  darkMode.set(stored === 'true');
  darkMode.subscribe((val) => {
    localStorage.setItem('darkMode', val ? 'true' : 'false');
    document.documentElement.classList.toggle('dark', val);
  });
}
