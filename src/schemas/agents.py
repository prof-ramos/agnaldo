"""Agent communication schemas and message types."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Message creation time")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


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
