"""Initial migration with all tables and RLS policies.

Revision ID: 001_initial
Revises:
Create Date: 2026-02-17

This migration creates:
- 11 core tables: users, sessions, messages, core_memories, recall_memories,
  archival_memories, knowledge_nodes, knowledge_edges, heartbeat_metrics,
  context_metrics
- Row Level Security (RLS) on all tables with user_id
- Policies for user isolation and service role access
- Indexes for performance including IVFFlat for vector similarity search
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

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

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables, enable RLS, create policies and indexes."""

    # ========================================
    # Enable pgvector extension
    # ========================================
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ========================================
    # Create tables
    # ========================================

    # Users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("discord_id", sa.String(32), nullable=False, unique=True),
        sa.Column("discord_username", sa.String(64), nullable=True),
        sa.Column("discord_global_name", sa.String(64), nullable=True),
        sa.Column("discord_avatar", sa.String(128), nullable=True),
        sa.Column("discord_discriminator", sa.String(8), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_discord_id", "users", ["discord_id"])
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_users_discord_id_active", "users", ["discord_id", "is_active"])

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel_id", sa.String(32), nullable=False),
        sa.Column("guild_id", sa.String(32), nullable=True),
        sa.Column("session_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_sessions_channel_id", "sessions", ["channel_id"])
    op.create_index("ix_sessions_guild_id", "sessions", ["guild_id"])
    op.create_index("ix_sessions_is_active", "sessions", ["is_active"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_user_active", "sessions", ["user_id", "is_active"])
    op.create_index("ix_sessions_channel_active", "sessions", ["channel_id", "is_active"])

    # Messages table
    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_messages_role", "messages", ["role"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_user_id", "messages", ["user_id"])
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_index("ix_messages_session_created", "messages", ["session_id", "created_at"])
    op.create_index("ix_messages_user_session", "messages", ["user_id", "session_id"])

    # Core memories table
    op.create_table(
        "core_memories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(256), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("memory_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_core_memories_user_id", "core_memories", ["user_id"])
    op.create_index("ix_core_memories_key", "core_memories", ["key"])
    op.create_index("ix_core_memories_user_key", "core_memories", ["user_id", "key"], unique=True)

    # Recall memories table (with vector)
    op.create_table(
        "recall_memories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("importance", sa.Float(), nullable=True),
        sa.Column("recall_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_recall_memories_user_id", "recall_memories", ["user_id"])
    op.create_index("ix_recall_memories_created_at", "recall_memories", ["created_at"])
    op.create_index("ix_recall_memories_user_created", "recall_memories", ["user_id", "created_at"])
    op.create_index("ix_recall_memories_importance", "recall_memories", ["user_id", "importance"])

    # Archival memories table (with vector)
    op.create_table(
        "archival_memories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("archival_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_archival_memories_user_id", "archival_memories", ["user_id"])
    op.create_index("ix_archival_memories_category", "archival_memories", ["category"])
    op.create_index("ix_archival_memories_created_at", "archival_memories", ["created_at"])
    op.create_index("ix_archival_memories_user_category", "archival_memories", ["user_id", "category"])
    op.create_index("ix_archival_memories_user_created", "archival_memories", ["user_id", "created_at"])

    # Knowledge nodes table (with vector)
    op.create_table(
        "knowledge_nodes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(512), nullable=False),
        sa.Column("node_type", sa.String(128), nullable=True),
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("node_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_knowledge_nodes_user_id", "knowledge_nodes", ["user_id"])
    op.create_index("ix_knowledge_nodes_label", "knowledge_nodes", ["label"])
    op.create_index("ix_knowledge_nodes_node_type", "knowledge_nodes", ["node_type"])
    op.create_index("ix_knowledge_nodes_user_type", "knowledge_nodes", ["user_id", "node_type"])
    op.create_index("ix_knowledge_nodes_user_label", "knowledge_nodes", ["user_id", "label"])

    # Knowledge edges table
    op.create_table(
        "knowledge_edges",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("edge_type", sa.String(128), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        sa.Column("edge_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_knowledge_edges_source_id", "knowledge_edges", ["source_id"])
    op.create_index("ix_knowledge_edges_target_id", "knowledge_edges", ["target_id"])
    op.create_index("ix_knowledge_edges_edge_type", "knowledge_edges", ["edge_type"])
    op.create_index("ix_knowledge_edges_source_type", "knowledge_edges", ["source_id", "edge_type"])
    op.create_index("ix_knowledge_edges_target_type", "knowledge_edges", ["target_id", "edge_type"])

    # Heartbeat metrics table
    op.create_table(
        "heartbeat_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("metric_type", sa.String(64), nullable=False),
        sa.Column("metric_name", sa.String(256), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("metric_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_heartbeat_metrics_user_id", "heartbeat_metrics", ["user_id"])
    op.create_index("ix_heartbeat_metrics_metric_type", "heartbeat_metrics", ["metric_type"])
    op.create_index("ix_heartbeat_metrics_metric_name", "heartbeat_metrics", ["metric_name"])
    op.create_index("ix_heartbeat_metrics_created_at", "heartbeat_metrics", ["created_at"])
    op.create_index("ix_heartbeat_metrics_type_created", "heartbeat_metrics", ["metric_type", "created_at"])
    op.create_index("ix_heartbeat_metrics_user_created", "heartbeat_metrics", ["user_id", "created_at"])

    # Context metrics table
    op.create_table(
        "context_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_type", sa.String(64), nullable=False),
        sa.Column("metric_name", sa.String(256), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("context_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_context_metrics_user_id", "context_metrics", ["user_id"])
    op.create_index("ix_context_metrics_session_id", "context_metrics", ["session_id"])
    op.create_index("ix_context_metrics_metric_type", "context_metrics", ["metric_type"])
    op.create_index("ix_context_metrics_metric_name", "context_metrics", ["metric_name"])
    op.create_index("ix_context_metrics_created_at", "context_metrics", ["created_at"])
    op.create_index("ix_context_metrics_session_created", "context_metrics", ["session_id", "created_at"])
    op.create_index("ix_context_metrics_type_created", "context_metrics", ["metric_type", "created_at"])

    # ========================================
    # Enable Row Level Security (RLS)
    # ========================================

    tables_with_user_id = [
        "users",
        "sessions",
        "messages",
        "core_memories",
        "recall_memories",
        "archival_memories",
        "knowledge_nodes",
        "heartbeat_metrics",
        "context_metrics",
    ]

    for table in tables_with_user_id:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Knowledge edges uses source_id which references knowledge_nodes
    # We use a special policy for edges that checks the source node's user_id
    op.execute("ALTER TABLE knowledge_edges ENABLE ROW LEVEL SECURITY")

    # ========================================
    # Create RLS Policies
    # ========================================

    # Users table policies
    op.execute("""
        CREATE POLICY "Users can view own data" ON users
        FOR SELECT USING (id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY "Users can insert own data" ON users
        FOR INSERT WITH CHECK (id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY "Users can update own data" ON users
        FOR UPDATE USING (id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY "Service role full access on users" ON users
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
    """)

    # Generic policies for tables with user_id
    user_id_tables = [
        "sessions",
        "messages",
        "core_memories",
        "recall_memories",
        "archival_memories",
        "knowledge_nodes",
        "heartbeat_metrics",
        "context_metrics",
    ]

    for table in user_id_tables:
        op.execute(f"""
            CREATE POLICY "{table.title()} can view own data" ON {table}
            FOR SELECT USING (user_id = auth.uid())
        """)
        op.execute(f"""
            CREATE POLICY "{table.title()} can insert own data" ON {table}
            FOR INSERT WITH CHECK (user_id = auth.uid())
        """)
        op.execute(f"""
            CREATE POLICY "{table.title()} can update own data" ON {table}
            FOR UPDATE USING (user_id = auth.uid())
        """)
        op.execute(f"""
            CREATE POLICY "{table.title()} can delete own data" ON {table}
            FOR DELETE USING (user_id = auth.uid())
        """)
        op.execute(f"""
            CREATE POLICY "Service role full access on {table}" ON {table}
            FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
        """)

    # Special policy for knowledge_edges using subquery to check user_id via source node
    op.execute("""
        CREATE POLICY "Knowledge Edges can view own data" ON knowledge_edges
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM knowledge_nodes
                WHERE knowledge_nodes.id = knowledge_edges.source_id
                AND knowledge_nodes.user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY "Knowledge Edges can insert own data" ON knowledge_edges
        FOR INSERT WITH CHECK (
            EXISTS (
                SELECT 1 FROM knowledge_nodes
                WHERE knowledge_nodes.id = knowledge_edges.source_id
                AND knowledge_nodes.user_id = auth.uid()
            )
            AND EXISTS (
                SELECT 1 FROM knowledge_nodes
                WHERE knowledge_nodes.id = knowledge_edges.target_id
                AND knowledge_nodes.user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY "Knowledge Edges can update own data" ON knowledge_edges
        FOR UPDATE USING (
            EXISTS (
                SELECT 1 FROM knowledge_nodes
                WHERE knowledge_nodes.id = knowledge_edges.source_id
                AND knowledge_nodes.user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY "Knowledge Edges can delete own data" ON knowledge_edges
        FOR DELETE USING (
            EXISTS (
                SELECT 1 FROM knowledge_nodes
                WHERE knowledge_nodes.id = knowledge_edges.source_id
                AND knowledge_nodes.user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY "Service role full access on knowledge_edges" ON knowledge_edges
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
    """)


def downgrade() -> None:
    """Drop all tables, policies, and indexes."""

    # Drop in reverse order due to foreign keys
    op.drop_table("context_metrics")
    op.drop_table("heartbeat_metrics")
    op.drop_table("knowledge_edges")
    op.drop_table("knowledge_nodes")
    op.drop_table("archival_memories")
    op.drop_table("recall_memories")
    op.drop_table("core_memories")
    op.drop_table("messages")
    op.drop_table("sessions")
    op.drop_table("users")

    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
