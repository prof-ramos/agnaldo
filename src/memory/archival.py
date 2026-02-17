"""Archival Memory implementation for long-term storage with compression.

This module provides a memory tier optimized for storing and compressing
conversation context and historical data with metadata-based retrieval.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.exceptions import DatabaseError, MemoryServiceError


class ArchivalMemory:
    """Archival Memory tier for compressed, searchable long-term storage.

    Stores memories with source tracking and JSONB metadata for flexible
    querying. Supports session compression to summarize and reduce context size.

    Attributes:
        user_id: User identifier for memory isolation.
        repository: Database connection pool (asyncpg).
    """

    def __init__(self, user_id: str, repository):
        """Initialize ArchivalMemory.

        Args:
            user_id: User identifier for memory isolation.
            repository: asyncpg connection pool or database connection.
        """
        self.user_id = user_id
        self.repository = repository

    @staticmethod
    def _to_utc(value: datetime | None) -> datetime | None:
        """Normalize datetimes to UTC without altering already-aware timestamps."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _escape_ilike(value: str) -> str:
        """Escape wildcard chars for safe ILIKE usage."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _affected_rows(command_tag: str) -> int:
        """Extract affected row count from asyncpg command tag."""
        try:
            return int(command_tag.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def add(
        self,
        content: str,
        source: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> str:
        """Add a memory to archival storage with source tracking.

        Args:
            content: Text content of the memory.
            source: Source identifier (e.g., "discord", "api", "system").
            metadata: Optional JSONB metadata for flexible querying.
            session_id: Optional session identifier for grouping.

        Returns:
            memory_id: UUID of the created memory.

        Raises:
            MemoryServiceError: If content or source is empty.
            DatabaseError: If database insert fails.
        """
        if not content or not content.strip():
            raise MemoryServiceError("Content cannot be empty", memory_type="archival")

        if not source or not source.strip():
            raise MemoryServiceError("Source cannot be empty", memory_type="archival")

        metadata = dict(metadata or {})
        metadata.setdefault("source", source)

        try:
            async with self.repository.acquire() as conn:
                memory_id = await conn.fetchval(
                    """
                    INSERT INTO archival_memories
                        (user_id, content, source, metadata, session_id, created_at)
                    VALUES ($1, $2, $3, $4::jsonb, $5, NOW())
                    RETURNING id
                    """,
                    self.user_id,
                    content,
                    source,
                    metadata,
                    session_id,
                )
                logger.info(f"Added archival memory {memory_id} from source {source}")
                return str(memory_id)

        except Exception as e:
            raise DatabaseError(f"Failed to insert archival memory: {e}", operation="insert") from e

    async def compress(self, session_id: str, summary: str | None = None) -> dict[str, Any]:
        """Compress and summarize memories from a session.

        Args:
            session_id: Session identifier to compress.
            summary: Optional pre-generated summary. If None, uses last message.

        Returns:
            Dict with compressed_memory_id and stats (original_count, compressed_count).

        Raises:
            DatabaseError: If compression operation fails.
        """
        try:
            async with self.repository.acquire() as conn:
                async with conn.transaction():
                    # Get all memories for the session
                    rows = await conn.fetch(
                        """
                        SELECT id, content, metadata
                        FROM archival_memories
                        WHERE user_id = $1
                            AND session_id = $2
                            AND compressed = false
                        ORDER BY created_at ASC
                        """,
                        self.user_id,
                        session_id,
                    )

                    if not rows:
                        return {"compressed_memory_id": None, "original_count": 0, "compressed_count": 0}

                    original_count = len(rows)
                    memory_ids = [str(row["id"]) for row in rows]

                    # Use provided summary or create a summary from content
                    if not summary:
                        # Concatenate all content with source tags
                        summary_parts = []
                        for row in rows:
                            metadata_value = row["metadata"]
                            metadata = metadata_value if isinstance(metadata_value, dict) else {}
                            source = metadata.get("source", "unknown")
                            summary_parts.append(f"[{source}] {row['content'][:200]}...")
                        summary = " | ".join(summary_parts)
                        if len(summary) > 5000:
                            summary = summary[:5000] + "..."

                    # Insert compressed memory
                    compressed_id = await conn.fetchval(
                        """
                        INSERT INTO archival_memories
                            (user_id, content, source, metadata, session_id, compressed, created_at)
                        VALUES ($1, $2, 'compression', $3::jsonb, $4, true, NOW())
                        RETURNING id
                        """,
                        self.user_id,
                        summary,
                        {"compressed_from_session": session_id, "original_count": original_count},
                        session_id,
                    )

                    # Mark original memories as compressed
                    await conn.execute(
                        """
                        UPDATE archival_memories
                        SET compressed = true,
                            compressed_into_id = $1::uuid,
                            updated_at = NOW()
                        WHERE id = ANY($2::uuid[])
                        """,
                        compressed_id,
                        memory_ids,
                    )

                    logger.info(
                        f"Compressed {original_count} memories from session {session_id} into {compressed_id}"
                    )

                    return {
                        "compressed_memory_id": str(compressed_id),
                        "original_count": original_count,
                        "compressed_count": 1,
                    }

        except Exception as e:
            raise DatabaseError(f"Failed to compress memories: {e}", operation="compress") from e

    async def search_by_metadata(
        self,
        filters: dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search memories by JSONB metadata filters.

        Args:
            filters: Dict of metadata key-value pairs to match.
                Supports nested queries with dot notation (e.g., "key.subkey").
            limit: Maximum results to return.
            offset: Pagination offset.

        Returns:
            List of memory dicts matching the filters.

        Raises:
            DatabaseError: If search fails.
        """
        if not filters:
            raise MemoryServiceError("At least one filter is required", memory_type="archival")

        try:
            async with self.repository.acquire() as conn:
                where_clauses = []
                params: list[Any] = [self.user_id]
                param_idx = 2

                for key, value in filters.items():
                    path_parts = key.split(".")
                    if any(not re.match(r"^[A-Za-z0-9_]+$", part) for part in path_parts):
                        raise MemoryServiceError(
                            f"Invalid filter key path: {key}",
                            memory_type="archival",
                        )
                    pg_path = ",".join(path_parts)
                    where_clauses.append(f"metadata #>> '{{{pg_path}}}' = ${param_idx}")
                    params.append(str(value))
                    param_idx += 1

                params.extend([limit, offset])
                where_clause = f" AND {' AND '.join(where_clauses)}" if where_clauses else ""

                query = f"""
                    SELECT
                        id, content, source, metadata, session_id,
                        compressed, compressed_into_id,
                        created_at, updated_at
                    FROM archival_memories
                    WHERE user_id = $1{where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """

                rows = await conn.fetch(query, *params)

                results = [
                    {
                        "memory_id": str(row["id"]),
                        "content": row["content"],
                        "source": row["source"],
                        "metadata": row["metadata"],
                        "session_id": row["session_id"],
                        "compressed": row["compressed"],
                        "compressed_into_id": str(row["compressed_into_id"]) if row["compressed_into_id"] else None,
                        "created_at": self._to_utc(row["created_at"]),
                        "updated_at": self._to_utc(row["updated_at"]),
                    }
                    for row in rows
                ]

                filters_hash = hashlib.sha256(repr(filters).encode()).hexdigest()[:12]
                logger.debug(
                    "Metadata search returned "
                    f"{len(results)} results for filters_hash={filters_hash} "
                    f"filter_count={len(filters)}"
                )
                return results

        except Exception as e:
            raise DatabaseError(f"Metadata search failed: {e}", operation="search") from e

    async def search_by_content(
        self,
        query: str,
        limit: int = 50,
        source: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories by content text using ILIKE.

        Args:
            query: Search query string.
            limit: Maximum results to return.
            source: Optional source filter.
            session_id: Optional session filter.

        Returns:
            List of memory dicts matching the content search.

        Raises:
            MemoryServiceError: If query is empty.
            DatabaseError: If search fails.
        """
        if not query or not query.strip():
            raise MemoryServiceError("Search query cannot be empty", memory_type="archival")

        try:
            async with self.repository.acquire() as conn:
                escaped_query = self._escape_ilike(query)
                rows = await conn.fetch(
                    """
                    SELECT
                        id, content, source, metadata, session_id,
                        compressed, compressed_into_id,
                        created_at, updated_at
                    FROM archival_memories
                    WHERE user_id = $1
                        AND content ILIKE $2 ESCAPE '\\'
                        AND ($3::text IS NULL OR source = $3)
                        AND ($4::text IS NULL OR session_id = $4)
                    ORDER BY created_at DESC
                    LIMIT $5
                    """,
                    self.user_id,
                    f"%{escaped_query}%",
                    source,
                    session_id,
                    limit,
                )

                results = [
                    {
                        "memory_id": str(row["id"]),
                        "content": row["content"],
                        "source": row["source"],
                        "metadata": row["metadata"],
                        "session_id": row["session_id"],
                        "compressed": row["compressed"],
                        "compressed_into_id": str(row["compressed_into_id"]) if row["compressed_into_id"] else None,
                        "created_at": self._to_utc(row["created_at"]),
                        "updated_at": self._to_utc(row["updated_at"]),
                    }
                    for row in rows
                ]

                query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]
                logger.debug(
                    "Content search returned "
                    f"{len(results)} results for query_hash={query_hash} "
                    f"query_length={len(query)}"
                )
                return results

        except Exception as e:
            raise DatabaseError(f"Content search failed: {e}", operation="search") from e

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
                        id, content, source, metadata, session_id,
                        compressed, compressed_into_id,
                        created_at, updated_at
                    FROM archival_memories
                    WHERE id = $1::uuid
                        AND user_id = $2
                    """,
                    memory_id,
                    self.user_id,
                )

                if not row:
                    return None

                return {
                    "memory_id": str(row["id"]),
                    "content": row["content"],
                    "source": row["source"],
                    "metadata": row["metadata"],
                    "session_id": row["session_id"],
                    "compressed": row["compressed"],
                    "compressed_into_id": str(row["compressed_into_id"]) if row["compressed_into_id"] else None,
                    "created_at": self._to_utc(row["created_at"]),
                    "updated_at": self._to_utc(row["updated_at"]),
                }

        except Exception as e:
            raise DatabaseError(f"Failed to get archival memory: {e}", operation="get") from e

    async def update_metadata(self, memory_id: str, metadata: dict[str, Any]) -> bool:
        """Update metadata for a memory.

        Args:
            memory_id: UUID of the memory.
            metadata: New metadata to merge with existing.

        Returns:
            True if updated, False if memory not found.
        """
        try:
            async with self.repository.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE archival_memories
                    SET metadata = metadata || $2::jsonb,
                        updated_at = NOW()
                    WHERE id = $1::uuid
                        AND user_id = $3
                    """,
                    memory_id,
                    metadata,
                    self.user_id,
                )
                success = self._affected_rows(result) > 0
                if success:
                    logger.info(f"Updated metadata for archival memory {memory_id}")
                return success

        except Exception as e:
            raise DatabaseError(f"Failed to update metadata: {e}", operation="update") from e

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory from archival storage.

        Args:
            memory_id: UUID of the memory to delete.

        Returns:
            True if deleted, False if not found.
        """
        try:
            async with self.repository.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM archival_memories
                    WHERE id = $1::uuid
                        AND user_id = $2
                    """,
                    memory_id,
                    self.user_id,
                )
                success = self._affected_rows(result) > 0
                if success:
                    logger.info(f"Deleted archival memory {memory_id}")
                return success

        except Exception as e:
            raise DatabaseError(f"Failed to delete memory: {e}", operation="delete") from e

    async def get_session_memories(
        self,
        session_id: str,
        include_compressed: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get all memories for a specific session.

        Args:
            session_id: Session identifier.
            include_compressed: Whether to include compressed memories.
            limit: Maximum results to return.

        Returns:
            List of memory dicts for the session.
        """
        try:
            async with self.repository.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        id, content, source, metadata, session_id,
                        compressed, compressed_into_id,
                        created_at, updated_at
                    FROM archival_memories
                    WHERE user_id = $1
                        AND session_id = $2
                        AND ($3 = true OR compressed = false)
                    ORDER BY created_at ASC
                    LIMIT $4
                    """,
                    self.user_id,
                    session_id,
                    include_compressed,
                    limit,
                )

                return [
                    {
                        "memory_id": str(row["id"]),
                        "content": row["content"],
                        "source": row["source"],
                        "metadata": row["metadata"],
                        "session_id": row["session_id"],
                        "compressed": row["compressed"],
                        "compressed_into_id": str(row["compressed_into_id"]) if row["compressed_into_id"] else None,
                        "created_at": self._to_utc(row["created_at"]),
                        "updated_at": self._to_utc(row["updated_at"]),
                    }
                    for row in rows
                ]

        except Exception as e:
            raise DatabaseError(f"Failed to get session memories: {e}", operation="get") from e
