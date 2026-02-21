"""Testes unitários para CitationValidator.

Este módulo testa a validação de citações jurídicas para minimizar alucinações
no StudyAgent do Agnaldo Concursos RAG.
"""

import pytest

from src.validators.citation_validator import (
    CitationValidator,
    ValidationResult,
    get_citation_validator,
)


class TestCitationValidator:
    """Testes para CitationValidator."""

    def test_initialization(self) -> None:
        """Testa inicialização do validator."""
        validator = CitationValidator(strict_mode=True)
        assert validator.strict_mode is True
        assert validator.PATTERNS is not None
        assert len(validator.PATTERNS) > 0

    def test_extract_citations_artigo(self) -> None:
        """Testa extração de citações de artigos."""
        validator = CitationValidator(strict_mode=True)

        text = "Conforme o Art. 121 do Código Penal, o homicídio é crime."
        citations = validator._extract_citations(text)

        assert len(citations) > 0
        assert any("art" in c.lower() and "121" in c for c in citations)

    def test_extract_citations_lei(self) -> None:
        """Testa extração de citações de leis."""
        validator = CitationValidator(strict_mode=True)

        text = "A Lei nº 13.964/2019 alterou o Código de Processo Penal."
        citations = validator._extract_citations(text)

        assert len(citations) > 0
        assert any("lei" in c.lower() and "13.964" in c for c in citations)

    def test_extract_citations_codigo(self) -> None:
        """Testa extração de citações de códigos."""
        validator = CitationValidator(strict_mode=True)

        text = "O Código Penal prevê as qualificadoras no Art. 121, §2º."
        citations = validator._extract_citations(text)

        assert len(citations) > 0
        assert any("código" in c.lower() and "penal" in c.lower() for c in citations)

    def test_extract_citations_sumula(self) -> None:
        """Testa extração de citações de súmulas."""
        validator = CitationValidator(strict_mode=True)

        text = "A Súmula Vinculante 11 do STF estabelece o entendimento."
        citations = validator._extract_citations(text)

        assert len(citations) > 0
        assert any("súmula" in c.lower() and "11" in c for c in citations)

    def test_extract_citations_cf(self) -> None:
        """Testa extração de citações da Constituição Federal."""
        validator = CitationValidator(strict_mode=True)

        text = "Conforme Art. 5º, CF, todos são iguais perante a lei."
        citations = validator._extract_citations(text)

        assert len(citations) > 0
        assert any("cf" in c.lower() or "constituição" in c.lower() for c in citations)

    def test_validate_response_with_valid_citations(self) -> None:
        """Testa validação de resposta com citações válidas (presentes no contexto)."""
        validator = CitationValidator(strict_mode=True)

        response = "As qualificadoras estão no Art. 121 do Código Penal."
        context = ["Art. 121 do Código Penal define o crime de homicídio doloso."]

        result: ValidationResult = validator.validate_response(response, context)

        assert result.is_valid is True
        assert len(result.invalid_citations) == 0

    def test_validate_response_with_invalid_citations(self) -> None:
        """Testa validação de resposta com citações inválidas (não presentes no contexto)."""
        validator = CitationValidator(strict_mode=True)

        response = "O Art. 122 do Código Penal define o homicídio culposo."
        context = ["Art. 121 do Código Penal define o crime de homicídio doloso."]

        result: ValidationResult = validator.validate_response(response, context)

        # A citação 122 não está no contexto, então deve ser inválida
        assert result.is_valid is False
        assert len(result.invalid_citations) > 0

    def test_validate_response_without_citations(self) -> None:
        """Testa validação de resposta sem citações."""
        validator = CitationValidator(strict_mode=True)

        response = "O homicídio é crime grave contra a vida."
        context = ["Art. 121 do Código Penal define o crime de homicídio doloso."]

        result: ValidationResult = validator.validate_response(response, context)

        # Sem citações, considera válido (resposta geral)
        assert result.is_valid is True

    def test_validate_response_with_multiple_citations(self) -> None:
        """Testa validação de resposta com múltiplas citações."""
        validator = CitationValidator(strict_mode=True)

        response = "Conforme Art. 121 e Art. 122, ambos do Código Penal."
        context = [
            "Art. 121 do Código Penal define o crime de homicídio doloso.",
            "Art. 122 do Código Penal define o crime de homicídio culposo.",
        ]

        result: ValidationResult = validator.validate_response(response, context)

        assert result.is_valid is True
        assert len(result.citations_verified) >= 2

    def test_citation_in_context_exact_match(self) -> None:
        """Testa verificação de citação no contexto com match exato."""
        validator = CitationValidator(strict_mode=True)

        citation = "Art. 121"
        context = "Art. 121 do Código Penal define o homicídio doloso."

        result = validator._citation_in_context(citation, context)

        assert result is True

    def test_citation_in_context_no_match(self) -> None:
        """Testa verificação de citação não presente no contexto."""
        validator = CitationValidator(strict_mode=True)

        citation = "Art. 999"
        context = "Art. 121 do Código Penal define o homicídio doloso."

        result = validator._citation_in_context(citation, context)

        assert result is False

    def test_confidence_score_all_verified(self) -> None:
        """Testa cálculo de score de confiança quando todas citações são verificadas."""
        validator = CitationValidator(strict_mode=True)

        response = "Conforme Art. 121 do Código Penal."
        context = ["Art. 121 do Código Penal define o homicídio doloso."]

        result: ValidationResult = validator.validate_response(response, context)

        assert result.confidence_score == 1.0

    def test_confidence_score_partial_verified(self) -> None:
        """Testa cálculo de score de confiança com verificações parciais."""
        validator = CitationValidator(strict_mode=True)

        response = "Conforme Art. 121 e Art. 999 do Código Penal."
        context = ["Art. 121 do Código Penal define o homicídio doloso."]

        result: ValidationResult = validator.validate_response(response, context)

        # 2 de 3 citações verificadas (art. 121, código penal, art. 999) = 0.666...
        # Ou pode variar dependendo de quantas citações são encontradas
        assert result.confidence_score < 1.0
        assert result.is_valid is False  # Pelo menos uma citação inválida

    def test_warning_message_generation(self) -> None:
        """Testa geração de mensagem de aviso para citações inválidas."""
        validator = CitationValidator(strict_mode=True)

        response = "Conforme Art. 999 do Código Penal."
        context = ["Art. 121 do Código Penal define o homicídio doloso."]

        result: ValidationResult = validator.validate_response(response, context)

        assert result.warning_message is not None
        assert "999" in result.warning_message or "não verificada" in result.warning_message.lower()

    def test_singleton_get_citation_validator(self) -> None:
        """Testa função singleton get_citation_validator."""
        validator1 = get_citation_validator(strict_mode=True)
        validator2 = get_citation_validator(strict_mode=True)

        # Singleton deve retornar a mesma instância
        assert validator1 is validator2

    def test_strict_mode_false(self) -> None:
        """Testa comportamento em modo não-estrito."""
        validator = CitationValidator(strict_mode=False)

        # Em modo não estrito, pode ter comportamento mais permissivo
        response = "Resposta sem citações específicas."
        context = ["Contexto genérico sobre direito penal."]

        result: ValidationResult = validator.validate_response(response, context)

        # Deve ser válido mesmo sem citações específicas
        assert result.is_valid is True


