# RAG App

A Retrieval-Augmented Generation (RAG) application built with Tauri, SvelteKit, and TypeScript.

## Description

RAG App is a desktop application that combines document retrieval with AI-powered generation capabilities. It allows users to upload documents, create knowledge bases, and perform intelligent question-answering using retrieval-augmented generation techniques.

## Features

- **Document Upload & Processing**: Support for various document formats (PDF, TXT, DOCX)
- **Vector Database**: Efficient document embedding and similarity search
- **AI Integration**: Connect with popular LLM providers for intelligent responses
- **Interactive Chat Interface**: User-friendly chat interface for querying documents
- **Knowledge Base Management**: Organize and manage multiple document collections
- **Cross-Platform**: Works on Windows, macOS, and Linux thanks to Tauri

## Recommended Development Tools

[VS Code](https://code.visualstudio.com/) + [Svelte](https://marketplace.visualstudio.com/items?itemName=svelte.svelte-vscode) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)

## Requirements

- [Node.js](https://nodejs.org/) (version 18 or higher)
- [Rust](https://www.rust-lang.org/tools/install)
- [pnpm](https://pnpm.io/installation) (recommended) or npm/yarn

## Installation

### Installing Dependencies

```bash
pnpm install
```

### Development Mode

To run the application in development mode:

```bash
pnpm tauri dev
```

### Building the Application

To build the application for production:

```bash
# Build for all formats by default
pnpm tauri build

# Build only the DMG package for macOS
pnpm tauri build --bundles dmg
```

After building, the executables will be available in the `src-tauri/target/release/bundle/` directory.

## Installation on macOS

If macOS blocks opening the DMG or launching the application, follow these steps:

1. Right-click (or Control-click) the DMG file in Finder
2. Select "Open" from the context menu
3. In the dialog that appears, click "Open"

Alternative method to run the application:

1. After installation, right-click (or Control-click) the application in the Applications folder
2. Select "Open" from the context menu
3. Confirm that you want to open the application by clicking "Open" in the dialog

After launching this way once, the application will open normally in the future.

## Technology Stack

- **Frontend**: SvelteKit + TypeScript
- **Backend**: Rust (Tauri)
- **UI Framework**: Svelte
- **Build Tool**: Vite
- **Package Manager**: pnpm

## Getting Started

1. Clone the repository
2. Install dependencies with `pnpm install`
3. Run in development mode with `pnpm tauri dev`
4. Upload your documents and start asking questions!

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).
