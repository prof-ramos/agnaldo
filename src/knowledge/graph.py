"""Knowledge Graph implementation for semantic network management.

This module provides a knowledge graph system using PostgreSQL with pgvector
for storing and querying entities (nodes) and their relationships (edges).

Features:
- Node creation with semantic embeddings
- Edge relationships with weights
- Graph traversal (BFS)
- Semantic similarity search
- Path finding between nodes
"""

from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import UUID, uuid4

from loguru import logger
from openai import AsyncOpenAI
import tiktoken

from src.config.settings import get_settings
from src.exceptions import DatabaseError, MemoryServiceError
from src.schemas.memory import MemoryTier


class KnowledgeNode:
    """Represents a node in the knowledge graph.

    Attributes:
        id: Unique node identifier.
        label: Node label/name.
        node_type: Type/category of the node.
        properties: Additional properties as JSONB.
        embedding: Vector embedding for semantic similarity.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    def __init__(
        self,
        id: str,
        label: str,
        node_type: str | None = None,
        properties: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """Initialize a KnowledgeNode."""
        self.id = id
        self.label = label
        self.node_type = node_type
        self.properties = properties or {}
        self.embedding = embedding
        self.created_at = created_at
        self.updated_at = updated_at


class KnowledgeEdge:
    """Represents an edge in the knowledge graph.

    Attributes:
        id: Unique edge identifier.
        source_id: Source node ID.
        target_id: Target node ID.
        edge_type: Type of relationship.
        weight: Edge weight/strength.
        properties: Additional properties as JSONB.
        created_at: Creation timestamp.
    """

    def __init__(
        self,
        id: str,
        source_id: str,
        target_id: str,
        edge_type: str,
        weight: float | None = None,
        properties: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        """Initialize a KnowledgeEdge."""
        self.id = id
        self.source_id = source_id
        self.target_id = target_id
        self.edge_type = edge_type
        self.weight = weight
        self.properties = properties or {}
        self.created_at = created_at


class KnowledgeGraph:
    """Knowledge Graph for semantic network management.

    Provides operations to create nodes, edges, and query the graph
    with semantic similarity support using pgvector.
    """

    def __init__(
        self,
        user_id: str,
        repository,
        openai_client: AsyncOpenAI | None = None,
        embedding_model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
    ) -> None:
        """Initialize the KnowledgeGraph.

        Args:
            user_id: User identifier for graph isolation.
            repository: asyncpg connection pool.
            openai_client: OpenAI client for embeddings.
            embedding_model: Model name for embeddings.
            embedding_dim: Embedding vector dimension.
        """
        self.user_id = user_id
        self.repository = repository
        self.openai: AsyncOpenAI | None = openai_client
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
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

    def _get_openai_client(self) -> AsyncOpenAI:
        """Get or lazily initialize the OpenAI client."""
        if self.openai is None:
            settings = get_settings()
            self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self.openai

    def _truncate_for_embedding(self, text: str, max_tokens: int = 8191) -> str:
        """Truncate text by token count for embedding calls."""
        tokens = self._encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return self._encoding.decode(tokens[:max_tokens])

    async def add_node(
        self,
        label: str,
        node_type: str | None = None,
        properties: dict[str, Any] | None = None,
        generate_embedding: bool = True,
    ) -> KnowledgeNode:
        """Add a node to the knowledge graph.

        Args:
            label: Node label/name.
            node_type: Type/category of the node.
            properties: Additional properties.
            generate_embedding: Whether to generate embedding.

        Returns:
            The created KnowledgeNode.

        Raises:
            MemoryServiceError: If label is empty.
            DatabaseError: If database operation fails.
        """
        if not label or not label.strip():
            raise MemoryServiceError("Label cannot be empty", memory_type="graph")

        # Generate embedding if requested
        embedding = None
        if generate_embedding:
            embedding = await self._generate_embedding(label)

        try:
            async with self.repository.acquire() as conn:
                node_id = await conn.fetchval(
                    """
                    INSERT INTO knowledge_nodes
                        (user_id, label, node_type, properties, embedding, created_at, updated_at)
                    VALUES ($1, $2, $3, $4::jsonb, $5::vector, NOW(), NOW())
                    RETURNING id
                    """,
                    self.user_id,
                    label,
                    node_type,
                    properties or {},
                    "[" + ",".join(map(str, embedding)) + "]" if embedding else None,
                )

                logger.info(f"Added knowledge node: {label} (type: {node_type})")

                # Fetch the created node
                row = await conn.fetchrow(
                    "SELECT * FROM knowledge_nodes WHERE id = $1::uuid",
                    node_id,
                )

                return KnowledgeNode(
                    id=str(row["id"]),
                    label=row["label"],
                    node_type=row["node_type"],
                    properties=row["properties"],
                    embedding=list(row["embedding"]) if row["embedding"] else None,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

        except Exception as e:
            raise DatabaseError(f"Failed to add knowledge node: {e}", operation="insert") from e

    async def get_node(self, node_id: str) -> KnowledgeNode | None:
        """Get a node by ID.

        Args:
            node_id: Node UUID.

        Returns:
            KnowledgeNode or None if not found.
        """
        try:
            async with self.repository.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, label, node_type, properties, embedding, created_at, updated_at
                    FROM knowledge_nodes
                    WHERE id = $1::uuid AND user_id = $2
                    """,
                    node_id,
                    self.user_id,
                )

                if not row:
                    return None

                return KnowledgeNode(
                    id=str(row["id"]),
                    label=row["label"],
                    node_type=row["node_type"],
                    properties=row["properties"],
                    embedding=list(row["embedding"]) if row["embedding"] else None,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

        except Exception as e:
            raise DatabaseError(f"Failed to get knowledge node: {e}", operation="get") from e

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> KnowledgeEdge:
        """Add an edge between two nodes.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            edge_type: Type of relationship.
            weight: Edge weight/strength.
            properties: Additional properties.

        Returns:
            The created KnowledgeEdge.

        Raises:
            MemoryServiceError: If edge_type is empty.
            DatabaseError: If database operation fails.
        """
        if not edge_type or not edge_type.strip():
            raise MemoryServiceError("Edge type cannot be empty", memory_type="graph")

        try:
            async with self.repository.acquire() as conn:
                edge_id = await conn.fetchval(
                    """
                    INSERT INTO knowledge_edges
                        (source_id, target_id, edge_type, weight, properties, created_at, updated_at)
                    VALUES ($1::uuid, $2::uuid, $3, $4, $5::jsonb, NOW(), NOW())
                    RETURNING id
                    """,
                    source_id,
                    target_id,
                    edge_type,
                    weight,
                    properties or {},
                )

                logger.info(f"Added knowledge edge: {source_id} -> {target_id} ({edge_type})")

                # Fetch the created edge
                row = await conn.fetchrow(
                    "SELECT * FROM knowledge_edges WHERE id = $1::uuid",
                    edge_id,
                )

                return KnowledgeEdge(
                    id=str(row["id"]),
                    source_id=str(row["source_id"]),
                    target_id=str(row["target_id"]),
                    edge_type=row["edge_type"],
                    weight=row["weight"],
                    properties=row["properties"],
                    created_at=row["created_at"],
                )

        except Exception as e:
            raise DatabaseError(f"Failed to add knowledge edge: {e}", operation="insert") from e

    async def get_edges(
        self,
        node_id: str | None = None,
        edge_type: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeEdge]:
        """Get edges from the graph.

        Args:
            node_id: Filter by source or target node (optional).
            edge_type: Filter by edge type (optional).
            limit: Maximum results.

        Returns:
            List of KnowledgeEdge.
        """
        try:
            async with self.repository.acquire() as conn:
                if node_id:
                    # Get edges where node is source or target
                    rows = await conn.fetch(
                        """
                        SELECT
                            e.id, e.source_id, e.target_id, e.edge_type,
                            e.weight, e.properties, e.created_at
                        FROM knowledge_edges e
                        JOIN knowledge_nodes s ON e.source_id = s.id
                        JOIN knowledge_nodes t ON e.target_id = t.id
                        WHERE (s.id = $1::uuid OR t.id = $1::uuid)
                            AND s.user_id = $2
                            AND ($3::text IS NULL OR e.edge_type = $3)
                        ORDER BY e.created_at DESC
                        LIMIT $4
                        """,
                        node_id,
                        self.user_id,
                        edge_type,
                        limit,
                    )
                else:
                    # Get all edges for user
                    rows = await conn.fetch(
                        """
                        SELECT
                            e.id, e.source_id, e.target_id, e.edge_type,
                            e.weight, e.properties, e.created_at
                        FROM knowledge_edges e
                        JOIN knowledge_nodes s ON e.source_id = s.id
                        WHERE s.user_id = $1
                            AND ($2::text IS NULL OR e.edge_type = $2)
                        ORDER BY e.created_at DESC
                        LIMIT $3
                        """,
                        self.user_id,
                        edge_type,
                        limit,
                    )

                return [
                    KnowledgeEdge(
                        id=str(row["id"]),
                        source_id=str(row["source_id"]),
                        target_id=str(row["target_id"]),
                        edge_type=row["edge_type"],
                        weight=row["weight"],
                        properties=row["properties"],
                        created_at=row["created_at"],
                    )
                    for row in rows
                ]

        except Exception as e:
            raise DatabaseError(f"Failed to get knowledge edges: {e}", operation="get") from e

    async def search_nodes(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        node_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search nodes by semantic similarity.

        Args:
            query: Search query.
            limit: Maximum results.
            threshold: Minimum similarity (0-1).
            node_type: Filter by node type.

        Returns:
            List of matching nodes with similarity scores.
        """
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)

            async with self.repository.acquire() as conn:
                max_distance = 1.0 - threshold

                type_filter = "AND ($2::text IS NULL OR node_type = $2)" if node_type else ""

                rows = await conn.fetch(
                    f"""
                    SELECT
                        id, label, node_type, properties,
                        1 - (embedding <=> $1::vector) as similarity,
                        created_at, updated_at
                    FROM knowledge_nodes
                    WHERE user_id = $3
                        {type_filter}
                        AND (embedding <=> $1::vector) <= $4
                    ORDER BY embedding <=> $1::vector
                    LIMIT $5
                    """,
                    "[" + ",".join(map(str, query_embedding)) + "]",
                    node_type,
                    self.user_id,
                    max_distance,
                    limit,
                )

                return [
                    {
                        "node_id": str(row["id"]),
                        "label": row["label"],
                        "node_type": row["node_type"],
                        "properties": row["properties"],
                        "similarity": float(row["similarity"]),
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]

        except Exception as e:
            raise DatabaseError(f"Failed to search knowledge nodes: {e}", operation="search") from e

    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        edge_types: list[str] | None = None,
    ) -> list[str] | None:
        """Find a path between two nodes using BFS.

        Args:
            source_id: Starting node ID.
            target_id: Target node ID.
            max_depth: Maximum search depth.
            edge_types: Allowed edge types (None = all).

        Returns:
            List of node IDs forming the path, or None if no path found.
        """
        try:
            async with self.repository.acquire() as conn:
                # BFS implementation using recursive CTE
                edge_filter = ""
                params = [source_id, target_id, self.user_id, max_depth]
                param_idx = 5

                if edge_types:
                    placeholders = ",".join(f"${param_idx + i}" for i in range(len(edge_types)))
                    edge_filter = f"AND e.edge_type IN ({placeholders})"
                    params.extend(edge_types)

                result = await conn.fetchval(
                    f"""
                    WITH RECURSIVE path AS (
                        SELECT $1::uuid as node_id, ARRAY[$1::uuid] as path, 0 as depth
                        UNION ALL
                        SELECT e.target_id,
                               p.path || e.target_id,
                               p.depth + 1
                        FROM path p
                        JOIN knowledge_edges e ON e.source_id = p.node_id
                        JOIN knowledge_nodes n ON e.target_id = n.id
                        WHERE n.user_id = $3::text
                            AND p.depth < $4
                            AND NOT e.target_id = ANY(p.path)
                            {edge_filter}
                    )
                    SELECT path
                    FROM path
                    WHERE node_id = $2::uuid
                    ORDER BY depth ASC
                    LIMIT 1
                    """,
                    *params,
                )

                if result:
                    return [str(node_id) for node_id in result]
                return None

        except Exception as e:
            raise DatabaseError(f"Failed to find path: {e}", operation="query") from e

    async def get_neighbors(
        self,
        node_id: str,
        edge_type: str | None = None,
        direction: str = "both",
    ) -> list[KnowledgeNode]:
        """Get neighboring nodes.

        Args:
            node_id: Center node ID.
            edge_type: Filter by edge type.
            direction: "out", "in", or "both".

        Returns:
            List of neighboring nodes.
        """
        try:
            async with self.repository.acquire() as conn:
                if direction == "out":
                    rows = await conn.fetch(
                        """
                        SELECT DISTINCT n.id, n.label, n.node_type, n.properties
                        FROM knowledge_nodes n
                        JOIN knowledge_edges e ON e.target_id = n.id
                        WHERE e.source_id = $1::uuid
                            AND n.user_id = $2
                            AND ($3::text IS NULL OR e.edge_type = $3)
                        """,
                        node_id,
                        self.user_id,
                        edge_type,
                    )
                elif direction == "in":
                    rows = await conn.fetch(
                        """
                        SELECT DISTINCT n.id, n.label, n.node_type, n.properties
                        FROM knowledge_nodes n
                        JOIN knowledge_edges e ON e.source_id = n.id
                        WHERE e.target_id = $1::uuid
                            AND n.user_id = $2
                            AND ($3::text IS NULL OR e.edge_type = $3)
                        """,
                        node_id,
                        self.user_id,
                        edge_type,
                    )
                else:  # both
                    rows = await conn.fetch(
                        """
                        SELECT DISTINCT n.id, n.label, n.node_type, n.properties
                        FROM knowledge_nodes n
                        WHERE n.user_id = $2
                            AND n.id IN (
                                SELECT source_id FROM knowledge_edges WHERE target_id = $1::uuid
                                UNION
                                SELECT target_id FROM knowledge_edges WHERE source_id = $1::uuid
                            )
                            AND ($3::text IS NULL OR n.id IN (
                                SELECT target_id FROM knowledge_edges
                                WHERE source_id = $1::uuid AND edge_type = $3
                                UNION
                                SELECT source_id FROM knowledge_edges
                                WHERE target_id = $1::uuid AND edge_type = $3
                            ))
                        """,
                        node_id,
                        self.user_id,
                        edge_type,
                    )

                return [
                    KnowledgeNode(
                        id=str(row["id"]),
                        label=row["label"],
                        node_type=row["node_type"],
                        properties=row["properties"],
                        created_at=None,
                        updated_at=None,
                    )
                    for row in rows
                ]

        except Exception as e:
            raise DatabaseError(f"Failed to get neighbors: {e}", operation="query") from e

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges.

        Args:
            node_id: Node ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        try:
            async with self.repository.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM knowledge_nodes
                    WHERE id = $1::uuid AND user_id = $2
                    """,
                    node_id,
                    self.user_id,
                )

                success = self._affected_rows(result) > 0
                if success:
                    logger.info(f"Deleted knowledge node {node_id}")

                return success

        except Exception as e:
            raise DatabaseError(f"Failed to delete knowledge node: {e}", operation="delete") from e

    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge.

        Args:
            edge_id: Edge ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        try:
            async with self.repository.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM knowledge_edges e
                    USING knowledge_nodes src, knowledge_nodes tgt
                    WHERE e.id = $1::uuid
                        AND src.id = e.source_id
                        AND tgt.id = e.target_id
                        AND src.user_id = $2
                        AND tgt.user_id = $2
                    """,
                    edge_id,
                    self.user_id,
                )

                success = self._affected_rows(result) > 0
                if success:
                    logger.info(f"Deleted knowledge edge {edge_id}")

                return success

        except Exception as e:
            raise DatabaseError(f"Failed to delete knowledge edge: {e}", operation="delete") from e

    async def get_stats(self) -> dict[str, Any]:
        """Get graph statistics.

        Returns:
            Dictionary with stats.
        """
        try:
            async with self.repository.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(DISTINCT n.id) as node_count,
                        COUNT(DISTINCT e.id) as edge_count,
                        COUNT(DISTINCT n.node_type) as type_count
                    FROM knowledge_nodes n
                    LEFT JOIN knowledge_edges e ON e.source_id = n.id OR e.target_id = n.id
                    WHERE n.user_id = $1
                    """,
                    self.user_id,
                )

                return {
                    "tier": "knowledge_graph",
                    "user_id": self.user_id,
                    "node_count": row["node_count"],
                    "edge_count": row["edge_count"],
                    "type_count": row["type_count"],
                }

        except Exception as e:
            logger.warning(f"Failed to get graph stats: {e}")
            return {
                "tier": "knowledge_graph",
                "user_id": self.user_id,
                "node_count": 0,
                "edge_count": 0,
                "type_count": 0,
            }

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed.

        Returns:
            List of floating point values.
        """
        try:
            openai_client = self._get_openai_client()
            truncated_text = self._truncate_for_embedding(text)
            response = await openai_client.embeddings.create(
                model=self.embedding_model,
                input=truncated_text,
            )
            embedding = response.data[0].embedding
            if len(embedding) != self.embedding_dim:
                raise MemoryServiceError(
                    "Embedding dimension mismatch",
                    memory_type="graph",
                    details={"expected_dim": self.embedding_dim, "actual_dim": len(embedding)},
                )
            return embedding
        except Exception as e:
            raise MemoryServiceError(
                f"Failed to generate embedding: {e}",
                memory_type="graph",
            ) from e
