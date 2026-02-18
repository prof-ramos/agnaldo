"""Testes de integração para IntentClassifier."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.intent.classifier import IntentClassifier
from src.intent.models import IntentCategory, IntentResult


@pytest.fixture
def mock_sentence_transformer():
    """Fixture que mocka o SentenceTransformer."""
    with patch("src.intent.classifier.SentenceTransformer") as mock:
        # Mock do modelo
        mock_model = MagicMock()
        mock.return_value = mock_model

        # Configurar encode para retornar embeddings mockados
        def mock_encode_fn(texts, convert_to_numpy=True):
            if isinstance(texts, str):
                texts = [texts]
            # Retorna embeddings aleatórios mas determinísticos baseados no texto
            embeddings = []
            for text in texts:
                # Usa hash do texto para gerar valores determinísticos
                np.random.seed(hash(text) % (2**32))
                emb = np.random.randn(384).astype(np.float32)  # Tamanho padrão do MiniLM
                if convert_to_numpy:
                    embeddings.append(emb)
                else:
                    embeddings.append(emb.tolist())
            return np.array(embeddings) if convert_to_numpy else embeddings

        mock_model.encode.side_effect = mock_encode_fn
        yield mock_model


@pytest.fixture
async def classifier(mock_sentence_transformer):
    """Fixture que fornece uma instância do IntentClassifier inicializada."""
    clf = IntentClassifier(model_name="all-MiniLM-L6-v2", dataset_path=None)
    await clf.initialize()
    return clf


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classify_conversational_intent(classifier: IntentClassifier):
    """Testa classificação de intents conversacionais (greeting, farewell, thanks)."""
    # Teste de saudação
    result = await classifier.classify("Olá, tudo bem?")
    assert result.raw_text == "Olá, tudo bem?"
    assert "word_count" in result.entities
    assert isinstance(result.intent, IntentCategory)

    # Teste de despedida
    result = await classifier.classify("Tchau, até mais!")
    assert isinstance(result.intent, IntentCategory)

    # Teste de agradecimento
    result = await classifier.classify("Obrigado pela ajuda!")
    assert isinstance(result.intent, IntentCategory)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classify_knowledge_query(classifier: IntentClassifier):
    """Testa classificação de queries de conhecimento."""
    # Queries de conhecimento típicas
    knowledge_queries = [
        "O que você sabe sobre Python?",
        "Me fale sobre machine learning",
        "Explique como funciona redes neurais",
        "Informações sobre processamento de linguagem natural",
    ]

    for query in knowledge_queries:
        result = await classifier.classify(query)
        # Verificar que retornou um resultado válido
        assert isinstance(result, IntentResult)
        assert isinstance(result.intent, IntentCategory)
        assert result.confidence >= 0.0
        assert result.raw_text == query


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classify_memory_operation(classifier: IntentClassifier):
    """Testa classificação de operações de memória."""
    # Operações de armazenamento
    storage_queries = [
        "Lembre que eu gosto de café",
        "Guarde esta informação",
        "Salve na memória que meu aniversário é em junho",
    ]

    for query in storage_queries:
        result = await classifier.classify(query)
        # Pode classificar como MEMORY_STORE ou outros intents relacionados
        assert isinstance(result.intent, IntentCategory)
        assert 0.0 <= result.confidence <= 1.0

    # Operações de recuperação
    retrieval_queries = [
        "O que você se lembra sobre mim?",
        "Me mostre minhas memórias",
        "Recupere informações anteriores",
    ]

    for query in retrieval_queries:
        result = await classifier.classify(query)
        assert isinstance(result.intent, IntentCategory)
        assert 0.0 <= result.confidence <= 1.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_confidence_scores(classifier: IntentClassifier):
    """Testa que scores de confiança estão no intervalo válido."""
    test_cases = [
        "Olá",  # Curto, pode ter baixa confiança
        "Me explique o que é inteligência artificial em detalhes",  # Específico
        "Status do sistema",  # Comando direto
        "Texto aleatório que não se encaixa bem em nenhuma categoria",  # Ambíguo
    ]

    for text in test_cases:
        result = await classifier.classify(text)
        assert 0.0 <= result.confidence <= 1.0, (
            f"Confiança fora do intervalo para '{text}': {result.confidence}"
        )
        assert isinstance(result.intent, IntentCategory)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unknown_intent(classifier: IntentClassifier):
    """Testa classificação de texto ambíguo ou desconhecido."""
    # Textos ambíguos que não se encaixam claramente em nenhuma categoria
    ambiguous_texts = [
        "xyzabc123",
        "(&*%$#@!",
        "",  # Texto vazio
        "a" * 500,  # Texto muito longo
    ]

    for text in ambiguous_texts:
        result = await classifier.classify(text)
        # Mesmo para textos desconhecidos, deve retornar algum intent
        assert isinstance(result.intent, IntentCategory)
        assert 0.0 <= result.confidence <= 1.0
        assert result.raw_text == text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_entity_extraction_knowledge(classifier: IntentClassifier):
    """Testa extração de entidades para queries de conhecimento."""
    result = await classifier.classify("Me fale sobre machine learning")
    assert isinstance(result.intent, IntentCategory)
    # Verificar que extraiu entidades básicas
    assert "word_count" in result.entities
    # Verificar que extraiu o tópico após "about" (se aplicável)
    if "topic" in result.entities:
        assert result.entities["topic"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_entity_extraction_graph(classifier: IntentClassifier):
    """Testa extração de entidades para queries de grafo."""
    result = await classifier.classify("Mostre conexões entre Python e Data Science")
    # Se classificar como GRAPH_QUERY, deve extrair nós potenciais
    if result.intent == IntentCategory.GRAPH_QUERY:
        assert "potential_nodes" in result.entities or "word_count" in result.entities


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classify_expected_intent_with_controlled_embeddings(classifier: IntentClassifier):
    """Testa classificação determinística com embeddings controlados."""
    classifier._intent_embeddings = {
        IntentCategory.GREETING: np.array([1.0, 0.0, 0.0]),
        IntentCategory.KNOWLEDGE_QUERY: np.array([0.0, 1.0, 0.0]),
        IntentCategory.HELP: np.array([0.0, 0.0, 1.0]),
    }

    def controlled_encode(texts, convert_to_numpy=True):
        if isinstance(texts, str):
            texts = [texts]
        embeddings = []
        for text in texts:
            lowered = text.lower()
            if "olá" in lowered or "oi" in lowered:
                emb = np.array([1.0, 0.0, 0.0])
            elif "python" in lowered:
                emb = np.array([0.0, 1.0, 0.0])
            else:
                emb = np.array([0.0, 0.0, 1.0])
            embeddings.append(emb)
        return np.array(embeddings) if convert_to_numpy else embeddings

    classifier.model.encode = controlled_encode

    result_greeting = await classifier.classify("Olá!")
    assert result_greeting.intent == IntentCategory.GREETING

    result_knowledge = await classifier.classify("O que é Python?")
    assert result_knowledge.intent == IntentCategory.KNOWLEDGE_QUERY

    result_help = await classifier.classify("Preciso de ajuda")
    assert result_help.intent == IntentCategory.HELP


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_classification(classifier: IntentClassifier):
    """Testa classificação em lote de múltiplos textos."""
    texts = [
        "Olá!",
        "O que é Python?",
        "Lembre que eu gosto de pizza",
        "Tchau!",
    ]

    results = await classifier.classify_batch(texts)

    assert len(results) == len(texts)
    for i, result in enumerate(results):
        assert isinstance(result, IntentResult)
        assert result.raw_text == texts[i]
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.intent, IntentCategory)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classifier_not_initialized():
    """Testa que o classificador chama initialize automaticamente."""
    with patch("src.intent.classifier.SentenceTransformer") as mock:
        # Mock do modelo que aceita kwargs
        mock_model = MagicMock()

        def mock_encode(texts, convert_to_numpy=True, **kwargs):
            if isinstance(texts, str):
                texts = [texts]
            return np.random.randn(len(texts), 384)

        mock_model.encode.side_effect = mock_encode
        mock.return_value = mock_model

        classifier = IntentClassifier(model_name="all-MiniLM-L6-v2")
        # Classificar deve chamar initialize automaticamente
        result = await classifier.classify("Teste")
        assert isinstance(result, IntentResult)
        assert classifier.is_ready()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_threshold_parameter(classifier: IntentClassifier):
    """Testa o parâmetro threshold na classificação."""
    # O threshold é usado para filtrar resultados de baixa confiança
    # mas a implementação atual sempre retorna o melhor match

    result_high_threshold = await classifier.classify("Olá!", threshold=0.9)
    result_low_threshold = await classifier.classify("Olá!", threshold=0.1)

    # Ambos devem retornar resultados válidos
    assert isinstance(result_high_threshold, IntentResult)
    assert isinstance(result_low_threshold, IntentResult)

    # Confiança deve ser a mesma independente do threshold
    # (implementação atual não filtra por threshold)
    assert result_high_threshold.confidence == result_low_threshold.confidence


@pytest.mark.integration
@pytest.mark.asyncio
async def test_is_ready(classifier: IntentClassifier):
    """Testa o método is_ready do classificador."""
    # Após initialize, deve estar pronto
    assert classifier.is_ready() is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_initialize_calls(classifier: IntentClassifier):
    """Testa que múltiplas chamadas a initialize não causam problemas."""
    # Primeira chamada
    await classifier.initialize()
    assert classifier.is_ready()

    # Segunda chamada não deve causar erro
    await classifier.initialize()
    assert classifier.is_ready()

    # Terceira chamada
    await classifier.initialize()
    assert classifier.is_ready()
