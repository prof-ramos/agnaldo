"""StudyAgent para RAG rigoroso em concursos públicos.

Este módulo implementa o StudyAgent, um agente especializado em responder
perguntas de estudo para concursos com base em documentos jurídicos
curados (legislação, doutrina, questões, jurisprudência).

Principais características:
- RAG rigoroso com busca semântica via pgvector
- Temperatura 0.0 para minimizar alucinações
- Citação obrigatória de fontes
- Thresholds dinâmicos por tipo de fonte
- Validação de citações jurídicas
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from loguru import logger
from openai import AsyncOpenAI

from src.config.settings import get_settings
from src.database.models import LEGAL_CATEGORIES
from src.schemas.knowledge import (
    RAGSearchResult,
    StudyAgentRequest,
    StudyAgentResponse,
)
from src.validators.citation_validator import CitationValidator, get_citation_validator

if TYPE_CHECKING:
    from asyncpg import Pool as AsyncPGPool
else:
    AsyncPGPool = object  # type: ignore[assignment]


class StudyAgent:
    """Agente de estudo especializado em RAG jurídico rigoroso.

    Implementa busca semântica em documentos legais com validação
    de citações para minimizar alucinações em respostas de estudo.

    Attributes:
        openai: Cliente OpenAI para embeddings e chat.
        validator: Validador de citações jurídicas.
        db_pool: Pool de conexões PostgreSQL.
        model: Modelo OpenAI para geração.
    """

    # Thresholds dinâmicos por categoria (do PRD)
    THRESHOLDS = {
        "legal_legislacao": 0.85,  # Legislação exige alta precisão
        "legal_doutrina": 0.75,  # Doutrina permite paráfrase
        "legal_questoes": 0.80,  # Questões requer boa precisão
        "legal_jurisprudencia": 0.80,  # Jurisprudência exige citação exata
    }

    # Modelo embedding (mesmo do ingestor)
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(
        self,
        db_pool: AsyncPGPool | None = None,
        openai_client: AsyncOpenAI | None = None,
        model: str = "gpt-4o",
        temperature: float = 0.0,  # Zero para determinismo
    ) -> None:
        """Inicializa o StudyAgent.

        Args:
            db_pool: Pool de conexões PostgreSQL.
            openai_client: Cliente OpenAI (opcional, cria padrão se None).
            model: Modelo OpenAI para geração.
            temperature: Temperatura para geração (0.0 para máximo rigor).
        """
        settings = get_settings()
        self.openai = openai_client or AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.validator = get_citation_validator(strict_mode=True)
        self.db_pool = db_pool
        self.model = model
        self.temperature = temperature

    async def answer(
        self,
        request: StudyAgentRequest,
    ) -> StudyAgentResponse:
        """Processa uma pergunta de estudo com RAG rigoroso.

        Args:
            request: Request com pergunta, user_id e filtros.

        Returns:
            StudyAgentResponse com resposta, fontes e métricas.

        Raises:
            ValueError: Se db_pool não estiver configurado.
        """
        if self.db_pool is None:
            raise ValueError("Database pool not configured for StudyAgent")

        start_time = datetime.now(timezone.utc)

        # 1. Gerar embedding da pergunta
        question_embedding = await self._generate_embedding(request.question)

        # 2. Buscar documentos relevantes (RAG)
        rag_results = await self._search_archival_memories(
            question_embedding=question_embedding,
            user_id=request.user_id,
            category_filter=request.category_filter,
            max_results=request.max_results,
            threshold=request.threshold,
        )

        # 3. Verificar se há resultados suficientes
        if not rag_results:
            return StudyAgentResponse(
                answer=self._format_uncertainty_response(request.question),
                sources=[],
                confidence=0.0,
                uncertainty=True,
            )

        # 4. Extrair contexto dos resultados
        context = [r.content for r in rag_results]

        # 5. Gerar resposta com LLM (temperatura 0.0)
        raw_response = await self._generate_response(request.question, context)

        # 6. Validar citações
        validation = self.validator.validate_response(raw_response, context)

        # 7. Se inválido (citações não verificadas), retornar resposta de incerteza
        if not validation.is_valid:
            logger.warning(f"Validação falhou para pergunta: {request.question[:50]}...")
            return StudyAgentResponse(
                answer=self._format_uncertainty_response(
                    request.question, validation.warning_message
                ),
                sources=[r.source for r in rag_results],
                confidence=validation.confidence_score,
                uncertainty=True,
            )

        # 8. Formatar resposta final com fontes
        formatted_response = self._format_response_with_sources(
            raw_response, rag_results
        )

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            f"StudyAgent respondeu em {duration:.2f}s, "
            f"{len(rag_results)} fontes, confiança={validation.confidence_score:.2f}"
        )

        return StudyAgentResponse(
            answer=formatted_response,
            sources=[r.source for r in rag_results],
            confidence=validation.confidence_score,
            uncertainty=False,
        )

    async def _generate_embedding(self, text: str) -> list[float]:
        """Gera embedding OpenAI para um texto.

        Args:
            text: Texto para gerar embedding.

        Returns:
            Lista de 1536 floats (embedding).
        """
        try:
            response = await self.openai.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            raise

    async def _search_archival_memories(
        self,
        question_embedding: list[float],
        user_id: str,
        category_filter: str | None = None,
        max_results: int = 5,
        threshold: float = 0.7,
    ) -> list[RAGSearchResult]:
        """Busca memóries arquivadas por similaridade de cosseno.

        Args:
            question_embedding: Embedding da pergunta.
            user_id: ID do usuário.
            category_filter: Filtro opcional por categoria legal.
            max_results: Máximo de resultados.
            threshold: Threshold mínimo de similaridade.

        Returns:
            Lista de RAGSearchResult ordenados por similaridade.
        """
        if self.db_pool is None:
            return []

        # Construir query SQL com pgvector
        # Filtro por categorias legais se não especificado
        categories = (
            [category_filter] if category_filter else LEGAL_CATEGORIES
        )

        async with self.db_pool.acquire() as conn:  # type: ignore[union-attr]
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    content,
                    category,
                    archival_metadata,
                    1 - (embedding <=> $1::vector(1536)) AS similarity
                FROM archival_memories
                WHERE user_id = $2::uuid
                    AND category = ANY($3::text[])
                    AND 1 - (embedding <=> $1::vector(1536)) >= $4
                ORDER BY embedding <=> $1::vector(1536)
                LIMIT $5
                """,
                question_embedding,
                user_id,
                categories,
                threshold,
                max_results,
            )

        # Converter para RAGSearchResult
        results = []
        for row in rows:
            metadata = row["archival_metadata"] or {}
            results.append(
                RAGSearchResult(
                    content=row["content"],
                    similarity=float(row["similarity"]),
                    category=row["category"],
                    metadata=metadata,
                    source=metadata.get("fonte", "Fonte desconhecida"),
                )
            )

        logger.info(
            f"Busca RAG retornou {len(results)} resultados "
            f"(threshold={threshold}, max={max_results})"
        )

        return results

    async def _generate_response(
        self,
        question: str,
        context: list[str],
    ) -> str:
        """Gera resposta usando OpenAI chat.

        Args:
            question: Pergunta do usuário.
            context: Contexto RAG recuperado.

        Returns:
            Resposta gerada pelo LLM.
        """
        # Formatar contexto para o prompt
        context_text = "\n\n---\n\n".join(context)

        system_prompt = """Você é um assistente jurídico especializado em concursos públicos.

**REGRAS RIGOROSAS**:
1. Responda APENAS com base no contexto fornecido abaixo.
2. Se a informação não estiver no contexto, diga explicitamente que não sabe.
3. NUNCA invente artigos, leis, doutrina ou jurisprudência.
4. Cite SEMPRE a fonte quando usar informação do contexto.
5. Seja didático: explique de forma clara e objetiva.
6. Use formatação markdown para organizar a resposta.

**ESTRUTURA DA RESPOSTA**:
- Título em negrito com o tema
- Resposta direta (2-3 parágrafos)
- Seção "💡 Didática" para contexto adicional (opcional)
- Seção "📖 Fonte" com as referências usadas

**EXEMPLO**:
```markdown
📚 **Crime de Homicídio - Qualificadoras**

As qualificadoras do homicídio são circunstâncias que agravam a pena...

💡 **Didática**: Qualificadoras dividem-se em subjetivas (motivo) e objetivas (meio de execução).

📖 **Fonte**: Código Penal, Art. 121, §2º
```"""

        try:
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"""**CONTEXTO** (documentos jurídicos):
{context_text}

**PERGUNTA**: {question}

Responda com base apenas no contexto fornecido.""",
                    },
                ],
                temperature=self.temperature,
                max_tokens=2000,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}")
            raise

    def _format_response_with_sources(
        self,
        response: str,
        rag_results: list[RAGSearchResult],
    ) -> str:
        """Formata a resposta com lista de fontes.

        Args:
            response: Resposta bruta do LLM.
            rag_results: Resultados RAG usados.

        Returns:
            Resposta formatada com fontes.
        """
        # Se a resposta já tem seção de fonte, não duplicar
        if "📖 **Fonte**" in response or "Fonte:" in response:
            return response

        # Adicionar fontes ao final
        sources_set = {r.source for r in rag_results}
        sources_list = sorted(sources_set)

        if not sources_list:
            return response

        sources_section = "\n\n📖 **Fonte(s)**:\n" + "\n".join(f"- {s}" for s in sources_list)
        return response + sources_section

    def _format_uncertainty_response(
        self,
        question: str,
        warning: str | None = None,
    ) -> str:
        """Formata resposta de incerteza quando não encontra informação.

        Args:
            question: Pergunta do usuário.
            warning: Mensagem de aviso opcional.

        Returns:
            Resposta de incerteza formatada.
        """
        base_response = """❌ Não encontrei informação precisa na base de estudos para responder esta pergunta.

**Por que isso acontece?**
- A pergunta pode estar sobre um tema não coberto nos materiais ingeridos
- A informação pode estar em uma fonte diferente das categorias atuais
- A formulação da pergunta pode não ter retornado resultados com similaridade suficiente

**Sugestão**:
- Tente reformular a pergunta com termos mais específicos
- Consulte as fontes oficiais (legislação atualizada, doutrina reconhecida)
- Considere ingerir mais materiais sobre este tema"""

        if warning:
            return f"{base_response}\n\n{warning}"

        return base_response


# Singleton instance
_study_agent: StudyAgent | None = None


def get_study_agent(
    db_pool: AsyncPGPool | None = None,
    model: str = "gpt-4o",
    temperature: float = 0.0,
) -> StudyAgent:
    """Retorna instância singleton do StudyAgent.

    Args:
        db_pool: Pool de conexões PostgreSQL.
        model: Modelo OpenAI para geração.
        temperature: Temperatura para geração (0.0 para máximo rigor).

    Returns:
        Instância do StudyAgent.
    """
    global _study_agent

    if _study_agent is None:
        _study_agent = StudyAgent(
            db_pool=db_pool,
            model=model,
            temperature=temperature,
        )

    return _study_agent
