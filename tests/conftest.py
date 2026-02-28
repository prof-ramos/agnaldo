"""Fixtures base para testes do Agnaldo.

Este módulo contém fixtures reutilizáveis para todos os testes.
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.base.logging import setup_logging


# Configurar logging para testes
setup_logging(level="DEBUG", json_output=False)


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
