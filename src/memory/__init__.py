"""Memory modules for the Agnaldo Discord bot.

This package provides memory tiers for storing and retrieving knowledge:
- RecallMemory: Semantic search using OpenAI embeddings and pgvector
- ArchivalMemory: Long-term storage with metadata-based retrieval
"""

from src.memory.archival import ArchivalMemory
from src.memory.recall import RecallMemory

__all__ = ["RecallMemory", "ArchivalMemory"]
