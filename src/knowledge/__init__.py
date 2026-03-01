"""Knowledge module for Agnaldo Discord bot.

This module provides knowledge base functionality including:
- Legal PDF ingestion for RAG (Retrieval Augmented Generation)
- Semantic search with pgvector
- Knowledge graph management
- Advanced graph operations with LLM-powered entity extraction
"""

from typing import Any

from src.knowledge.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
from src.knowledge.graph_service import (
    EntityType,
    ExtractedEntity,
    ExtractedRelation,
    GraphService,
    RelationType,
)

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


def __getattr__(name: str) -> Any:
    """Carrega preguiçosamente símbolos pesados do ingestor de PDF para evitar efeitos colaterais na importação.

    Esta função permite importar LegalPDFIngestor e get_ingestor sob demanda,
    adiando o carregamento de dependências pesadas até que sejam realmente necessárias.
    """
    if name in {"LegalPDFIngestor", "get_ingestor"}:
        from src.knowledge.legal_pdf_ingestor import LegalPDFIngestor, get_ingestor

        exports: dict[str, Any] = {
            "LegalPDFIngestor": LegalPDFIngestor,
            "get_ingestor": get_ingestor,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
