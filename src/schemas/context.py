"""
Context management schemas for Agnaldo.

This module defines Pydantic v2 schemas for context window management,
including modes, window tracking, reduction results, and metrics.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ContextMode(str, Enum):
    """Context management modes."""

    ACTIVE = "active"
    """Active context processing mode."""

    PASSIVE = "passive"
    """Passive context observation mode."""

    OFFLOAD = "offload"
    """Context offloading to external storage."""


class ContextWindow(BaseModel):
    """Context window state and tracking.

    Attributes:
        total_tokens: Total tokens in the context window.
        max_tokens: Maximum allowed tokens in the window.
        utilization_percent: Percentage of window utilization.
        last_updated: Timestamp of last update.
    """

    total_tokens: int = Field(
        ..., ge=0, description="Total tokens currently in the context window"
    )
    max_tokens: int = Field(
        ..., ge=1, description="Maximum allowed tokens in the context window"
    )
    utilization_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of context window utilization",
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of last update"
    )

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "total_tokens": 45000,
                "max_tokens": 128000,
                "utilization_percent": 35.16,
                "last_updated": "2026-02-17T12:00:00Z",
            }
        ]
    }}

    @model_validator(mode="after")
    def validate_window(self) -> "ContextWindow":
        """Ensure window constraints and utilization are consistent."""
        if self.total_tokens > self.max_tokens:
            raise ValueError("total_tokens must be <= max_tokens")
        expected = (self.total_tokens / self.max_tokens) * 100 if self.max_tokens > 0 else 0.0
        if abs(self.utilization_percent - expected) > 0.5:
            raise ValueError("utilization_percent is inconsistent with total_tokens/max_tokens")
        return self


class ContextOffloadItem(BaseModel):
    """An item offloaded from context window.

    Attributes:
        id: Unique identifier for the offloaded item.
        content: The content that was offloaded.
        token_count: Number of tokens in the offloaded content.
        offloaded_at: Timestamp when the item was offloaded.
        storage_path: Path or reference to where content is stored.
        retrieval_score: Score indicating likelihood of retrieval need.
    """

    id: str = Field(..., description="Unique identifier for the offloaded item")
    content: str = Field(..., description="The content that was offloaded")
    token_count: int = Field(..., ge=0, description="Number of tokens in offloaded content")
    offloaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when offloaded"
    )
    storage_path: Optional[str] = Field(
        None, description="Path or reference to storage location"
    )
    retrieval_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Score indicating likelihood of retrieval need",
    )

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "id": "offload_123",
                "content": "Previous conversation context...",
                "token_count": 2500,
                "offloaded_at": "2026-02-17T12:00:00Z",
                "storage_path": "memory://archival/conversation_123",
                "retrieval_score": 0.75,
            }
        ]
    }}


class ContextReductionResult(BaseModel):
    """Result of a context reduction operation.

    Attributes:
        original_tokens: Token count before reduction.
        reduced_tokens: Token count after reduction.
        tokens_saved: Number of tokens saved.
        offloaded_items: List of items that were offloaded.
        reduction_strategy: Strategy used for reduction.
        processed_at: Timestamp of reduction processing.
    """

    original_tokens: int = Field(..., ge=0, description="Token count before reduction")
    reduced_tokens: int = Field(..., ge=0, description="Token count after reduction")
    tokens_saved: int = Field(..., ge=0, description="Number of tokens saved")
    offloaded_items: list[ContextOffloadItem] = Field(
        default_factory=list, description="Items that were offloaded"
    )
    reduction_strategy: str = Field(
        ..., description="Strategy used for context reduction"
    )
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of reduction"
    )

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "original_tokens": 95000,
                "reduced_tokens": 45000,
                "tokens_saved": 50000,
                "offloaded_items": [],
                "reduction_strategy": "lru_with_summary",
                "processed_at": "2026-02-17T12:00:00Z",
            }
        ]
    }}

    @model_validator(mode="after")
    def validate_reduction_numbers(self) -> "ContextReductionResult":
        """Ensure token counters are coherent."""
        expected_saved = self.original_tokens - self.reduced_tokens
        if expected_saved < 0:
            raise ValueError("reduced_tokens cannot exceed original_tokens")
        if self.tokens_saved != expected_saved:
            raise ValueError("tokens_saved must equal original_tokens - reduced_tokens")
        return self


class ContextMetrics(BaseModel):
    """Metrics for context monitoring and analysis.

    Attributes:
        mode: Current context management mode.
        current_window: Current context window state.
        total_offloaded: Total count of offloaded items.
        total_reductions: Total count of reduction operations performed.
        average_reduction_ratio: Average ratio of tokens saved per reduction.
        last_reduction: Most recent reduction result.
        metrics_collected_at: Timestamp of metrics collection.
    """

    mode: ContextMode = Field(..., description="Current context management mode")
    current_window: ContextWindow = Field(
        ..., description="Current context window state"
    )
    total_offloaded: int = Field(
        default=0, ge=0, description="Total count of offloaded items"
    )
    total_reductions: int = Field(
        default=0, ge=0, description="Total count of reduction operations"
    )
    average_reduction_ratio: float = Field(
        default=0.0,
        ge=0.0,
        description="Average ratio of tokens saved per reduction",
    )
    last_reduction: Optional[ContextReductionResult] = Field(
        None, description="Most recent reduction result"
    )
    metrics_collected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of metrics collection"
    )

    model_config = {"use_enum_values": True, "json_schema_extra": {
        "examples": [
            {
                "mode": "active",
                "current_window": {
                    "total_tokens": 45000,
                    "max_tokens": 128000,
                    "utilization_percent": 35.16,
                },
                "total_offloaded": 15,
                "total_reductions": 3,
                "average_reduction_ratio": 0.52,
                "metrics_collected_at": "2026-02-17T12:00:00Z",
            }
        ]
    }}
