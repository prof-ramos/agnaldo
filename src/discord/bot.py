"""Discord bot core implementation."""

from typing import Any

from discord import Intents
from discord.ext.commands import Bot

from loguru import logger

from src.config.settings import get_settings
from src.discord.commands import setup_commands
from src.discord.events import setup_events
from src.discord.rate_limiter import RateLimiter


class AgnaldoBot(Bot):
    """Custom Discord bot with rate limiting."""

    def __init__(self) -> None:
        """Initialize the bot with configured intents."""
        settings = get_settings()

        # Configure intents based on settings
        intents = Intents.default()
        intents.message_content = "message_content" in settings.DISCORD_INTENTS
        intents.guild_messages = "guild_messages" in settings.DISCORD_INTENTS
        intents.dm_messages = "dm_messages" in settings.DISCORD_INTENTS

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,  # We'll use slash commands
        )

        self.rate_limiter = RateLimiter()
        self.settings = settings
        self.personality: str | None = None
        self.db_pool: Any = None  # Set during initialization

    async def setup_hook(self) -> None:
        """
        Called when the bot is starting up.

        Sets up commands and event handlers.
        """
        logger.info("Setting up bot hooks...")

        # Setup event handlers
        setup_events(self)

        # Setup slash commands
        await setup_commands(self)
        await self.tree.sync()

        logger.info("Bot setup complete")

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Connected to {len(self.guilds)} guilds")

    def get_rate_limiter(self) -> RateLimiter:
        """Get the bot's rate limiter instance."""
        return self.rate_limiter

    async def process_message(self, message: Message) -> str | None:
        """Process a message through Agno agents.

        Args:
            message: Discord message to process.

        Returns:
            Agent response or None if message should be ignored.
        """
        # Ignore messages from bots
        if message.author.bot:
            return None

        # Ignore empty messages
        if not message.content or not message.content.strip():
            return None

        # Get user ID for memory isolation
        user_id = str(message.author.id)

        # Build context for agent
        context = {
            "username": message.author.display_name,
            "global_name": message.author.global_name,
            "channel_id": str(message.channel.id),
            "guild_id": str(message.guild.id) if message.guild else None,
            "guild_name": message.guild.name if message.guild else "DM",
            "is_dm": message.guild is None,
        }

        try:
            # Ensure message handler is initialized
            if self.message_handler is None:
                logger.warning("Message handler not initialized, skipping message processing")
                return "Desculpe, o sistema está configurando..."

            # Process message through handler
            response = await self.message_handler.process_message(message, context)

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Ocorreu um erro ao processar sua mensagem: {e}"

    def set_message_handler(self, message_handler) -> None:
        """Set the message handler for agent processing."""
        self.message_handler = message_handler


def create_bot() -> AgnaldoBot:
    """
    Factory function to create a new bot instance.

    Returns:
        AgnaldoBot: Configured bot instance.
    """
    bot = AgnaldoBot()
    logger.info("Agnaldo bot instance created")
    return bot
