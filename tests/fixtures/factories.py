"""Test data factories para testes do Agnaldo.

Este módulo fornece factories para gerar dados de teste
usando Faker, facilitando a criação de dados realistas.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest
from faker import Faker

# Instância singleton do Faker com locale pt-BR
_fake = Faker("pt_BR")


def get_faker() -> Faker:
    """Retorna a instância do Faker.

    Returns:
        Instância do Faker configurada com locale pt-BR.
    """
    return _fake


def create_test_user(
    user_id: str | None = None,
    username: str | None = None,
    email: str | None = None,
    is_bot: bool = False,
) -> dict[str, Any]:
    """Factory para criar dados de usuário de teste.

    Args:
        user_id: ID do usuário (snowflake). Se None, gera um aleatório.
        username: Nome de usuário. Se None, gera um aleatório.
        email: Email do usuário. Se None, gera um aleatório.
        is_bot: Se é um bot.

    Returns:
        Dict com dados do usuário compatível com DiscordUser schema.
    """
    if user_id is None:
        user_id = str(_fake.random_int(min=100000000000000000, max=999999999999999999))

    if username is None:
        username = _fake.user_name()

    if email is None:
        email = _fake.email()

    return {
        "id": user_id,
        "username": username,
        "discriminator": f"{_fake.random_int(min=0, max=9999):04d}",
        "global_name": _fake.name(),
        "avatar_hash": _fake.hexify(text="^^^^^^^^^^^^^^^^", upper=True),
        "is_bot": is_bot,
        "is_system": False,
        "public_flags": 0,
        "created_at": _fake.date_time_this_decade(before_now=True, after_now=False).replace(
            tzinfo=timezone.utc
        ),
        "email": email,
    }


def create_test_memory_item(
    item_id: str | None = None,
    content: str | None = None,
    tier: str = "core",
    importance: float = 0.5,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Factory para criar item de memória de teste.

    Args:
        item_id: ID único do item. Se None, gera um UUID.
        content: Conteúdo da memória. Se None, gera texto aleatório.
        tier: Tipo de memória (core, recall, archival).
        importance: Score de importância (0.0 a 1.0).
        user_id: ID do usuário dono da memória.

    Returns:
        Dict com dados de memória compatível com schemas de memória.
    """
    if item_id is None:
        item_id = str(uuid4())

    if content is None:
        # Gera conteúdo mais realista baseado em contexto
        content = _fake.sentence()

    if user_id is None:
        user_id = str(_fake.random_int(min=100000000000000000, max=999999999999999999))

    base_item = {
        "id": item_id,
        "content": content,
        "created_at": _fake.date_time_this_year(before_now=True, after_now=False).replace(
            tzinfo=timezone.utc
        ),
        "metadata": {
            "user_id": user_id,
            "source": _fake.word(ext_word_list=["conversation", "manual", "import", "api"]),
        },
    }

    if tier == "core":
        return {
            **base_item,
            "importance": importance,
            "access_count": _fake.random_int(min=0, max=100),
            "last_accessed": _fake.date_time_this_month(before_now=True, after_now=False).replace(
                tzinfo=timezone.utc
            ),
        }
    elif tier == "recall":
        return {
            **base_item,
            "conversation_id": str(uuid4()),
            "message_id": str(uuid4()) if _fake.boolean() else None,
            "timestamp": _fake.date_time_this_year(before_now=True, after_now=False).replace(
                tzinfo=timezone.utc
            ),
            "embedding": None,  # Será preenchido pelo teste
            "relevance_score": _fake.pyfloat(min_value=0.0, max_value=1.0),
        }
    elif tier == "archival":
        return {
            **base_item,
            "tier": "archival",
            "compressed": _fake.boolean(),
            "storage_location": f"s3://agnaldo-archive/{_fake.date_this_year().isoformat()}/",
            "tags": _fake.words(nb=_fake.random_int(min=1, max=5)),
            "last_accessed": _fake.date_time_this_year(before_now=True, after_now=False).replace(
                tzinfo=timezone.utc
            )
            if _fake.boolean()
            else None,
        }
    else:
        raise ValueError(f"Tier inválido: {tier}. Use 'core', 'recall' ou 'archival'.")


