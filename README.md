# Ayyy-AI
An experimental assistant that uses OpenAI-compatible models and a set of tools.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the assistant:

```bash
python main.py
```

The assistant will automatically load available tools and start an interactive session.

Environment variables can override the defaults in `AppConfig`:

```
AYYY_BASE_URL=http://localhost:1234/v1
AYYY_API_KEY=lm-studio-key
AYYY_MODEL=qwen2.5-vl-7b-instruct
AYYY_CONFIG_FILE=./config.yaml
```

These variables are optional but allow quick configuration changes without editing code.
If `AYYY_CONFIG_FILE` points to a YAML file, settings in that file override defaults.

### Memory Tools

If `mem0` and `sentence-transformers` are installed, additional memory-related
tools will be available for storing and retrieving information between sessions.

### Web Tools

A basic `fetch_url` tool allows retrieving the contents of a web page. Network access must be available for this tool to function.

### System Tools

`run_command` executes shell commands with an optional timeout. Use with care.

### Conversation History

The assistant saves conversation history to `chat_history.json` by default. Set the `AYYY_HISTORY_FILE` environment variable to change the path or delete the file to start fresh.
