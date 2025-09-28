from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
import os
import asyncio
from datetime import datetime

from .base import ToolDefinition

# Check for optional dependencies
MEM0_AVAILABLE = False
SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass

try:
    # Import mem0 components (if available)
    from mem0.async_memory import AsyncMemory
    from mem0.embeddings import OpenAIEmbeddingModel, CustomEmbeddingModel
    from mem0.llm import OpenAILLM
    from mem0.storage import ChromaVectorStore
    MEM0_AVAILABLE = True
except ImportError:
    pass


# Simple fallback memory store for when mem0 is not available
class SimpleMemoryStore:
    """Simple in-memory store for basic memory functionality."""
    def __init__(self):
        self.memories: List[Dict[str, Any]] = []
        self.next_id = 1
    
    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        memory_id = str(self.next_id)
        self.next_id += 1
        
        memory = {
            'id': memory_id,
            'text': content,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.memories.append(memory)
        return memory_id
    
    async def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # Simple text matching for retrieval
        query_lower = query.lower()
        matches = []
        
        for memory in self.memories:
            if query_lower in memory['text'].lower():
                matches.append(memory)
        
        return matches[:limit]
    
    async def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        for memory in self.memories:
            if memory['id'] == memory_id:
                return memory
        return None


# Memory manager with fallback support
class MemoryManager:
    _instance = None
    _simple_store = None
    
    @classmethod
    async def get_instance(cls, **kwargs):
        """Get memory instance (mem0 if available, otherwise simple store)."""
        if MEM0_AVAILABLE and cls._instance is None:
            try:
                # Initialize mem0 with provided settings
                storage_path = kwargs.get('storage_path', './memory_store')
                api_base = kwargs.get('api_base', 'http://localhost:1234/v1')
                model_name = kwargs.get('model_name', 'gpt-3.5-turbo')
                use_local_embeddings = kwargs.get('use_local_embeddings', True)
                embedding_model_name = kwargs.get('embedding_model_name', 'all-MiniLM-L6-v2')
                
                if use_local_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE:
                    # Use local embeddings
                    from .embedding_tools import LocalEmbeddings
                    embedding_model = CustomEmbeddingModel(LocalEmbeddings(embedding_model_name))
                else:
                    # Use OpenAI embeddings via LM Studio
                    embedding_model = OpenAIEmbeddingModel(
                        model_name="text-embedding-ada-002",
                        api_key="not-needed",
                        api_base=api_base
                    )
                
                llm = OpenAILLM(
                    model_name=model_name,
                    api_key="not-needed", 
                    api_base=api_base
                )
                
                os.makedirs(storage_path, exist_ok=True)
                
                cls._instance = AsyncMemory(
                    embedding_model=embedding_model,
                    llm=llm,
                    storage_path=storage_path
                )
            except Exception:
                # Fall back to simple store if mem0 fails
                pass
        
        if cls._instance is not None:
            return cls._instance
        
        # Use simple fallback store
        if cls._simple_store is None:
            cls._simple_store = SimpleMemoryStore()
        return cls._simple_store


# Tool implementation functions
async def mem0_add(content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Add a memory to the memory system."""
    try:
        memory = await MemoryManager.get_instance()
        memory_id = await memory.add(content, metadata=metadata)
        return f"Memory added with ID {memory_id}: {content[:50]}..." if len(content) > 50 else f"Memory added with ID {memory_id}: {content}"
    except Exception as e:
        return f"Error adding memory: {str(e)}"


async def mem0_retrieve(query: str, limit: int = 5) -> str:
    """Retrieve relevant memories based on a query."""
    try:
        memory = await MemoryManager.get_instance()
        memories = await memory.retrieve(query, limit=limit)
        
        if not memories:
            return "No relevant memories found."
        
        result = "Retrieved memories:\n\n"
        for i, mem in enumerate(memories):
            timestamp = mem.get('metadata', {}).get('timestamp', mem.get('timestamp', 'No timestamp'))
            text = mem.get('text', mem.get('content', str(mem)))
            result += f"Memory {i+1} [{timestamp}]:\n{text}\n\n"
        
        return result
    except Exception as e:
        return f"Error retrieving memories: {str(e)}"


async def mem0_init(storage_path: str = "./memory_store", 
                   api_base: str = "http://localhost:1234/v1",
                   model_name: str = "gpt-3.5-turbo",
                   use_local_embeddings: bool = True) -> str:
    """Initialize the memory system with custom settings."""
    try:
        # Reset instance to force reinitialization
        MemoryManager._instance = None
        MemoryManager._simple_store = None
        
        # Get new instance with provided settings
        memory = await MemoryManager.get_instance(
            storage_path=storage_path,
            api_base=api_base,
            model_name=model_name,
            use_local_embeddings=use_local_embeddings
        )
        
        if MEM0_AVAILABLE and isinstance(memory, AsyncMemory):
            return f"Memory system initialized with mem0 at {storage_path}"
        else:
            return "Memory system initialized with simple fallback store (mem0 not available)"
    except Exception as e:
        return f"Error initializing memory system: {str(e)}"


# Export the tools (only if dependencies allow)
DATABASE_TOOLS = [
    ToolDefinition(
        name="mem0_add",
        description="Add a memory to the memory system",
        parameters={
            "content": {"type": "string", "description": "Content to remember"},
            "metadata": {"type": "object", "description": "Optional metadata", "required": False},
        },
        implementation=mem0_add,
    ),
    ToolDefinition(
        name="mem0_retrieve", 
        description="Retrieve memories based on a query",
        parameters={
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Maximum results", "required": False},
        },
        implementation=mem0_retrieve,
    ),
    ToolDefinition(
        name="mem0_init",
        description="Initialize the memory system with custom settings",
        parameters={
            "storage_path": {"type": "string", "description": "Storage directory", "required": False},
            "api_base": {"type": "string", "description": "API base URL", "required": False},
            "model_name": {"type": "string", "description": "Model name", "required": False},
            "use_local_embeddings": {"type": "boolean", "description": "Use local embeddings", "required": False},
        },
        implementation=mem0_init,
    ),
]