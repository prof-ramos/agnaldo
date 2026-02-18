"""Validador de citações jurídicas para prevenção de alucinações.

Este módulo fornece validação de citações jurídicas em respostas do StudyAgent,
garantindo que referências a artigos, leis e jurisprudência sejam baseadas apenas
em conteúdo recuperado da base RAG.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ValidationResult:
    """Resultado da validação de citações.

    Attributes:
        is_valid: Se todas as citações são válidas.
        citations_found: Lista de citações encontradas na resposta.
        citations_verified: Lista de citações verificadas no contexto.
        invalid_citations: Lista de citações não encontradas no contexto.
        confidence_score: Score de confiança (0-1) baseado em verificações.
        warning_message: Mensagem de aviso se houver problemas.
    """

    is_valid: bool
    citations_found: list[str]
    citations_verified: list[str]
    invalid_citations: list[str]
    confidence_score: float
    warning_message: str | None = None


class CitationValidator:
    """Validador de citações jurídicas.

    Extrai citações de texto e verifica se elas existem no contexto RAG
    recuperado, prevenindo alucinações de referências jurídicas.
    """

    # Padrões regex para citações jurídicas brasileiras
    PATTERNS = {
        "artigo": r"art\.?\s*\d+[º°]?\s*(?:§\s*\d+[º°]?\s*)?(?:incisos?\s*[IVX]+)?",
        "lei": r"lei\s*n?[º°]?\s*\d+[.,]?\d*\s*/\s*\d{4}",
        "codigo": r"código\s+(?:penal|civil|processual\s+civil|tributário)",
        "sumula": r"súmula\s*(?:vinculante\s*)?\d+",
        "cf": r"constituição\s+Federal|art\.?\s*\d+[º°]?\s*,?\s*CF",
        "stf_stj": r"ST[FI].*?(?:\s+\d+)?",
    }

    def __init__(self, strict_mode: bool = True) -> None:
        """Inicializa o validador.

        Args:
            strict_mode: Se True, rejeita resposta com qualquer citação inválida.
                Se False, apenas avisa sobre citações não verificadas.
        """
        self.strict_mode = strict_mode

    def validate_response(
        self,
        response: str,
        retrieved_context: list[str],
    ) -> ValidationResult:
        """Valida as citações em uma resposta do StudyAgent.

        Args:
            response: Resposta gerada pelo LLM.
            retrieved_context: Contexto RAG recuperado (chunks de referência).

        Returns:
            ValidationResult com detalhes da validação.
        """
        # 1. Extrair citações da resposta
        citations = self._extract_citations(response)
        if not citations:
            # Sem citações é válido (pergunta geral)
            return ValidationResult(
                is_valid=True,
                citations_found=[],
                citations_verified=[],
                invalid_citations=[],
                confidence_score=0.5,
                warning_message=None,
            )

        # 2. Normalizar contexto recuperado para busca
        context_text = self._normalize_context(retrieved_context)

        # 3. Verificar cada citação no contexto
        verified: list[str] = []
        invalid: list[str] = []

        for citation in citations:
            normalized_citation = self._normalize_citation(citation)
            if self._citation_in_context(normalized_citation, context_text):
                verified.append(citation)
            else:
                invalid.append(citation)
                logger.warning(f"Citação não verificada: {citation}")

        # 4. Calcular score de confiança
        total = len(citations)
        confidence = len(verified) / total if total > 0 else 0.5

        # 5. Determinar validade
        is_valid = len(invalid) == 0 if self.strict_mode else confidence >= 0.7

        # 6. Gerar mensagem de aviso se necessário
        warning = None
        if invalid and not is_valid:
            if self.strict_mode:
                warning = (
                    f"❌ Resposta contém citações não verificadas: {', '.join(invalid)}. "
                    "Por segurança, a resposta foi rejeitada. Tente novamente."
                )
            else:
                warning = (
                    f"⚠️ Atenção: As seguintes citações não puderam ser verificadas "
                    f"na base de estudo: {', '.join(invalid)}. Verifique antes de confiar."
                )

        return ValidationResult(
            is_valid=is_valid,
            citations_found=citations,
            citations_verified=verified,
            invalid_citations=invalid,
            confidence_score=confidence,
            warning_message=warning,
        )

    def _extract_citations(self, text: str) -> list[str]:
        """Extrai citações jurídicas do texto.

        Args:
            text: Texto para extrair citações.

        Returns:
            Lista de citações encontradas (sem duplicatas).
        """
        citations: set[str] = set()
        text_lower = text.lower()

        for pattern_name, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            citations.update(matches)

        return sorted(citations)

    def _normalize_context(self, context_list: list[str]) -> str:
        """Normaliza o contexto recuperado para busca.

        Args:
            context_list: Lista de chunks de contexto.

        Returns:
            Texto normalizado em minúsculas.
        """
        return " ".join(context_list).lower()

    def _normalize_citation(self, citation: str) -> str:
        """Normaliza uma citação para comparação.

        Args:
            citation: Citação original.

        Returns:
            Citação normalizada em minúsculas.
        """
        return citation.lower().strip()

    def _citation_in_context(self, citation: str, context: str) -> bool:
        """Verifica se a citação existe no contexto.

        Args:
            citation: Citação normalizada.
            context: Contexto normalizado.

        Returns:
            True se a citação for encontrada no contexto.
        """
        # Busca exata primeiro
        if citation in context:
            return True

        # Busca parcial para artigos (ex: "art. 121" → "art 121")
        partial = re.sub(r"[^\w\s]", "", citation)
        context_partial = re.sub(r"[^\w\s]", "", context)
        return partial in context_partial

    def format_response_with_validation(
        self,
        response: str,
        validation: ValidationResult,
    ) -> str:
        """Formata a resposta com indicador de validação.

        Args:
            response: Resposta original do LLM.
            validation: Resultado da validação.

        Returns:
            Resposta formatada com badges de validação.
        """
        if not validation.citations_found:
            return response

        # Badge de confiança
        if validation.confidence_score >= 0.9:
            badge = "✅ Alta confiança - Fontes verificadas"
        elif validation.confidence_score >= 0.7:
            badge = "⚠️ Confiança média - Verifique fontes"
        else:
            badge = "❌ Baixa confiança - Não confie nesta resposta"

        # Adicionar badge ao final
        return f"{response}\n\n📊 **Validação**: {badge}"


# Singleton instance
_validator: CitationValidator | None = None


def get_citation_validator(strict_mode: bool = True) -> CitationValidator:
    """Retorna instância singleton do CitationValidator.

    Args:
        strict_mode: Modo estrito de validação.

    Returns:
        Instância do CitationValidator.
    """
    global _validator

    if _validator is None or _validator.strict_mode != strict_mode:
        _validator = CitationValidator(strict_mode=strict_mode)

    return _validator
