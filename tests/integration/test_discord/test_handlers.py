"""Testes de integração para MessageHandler do Discord.

Este módulo testa o processamento de mensagens do Discord através
do MessageHandler, incluindo interação com o orquestrador de agentes
e armazenamento de conversas no banco de dados.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.discord.handlers import MessageHandler
from src.exceptions import AgentCommunicationError
from src.intent.classifier import IntentClassifier


def _build_mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """Build a mock asyncpg pool com async context manager para acquire()."""
    mock_pool = MagicMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm

    # Mock transaction como async context manager
    transaction_cm = AsyncMock()
    transaction_cm.__aenter__.return_value = None
    transaction_cm.__aexit__.return_value = None
    mock_conn.transaction.return_value = transaction_cm

    return mock_pool


def _create_mock_message(
    content: str = "Hello bot",
    author_id: int = 123456,
    author_name: str = "TestUser",
    channel_id: int = 789012,
    guild_id: int | None = 987654,
    is_bot: bool = False,
) -> MagicMock:
    """Create a mock Discord Message object.

    Args:
        content: Message content.
        author_id: Discord user ID.
        author_name: Username.
        channel_id: Channel ID.
        guild_id: Guild ID (None for DM).
        is_bot: Whether the author is a bot.

    Returns:
        Mocked Discord Message object.
    """
    mock_message = MagicMock()
    mock_message.content = content
    mock_message.id = 999999

    # Mock author
    mock_author = MagicMock()
    mock_author.id = author_id
    mock_author.name = author_name
    mock_author.global_name = author_name
    mock_author.bot = is_bot
    mock_message.author = mock_author

    # Mock channel
    mock_channel = MagicMock()
    mock_channel.id = channel_id
    mock_message.channel = mock_channel

    # Mock guild
    if guild_id:
        mock_guild = MagicMock()
        mock_guild.id = guild_id
        mock_guild.name = "TestServer"
        mock_message.guild = mock_guild
    else:
        mock_message.guild = None

    return mock_message


@pytest.fixture
async def mock_intent_classifier():
    """Fixture que fornece um mock de IntentClassifier."""
    classifier = MagicMock(spec=IntentClassifier)
    yield classifier


@pytest.fixture
async def mock_bot():
    """Fixture que fornece um mock do Bot Discord."""
    bot = MagicMock()
    bot.personality = "You are a helpful assistant."
    yield bot


@pytest.fixture
async def mock_db_pool():
    """Fixture que fornece um mock do pool de banco de dados."""
    mock_conn = AsyncMock()

    # Mock fetchval para user_id
    mock_conn.fetchval.return_value = "mock-user-uuid"

    # Mock execute para inserts
    mock_conn.execute.return_value = "INSERT 1"

    return _build_mock_pool(mock_conn)


# Helper para criar mock de async generator para route_and_process
def _mock_async_generator(response_text: str):
    """Cria um async generator para mock de route_and_process."""
    async def gen(*args, **kwargs):
        yield response_text
    return gen


# Helper para criar mock de async generator com múltiplos chunks
def _mock_async_multi_chunk(*chunks: str):
    """Cria um async generator com múltiplos chunks."""
    async def gen(*args, **kwargs):
        for chunk in chunks:
            yield chunk
    return gen


# Helper para mock que lança exceção
def _mock_async_generator_error(error: Exception):
    """Cria um async generator que lança exceção."""
    async def gen(*args, **kwargs):
        raise error
        yield  # pragma: no cover (never reached)
    return gen


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_handle_ping_command(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa o processamento de comando /ping.

    Verifica se o handler reconhece e processa corretamente
    comandos de ping do Discord.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_db_pool)

    # Mock do orchestrator com async generator
    mock_orch = MagicMock()
    mock_orch.route_and_process = _mock_async_generator("Pong! Latency: 50ms")
    handler._orchestrator = mock_orch

    # Criar mensagem simulando /ping
    mock_message = _create_mock_message(content="/ping")

    # Act
    response = await handler.process_message(mock_message)

    # Assert
    assert response is not None
    assert "Pong" in response


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_handle_help_command(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa o processamento de comando /help.

    Verifica se o handler retorna as informações de ajuda
    corretas quando solicitado.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_db_pool)

    # Mock do orchestrator
    mock_orch = MagicMock()
    help_text = """
**Agnaldo Bot Commands**

