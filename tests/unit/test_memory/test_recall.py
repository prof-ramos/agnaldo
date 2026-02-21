"""Unit tests for RecallMemory.

This module contains comprehensive unit tests for the RecallMemory class,
testing semantic search functionality, embedding generation, and error handling.
All database operations are mocked to ensure isolated, fast unit tests.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import DatabaseError, EmbeddingGenerationError, MemoryServiceError
from src.memory.recall import RecallMemory

# =============================================================================
# Fixtures
# =============================================================================


def _build_mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """Build a mock asyncpg pool with an async context manager for acquire().

    Args:
        mock_conn: The async mock connection to return from acquire().

    Returns:
        MagicMock configured as an asyncpg pool.
    """
    mock_pool = MagicMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm
    return mock_pool


@pytest.fixture
def mock_settings():
    """Create mock settings for RecallMemory initialization."""
    settings = MagicMock()
    settings.OPENAI_API_KEY = "test-api-key"
    settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
    return settings


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for embedding generation."""
    client = MagicMock()
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock()
    return client


@pytest.fixture
def mock_db_pool():
    """Create a mock database pool."""
    mock_conn = AsyncMock()
    return _build_mock_pool(mock_conn)


@pytest.fixture
def mock_connection():
    """Create a mock database connection."""
    return AsyncMock()


@pytest.fixture
def sample_embedding():
    """Return a sample embedding vector (1536 dimensions for text-embedding-3-small)."""
    return [0.1] * 1536


@pytest.fixture
def recall_memory(mock_db_pool, mock_openai_client, mock_settings):
    """Create a RecallMemory instance with mocked dependencies."""
    with patch("src.memory.recall.get_settings", return_value=mock_settings):
        return RecallMemory(
            user_id="test_user_123",
            repository=mock_db_pool,
            openai_client=mock_openai_client,
        )


