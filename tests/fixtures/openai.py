"""OpenAI client mocks para testes do Agnaldo.

Este módulo fornece mocks assíncronos do cliente OpenAI
para testes de embeddings e chat completions.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


def create_mock_embedding(
    embedding: list[float] | None = None,
    model: str = "text-embedding-3-small",
    embedding_dim: int = 1536,
) -> dict[str, Any]:
    """Cria uma resposta de embedding mockada.

    Args:
        embedding: Vetor de embedding. Se None, gera um vetor aleatório.
        model: Nome do modelo usado.
        embedding_dim: Dimensão do vetor se embedding for None.

    Returns:
        Dict com estrutura de resposta da API OpenAI embeddings.
    """
    if embedding is None:
        # Gera um embedding mockado com valores entre -1 e 1
        import random
        random.seed(42)  # Seed para reprodutibilidade
        embedding = [random.uniform(-1, 1) for _ in range(embedding_dim)]

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "embedding": embedding,
                "index": 0,
            }
        ],
        "model": model,
        "usage": {
            "prompt_tokens": 10,
            "total_tokens": 10,
        },
    }


def create_mock_chat_completion(
    content: str = "Test response",
    model: str = "gpt-4o",
    finish_reason: str = "stop",
    prompt_tokens: int = 20,
    completion_tokens: int = 10,
    total_tokens: int = 30,
) -> dict[str, Any]:
    """Cria uma resposta de chat completion mockada.

    Args:
        content: Conteúdo da resposta do modelo.
        model: Nome do modelo usado.
        finish_reason: Razão do término (stop, length, etc).
        prompt_tokens: Tokens de entrada.
        completion_tokens: Tokens de saída.
        total_tokens: Total de tokens.

    Returns:
        Dict com estrutura de resposta da API OpenAI chat completions.
    """
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    }


def create_mock_openai_client(
    embedding_response: dict[str, Any] | None = None,
    chat_response: dict[str, Any] | None = None,
    embedding_model: str = "text-embedding-3-small",
    chat_model: str = "gpt-4o",
) -> AsyncMock:
    """Cria um mock do cliente OpenAI com métodos assíncronos.

    Args:
        embedding_response: Resposta padrão para embeddings.create.
        chat_response: Resposta padrão para chat.completions.create.
        embedding_model: Modelo de embedding padrão.
        chat_model: Modelo de chat padrão.

    Returns:
        AsyncMock configurado como AsyncOpenAI client.
    """
    mock_client = AsyncMock()

    # Configurar embeddings
    if embedding_response is None:
        embedding_response = create_mock_embedding(model=embedding_model)

    mock_embeddings = MagicMock()
    mock_embeddings.create = AsyncMock(return_value=MagicMock(**embedding_response))
    mock_client.embeddings = mock_embeddings

    # Configurar chat completions
    if chat_response is None:
        chat_response = create_mock_chat_completion(model=chat_model)

    mock_chat = MagicMock()
    mock_chat.completions = MagicMock()
    mock_chat.completions.create = AsyncMock(return_value=MagicMock(**chat_response))
    mock_client.chat = mock_chat

    return mock_client


def create_mock_openai_with_side_effects(
    embedding_side_effect: list | None = None,
    chat_side_effect: list | None = None,
) -> AsyncMock:
    """Cria um mock do cliente OpenAI com efeitos colaterais (side effects).

    Útil para testar chamadas múltiplas com respostas diferentes.

    Args:
        embedding_side_effect: Lista de respostas para embeddings sequencialmente.
        chat_side_effect: Lista de respostas para chat sequencialmente.

    Returns:
        AsyncMock configurado com side_effects.
    """
    mock_client = AsyncMock()

    # Configurar embeddings com side_effect
    mock_embeddings = MagicMock()
    if embedding_side_effect:
        mock_embeddings.create = AsyncMock(
            side_effect=[MagicMock(**r) for r in embedding_side_effect]
        )
    else:
        mock_embeddings.create = AsyncMock()
    mock_client.embeddings = mock_embeddings

    # Configurar chat com side_effect
    mock_chat = MagicMock()
    mock_chat.completions = MagicMock()
    if chat_side_effect:
        mock_chat.completions.create = AsyncMock(
            side_effect=[MagicMock(**r) for r in chat_side_effect]
        )
    else:
        mock_chat.completions.create = AsyncMock()
    mock_client.chat = mock_chat

    return mock_client


class MockOpenAIEmbeddingResponse:
    """Mock de resposta de embedding OpenAI.

    Acessa os dados via atributos para compatibilidade com
    response.data[0].embedding.
    """

    def __init__(
        self,
        embedding: list[float] | None = None,
        model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
    ):
        """Inicializa o mock de resposta de embedding."""
        if embedding is None:
            import random
            random.seed(42)
            embedding = [random.uniform(-1, 1) for _ in range(embedding_dim)]

        self.object = "list"
        self.model = model

        self.data = [self._MockEmbeddingData(embedding)]
        self.usage = self._MockUsage(10, 10)

    class _MockEmbeddingData:
        """Mock de item de embedding."""

        def __init__(self, embedding: list[float]):
            self.object = "embedding"
            self.embedding = embedding
            self.index = 0

    class _MockUsage:
        """Mock de usage."""

        def __init__(self, prompt_tokens: int, total_tokens: int):
            self.prompt_tokens = prompt_tokens
            self.total_tokens = total_tokens


class MockOpenAIChatCompletionResponse:
    """Mock de resposta de chat completion OpenAI.

    Acessa os dados via atributos para compatibilidade com
    response.choices[0].message.content.
    """

    def __init__(
        self,
        content: str = "Test response",
        model: str = "gpt-4o",
        finish_reason: str = "stop",
        prompt_tokens: int = 20,
        completion_tokens: int = 10,
        total_tokens: int = 30,
    ):
        """Inicializa o mock de resposta de chat completion."""
        self.id = "chatcmpl-test123"
        self.object = "chat.completion"
        self.created = 1234567890
        self.model = model

        self.choices = [self._MockChoice(content, finish_reason)]
        self.usage = self._MockUsage(prompt_tokens, completion_tokens, total_tokens)

    class _MockChoice:
        """Mock de choice."""

        def __init__(self, content: str, finish_reason: str):
            self.index = 0
            self.message = self._MockMessage(content)
            self.finish_reason = finish_reason

        class _MockMessage:
            """Mock de message."""

            def __init__(self, content: str):
                self.role = "assistant"
                self.content = content

    class _MockUsage:
        """Mock de usage."""

        def __init__(self, prompt_tokens: int, completion_tokens: int, total_tokens: int):
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens
            self.total_tokens = total_tokens


@pytest.fixture
def mock_openai_client():
    """Fixture pytest que retorna um mock do cliente OpenAI."""
    return create_mock_openai_client()


@pytest.fixture
def mock_openai_embedding_response():
    """Fixture pytest que retorna uma resposta de embedding mockada."""
    return create_mock_embedding()


@pytest.fixture
def mock_openai_chat_response():
    """Fixture pytest que retorna uma resposta de chat mockada."""
    return create_mock_chat_completion()


@pytest.fixture
def mock_openai_with_embeddings():
    """Fixture pytest que retorna cliente OpenAI com embedings."""
    mock = AsyncMock()
    mock.embeddings = MagicMock()
    mock.embeddings.create = AsyncMock(
        return_value=MockOpenAIEmbeddingResponse()
    )
    return mock


@pytest.fixture
def mock_openai_with_chat():
    """Fixture pytest que retorna cliente OpenAI com chat."""
    mock = AsyncMock()
    mock.chat = MagicMock()
    mock.chat.completions = MagicMock()
    mock.chat.completions.create = AsyncMock(
        return_value=MockOpenAIChatCompletionResponse()
    )
    return mock


@pytest.fixture
def mock_openai_full():
    """Fixture pytest que retorna cliente OpenAI completo."""
    mock = AsyncMock()

    # Embeddings
    mock.embeddings = MagicMock()
    mock.embeddings.create = AsyncMock(
        return_value=MockOpenAIEmbeddingResponse()
    )

    # Chat
    mock.chat = MagicMock()
    mock.chat.completions = MagicMock()
    mock.chat.completions.create = AsyncMock(
        return_value=MockOpenAIChatCompletionResponse()
    )

    return mock
