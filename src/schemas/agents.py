"""Agent communication schemas and message types."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class MessageType(str, Enum):
    """Types of messages that can be exchanged between agents."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class ResponseStatus(str, Enum):
    """Allowed statuses for agent responses."""

    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


class AgentMessage(BaseModel):
    """Base message format for agent communication."""

    id: str = Field(..., description="Unique message identifier")
    sender: str = Field(..., description="Agent ID sending the message")
    receiver: str = Field(..., description="Agent ID receiving the message")
    type: MessageType = Field(..., description="Message type")
    content: dict[str, Any] = Field(default_factory=dict, description="Message payload")

    def _get_utc_now() -> datetime:
        """Retorna datetime atual em UTC."""
        return datetime.now(timezone.utc)

    timestamp: datetime = Field(
        default_factory=_get_utc_now,
        description="Message creation time (UTC)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serializa timestamp como string ISO-8601 nos dumps do modelo.

        Args:
            value: Objeto datetime a ser serializado.

        Returns:
            String formatada em ISO-8601 via value.isoformat().
        """
        return value.isoformat()


class AgentResponse(BaseModel):
    """Response format for agent operations."""

    message_id: str = Field(..., description="ID of the message this response corresponds to")
    status: ResponseStatus = Field(..., description="Response status")
    data: dict[str, Any] | None = Field(default=None, description="Response data")
    error: str | None = Field(default=None, description="Error message if status is error")

    model_config = ConfigDict(use_enum_values=True)


class AgentMetrics(BaseModel):
    """Performance and usage metrics for agent execution."""

    agent_name: str = Field(..., description="Name of the agent")
    execution_time: float = Field(..., description="Execution time in seconds")
    memory_usage: int | None = Field(default=None, description="Memory usage in bytes")
    tokens_used: int | None = Field(default=None, description="Number of tokens consumed")

    model_config = ConfigDict()
