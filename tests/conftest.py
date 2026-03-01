"""Fixtures base para testes do Agnaldo.

Este módulo contém fixtures reutilizáveis para todos os testes.
"""

import asyncio
from collections.abc import Awaitable, Callable, Generator
from typing import Any, NamedTuple
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.base.logging import setup_logging
from src.discord.commands import setup_commands

pytest_plugins = ["tests.fixtures.discord"]


# Configurar logging para testes
setup_logging(level="DEBUG", json_output=False)


class BotTestContext(NamedTuple):
    """Contexto de teste para bot com comandos configurados.

    Attributes:
        bot: Instância do bot mockado.
        pool: Pool de banco de dados mockado.
        conn: Conexão de banco de dados mockada.
    """

    bot: MagicMock
    pool: MagicMock
    conn: AsyncMock


class MockCommandTree:
    """Minimal command tree for slash-command E2E tests."""

    def __init__(self) -> None:
        self._commands: dict[str, Any] = {}

    def command(
        self,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable[[Any], Any]:
        """Decorator that captures root slash commands."""

        def decorator(func: Any) -> Any:
            cmd_name = name or func.__name__
            command = MagicMock()
            command.name = cmd_name
            command.qualified_name = cmd_name
            command.description = description or ""
            command.callback = func
            self._commands[cmd_name] = command
            return func

        return decorator

    async def sync(self, guild: Any = None) -> list[Any]:
        """Mock tree sync."""
        return list(self._commands.values())

    def add_command(self, command):
        """Capture command groups and their subcommands."""
        group_commands = getattr(command, "commands", None)
        if group_commands is None:
            command_name = getattr(command, "qualified_name", None) or getattr(command, "name", None)
            if command_name:
                self._commands[command_name] = command
            return

        commands = group_commands.values() if hasattr(group_commands, "values") else group_commands
        for cmd in commands:
            cmd_name = getattr(cmd, "name", None)
            qualified_name = getattr(cmd, "qualified_name", None)
            if cmd_name:
                self._commands[cmd_name] = cmd
            if qualified_name:
                self._commands[qualified_name] = cmd

    def get_command(self, name: str, guild=None):
        """Return command by name or qualified name."""
        return self._commands.get(name)


@pytest_asyncio.fixture
async def bot_with_commands(monkeypatch) -> BotTestContext:
    """Build a bot-like object with all slash commands registered.

    Returns:
        BotTestContext com bot, pool e conn mockados.
    """
    # Required settings for the settings singleton
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token_123")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test_key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    from src.config.settings import reset_settings

    reset_settings()

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchval = AsyncMock(return_value="mock-uuid")
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock(return_value="INSERT 1")

    transaction_cm = AsyncMock()
    transaction_cm.__aenter__.return_value = None
    transaction_cm.__aexit__.return_value = None
    mock_conn.transaction = MagicMock(return_value=transaction_cm)

    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=acquire_cm)

    rate_limiter = MagicMock()
    rate_limiter.acquire = AsyncMock()
    rate_limiter.get_available_tokens = MagicMock(
        return_value={
            "global_tokens": 50.0,
            "channel_tokens": 5.0,
        }
    )

    bot = MagicMock()
    bot.tree = MockCommandTree()
    bot.db_pool = mock_pool
    bot.user = MagicMock()
    bot.user.mention = "@Agnaldo"
    bot.user.name = "Agnaldo"
    bot.guilds = []
    bot.latency = 0.05
    bot.get_rate_limiter = MagicMock(return_value=rate_limiter)

    await setup_commands(bot)

    return BotTestContext(bot=bot, pool=mock_pool, conn=mock_conn)


# ============================================================================
# Event Loop
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Fixture do event loop para testes assíncronos."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mocks de Banco de Dados
# ============================================================================


@pytest.fixture
def mock_db_pool() -> AsyncMock:
    """Mock do pool de conexão do banco de dados.

    Returns:
        AsyncMock com interface de asyncpg.Pool.
    """
    pool = AsyncMock()

    # Mock do context manager acquire()
    conn = AsyncMock()

    # Configurar métodos comuns
    conn.fetchval = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value="UPDATE 1")

    # Configurar transaction
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=transaction)

    # Configurar acquire context manager
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=acquire_cm)

    return pool


