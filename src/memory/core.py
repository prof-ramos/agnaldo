"""Core Memory implementation for storing important facts about users.

Core Memory (Tier 1) - High-speed, frequently accessed memory for:
- User preferences and settings
- Important facts the bot should remember
- Frequently accessed information
- User-specific configuration

This tier provides instant access to critical information without
requiring semantic search or database queries.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.exceptions import DatabaseError, MemoryServiceError
from src.schemas.memory import CoreMemoryItem


class CoreMemory:
    """Core Memory tier for fast access to important user facts.

    This tier stores critical information that should be instantly
    accessible, such as user preferences, important facts, and
    frequently accessed data.

    Attributes:
        user_id: User identifier for memory isolation.
        repository: Database connection pool (asyncpg).
        max_items: Maximum number of items to store in memory.
        max_tokens: Maximum tokens allowed in core memory.
        _cache: In-memory cache for fast access.
    """

    def __init__(
        self,
        user_id: str,
        repository,
        max_items: int = 100,
        max_tokens: int = 10000,
    ) -> None:
        """Initialize CoreMemory.

        Args:
            user_id: User identifier for memory isolation.
            repository: asyncpg connection pool or database connection.
            max_items: Maximum items to store in core memory.
            max_tokens: Maximum tokens allowed in core memory.
        """
        self.user_id = user_id
        self.repository = repository
        self.max_items = max_items
        self.max_tokens = max_tokens
        self._cache: dict[str, CoreMemoryItem] = {}
        self._loaded = False
        self._load_lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task[None]] = set()

    @staticmethod
    def _affected_rows(command_tag: str) -> int:
        """Extract affected row count from asyncpg command tag."""
        try:
            return int(command_tag.split()[-1])
        except (ValueError, IndexError):
            return 0

    def _schedule_access_update(self, key: str) -> None:
        """Schedule a safe background update for access counters."""
        task = asyncio.create_task(self._update_access_count(key))
        self._background_tasks.add(task)

        def _done_callback(done_task: asyncio.Task[None]) -> None:
            self._background_tasks.discard(done_task)
            try:
                done_task.result()
            except Exception as exc:
                logger.debug(f"Background access update failed for {key}: {exc}")

        task.add_done_callback(_done_callback)

    async def _ensure_loaded(self) -> None:
        """Ensure core memory is loaded from database."""
        if self._loaded:
            return

        async with self._load_lock:
            if self._loaded:
                return

            try:
                async with self.repository.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT
                            id, key, value, importance, metadata,
                            access_count, last_accessed,
                            created_at, updated_at
                        FROM core_memories
                        WHERE user_id = $1
                        ORDER BY importance DESC, last_accessed DESC NULLS LAST
                        LIMIT $2
                        """,
                        self.user_id,
                        self.max_items,
                    )

                    for row in rows:
                        item = CoreMemoryItem(
                            id=str(row["id"]),
                            content=row["value"],
                            importance=row["importance"] if row["importance"] is not None else 0.5,
                            access_count=row["access_count"] if row["access_count"] is not None else 0,
                            last_accessed=row["last_accessed"],
                            created_at=row["created_at"],
                            metadata={"key": row["key"], **(row["metadata"] or {})},
                        )
                        self._cache[row["key"]] = item

                    self._loaded = True
                    logger.debug(f"Loaded {len(self._cache)} core memories for user {self.user_id}")

            except Exception as e:
                raise DatabaseError(f"Failed to load core memory: {e}", operation="load") from e

    async def add(
        self,
        key: str,
        value: str,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> CoreMemoryItem:
        """Add or update a core memory item.

        Args:
            key: Unique key for the memory item.
            value: Value/content to store.
            importance: Importance score (0.0-1.0).
            metadata: Optional additional metadata.

        Returns:
            The created or updated CoreMemoryItem.

        Raises:
            MemoryServiceError: If key is empty or importance out of range.
            DatabaseError: If database operation fails.
        """
        if not key or not key.strip():
            raise MemoryServiceError("Key cannot be empty", memory_type="core")

        if not 0.0 <= importance <= 1.0:
            raise MemoryServiceError("Importance must be between 0.0 and 1.0", memory_type="core")

        await self._ensure_loaded()

        # Check if we're at capacity and need to evict
        if key not in self._cache and len(self._cache) >= self.max_items:
            await self._evict_least_important()

        try:
            async with self.repository.acquire() as conn:
                # Try to update existing
                existing = await conn.fetchval(
                    """
                    SELECT id FROM core_memories
                    WHERE user_id = $1 AND key = $2
                    """,
                    self.user_id,
                    key,
                )

                if existing:
                    # Update existing
                    await conn.execute(
                        """
                        UPDATE core_memories
                        SET value = $1,
                            importance = $2,
                            metadata = $3::jsonb,
                            updated_at = NOW()
                        WHERE id = $4::uuid
                        """,
                        value,
                        importance,
                        metadata or {},
                        existing,
                    )
                    memory_id = str(existing)
                    logger.debug(f"Updated core memory {key}")
                else:
                    # Insert new
                    memory_id = await conn.fetchval(
                        """
                        INSERT INTO core_memories
                            (user_id, key, value, importance, metadata, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5::jsonb, NOW(), NOW())
                        RETURNING id
                        """,
                        self.user_id,
                        key,
                        value,
                        importance,
                        metadata or {},
                    )
                    logger.info(f"Added core memory {key}")

        except Exception as e:
            raise DatabaseError(f"Failed to add core memory: {e}", operation="insert") from e

        # Update cache
        existing_item = self._cache.get(key)
        merged_metadata = {"key": key}
        if existing_item is not None:
            merged_metadata.update(existing_item.metadata)
        merged_metadata.update(metadata or {})

        item = CoreMemoryItem(
            id=memory_id,
            content=value,
            importance=importance,
            access_count=existing_item.access_count if existing_item else 0,
            last_accessed=existing_item.last_accessed if existing_item else None,
            created_at=existing_item.created_at if existing_item else datetime.now(timezone.utc),
            metadata=merged_metadata,
        )
        self._cache[key] = item

        return item

    async def get(self, key: str, default: str | None = None) -> str | None:
        """Get a core memory value by key.

        Args:
            key: The key to retrieve.
            default: Default value if key not found.

        Returns:
            The value associated with the key, or default if not found.

        Raises:
            MemoryServiceError: If key is empty.
            DatabaseError: If database operation fails.
        """
        if not key:
            raise MemoryServiceError("Key cannot be empty", memory_type="core")

        await self._ensure_loaded()

        item = self._cache.get(key)
        if item is None:
            return default

        # Update access count asynchronously
        self._schedule_access_update(key)

        return item.content

    async def get_all(self) -> dict[str, str]:
        """Get all core memory key-value pairs.

        Returns:
            Dictionary of all core memories.
        """
        await self._ensure_loaded()

        # Update access for all items without unbounded task fan-out
        for key in self._cache:
            await self._update_access_count(key)

        return {key: item.content for key, item in self._cache.items()}

    async def update(
        self,
        key: str,
        value: str | None = None,
        importance: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update an existing core memory item.

        Args:
            key: The key to update.
            value: New value (None to keep current).
            importance: New importance (None to keep current).
            metadata: New metadata to merge.

        Returns:
            True if updated, False if key not found.

        Raises:
            MemoryServiceError: If key is empty or importance out of range.
        """
        if not key:
            raise MemoryServiceError("Key cannot be empty", memory_type="core")

        if importance is not None and not 0.0 <= importance <= 1.0:
            raise MemoryServiceError("Importance must be between 0.0 and 1.0", memory_type="core")

        await self._ensure_loaded()

        if key not in self._cache:
            return False

        try:
            async with self.repository.acquire() as conn:
                # Build update parts dynamically
                updates = []
                params: list[Any] = []
                param_idx = 1

                if value is not None:
                    updates.append(f"value = ${param_idx}")
                    params.append(value)
                    param_idx += 1

                if importance is not None:
                    updates.append(f"importance = ${param_idx}")
                    params.append(importance)
                    param_idx += 1

                if metadata is not None:
                    updates.append(f"metadata = metadata || ${param_idx}::jsonb")
                    params.append(metadata)
                    param_idx += 1

                updates.append("updated_at = NOW()")
                params.extend([self.user_id, key])

                result = await conn.execute(
                    f"""
                    UPDATE core_memories
                    SET {', '.join(updates)}
                    WHERE user_id = ${param_idx} AND key = ${param_idx + 1}
                    """,
                    *params,
                )

                success = self._affected_rows(result) > 0
                if success:
                    # Update cache
                    item = self._cache[key]
                    if value is not None:
                        item.content = value
                    if importance is not None:
                        item.importance = importance
                    if metadata is not None:
                        item.metadata.update(metadata)

                    logger.debug(f"Updated core memory {key}")

                return success

        except Exception as e:
            raise DatabaseError(f"Failed to update core memory: {e}", operation="update") from e

    async def delete(self, key: str) -> bool:
        """Delete a core memory item.

        Args:
            key: The key to delete.

        Returns:
            True if deleted, False if key not found.

        Raises:
            MemoryServiceError: If key is empty.
        """
        if not key:
            raise MemoryServiceError("Key cannot be empty", memory_type="core")

        await self._ensure_loaded()

        if key not in self._cache:
            return False

        try:
            async with self.repository.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM core_memories
                    WHERE user_id = $1 AND key = $2
                    """,
                    self.user_id,
                    key,
                )

                success = self._affected_rows(result) > 0
                if success:
                    del self._cache[key]
                    logger.info(f"Deleted core memory {key}")

                return success

        except Exception as e:
            raise DatabaseError(f"Failed to delete core memory: {e}", operation="delete") from e

    async def clear(self) -> int:
        """Clear all core memories for the user.

        Returns:
            Number of items cleared.
        """
        await self._ensure_loaded()

        count = len(self._cache)

        try:
            async with self.repository.acquire() as conn:
                await conn.execute(
                    """
                    DELETE FROM core_memories
                    WHERE user_id = $1
                    """,
                    self.user_id,
                )

            self._cache.clear()
            logger.info(f"Cleared {count} core memories")

            return count

        except Exception as e:
            raise DatabaseError(f"Failed to clear core memories: {e}", operation="delete") from e

    async def search(self, query: str, limit: int = 10) -> list[str]:
        """Search core memories by key or content.

        Args:
            query: Search query.
            limit: Maximum results to return.

        Returns:
            List of matching keys.
        """
        await self._ensure_loaded()

        query_lower = query.lower()
        results: list[str] = []

        for key, item in self._cache.items():
            if query_lower in key.lower() or query_lower in item.content.lower():
                results.append(key)
                if len(results) >= limit:
                    break

        return results

    async def _evict_least_important(self) -> None:
        """Evict the least important memory item when at capacity."""
        if not self._cache:
            return

        # Find item with lowest importance and oldest access
        min_aware_datetime = datetime.min.replace(tzinfo=timezone.utc)
        least_important_key = min(
            self._cache.keys(),
            key=lambda k: (
                self._cache[k].importance,
                self._cache[k].last_accessed or min_aware_datetime,
            ),
        )

        logger.warning(f"Evicting core memory {least_important_key} (capacity limit)")
        await self.delete(least_important_key)

    async def _update_access_count(self, key: str) -> None:
        """Update access count and last_accessed timestamp."""
        try:
            async with self.repository.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE core_memories
                    SET access_count = access_count + 1,
                        last_accessed = NOW()
                    WHERE user_id = $1 AND key = $2
                    """,
                    self.user_id,
                    key,
                )

                # Update cache if item exists
                if key in self._cache:
                    self._cache[key].access_count += 1
                    self._cache[key].last_accessed = datetime.now(timezone.utc)

        except Exception as e:
            logger.warning(f"Failed to update access count for {key}: {e}")

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about core memory usage.

        Returns:
            Dictionary with stats.
        """
        await self._ensure_loaded()

        total_importance = sum(item.importance for item in self._cache.values())
        avg_importance = total_importance / len(self._cache) if self._cache else 0

        return {
            "tier": "core",
            "user_id": self.user_id,
            "item_count": len(self._cache),
            "max_items": self.max_items,
            "usage_percent": len(self._cache) / self.max_items * 100 if self.max_items else 0,
            "avg_importance": avg_importance,
            "total_access_count": sum(item.access_count for item in self._cache.values()),
        }
