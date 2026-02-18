"""Testes end-to-end para comandos Discord do Agnaldo Bot.

Estes testes simulam fluxos completos de interação com comandos slash,
desde a chamada do comando até a resposta ao usuário, usando todos os
mocks necessários (Discord, OpenAI, DB).
"""

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# Testes E2E de Comandos de Memória
# ============================================================================


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_memory_add_command_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do fluxo de adicionar memória via comando /memory add."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mocks do banco para a operação de add
    mock_conn.fetch.return_value = []  # Nenhuma memória existente com essa chave
    mock_conn.fetchval.return_value = "mock-uuid-1234"

    # Obter o comando de adicionar memória
    memory_add_cmd = bot.tree.get_command("memory add")
    assert memory_add_cmd is not None

    # Executar o comando
    await memory_add_cmd.callback(
        mock_discord_interaction, key="linguagem_preferida", value="Python", importance=0.8
    )

    # Verificar que a resposta foi enviada
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "linguagem_preferida" in call_args[0][0]
    assert "Python" in call_args[0][0]
    assert "0.8" in call_args[0][0]


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_memory_add_invalid_importance_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do fluxo de adicionar memória com importância inválida."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Obter o comando de adicionar memória
    memory_add_cmd = bot.tree.get_command("memory add")

    # Executar com importância inválida
    await memory_add_cmd.callback(
        mock_discord_interaction,
        key="teste",
        value="valor",
        importance=1.5,  # Inválido (> 1.0)
    )

    # Verificar mensagem de erro
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "Importance must be between 0.0 and 1.0" in call_args[0][0]


@pytest.mark.e2e
@pytest.mark.discord
@patch("src.memory.recall.AsyncOpenAI")
@patch("src.knowledge.graph.AsyncOpenAI")
async def test_memory_search_command_flow(
    mock_openai_graph, mock_openai_recall, bot_with_commands, mock_discord_interaction
):
    """Teste E2E do fluxo de buscar memória via comando /memory recall."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mocks para busca semântica
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    mock_conn.fetch.return_value = [
        {
            "id": "mem-uuid-1",
            "content": "O usuário prefere programar em Python",
            "importance": 0.9,
            "similarity": 0.92,
            "created_at": now,
            "updated_at": now,
            "access_count": 0,
        },
        {
            "id": "mem-uuid-2",
            "content": "Python é a linguagem favorita",
            "importance": 0.8,
            "similarity": 0.85,
            "created_at": now,
            "updated_at": now,
            "access_count": 0,
        },
    ]

    # Mock OpenAI para evitar chamadas reais de API
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock(embedding=[0.1] * 1536)]

    # Configurar o mock que já foi injetado pelo decorator @patch
    mock_client = mock_openai_recall.return_value
    mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    # Obter o comando de recall
    memory_recall_cmd = bot.tree.get_command("memory recall")
    assert memory_recall_cmd is not None

    # Executar o comando
    await memory_recall_cmd.callback(
        mock_discord_interaction, query="linguagem de programação", limit=5
    )

    # Verificar resposta
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    response_text = call_args[0][0]
    assert "Found 2 memories" in response_text or "memories" in response_text.lower()
    assert "92%" in response_text or "85%" in response_text


@pytest.mark.e2e
@pytest.mark.discord
@patch("src.memory.recall.AsyncOpenAI")
@patch("src.knowledge.graph.AsyncOpenAI")
async def test_memory_search_empty_results_flow(
    mock_openai_graph, mock_openai_recall, bot_with_commands, mock_discord_interaction
):
    """Teste E2E do fluxo de busca sem resultados."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mock para não retornar resultados
    mock_conn.fetch.return_value = []

    # Mock OpenAI para evitar chamadas reais de API
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock(embedding=[0.1] * 1536)]

    # Configurar o mock injetado
    mock_client = mock_openai_recall.return_value
    mock_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    # Obter o comando de recall
    memory_recall_cmd = bot.tree.get_command("memory recall")

    # Executar o comando
    await memory_recall_cmd.callback(mock_discord_interaction, query="algo que não existe", limit=5)

    # Verificar mensagem de "não encontrado"
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "No memories found" in call_args[0][0]


# ============================================================================
# Testes E2E de Comandos de Grafo
# ============================================================================


