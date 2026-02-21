"""Discord API mocks para testes do Agnaldo.

Este módulo fornece mocks assíncronos das classes do discord.py
para facilitar testes isolados de componentes Discord.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def create_mock_user(
    user_id: int = 123456789012345678,
    username: str = "TestUser",
    discriminator: str | None = "0000",
    global_name: str | None = "Test User",
    bot: bool = False,
) -> MagicMock:
    """Cria um mock de discord.User.

    Args:
        user_id: ID do usuário (snowflake).
        username: Nome de usuário do Discord.
        discriminator: Discriminador (tag de 4 dígitos).
        global_name: Nome de exibição global.
        bot: Se é um bot.

    Returns:
        MagicMock configurado como User do Discord.
    """
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.name = username
    mock_user.username = username
    mock_user.discriminator = discriminator
    mock_user.global_name = global_name
    mock_user.avatar = "avatar_hash"
    mock_user.bot = bot
    mock_user.system = False
    mock_user.public_flags = 0
    mock_user.created_at = datetime.now(timezone.utc)
    mock_user.mention = f"<@{user_id}>"
    mock_user.display_name = global_name or username

    # Mock para guild_permissions (se necessário)
    mock_permissions = MagicMock()
    mock_permissions.administrator = False
    mock_user.guild_permissions = mock_permissions

    return mock_user


def create_mock_guild(
    guild_id: int = 333444555666777888,
    name: str = "Test Server",
    owner_id: int = 123456789012345678,
) -> MagicMock:
    """Cria um mock de discord.Guild.

    Args:
        guild_id: ID do servidor (snowflake).
        name: Nome do servidor.
        owner_id: ID do usuário dono.

    Returns:
        MagicMock configurado como Guild do Discord.
    """
    mock_guild = MagicMock()
    mock_guild.id = guild_id
    mock_guild.name = name
    mock_guild.owner_id = owner_id
    mock_guild.icon = "icon_hash"
    mock_guild.description = "Test server description"
    mock_guild.member_count = 100
    mock_guild.preferred_locale = "pt-BR"
    mock_guild.emojis = []
    mock_guild.roles = []

    return mock_guild


def create_mock_channel(
    channel_id: int = 777888999000111222,
    name: str = "general",
    channel_type: int = 0,  # 0 = GUILD_TEXT
    guild_id: int | None = 333444555666777888,
) -> MagicMock:
    """Cria um mock de discord.abc.Messageable (canal).

    Args:
        channel_id: ID do canal (snowflake).
        name: Nome do canal.
        channel_type: Tipo do canal (0=texto, 2=voz, etc).
        guild_id: ID do servidor se aplicável.

    Returns:
        MagicMock configurado como Channel do Discord.
    """
    mock_channel = MagicMock()
    mock_channel.id = channel_id
    mock_channel.name = name
    mock_channel.type = channel_type
    mock_channel.guild_id = guild_id
    mock_channel.send = AsyncMock(return_value=None)

    # Configurar guild se guild_id fornecido
    if guild_id:
        mock_channel.guild = create_mock_guild(guild_id=guild_id)

    return mock_channel


def create_mock_message(
    message_id: int = 111222333444555666,
    content: str = "Test message",
    author: MagicMock | None = None,
    channel_id: int = 777888999000111222,
    guild_id: int | None = 333444555666777888,
) -> MagicMock:
    """Cria um mock de discord.Message.

    Args:
        message_id: ID da mensagem (snowflake).
        content: Conteúdo da mensagem.
        author: Mock do autor (User). Se None, cria um padrão.
        channel_id: ID do canal onde foi enviada.
        guild_id: ID do servidor se aplicável.

    Returns:
        MagicMock configurado como Message do Discord.
    """
    mock_message = MagicMock()
    mock_message.id = message_id
    mock_message.content = content
    mock_message.channel = create_mock_channel(channel_id=channel_id, guild_id=guild_id)
    mock_message.channel_id = channel_id
    mock_message.guild_id = guild_id

    if author is None:
        author = create_mock_user()
    mock_message.author = author

    mock_message.created_at = datetime.now(timezone.utc)
    mock_message.edited_at = None
    mock_message.tts = False
    mock_message.mention_everyone = False
    mock_message.attachments = []
    mock_message.embeds = []
    mock_message.reactions = []
    mock_message.pinned = False
    mock_message.type = 0  # DEFAULT

    # Métodos assíncronos comuns
    mock_message.add_reaction = AsyncMock()
    mock_message.remove_reaction = AsyncMock()
    mock_message.reply = AsyncMock()
    mock_message.edit = AsyncMock()
    mock_message.delete = AsyncMock()
    mock_message.pin = AsyncMock()
    mock_message.unpin = AsyncMock()

    return mock_message


def create_mock_interaction(
    interaction_id: int = 999888777666555444,
    user: MagicMock | None = None,
    channel_id: int = 777888999000111222,
    guild_id: int | None = 333444555666777888,
    response_done: bool = False,
) -> MagicMock:
    """Cria um mock de discord.Interaction (slash command).

    Args:
        interaction_id: ID da interação (snowflake).
        user: Mock do usuário. Se None, cria um padrão.
        channel_id: ID do canal da interação.
        guild_id: ID do servidor se aplicável.
        response_done: Se response.is_done() retorna True.

    Returns:
        MagicMock configurado como Interaction do Discord.
    """
    mock_interaction = MagicMock()
    mock_interaction.id = interaction_id

    if user is None:
        user = create_mock_user()
    mock_interaction.user = user

    mock_interaction.channel_id = channel_id
    mock_interaction.guild_id = guild_id
    mock_interaction.channel = create_mock_channel(channel_id=channel_id, guild_id=guild_id)

    if guild_id:
        mock_interaction.guild = create_mock_guild(guild_id=guild_id)

    # Configurar response mock
    mock_response = MagicMock()
    mock_response.is_done = MagicMock(return_value=response_done)

    # Métodos de response assíncronos
    mock_response.send_message = AsyncMock()
    mock_response.defer = AsyncMock()
    mock_response.edit_message = AsyncMock()

    # Alias para followup
    mock_followup = MagicMock()
    mock_followup.send = AsyncMock()
    mock_interaction.followup = mock_followup

    mock_interaction.response = mock_response

    return mock_interaction


def create_mock_bot(
    bot_id: int = 111222333444555666,
    username: str = "Agnaldo",
    latency: float = 0.05,
    guilds_count: int = 5,
) -> MagicMock:
    """Cria um mock de discord.ext.commands.Bot.

    Args:
        bot_id: ID do bot (snowflake).
        username: Nome do bot.
        latency: Latência simulada em segundos.
        guilds_count: Número de servidores conectados.

    Returns:
        MagicMock configurado como Bot do Discord.
    """
    mock_bot = MagicMock()

    # Configurar user do bot
    mock_bot.user = create_mock_user(user_id=bot_id, username=username, bot=True)
    mock_bot.app = MagicMock()  # ClientApplication
    mock_bot.app.id = bot_id

    mock_bot.latency = latency

    # Mock de guilds
    mock_guilds = [
        create_mock_guild(guild_id=f"{i}333444555666777888") for i in range(guilds_count)
    ]
    mock_bot.guilds = mock_guilds

    # Mock de tree (comandos slash)
    mock_tree = MagicMock()
    mock_tree.sync = AsyncMock()
    mock_tree.add_command = MagicMock()
    mock_tree.get_command = MagicMock()
    mock_tree.remove_command = MagicMock()
    mock_bot.tree = mock_tree

    # Rate limiter mock
    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock()
    mock_rate_limiter.get_available_tokens = MagicMock(
        return_value={
            "global_tokens": 50.0,
            "channel_tokens": 5.0,
        }
    )
    mock_bot.get_rate_limiter = MagicMock(return_value=mock_rate_limiter)

    # Database pool
    mock_bot.db_pool = None  # Será configurado pelo teste

    return mock_bot


def create_mock_rate_limiter(
    global_tokens: float = 50.0,
    channel_tokens: float = 5.0,
    global_limit: int = 50,
    channel_limit: int = 5,
) -> MagicMock:
    """Cria um mock do RateLimiter.

    Args:
        global_tokens: Tokens globais disponíveis.
        channel_tokens: Tokens por canal disponíveis.
        global_limit: Limite global de requisições.
        channel_limit: Limite por canal de requisições.

    Returns:
        MagicMock configurado como RateLimiter.
    """
    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock()
    mock_rate_limiter.get_available_tokens = MagicMock(
        return_value={
            "global_tokens": global_tokens,
            "channel_tokens": channel_tokens,
        }
    )
    mock_rate_limiter.global_limit = global_limit
    mock_rate_limiter.channel_limit = channel_limit

    return mock_rate_limiter


@pytest.fixture
def mock_discord_user():
    """Fixture pytest que retorna um mock de User do Discord."""
    return create_mock_user()


@pytest.fixture
def mock_discord_guild():
    """Fixture pytest que retorna um mock de Guild do Discord."""
    return create_mock_guild()


@pytest.fixture
def mock_discord_channel():
    """Fixture pytest que retorna um mock de Channel do Discord."""
    return create_mock_channel()


@pytest.fixture
def mock_discord_message():
    """Fixture pytest que retorna um mock de Message do Discord."""
    return create_mock_message()


@pytest.fixture
def mock_discord_interaction():
    """Fixture pytest que retorna um mock de Interaction do Discord."""
    return create_mock_interaction()


@pytest.fixture
def mock_discord_bot():
    """Fixture pytest que retorna um mock de Bot do Discord."""
    return create_mock_bot()


@pytest.fixture
def mock_rate_limiter():
    """Fixture pytest que retorna um mock de RateLimiter."""
    return create_mock_rate_limiter()
