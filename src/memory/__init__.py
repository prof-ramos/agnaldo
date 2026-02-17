"""Memory modules for the Agnaldo Discord bot.

This package provides memory tiers for storing and retrieving knowledge:
- CoreMemory: Fast key-value storage for important facts
- RecallMemory: Semantic search using OpenAI embeddings and pgvector
- ArchivalMemory: Long-term storage with metadata-based retrieval
- MemoryManager: Unified facade for all memory tiers
- MemoryContext: Context object for prompt injection
"""

from src.memory.archival import ArchivalMemory
from src.memory.core import CoreMemory
from src.memory.recall import RecallMemory
from src.memory.manager import MemoryManager, MemoryContext

__all__ = [
    "CoreMemory",
    "RecallMemory",
    "ArchivalMemory",
    "MemoryManager",
    "MemoryContext",
]
