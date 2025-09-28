# Ayyy-AI

An experimental AI assistant that uses OpenAI-compatible models and a comprehensive set of tools for various tasks.

## Features

- **Modern Python Architecture**: Built with async/await patterns and modern Python typing
- **Flexible Tool System**: Extensible tool registry supporting file operations, web requests, system commands, and more
- **Memory System**: Optional long-term memory using embedding-based storage (when mem0 is available)
- **Configuration Management**: Environment-based configuration with optional YAML file support
- **Rich Console Interface**: Beautiful terminal interface using the Rich library

## Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Run the assistant:**

```bash
python main.py
```

The assistant will automatically load available tools and start an interactive session.

## Configuration

Environment variables can override the defaults:

```bash
AYYY_BASE_URL=http://localhost:1234/v1     # LLM API base URL
AYYY_API_KEY=lm-studio-key                 # API key (often optional for local LLMs)
AYYY_MODEL=qwen2.5-vl-7b-instruct         # Model identifier
AYYY_CONFIG_FILE=./config.yaml             # Path to YAML config file
AYYY_HISTORY_FILE=chat_history.json        # Conversation history file
```

These variables are optional but allow quick configuration changes without editing code.
If `AYYY_CONFIG_FILE` points to a YAML file, settings in that file override defaults.

## Available Tools

### File Operations
- `read_file`: Read content from files with proper error handling
- `write_file`: Write content to files with UTF-8 encoding

### Web Tools
- `fetch_url`: Retrieve web page contents with modern async HTTP support
- `make_api_request`: Make HTTP API requests with customizable headers and methods

### System Tools
- `run_command`: Execute shell commands with timeout protection
- `run_python`: Execute Python code in a sandboxed environment

### Image Processing Tools
- `process_image`: Resize or convert images to grayscale (requires Pillow)

### Memory Tools (Optional)
If `sentence-transformers` is installed, additional memory-related tools will be available:
- `mem0_add`: Store information for later retrieval
- `mem0_retrieve`: Search stored memories by similarity
- `mem0_init`: Initialize memory system with custom settings

The memory system automatically falls back to a simple in-memory store if the full mem0 stack is not available.

## Conversation History

The assistant saves conversation history to `chat_history.json` by default. Set the `AYYY_HISTORY_FILE` environment variable to change the path or delete the file to start fresh.

## Architecture

- **Modern Type Annotations**: Full type hints using `from __future__ import annotations`
- **Error Handling**: Comprehensive error handling with graceful fallbacks
- **Optional Dependencies**: Tools gracefully handle missing optional dependencies
- **Async/Await**: Proper async patterns throughout the codebase
- **Rich Logging**: Structured logging with the Rich library

## Requirements

Core dependencies:
- `openai>=1.0` - OpenAI API client
- `pydantic>=2.0` - Data validation and settings
- `pydantic-settings>=2.0` - Settings management
- `rich>=13.0` - Terminal UI and logging
- `pyyaml>=6.0` - YAML configuration support
- `aiohttp>=3.8` - Async HTTP client

Optional dependencies:
- `pillow>=9.0` - Image processing
- `sentence-transformers>=2.0` - Local embeddings for memory features
