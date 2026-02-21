"""Gerenciador de Memória Unificado para Agnaldo.

Este módulo fornece uma fachada unificada para gerenciar os três tiers de memória
(Núcleo, Recordação, Arquivo) e integração com o Grafo de Conhecimento.

Funcionalidades:
- Interface unificada para todos os tiers de memória
- Recuperação automática de contexto para prompts
- Seleção baseada em prioridade
- Integração com grafo de conhecimento
- Gerenciamento de orçamento de tokens
"""

import asyncio
import hashlib
from typing import Any

from loguru import logger
from openai import AsyncOpenAI
from tiktoken import encoding_for_model

from src.exceptions import DatabaseError, MemoryServiceError
from src.knowledge.graph import KnowledgeGraph
from src.memory.archival import ArchivalMemory
from src.memory.core import CoreMemory
from src.memory.recall import RecallMemory
from src.schemas.memory import MemoryStats

# Tabelas permitidas para consulta de contagem (prevenção de SQL injection)
_ALLOWED_COUNT_TABLES = frozenset({"recall_memories", "archival_memories"})


def redact_user_id(user_id: str) -> str:
    """Retorna uma representação não reversível do user_id para uso em logs.

    Args:
        user_id: Identificador original do usuário.

    Returns:
        Prefixo de 8 caracteres do hash SHA-256 do user_id.
    """
    return "user:" + hashlib.sha256(user_id.encode()).hexdigest()[:8]


class MemoryContext:
    """Objeto de contexto contendo memórias recuperadas de todos os tiers.

    Attributes:
        core: Pares chave-valor da memória core.
        recall: Memórias recentes obtidas por busca semântica.
        archival: Memórias históricas obtidas por busca de metadados.
        graph: Nós e relacionamentos do grafo de conhecimento.
        total_tokens: Total de tokens no contexto.
    """

    def __init__(self) -> None:
        """Inicializa contexto vazio."""
        self.core: dict[str, str] = {}
        self.recall: list[dict[str, Any]] = []
        self.archival: list[dict[str, Any]] = []
        self.graph: list[dict[str, Any]] = []
        self.total_tokens: int = 0

        # Encoder tiktoken para contagem exata de tokens
        try:
            self._encoding = encoding_for_model("gpt-4o")
        except Exception:
            import tiktoken

            self._encoding = tiktoken.get_encoding("cl100k_base")

    def to_prompt_section(self, max_tokens: int = 1500) -> str:
        """Converte o contexto em uma seção de prompt.

        Args:
            max_tokens: Número máximo de tokens a incluir.

        Returns:
            String formatada para injeção no prompt.
        """
        sections = []
        current_tokens = 0

        # Memória Core - Incluir sempre que disponível
        if self.core:
            core_text = "## Fatos Importantes\n"
            for key, value in self.core.items():
                line = f"- {key}: {value}\n"
                line_tokens = len(self._encoding.encode(line))
                if current_tokens + line_tokens > max_tokens:
                    break
                core_text += line
                current_tokens += line_tokens
            sections.append(core_text)

        # Memória Recall - Conversas recentes relevantes
        if self.recall and current_tokens < max_tokens:
            recall_text = "## Conversas Relevantes\n"
            for item in self.recall:
                content = item.get("content", "")
                similarity = item.get("similarity", 0)
                line = (
                    f"- [Relevância: {similarity:.0%}] "
                    f"{content[:200]}{'...' if len(content) > 200 else ''}\n"
                )
                line_tokens = len(self._encoding.encode(line))
                if current_tokens + line_tokens > max_tokens:
                    break
                recall_text += line
                current_tokens += line_tokens
            if len(recall_text) > 30:  # Mais do que apenas o cabeçalho
                sections.append(recall_text)

        # Grafo de Conhecimento - Conceitos relacionados
        if self.graph and current_tokens < max_tokens:
            graph_text = "## Conhecimentos Relacionados\n"
            for item in self.graph:
                label = item.get("label", "")
                node_type = item.get("node_type", "")
                similarity = item.get("similarity", 0)
                line = f"- {label} ({node_type}) [Similaridade: {similarity:.0%}]\n"
                line_tokens = len(self._encoding.encode(line))
                if current_tokens + line_tokens > max_tokens:
                    break
                graph_text += line
                current_tokens += line_tokens
            if len(graph_text) > 35:  # Mais do que apenas o cabeçalho
                sections.append(graph_text)

        # Memória Archival - Contexto histórico (prioridade mais baixa)
        if self.archival and current_tokens < max_tokens * 0.8:  # Utilizar apenas 80% do orçamento
            archival_text = "## Histórico Relevante\n"
            for item in self.archival:
                content = item.get("content", "")
                source = item.get("source", "unknown")
                line = f"- [{source}] {content[:150]}{'...' if len(content) > 150 else ''}\n"
                line_tokens = len(self._encoding.encode(line))
                if current_tokens + line_tokens > max_tokens:
                    break
                archival_text += line
                current_tokens += line_tokens
            if len(archival_text) > 25:  # Mais do que apenas o cabeçalho
                sections.append(archival_text)

        if not sections:
            return ""

        return "\n".join(sections)


