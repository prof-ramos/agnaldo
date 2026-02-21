"""Fixtures compartilhadas para testes do Agnaldo.

Este módulo fornece fixtures reutilizáveis para testes de memória,
grafo de conhecimento, Discord e integrações externas.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from faker import Faker

from src.knowledge.graph import KnowledgeEdge, KnowledgeNode
from src.schemas.memory import CoreMemoryItem

# ============================================================================
# Fixtures de Banco de Dados
# ============================================================================


@pytest.fixture
def mock_asyncpg_pool() -> MagicMock:
    """Mock de pool asyncpg com suporte a acquire().

    Retorna um mock que suporta o pattern de async context manager
    usado para adquirir conexões do pool.

    Example:
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT...")
    """
    mock_pool = MagicMock()

    # Criar mock de conexão
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchval = AsyncMock(return_value=None)
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock(return_value="SELECT 1")

    # Configurar acquire() para retornar async context manager
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm

    return mock_pool


@pytest.fixture
def build_mock_pool():
    """Helper function para criar mock pool com conexão customizada.

    Esta função permite customizar o comportamento do mock de conexão
    para diferentes cenários de teste.

    Args:
        mock_conn: AsyncMock de conexão customizada.

    Returns:
        MagicMock configurado como pool asyncpg.

    Example:
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = "test-id"
        pool = build_mock_pool(mock_conn)
    """

    def _build(mock_conn: AsyncMock) -> MagicMock:
        mock_pool = MagicMock()
        acquire_cm = AsyncMock()
        acquire_cm.__aenter__.return_value = mock_conn
        acquire_cm.__aexit__.return_value = None
        mock_pool.acquire.return_value = acquire_cm
        return mock_pool

    return _build


# ============================================================================
# Fixtures de OpenAI
# ============================================================================


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Mock de client OpenAI com embeddings e chat completions.

    Configura respostas padrão para:
    - embeddings.create: Retorna vetor de 1536 dimensões
    - chat.completions.create: Retorna resposta básica

    Example:
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        )
    """
    mock_client = MagicMock()

    # Mock para embeddings
    mock_embeddings = MagicMock()
    mock_embeddings.create = AsyncMock()
    mock_embeddings.create.return_value = MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
    mock_client.embeddings = mock_embeddings

    # Mock para chat completions
    mock_chat = MagicMock()
    mock_chat.completions = MagicMock()
    mock_chat.completions.create = AsyncMock()
    mock_chat.completions.create.return_value = MagicMock(
        id="chatcmpl-test",
        choices=[
            MagicMock(
                message=MagicMock(content="Test response", role="assistant"),
                finish_reason="stop",
                index=0,
            )
        ],
        usage=MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        model="gpt-4o",
        object="chat.completion",
    )
    mock_client.chat = mock_chat

    return mock_client


# ============================================================================
# Fixtures Discord & Bot
# ============================================================================


class MockCommandTree:
    """Mock de CommandTree que captura comandos registrados."""

    def __init__(self):
        self._commands = {}
        self._groups = {}

    def command(self, name=None, description=None):
        def decorator(func):
            cmd_name = name or func.__name__
            cmd = MagicMock()
            cmd.name = cmd_name
            cmd.callback = func
            cmd.description = description or ""
            self._commands[cmd_name] = cmd
            return func

        return decorator

    def get_command(self, name: str, guild=None):
        if " " in name:
            parts = name.split(" ", 1)
            group_name = parts[0]
            sub_cmd_name = parts[1]
            if group_name in self._groups:
                group = self._groups[group_name]
                if hasattr(group, "commands"):
                    if hasattr(group.commands, "values"):
                        return group.commands.get(sub_cmd_name)
                    else:
                        for cmd in group.commands:
                            if cmd.name == sub_cmd_name:
                                return cmd
        return self._commands.get(name)

    async def sync(self, guild=None):
        pass

    def add_command(self, command):
        if hasattr(command, "commands"):
            self._groups[command.name] = command
            cmds = (
                command.commands.values()
                if hasattr(command.commands, "values")
                else command.commands
            )
            for cmd in cmds:
                full_name = f"{command.name} {cmd.name}"
                self._commands[full_name] = cmd
        else:
            self._commands[command.name] = command


@pytest.fixture
async def bot_with_commands(mock_asyncpg_pool, monkeypatch):
    """Fixture para bot com comandos configurados e DB pool mockado."""
    from src.config.settings import reset_settings
    from src.discord.bot import AgnaldoBot
    from src.discord.commands import setup_commands

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token_123")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test_key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    reset_settings()

    mock_user = MagicMock()
    mock_user.mention = "@Agnaldo"
    mock_user.name = "Agnaldo"
    mock_user.id = 999888777

    mock_tree = MockCommandTree()
    mock_rate_limiter = MagicMock()
    mock_rate_limiter.acquire = AsyncMock()
    mock_rate_limiter.get_available_tokens = MagicMock(
        return_value={
            "global_tokens": 50.0,
            "channel_tokens": 5.0,
        }
    )

    bot = MagicMock(spec=AgnaldoBot)
    bot.db_pool = (
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
    )  # Retorna mock_conn
    # Wait, bot.db_pool should be the pool itself
    bot.db_pool = mock_asyncpg_pool
    bot.user = mock_user
    bot.guilds = []
    bot.latency = 0.05
    bot.tree = mock_tree
    bot.rate_limiter = mock_rate_limiter
    bot.get_rate_limiter = MagicMock(return_value=mock_rate_limiter)

    await setup_commands(bot)
    return bot, mock_asyncpg_pool, mock_asyncpg_pool.acquire.return_value.__aenter__.return_value