def create_test_graph_node(
    node_id: str | None = None,
    label: str | None = None,
    node_type: str | None = None,
    embedding_dim: int = 1536,
) -> dict[str, Any]:
    """Factory para criar nó do grafo de conhecimento de teste.

    Args:
        node_id: ID UUID do nó. Se None, gera um UUID.
        label: Rótulo do nó. Se None, gera uma palavra/conceito aleatório.
        node_type: Tipo do nó. Se None, gera um tipo aleatório.
        embedding_dim: Dimensão do vetor de embedding.

    Returns:
        Dict com dados de nó compatível com KnowledgeNode.
    """
    if node_id is None:
        node_id = str(uuid4())

    if label is None:
        label = _fake.word()

    if node_type is None:
        node_type = _fake.word(
            ext_word_list=["concept", "entity", "topic", "category", "language", "framework"]
        )

    # Gera embedding mockado determinístico usando SHA-256
    seed_val = int(hashlib.sha256(label.encode()).hexdigest(), 16) % (2**32)
    _fake.seed_instance(seed_val)
    embedding = [_fake.pyfloat(min_value=-1, max_value=1) for _ in range(embedding_dim)]
    _fake.seed_instance(None)  # Reseta seed

    return {
        "id": node_id,
        "label": label,
        "node_type": node_type,
        "properties": {
            "description": _fake.sentence() if _fake.boolean() else None,
            "created_by": "test",
        },
        "embedding": embedding,
        "created_at": _fake.date_time_this_year(before_now=True, after_now=False).replace(
            tzinfo=timezone.utc
        ),
        "updated_at": _fake.date_time_this_month(before_now=True, after_now=False).replace(
            tzinfo=timezone.utc
        ),
    }


def create_test_graph_edge(
    edge_id: str | None = None,
    source_id: str | None = None,
    target_id: str | None = None,
    edge_type: str | None = None,
    weight: float = 1.0,
) -> dict[str, Any]:
    """Factory para criar aresta do grafo de conhecimento de teste.

    Args:
        edge_id: ID UUID da aresta. Se None, gera um UUID.
        source_id: ID do nó de origem. Se None, gera um UUID.
        target_id: ID do nó de destino. Se None, gera um UUID.
        edge_type: Tipo da relação. Se None, gera um tipo aleatório.
        weight: Peso da aresta (0.0 a 2.0).

    Returns:
        Dict com dados de aresta compatível com KnowledgeEdge.
    """
    if edge_id is None:
        edge_id = str(uuid4())

    if source_id is None:
        source_id = str(uuid4())

    if target_id is None:
        target_id = str(uuid4())

    if edge_type is None:
        edge_type = _fake.word(
            ext_word_list=[
                "relates_to",
                "part_of",
                "used_for",
                "similar_to",
                "depends_on",
                "precedes",
            ]
        )

    return {
        "id": edge_id,
        "source_id": source_id,
        "target_id": target_id,
        "edge_type": edge_type,
        "weight": weight,
        "properties": {
            "confidence": _fake.pyfloat(min_value=0.0, max_value=1.0),
            "created_by": "test",
        },
        "created_at": _fake.date_time_this_month(before_now=True, after_now=False).replace(
            tzinfo=timezone.utc
        ),
    }


def create_test_discord_message(
    message_id: str | None = None,
    content: str | None = None,
    user_id: str | None = None,
    channel_id: str | None = None,
    guild_id: str | None = None,
) -> dict[str, Any]:
    """Factory para criar mensagem Discord de teste.

    Args:
        message_id: ID da mensagem. Se None, gera um snowflake.
        content: Conteúdo da mensagem. Se None, gera texto.
        user_id: ID do autor. Se None, gera um snowflake.
        channel_id: ID do canal. Se None, gera um snowflake.
        guild_id: ID do servidor. Se None, gera um snowflake.

    Returns:
        Dict com dados de mensagem compatível com DiscordMessage schema.
    """
    if message_id is None:
        message_id = str(_fake.random_int(min=100000000000000000, max=999999999999999999))

    if content is None:
        content = _fake.sentence()

    if user_id is None:
        user_id = str(_fake.random_int(min=100000000000000000, max=999999999999999999))

    if channel_id is None:
        channel_id = str(_fake.random_int(min=100000000000000000, max=999999999999999999))

    if guild_id is None:
        guild_id = str(_fake.random_int(min=100000000000000000, max=999999999999999999))

    user_data = create_test_user(user_id=user_id)

    return {
        "id": message_id,
        "channel_id": channel_id,
        "guild_id": guild_id,
        "author": user_data,
        "content": content,
        "timestamp": _fake.date_time_this_year(before_now=True, after_now=False).replace(
            tzinfo=timezone.utc
        ),
        "edited_timestamp": _fake.date_time_this_year(before_now=True, after_now=False).replace(
            tzinfo=timezone.utc
        )
        if _fake.boolean()
        else None,
        "tts": False,
        "mention_everyone": False,
        "attachments": [],
        "embeds": [],
        "reactions": [],
        "pinned": False,
        "type": 0,
        "message_reference": None,
    }


