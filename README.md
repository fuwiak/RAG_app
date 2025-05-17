# README Update

## Building the Application

```bash
# Build for all formats by default
pnpm tauri build

# Build only the DMG package for macOS
pnpm tauri build --bundles dmg
```

After building, the executables will be available in the `src-tauri/target/release/bundle/` directory.

## Installation on macOS

If macOS blocks opening the DMG or launching the application, follow these steps:

1. Right click (or Control-click) the DMG file in Finder
2. Select "Open" from the context menu
3. In the dialog that appears, click "Open"

An alternative way to run the application:

1. After installation, right click (or Control-click) the application in the Applications folder
2. Select "Open" from the context menu
3. Confirm that you want to open the application by clicking "Open" in the dialog

After launching this way once, the application will open normally in the future.

```language=markdown:clipboard-history-tauri/README.md
# Clipboard History

An application for storing and managing clipboard history built with Tauri, SvelteKit, and TypeScript.

## Description

Clipboard History lets you save previously copied items and quickly restore them to the clipboard. The application works on all major operating systems thanks to Tauri.

## Recommended development tools

[VS Code](https://code.visualstudio.com/) + [Svelte](https://marketplace.visualstudio.com/items?itemName=svelte.svelte-vscode) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer).

## Requirements

- [Node.js](https://nodejs.org/) (version 16 or higher)
- [Rust](https://www.rust-lang.org/tools/install)
- [pnpm](https://pnpm.io/installation) (recommended) or npm/yarn

## Installing dependencies


pnpm install
```

## Running in development mode

```bash
pnpm tauri dev
```

## Building the application

```bash
pnpm tauri build
```

After building, the executables will be available in the `src-tauri/target/release` directory.

## Features

- Save clipboard history
- Copy items from the history back to the clipboard
- Automatically refresh when the clipboard changes
- Support for all major operating systems (Windows, macOS, Linux)
```
