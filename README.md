# Обновление README.md

## Сборка приложения

```bash
# Сборка для всех форматов по умолчанию
pnpm tauri build

# Сборка только DMG-пакета для macOS
pnpm tauri build --bundles dmg
```

После сборки исполняемые файлы будут доступны в папке `src-tauri/target/release/bundle/`.

```language=markdown:clipboard-history-tauri/README.md
# Clipboard History

Приложение для хранения и управления историей буфера обмена, построенное с использованием Tauri, SvelteKit и TypeScript.

## Описание

Clipboard History позволяет сохранять историю скопированных элементов и быстро восстанавливать их в буфер обмена. Приложение работает на всех основных операционных системах благодаря Tauri.

## Рекомендуемые инструменты для разработки

[VS Code](https://code.visualstudio.com/) + [Svelte](https://marketplace.visualstudio.com/items?itemName=svelte.svelte-vscode) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer).

## Требования

- [Node.js](https://nodejs.org/) (версия 16 или выше)
- [Rust](https://www.rust-lang.org/tools/install)
- [pnpm](https://pnpm.io/installation) (рекомендуется) или npm/yarn

## Установка зависимостей

```bash
pnpm install
```

## Запуск в режиме разработки

```bash
pnpm tauri dev
```

## Сборка приложения

```bash
pnpm tauri build
```

После сборки исполняемые файлы будут доступны в папке `src-tauri/target/release`.

## Функциональность

- Сохранение историй буфера обмена
- Копирование элементов из истории обратно в буфер обмена
- Автоматическое обновление при изменении буфера обмена
- Поддержка всех основных операционных систем (Windows, macOS, Linux)
```
