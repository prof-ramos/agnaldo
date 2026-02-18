"""Unit tests for ArchivalMemory validation and edge cases."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import DatabaseError, MemoryServiceError
from src.memory.archival import ArchivalMemory


def _build_mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """Build a mock asyncpg pool with an async context manager for acquire()."""
    mock_pool = MagicMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm
    return mock_pool


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_empty_content_raises():
    """ArchivalMemory.add should reject empty content."""
    archival = ArchivalMemory(user_id="user-1", repository=MagicMock())

    with pytest.raises(MemoryServiceError, match="Content cannot be empty"):
        await archival.add(content=" ", source="discord")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_empty_source_raises():
    """ArchivalMemory.add should reject empty source."""
    archival = ArchivalMemory(user_id="user-1", repository=MagicMock())

    with pytest.raises(MemoryServiceError, match="Source cannot be empty"):
        await archival.add(content="Hello", source=" ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_content_empty_query_raises():
    """ArchivalMemory.search_by_content should reject empty query."""
    archival = ArchivalMemory(user_id="user-1", repository=MagicMock())

    with pytest.raises(MemoryServiceError, match="Search query cannot be empty"):
        await archival.search_by_content(query="   ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_metadata_invalid_filters_raises():
    """ArchivalMemory.search_by_metadata should validate filters."""
    archival = ArchivalMemory(user_id="user-1", repository=MagicMock())

    with pytest.raises(MemoryServiceError, match="At least one filter is required"):
        await archival.search_by_metadata(filters={})

    with pytest.raises(DatabaseError, match="Invalid filter key path"):
        await archival.search_by_metadata(filters={"bad$key": "value"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_compress_no_rows_returns_empty_stats():
    """ArchivalMemory.compress should return zero stats when no rows exist."""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []
    transaction_cm = AsyncMock()
    transaction_cm.__aenter__.return_value = None
    transaction_cm.__aexit__.return_value = None
    mock_conn.transaction = MagicMock(return_value=transaction_cm)
    mock_pool = _build_mock_pool(mock_conn)

    archival = ArchivalMemory(user_id="user-1", repository=mock_pool)
    result = await archival.compress(session_id="session-1")

    assert result == {
        "compressed_memory_id": None,
        "original_count": 0,
        "compressed_count": 0,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_metadata_not_found_returns_false():
    """ArchivalMemory.update_metadata should return False when no rows updated."""
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "UPDATE 0"
    mock_pool = _build_mock_pool(mock_conn)

    archival = ArchivalMemory(user_id="user-1", repository=mock_pool)
    success = await archival.update_metadata(memory_id="00000000-0000-0000-0000-000000000000", metadata={"k": "v"})

    assert success is False
