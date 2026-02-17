"""Recall Memory implementation using pgvector for semantic search.

This module provides a memory tier optimized for fast retrieval of relevant
memories using vector embeddings and cosine similarity search.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from openai import AsyncOpenAI
import tiktoken

from src.config.settings import get_settings
from src.exceptions import DatabaseError, EmbeddingGenerationError, MemoryServiceError


class RecallMemory:
    """Recall Memory tier for semantic search over stored memories.

    Uses OpenAI embeddings and pgvector IVFFlat index for fast similarity
    search. Each memory has an importance score (0.0-1.0) for relevance ranking.

    Attributes:
        user_id: User identifier for memory isolation.
        repository: Database connection pool (asyncpg).
        openai: OpenAI client for embedding generation.
        embedding_model: Model name for embeddings.
    """

    def __init__(self, user_id: str, repository, openai_client: AsyncOpenAI | None = None):
        """Initialize RecallMemory.

        Args:
            user_id: User identifier for memory isolation.
            repository: asyncpg connection pool or database connection.
            openai_client: Optional OpenAI client instance.
        """
        settings = get_settings()
        self.user_id = user_id
        self.repository = repository
        self.openai = openai_client or AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self._embedding_dim = 1536  # text-embedding-3-small dimension
        try:
            self._encoding = tiktoken.encoding_for_model(self.embedding_model)
        except Exception:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    @staticmethod
    def _affected_rows(command_tag: str) -> int:
        """Extract affected row count from asyncpg command tag."""
        try:
            return int(command_tag.split()[-1])
        except (ValueError, IndexError):
            return 0

    @staticmethod
    def _to_utc(value: datetime | None) -> datetime | None:
        """Normalize datetimes to UTC without altering already-aware timestamps."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _truncate_for_embedding(self, text: str, max_tokens: int = 8191) -> str:
        """Truncate text by token count (not characters) for embedding models."""
        tokens = self._encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self._encoding.decode(tokens[:max_tokens])

    async def add(self, content: str, importance: float = 0.5) -> str:
        """Add a memory to recall storage with embedding.

        Args:
            content: Text content of the memory.
            importance: Importance score from 0.0 (low) to 1.0 (high).

        Returns:
            memory_id: UUID of the created memory.

        Raises:
            EmbeddingGenerationError: If embedding generation fails.
            DatabaseError: If database insert fails.
        """
        if not content or not content.strip():
            raise MemoryServiceError("Content cannot be empty", memory_type="recall")

        if not 0.0 <= importance <= 1.0:
            raise MemoryServiceError("Importance must be between 0.0 and 1.0", memory_type="recall")

        try:
            # Generate embedding using OpenAI
            embedding = await self._generate_embedding(content)
        except Exception as e:
            raise EmbeddingGenerationError(
                f"Failed to generate embedding: {e}",
                model=self.embedding_model,
                text_length=len(content),
            ) from e

        # Insert into database with pgvector
        memory_id = await self._insert_memory(content, embedding, importance)

        logger.info(f"Added recall memory {memory_id} with importance {importance}")
        return memory_id

    async def search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        min_importance: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity.

        Args:
            query: Search query text.
            limit: Maximum number of results to return.
            threshold: Minimum cosine similarity (0.0-1.0) for results.
            min_importance: Minimum importance score to filter results.

        Returns:
            List of memory dicts with content, similarity, and metadata.

        Raises:
            MemoryServiceError: If search query is empty or search fails.
        """
        if not query or not query.strip():
            raise MemoryServiceError("Search query cannot be empty", memory_type="recall")

        try:
            query_embedding = await self._generate_embedding(query)
        except Exception as e:
            raise EmbeddingGenerationError(
                f"Failed to generate query embedding: {e}",
                model=self.embedding_model,
                text_length=len(query),
            ) from e

        try:
            async with self.repository.acquire() as conn:
                # Use pgvector <-> operator for cosine distance
                # Convert cosine similarity threshold to distance: distance = 1 - similarity
                max_distance = 1.0 - threshold

                rows = await conn.fetch(
                    """
                    SELECT
                        id,
                        content,
                        importance,
                        1 - (embedding <=> $1::vector) as similarity,
                        created_at,
                        updated_at,
                        access_count
                    FROM recall_memories
                    WHERE user_id = $2
                        AND importance >= $3
                        AND (embedding <=> $1::vector) <= $4
                    ORDER BY embedding <=> $1::vector
                    LIMIT $5
                    """,
                    "[" + ",".join(map(str, query_embedding)) + "]",
                    self.user_id,
                    min_importance,
                    max_distance,
                    limit,
                )

                results = [
                    {
                        "memory_id": str(row["id"]),
                        "content": row["content"],
                        "importance": row["importance"],
                        "similarity": float(row["similarity"]),
                        "created_at": self._to_utc(row["created_at"]),
                        "updated_at": self._to_utc(row["updated_at"]),
                        "access_count": row["access_count"],
                    }
                    for row in rows
                ]

                # Update access count for returned memories
                if results:
                    memory_ids = [r["memory_id"] for r in results]
                    await conn.execute(
                        """
                        UPDATE recall_memories
                        SET access_count = access_count + 1,
                            last_accessed = NOW()
                        WHERE id = ANY($1::uuid[])
                            AND user_id = $2
                        """,
                        memory_ids,
                        self.user_id,
                    )

                query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]
                logger.debug(
                    "Recall search returned "
                    f"{len(results)} results for query_hash={query_hash} "
                    f"query_length={len(query)}"
                )
                return results

        except Exception as e:
            raise DatabaseError(f"Recall search failed: {e}", operation="search") from e

    async def update_importance(self, memory_id: str, importance: float) -> bool:
        """Update the importance score of a memory.

        Args:
            memory_id: UUID of the memory to update.
            importance: New importance score (0.0-1.0).

        Returns:
            True if updated, False if memory not found.

        Raises:
            MemoryServiceError: If importance is out of range.
            DatabaseError: If update fails.
        """
        if not 0.0 <= importance <= 1.0:
            raise MemoryServiceError("Importance must be between 0.0 and 1.0", memory_type="recall")

        try:
            async with self.repository.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE recall_memories
                    SET importance = $1,
                        updated_at = NOW()
                    WHERE id = $2::uuid
                        AND user_id = $3
                    """,
                    importance,
                    memory_id,
                    self.user_id,
                )
                success = self._affected_rows(result) > 0
                if success:
                    logger.info(f"Updated importance for memory {memory_id} to {importance}")
                return success

        except Exception as e:
            raise DatabaseError(f"Failed to update importance: {e}", operation="update") from e

    async def get(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve a specific memory by ID.

        Args:
            memory_id: UUID of the memory.

        Returns:
            Memory dict or None if not found.
        """
        try:
            async with self.repository.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        id, content, importance, created_at,
                        updated_at, access_count, last_accessed
                    FROM recall_memories
                    WHERE id = $1::uuid
                        AND user_id = $2
                    """,
                    memory_id,
                    self.user_id,
                )

                if not row:
                    return None

                # Update access count and get the fresh counters
                access_row = await conn.fetchrow(
                    """
                    UPDATE recall_memories
                    SET access_count = access_count + 1,
                        last_accessed = NOW()
                    WHERE id = $1::uuid
                        AND user_id = $2
                    RETURNING access_count, last_accessed
                    """,
                    memory_id,
                    self.user_id,
                )
                if access_row is None:
                    return None

                return {
                    "memory_id": str(row["id"]),
                    "content": row["content"],
                    "importance": row["importance"],
                    "created_at": self._to_utc(row["created_at"]),
                    "updated_at": self._to_utc(row["updated_at"]),
                    "access_count": access_row["access_count"],
                    "last_accessed": self._to_utc(access_row["last_accessed"]),
                }

        except Exception as e:
            raise DatabaseError(f"Failed to get memory: {e}", operation="get") from e

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory from recall storage.

        Args:
            memory_id: UUID of the memory to delete.

        Returns:
            True if deleted, False if not found.
        """
        try:
            async with self.repository.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM recall_memories
                    WHERE id = $1::uuid
                        AND user_id = $2
                    """,
                    memory_id,
                    self.user_id,
                )
                success = self._affected_rows(result) > 0
                if success:
                    logger.info(f"Deleted recall memory {memory_id}")
                return success

        except Exception as e:
            raise DatabaseError(f"Failed to delete memory: {e}", operation="delete") from e

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text using OpenAI.

        Args:
            text: Text to embed.

        Returns:
            List of floating point values representing the embedding.

        Raises:
            EmbeddingGenerationError: If API call fails.
        """
        try:
            truncated_text = self._truncate_for_embedding(text)
            response = await self.openai.embeddings.create(
                model=self.embedding_model,
                input=truncated_text,
            )
            embedding = response.data[0].embedding
            if len(embedding) != self._embedding_dim:
                raise EmbeddingGenerationError(
                    "Embedding dimension mismatch",
                    model=self.embedding_model,
                    text_length=len(text),
                    details={"expected_dim": self._embedding_dim, "actual_dim": len(embedding)},
                )
            return embedding
        except Exception as e:
            raise EmbeddingGenerationError(
                f"OpenAI API error: {e}",
                model=self.embedding_model,
                text_length=len(text),
            ) from e

    async def _insert_memory(
        self,
        content: str,
        embedding: list[float],
        importance: float,
    ) -> str:
        """Insert memory into database.

        Args:
            content: Memory content text.
            embedding: Vector embedding.
            importance: Importance score.

        Returns:
            UUID of inserted memory.
        """
        try:
            async with self.repository.acquire() as conn:
                memory_id = await conn.fetchval(
                    """
                    INSERT INTO recall_memories
                        (user_id, content, embedding, importance, created_at)
                    VALUES ($1, $2, $3::vector, $4, NOW())
                    RETURNING id
                    """,
                    self.user_id,
                    content,
                    "[" + ",".join(map(str, embedding)) + "]",
                    importance,
                )
                return str(memory_id)

        except Exception as e:
            raise DatabaseError(f"Failed to insert memory: {e}", operation="insert") from e
