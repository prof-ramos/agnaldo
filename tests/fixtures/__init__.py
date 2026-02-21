"""Fixtures compartilhadas para testes do Agnaldo Bot.

Este módulo fornece mocks, factories e fixtures pytest para facilitar
a escrita de testes isolados e reproduzíveis.

Módulos:
    discord: Mocks das classes do discord.py (User, Message, Interaction, etc)
    openai: Mocks do cliente OpenAI (embeddings, chat completions)
    factories: Factories usando Faker para gerar dados de teste

Exemplo de uso:

    from tests.fixtures.discord import create_mock_user, create_mock_interaction
    from tests.fixtures.openai import create_mock_openai_client
    from tests.fixtures.factories import create_test_memory_item

    # Criar mocks
    user = create_mock_user(username="TestUser")
    interaction = create_mock_interaction(user=user)

    # Criar dados de teste
    memory = create_test_memory_item(tier="core", importance=0.8)
"""

# Exporta funções mais comuns para facilitar imports
from tests.fixtures.discord import (
    create_mock_bot,
    create_mock_channel,
    create_mock_guild,
    create_mock_interaction,
    create_mock_message,
    create_mock_rate_limiter,
    create_mock_user,
)
from tests.fixtures.factories import (
    create_test_agent_message,
    create_test_db_pool,
    create_test_discord_message,
    create_test_graph_edge,
    create_test_graph_node,
    create_test_memory_item,
    create_test_memory_stats,
    create_test_user,
    get_faker,
)
from tests.fixtures.openai import (
    create_mock_chat_completion,
    create_mock_embedding,
    create_mock_openai_client,
)

__all__ = [
    # Discord mocks
    "create_mock_user",
    "create_mock_message",
    "create_mock_interaction",
    "create_mock_guild",
    "create_mock_channel",
    "create_mock_bot",
    "create_mock_rate_limiter",
    # OpenAI mocks
    "create_mock_openai_client",
    "create_mock_embedding",
    "create_mock_chat_completion",
    # Factories
    "get_faker",
    "create_test_user",
    "create_test_memory_item",
    "create_test_graph_node",
    "create_test_graph_edge",
    "create_test_discord_message",
    "create_test_agent_message",
    "create_test_memory_stats",
    "create_test_db_pool",
]
