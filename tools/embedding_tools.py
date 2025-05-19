from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import os
import asyncio
from datetime import datetime

# Import mem0 components
from mem0.async_memory import AsyncMemory
from mem0.embeddings import OpenAIEmbeddingModel, CustomEmbeddingModel
from mem0.llm import OpenAILLM
from mem0.storage import ChromaVectorStore


# Import sentence-transformers for local embeddings option
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    pass

# Tool definition structure that matches your existing system
class ToolDefinition:
    def __init__(self, name, description, parameters, implementation):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.implementation = implementation

# Local embeddings implementation
class LocalEmbeddings:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text):
        return self.model.encode(text).tolist()

# Memory singleton manager
class MemoryManager:
    _instance = None
    
    @classmethod
    async def get_instance(cls, 
                          storage_path: str = "./memory_store", 
                          api_base: str = "http://localhost:1234/v1", 
                          model_name: str = "gpt-3.5-turbo",
                          use_local_embeddings: bool = True,
                          embedding_model_name: str = "all-MiniLM-L6-v2") -> AsyncMemory:
        """Get or create a singleton AsyncMemory instance."""
        if cls._instance is None:
            # Create embedding model (local or API-based)
            if use_local_embeddings:
                try:
                    embedding_model = CustomEmbeddingModel(LocalEmbeddings(embedding_model_name))
                except (ImportError, NameError):
                    print("Warning: sentence-transformers not installed. Falling back to API embeddings.")
                    embedding_model = OpenAIEmbeddingModel(
                        model_name="text-embedding-ada-002",
                        api_key="not-needed",
                        api_base=api_base
                    )
            else:
                embedding_model = OpenAIEmbeddingModel(
                    model_name="text-embedding-ada-002",
                    api_key="not-needed",
                    api_base=api_base
                )
            
            # Configure LLM for LM Studio
            llm = OpenAILLM(
                model_name=model_name,
                api_key="not-needed",
                api_base=api_base
            )
            
            # Create directory if it doesn't exist
            os.makedirs(storage_path, exist_ok=True)
            
            # Initialize the memory with async support
            cls._instance = AsyncMemory(
                embedding_model=embedding_model,
                llm=llm,
                storage_path=storage_path
            )
        
        return cls._instance

# Tool implementation functions
async def mem0_add(content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Add a memory to mem0."""
    # Auto-add timestamp if not provided
    if metadata is None:
        metadata = {}
    
    if 'timestamp' not in metadata:
        metadata['timestamp'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get memory instance
    memory = await MemoryManager.get_instance()
    
    # Add the memory
    memory_id = await memory.add(content, metadata=metadata)
    
    return f"Memory added with ID {memory_id}: {content[:50]}..." if len(content) > 50 else f"Memory added with ID {memory_id}: {content}"

async def mem0_retrieve(query: str, limit: int = 5) -> str:
    """Retrieve relevant memories based on a query."""
    memory = await MemoryManager.get_instance()
    memories = await memory.retrieve(query, limit=limit)
    
    # Format the retrieved memories
    if not memories:
        return "No relevant memories found."
    
    result = "Retrieved memories:\n\n"
    for i, memory in enumerate(memories):
        timestamp = memory.get('metadata', {}).get('timestamp', 'No timestamp')
        result += f"Memory {i+1} [{timestamp}]:\n{memory['text']}\n\n"
    
    return result

async def mem0_retrieve_by_id(memory_id: str) -> str:
    """Retrieve a specific memory by its ID."""
    memory = await MemoryManager.get_instance()
    
    try:
        result = await memory.get(memory_id)
        if not result:
            return f"No memory found with ID {memory_id}."
        
        timestamp = result.get('metadata', {}).get('timestamp', 'No timestamp')
        return f"Memory [{timestamp}]:\n{result['text']}"
    except Exception as e:
        return f"Error retrieving memory: {str(e)}"

async def mem0_summarize(query: str = "") -> str:
    """Summarize memories, optionally filtered by a query."""
    memory = await MemoryManager.get_instance()
    
    if query:
        # If query provided, get relevant memories first
        memories = await memory.retrieve(query)
        if not memories:
            return "No memories found matching your query."
        memory_texts = [m["text"] for m in memories]
        summary = await memory.summarize(memory_texts)
    else:
        # Summarize all memories
        summary = await memory.summarize_all()
    
    return f"Memory summary: {summary}"

async def mem0_search_by_metadata(key: str, value: str, limit: int = 5) -> str:
    """Search memories by metadata field."""
    memory = await MemoryManager.get_instance()
    
    try:
        # Get vector store directly to perform metadata filtering
        vector_store = memory._store
        results = await vector_store.similarity_search_with_metadata_filter(
            query="",  # Empty query to return based on metadata only
            metadata_filter={key: value},
            k=limit
        )
        
        if not results:
            return f"No memories found with metadata {key}={value}."
        
        result_text = f"Found {len(results)} memories with {key}={value}:\n\n"
        for i, item in enumerate(results):
            timestamp = item.get('metadata', {}).get('timestamp', 'No timestamp')
            result_text += f"Memory {i+1} [{timestamp}]:\n{item['text']}\n\n"
        
        return result_text
    except Exception as e:
        return f"Error searching by metadata: {str(e)}"

async def mem0_clear() -> str:
    """Clear all memories."""
    memory = await MemoryManager.get_instance()
    await memory.clear()
    return "All memories have been cleared."

async def mem0_delete(memory_id: str) -> str:
    """Delete a specific memory by ID."""
    memory = await MemoryManager.get_instance()
    
    try:
        await memory.delete(memory_id)
        return f"Memory {memory_id} deleted successfully."
    except Exception as e:
        return f"Error deleting memory: {str(e)}"

async def mem0_update(memory_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Update an existing memory."""
    memory = await MemoryManager.get_instance()
    
    try:
        # First check if memory exists
        existing = await memory.get(memory_id)
        if not existing:
            return f"No memory found with ID {memory_id}."
        
        # If no new metadata provided, keep the existing metadata
        if metadata is None:
            metadata = existing.get('metadata', {})
        
        # Update the memory
        await memory.update(memory_id, content, metadata)
        return f"Memory {memory_id} updated successfully."
    except Exception as e:
        return f"Error updating memory: {str(e)}"

async def mem0_init(storage_path: str = "./memory_store", 
                   api_base: str = "http://localhost:1234/v1",
                   model_name: str = "gpt-3.5-turbo",
                   use_local_embeddings: bool = True) -> str:
    """Initialize or reinitialize the memory system."""
    try:
        # Force recreation of the memory instance
        MemoryManager._instance = None
        await MemoryManager.get_instance(
            storage_path=storage_path,
            api_base=api_base,
            model_name=model_name,
            use_local_embeddings=use_local_embeddings
        )
        return f"Memory system initialized with storage at {storage_path}, using {model_name} via {api_base}."
    except Exception as e:
        return f"Error initializing memory system: {str(e)}"