@pytest.fixture
def mock_db_connection() -> AsyncMock:
    """Mock de conexão individual do banco de dados."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value="UPDATE 1")

    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=transaction)

    return conn


# ============================================================================
# Mocks de OpenAI
# ============================================================================


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    """Mock do cliente OpenAI.

    Returns:
        AsyncMock com interface de AsyncOpenAI.
    """
    client = AsyncMock()

    # Mock de embeddings
    embedding_response = MagicMock()
    embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
    client.embeddings.create = AsyncMock(return_value=embedding_response)

    # Mock de chat completions
    chat_response = MagicMock()
    chat_response.choices = [
        MagicMock(message=MagicMock(content="Mocked response"))
    ]
    chat_response.usage = MagicMock(total_tokens=100)
    client.chat.completions.create = AsyncMock(return_value=chat_response)

    return client


# ============================================================================
# Fixtures de Usuário
# ============================================================================


@pytest.fixture
def sample_user_id() -> str:
    """ID de usuário para testes."""
    return "test_user_123"


@pytest.fixture
def sample_session_id() -> str:
    """ID de sessão para testes."""
    return "test_session_456"


# ============================================================================
# Fixtures de Contexto
# ============================================================================


@pytest.fixture
def sample_discord_context() -> dict:
    """Contexto de Discord para testes."""
    return {
        "user_id": "discord_user_123",
        "username": "TestUser",
        "channel_id": "channel_456",
        "guild_id": "guild_789",
        "guild_name": "Test Server",
    }


# ============================================================================
# Fixtures de Memória
# ============================================================================


@pytest.fixture
def sample_core_memory() -> dict:
    """Dados de memória core para testes."""
    return {
        "name": "João",
        "interest": "Direito Constitucional",
        "level": "iniciante",
    }


@pytest.fixture
def sample_recall_memory() -> list[dict]:
    """Dados de memória recall para testes."""
    return [
        {
            "memory_id": "mem_1",
            "content": "User perguntou sobre direitos fundamentais",
            "similarity": 0.95,
            "created_at": "2026-02-28T10:00:00Z",
        },
        {
            "memory_id": "mem_2",
            "content": "Assistant explicou Art. 5º da Constituição",
            "similarity": 0.89,
            "created_at": "2026-02-28T10:05:00Z",
        },
    ]


# ============================================================================
# Fixtures de Graph
# ============================================================================


@pytest.fixture
def sample_graph_nodes() -> list[dict]:
    """Nós do grafo para testes."""
    return [
        {"id": "node_1", "label": "Direito Constitucional", "node_type": "concept"},
        {"id": "node_2", "label": "Art. 5º", "node_type": "law"},
        {"id": "node_3", "label": "João", "node_type": "person"},
    ]


@pytest.fixture
def sample_graph_edges() -> list[dict]:
    """Arestas do grafo para testes."""
    return [
        {"source": "node_3", "target": "node_1", "edge_type": "studies"},
        {"source": "node_2", "target": "node_1", "edge_type": "part_of"},
    ]


# ============================================================================
# Fixtures de Intent
# ============================================================================


@pytest.fixture
def sample_intent_result() -> dict:
    """Resultado de classificação de intent para testes."""
    return {
        "intent": "KNOWLEDGE_QUERY",
        "confidence": 0.92,
        "entities": {"topic": "direitos fundamentais"},
    }


# ============================================================================
# Fixtures de Ambiente
# ============================================================================


@pytest.fixture(autouse=True)
def reset_isolation_guard():
    """Reseta o guarda de isolamento entre testes."""
    from src.memory.isolation import get_isolation_guard

    guard = get_isolation_guard()
    guard.clear_audit_logs()

    yield

    guard.clear_audit_logs()


@pytest.fixture(autouse=True)
def reset_memoize_caches():
    """Limpa caches de memoize entre testes."""
    from src.base.decorators import _memoize_caches

    _memoize_caches.clear()

    yield

    _memoize_caches.clear()


# ============================================================================
# Marcadores Customizados
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configura marcadores customizados."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "requires_db: marks tests that need database")
    config.addinivalue_line("markers", "requires_openai: marks tests that need OpenAI API")
