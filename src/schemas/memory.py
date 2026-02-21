"""
Memory management schemas for Agnaldo.

This module defines Pydantic v2 schemas for memory tier management,
including core, recall, and archival memory items with search and stats.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class MemoryTier(str, Enum):
    """Memory storage tiers."""

    CORE = "core"
    """High-speed, frequently accessed memory."""

    RECALL = "recall"
    """Medium-term memory for recent conversations."""

    ARCHIVAL = "archival"
    """Long-term storage for infrequently accessed content."""


class CoreMemoryItem(BaseModel):
    """Item stored in core memory tier.

    Attributes:
        id: Unique identifier for the memory item.
        content: The content stored in core memory.
        importance: Importance score (0-1) for retention priority.
        access_count: Number of times this item was accessed.
        last_accessed: Timestamp of last access.
        created_at: Timestamp when the item was created.
        metadata: Additional metadata associated with the item.
    """

    id: str = Field(..., description="Unique identifier for the memory item")
    content: str = Field(..., description="The content stored in core memory")
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance score for retention priority",
    )
    access_count: int = Field(
        default=0, ge=0, description="Number of times accessed"
    )
    last_accessed: datetime | None = Field(
        None, description="Timestamp of last access"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "id": "core_mem_001",
                "content": "User prefers concise responses",
                "importance": 0.9,
                "access_count": 42,
                "last_accessed": "2026-02-17T12:00:00Z",
                "created_at": "2026-02-15T08:00:00Z",
                "metadata": {"source": "conversation", "user_id": "123"},
            }
        ]
    }}


class RecallMemoryItem(BaseModel):
    """Item stored in recall memory tier.

    Attributes:
        id: Unique identifier for the memory item.
        content: The content stored in recall memory.
        conversation_id: Associated conversation identifier.
        message_id: Original message identifier if applicable.
        timestamp: Original message/contribution timestamp.
        embedding: Vector embedding for semantic search.
        relevance_score: Relevance score for current context.
        created_at: Timestamp when the item was stored.
    """

    id: str = Field(..., description="Unique identifier for the memory item")
    content: str = Field(..., description="The content stored in recall memory")
    conversation_id: str = Field(..., description="Associated conversation identifier")
    message_id: str | None = Field(None, description="Original message identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Original content timestamp"
    )
    embedding: list[float] | None = Field(
        None, description="Vector embedding for semantic search"
    )
    relevance_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Relevance score for current context",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Storage timestamp"
    )

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "id": "recall_mem_001",
                "content": "Previous discussion about API authentication",
                "conversation_id": "conv_123",
                "message_id": "msg_456",
                "timestamp": "2026-02-16T14:30:00Z",
                "embedding": None,
                "relevance_score": 0.85,
                "created_at": "2026-02-16T14:30:00Z",
            }
        ]
    }}


class ArchivalMemoryItem(BaseModel):
    """Item stored in archival memory tier.

    Attributes:
        id: Unique identifier for the memory item.
        content: The content stored in archival memory.
        tier: Memory tier (should be ARCHIVAL).
        compressed: Whether content is compressed.
        storage_location: Physical or logical storage location.
        tags: Tags for categorization and retrieval.
        created_at: Timestamp when the item was archived.
        last_accessed: Timestamp of last access if any.
    """

    id: str = Field(..., description="Unique identifier for the memory item")
    content: str = Field(..., description="The content stored in archival memory")
    tier: MemoryTier = Field(
        default=MemoryTier.ARCHIVAL, description="Memory tier classification"
    )
    compressed: bool = Field(
        default=False, description="Whether content is compressed"
    )
    storage_location: str = Field(..., description="Physical or logical storage location")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Archive timestamp"
    )
    last_accessed: datetime | None = Field(None, description="Timestamp of last access")

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "id": "archive_mem_001",
                "content": "Historical conversation from 2025-01-15...",
                "tier": "archival",
                "compressed": True,
                "storage_location": "s3://agnaldo-archive/2025/01/",
                "tags": ["historical", "q1_2025"],
                "created_at": "2025-01-15T10:00:00Z",
                "last_accessed": None,
            }
        ]
    }}


class MemorySearchResult(BaseModel):
    """Result of a memory search operation with pagination.

    Attributes:
        query: The search query used.
        results: List of memory items matching the query.
        total_results: Total count of matching items.
        page: Current page number (1-indexed).
        page_size: Number of results per page.
        total_pages: Total number of pages available.
        has_next: Whether there is a next page.
        has_previous: Whether there is a previous page.
        searched_at: Timestamp of the search operation.
    """

    query: str = Field(..., description="The search query used")
    results: list[CoreMemoryItem | RecallMemoryItem | ArchivalMemoryItem] = Field(
        default_factory=list, description="Matching memory items"
    )
    total_results: int = Field(..., ge=0, description="Total count of matching items")
    page: int = Field(default=1, ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(default=10, ge=1, description="Results per page")
    total_pages: int = Field(default=1, ge=1, description="Total pages available")
    has_next: bool = Field(default=False, description="Whether next page exists")
    has_previous: bool = Field(default=False, description="Whether previous page exists")
    searched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Search timestamp"
    )

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "query": "API authentication",
                "results": [],
                "total_results": 25,
                "page": 1,
                "page_size": 10,
                "total_pages": 3,
                "has_next": True,
                "has_previous": False,
                "searched_at": "2026-02-17T12:00:00Z",
            }
        ]
    }}


class MemoryStats(BaseModel):
    """Statistics for memory system monitoring.

    Attributes:
        core_count: Number of items in core memory.
        recall_count: Number of items in recall memory.
        archival_count: Number of items in archival memory.
        total_count: Total items across all tiers.
        core_tokens: Total tokens in core memory.
        recall_tokens: Total tokens in recall memory.
        archival_tokens: Total tokens in archival memory.
        total_tokens: Total tokens across all tiers.
        last_updated: Timestamp of last statistics update.
    """

    core_count: int = Field(default=0, ge=0, description="Items in core memory")
    recall_count: int = Field(default=0, ge=0, description="Items in recall memory")
    archival_count: int = Field(default=0, ge=0, description="Items in archival memory")
    total_count: int = Field(default=0, ge=0, description="Total items across all tiers")
    core_tokens: int = Field(default=0, ge=0, description="Tokens in core memory")
    recall_tokens: int = Field(default=0, ge=0, description="Tokens in recall memory")
    archival_tokens: int = Field(default=0, ge=0, description="Tokens in archival memory")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens across all tiers")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp"
    )

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "core_count": 150,
                "recall_count": 1250,
                "archival_count": 8500,
                "total_count": 9900,
                "core_tokens": 45000,
                "recall_tokens": 375000,
                "archival_tokens": 2550000,
                "total_tokens": 2970000,
                "last_updated": "2026-02-17T12:00:00Z",
            }
        ]
    }}

    @model_validator(mode="after")
    def validate_totals(self) -> "MemoryStats":
        """Ensure total counters match tier counters."""
        expected_total_count = self.core_count + self.recall_count + self.archival_count
        expected_total_tokens = self.core_tokens + self.recall_tokens + self.archival_tokens
        if self.total_count != expected_total_count:
            raise ValueError("total_count must equal core_count + recall_count + archival_count")
        if self.total_tokens != expected_total_tokens:
            raise ValueError("total_tokens must equal core_tokens + recall_tokens + archival_tokens")
        return self
