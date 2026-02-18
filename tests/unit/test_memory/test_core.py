"""Unit tests for CoreMemory validation and error handling."""

from unittest.mock import MagicMock

import pytest

from src.exceptions import MemoryServiceError
from src.memory.core import CoreMemory


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_empty_key_raises():
    """CoreMemory.add should reject empty keys."""
    memory = CoreMemory(user_id="user-1", repository=MagicMock())

    with pytest.raises(MemoryServiceError, match="Key cannot be empty"):
        await memory.add("", "value")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_invalid_importance_raises():
    """CoreMemory.add should reject importance outside 0..1."""
    memory = CoreMemory(user_id="user-1", repository=MagicMock())

    with pytest.raises(MemoryServiceError, match="Importance must be between 0.0 and 1.0"):
        await memory.add("key", "value", importance=1.5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_empty_key_raises():
    """CoreMemory.get should reject empty keys."""
    memory = CoreMemory(user_id="user-1", repository=MagicMock())

    with pytest.raises(MemoryServiceError, match="Key cannot be empty"):
        await memory.get("")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_invalid_importance_raises():
    """CoreMemory.update should reject invalid importance values."""
    memory = CoreMemory(user_id="user-1", repository=MagicMock())

    with pytest.raises(MemoryServiceError, match="Importance must be between 0.0 and 1.0"):
        await memory.update("key", importance=-0.1)