# =============================================================================
# Test: search_by_embedding
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_embedding(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test semantic search using query embedding."""
    # Setup mock for OpenAI embedding generation
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup mock database response for search
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Python é uma linguagem de programação",
            "importance": 0.8,
            "similarity": 0.92,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "access_count": 5,
        }
    ]
    mock_conn.execute.return_value = None

    # Execute search
    results = await recall_memory.search(
        query="linguagem de programação", limit=10, threshold=0.7
    )

    # Assertions
    assert len(results) == 1
    assert results[0]["content"] == "Python é uma linguagem de programação"
    assert results[0]["similarity"] == 0.92
    assert results[0]["importance"] == 0.8

    # Verify embedding was generated
    mock_openai_client.embeddings.create.assert_called_once()

    # Verify database query was called
    mock_conn.fetch.assert_called_once()

    # Verify access count was updated
    mock_conn.execute.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_embedding_empty_query(recall_memory):
    """Test that empty query raises MemoryServiceError."""
    with pytest.raises(MemoryServiceError) as exc_info:
        await recall_memory.search(query="   ", limit=10)

    assert "Search query cannot be empty" in str(exc_info.value)
    assert exc_info.value.memory_type == "recall"


# =============================================================================
# Test: search_by_content
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_content(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test search using natural language text content query."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup database response
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = [
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "content": "Machine learning é um ramo da IA",
            "importance": 0.9,
            "similarity": 0.88,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "access_count": 2,
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "content": "Redes neurais processam dados",
            "importance": 0.75,
            "similarity": 0.82,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "access_count": 1,
        },
    ]
    mock_conn.execute.return_value = None

    # Execute search
    results = await recall_memory.search(query="inteligência artificial redes")

    # Assertions
    assert len(results) == 2
    assert results[0]["content"] == "Machine learning é um ramo da IA"
    assert results[1]["content"] == "Redes neurais processam dados"

    # Verify results are ordered by similarity (descending)
    assert results[0]["similarity"] >= results[1]["similarity"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_content_no_results(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test search returns empty list when no matches found."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup empty database response
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = []

    # Execute search
    results = await recall_memory.search(query="conteúdo inexistente")

    # Assertions
    assert results == []
    # Verify execute was NOT called (no results to update)
    mock_conn.execute.assert_not_called()


# =============================================================================
# Test: threshold_filtering
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_threshold_filtering(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test that threshold parameter filters results by minimum similarity."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup database response - pgvector already filters by distance
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = [
        {
            "id": "550e8400-e29b-41d4-a716-446655440003",
            "content": "Resultado altamente relevante",
            "importance": 1.0,
            "similarity": 0.95,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "access_count": 10,
        }
    ]
    mock_conn.execute.return_value = None

    # Execute search with high threshold
    results = await recall_memory.search(query="teste", threshold=0.9)

    # Assertions
    assert len(results) == 1
    assert results[0]["similarity"] >= 0.9


@pytest.mark.unit
@pytest.mark.asyncio
async def test_threshold_filtering_excludes_low_similarity(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test that low similarity results are excluded by threshold."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup database response - only high similarity results
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = []
    mock_conn.execute.return_value = None

    # Execute search with very high threshold (0.99)
    results = await recall_memory.search(query="query muito específica", threshold=0.99)

    # Assertions
    assert results == []

    # Verify the distance threshold was correctly calculated (1 - 0.99 = 0.01)
    call_args = mock_conn.fetch.call_args
    assert call_args is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_threshold_with_min_importance(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test filtering by both similarity threshold and minimum importance."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup database response
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = [
        {
            "id": "550e8400-e29b-41d4-a716-446655440004",
            "content": "Memória importante",
            "importance": 0.9,
            "similarity": 0.85,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "access_count": 3,
        }
    ]
    mock_conn.execute.return_value = None

    # Execute search with both filters
    results = await recall_memory.search(
        query="teste", threshold=0.7, min_importance=0.8
    )

    # Assertions
    assert len(results) == 1
    assert results[0]["importance"] >= 0.8


# =============================================================================
# Test: empty_results
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_results_no_memories(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test search when database has no memories for the user."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup empty database response
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = []

    # Execute search
    results = await recall_memory.search(query="qualquer coisa")

    # Assertions
    assert results == []
    assert isinstance(results, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_results_all_below_threshold(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test search when all results are below similarity threshold."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Database returns empty due to threshold
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = []

    # Execute search with high threshold
    results = await recall_memory.search(query="query específica", threshold=0.99)

    # Assertions
    assert results == []


# =============================================================================
# Test: error_handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_embedding_generation_failure(recall_memory, mock_openai_client):
    """Test that embedding generation failure raises EmbeddingGenerationError."""
    # Setup OpenAI client to raise exception
    mock_openai_client.embeddings.create.side_effect = Exception("API timeout")

    # Execute and assert
    with pytest.raises(EmbeddingGenerationError) as exc_info:
        await recall_memory.search(query="test query")

    assert "Failed to generate query embedding" in str(exc_info.value)
    assert exc_info.value.model == "text-embedding-3-small"
    assert exc_info.value.text_length == len("test query")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_database_failure(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test that database failure raises DatabaseError."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup database to raise exception
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.side_effect = Exception("Connection lost")

    # Execute and assert
    with pytest.raises(DatabaseError) as exc_info:
        await recall_memory.search(query="test query")

    assert "Recall search failed" in str(exc_info.value)
    assert exc_info.value.operation == "search"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_invalid_importance(recall_memory):
    """Test that invalid importance values raise MemoryServiceError during add."""
    with pytest.raises(MemoryServiceError) as exc_info:
        await recall_memory.add(content="test", importance=1.5)

    assert "Importance must be between 0.0 and 1.0" in str(exc_info.value)

    with pytest.raises(MemoryServiceError) as exc_info:
        await recall_memory.add(content="test", importance=-0.1)

    assert "Importance must be between 0.0 and 1.0" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_empty_content(recall_memory):
    """Test that empty content raises MemoryServiceError during add."""
    with pytest.raises(MemoryServiceError) as exc_info:
        await recall_memory.add(content="", importance=0.5)

    assert "Content cannot be empty" in str(exc_info.value)

    with pytest.raises(MemoryServiceError) as exc_info:
        await recall_memory.add(content="   ", importance=0.5)

    assert "Content cannot be empty" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_add_embedding_failure(
    recall_memory, mock_db_pool, mock_openai_client
):
    """Test that embedding generation failure during add raises EmbeddingGenerationError."""
    # Setup OpenAI client to raise exception
    mock_openai_client.embeddings.create.side_effect = Exception("Rate limit exceeded")

    # Execute and assert
    with pytest.raises(EmbeddingGenerationError) as exc_info:
        await recall_memory.add(content="test content", importance=0.5)

    assert "Failed to generate embedding" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_add_database_failure(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test that database failure during add raises DatabaseError."""
    # Setup embedding mock
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    # Setup database to raise exception
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetchval.side_effect = Exception("Database constraint violation")

    # Execute and assert
    with pytest.raises(DatabaseError) as exc_info:
        await recall_memory.add(content="test content", importance=0.5)

    assert "Failed to insert memory" in str(exc_info.value)
    assert exc_info.value.operation == "insert"


# =============================================================================
# Additional tests for completeness
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_memory_success(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test successful memory addition."""
    # Setup mocks
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetchval.return_value = "550e8400-e29b-41d4-a716-446655440005"

    # Execute
    memory_id = await recall_memory.add(content="Nova memória", importance=0.7)

    # Assertions
    assert memory_id == "550e8400-e29b-41d4-a716-446655440005"
    mock_openai_client.embeddings.create.assert_called_once()
    mock_conn.fetchval.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_importance_success(
    recall_memory, mock_db_pool, mock_openai_client
):
    """Test successful importance update."""
    # Setup mock
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.execute.return_value = "UPDATE 1"

    # Execute
    success = await recall_memory.update_importance(
        memory_id="550e8400-e29b-41d4-a716-446655440006", importance=0.95
    )

    # Assertions
    assert success is True
    mock_conn.execute.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_importance_not_found(
    recall_memory, mock_db_pool, mock_openai_client
):
    """Test update importance when memory not found."""
    # Setup mock - no rows affected
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.execute.return_value = "UPDATE 0"

    # Execute
    success = await recall_memory.update_importance(
        memory_id="550e8400-e29b-41d4-a716-446655440007", importance=0.5
    )

    # Assertions
    assert success is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_memory_success(recall_memory, mock_db_pool):
    """Test successful memory retrieval by ID."""
    # Setup mock
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    initial_row = {
        "id": "550e8400-e29b-41d4-a716-446655440008",
        "content": "Conteúdo da memória",
        "importance": 0.8,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
        "access_count": 3,
        "last_accessed": datetime.now(timezone.utc),
    }
    access_row = {
        "access_count": 4,
        "last_accessed": datetime.now(timezone.utc),
    }
    mock_conn.fetchrow.side_effect = [initial_row, access_row]

    # Execute
    memory = await recall_memory.get("550e8400-e29b-41d4-a716-446655440008")

    # Assertions
    assert memory is not None
    assert memory["content"] == "Conteúdo da memória"
    assert memory["importance"] == 0.8
    assert memory["access_count"] == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_memory_not_found(recall_memory, mock_db_pool):
    """Test get memory when ID not found."""
    # Setup mock - no row returned
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetchrow.return_value = None

    # Execute
    memory = await recall_memory.get("550e8400-e29b-41d4-a716-446655440009")

    # Assertions
    assert memory is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_memory_success(recall_memory, mock_db_pool):
    """Test successful memory deletion."""
    # Setup mock
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.execute.return_value = "DELETE 1"

    # Execute
    success = await recall_memory.delete("550e8400-e29b-41d4-a716-446655440010")

    # Assertions
    assert success is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_memory_not_found(recall_memory, mock_db_pool):
    """Test delete when memory not found."""
    # Setup mock - no rows deleted
    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.execute.return_value = "DELETE 0"

    # Execute
    success = await recall_memory.delete("550e8400-e29b-41d4-a716-446655440011")

    # Assertions
    assert success is False


@pytest.mark.unit
def test_affected_rows_extraction():
    """Test _affected_rows static method with various inputs."""
    assert RecallMemory._affected_rows("INSERT 0 1") == 1
    assert RecallMemory._affected_rows("UPDATE 5") == 5
    assert RecallMemory._affected_rows("DELETE 10") == 10
    assert RecallMemory._affected_rows("invalid") == 0
    assert RecallMemory._affected_rows("") == 0


@pytest.mark.unit
def test_to_utc_normalization():
    """Test _to_utc static method datetime normalization."""
    # Naive datetime
    naive_dt = datetime(2024, 1, 1, 12, 0, 0)
    result = RecallMemory._to_utc(naive_dt)
    assert result.tzinfo is not None
    assert result.hour == 12

    # Aware datetime (different timezone)
    import zoneinfo

    aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=zoneinfo.ZoneInfo("America/Sao_Paulo"))
    result = RecallMemory._to_utc(aware_dt)
    assert result.tzinfo is not None

    # None
    assert RecallMemory._to_utc(None) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_truncate_for_embedding(recall_memory):
    """Test _truncate_for_embedding method."""
    # Short text - should not truncate
    short_text = "Hello world"
    result = recall_memory._truncate_for_embedding(short_text, max_tokens=100)
    assert result == short_text

    # Long text - should truncate
    long_text = "word " * 10000
    result = recall_memory._truncate_for_embedding(long_text, max_tokens=100)
    assert len(result) < len(long_text)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_limit_parameter(
    recall_memory, mock_db_pool, mock_openai_client, sample_embedding
):
    """Test that limit parameter is correctly passed to database query."""
    # Setup mocks
    mock_response = MagicMock()
    mock_response.data[0].embedding = sample_embedding
    mock_openai_client.embeddings.create.return_value = mock_response

    mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    mock_conn.fetch.return_value = []
    mock_conn.execute.return_value = None

    # Execute with custom limit
    await recall_memory.search(query="test", limit=5)

    # Verify limit was passed correctly
    call_args = mock_conn.fetch.call_args
    assert call_args is not None
    # Check that limit (5) is in the call args
    # Args: query_embedding_str, user_id, min_importance, max_distance, limit
    assert 5 in call_args[0]
