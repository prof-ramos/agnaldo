"""Row Level Security (RLS) policies for database tables.

This module contains SQL policy definitions used in migrations and for documentation.
All policies follow Supabase auth conventions with auth.uid() for user identification
and auth.jwt() for role-based access control.
"""

# =============================================================================
# Users Table RLS Policies
# =============================================================================

USERS_POLICIES = {
    "select_own": """
        CREATE POLICY "Users can view own data" ON users
        FOR SELECT USING (id = auth.uid())
    """,
    "insert_own": """
        CREATE POLICY "Users can insert own data" ON users
        FOR INSERT WITH CHECK (id = auth.uid())
    """,
    "update_own": """
        CREATE POLICY "Users can update own data" ON users
        FOR UPDATE USING (id = auth.uid())
    """,
    "service_role_full": """
        CREATE POLICY "Service role full access on users" ON users
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
    """,
}


# =============================================================================
# Generic Policies for Tables with user_id
# =============================================================================

def get_user_id_policies(table_name: str) -> dict[str, str]:
    """Generate standard RLS policies for tables with user_id column.

    Args:
        table_name: Name of the table (lowercase, snake_case)

    Returns:
        Dictionary with policy names as keys and SQL as values
    """
    title_case = table_name.replace("_", " ").title().replace(" ", "_")
    return {
        "select_own": f"""
            CREATE POLICY "{title_case} can view own data" ON {table_name}
            FOR SELECT USING (user_id = auth.uid())
        """,
        "insert_own": f"""
            CREATE POLICY "{title_case} can insert own data" ON {table_name}
            FOR INSERT WITH CHECK (user_id = auth.uid())
        """,
        "update_own": f"""
            CREATE POLICY "{title_case} can update own data" ON {table_name}
            FOR UPDATE USING (user_id = auth.uid())
        """,
        "delete_own": f"""
            CREATE POLICY "{title_case} can delete own data" ON {table_name}
            FOR DELETE USING (user_id = auth.uid())
        """,
        "service_role_full": f"""
            CREATE POLICY "Service role full access on {table_name}" ON {table_name}
            FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
        """,
    }


# Table-specific policies
SESSIONS_POLICIES = get_user_id_policies("sessions")
MESSAGES_POLICIES = get_user_id_policies("messages")
CORE_MEMORIES_POLICIES = get_user_id_policies("core_memories")
RECALL_MEMORIES_POLICIES = get_user_id_policies("recall_memories")
ARCHIVAL_MEMORIES_POLICIES = get_user_id_policies("archival_memories")
KNOWLEDGE_NODES_POLICIES = get_user_id_policies("knowledge_nodes")
HEARTBEAT_METRICS_POLICIES = get_user_id_policies("heartbeat_metrics")
CONTEXT_METRICS_POLICIES = get_user_id_policies("context_metrics")


# =============================================================================
# Knowledge Edges Table RLS Policies
# =============================================================================

KNOWLEDGE_EDGES_POLICIES = {
    "select_own": """
        CREATE POLICY "Knowledge Edges can view own data" ON knowledge_edges
        FOR SELECT USING (
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
    """,
    "insert_own": """
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
    """,
    "update_own": """
        CREATE POLICY "Knowledge Edges can update own data" ON knowledge_edges
        FOR UPDATE USING (
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
    """,
    "delete_own": """
        CREATE POLICY "Knowledge Edges can delete own data" ON knowledge_edges
        FOR DELETE USING (
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
    """,
    "service_role_full": """
        CREATE POLICY "Service role full access on knowledge_edges" ON knowledge_edges
        FOR ALL USING (auth.jwt() ->> 'role' = 'service_role')
    """,
}


# =============================================================================
# Policy Documentation
# =============================================================================

RLS_POLICY_DOCUMENTATION = """
Row Level Security (RLS) Policy Documentation
==============================================

Overview:
---------
All tables with user-scoped data have RLS enabled to ensure users can only
access their own data. The service_role has full access for backend operations.

Auth Functions Used:
--------------------
- auth.uid(): Returns the UUID of the authenticated user from JWT
- auth.jwt(): Returns the full JWT payload, used for role checking

Policy Pattern for Standard Tables (with user_id):
--------------------------------------------------
1. SELECT: Users can view rows where user_id = auth.uid()
2. INSERT: Users can insert rows where user_id = auth.uid()
3. UPDATE: Users can update rows where user_id = auth.uid()
4. DELETE: Users can delete rows where user_id = auth.uid()
5. Service Role: Full access when auth.jwt() ->> 'role' = 'service_role'

Special Case: Knowledge Edges
-----------------------------
Knowledge edges don't have a direct user_id column. Instead, policies use
a subquery to check that both source_id and target_id reference nodes
belonging to the authenticated user.

Tables with RLS Enabled:
------------------------
1. users              - Direct id comparison
2. sessions           - user_id comparison
3. messages           - user_id comparison
4. core_memories      - user_id comparison
5. recall_memories    - user_id comparison
6. archival_memories  - user_id comparison
7. knowledge_nodes    - user_id comparison
8. knowledge_edges    - Subquery via source_id and target_id to nodes.user_id
9. heartbeat_metrics  - user_id comparison (nullable for system metrics)
10. context_metrics   - user_id comparison

Security Notes:
---------------
- RLS is enforced at the database level, bypassing application-level checks
- Service role key must be protected and only used server-side
- Policies use EXISTS subqueries for both source/target on edge table
- All policies default to DENY if no matching policy is found
"""


# =============================================================================
# Utility Functions
# =============================================================================

def get_all_policies() -> dict[str, dict[str, str]]:
    """Get all RLS policies organized by table.

    Returns:
        Dictionary mapping table names to their policy dictionaries
    """
    return {
        "users": USERS_POLICIES,
        "sessions": SESSIONS_POLICIES,
        "messages": MESSAGES_POLICIES,
        "core_memories": CORE_MEMORIES_POLICIES,
        "recall_memories": RECALL_MEMORIES_POLICIES,
        "archival_memories": ARCHIVAL_MEMORIES_POLICIES,
        "knowledge_nodes": KNOWLEDGE_NODES_POLICIES,
        "knowledge_edges": KNOWLEDGE_EDGES_POLICIES,
        "heartbeat_metrics": HEARTBEAT_METRICS_POLICIES,
        "context_metrics": CONTEXT_METRICS_POLICIES,
    }


def format_policy_sql(table_name: str, policy_type: str) -> str | None:
    """Get formatted SQL for a specific policy.

    Args:
        table_name: Name of the table
        policy_type: Type of policy (select_own, insert_own, etc.)

    Returns:
        SQL string or None if table/policy not found
    """
    policies = get_all_policies().get(table_name)
    if policies:
        return policies.get(policy_type)
    return None
