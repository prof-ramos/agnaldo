"""Testes end-to-end para comandos Discord do Agnaldo Bot.

Estes testes simulam fluxos completos de interação com comandos slash,
desde a chamada do comando até a resposta ao usuário, usando todos os
mocks necessários (Discord, OpenAI, DB).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.discord.bot import AgnaldoBot
from src.discord.commands import setup_commands


# ============================================================================
# Fixtures E2E Específicas
# ============================================================================


def _build_mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """Build a mock asyncpg pool with an async context manager for acquire()."""
    mock_pool = MagicMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm
    return mock_pool


@pytest.fixture
def mock_db_pool():
    """Fixture para mock do pool de banco de dados."""
    mock_conn = AsyncMock()
    mock_pool = _build_mock_pool(mock_conn)
    return mock_pool, mock_conn


@pytest.fixture
def mock_openai_client():
    """Fixture para mock do cliente OpenAI."""
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock()
    mock_client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )
    return mock_client


@pytest.fixture
def mock_discord_interaction():
    """Fixture para mock de interação Discord completa."""
    interaction = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.user.id = 123456789
    interaction.user.name = "TestUser"
    interaction.channel_id = 987654321
    interaction.guild.id = 111222333
    return interaction


class MockCommandTree:
    """Mock de CommandTree que captura comandos registrados."""

    def __init__(self):
        self._commands = {}

    def command(self, name=None, description=None):
        """Decorator que captura comandos registrados."""
        def decorator(func):
            cmd_name = name or func.__name__
            # Criar mock de comando com callback
            cmd = MagicMock()
            cmd.name = cmd_name
            cmd.callback = func
            cmd.description = description or ""
            self._commands[cmd_name] = cmd
            return func  # Retorna a função original para o decorator funcionar
        return decorator

    def get_command(self, name: str, guild=None):
        """Retorna comando registrado pelo nome."""
        return self._commands.get(name)

    async def sync(self, guild=None):
        """Mock de sync."""
        pass

    def add_command(self, command):
        """Mock de add_command para grupos de comandos."""
        # Para grupos, precisamos extrair comandos aninhados
        if hasattr(command, "commands"):
            # commands pode ser uma lista ou dict
            cmds = command.commands.values() if hasattr(command.commands, "values") else command.commands
            for cmd in cmds:
                self._commands[cmd.name] = cmd
        else:
            self._commands[command.name] = command


@pytest.fixture
async def bot_with_commands(mock_db_pool, monkeypatch):
    """Fixture para bot com comandos configurados e DB pool mockado."""
    # Mock variáveis de ambiente obrigatórias
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token_123")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test_key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    # Limpar cache de settings global para usar novas variáveis
    from src.config.settings import _settings
    if _settings is not None:
        import importlib
        import src.config.settings
        importlib.reload(src.config.settings)

    mock_pool, mock_conn = mock_db_pool

    # Criar mocks para propriedades herdadas
    mock_user = MagicMock()
    mock_user.mention = "@Agnaldo"
    mock_user.name = "Agnaldo"
    mock_user.id = 999888777

    mock_tree = MockCommandTree()

    # Criar bot mockado manualmente para evitar propriedades read-only
    bot = MagicMock(spec=AgnaldoBot)
    bot.db_pool = mock_pool
    bot.user = mock_user
    bot.guilds = []
    bot.latency = 0.05
    bot.tree = mock_tree
    bot.rate_limiter = MagicMock()
    bot.rate_limiter.acquire = AsyncMock()
    bot.rate_limiter.get_available_tokens = MagicMock(return_value={
        "global_tokens": 50.0,
        "channel_tokens": 5.0,
    })

    # Setup comandos no bot mockado
    await setup_commands(bot)

    return bot, mock_pool, mock_conn


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
        memory_add_cmd,
        mock_discord_interaction,
        key="linguagem_preferida",
        value="Python",
        importance=0.8
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
        memory_add_cmd,
        mock_discord_interaction,
        key="teste",
        value="valor",
        importance=1.5  # Inválido (> 1.0)
    )

    # Verificar mensagem de erro
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "Importance must be between 0.0 and 1.0" in call_args[0][0]


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_memory_search_command_flow(bot_with_commands, mock_discord_interaction, mock_openai_client):
    """Teste E2E do fluxo de buscar memória via comando /memory recall."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mocks para busca semântica
    mock_conn.fetch.return_value = [
        {
            "id": "mem-uuid-1",
            "content": "O usuário prefere programar em Python",
            "similarity": 0.92,
        },
        {
            "id": "mem-uuid-2",
            "content": "Python é a linguagem favorita",
            "similarity": 0.85,
        },
    ]

    # Obter o comando de recall
    memory_recall_cmd = bot.tree.get_command("memory recall")
    assert memory_recall_cmd is not None

    # Executar o comando
    await memory_recall_cmd.callback(
        memory_recall_cmd,
        mock_discord_interaction,
        query="linguagem de programação",
        limit=5
    )

    # Verificar resposta
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    response_text = call_args[0][0]
    assert "Found 2 memories" in response_text or "memories" in response_text.lower()
    assert "92%" in response_text or "85%" in response_text


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_memory_search_empty_results_flow(bot_with_commands, mock_discord_interaction, mock_openai_client):
    """Teste E2E do fluxo de busca sem resultados."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mock para não retornar resultados
    mock_conn.fetch.return_value = []

    # Obter o comando de recall
    memory_recall_cmd = bot.tree.get_command("memory recall")

    # Executar o comando
    await memory_recall_cmd.callback(
        memory_recall_cmd,
        mock_discord_interaction,
        query="algo que não existe",
        limit=5
    )

    # Verificar mensagem de "não encontrado"
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "No memories found" in call_args[0][0]


# ============================================================================
# Testes E2E de Comandos de Grafo
# ============================================================================


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_graph_add_node_command_flow(bot_with_commands, mock_discord_interaction, mock_openai_client):
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

    # Executar o comando
    await graph_add_node_cmd.callback(
        graph_add_node_cmd,
        mock_discord_interaction,
        label="Python",
        node_type="language"
    )

    # Verificar resposta
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "Python" in call_args[0][0]
    assert "language" in call_args[0][0]


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_graph_add_edge_command_flow(bot_with_commands, mock_discord_interaction, mock_openai_client):
    """Teste E2E do fluxo de adicionar aresta ao grafo via /graph add_edge."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Configurar mocks para busca e criação de nós + aresta
    mock_conn.fetch.return_value = []
    mock_conn.fetchval.return_value = "edge-uuid-456"

    # Obter o comando
    graph_add_edge_cmd = bot.tree.get_command("graph add_edge")
    assert graph_add_edge_cmd is not None

    # Executar o comando
    await graph_add_edge_cmd.callback(
        graph_add_edge_cmd,
        mock_discord_interaction,
        source="Python",
        target="Discord",
        edge_type="used_for",
        weight=1.0
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
@pytest.mark.asyncio
async def test_graph_query_command_flow(bot_with_commands, mock_discord_interaction, mock_openai_client):
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

    # Executar o comando
    await graph_query_cmd.callback(
        graph_query_cmd,
        mock_discord_interaction,
        query="bibliotecas para bots discord",
        limit=5
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
    await help_cmd.callback( mock_discord_interaction)

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
    await ping_cmd.callback( mock_discord_interaction)

    # Verificar defer e followup (ping usa defer + followup)
    mock_discord_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_discord_interaction.followup.send.assert_called_once()
    call_args = mock_discord_interaction.followup.send.call_args
    assert "Pong!" in call_args[0][0]
    assert "50ms" in call_args[0][0]  # Latência configurada no fixture


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
    await status_cmd.callback( mock_discord_interaction)

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
@pytest.mark.asyncio
async def test_multi_command_session(bot_with_commands, mock_openai_client):
    """Teste E2E de múltiplos comandos em sequência simulando uma sessão."""
    bot, mock_pool, mock_conn = bot_with_commands

    # Comando 1: Adicionar memória
    interaction1 = MagicMock()
    interaction1.response.is_done.return_value = False
    interaction1.response.send_message = AsyncMock()
    interaction1.user.id = 123456789
    interaction1.channel_id = 987654321

    mock_conn.fetch.return_value = []
    mock_conn.fetchval.return_value = "uuid-1"

    memory_add_cmd = bot.tree.get_command("memory add")
    await memory_add_cmd.callback(
        memory_add_cmd, interaction1, key="projeto", value="Agnaldo Bot", importance=0.9
    )

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
        "embedding": None,
        "created_at": None,
        "updated_at": None,
    }

    graph_add_node_cmd = bot.tree.get_command("graph add_node")
    await graph_add_node_cmd.callback(
        graph_add_node_cmd, interaction2, label="Python", node_type="language"
    )

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

    mock_conn.fetch.return_value = [
        {
            "id": "uuid-1",
            "content": "Agnaldo Bot",
            "similarity": 0.95,
        }
    ]

    memory_recall_cmd = bot.tree.get_command("memory recall")
    await memory_recall_cmd.callback(
        memory_recall_cmd, interaction3, query="nome do projeto", limit=5
    )

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
        memory_add_cmd,
        mock_discord_interaction,
        key="teste",
        value="valor",
        importance=0.5
    )

    # Verificar mensagem de erro
    mock_discord_interaction.response.send_message.assert_called_once()
    call_args = mock_discord_interaction.response.send_message.call_args
    assert "Database not available" in call_args[0][0]


@pytest.mark.e2e
@pytest.mark.discord
@pytest.mark.asyncio
async def test_command_with_database_error_flow(bot_with_commands, mock_discord_interaction, mock_openai_client):
    """Teste E2E do comportamento quando ocorre erro no banco de dados."""
    bot, mock_pool, mock_conn = bot_with_commands

