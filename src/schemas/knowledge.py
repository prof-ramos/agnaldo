"""Schemas Pydantic para conhecimento jurídico e RAG.

This module defines schemas for legal document ingestion and RAG operations.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LegalPDFMetadata(BaseModel):
    """Metadados para PDF jurídico durante ingestão.

    Attributes:
        fonte: Nome da fonte (ex: "Código Penal", "Doutrina Rogério Greco")
        autor: Autor da obra (para doutrina)
        area_direito: Área do direito (penal, constitucional, administrativo, etc)
        ano_vigencia: Ano de vigência ou publicação
        pagina_inicial: Página inicial (se aplicável)
        pagina_final: Página final (se aplicável)
    """

    fonte: str = Field(..., description="Nome da fonte jurídica")
    autor: str | None = Field(None, description="Autor da obra (para doutrina)")
    area_direito: str = Field(..., description="Área do direito")
    ano_vigencia: int | None = Field(None, description="Ano de vigência ou publicação")
    pagina_inicial: int | None = Field(None, description="Página inicial do documento")
    pagina_final: int | None = Field(None, description="Página final do documento")


class LegalDocumentChunk(BaseModel):
    """Representa um chunk de documento jurídico processado.

    Attributes:
        content: Conteúdo do chunk
        metadata: Metadados do chunk
        category: Categoria do documento legal
        chunk_index: Índice do chunk no documento
        total_chunks: Total de chunks no documento
    """

    content: str
    metadata: LegalPDFMetadata
    category: str  # legal_legislacao, legal_doutrina, etc
    chunk_index: int
    total_chunks: int


class IngestionResult(BaseModel):
    """Resultado da ingestão de PDF jurídico.

    Attributes:
        file_path: Caminho do arquivo processado
        category: Categoria do documento
        total_chunks: Total de chunks criados
        chunks_inserted: Quantidade de chunks inseridos com sucesso
        errors: Lista de erros ocorridos
        duration_seconds: Tempo de processamento em segundos
    """

    file_path: str
    category: str
    total_chunks: int
    chunks_inserted: int
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None


class RAGSearchResult(BaseModel):
    """Resultado de busca RAG em documentos jurídicos.

    Attributes:
        content: Conteúdo recuperado
        similarity: Score de similaridade (0-1)
        category: Categoria do documento
        metadata: Metadados do documento
        source: Fonte do documento (extraído de metadata)
    """

    content: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    category: str
    metadata: dict[str, Any]
    source: str

    @classmethod
    def from_db_record(cls, record: Any) -> "RAGSearchResult":
        """Cria resultado a partir de um registro do banco."""
        metadata = record.archival_metadata or {}
        return cls(
            content=record.content,
            similarity=metadata.get("similarity", 0.0),
            category=record.category,
            metadata=metadata,
            source=metadata.get("fonte", "Fonte desconhecida"),
        )


class StudyAgentRequest(BaseModel):
    """Request para Study Agent.

    Attributes:
        question: Pergunta do usuário
        user_id: ID do usuário Discord
        category_filter: Filtro opcional por categoria
        max_results: Máximo de resultados RAG
        threshold: Threshold mínimo de similaridade
    """

    question: str
    user_id: str
    category_filter: str | None = Field(
        None, description="Filtro opcional por categoria (legal_legislacao, etc)"
    )
    max_results: int = Field(5, ge=1, le=10)
    threshold: float = Field(0.7, ge=0.0, le=1.0)


class StudyAgentResponse(BaseModel):
    """Resposta do Study Agent.

    Attributes:
        answer: Resposta gerada
        sources: Fontes citadas
        confidence: Confiança da resposta (0-1)
        didactic_content: Conteúdo didático adicional
        uncertainty: Se a resposta indica incerteza
    """

    answer: str
    sources: list[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    didactic_content: str | None = None
    uncertainty: bool = False
