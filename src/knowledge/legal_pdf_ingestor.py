"""Ingestor de PDFs jurídicos para RAG em concursos públicos.

This module provides functionality to ingest legal PDFs into the archival_memory
table with OpenAI embeddings for semantic search.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import PyPDF2  # type: ignore[import-not-found]
from loguru import logger
from openai import AsyncOpenAI
from tiktoken import encoding_for_model

from src.config.settings import get_settings
from src.database.models import ArchivalMemory, LEGAL_CATEGORIES, User
from src.schemas.knowledge import (
    IngestionResult,
    LegalDocumentChunk,
    LegalPDFMetadata,
)

if TYPE_CHECKING:
    from asyncpg import Pool as AsyncPGPool
else:
    AsyncPGPool = object  # type: ignore[assignment]


class LegalPDFIngestor:
    """Ingestor de PDFs jurídicos para o sistema RAG.

    Extrai texto de PDFs, chunka com tiktoken, gera embeddings OpenAI
    e armazena em archival_memories com category apropriada.
    """

    # Configurações de chunking
    MIN_CHUNK_TOKENS = 512
    MAX_CHUNK_TOKENS = 1024
    CHUNK_OVERLAP = 128
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self, db_pool: "AsyncPGPool" | None = None) -> None:
        """Inicializa o ingestor.

        Args:
            db_pool: Pool de conexões PostgreSQL (opcional para operações assíncronas).
        """
        self.settings = get_settings()
        self.openai = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        self.encoding = encoding_for_model(self.EMBEDDING_MODEL)
        self.db_pool = db_pool

    async def ingest_pdf(
        self,
        pdf_path: Path,
        user_id: str,
        category: str,
        metadata: LegalPDFMetadata,
    ) -> IngestionResult:
        """Ingere PDF jurídico no banco de dados.

        Args:
            pdf_path: Caminho para o arquivo PDF.
            user_id: ID do usuário (UUID string).
            category: Categoria legal (legal_legislacao, legal_doutrina, etc).
            metadata: Metadados do documento.

        Returns:
            IngestionResult com estatísticas da ingestão.

        Raises:
            ValueError: Se categoria não for válida.
            FileNotFoundError: Se PDF não existir.
        """
        # Valida categoria
        if category not in LEGAL_CATEGORIES:
            raise ValueError(f"Categoria inválida: {category}. Use uma de: {LEGAL_CATEGORIES}")

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

        start_time = datetime.now(timezone.utc)
        errors: list[str] = []

        logger.info(f"Iniciando ingestão: {pdf_path.name} (category: {category})")

        try:
            # 1. Extrair texto do PDF
            text_content = await self._extract_text_from_pdf(pdf_path)
            if not text_content:
                raise ValueError("PDF não contém texto extraível")

            # 2. Chunkar o conteúdo
            chunks = self._chunk_text(text_content)

            # 3. Gerar embeddings em batch
            embeddings = await self._generate_embeddings(chunks)

            # 4. Inserir no banco
            chunks_inserted = 0
            if self.db_pool:
                chunks_inserted = await self._insert_chunks(
                    chunks, embeddings, user_id, category, metadata
                )
            else:
                logger.warning("No database pool, skipping insertion")
                chunks_inserted = len(chunks)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            result = IngestionResult(
                file_path=str(pdf_path),
                category=category,
                total_chunks=len(chunks),
                chunks_inserted=chunks_inserted,
                errors=errors,
                duration_seconds=duration,
            )

            logger.info(f"Ingestão concluída: {chunks_inserted}/{len(chunks)} chunks inseridos em {duration:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Erro na ingestão de {pdf_path.name}: {e}")
            errors.append(str(e))
            raise

    async def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extrai texto completo do PDF.

        Args:
            pdf_path: Caminho para o PDF.

        Returns:
            Texto extraído do PDF.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_text_sync, pdf_path)

    def _extract_text_sync(self, pdf_path: Path) -> str:
        """Versão síncrona da extração de texto.

        Args:
            pdf_path: Caminho para o PDF.

        Returns:
            Texto extraído do PDF.
        """
        text_parts = []

        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)

            # Verificar se PDF está protegido
            if reader.is_encrypted:
                logger.warning(f"PDF está criptografado: {pdf_path.name}")
                # Tentar decrypt com senha vazia (comum em PDFs públicos)
                try:
                    reader.decrypt("")
                except Exception:
                    return ""

            # Extrair texto de todas as páginas
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Erro ao extrair página {page_num}: {e}")

        return "\n\n".join(text_parts)

    def _chunk_text(self, text: str) -> list[str]:
        """Divide texto em chunks usando tiktoken.

        Args:
            text: Texto completo.

        Returns:
            Lista de chunks.
        """
        tokens = self.encoding.encode(text)
        chunks = []

        start = 0
        chunk_index = 0

        while start < len(tokens):
            # Define final do chunk
            end = min(start + self.MAX_CHUNK_TOKENS, len(tokens))

            # Ajusta para não quebrar no meio de um token
            if end < len(tokens):
                # Tenta encontrar ponto de quebra (quebra de linha ou ponto)
                for lookback in range(self.CHUNK_OVERLAP, 0, -1):
                    if end - lookback <= start:
                        break
                    if tokens[end - lookback] in (101, 198, 616):  # \n, \n\n, .
                        end -= lookback
                        break

            # Decodifica chunk
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)

            # Skip chunks vazios ou muito pequenos
            if len(chunk_text.strip()) > 50:
                chunks.append(chunk_text)
                chunk_index += 1

            # Próximo chunk com overlap
            start = end - self.CHUNK_OVERLAP

        logger.info(f"Texto dividido em {len(chunks)} chunks ({len(tokens)} tokens totais)")
        return chunks

    async def _generate_embeddings(self, chunks: list[str]) -> list[list[float]]:
        """Gera embeddings OpenAI para os chunks.

        Args:
            chunks: Lista de textos dos chunks.

        Returns:
            Lista de embeddings (1536 dimensões cada).
        """
        # Processar em batches de 100 (limite da API)
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            try:
                response = await self.openai.embeddings.create(
                    model=self.EMBEDDING_MODEL,
                    input=batch,
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.debug(f"Generated {len(batch_embeddings)} embeddings (batch {i // batch_size + 1})")

            except Exception as e:
                logger.error(f"Erro ao gerar embeddings batch {i // batch_size + 1}: {e}")
                # Se falhar, retorna embeddings vazios para manter a contagem
                all_embeddings.extend([[0.0] * self.EMBEDDING_DIMENSIONS] * len(batch))

        return all_embeddings

    async def _insert_chunks(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        user_id: str,
        category: str,
        metadata: LegalPDFMetadata,
    ) -> int:
        """Insere chunks na tabela archival_memories.

        Args:
            chunks: Lista de textos dos chunks.
            embeddings: Lista de embeddings.
            user_id: ID do usuário (UUID string).
            category: Categoria legal.
            metadata: Metadados do documento.

        Returns:
            Número de chunks inseridos.
        """
        inserted = 0

        if self.db_pool is None:
            logger.warning("No database pool available")
            return 0

        async with self.db_pool.acquire() as conn:  # type: ignore[union-attr]
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                try:
                    # Prepara metadados JSONB
                    archival_metadata = {
                        **metadata.model_dump(),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    }

                    # Insere usando SQL direto (mais rápido que ORM)
                    await conn.execute(
                        """
                        INSERT INTO archival_memories
                        (user_id, content, embedding, category, archival_metadata, created_at)
                        VALUES (
                            $1::uuid,
                            $2,
                            $3::vector(1536),
                            $4,
                            $5::jsonb,
                            NOW()
                        )
                        """,
                        user_id,
                        chunk,
                        embedding,
                        category,
                        archival_metadata,
                    )
                    inserted += 1

                except Exception as e:
                    logger.error(f"Erro ao inserir chunk {i}: {e}")

        logger.info(f"Inseridos {inserted}/{len(chunks)} chunks no banco")
        return inserted


# Singleton instance
_ingestor: LegalPDFIngestor | None = None


def get_ingestor(db_pool: "AsyncPGPool" | None = None) -> LegalPDFIngestor:
    """Retorna instância singleton do LegalPDFIngestor.

    Args:
        db_pool: Pool de conexões PostgreSQL.

    Returns:
        Instância do LegalPDFIngestor.
    """
    global _ingestor

    if _ingestor is None:
        _ingestor = LegalPDFIngestor(db_pool)

    return _ingestor
