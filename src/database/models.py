"""SQLAlchemy ORM models for Agnaldo Discord bot database.

This module defines all database tables with support for:
- User and session management
- Message and memory storage (core, recall, archival)
- Knowledge graph (nodes and edges)
- Heartbeat and context metrics
- Vector embeddings via pgvector
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

if TYPE_CHECKING:
    from pgvector.sqlalchemy import Vector
else:
    try:
        from pgvector.sqlalchemy import Vector
    except ImportError:
        class Vector(UserDefinedType):  # type: ignore[no-redef]
            """Fallback SQL type for vector columns when pgvector isn't installed."""

            cache_ok = True

            def __init__(self, dimensions: int) -> None:
                self.dimensions = dimensions

            def get_col_spec(self, **_: object) -> str:
                return f"vector({self.dimensions})"


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class User(Base):
    """User table representing Discord users.

    Attributes:
        id: Primary key UUID
        discord_id: Discord user ID (unique)
        discord_username: Discord username
        discord_global_name: Discord global display name
        discord_avatar: Discord avatar hash
        discord_discriminator: Discord discriminator (legacy, 4 digits)
        is_bot: Whether the user is a bot
        is_active: Whether the user is active in the system
        user_metadata: Additional user metadata as JSONB
        created_at: User creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    discord_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    discord_global_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    discord_avatar: Mapped[str | None] = mapped_column(String(128), nullable=True)
    discord_discriminator: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_bot: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    user_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    core_memories: Mapped[list["CoreMemory"]] = relationship(
        "CoreMemory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    recall_memories: Mapped[list["RecallMemory"]] = relationship(
        "RecallMemory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    archival_memories: Mapped[list["ArchivalMemory"]] = relationship(
        "ArchivalMemory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    knowledge_nodes: Mapped[list["KnowledgeNode"]] = relationship(
        "KnowledgeNode",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_users_discord_id_active", "discord_id", "is_active"),
    )


class Session(Base):
    """Session table for conversation sessions.

    Attributes:
        id: Primary key UUID
        user_id: Foreign key to users table
        channel_id: Discord channel ID
        guild_id: Discord guild ID (server)
        session_metadata: Additional session metadata as JSONB
        is_active: Whether the session is active
        created_at: Session creation timestamp
        updated_at: Last activity timestamp
    """

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[str] = mapped_column(String(32), index=True)
    guild_id: Mapped[str] = mapped_column(String(32), index=True, nullable=True)
    session_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_sessions_user_active", "user_id", "is_active"),
        Index("ix_sessions_channel_active", "channel_id", "is_active"),
    )


class Message(Base):
    """Message table for storing conversation messages.

    Attributes:
        id: Primary key UUID
        user_id: Foreign key to users table
        session_id: Foreign key to sessions table
        role: Message role (user, assistant, system, tool)
        content: Message content
        message_metadata: Additional message metadata as JSONB
        created_at: Message creation timestamp
    """

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="messages")
    session: Mapped["Session"] = relationship("Session", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
        Index("ix_messages_user_session", "user_id", "session_id"),
    )


class CoreMemory(Base):
    """Core memory table for persistent important facts.

    Attributes:
        id: Primary key UUID
        user_id: Foreign key to users table
        key: Memory key for fact identification
        value: Memory value
        memory_metadata: Additional memory metadata as JSONB
        created_at: Memory creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "core_memories"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(256), index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    memory_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="core_memories")

    __table_args__ = (
        Index("ix_core_memories_user_key", "user_id", "key", unique=True),
    )


class RecallMemory(Base):
    """Recall memory table for conversation history with semantic search.

    Attributes:
        id: Primary key UUID
        user_id: Foreign key to users table
        content: Memory content
        embedding: Vector embedding for semantic search
        importance: Importance score (0-1)
        recall_metadata: Additional memory metadata as JSONB
        created_at: Memory creation timestamp
    """

    __tablename__ = "recall_memories"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),  # OpenAI text-embedding-3-small dimension
        nullable=True,
    )
    importance: Mapped[float | None] = mapped_column(nullable=True)
    recall_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recall_memories")

    __table_args__ = (
        Index("ix_recall_memories_user_created", "user_id", "created_at"),
        Index("ix_recall_memories_importance", "user_id", "importance"),
    )


