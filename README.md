# Обновление README.md

## Сборка приложения

```bash
# Сборка для всех форматов по умолчанию
pnpm tauri build

# Сборка только DMG-пакета для macOS
pnpm tauri build --bundles dmg
```

После сборки исполняемые файлы будут доступны в папке `src-tauri/target/release/bundle/`.

## Установка на macOS

Если macOS блокирует открытие DMG или запуск приложения, выполните следующие шаги:

1. Щелкните правой кнопкой мыши (или Control + клик) по DMG-файлу в Finder
2. Выберите "Открыть" в контекстном меню
3. В появившемся диалоге нажмите "Открыть"

Альтернативный способ для запуска приложения:

1. После установки приложения щелкните правой кнопкой мыши (или Control + клик) по приложению в папке Applications
2. Выберите "Открыть" в контекстном меню
3. Подтвердите, что вы хотите открыть приложение, нажав "Открыть" в диалоговом окне

После первого запуска таким способом, в дальнейшем приложение будет открываться нормально.

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
