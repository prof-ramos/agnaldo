"""Memory modules for the Agnaldo Discord bot.

This package provides memory tiers for storing and retrieving knowledge:
- CoreMemory: Fast key-value storage for important facts
- RecallMemory: Semantic search using OpenAI embeddings and pgvector
- ArchivalMemory: Long-term storage with metadata-based retrieval
- MemoryManager: Unified facade for all memory tiers
- MemoryContext: Context object for prompt injection
- Isolation: Memory isolation guard to prevent cross-user data access
"""

from src.memory.archival import ArchivalMemory
from src.memory.core import CoreMemory
from src.memory.isolation import (
    MemoryIsolationError,
    MemoryIsolationGuard,
    UserContext,
    get_isolation_guard,
    require_isolation,
    set_user_context,
    clear_user_context,
)
from src.memory.manager import MemoryContext, MemoryManager
from src.memory.recall import RecallMemory

__all__ = [
    "ArchivalMemory",
    "CoreMemory",
    "MemoryContext",
    "MemoryIsolationError",
    "MemoryIsolationGuard",
    "MemoryManager",
    "RecallMemory",
    "UserContext",
    "clear_user_context",
    "get_isolation_guard",
    "require_isolation",
    "set_user_context",
]
