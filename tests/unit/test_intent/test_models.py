"""Testes unitários para IntentCategory e IntentResult."""

import pytest

from src.intent.models import IntentCategory, IntentResult


class TestIntentCategory:
    """Testes para o enum IntentCategory."""

    def test_intent_category_values(self) -> None:
        """Verifica se todos os valores esperados estão definidos."""
        # Knowledge & Information
        assert IntentCategory.KNOWLEDGE_QUERY.value == "knowledge_query"
        assert IntentCategory.DEFINITION.value == "definition"
        assert IntentCategory.EXPLANATION.value == "explanation"

        # Actions & Operations
        assert IntentCategory.SEARCH.value == "search"
        assert IntentCategory.COMPUTE.value == "compute"
        assert IntentCategory.ANALYZE.value == "analyze"

        # Conversational
        assert IntentCategory.GREETING.value == "greeting"
        assert IntentCategory.FAREWELL.value == "farewell"
        assert IntentCategory.THANKS.value == "thanks"

        # Bot Management
        assert IntentCategory.HELP.value == "help"
        assert IntentCategory.STATUS.value == "status"

        # Graph & Memory
        assert IntentCategory.GRAPH_QUERY.value == "graph_query"
        assert IntentCategory.MEMORY_STORE.value == "memory_store"
        assert IntentCategory.MEMORY_RETRIEVE.value == "memory_retrieve"

    def test_intent_classification(self) -> None:
        """Verifica a categorização correta dos intents."""
        # Knowledge & Information
        knowledge_intents = [
            IntentCategory.KNOWLEDGE_QUERY,
            IntentCategory.DEFINITION,
            IntentCategory.EXPLANATION,
        ]
        for intent in knowledge_intents:
            assert intent.value in [
                "knowledge_query",
                "definition",
                "explanation",
            ]

        # Actions & Operations
        action_intents = [
            IntentCategory.SEARCH,
            IntentCategory.COMPUTE,
            IntentCategory.ANALYZE,
        ]
        for intent in action_intents:
            assert intent.value in ["search", "compute", "analyze"]

        # Conversational
        conversational_intents = [
            IntentCategory.GREETING,
            IntentCategory.FAREWELL,
            IntentCategory.THANKS,
        ]
        for intent in conversational_intents:
            assert intent.value in ["greeting", "farewell", "thanks"]

        # Bot Management
        management_intents = [IntentCategory.HELP, IntentCategory.STATUS]
        for intent in management_intents:
            assert intent.value in ["help", "status"]

        # Graph & Memory
        graph_memory_intents = [
            IntentCategory.GRAPH_QUERY,
            IntentCategory.MEMORY_STORE,
            IntentCategory.MEMORY_RETRIEVE,
        ]
        for intent in graph_memory_intents:
            assert intent.value in ["graph_query", "memory_store", "memory_retrieve"]

    def test_intent_display_names(self) -> None:
        """Verifica os nomes de exibição das categorias."""
        # Como IntentCategory herda de str, o valor é retornado diretamente
        assert IntentCategory.KNOWLEDGE_QUERY == "knowledge_query"
        assert IntentCategory.GREETING == "greeting"
        assert IntentCategory.MEMORY_STORE == "memory_store"

    def test_all_categories_defined(self) -> None:
        """Verifica se existem exatamente 15 categorias definidas."""
        all_categories = list(IntentCategory)
        assert len(all_categories) == 15

        # Verificar que não há duplicatas
        unique_values = {cat.value for cat in all_categories}
        assert len(unique_values) == 15

        # Lista completa de categorias esperadas
        expected_categories = {
            "knowledge_query",
            "definition",
            "explanation",
            "search",
            "compute",
            "analyze",
            "greeting",
            "farewell",
            "thanks",
            "help",
            "status",
            "graph_query",
            "memory_store",
            "memory_retrieve",
            "out_of_scope",
        }
        actual_values = {cat.value for cat in all_categories}
        assert actual_values == expected_categories


class TestIntentResult:
    """Testes para o dataclass IntentResult."""

    def test_intent_result_creation(self) -> None:
        """Verifica a criação bem-sucedida de IntentResult."""
        result = IntentResult(
            intent=IntentCategory.GREETING,
            confidence=0.95,
            entities={"user": "Gabriel"},
            raw_text="Olá, tudo bem?",
        )

        assert result.intent == IntentCategory.GREETING
        assert result.confidence == 0.95
        assert result.entities == {"user": "Gabriel"}
        assert result.raw_text == "Olá, tudo bem?"

    def test_confidence_within_bounds(self) -> None:
        """Verifica confianças dentro dos limites válidos."""
        # Confiança mínima
        result_min = IntentResult(
            intent=IntentCategory.HELP,
            confidence=0.0,
            entities={},
            raw_text="help",
        )
        assert result_min.confidence == 0.0

        # Confiança máxima
        result_max = IntentResult(
            intent=IntentCategory.HELP,
            confidence=1.0,
            entities={},
            raw_text="help",
        )
        assert result_max.confidence == 1.0

        # Confiança intermediária
        result_mid = IntentResult(
            intent=IntentCategory.HELP,
            confidence=0.5,
            entities={},
            raw_text="help",
        )
        assert result_mid.confidence == 0.5

    def test_confidence_out_of_bounds_high(self) -> None:
        """Verifica erro quando confiança > 1.0."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            IntentResult(
                intent=IntentCategory.SEARCH,
                confidence=1.5,
                entities={},
                raw_text="search",
            )

    def test_confidence_out_of_bounds_low(self) -> None:
        """Verifica erro quando confiança < 0.0."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            IntentResult(
                intent=IntentCategory.SEARCH,
                confidence=-0.1,
                entities={},
                raw_text="search",
            )

    def test_confidence_exactly_at_boundary(self) -> None:
        """Verifica valores exatos nos limites (0.0 e 1.0)."""
        # Limite inferior
        result_0 = IntentResult(
            intent=IntentCategory.MEMORY_STORE,
            confidence=0.0,
            entities={"key": "value"},
            raw_text="memorize isso",
        )
        assert result_0.confidence == 0.0

        # Limite superior
        result_1 = IntentResult(
            intent=IntentCategory.MEMORY_STORE,
            confidence=1.0,
            entities={"key": "value"},
            raw_text="memorize isso",
        )
        assert result_1.confidence == 1.0
