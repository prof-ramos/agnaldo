"""Event handlers for Discord bot."""

import re
from typing import Any

from discord.ext.commands import Bot
from loguru import logger

from discord import Guild, Interaction, Message


def sanitize_message_preview(content: str, max_chars: int = 80) -> str:
    """Create a safer message preview for debug logs."""
    if not content:
        return "<empty>"

    normalized = " ".join(content.split())
    redacted = re.sub(r"https?://\S+", "[url]", normalized, flags=re.IGNORECASE)
    redacted = re.sub(r"\S+@\S+\.\S+", "[email]", redacted)
    redacted = re.sub(r"\b\d{4,}\b", "[number]", redacted)

    if len(redacted) <= max_chars:
        return redacted
    return f"{redacted[:max_chars]}..."


async def _send_context_message(ctx: Any, message: str) -> None:
    """Send message to context while handling ephemeral compatibility."""
    interaction = ctx if isinstance(ctx, Interaction) else getattr(ctx, "interaction", None)
    if isinstance(interaction, Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=True)
            else:
                await interaction.followup.send(message, ephemeral=True)
            return
        except Exception:
            logger.debug(
                "Failed to send interaction ephemeral response, falling back to regular send"
            )

    await ctx.send(message)


def setup_events(bot: Bot) -> None:
    """
    Register all event handlers with the bot.

    Args:
        bot: The bot instance to register events with.
    """

    @bot.event
    async def on_guild_join(guild: Guild) -> None:
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

    @bot.event
    async def on_guild_remove(guild: Guild) -> None:
        """Called when the bot leaves a guild."""
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")

    @bot.event
    async def on_message(message: Message) -> None:
        """Called when a message is received."""
        # Ignore messages from bots
        if message.author.bot:
            return

        # Process commands first
        await bot.process_commands(message)

        # Process natural messages through agent handler
        if message_handler := bot.message_handler:
            try:
                response = await message_handler.process_message(message)
                if response:
                    await message.channel.send(response)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
                await message.channel.send("Ocorreu um erro ao processar sua mensagem.")

        # Log message for monitoring (in dev mode only)
        if bot.settings.is_dev:
            preview = sanitize_message_preview(message.content)
            author_id = getattr(message.author, "id", None)
            channel_id = getattr(message.channel, "id", None)
            logger.debug(
                f"Message metadata author_id={author_id} channel_id={channel_id} preview={preview}"
            )

    @bot.event
    async def on_command_completion(ctx) -> None:
        """Called when a command completes successfully."""
        command_name = getattr(getattr(ctx, "command", None), "qualified_name", None)
        author_id = getattr(getattr(ctx, "author", None), "id", None)
        channel_id = getattr(getattr(ctx, "channel", None), "id", None)
        logger.info(
            f"Command '{command_name or '<unknown>'}' completed successfully "
            f"(user_id={author_id}, channel_id={channel_id})"
        )

    @bot.event
    async def on_command_error(ctx, error) -> None:
        """Called when a command raises an error."""
        command = getattr(ctx, "command", None)
        command_name = getattr(command, "qualified_name", None) or str(command or "<unknown>")
        logger.error(f"Command '{command_name}' raised error: {error}")

        # Prevent default error handling
        if command and hasattr(command, "on_error"):
            return

        # Send user-friendly error message
        error_messages = {
            "CommandNotFound": "Unknown command. Use /help to see available commands.",
            "MissingPermissions": "You don't have permission to use this command.",
            "BotMissingPermissions": "I'm missing required permissions for this command.",
        }

        error_type = type(error).__name__
        message = error_messages.get(error_type, "An error occurred while executing the command.")

        try:
            await _send_context_message(ctx, message)
        except Exception:
            logger.warning("Failed to send error message to user")

    logger.info("Event handlers registered")
