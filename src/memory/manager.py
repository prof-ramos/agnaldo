"""Unified Memory Manager for Agnaldo.

This module provides a unified facade for managing all three memory tiers
(Core, Recall, Archival) and Knowledge Graph integration.

Features:
- Unified interface for all memory tiers
- Automatic context retrieval for prompts
- Priority-based memory selection
- Knowledge graph integration
- Token budget management
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from src.config.settings import get_settings
from src.exceptions import DatabaseError, MemoryServiceError
from src.memory.archival import ArchivalMemory
from src.memory.core import CoreMemory
from src.memory.recall import RecallMemory
from src.knowledge.graph import KnowledgeGraph
from src.schemas.memory import MemoryStats


class MemoryContext:
    """Context object containing retrieved memories from all tiers.

    Attributes:
        core: Core memory key-value pairs.
        recall: Recent memories from semantic search.
        archival: Historical memories from metadata search.
        graph: Knowledge graph nodes and relationships.
        total_tokens: Estimated total tokens in context.
    """

    def __init__(self) -> None:
        """Initialize empty context."""
        self.core: dict[str, str] = {}
        self.recall: list[dict[str, Any]] = []
        self.archival: list[dict[str, Any]] = []
        self.graph: list[dict[str, Any]] = []
        self.total_tokens: int = 0

    def to_prompt_section(self, max_tokens: int = 1500) -> str:
        """Convert context to a prompt section.

        Args:
            max_tokens: Maximum tokens to include (approximate).

        Returns:
            Formatted string for prompt injection.
        """
        sections = []
        current_tokens = 0

        # Core Memory - Always include if available
        if self.core:
            core_text = "## Fatos Importantes\n"
            for key, value in self.core.items():
                line = f"- {key}: {value}\n"
                estimated_tokens = len(line.split()) * 1.3  # Rough estimate
                if current_tokens + estimated_tokens > max_tokens:
                    break
                core_text += line
                current_tokens += estimated_tokens
            sections.append(core_text)

        # Recall Memory - Recent relevant conversations
        if self.recall and current_tokens < max_tokens:
            recall_text = "## Conversas Relevantes\n"
            for item in self.recall:
                content = item.get("content", "")
                similarity = item.get("similarity", 0)
                line = f"- [Relevância: {similarity:.0%}] {content[:200]}{'...' if len(content) > 200 else ''}\n"
                estimated_tokens = len(line.split()) * 1.3
                if current_tokens + estimated_tokens > max_tokens:
                    break
                recall_text += line
                current_tokens += estimated_tokens
            if len(recall_text) > 30:  # More than just header
                sections.append(recall_text)

        # Knowledge Graph - Related concepts
        if self.graph and current_tokens < max_tokens:
            graph_text = "## Conhecimentos Relacionados\n"
            for item in self.graph:
                label = item.get("label", "")
                node_type = item.get("node_type", "")
                similarity = item.get("similarity", 0)
                line = f"- {label} ({node_type}) [Similaridade: {similarity:.0%}]\n"
                estimated_tokens = len(line.split()) * 1.3
                if current_tokens + estimated_tokens > max_tokens:
                    break
                graph_text += line
                current_tokens += estimated_tokens
            if len(graph_text) > 35:  # More than just header
                sections.append(graph_text)

        # Archival Memory - Historical context (lowest priority)
        if self.archival and current_tokens < max_tokens * 0.8:  # Only use 80% of budget
            archival_text = "## Histórico Relevante\n"
            for item in self.archival:
                content = item.get("content", "")
                source = item.get("source", "unknown")
                line = f"- [{source}] {content[:150]}{'...' if len(content) > 150 else ''}\n"
                estimated_tokens = len(line.split()) * 1.3
                if current_tokens + estimated_tokens > max_tokens:
                    break
                archival_text += line
                current_tokens += estimated_tokens
            if len(archival_text) > 25:  # More than just header
                sections.append(archival_text)

        if not sections:
            return ""

        return "\n".join(sections)


class MemoryManager:
    """Unified manager for all memory tiers and knowledge graph.

    Provides a single interface for memory operations and automatic
    context retrieval with token budget management.
    """

    def __init__(
        self,
        user_id: str,
        db_pool,
        openai_client: AsyncOpenAI | None = None,
        core_max_items: int = 100,
        core_max_tokens: int = 10000,
        recall_search_limit: int = 5,
        recall_similarity_threshold: float = 0.6,
        archival_search_limit: int = 3,
        graph_search_limit: int = 5,
        graph_similarity_threshold: float = 0.7,
        context_max_tokens: int = 1500,
    ) -> None:
        """Initialize the Memory Manager.

        Args:
            user_id: User identifier for memory isolation.
            db_pool: Database connection pool (asyncpg).
            openai_client: OpenAI client for embeddings.
            core_max_items: Maximum items in core memory.
            core_max_tokens: Maximum tokens in core memory.
            recall_search_limit: Maximum recall results to retrieve.
            recall_similarity_threshold: Minimum similarity for recall search.
            archival_search_limit: Maximum archival results to retrieve.
            graph_search_limit: Maximum graph nodes to retrieve.
            graph_similarity_threshold: Minimum similarity for graph search.
            context_max_tokens: Maximum tokens in generated context.
        """
        self.user_id = user_id
        self.db_pool = db_pool
        self.openai = openai_client

        # Configuration
        self.core_max_items = core_max_items
        self.core_max_tokens = core_max_tokens
        self.recall_search_limit = recall_search_limit
        self.recall_similarity_threshold = recall_similarity_threshold
        self.archival_search_limit = archival_search_limit
        self.graph_search_limit = graph_search_limit
        self.graph_similarity_threshold = graph_similarity_threshold
        self.context_max_tokens = context_max_tokens

        # Lazy-loaded memory instances
        self._core: CoreMemory | None = None
        self._recall: RecallMemory | None = None
        self._archival: ArchivalMemory | None = None
        self._graph: KnowledgeGraph | None = None

        logger.debug(f"MemoryManager initialized for user {user_id}")

    @property
    def core(self) -> CoreMemory:
        """Get or create CoreMemory instance."""
        if self._core is None:
            self._core = CoreMemory(
                user_id=self.user_id,
                repository=self.db_pool,
                max_items=self.core_max_items,
                max_tokens=self.core_max_tokens,
            )
        return self._core

    @property
    def recall(self) -> RecallMemory:
        """Get or create RecallMemory instance."""
        if self._recall is None:
            self._recall = RecallMemory(
                user_id=self.user_id,
                repository=self.db_pool,
                openai_client=self.openai,
            )
        return self._recall

    @property
    def archival(self) -> ArchivalMemory:
        """Get or create ArchivalMemory instance."""
        if self._archival is None:
            self._archival = ArchivalMemory(
                user_id=self.user_id,
                repository=self.db_pool,
            )
        return self._archival

    @property
    def graph(self) -> KnowledgeGraph:
        """Get or create KnowledgeGraph instance."""
        if self._graph is None:
            self._graph = KnowledgeGraph(
                user_id=self.user_id,
                repository=self.db_pool,
                openai_client=self.openai,
            )
        return self._graph

    async def retrieve_context(
        self,
        query: str,
        include_core: bool = True,
        include_recall: bool = True,
        include_archival: bool = False,
        include_graph: bool = True,
        extracted_topics: list[str] | None = None,
    ) -> MemoryContext:
        """Retrieve context from all memory tiers for prompt injection.

        Args:
            query: The user's query to search for relevant context.
            include_core: Whether to include core memory.
            include_recall: Whether to include recall memory search.
            include_archival: Whether to include archival memory search.
            include_graph: Whether to include knowledge graph search.
            extracted_topics: Optional list of extracted topics for targeted search.

        Returns:
            MemoryContext object with retrieved memories.
        """
        context = MemoryContext()

        try:
            # Run searches in parallel for efficiency
            tasks = []

            if include_core:
                tasks.append(self._retrieve_core_context(context))

            if include_recall:
                tasks.append(self._retrieve_recall_context(query, context))

            if include_archival and extracted_topics:
                tasks.append(self._retrieve_archival_context(extracted_topics, context))

            if include_graph:
                tasks.append(self._retrieve_graph_context(query, context))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            logger.info(
                f"Retrieved context for query: core={len(context.core)}, "
                f"recall={len(context.recall)}, archival={len(context.archival)}, "
                f"graph={len(context.graph)}"
            )

        except Exception as e:
            logger.warning(f"Failed to retrieve full context: {e}")

        return context

    async def _retrieve_core_context(self, context: MemoryContext) -> None:
        """Retrieve core memory context."""
        try:
            context.core = await self.core.get_all()
        except Exception as e:
            logger.warning(f"Failed to retrieve core memory: {e}")

    async def _retrieve_recall_context(self, query: str, context: MemoryContext) -> None:
        """Retrieve recall memory context via semantic search."""
        try:
            results = await self.recall.search(
                query=query,
                limit=self.recall_search_limit,
                threshold=self.recall_similarity_threshold,
            )
            context.recall = results
        except Exception as e:
            logger.warning(f"Failed to retrieve recall memory: {e}")

    async def _retrieve_archival_context(
        self, topics: list[str], context: MemoryContext
    ) -> None:
        """Retrieve archival memory context by metadata."""
        try:
            # Search by topic in metadata
            for topic in topics[:2]:  # Limit to top 2 topics
                results = await self.archival.search_by_metadata(
                    filters={"topic": topic},
                    limit=self.archival_search_limit,
                )
                context.archival.extend(results)

            # Also do content search for first topic
            if topics:
                content_results = await self.archival.search_by_content(
                    query=topics[0],
                    limit=self.archival_search_limit,
                )
                # Deduplicate by memory_id
                existing_ids = {r.get("memory_id") for r in context.archival}
                for result in content_results:
                    if result.get("memory_id") not in existing_ids:
                        context.archival.append(result)

        except Exception as e:
            logger.warning(f"Failed to retrieve archival memory: {e}")

    async def _retrieve_graph_context(self, query: str, context: MemoryContext) -> None:
        """Retrieve knowledge graph context."""
        try:
            results = await self.graph.search_nodes(
                query=query,
                limit=self.graph_search_limit,
                threshold=self.graph_similarity_threshold,
            )
            context.graph = results
        except Exception as e:
            logger.warning(f"Failed to retrieve graph context: {e}")

    async def store_interaction(
        self,
        user_message: str,
        assistant_response: str,
        importance: float = 0.5,
        store_in_recall: bool = True,
        store_in_graph: bool = False,
        extract_entities: bool = False,
    ) -> dict[str, Any]:
        """Store an interaction in appropriate memory tiers.

        Args:
            user_message: The user's message.
            assistant_response: The assistant's response.
            importance: Importance score (0.0-1.0).
            store_in_recall: Whether to store in recall memory.
            store_in_graph: Whether to extract and store entities in graph.
            extract_entities: Whether to extract entities (requires LLM).

        Returns:
            Dict with IDs of created memories.
        """
        result: dict[str, Any] = {
            "recall_id": None,
            "graph_nodes": [],
        }

        try:
            # Store in recall memory
            if store_in_recall:
                content = f"User: {user_message}\nAssistant: {assistant_response}"
                result["recall_id"] = await self.recall.add(
                    content=content,
                    importance=importance,
                )

            # Extract entities and store in knowledge graph
            if store_in_graph and extract_entities:
                # Note: Entity extraction would require LLM call
                # This is a placeholder for future implementation
                logger.debug("Entity extraction for graph storage not yet implemented")

        except Exception as e:
            logger.warning(f"Failed to store interaction: {e}")

        return result

    async def store_core_fact(
        self,
        key: str,
        value: str,
        importance: float = 0.7,
    ) -> str | None:
        """Store a fact in core memory.

        Args:
            key: Unique key for the fact.
            value: The fact value.
            importance: Importance score (0.0-1.0).

        Returns:
            Memory ID or None if failed.
        """
        try:
            item = await self.core.add(key, value, importance=importance)
            return item.id
        except Exception as e:
            logger.warning(f"Failed to store core fact: {e}")
            return None

    async def get_stats(self) -> MemoryStats:
        """Get statistics for all memory tiers.

        Returns:
            MemoryStats object with counts and token estimates.
        """
        try:
            # Get stats from each tier
            core_stats = await self.core.get_stats()
            graph_stats = await self.graph.get_stats()

            # Recall and archival don't have get_stats methods, estimate from DB
            recall_count = await self._count_table("recall_memories")
            archival_count = await self._count_table("archival_memories")

            # Estimate tokens (rough approximation)
            core_tokens = int(core_stats.get("avg_importance", 0) * core_stats.get("item_count", 0) * 50)
            recall_tokens = recall_count * 100  # Assume avg 100 tokens per recall
            archival_tokens = archival_count * 200  # Assume avg 200 tokens per archival

            return MemoryStats(
                core_count=core_stats.get("item_count", 0),
                recall_count=recall_count,
                archival_count=archival_count,
                total_count=core_stats.get("item_count", 0) + recall_count + archival_count,
                core_tokens=core_tokens,
                recall_tokens=recall_tokens,
                archival_tokens=archival_tokens,
                total_tokens=core_tokens + recall_tokens + archival_tokens,
            )

        except Exception as e:
            logger.warning(f"Failed to get memory stats: {e}")
            return MemoryStats()

    async def _count_table(self, table_name: str) -> int:
        """Count rows in a table for the current user."""
        try:
            async with self.db_pool.acquire() as conn:
                count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table_name} WHERE user_id = $1",
                    self.user_id,
                )
                return count or 0
        except Exception as e:
            logger.warning(f"Failed to count {table_name}: {e}")
            return 0

    async def compress_session(self, session_id: str, summary: str | None = None) -> dict[str, Any]:
        """Compress all memories from a session in archival memory.

        Args:
            session_id: The session identifier.
            summary: Optional pre-generated summary.

        Returns:
            Compression result with stats.
        """
        try:
            result = await self.archival.compress(session_id, summary)
            logger.info(f"Compressed session {session_id}: {result}")
            return result
        except Exception as e:
            logger.warning(f"Failed to compress session: {e}")
            return {"compressed_memory_id": None, "original_count": 0, "compressed_count": 0}

    async def clear_all(self, confirm: bool = False) -> int:
        """Clear all memories for the user across all tiers.

        Args:
            confirm: Must be True to actually clear.

        Returns:
            Total number of items cleared.

        Warning:
            This is a destructive operation!
        """
        if not confirm:
            raise MemoryServiceError(
                "Must pass confirm=True to clear all memories",
                memory_type="all",
            )

        total_cleared = 0

        try:
            # Clear each tier
            total_cleared += await self.core.clear()

            # Clear recall and archival via direct DB operations
            async with self.db_pool.acquire() as conn:
                recall_count = await conn.fetchval(
                    "DELETE FROM recall_memories WHERE user_id = $1 RETURNING COUNT(*)",
                    self.user_id,
                )
                total_cleared += recall_count or 0

                archival_count = await conn.fetchval(
                    "DELETE FROM archival_memories WHERE user_id = $1 RETURNING COUNT(*)",
                    self.user_id,
                )
                total_cleared += archival_count or 0

                # Clear graph nodes (edges cascade)
                graph_count = await conn.fetchval(
                    "DELETE FROM knowledge_nodes WHERE user_id = $1 RETURNING COUNT(*)",
                    self.user_id,
                )
                total_cleared += graph_count or 0

            logger.warning(f"Cleared {total_cleared} memories for user {self.user_id}")
            return total_cleared

        except Exception as e:
            raise DatabaseError(f"Failed to clear memories: {e}", operation="delete") from e
