"""Knowledge module for Agnaldo Discord bot.

This module provides knowledge base functionality including:
- Legal PDF ingestion for RAG (Retrieval Augmented Generation)
- Semantic search with pgvector
- Knowledge graph management
"""

from src.knowledge.legal_pdf_ingestor import LegalPDFIngestor, get_ingestor

__all__ = ["LegalPDFIngestor", "get_ingestor"]