@pytest.fixture
def mock_discord_user() -> MagicMock:
    """Mock de User do Discord.

    Retorna um mock com atributos básicos de usuário Discord.

    Attributes:
        id: ID do usuário (snowflake)
        name: Nome do usuário
        discriminator: Discriminador (0000)
        global_name: Nome de exibição
        bot: Se é um bot
    """
    user = MagicMock()
    user.id = "123456789012345678"
    user.name = "TestUser"
    user.discriminator = "0000"
    user.global_name = "Test User"
    user.avatar = "avatar_hash"
    user.bot = False
    user.system = False
    user.public_flags = 0
    user.created_at = datetime.now(timezone.utc)
    user.mention = f"<@{user.id}>"
    return user


@pytest.fixture
def mock_discord_message(mock_discord_user: MagicMock) -> MagicMock:
    """Mock de Message do Discord.

    Retorna um mock com atributos básicos de mensagem Discord.
    Usa mock_discord_user como autor da mensagem.

    Attributes:
        id: ID da mensagem (snowflake)
        channel_id: ID do canal
        guild_id: ID do servidor (opcional)
        author: Autor da mensagem
        content: Conteúdo da mensagem
        embeds: Lista de embeds
        attachments: Lista de anexos
    """
    message = MagicMock()
    message.id = "111222333444555666"
    message.channel_id = "777888999000111222"
    message.guild = MagicMock(id="333444555666777888")
    message.guild_id = "333444555666777888"
    message.author = mock_discord_user
    message.content = "Test message content"
    message.embeds = []
    message.attachments = []
    message.reactions = []
    message.reference = None
    message.type = 0
    message.pinned = False
    message.tts = False
    message.mention_everyone = False
    message.edited_timestamp = None
    message.created_at = datetime.now(timezone.utc)
    message.jump_url = (
        f"https://discord.com/channels/{message.guild_id}/{message.channel_id}/{message.id}"
    )
    return message


@pytest.fixture
def mock_discord_guild() -> MagicMock:
    """Mock de Guild do Discord.

    Retorna um mock com atributos básicos de servidor Discord.

    Attributes:
        id: ID do servidor (snowflake)
        name: Nome do servidor
        owner_id: ID do dono
        member_count: Número de membros
        features: Lista de features
    """
    guild = MagicMock()
    guild.id = "333444555666777888"
    guild.name = "Test Server"
    guild.icon = "icon_hash"
    guild.description = "A test server"
    guild.owner_id = "123456789012345678"
    guild.region = "us-east"
    guild.afk_channel_id = None
    guild.afk_timeout = 300
    guild.verification_level = 0
    guild.default_message_notifications = 0
    guild.explicit_content_filter = 0
    guild.roles = []
    guild.emojis = []
    guild.features = []
    guild.mfa_level = 0
    guild.system_channel_id = None
    guild.premium_tier = 0
    guild.member_count = 100
    guild.created_at = datetime.now(timezone.utc)
    return guild


@pytest.fixture
def mock_discord_interaction(
    mock_discord_user: MagicMock, mock_discord_guild: MagicMock
) -> MagicMock:
    """Mock de Interaction do Discord.

    Retorna um mock com atributos básicos de interação Discord
    (usado em slash commands).

    Attributes:
        id: ID da interação
        type: Tipo da interação (1 = Ping, 2 = ApplicationCommand)
        data: Dados do comando
        user: Usuário que invocou
        guild: Servidor onde ocorreu
        channel: Canal onde ocorreu
    """
    interaction = MagicMock()
    interaction.id = "999888777666555444"
    interaction.type = 2  # ApplicationCommand
    interaction.token = "interaction_token"
    interaction.version = 1

    # Mock do comando
    interaction.data = MagicMock()
    interaction.data.name = "test"
    interaction.data.options = []

    # Contexto
    interaction.user = mock_discord_user
    interaction.guild_id = mock_discord_guild.id
    interaction.guild = mock_discord_guild
    interaction.channel_id = "777888999000111222"
    interaction.channel = MagicMock(id="777888999000111222", type=0)

    # Métodos de resposta
    interaction.response = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()

    # Métodos de followup
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    # Métodos de edição
    interaction.edit_original_response = AsyncMock()

    return interaction


