# Ayyy-AI

An experimental AI assistant powered by OpenAI-compatible models with extensible tooling capabilities.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Start the assistant:

```bash
python main.py
```

The assistant automatically loads available tools and initiates an interactive session.

## Configuration

Environment variables can be used to override the default settings in `AppConfig`:

| Variable | Description | Default |
|----------|-------------|---------|
| `AYYY_BASE_URL` | API endpoint URL | `http://localhost:1234/v1` |
| `AYYY_API_KEY` | API authentication key | `lm-studio-key` |
| `AYYY_MODEL` | Model identifier | `qwen2.5-vl-7b-instruct` |
| `AYYY_CONFIG_FILE` | Path to YAML configuration file | `./config.yaml` |

All environment variables are optional and provide a convenient way to adjust configuration without modifying code. If `AYYY_CONFIG_FILE` points to a valid YAML file, its settings take precedence over defaults.

## Available Tools

### Memory Tools

When `mem0` and `sentence-transformers` are installed, additional memory-related tools become available for storing and retrieving information across sessions.

### Web Tools

The `fetch_url` tool retrieves the contents of a web page. Network access is required for this functionality.

### System Tools

The `run_command` tool executes shell commands with an optional timeout. Exercise caution when using this tool.

## Conversation History

Conversation history is saved to `chat_history.json` by default. To customize the storage location, set the `AYYY_HISTORY_FILE` environment variable. Delete the history file to start a new session.
