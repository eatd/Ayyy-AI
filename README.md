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

The assistant will load any available tools and start an interactive session.

### Memory Tools

If `mem0` and `sentence-transformers` are installed, additional memory-related
tools will be available for storing and retrieving information between sessions.