# ============================================================================
# Fixtures de Dados de Teste
# ============================================================================


@pytest.fixture
def faker() -> Faker:
    """Instância do Faker para geração de dados de teste.

    Fornece métodos para gerar dados realistas como nomes,
    emails, textos, etc.

    Example:
        name = faker.name()
        email = faker.email()
        text = faker.paragraph()
    """
    return Faker()


@pytest.fixture
def mock_memory_item(faker: Faker) -> callable:
    """Factory para criar instâncias de CoreMemoryItem.

    Permite criar itens de memória com valores customizados
    ou usar defaults sensatos.

    Args:
        id: ID do item (default: UUID aleatório)
        content: Conteúdo da memória (default: texto Faker)
        importance: Score de importância 0-1 (default: 0.5)
        access_count: Número de acessos (default: 0)
        metadata: Metadados adicionais (default: {})

    Returns:
        Instância de CoreMemoryItem

    Example:
        item = mock_memory_item()  # Defaults
        custom = mock_memory_item(content="Custom", importance=0.9)
    """

    def _create(
        id: str | None = None,
        content: str | None = None,
        importance: float = 0.5,
        access_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> CoreMemoryItem:
        return CoreMemoryItem(
            id=id or str(uuid4()),
            content=content or faker.sentence(),
            importance=importance,
            access_count=access_count,
            last_accessed=None,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

    return _create


@pytest.fixture
def mock_graph_node(faker: Faker) -> callable:
    """Factory para criar instâncias de KnowledgeNode.

    Permite criar nós do grafo com valores customizados
    ou usar defaults sensatos.

    Args:
        id: ID do nó (default: UUID aleatório)
        label: Rótulo do nó (default: texto Faker)
        node_type: Tipo do nó (default: "concept")
        properties: Propriedades adicionais (default: {})
        embedding: Vetor de embedding (default: None)

    Returns:
        Instância de KnowledgeNode

    Example:
        node = mock_graph_node()  # Defaults
        custom = mock_graph_node(label="Python", node_type="language")
    """

    def _create(
        id: str | None = None,
        label: str | None = None,
        node_type: str | None = None,
        properties: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
    ) -> KnowledgeNode:
        return KnowledgeNode(
            id=id or str(uuid4()),
            label=label or faker.word(),
            node_type=node_type or "concept",
            properties=properties or {},
            embedding=embedding,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    return _create


@pytest.fixture
def mock_graph_edge(faker: Faker) -> callable:
    """Factory para criar instâncias de KnowledgeEdge.

    Permite criar arestas do grafo com valores customizados
    ou usar defaults sensatos.

    Args:
        id: ID da aresta (default: UUID aleatório)
        source_id: ID do nó de origem (default: UUID aleatório)
        target_id: ID do nó de destino (default: UUID aleatório)
        edge_type: Tipo da relação (default: "relates_to")
        weight: Peso da aresta (default: 1.0)
        properties: Propriedades adicionais (default: {})

    Returns:
        Instância de KnowledgeEdge

    Example:
        edge = mock_graph_edge()  # Defaults
        custom = mock_graph_edge(
            source_id="node-1",
            target_id="node-2",
            edge_type="depends_on",
            weight=0.8
        )
    """

    def _create(
        id: str | None = None,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: str = "relates_to",
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> KnowledgeEdge:
        return KnowledgeEdge(
            id=id or str(uuid4()),
            source_id=source_id or str(uuid4()),
            target_id=target_id or str(uuid4()),
            edge_type=edge_type,
            weight=weight,
            properties=properties or {},
            created_at=datetime.now(timezone.utc),
        )

    return _create


# ============================================================================
# Fixtures de Configuração
# ============================================================================


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock das configurações do aplicativo.

    Retorna um mock com valores padrão para testes,
    evitando a necessidade de variáveis de ambiente reais.

    Attributes:
        DISCORD_BOT_TOKEN: Token do bot Discord
        SUPABASE_URL: URL do Supabase
        OPENAI_API_KEY: Chave da API OpenAI
        ENVIRONMENT: Ambiente (dev/test)
        LOG_LEVEL: Nível de log
    """
    settings = MagicMock()
    settings.DISCORD_BOT_TOKEN = "test_bot_token"
    settings.SUPABASE_URL = "https://test.supabase.co"
    settings.SUPABASE_DB_URL = "postgresql://localhost:5432/test"
    settings.SUPABASE_SERVICE_ROLE_KEY = "test_service_role_key"
    settings.OPENAI_API_KEY = "test_openai_key"
    settings.ENVIRONMENT = "test"
    settings.LOG_LEVEL = "DEBUG"
    settings.OPENAI_CHAT_MODEL = "gpt-4o"
    settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
    settings.SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
    settings.CACHE_MAX_SIZE = 1000
    settings.CACHE_TTL = 300
    settings.RATE_LIMIT_GLOBAL = 50
    settings.RATE_LIMIT_PER_CHANNEL = 5
    return settings
