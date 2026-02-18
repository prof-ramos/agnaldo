"""Context offloading module for caching and on-demand loading."""

from asyncio import Lock
from typing import Any


class ContextOffloading:
    """Offloads context to cache with on-demand loading capabilities."""

    def __init__(self, maxsize: int = 100) -> None:
        """Initialize the offloading manager.

        Args:
            maxsize: Maximum number of cached items
        """
        self._maxsize = maxsize
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = Lock()
        self._priority_index: dict[int, list[str]] = {}

    async def offload(self, key: str, content: str, priority: int = 0) -> str:
        """Offload context content to cache.

        Args:
            key: Unique identifier for the content
            content: Content to offload
            priority: Priority level (higher = more important, default: 0)

        Returns:
            The key used for storage
        """
        async with self._lock:
            self._cache[key] = {"content": content, "priority": priority}
            self._update_priority_index(key, priority)
            await self._evict_if_needed()
        return key

    async def load_on_demand(self, key: str) -> str | None:
        """Load offloaded context by key.

        Args:
            key: Identifier of the content to load

        Returns:
            The cached content or None if not found
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry:
                # Update access time by re-inserting
                previous_priority = int(entry.get("priority", 0))
                entry["priority"] = previous_priority + 1
                self._reindex_priority(key, previous_priority, int(entry["priority"]))
                content = entry["content"]
                return str(content) if content is not None else None
        return None

    async def remove(self, key: str) -> bool:
        """Remove content from cache.

        Args:
            key: Identifier of the content to remove

        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            if key in self._cache:
                priority = self._cache[key]["priority"]
                del self._cache[key]
                if priority in self._priority_index and key in self._priority_index[priority]:
                    self._priority_index[priority].remove(key)
                return True
        return False

    async def clear(self) -> None:
        """Clear all cached content."""
        async with self._lock:
            self._cache.clear()
            self._priority_index.clear()

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache size, keys, and priority distribution
        """
        async with self._lock:
            return {
                "size": len(self._cache),
                "keys": list(self._cache.keys()),
                "priorities": {
                    p: len(keys) for p, keys in self._priority_index.items()
                },
            }

    def _update_priority_index(self, key: str, priority: int) -> None:
        """Update the priority index for a key."""
        if priority not in self._priority_index:
            self._priority_index[priority] = []
        if key not in self._priority_index[priority]:
            self._priority_index[priority].append(key)

    def _reindex_priority(self, key: str, old_priority: int, new_priority: int) -> None:
        """Move key between priority buckets without leaving stale references."""
        if old_priority in self._priority_index and key in self._priority_index[old_priority]:
            self._priority_index[old_priority].remove(key)
            if not self._priority_index[old_priority]:
                del self._priority_index[old_priority]
        self._update_priority_index(key, new_priority)

    async def _evict_if_needed(self) -> None:
        """Evict lowest priority items when cache is full."""
        if len(self._cache) <= self._maxsize:
            return

        # Find lowest priority keys
        lowest_priority = min(self._priority_index.keys()) if self._priority_index else 0
        keys_to_evict = self._priority_index.get(lowest_priority, [])

        if keys_to_evict:
            key_to_remove = keys_to_evict[0]
            del self._cache[key_to_remove]
            self._priority_index[lowest_priority].remove(key_to_remove)
            if not self._priority_index[lowest_priority]:
                del self._priority_index[lowest_priority]