class TestCitationValidatorPatterns:
    """Testes específicos para padrões de regex."""

    def test_pattern_artigo_variations(self) -> None:
        """Testa padrão de artigo com variações."""
        validator = CitationValidator(strict_mode=True)

        variations = [
            "Art. 121",
            "artigo 121",
            "Art 121",
            "art. 121º",
            "Artigo 121",
        ]

        for variation in variations:
            text = f"Conforme {variation} do Código Penal."
            citations = validator._extract_citations(text)
            assert len(citations) > 0, f"Falha para variação: {variation}"

    def test_pattern_lei_variations(self) -> None:
        """Testa padrão de lei com variações."""
        validator = CitationValidator(strict_mode=True)

        variations = [
            "Lei 13.964/2019",
            "Lei nº 13.964/2019",
            "Lei nº 13.964/2019",
            "lei 13964/2019",
        ]

        for variation in variations:
            text = f"Conforme {variation}."
            citations = validator._extract_citations(text)
            assert len(citations) > 0, f"Falha para variação: {variation}"

    def test_pattern_paragrafo(self) -> None:
        """Testa padrão com parágrafo."""
        validator = CitationValidator(strict_mode=True)

        text = "Conforme Art. 121, §2º do Código Penal."
        citations = validator._extract_citations(text)

        assert len(citations) > 0
        # Deve capturar tanto o artigo quanto o parágrafo
        combined = " ".join(citations).lower()
        assert "121" in combined

    def test_pattern_inciso(self) -> None:
        """Testa padrão com inciso romano."""
        validator = CitationValidator(strict_mode=True)

        text = "Conforme inciso I do Art. 121."
        citations = validator._extract_citations(text)

        assert len(citations) > 0
        combined = " ".join(citations).lower()
        assert "121" in combined
