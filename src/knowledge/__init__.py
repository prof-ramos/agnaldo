"""Knowledge module for Agnaldo Discord bot.

This module provides knowledge base functionality including:
- Legal PDF ingestion for RAG (Retrieval Augmented Generation)
- Semantic search with pgvector
- Knowledge graph management
- Advanced graph operations with LLM-powered entity extraction
"""

from src.knowledge.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
from src.knowledge.graph_service import (
    EntityType,
    ExtractedEntity,
    ExtractedRelation,
    GraphService,
    RelationType,
)
from src.knowledge.legal_pdf_ingestor import LegalPDFIngestor, get_ingestor

__all__ = [
    "EntityType",
    "ExtractedEntity",
    "ExtractedRelation",
    "GraphService",
    "KnowledgeEdge",
    "KnowledgeGraph",
    "KnowledgeNode",
    "LegalPDFIngestor",
    "RelationType",
    "get_ingestor",
]
