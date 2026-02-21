"""Integration tests for memory management."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.archival import ArchivalMemory
from src.memory.core import CoreMemory


def _build_mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """Build a mock asyncpg pool with an async context manager for acquire()."""
    mock_pool = MagicMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm
    return mock_pool


@pytest.mark.asyncio
async def test_core_memory_add_and_get():
    """Test CoreMemory add and get operations."""
    mock_conn = AsyncMock()

    # _ensure_loaded returns no data, then add() sees no existing and inserts
    mock_conn.fetch.return_value = []
    mock_conn.fetchval.side_effect = [None, "mock-uuid-1234"]

    mock_pool = _build_mock_pool(mock_conn)

    # Test
    core_memory = CoreMemory(user_id="test_user", repository=mock_pool)

    # Add
    item = await core_memory.add("test_key", "test_value", importance=0.5)
    assert item.content == "test_value"

    # Get
    value = await core_memory.get("test_key")
    assert value == "test_value"


@pytest.mark.asyncio
async def test_core_memory_update_and_delete():
    """Test CoreMemory update and delete operations."""
    mock_conn = AsyncMock()

    # Seed cache through add(), then update and delete same key
    mock_conn.fetch.return_value = []
    mock_conn.fetchval.side_effect = [None, "mock-uuid-seed"]
    mock_conn.execute.side_effect = ["UPDATE 1", "DELETE 1"]

    mock_pool = _build_mock_pool(mock_conn)

    core_memory = CoreMemory(user_id="test_user", repository=mock_pool)

    await core_memory.add("test_key", "initial_value", importance=0.5)

    # Update
    success = await core_memory.update("test_key", value="updated_value")
    assert success is True

    # Delete
    success = await core_memory.delete("test_key")
    assert success is True


@pytest.mark.asyncio
async def test_archival_memory_add_and_search():
    """Test ArchivalMemory add and search operations."""
    mock_conn = AsyncMock()

    # Mock fetchval for add
    mock_conn.fetchval.return_value = "archival-uuid-123"

    # Mock fetch for search_by_content
    mock_conn.fetch.return_value = [
        {
            "id": "archival-uuid-123",
            "content": "Test memory content",
            "source": "discord",
            "metadata": {},
            "session_id": None,
            "compressed": False,
            "compressed_into_id": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        }
    ]

    mock_pool = _build_mock_pool(mock_conn)

    archival = ArchivalMemory(user_id="test_user", repository=mock_pool)

    # Add
    memory_id = await archival.add(
        content="Important conversation",
        source="discord",
        metadata={"topic": "AI"}
    )
    assert memory_id is not None

    # Search
    results = await archival.search_by_content(query="conversation", limit=10)
    assert len(results) > 0