@pytest.mark.e2e
@pytest.mark.discord
@patch("src.memory.recall.AsyncOpenAI")
@patch("src.knowledge.graph.AsyncOpenAI")
async def test_graph_add_node_command_flow(
    mock_openai_graph, mock_openai_recall, bot_with_commands, mock_discord_interaction
):
    """Teste E2E do fluxo de adicionar nó ao grafo via /graph add_node."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mocks
    mock_conn.fetchval.return_value = "node-uuid-123"
    mock_conn.fetchrow.return_value = {
        "id": "node-uuid-123",
        "label": "Python",
        "node_type": "language",
        "properties": {},
        "embedding": None,
        "created_at": None,
        "updated_at": None,
    }

    # Obter o comando
    graph_add_node_cmd = bot.tree.get_command("graph add_node")
    assert graph_add_node_cmd is not None

    # Configurar mock OpenAI recall e graph
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock(embedding=[0.1] * 1536)]

    mock_recall_client = mock_openai_recall.return_value
    mock_recall_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    mock_graph_client = mock_openai_graph.return_value
    mock_graph_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    # Configurar mocks para o nó criado
    mock_conn.fetchval.return_value = "node-uuid-123"
    mock_conn.fetchrow.return_value = {
        "id": "node-uuid-123",
        "label": "Python",
        "node_type": "language",
        "properties": {},
        "embedding": [0.1] * 1536,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    # Executar o comando
    await graph_add_node_cmd.callback(
        mock_discord_interaction, label="Python", node_type="language"
    )

    # Verificar resposta
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "Python" in call_args[0][0]
    assert "language" in call_args[0][0]


@pytest.mark.e2e
@pytest.mark.discord
@patch("src.memory.recall.AsyncOpenAI")
@patch("src.knowledge.graph.AsyncOpenAI")
async def test_graph_add_edge_command_flow(
    mock_openai_graph, mock_openai_recall, bot_with_commands, mock_discord_interaction
):
    """Teste E2E do fluxo de adicionar aresta ao grafo via /graph add_edge."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mocks para busca de nós (não encontra) -> criação de nós -> criação de aresta
    mock_conn.fetch.return_value = []  # search_nodes não encontra nada inicialmente
    mock_conn.fetchval.return_value = "uuid-gerado"

    # Criar resultados para as chamadas consecutivas de fetchrow:
    # 1. add_node(source)
    # 2. add_node(target)
    # 3. add_edge(source, target)
    now = datetime.now(timezone.utc)
    res_source = {
        "id": "node-source-123",
        "label": "Python",
        "node_type": "language",
        "properties": {},
        "embedding": [0.1] * 1536,
        "created_at": now,
        "updated_at": now,
    }
    res_target = {
        "id": "node-target-789",
        "label": "Discord API",
        "node_type": "library",
        "properties": {},
        "embedding": [0.1] * 1536,
        "created_at": now,
        "updated_at": now,
    }
    res_edge = {
        "id": "edge-uuid-456",
        "source_id": "node-source-123",
        "target_id": "node-target-789",
        "edge_type": "é_usado_em",
        "weight": 1.0,
        "properties": {},
        "created_at": now,
    }

    mock_conn.fetchrow.side_effect = [res_source, res_target, res_edge]

    # Configurar mock OpenAI recall e graph
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock(embedding=[0.1] * 1536)]

    mock_recall_client = mock_openai_recall.return_value
    mock_recall_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    mock_graph_client = mock_openai_graph.return_value
    mock_graph_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    # Obter o comando
    graph_add_edge_cmd = bot.tree.get_command("graph add_edge")
    assert graph_add_edge_cmd is not None

    # Executar o comando
    await graph_add_edge_cmd.callback(
        mock_discord_interaction,
        source="Python",
        target="Discord",
        edge_type="used_for",
        weight=1.0,
    )

    # Verificar resposta
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    response_text = call_args[0][0]
    assert "Python" in response_text
    assert "Discord" in response_text
    assert "used_for" in response_text