`/ping` - Check bot responsiveness and latency
`/help` - Show this help message
`/status` - Show bot status and rate limit info
    """
    mock_orch.route_and_process = _mock_async_generator(help_text)
    handler._orchestrator = mock_orch

    # Criar mensagem simulando /help
    mock_message = _create_mock_message(content="/help")

    # Act
    response = await handler.process_message(mock_message)

    # Assert
    assert response is not None
    assert "Commands" in response or "commands" in response


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_handle_status_command(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa o processamento de comando /status.

    Verifica se o handler retorna o status atual do bot
    incluindo informações de rate limit.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_db_pool)

    # Mock do orchestrator
    mock_orch = MagicMock()
    status_text = """
**Agnaldo Bot Status**

Connected as: Agnaldo#1234
Servers: 5
Latency: 45ms

**Rate Limit Status**
Global tokens available: 50.0
Channel tokens available: 5.0
    """
    mock_orch.route_and_process = _mock_async_generator(status_text)
    handler._orchestrator = mock_orch

    # Criar mensagem simulando /status
    mock_message = _create_mock_message(content="/status")

    # Act
    response = await handler.process_message(mock_message)

    # Assert
    assert response is not None
    assert "Status" in response or "status" in response


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_handle_message(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa processamento de mensagem genérica.

    Verifica se uma mensagem comum do usuário é processada
    corretamente através do orquestrador e armazenada no banco.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_db_pool)

    # Mock do orchestrator que retorna múltiplos chunks
    mock_orch = MagicMock()
    mock_orch.route_and_process = _mock_async_multi_chunk("Olá! ", "Como posso ajudar você hoje?")
    handler._orchestrator = mock_orch

    # Criar mensagem genérica
    mock_message = _create_mock_message(
        content="Oi, tudo bem?",
        author_id=123456,
        author_name="Gabriel",
    )

    # Act
    response = await handler.process_message(mock_message)

    # Assert
    assert response == "Olá! Como posso ajudar você hoje?"

    # Verifica que o banco foi usado para armazenar a conversa
    assert mock_db_pool.acquire.called


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_handle_message_ignore_bot(mock_bot, mock_intent_classifier):
    """Testa que mensagens de bots são ignoradas.

    Verifica se o handler retorna None quando a mensagem
    é de outro bot.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, None)

    # Mock do orchestrator (não deve ser chamado)
    mock_orch = MagicMock()
    handler._orchestrator = mock_orch

    # Criar mensagem de bot
    mock_message = _create_mock_message(
        content="Hello from another bot",
        is_bot=True,
    )

    # Act
    response = await handler.process_message(mock_message)

    # Assert
    assert response is None


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_handle_message_ignore_empty(mock_bot, mock_intent_classifier):
    """Testa que mensagens vazias são ignoradas.

    Verifica se o handler retorna None quando a mensagem
    está vazia ou contém apenas espaços.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, None)

    # Mock do orchestrator (não deve ser chamado)
    mock_orch = MagicMock()
    handler._orchestrator = mock_orch

    # Testar mensagem vazia
    mock_message_empty = _create_mock_message(content="")
    response = await handler.process_message(mock_message_empty)
    assert response is None

    # Testar mensagem com apenas espaços
    mock_message_whitespace = _create_mock_message(content="   ")
    response = await handler.process_message(mock_message_whitespace)
    assert response is None


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_error_handling_agent_communication(mock_bot, mock_intent_classifier):
    """Testa tratamento de erros de comunicação com agente.

    Verifica se o handler lida corretamente com exceções
    AgentCommunicationError e retorna uma mensagem amigável.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, None)

    # Mock do orchestrator que levanta exceção
    mock_orch = MagicMock()
    error = AgentCommunicationError("API timeout", source_agent="orchestrator", target_agent="agent")
    mock_orch.route_and_process = _mock_async_generator_error(error)
    handler._orchestrator = mock_orch

    # Criar mensagem
    mock_message = _create_mock_message(content="Hello")

    # Act
    response = await handler.process_message(mock_message)

    # Assert
    assert response is not None
    assert "erro" in response.lower() or "error" in response.lower()
    assert "ocorre" in response.lower() or "ocurred" in response.lower()


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_error_handling_unexpected_exception(mock_bot, mock_intent_classifier):
    """Testa tratamento de exceções inesperadas.

    Verifica se o handler lida corretamente com exceções genéricas
    e retorna uma mensagem de erro padrão.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, None)

    # Mock do orchestrator que levanta exceção genérica
    mock_orch = MagicMock()
    mock_orch.route_and_process = _mock_async_generator_error(RuntimeError("Unexpected error"))
    handler._orchestrator = mock_orch

    # Criar mensagem
    mock_message = _create_mock_message(content="Hello")

    # Act
    response = await handler.process_message(mock_message)

    # Assert
    assert response is not None
    assert "erro" in response.lower() or "error" in response.lower()
    assert "tente novamente" in response.lower() or "try again" in response.lower()


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_orchestrator_not_initialized(mock_bot, mock_intent_classifier):
    """Testa erro quando o orchestrator não foi inicializado.

    Verifica se o handler retorna mensagem de erro apropriada
    quando process_message é chamado antes de initialize.
    """
    # Setup - handler sem inicializar o orchestrator
    handler = MessageHandler(mock_bot, mock_intent_classifier, None)
    # Não chamar initialize(), deixando _orchestrator como None

    # Criar mensagem
    mock_message = _create_mock_message(content="Hello")

    # Act
    response = await handler.process_message(mock_message)

    # Assert
    assert response is not None
    assert "erro" in response.lower() or "error" in response.lower()


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_message_context_building(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa que o contexto da mensagem é construído corretamente.

    Verifica se user_id, username, channel_id, guild_id e outras
    informações são extraídas e passadas corretamente ao orchestrator.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_db_pool)

    # Mock do orchestrator para capturar os argumentos
    received_context = {}

    async def mock_route_with_context(message, context, user_id, db_pool):
        received_context.update(context)
        received_context["user_id"] = user_id
        received_context["db_pool"] = db_pool
        yield "Response"

    mock_orch = MagicMock()
    mock_orch.route_and_process = mock_route_with_context
    handler._orchestrator = mock_orch

    # Criar mensagem com contexto completo
    mock_message = _create_mock_message(
        content="Test context",
        author_id=999888,
        author_name="ContextUser",
        channel_id=111222,
        guild_id=333444,
    )

    # Act
    await handler.process_message(mock_message)

    # Assert
    assert received_context.get("user_id") == "999888"
    assert received_context.get("username") == "ContextUser"
    assert received_context.get("channel_id") == "111222"
    assert received_context.get("guild_id") == "333444"
    assert received_context.get("guild_name") == "TestServer"
    assert received_context.get("is_dm") is False
    assert received_context.get("db_pool") == mock_db_pool


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_message_dm_context(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa que mensagens em DM são identificadas corretamente.

    Verifica se is_dm=True quando a mensagem não tem guild.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_db_pool)

    # Mock do orchestrator para capturar contexto
    received_context = {}

    async def mock_route_dm(message, context, user_id, db_pool):
        received_context.update(context)
        yield "DM Response"

    mock_orch = MagicMock()
    mock_orch.route_and_process = mock_route_dm
    handler._orchestrator = mock_orch

    # Criar mensagem DM (guild_id=None)
    mock_message = _create_mock_message(
        content="DM message",
        author_id=555666,
        guild_id=None,
    )

    # Act
    await handler.process_message(mock_message)

    # Assert
    assert received_context.get("is_dm") is True
    assert received_context.get("guild_id") is None
    assert received_context.get("guild_name") == "DM"


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_conversation_storage(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa que a conversa é armazenada no banco de dados.

    Verifica se as mensagens do usuário e respostas do assistente
    são persistidas corretamente nas tabelas apropriadas.
    """
    # Setup
    mock_conn = MagicMock()  # Use MagicMock, not AsyncMock, para evitar coroutines
    mock_conn.fetchval = AsyncMock(return_value="test-uuid-123")
    mock_conn.execute = AsyncMock(return_value="INSERT 1")
    mock_conn.fetch = AsyncMock(return_value=[])

    # Mock transaction como async context manager
    transaction_cm = AsyncMock()
    transaction_cm.__aenter__.return_value = None
    transaction_cm.__aexit__.return_value = None
    # transaction() deve retornar o context manager diretamente (não como coroutine)
    mock_conn.transaction = MagicMock(return_value=transaction_cm)

    # Criar pool
    mock_pool = MagicMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm

    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_pool)

    # Mock do orchestrator
    mock_orch = MagicMock()
    mock_orch.route_and_process = _mock_async_generator("Test response")
    handler._orchestrator = mock_orch

    # Criar mensagem
    mock_message = _create_mock_message(
        content="User message",
        author_id=777888,
        channel_id=999000,
        guild_id=111222,
    )

    # Act
    await handler.process_message(mock_message)

    # Assert - verifica que o banco foi usado
    assert mock_pool.acquire.called

    # Verifica que transação foi usada
    assert mock_conn.transaction.called

    # Verifica que execute foi chamado para inserts
    # (user insert, session insert, 2 message inserts)
    assert mock_conn.execute.call_count >= 2


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_get_conversation_history(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa a recuperação do histórico de conversas.

    Verifica se get_conversation_history retorna mensagens
    em ordem cronológica corretamente.

    NOTA: O SQL usa ORDER BY created_at DESC, então o fetch
    retorna em ordem reversa. O método inverte para cronológica.
    """
    # Setup
    mock_conn = AsyncMock()
    # O fetch retorna em ordem DESC (mais recente primeiro)
    mock_conn.fetch.return_value = [
        {
            "role": "user",
            "content": "How are you?",
            "created_at": datetime(2025, 1, 1, 10, 2, tzinfo=timezone.utc),
        },
        {
            "role": "assistant",
            "content": "Hi there!",
            "created_at": datetime(2025, 1, 1, 10, 1, tzinfo=timezone.utc),
        },
        {
            "role": "user",
            "content": "Hello",
            "created_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        },
    ]

    mock_pool = _build_mock_pool(mock_conn)

    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_pool)

    # Act
    history = await handler.get_conversation_history(
        user_id="123456",
        channel_id="789012",
        limit=10,
    )

    # Assert - após inverter, deve estar em ordem cronológica
    assert len(history) == 3
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hi there!"
    assert history[2]["role"] == "user"
    assert history[2]["content"] == "How are you?"

    # Verifica que fetch foi chamado com os parâmetros corretos
    mock_conn.fetch.assert_called_once()
    call_args = mock_conn.fetch.call_args
    assert "123456" in call_args[0]
    assert "789012" in call_args[0]


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_get_conversation_history_no_db(mock_bot, mock_intent_classifier):
    """Testa get_conversation_history sem banco de dados.

    Verifica que retorna lista vazia quando db_pool é None.
    """
    # Setup - handler sem db_pool
    handler = MessageHandler(mock_bot, mock_intent_classifier, None)

    # Act
    history = await handler.get_conversation_history(
        user_id="123456",
        channel_id="789012",
    )

    # Assert
    assert history == []


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_initialize_handler(mock_bot, mock_intent_classifier):
    """Testa a inicialização do MessageHandler.

    Verifica se initialize() configura o orchestrator corretamente
    com a personalidade do bot.
    """
    # Setup
    handler = MessageHandler(mock_bot, mock_intent_classifier, None)
    handler._orchestrator = None

    # Mock get_orchestrator
    mock_orch = AsyncMock()

    with patch("src.discord.handlers.get_orchestrator", return_value=mock_orch) as mock_get_orch:
        # Act
        await handler.initialize()

        # Assert
        assert handler._orchestrator == mock_orch
        mock_get_orch.assert_called_once_with(
            personality_instructions=["You are a helpful assistant."]
        )


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_database_error_during_storage(mock_bot, mock_intent_classifier):
    """Testa que erros no banco durante storage não quebram o fluxo.

    Verifica que mesmo com erro ao armazenar, o handler
    ainda retorna a resposta do agente.
    """
    # Setup
    mock_conn = AsyncMock()
    mock_conn.fetchval.side_effect = Exception("DB connection lost")

    mock_pool = _build_mock_pool(mock_conn)

    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_pool)

    # Mock do orchestrator
    mock_orch = MagicMock()
    mock_orch.route_and_process = _mock_async_generator("Response despite DB error")
    handler._orchestrator = mock_orch

    # Criar mensagem
    mock_message = _create_mock_message(content="Test message")

    # Act
    response = await handler.process_message(mock_message)

    # Assert - resposta ainda deve ser retornada
    assert response == "Response despite DB error"


@pytest.mark.integration
@pytest.mark.discord
@pytest.mark.asyncio
async def test_get_conversation_history_db_error(mock_bot, mock_intent_classifier, mock_db_pool):
    """Testa que erros no banco ao buscar histórico retornam lista vazia.

    Verifica que get_conversation_history lida gracefulmente com erros.
    """
    # Setup
    mock_conn = AsyncMock()
    mock_conn.fetch.side_effect = Exception("Database error")

    mock_pool = _build_mock_pool(mock_conn)

    handler = MessageHandler(mock_bot, mock_intent_classifier, mock_pool)

    # Act
    history = await handler.get_conversation_history(
        user_id="123456",
        channel_id="789012",
    )

    # Assert - deve retornar lista vazia em caso de erro
    assert history == []
