"""Slash command handlers for Discord bot."""

from discord.ext.commands import Bot
from loguru import logger

from discord import app_commands
from src.knowledge.graph import KnowledgeGraph
from src.memory.core import CoreMemory
from src.memory.recall import RecallMemory


def _preview_with_ellipsis(text: str, max_len: int = 100) -> str:
    """Render preview with ellipsis only when text is truncated."""
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."


async def setup_commands(bot: Bot) -> None:
    """
    Register all slash commands with the bot.

    Args:
        bot: The bot instance to register commands with.
    """

    @bot.tree.command(name="ping", description="Check if the bot is responsive")
    async def ping(interaction) -> None:
        """Respond to ping command with latency."""
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        latency = round(bot.latency * 1000)
        await interaction.followup.send(f"Pong! 🏓 Latency: {latency}ms", ephemeral=True)
        logger.info(f"Ping command executed by {interaction.user} (Latency: {latency}ms)")

    @bot.tree.command(name="help", description="Show available commands")
    async def help_command(interaction) -> None:
        """Display help information."""
        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        help_text = """
**Agnaldo Bot Commands**

`/ping` - Check bot responsiveness and latency
`/help` - Show this help message
`/status` - Show bot status and rate limit info

More commands coming soon!
        """
        await interaction.response.send_message(help_text, ephemeral=True)
        logger.info(f"Help command executed by {interaction.user}")

    @bot.tree.command(name="status", description="Show bot status and rate limit info")
    async def status(interaction) -> None:
        """Display bot status including rate limiter state."""
        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        tokens_info = rate_limiter.get_available_tokens(channel_id=str(interaction.channel_id))
        global_tokens = tokens_info.get("global_tokens")
        channel_tokens = tokens_info.get("channel_tokens")
        global_text = (
            f"{float(global_tokens):.1f}" if isinstance(global_tokens, (int, float)) else "N/A"
        )
        channel_text = (
            f"{float(channel_tokens):.1f}" if isinstance(channel_tokens, (int, float)) else "N/A"
        )

        status_text = f"""
**Agnaldo Bot Status**

Connected as: {bot.user.mention}
Servers: {len(bot.guilds)}
Latency: {round(bot.latency * 1000)}ms

**Rate Limit Status**
Global tokens available: {global_text}
Channel tokens available: {channel_text}
        """
        await interaction.response.send_message(status_text, ephemeral=True)
        logger.info(f"Status command executed by {interaction.user}")

    @bot.tree.command(name="sync", description="Sync commands with Discord (Admin only)")
    async def sync_commands(interaction) -> None:
        """Manually sync slash commands with Discord."""
        # Check for admin permissions
        permissions = getattr(interaction.user, "guild_permissions", None)
        is_admin = bool(permissions and permissions.administrator)
        if not is_admin:
            await interaction.response.send_message(
                "You need administrator permissions to use this command.", ephemeral=True
            )
            return

        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        try:
            # Sync commands globally (takes up to 1 hour) or to the current guild
            await bot.tree.sync()
            await interaction.response.send_message(
                "Commands have been synced globally!", ephemeral=True
            )
            logger.info(f"Commands synced by {interaction.user}")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            await interaction.response.send_message(f"Failed to sync commands: {e}", ephemeral=True)

    # ================================================================
    # Memory Commands
    # ================================================================

    memory_group = app_commands.Group(
        name="memory",
        description="Memory management commands",
    )

    @memory_group.command(name="add", description="Store an important fact in core memory")
    @app_commands.describe(
        key="Unique key for memory (e.g., 'preference-language')",
        value="The value/content to store",
        importance="Importance score from 0.0 to 1.0 (default: 0.5)",
    )
    async def memory_add(
        interaction,
        key: str,
        value: str,
        importance: float = 0.5,
    ) -> None:
        """Store a fact in core memory."""
        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        # Validate importance
        if not 0.0 <= importance <= 1.0:
            await interaction.response.send_message(
                "Importance must be between 0.0 and 1.0", ephemeral=True
            )
            return

        try:
            # Get database pool from bot
            db_pool = getattr(bot, "db_pool", None)
            if not db_pool:
                await interaction.response.send_message("Database not available", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            core_memory = CoreMemory(user_id, db_pool)

            await core_memory.add(key, value, importance=importance)

            await interaction.response.send_message(
                f"✅ Stored: `{key}` = `{value}` (importance: {importance})",
                ephemeral=True,
            )
            logger.info(f"Memory added by {interaction.user}: {key}={value}")

        except Exception as e:
            logger.error(f"Memory add error: {e}")
            await interaction.response.response.send_message(
                f"Failed to store memory: {e}", ephemeral=True
            )

    @memory_group.command(name="recall", description="Search your memories by semantic similarity")
    @app_commands.describe(
        query="What to search for in your memories",
        limit="Maximum number of results (default: 5)",
    )
    async def memory_recall(
        interaction,
        query: str,
        limit: int = 5,
    ) -> None:
        """Search memories semantically."""
        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        try:
            db_pool = getattr(bot, "db_pool", None)
            if not db_pool:
                await interaction.response.send_message("Database not available", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            recall_memory = RecallMemory(user_id, db_pool)

            results = await recall_memory.search(query, limit=limit, threshold=0.5)

            if not results:
                await interaction.response.send_message(
                    f"🔍 No memories found for: `{query}`", ephemeral=True
                )
                return

            # Format results
            response_parts = [f"🔍 Found {len(results)} memories for: `{query}`\n"]
            for i, r in enumerate(results[:10], 1):
                similarity_pct = int(r["similarity"] * 100)
                preview = _preview_with_ellipsis(r["content"], 100)
                response_parts.append(f"**{i}.** {preview} (similarity: {similarity_pct}%)")

            await interaction.response.send_message("\n".join(response_parts), ephemeral=True)
            logger.info(f"Memory recall by {interaction.user}: {query} ({len(results)} results)")

        except Exception as e:
            logger.error(f"Memory recall error: {e}")
            await interaction.response.send_message(
                f"Failed to search memories: {e}", ephemeral=True
            )

    # ================================================================
    # Chat Commands (NEW - Natural conversation)
    # ================================================================

    @bot.tree.command(name="chat", description="Chat naturalmente com o Agno")
    async def chat_command(interaction) -> None:
        """Process natural language message through Agno agents."""
        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        try:
            # Get message handler if available
            message_handler = getattr(bot, "message_handler", None)
            if not message_handler:
                await interaction.response.send_message(
                    "Sistema de agentes ainda está configurando. Tente novamente em alguns segundos.",
                    ephemeral=True,
                )
                return

            # Process message through agent handler
            response = await message_handler.process_message(interaction.message)

            # Send response or handle error
            if response:
                await interaction.response.send_message(response, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "Não consegui entender sua mensagem. Tente ser mais específico.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Chat command error: {e}")
            await interaction.response.send_message(
                f"Ocorreu um erro no comando chat: {e}",
                ephemeral=True,
            )

    # ================================================================
    # Knowledge Graph Commands
    # ================================================================

    # ================================================================
    # Knowledge Graph Commands
    # ================================================================

    graph_group = app_commands.Group(
        name="graph",
        description="Knowledge graph commands",
    )

    @graph_group.command(name="add_node", description="Add a node to the knowledge graph")
    @app_commands.describe(
        label="Node label/name (e.g., 'Python', 'Discord API')",
        node_type="Type/category (optional, e.g., 'language', 'API', 'concept')",
    )
    async def graph_add_node(
        interaction,
        label: str,
        node_type: str | None = None,
    ) -> None:
        """Add a node to the knowledge graph."""
        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        try:
            db_pool = getattr(bot, "db_pool", None)
            if not db_pool:
                await interaction.response.send_message("Database not available", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            graph = KnowledgeGraph(user_id, db_pool)

            await graph.add_node(label, node_type)

            await interaction.response.send_message(
                f"✅ Added node: **{label}** (type: {node_type or 'default'})",
                ephemeral=True,
            )
            logger.info(f"Graph node added by {interaction.user}: {label}")

        except Exception as e:
            logger.error(f"Graph add_node error: {e}")
            await interaction.response.send_message(f"Failed to add node: {e}", ephemeral=True)

    @graph_group.command(name="add_edge", description="Add a relationship between two concepts")
    @app_commands.describe(
        source="Source node label",
        target="Target node label",
        edge_type="Relationship type (e.g., 'relates_to', 'part_of', 'used_for')",
        weight="Strength of relationship (0.0 to 2.0, default: 1.0)",
    )
    async def graph_add_edge(
        interaction,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
    ) -> None:
        """Add an edge to the knowledge graph."""
        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        try:
            db_pool = getattr(bot, "db_pool", None)
            if not db_pool:
                await interaction.response.send_message("Database not available", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            graph = KnowledgeGraph(user_id, db_pool)

            # First, find or create the nodes
            source_results = await graph.search_nodes(source, limit=1, threshold=0.3)
            target_results = await graph.search_nodes(target, limit=1, threshold=0.3)

            if not source_results:
                source_node = await graph.add_node(source)
                source_id = source_node.id
            else:
                source_id = source_results[0]["node_id"]

            if not target_results:
                target_node = await graph.add_node(target)
                target_id = target_node.id
            else:
                target_id = target_results[0]["node_id"]

            # Add edge
            await graph.add_edge(source_id, target_id, edge_type, weight)

            await interaction.response.send_message(
                f"✅ Added relationship: **{source}** → *{edge_type}* → **{target}**",
                ephemeral=True,
            )
            logger.info(f"Graph edge added by {interaction.user}: {source}->{target} ({edge_type})")

        except Exception as e:
            logger.error(f"Graph add_edge error: {e}")
            await interaction.response.send_message(f"Failed to add edge: {e}", ephemeral=True)

    @graph_group.command(name="query", description="Search the knowledge graph semantically")
    @app_commands.describe(
        query="What to search for",
        limit="Maximum results (default: 5)",
    )
    async def graph_query(
        interaction,
        query: str,
        limit: int = 5,
    ) -> None:
        """Search the knowledge graph."""
        # Apply rate limiting
        rate_limiter = bot.get_rate_limiter()
        await rate_limiter.acquire(channel_id=str(interaction.channel_id))

        try:
            db_pool = getattr(bot, "db_pool", None)
            if not db_pool:
                await interaction.response.send_message("Database not available", ephemeral=True)
                return

            user_id = str(interaction.user.id)
            graph = KnowledgeGraph(user_id, db_pool)

            results = await graph.search_nodes(query, limit=limit, threshold=0.5)

            if not results:
                await interaction.response.send_message(
                    f"🔍 No nodes found for: `{query}`\n\n"
                    f"💡 Tip: Use `/graph add_node` to create nodes first!",
                    ephemeral=True,
                )
                return

            # Format results with connections
            response_parts = [f"🔍 Found {len(results)} nodes for: `{query}`\n"]

            for r in results:
                similarity_pct = int(r["similarity"] * 100)
                node_type = f" [{r['node_type']}]" if r["node_type"] else ""
                response_parts.append(
                    f"**{r['label']}**{node_type} (similarity: {similarity_pct}%)"
                )

                # Get neighbors for this node
                neighbors = await graph.get_neighbors(r["node_id"], direction="both")
                if neighbors:
                    neighbor_labels = [n.label for n in neighbors[:5]]
                    response_parts.append(f"   ↪ Connected to: {', '.join(neighbor_labels)}")

            await interaction.response.send_message("\n".join(response_parts), ephemeral=True)
            logger.info(f"Graph query by {interaction.user}: {query} ({len(results)} results)")

        except Exception as e:
            logger.error(f"Graph query error: {e}")
            await interaction.response.send_message(f"Failed to query graph: {e}", ephemeral=True)

    try:
        bot.tree.add_command(memory_group)
    except app_commands.CommandAlreadyRegistered:
        logger.debug("Memory command group already registered")

    try:
        bot.tree.add_command(graph_group)
    except app_commands.CommandAlreadyRegistered:
        logger.debug("Graph command group already registered")

    logger.info("Slash commands registered")