class ArchivalMemory(Base):
    """Archival memory table for long-term knowledge storage.

    Attributes:
        id: Primary key UUID
        user_id: Foreign key to users table
        content: Memory content
        embedding: Vector embedding for semantic search
        category: Memory category for organization
        archival_metadata: Additional memory metadata as JSONB
        created_at: Memory creation timestamp
    """

    __tablename__ = "archival_memories"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )
    category: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    archival_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="archival_memories")

    __table_args__ = (
        Index("ix_archival_memories_user_category", "user_id", "category"),
        Index("ix_archival_memories_user_created", "user_id", "created_at"),
    )


class KnowledgeNode(Base):
    """Knowledge graph nodes for semantic network.

    Attributes:
        id: Primary key UUID
        user_id: Foreign key to users table
        label: Node label/name
        node_type: Type of knowledge node
        properties: Node properties as JSONB
        embedding: Vector embedding for semantic similarity
        node_metadata: Additional node metadata as JSONB
        created_at: Node creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "knowledge_nodes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    node_type: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )
    node_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="knowledge_nodes")

    # Self-referential relationships for edges
    outgoing_edges: Mapped[list["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge",
        foreign_keys="KnowledgeEdge.source_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge",
        foreign_keys="KnowledgeEdge.target_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_knowledge_nodes_user_type", "user_id", "node_type"),
        Index("ix_knowledge_nodes_user_label", "user_id", "label"),
    )


class KnowledgeEdge(Base):
    """Knowledge graph edges connecting nodes.

    Attributes:
        id: Primary key UUID
        source_id: Foreign key to knowledge_nodes (source)
        target_id: Foreign key to knowledge_nodes (target)
        edge_type: Type of relationship
        weight: Edge weight/strength
        properties: Edge properties as JSONB
        edge_metadata: Additional edge metadata as JSONB
        created_at: Edge creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "knowledge_edges"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    edge_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    source_node: Mapped["KnowledgeNode"] = relationship(
        "KnowledgeNode",
        foreign_keys=[source_id],
        back_populates="outgoing_edges",
    )
    target_node: Mapped["KnowledgeNode"] = relationship(
        "KnowledgeNode",
        foreign_keys=[target_id],
        back_populates="incoming_edges",
    )

    __table_args__ = (
        Index("ix_knowledge_edges_source_type", "source_id", "edge_type"),
        Index("ix_knowledge_edges_target_type", "target_id", "edge_type"),
    )


class HeartbeatMetric(Base):
    """Heartbeat metrics for system health monitoring.

    Attributes:
        id: Primary key UUID
        user_id: Foreign key to users table (nullable for system metrics)
        metric_type: Type of metric (cpu, memory, latency, etc)
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        metric_metadata: Additional metric metadata as JSONB
        created_at: Metric creation timestamp
    """

    __tablename__ = "heartbeat_metrics"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    metric_type: Mapped[str] = mapped_column(String(64), index=True)
    metric_name: Mapped[str] = mapped_column(String(256), index=True)
    value: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metric_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index("ix_heartbeat_metrics_type_created", "metric_type", "created_at"),
        Index("ix_heartbeat_metrics_user_created", "user_id", "created_at"),
    )


class ContextMetric(Base):
    """Context metrics for conversation context tracking.

    Attributes:
        id: Primary key UUID
        user_id: Foreign key to users table
        session_id: Foreign key to sessions table
        metric_type: Type of context metric
        metric_name: Name of the metric
        value: Metric value
        context_metadata: Additional context metadata as JSONB
        created_at: Metric creation timestamp
    """

    __tablename__ = "context_metrics"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_type: Mapped[str] = mapped_column(String(64), index=True)
    metric_name: Mapped[str] = mapped_column(String(256), index=True)
    value: Mapped[float] = mapped_column(nullable=False)
    context_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index("ix_context_metrics_session_created", "session_id", "created_at"),
        Index("ix_context_metrics_type_created", "metric_type", "created_at"),
    )
