"""Integration tests for knowledge graph operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import DatabaseError, MemoryServiceError
from src.knowledge.graph import KnowledgeGraph


def _build_mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """Build a mock asyncpg pool with an async context manager for acquire()."""
    mock_pool = MagicMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm
    return mock_pool


@pytest.mark.asyncio
async def test_graph_add_node():
    """Test adding a node to the knowledge graph."""
    mock_conn = AsyncMock()

    # Mock fetchval for insert
    mock_conn.fetchval.return_value = "node-uuid-123"

    # Mock fetchrow for getting created node
    mock_conn.fetchrow.return_value = {
        "id": "node-uuid-123",
        "label": "Python",
        "node_type": "language",
        "properties": {},
        "embedding": None,
        "created_at": None,
        "updated_at": None,
    }

    mock_pool = _build_mock_pool(mock_conn)

    # Mock OpenAI client
    mock_openai = MagicMock()
    mock_openai.embeddings.create = AsyncMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )

    graph = KnowledgeGraph(user_id="test_user", repository=mock_pool, openai_client=mock_openai)

    # Add node
    node = await graph.add_node("Python", node_type="language")
    assert node.label == "Python"
    assert node.node_type == "language"


@pytest.mark.asyncio
async def test_graph_add_edge():
    """Test adding an edge to the knowledge graph."""
    mock_conn = AsyncMock()

    # Mock fetchval for edge insert
    mock_conn.fetchval.return_value = "edge-uuid-123"

    # Mock fetchrow for getting created edge
    mock_conn.fetchrow.return_value = {
        "id": "edge-uuid-123",
        "source_id": "source-uuid",
        "target_id": "target-uuid",
        "edge_type": "relates_to",
        "weight": 0.8,
        "properties": {},
        "created_at": None,
    }

    mock_pool = _build_mock_pool(mock_conn)

    graph = KnowledgeGraph(user_id="test_user", repository=mock_pool, openai_client=None)

    # Add edge
    edge = await graph.add_edge(
        source_id="source-uuid",
        target_id="target-uuid",
        edge_type="relates_to",
        weight=0.8
    )
    assert edge.edge_type == "relates_to"
    assert edge.weight == 0.8


@pytest.mark.asyncio
async def test_graph_search_nodes():
    """Test semantic search in knowledge graph."""
    mock_conn = AsyncMock()

    # Mock fetch for search results
    mock_conn.fetch.return_value = [
        {
            "id": "node-uuid-1",
            "label": "Python Programming",
            "node_type": "language",
            "properties": {},
            "similarity": 0.85,
            "created_at": None,
        },
        {
            "id": "node-uuid-2",
            "label": "JavaScript",
            "node_type": "language",
            "properties": {},
            "similarity": 0.72,
            "created_at": None,
        },
    ]

    mock_pool = _build_mock_pool(mock_conn)

    # Mock OpenAI client
    mock_openai = MagicMock()
    mock_openai.embeddings.create = AsyncMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )

    graph = KnowledgeGraph(user_id="test_user", repository=mock_pool, openai_client=mock_openai)

    # Search
    results = await graph.search_nodes(query="programming languages", limit=5)
    assert len(results) == 2
    assert results[0]["similarity"] == 0.85


@pytest.mark.asyncio
async def test_graph_get_neighbors():
    """Test getting neighboring nodes."""
    mock_conn = AsyncMock()

    # Mock fetch for neighbors
    mock_conn.fetch.return_value = [
        {
            "id": "neighbor-uuid-1",
            "label": "Library",
            "node_type": "concept",
            "properties": {},
        },
        {
            "id": "neighbor-uuid-2",
            "label": "Framework",
            "node_type": "concept",
            "properties": {},
        },
    ]

    mock_pool = _build_mock_pool(mock_conn)

    graph = KnowledgeGraph(user_id="test_user", repository=mock_pool, openai_client=None)

    # Get neighbors
    neighbors = await graph.get_neighbors(node_id="some-node-uuid")
    assert len(neighbors) == 2
    assert neighbors[0].label == "Library"


@pytest.mark.asyncio
async def test_graph_add_node_empty_label_raises():
    """Test that empty node label raises MemoryServiceError."""
    graph = KnowledgeGraph(user_id="test_user", repository=MagicMock(), openai_client=None)

    with pytest.raises(MemoryServiceError, match="Label cannot be empty"):
        await graph.add_node("   ")


@pytest.mark.asyncio
async def test_graph_add_edge_empty_type_raises():
    """Test that empty edge type raises MemoryServiceError."""
    graph = KnowledgeGraph(user_id="test_user", repository=MagicMock(), openai_client=None)

    with pytest.raises(MemoryServiceError, match="Edge type cannot be empty"):
        await graph.add_edge("source-uuid", "target-uuid", "   ")


@pytest.mark.asyncio
async def test_graph_generate_embedding_dimension_mismatch():
    """Test that embedding dimension mismatch raises MemoryServiceError."""
    mock_conn = AsyncMock()
    mock_pool = _build_mock_pool(mock_conn)

    mock_openai = MagicMock()
    mock_openai.embeddings.create = AsyncMock(
        return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 10)])
    )

    graph = KnowledgeGraph(user_id="test_user", repository=mock_pool, openai_client=mock_openai)

    with pytest.raises(MemoryServiceError, match="Failed to generate embedding"):
        await graph.add_node("Python", node_type="language")


@pytest.mark.asyncio
async def test_graph_search_nodes_database_error():
    """Test that database errors during search are wrapped as DatabaseError."""
    mock_conn = AsyncMock()
    mock_conn.fetch.side_effect = Exception("DB down")
    mock_pool = _build_mock_pool(mock_conn)

    mock_openai = MagicMock()
    mock_openai.embeddings.create = AsyncMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )

    graph = KnowledgeGraph(user_id="test_user", repository=mock_pool, openai_client=mock_openai)

    with pytest.raises(DatabaseError, match="Failed to search knowledge nodes"):
        await graph.search_nodes(query="python", limit=5)