def create_test_agent_message(
    sender: str = "orchestrator",
    receiver: str = "memory",
    message_type: str = "request",
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Factory para criar mensagem entre agentes de teste.

    Args:
        sender: ID do agente remetente.
        receiver: ID do agente destinatário.
        message_type: Tipo da mensagem (request, response, notification, error).
        content: Conteúdo da mensagem.

    Returns:
        Dict com dados de mensagem compatível com AgentMessage schema.
    """
    if content is None:
        content = {"action": _fake.word(), "params": {}}

    return {
        "id": str(uuid4()),
        "sender": sender,
        "receiver": receiver,
        "type": message_type,
        "content": content,
        "timestamp": _fake.date_time_this_year(before_now=True, after_now=False).replace(
            tzinfo=timezone.utc
        ),
        "metadata": {
            "priority": _fake.word(ext_word_list=["low", "normal", "high"]),
        },
    }


def create_test_memory_stats(
    core_count: int = 100,
    recall_count: int = 1000,
    archival_count: int = 5000,
) -> dict[str, Any]:
    """Factory para criar estatísticas de memória de teste.

    Args:
        core_count: Número de itens na memória core.
        recall_count: Número de itens na memória recall.
        archival_count: Número de itens na memória archival.

    Returns:
        Dict com estatísticas compatível com MemoryStats schema.
    """
    # Assumindo ~300 tokens por item em média
    core_tokens = core_count * 300
    recall_tokens = recall_count * 300
    archival_tokens = archival_count * 150  # Comprimido

    return {
        "core_count": core_count,
        "recall_count": recall_count,
        "archival_count": archival_count,
        "total_count": core_count + recall_count + archival_count,
        "core_tokens": core_tokens,
        "recall_tokens": recall_tokens,
        "archival_tokens": archival_tokens,
        "total_tokens": core_tokens + recall_tokens + archival_tokens,
        "last_updated": datetime.now(timezone.utc),
    }


def create_test_db_pool(
    fetchval_result: Any | None = None,
    fetchrow_result: dict | None = None,
    fetch_result: list[dict] | None = None,
    execute_result: str = "SELECT 1",
) -> Any:
    """Factory para criar mock de asyncpg Pool.

    Args:
        fetchval_result: Resultado padrão para fetchval.
        fetchrow_result: Resultado padrão para fetchrow.
        fetch_result: Resultado padrão para fetch.
        execute_result: Resultado padrão para execute.

    Returns:
        AsyncMock configurado como pool asyncpg.
    """
    from unittest.mock import AsyncMock

    mock_pool = AsyncMock()

    # Configurar connection mock
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=fetchval_result)
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    mock_conn.fetch = AsyncMock(return_value=fetch_result or [])
    mock_conn.execute = AsyncMock(return_value=execute_result)

    # Configurar acquire/release como context manager
    class MockAsyncContextManager:
        def __init__(self, return_value):
            self._return_value = return_value

        async def __aenter__(self):
            return self._return_value

        async def __aexit__(self, exc_type, exc, tb):
            pass

    mock_pool.acquire.return_value = MockAsyncContextManager(mock_conn)
    mock_pool.release = AsyncMock()
    mock_pool.close = AsyncMock()

    return mock_pool


# Fixtures pytest


@pytest.fixture
def fake():
    """Fixture que retorna a instância do Faker."""
    return get_faker()


@pytest.fixture
def test_user():
    """Fixture que retorna dados de usuário de teste."""
    return create_test_user()


@pytest.fixture
def test_memory_item():
    """Fixture que retorna item de memória de teste."""
    return create_test_memory_item()


@pytest.fixture
def test_graph_node():
    """Fixture que retorna nó de grafo de teste."""
    return create_test_graph_node()


@pytest.fixture
def test_graph_edge():
    """Fixture que retorna aresta de grafo de teste."""
    return create_test_graph_edge()


@pytest.fixture
def test_discord_message():
    """Fixture que retorna mensagem Discord de teste."""
    return create_test_discord_message()


@pytest.fixture
def test_agent_message():
    """Fixture que retorna mensagem entre agentes de teste."""
    return create_test_agent_message()


@pytest.fixture
def test_memory_stats():
    """Fixture que retorna estatísticas de memória de teste."""
    return create_test_memory_stats()


@pytest.fixture
def test_db_pool():
    """Fixture que retorna mock de pool asyncpg."""
    return create_test_db_pool()