@pytest.mark.e2e
@pytest.mark.discord
@patch("src.memory.recall.AsyncOpenAI")
@patch("src.knowledge.graph.AsyncOpenAI")
async def test_graph_query_command_flow(
    mock_openai_graph, mock_openai_recall, bot_with_commands, mock_discord_interaction
):
    """Teste E2E do fluxo de query no grafo via /graph query."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mocks para busca de nós
    mock_conn.fetch.return_value = [
        {
            "id": "node-uuid-1",
            "label": "Python Programming",
            "node_type": "language",
            "properties": {},
            "similarity": 0.88,
            "created_at": None,
        },
        {
            "id": "node-uuid-2",
            "label": "Discord.py",
            "node_type": "library",
            "properties": {},
            "similarity": 0.75,
            "created_at": None,
        },
    ]

    # Mock para get_neighbors
    mock_conn.fetchrow.return_value = {
        "id": "neighbor-1",
        "label": "AsyncIO",
        "node_type": "concept",
        "properties": {},
    }

    # Obter o comando
    graph_query_cmd = bot.tree.get_command("graph query")
    assert graph_query_cmd is not None

    # Configurar mock OpenAI recall e graph
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock(embedding=[0.1] * 1536)]

    mock_recall_client = mock_openai_recall.return_value
    mock_recall_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    mock_graph_client = mock_openai_graph.return_value
    mock_graph_client.embeddings.create = AsyncMock(return_value=mock_openai_response)

    # Executar o comando
    await graph_query_cmd.callback(
        mock_discord_interaction, query="bibliotecas para bots discord", limit=5
    )

    # Verificar resposta
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    response_text = call_args[0][0]
    assert "nodes" in response_text.lower() or "Python Programming" in response_text


# ============================================================================
# Testes E2E de Comandos Gerais
# ============================================================================


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_help_command_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do fluxo do comando /help."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Obter o comando help
    help_cmd = bot.tree.get_command("help")
    assert help_cmd is not None

    # Executar o comando
    await help_cmd.callback(mock_discord_interaction)

    # Verificar resposta
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    response_text = call_args[0][0]
    assert "Agnaldo Bot Commands" in response_text
    assert "/ping" in response_text
    assert "/help" in response_text
    assert "/status" in response_text


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_ping_command_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do fluxo do comando /ping."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Obter o comando ping
    ping_cmd = bot.tree.get_command("ping")
    assert ping_cmd is not None

    # Executar o comando
    await ping_cmd.callback(mock_discord_interaction)

    # Verificar defer e followup (ping usa defer + followup)
    mock_discord_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_discord_interaction.followup.send.assert_called_once()
    call_args = mock_discord_interaction.followup.send.call_args

    assert "Pong!" in call_args[0][0]
    assert re.search(r"\d+ms", call_args[0][0])  # Verifica latência via regex


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_status_command_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do fluxo do comando /status."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Obter o comando status
    status_cmd = bot.tree.get_command("status")
    assert status_cmd is not None

    # Executar o comando
    await status_cmd.callback(mock_discord_interaction)

    # Verificar resposta
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    response_text = call_args[0][0]
    assert "Agnaldo Bot Status" in response_text
    assert "@Agnaldo" in response_text
    assert "Rate Limit Status" in response_text


# ============================================================================
# Testes E2E de Múltiplos Comandos em Sessão
# ============================================================================


@pytest.mark.e2e
@pytest.mark.discord
@patch("src.memory.recall.AsyncOpenAI")
@patch("src.knowledge.graph.AsyncOpenAI")
async def test_multi_command_session(mock_openai_graph, mock_openai_recall, bot_with_commands):
    """Teste E2E de múltiplos comandos em sequência simulando uma sessão."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mock OpenAI recall e graph para a sessão
    mock_openai_response = MagicMock()
    mock_openai_response.data = [MagicMock(embedding=[0.1] * 1536)]
    mock_client_recall = mock_openai_recall.return_value
    mock_client_recall.embeddings.create = AsyncMock(return_value=mock_openai_response)
    mock_client_graph = mock_openai_graph.return_value
    mock_client_graph.embeddings.create = AsyncMock(return_value=mock_openai_response)

    # Comando 1: Adicionar memória
    interaction1 = MagicMock()
    interaction1.response.is_done.return_value = False
    interaction1.response.send_message = AsyncMock()
    interaction1.user.id = 123456789
    interaction1.channel_id = 987654321

    mock_conn.fetch.return_value = []
    mock_conn.fetchval.return_value = "uuid-1"

    memory_add_cmd = bot.tree.get_command("memory add")
    await memory_add_cmd.callback(interaction1, key="projeto", value="Agnaldo Bot", importance=0.9)

    # Verificar primeiro comando
    interaction1.response.send_message.assert_called_once()
    assert "projeto" in interaction1.response.send_message.call_args[0][0]

    # Reset mocks para próximo comando
    mock_conn.reset_mock()

    # Comando 2: Adicionar nó ao grafo
    interaction2 = MagicMock()
    interaction2.response.is_done.return_value = False
    interaction2.response.send_message = AsyncMock()
    interaction2.user.id = 123456789
    interaction2.channel_id = 987654321

    mock_conn.fetchval.return_value = "node-uuid-1"
    mock_conn.fetchrow.return_value = {
        "id": "node-uuid-1",
        "label": "Python",
        "node_type": "language",
        "properties": {},
        "embedding": [0.1] * 1536,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    graph_add_node_cmd = bot.tree.get_command("graph add_node")
    await graph_add_node_cmd.callback(interaction2, label="Python", node_type="language")

    # Verificar segundo comando
    interaction2.response.send_message.assert_called_once()
    assert "Python" in interaction2.response.send_message.call_args[0][0]

    # Reset mocks para próximo comando
    mock_conn.reset_mock()

    # Comando 3: Buscar memória
    interaction3 = MagicMock()
    interaction3.response.is_done.return_value = False
    interaction3.response.send_message = AsyncMock()
    interaction3.user.id = 123456789
    interaction3.channel_id = 987654321

    now = datetime.now(timezone.utc)
    mock_conn.fetch.return_value = [
        {
            "id": "uuid-1",
            "content": "Agnaldo Bot",
            "importance": 0.9,
            "similarity": 0.95,
            "created_at": now,
            "updated_at": now,
            "access_count": 0,
        }
    ]

    memory_recall_cmd = bot.tree.get_command("memory recall")
    await memory_recall_cmd.callback(interaction3, query="nome do projeto", limit=5)

    # Verificar terceiro comando
    interaction3.response.send_message.assert_called_once()
    assert "memories" in interaction3.response.send_message.call_args[0][0].lower()


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_command_without_database_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do comportamento quando banco de dados não está disponível."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Remover o pool do bot (simular DB não disponível)
    bot.db_pool = None

    # Tentar adicionar memória
    memory_add_cmd = bot.tree.get_command("memory add")
    await memory_add_cmd.callback(
        mock_discord_interaction, key="teste", value="valor", importance=0.5
    )

    # Verificar mensagem de erro
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "Database not available" in call_args[0][0]


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_command_with_database_error_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do comportamento quando ocorre erro no banco de dados."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mock para lançar exceção
    mock_conn.fetch.side_effect = Exception("Database connection lost")

    # Tentar buscar memória
    memory_recall_cmd = bot.tree.get_command("memory recall")
    await memory_recall_cmd.callback(mock_discord_interaction, query="teste", limit=5)

    # Verificar mensagem de erro
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert (
        "Failed to search memories" in call_args[0][0]
        or "Database connection lost" in call_args[0][0]
    )


# ============================================================================
# Testes E2E de Rate Limiting
# ============================================================================


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_rate_limiting_on_commands(bot_with_commands):
    """Teste E2E de que rate limiter é aplicado aos comandos."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Criar múltiplas interações no mesmo canal
    interactions = []
    for i in range(3):
        interaction = MagicMock()
        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()
        interaction.user.id = 123456789
        interaction.channel_id = 987654321  # Mesmo canal
        interactions.append(interaction)

    # Configurar mocks
    mock_conn.fetch.return_value = []
    mock_conn.fetchval.return_value = f"uuid-{i}"

    # Executar comandos sequencialmente
    memory_add_cmd = bot.tree.get_command("memory add")

    for i, interaction in enumerate(interactions):
        await memory_add_cmd.callback(
            interaction, key=f"key_{i}", value=f"value_{i}", importance=0.5
        )

    # Verificar que todos foram processados (rate limiter permite)
    for interaction in interactions:
        interaction.response.send_message.assert_called_once()


# ============================================================================
# Testes E2E de Comandos Admin
# ============================================================================


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_sync_command_admin_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do comando /sync com permissões de admin."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar usuário como admin
    mock_discord_interaction.user.guild_permissions.administrator = True

    # Obter o comando sync
    sync_cmd = bot.tree.get_command("sync")
    assert sync_cmd is not None

    # Executar o comando
    await sync_cmd.callback(mock_discord_interaction)

    # Verificar resposta de sucesso
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "synced" in call_args[0][0].lower()


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_sync_command_non_admin_flow(bot_with_commands, mock_discord_interaction):
    """Teste E2E do comando /sync sem permissões de admin."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar usuário sem permissões de admin
    mock_discord_interaction.user.guild_permissions = None

    # Obter o comando sync
    sync_cmd = bot.tree.get_command("sync")

    # Executar o comando
    await sync_cmd.callback(mock_discord_interaction)

    # Verificar resposta de permissão negada
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "administrator permissions" in call_args[0][0].lower()
