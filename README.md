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
```

These variables are optional but allow quick configuration changes without editing code.

### Memory Tools

If `mem0` and `sentence-transformers` are installed, additional memory-related
tools will be available for storing and retrieving information between sessions.
