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


def create_bot() -> AgnaldoBot:
    """
    Factory function to create a new bot instance.

    Returns:
        AgnaldoBot: Configured bot instance.
    """
    bot = AgnaldoBot()
    logger.info("Agnaldo bot instance created")
    return bot
