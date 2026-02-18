"""
Discord-related schemas for Agnaldo.

This module defines Pydantic v2 schemas for Discord entities including
users, messages, commands, attachments, channels, and guilds.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DiscordEmbed(BaseModel):
    """Typed representation for Discord embeds."""

    title: str | None = None
    description: str | None = None
    type: str | None = None
    url: str | None = None


class DiscordReaction(BaseModel):
    """Typed representation for Discord reactions."""

    emoji: dict[str, Any] = Field(default_factory=dict)
    count: int = Field(default=0, ge=0)
    me: bool = Field(default=False)


class DiscordUser(BaseModel):
    """Discord user information.

    Attributes:
        id: Discord user ID (snowflake).
        username: Discord username.
        discriminator: User discriminator (legacy 4-digit tag).
        global_name: User's display name.
        avatar_hash: Hash for user's avatar.
        is_bot: Whether the user is a bot.
        is_system: Whether the user is a system user.
        public_flags: Public flags for the user.
        created_at: Account creation timestamp.
    """

    id: str = Field(..., description="Discord user ID (snowflake)")
    username: str = Field(..., min_length=1, max_length=32, description="Discord username")
    discriminator: str | None = Field(
        None, description="User discriminator (legacy 4-digit tag)"
    )
    global_name: str | None = Field(None, description="User's display name")
    avatar_hash: str | None = Field(None, description="Hash for user's avatar")
    is_bot: bool = Field(default=False, description="Whether the user is a bot")
    is_system: bool = Field(default=False, description="Whether the user is a system user")
    public_flags: int = Field(default=0, description="Public flags for the user")
    created_at: datetime | None = Field(None, description="Account creation timestamp")

    model_config = {"use_enum_values": True}

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "123456789012345678",
                    "username": "Agnaldo",
                    "discriminator": "0000",
                    "global_name": "Agnaldo Bot",
                    "avatar_hash": "a_hash_value",
                    "is_bot": True,
                    "is_system": False,
                    "public_flags": 0,
                }
            ]
        }


class DiscordAttachment(BaseModel):
    """Discord message attachment.

    Attributes:
        id: Attachment ID (snowflake).
        filename: Original filename of the attachment.
        url: URL to download the attachment.
        proxy_url: Proxied URL for the attachment.
        size: Size of the attachment in bytes.
        content_type: MIME type of the attachment.
        description: User-provided description (alt text).
        ephemeral: Whether the attachment is ephemeral.
        width: Image width if applicable.
        height: Image height if applicable.
    """

    id: str = Field(..., description="Attachment ID (snowflake)")
    filename: str = Field(..., description="Original filename")
    url: str = Field(..., description="URL to download the attachment")
    proxy_url: str = Field(..., description="Proxied URL for the attachment")
    size: int = Field(..., ge=0, description="Size in bytes")
    content_type: str | None = Field(None, description="MIME type of the attachment")
    description: str | None = Field(None, description="User-provided description (alt text)")
    ephemeral: bool = Field(default=False, description="Whether attachment is ephemeral")
    width: int | None = Field(None, ge=0, description="Image width if applicable")
    height: int | None = Field(None, ge=0, description="Image height if applicable")

    model_config = {"use_enum_values": True}

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "987654321098765432",
                    "filename": "document.pdf",
                    "url": "https://cdn.discordapp.com/attachments/...",
                    "proxy_url": "https://media.discordapp.net/attachments/...",
                    "size": 1048576,
                    "content_type": "application/pdf",
                    "description": "Project documentation",
                    "ephemeral": False,
                }
            ]
        }


class DiscordMessage(BaseModel):
    """Discord message information.

    Attributes:
        id: Message ID (snowflake).
        channel_id: Channel ID where message was sent.
        guild_id: Guild ID if in a guild.
        author: Message author information.
        content: Message content text.
        timestamp: Message creation timestamp.
        edited_timestamp: Timestamp of last edit if edited.
        tts: Whether this is a TTS message.
        mention_everyone: Whether @everyone was mentioned.
        attachments: List of attachments in the message.
        embeds: List of embeds in the message.
        reactions: List of reactions on the message.
        pinned: Whether the message is pinned.
        type: Message type integer.
        message_reference: Reference if this is a reply.
    """

    id: str = Field(..., description="Message ID (snowflake)")
    channel_id: str = Field(..., description="Channel ID where message was sent")
    guild_id: str | None = Field(None, description="Guild ID if in a guild")
    author: DiscordUser = Field(..., description="Message author information")
    content: str = Field(default="", description="Message content text")
    timestamp: datetime = Field(..., description="Message creation timestamp")
    edited_timestamp: datetime | None = Field(None, description="Timestamp of last edit")
    tts: bool = Field(default=False, description="Whether this is a TTS message")
    mention_everyone: bool = Field(
        default=False, description="Whether @everyone was mentioned"
    )
    attachments: list[DiscordAttachment] = Field(
        default_factory=list, description="Message attachments"
    )
    embeds: list[DiscordEmbed] = Field(default_factory=list, description="Message embeds")
    reactions: list[DiscordReaction] = Field(
        default_factory=list, description="Message reactions"
    )
    pinned: bool = Field(default=False, description="Whether the message is pinned")
    type: int = Field(default=0, description="Message type integer")
    message_reference: dict[str, Any] | None = Field(
        None, description="Reference if this is a reply"
    )

    model_config = {"use_enum_values": True}

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "111222333444555666",
                    "channel_id": "777888999000111222",
                    "guild_id": "333444555666777888",
                    "author": {"id": "123456789012345678", "username": "User", "is_bot": False},
                    "content": "Hello, Agnaldo!",
                    "timestamp": "2026-02-17T12:00:00Z",
                    "attachments": [],
                    "pinned": False,
                    "type": 0,
                }
            ]
        }


class DiscordCommandType(str, Enum):
    """Types of Discord commands."""

    CHAT_INPUT = "chat_input"
    """Slash command invoked from chat input."""

    USER = "user"
    """Context menu command on a user."""

    MESSAGE = "message"
    """Context menu command on a message."""

    class Config:
        use_enum_values = True


class DiscordCommand(BaseModel):
    """Discord command (slash command) information.

    Attributes:
        id: Command ID (snowflake).
        type: Type of command (chat_input, user, message).
        application_id: Application ID that created the command.
        guild_id: Guild ID if guild-specific command.
        name: Command name.
        description: Command description (for chat_input).
        options: Command options/parameters.
        default_permission: Whether command is enabled by default.
        version: Command auto-incrementing version.
        created_at: Command creation timestamp.
        updated_at: Last update timestamp.
    """

    id: str = Field(..., description="Command ID (snowflake)")
    type: DiscordCommandType = Field(
        default=DiscordCommandType.CHAT_INPUT, description="Type of command"
    )
    application_id: str = Field(..., description="Application ID that created the command")
    guild_id: str | None = Field(None, description="Guild ID if guild-specific")
    name: str = Field(..., min_length=1, max_length=32, description="Command name")
    description: str = Field(default="", description="Command description")
    options: list[dict[str, Any]] = Field(
        default_factory=list, description="Command options/parameters"
    )
    default_permission: bool = Field(
        default=True, description="Whether enabled by default"
    )
    version: str = Field(..., description="Command version identifier")
    created_at: datetime | None = Field(None, description="Command creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    model_config = {"use_enum_values": True}

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "999888777666555444",
                    "type": "chat_input",
                    "application_id": "111222333444555666",
                    "name": "ask",
                    "description": "Ask Agnaldo a question",
                    "options": [],
                    "default_permission": True,
                    "version": "1.0.0",
                }
            ]
        }


class DiscordChannelType(str, Enum):
    """Types of Discord channels."""

    GUILD_TEXT = "guild_text"
    """Text channel in a guild."""

    GUILD_VOICE = "guild_voice"
    """Voice channel in a guild."""

    GUILD_CATEGORY = "guild_category"
    """Category for organizing channels."""

    DM = "dm"
    """Direct message channel."""

    GROUP_DM = "group_dm"
    """Group direct message channel."""

    GUILD_NEWS = "guild_news"
    """News/announcement channel."""

    GUILD_NEWS_THREAD = "guild_news_thread"
    """Thread in a news channel."""

    GUILD_PUBLIC_THREAD = "guild_public_thread"
    """Public thread in a text channel."""

    GUILD_PRIVATE_THREAD = "guild_private_thread"
    """Private thread in a text channel."""

    class Config:
        use_enum_values = True


class DiscordChannel(BaseModel):
    """Discord channel information.

    Attributes:
        id: Channel ID (snowflake).
        type: Channel type.
        guild_id: Guild ID if in a guild.
        position: Sorting position in channel list.
        name: Channel name.
        topic: Channel topic/description.
        nsfw: Whether channel is NSFW.
        last_message_id: ID of last message in channel.
        bitrate: Voice channel bitrate if applicable.
        user_limit: Voice channel user limit if applicable.
        rate_limit_per_user: Slowmode delay in seconds.
        parent_id: Category parent ID if applicable.
        created_at: Channel creation timestamp.
    """

    id: str = Field(..., description="Channel ID (snowflake)")
    type: DiscordChannelType = Field(..., description="Channel type")
    guild_id: str | None = Field(None, description="Guild ID if in a guild")
    position: int | None = Field(None, description="Sorting position")
    name: str | None = Field(None, max_length=100, description="Channel name")
    topic: str | None = Field(None, max_length=1024, description="Channel topic")
    nsfw: bool = Field(default=False, description="Whether channel is NSFW")
    last_message_id: str | None = Field(None, description="ID of last message")
    bitrate: int | None = Field(None, ge=0, description="Voice channel bitrate")
    user_limit: int | None = Field(None, ge=0, description="Voice channel user limit")
    rate_limit_per_user: int = Field(default=0, ge=0, description="Slowmode delay")
    parent_id: str | None = Field(None, description="Category parent ID")
    created_at: datetime | None = Field(None, description="Channel creation timestamp")

    model_config = {"use_enum_values": True}

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "777888999000111222",
                    "type": "guild_text",
                    "guild_id": "333444555666777888",
                    "position": 0,
                    "name": "general",
                    "topic": "General discussion",
                    "nsfw": False,
                    "rate_limit_per_user": 0,
                }
            ]
        }


class DiscordGuild(BaseModel):
    """Discord guild (server) information.

    Attributes:
        id: Guild ID (snowflake).
        name: Guild name.
        icon_hash: Hash for guild icon.
        description: Guild description.
        splash_hash: Hash for splash image.
        owner_id: Owner user ID.
        region: Voice region (deprecated).
        afk_channel_id: AFK voice channel ID.
        afk_timeout: AFK timeout in seconds.
        verification_level: Required verification level.
        default_message_notifications: Default notification level.
        explicit_content_filter: Explicit content filter level.
        roles: List of roles in the guild.
        emojis: List of emojis in the guild.
        features: List of guild features.
        mfa_level: Required MFA level.
        application_id: Application ID if bot is creator.
        system_channel_id: System channel ID.
        premium_tier: Server boost level.
        member_count: Approximate member count.
        created_at: Guild creation timestamp.
    """

    id: str = Field(..., description="Guild ID (snowflake)")
    name: str = Field(..., min_length=1, max_length=100, description="Guild name")
    icon_hash: str | None = Field(None, description="Hash for guild icon")
    description: str | None = Field(None, description="Guild description")
    splash_hash: str | None = Field(None, description="Hash for splash image")
    owner_id: str = Field(..., description="Owner user ID")
    region: str | None = Field(None, description="Voice region (deprecated)")
    afk_channel_id: str | None = Field(None, description="AFK voice channel ID")
    afk_timeout: int = Field(default=300, ge=0, description="AFK timeout in seconds")
    verification_level: int = Field(default=0, ge=0, le=4, description="Verification level")
    default_message_notifications: int = Field(
        default=0, description="Default notification level"
    )
    explicit_content_filter: int = Field(
        default=0, ge=0, le=2, description="Explicit content filter level"
    )
    roles: list[dict[str, Any]] = Field(default_factory=list, description="Guild roles")
    emojis: list[dict[str, Any]] = Field(default_factory=list, description="Guild emojis")
    features: list[str] = Field(default_factory=list, description="Guild features")
    mfa_level: int = Field(default=0, ge=0, le=1, description="Required MFA level")
    application_id: str | None = Field(None, description="Application ID if bot creator")
    system_channel_id: str | None = Field(None, description="System channel ID")
    premium_tier: int = Field(default=0, ge=0, le=3, description="Server boost level")
    member_count: int | None = Field(None, ge=0, description="Approximate member count")
    created_at: datetime | None = Field(None, description="Guild creation timestamp")

    model_config = {"use_enum_values": True}

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "333444555666777888",
                    "name": "Agnaldo's Server",
                    "icon_hash": "icon_hash_value",
                    "owner_id": "123456789012345678",
                    "afk_timeout": 300,
                    "verification_level": 0,
                    "default_message_notifications": 0,
                    "explicit_content_filter": 0,
                    "premium_tier": 1,
                    "member_count": 150,
                }
            ]
        }