class MemoryManager:
    """Gerenciador unificado para todos os tiers de memória e grafo de conhecimento.

    Fornece uma interface única para operações de memória e recuperação
    automática de contexto com gerenciamento de orçamento de tokens.
    """

    def __init__(
        self,
        user_id: str,
        db_pool,
        openai_client: AsyncOpenAI | None = None,
        core_max_items: int = 100,
        core_max_tokens: int = 10000,
        recall_search_limit: int = 5,
        recall_similarity_threshold: float = 0.6,
        archival_search_limit: int = 3,
        graph_search_limit: int = 5,
        graph_similarity_threshold: float = 0.7,
        context_max_tokens: int = 1500,
    ) -> None:
        """Inicializa o Gerenciador de Memória.

        Args:
            user_id: Identificador do usuário para isolamento de memória.
            db_pool: Pool de conexão com o banco de dados (asyncpg).
            openai_client: Cliente OpenAI para geração de embeddings.
            core_max_items: Número máximo de itens na memória core.
            core_max_tokens: Número máximo de tokens na memória core.
            recall_search_limit: Número máximo de resultados a recuperar da recall.
            recall_similarity_threshold: Similaridade mínima para busca recall.
            archival_search_limit: Número máximo de resultados a recuperar do archival.
            graph_search_limit: Número máximo de nós a recuperar do grafo.
            graph_similarity_threshold: Similaridade mínima para busca no grafo.
            context_max_tokens: Número máximo de tokens no contexto gerado.
        """
        self.user_id = user_id
        self.db_pool = db_pool
        self.openai = openai_client

        # Configuração dos tiers de memória
        self.core_max_items = core_max_items
        self.core_max_tokens = core_max_tokens
        self.recall_search_limit = recall_search_limit
        self.recall_similarity_threshold = recall_similarity_threshold
        self.archival_search_limit = archival_search_limit
        self.graph_search_limit = graph_search_limit
        self.graph_similarity_threshold = graph_similarity_threshold
        self.context_max_tokens = context_max_tokens

        # Instâncias de memória com carregamento lazy
        self._core: CoreMemory | None = None
        self._recall: RecallMemory | None = None
        self._archival: ArchivalMemory | None = None
        self._graph: KnowledgeGraph | None = None

        logger.debug(f"MemoryManager inicializado para {redact_user_id(user_id)}")

    @property
    def core(self) -> CoreMemory:
        """Obtém ou cria instância de CoreMemory."""
        if self._core is None:
            self._core = CoreMemory(
                user_id=self.user_id,
                repository=self.db_pool,
                max_items=self.core_max_items,
                max_tokens=self.core_max_tokens,
            )
        return self._core

    @property
    def recall(self) -> RecallMemory:
        """Obtém ou cria instância de RecallMemory."""
        if self._recall is None:
            self._recall = RecallMemory(
                user_id=self.user_id,
                repository=self.db_pool,
                openai_client=self.openai,
            )
        return self._recall

    @property
    def archival(self) -> ArchivalMemory:
        """Obtém ou cria instância de ArchivalMemory."""
        if self._archival is None:
            self._archival = ArchivalMemory(
                user_id=self.user_id,
                repository=self.db_pool,
            )
        return self._archival

    @property
    def graph(self) -> KnowledgeGraph:
        """Obtém ou cria instância de KnowledgeGraph."""
        if self._graph is None:
            self._graph = KnowledgeGraph(
                user_id=self.user_id,
                repository=self.db_pool,
                openai_client=self.openai,
            )
        return self._graph

    async def retrieve_context(
        self,
        query: str,
        include_core: bool = True,
        include_recall: bool = True,
        include_archival: bool = False,
        include_graph: bool = True,
        extracted_topics: list[str] | None = None,
    ) -> MemoryContext:
        """Recupera contexto de todos os tiers de memória para injeção no prompt.

        Args:
            query: Consulta do usuário para busca de contexto relevante.
            include_core: Se deve incluir a memória core.
            include_recall: Se deve incluir busca na memória recall.
            include_archival: Se deve incluir busca na memória archival.
            include_graph: Se deve incluir busca no grafo de conhecimento.
            extracted_topics: Lista opcional de tópicos extraídos para busca direcionada.

        Returns:
            Objeto MemoryContext com as memórias recuperadas.
        """
        context = MemoryContext()

        try:
            # Executar buscas em paralelo para eficiência
            tasks = []

            if include_core:
                tasks.append(self._retrieve_core_context(context))

            if include_recall:
                tasks.append(self._retrieve_recall_context(query, context))

            if include_archival and extracted_topics:
                tasks.append(self._retrieve_archival_context(extracted_topics, context))

            if include_graph:
                tasks.append(self._retrieve_graph_context(query, context))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # Registrar e repassar exceções para não suprimir silenciosamente
                first_exc: Exception | None = None
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning(
                            f"Falha em sub-tarefa de recuperação de contexto: {result}"
                        )
                        if first_exc is None:
                            first_exc = result
                if first_exc is not None:
                    raise first_exc

            logger.info(
                f"Contexto recuperado: core={len(context.core)}, "
                f"recall={len(context.recall)}, archival={len(context.archival)}, "
                f"graph={len(context.graph)}"
            )

        except Exception as e:
            logger.warning(f"Falha ao recuperar contexto completo: {e}")

        return context

    async def _retrieve_core_context(self, context: MemoryContext) -> None:
        """Recupera contexto da memória core."""
        try:
            context.core = await self.core.get_all()
        except Exception as e:
            logger.warning(f"Falha ao recuperar memória core: {e}")

    async def _retrieve_recall_context(self, query: str, context: MemoryContext) -> None:
        """Recupera contexto da memória recall via busca semântica."""
        try:
            results = await self.recall.search(
                query=query,
                limit=self.recall_search_limit,
                threshold=self.recall_similarity_threshold,
            )
            context.recall = results
        except Exception as e:
            logger.warning(f"Falha ao recuperar memória recall: {e}")

    async def _retrieve_archival_context(
        self, topics: list[str], context: MemoryContext
    ) -> None:
        """Recupera contexto da memória archival por metadados e conteúdo em paralelo."""
        try:
            # Criar tarefas para busca por metadados dos dois primeiros tópicos e por conteúdo
            gather_tasks = []
            for topic in topics[:2]:
                gather_tasks.append(
                    self.archival.search_by_metadata(
                        filters={"topic": topic},
                        limit=self.archival_search_limit,
                    )
                )
            if topics:
                # Busca por conteúdo usando o primeiro tópico
                gather_tasks.append(
                    self.archival.search_by_content(
                        query=topics[0],
                        limit=self.archival_search_limit,
                    )
                )

            # Executar todas as buscas archival em paralelo
            all_results = await asyncio.gather(*gather_tasks, return_exceptions=True)

            # Mesclar resultados deduplicando por memory_id
            existing_ids: set[str | None] = set()
            for result in all_results:
                if isinstance(result, Exception):
                    logger.warning(f"Falha em busca archival: {result}")
                    continue
                for item in result:
                    memory_id = item.get("memory_id")
                    if memory_id not in existing_ids:
                        existing_ids.add(memory_id)
                        context.archival.append(item)

        except Exception as e:
            logger.warning(f"Falha ao recuperar memória archival: {e}")

    async def _retrieve_graph_context(self, query: str, context: MemoryContext) -> None:
        """Recupera contexto do grafo de conhecimento."""
        try:
            results = await self.graph.search_nodes(
                query=query,
                limit=self.graph_search_limit,
                threshold=self.graph_similarity_threshold,
            )
            context.graph = results
        except Exception as e:
            logger.warning(f"Falha ao recuperar contexto do grafo: {e}")

    async def store_interaction(
        self,
        user_message: str,
        assistant_response: str,
        importance: float = 0.5,
        store_in_recall: bool = True,
        store_in_graph: bool = False,
        extract_entities: bool = False,
    ) -> dict[str, Any]:
        """Armazena uma interação nos tiers de memória apropriados.

        Args:
            user_message: Mensagem do usuário.
            assistant_response: Resposta do assistente.
            importance: Pontuação de importância (0.0-1.0).
            store_in_recall: Se deve armazenar na memória recall.
            store_in_graph: Se deve extrair e armazenar entidades no grafo.
            extract_entities: Se deve extrair entidades (requer LLM).

        Returns:
            Dict com IDs das memórias criadas.
        """
        result: dict[str, Any] = {
            "recall_id": None,
            "graph_nodes": [],
        }

        try:
            # Armazenar na memória recall
            if store_in_recall:
                content = f"User: {user_message}\nAssistant: {assistant_response}"
                result["recall_id"] = await self.recall.add(
                    content=content,
                    importance=importance,
                )

            # Extrair entidades e armazenar no grafo de conhecimento
            if store_in_graph and extract_entities:
                # Nota: Extração de entidades requer chamada LLM
                # Placeholder para implementação futura
                logger.debug(
                    "Extração de entidades para armazenamento no grafo ainda não implementada"
                )

        except Exception as e:
            logger.warning(f"Falha ao armazenar interação: {e}")

        return result

    async def store_core_fact(
        self,
        key: str,
        value: str,
        importance: float = 0.7,
    ) -> str | None:
        """Armazena um fato na memória core.

        Args:
            key: Chave única para o fato.
            value: Valor do fato.
            importance: Pontuação de importância (0.0-1.0).

        Returns:
            ID da memória ou None em caso de falha.
        """
        try:
            item = await self.core.add(key, value, importance=importance)
            return item.id
        except Exception as e:
            logger.warning(f"Falha ao armazenar fato core: {e}")
            return None

    async def get_stats(self) -> MemoryStats:
        """Obtém estatísticas de todos os tiers de memória.

        Returns:
            Objeto MemoryStats com contagens e estimativas de tokens.
        """
        try:
            # Obter estatísticas do tier core
            core_stats = await self.core.get_stats()

            # Recall e archival não possuem get_stats; estimar via banco de dados
            recall_count = await self._count_table("recall_memories")
            archival_count = await self._count_table("archival_memories")

            # Estimativa de tokens por tier com base na contagem de itens
            core_tokens = core_stats.get("avg_tokens_per_item", 50) * core_stats.get(
                "item_count", 0
            )
            recall_tokens = recall_count * 100  # Média estimada de 100 tokens por memória recall
            archival_tokens = archival_count * 200  # Média estimada de 200 tokens por memória archival

            return MemoryStats(
                core_count=core_stats.get("item_count", 0),
                recall_count=recall_count,
                archival_count=archival_count,
                total_count=core_stats.get("item_count", 0) + recall_count + archival_count,
                core_tokens=core_tokens,
                recall_tokens=recall_tokens,
                archival_tokens=archival_tokens,
                total_tokens=core_tokens + recall_tokens + archival_tokens,
            )

        except Exception as e:
            logger.warning(f"Falha ao obter estatísticas de memória: {e}")
            return MemoryStats()

    async def _count_table(self, table_name: str) -> int:
        """Conta registros em uma tabela para o usuário atual.

        Valida o nome da tabela contra uma lista de permissão para
        prevenir SQL injection.

        Args:
            table_name: Nome da tabela a contar (deve estar na lista de permissão).

        Returns:
            Número de registros encontrados ou 0 em caso de erro ou tabela não permitida.
        """
        if table_name not in _ALLOWED_COUNT_TABLES:
            logger.warning(
                f"Tentativa de consulta em tabela não permitida: {table_name!r}. "
                f"Permitidas: {sorted(_ALLOWED_COUNT_TABLES)}"
            )
            return 0

        try:
            async with self.db_pool.acquire() as conn:
                count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table_name} WHERE user_id = $1",
                    self.user_id,
                )
                return count or 0
        except Exception as e:
            logger.warning(f"Falha ao contar registros em {table_name}: {e}")
            return 0

    async def compress_session(
        self, session_id: str, summary: str | None = None
    ) -> dict[str, Any]:
        """Comprime todas as memórias de uma sessão na memória archival.

        Args:
            session_id: Identificador da sessão.
            summary: Resumo pré-gerado opcional.

        Returns:
            Resultado da compressão com estatísticas.
        """
        try:
            result = await self.archival.compress(session_id, summary)
            logger.info(f"Sessão {session_id} comprimida: {result}")
            return result
        except Exception as e:
            logger.warning(f"Falha ao comprimir sessão: {e}")
            return {"compressed_memory_id": None, "original_count": 0, "compressed_count": 0}

    async def clear_all(self, confirm: bool = False) -> int:
        """Limpa todas as memórias do usuário em todos os tiers.

        Args:
            confirm: Deve ser True para efetuar a limpeza.

        Returns:
            Total de itens removidos.

        Warning:
            Esta é uma operação destrutiva!
        """
        if not confirm:
            raise MemoryServiceError(
                "Must pass confirm=True to clear all memories",
                memory_type="all",
            )

        total_cleared = 0

        try:
            # Limpar tier core
            total_cleared += await self.core.clear()

            # Limpar recall e archival via operações diretas no banco de dados
            async with self.db_pool.acquire() as conn:
                # Deletar memórias recall; asyncpg retorna status "DELETE N"
                recall_status = await conn.execute(
                    "DELETE FROM recall_memories WHERE user_id = $1",
                    self.user_id,
                )
                recall_count = int(recall_status.split()[-1])
                total_cleared += recall_count

                archival_status = await conn.execute(
                    "DELETE FROM archival_memories WHERE user_id = $1",
                    self.user_id,
                )
                archival_count = int(archival_status.split()[-1])
                total_cleared += archival_count

                # Limpar nós do grafo (arestas são removidas em cascata)
                graph_status = await conn.execute(
                    "DELETE FROM knowledge_nodes WHERE user_id = $1",
                    self.user_id,
                )
                graph_count = int(graph_status.split()[-1])
                total_cleared += graph_count

            logger.warning(
                f"Removidas {total_cleared} memórias para {redact_user_id(self.user_id)}"
            )
            return total_cleared

        except Exception as e:
            raise DatabaseError(f"Falha ao limpar memórias: {e}", operation="delete") from e
