"""Serviço avançado de Knowledge Graph para Agnaldo.

Este módulo fornece funcionalidades avançadas de grafos:

- Extração automática de entidades de conversas
- Relacionamentos semânticos automáticos
- Consultas avançadas (subgraph, clustering, centralidade)
- Integração com sistema de isolamento
- Exportação para visualização
"""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from loguru import logger
from openai import AsyncOpenAI

from src.config.settings import get_settings
from src.exceptions import DatabaseError, MemoryServiceError
from src.knowledge.graph import KnowledgeEdge, KnowledgeNode, KnowledgeGraph
from src.memory.isolation import (
    MemoryIsolationGuard,
    get_isolation_guard,
    UserContext,
)


class EntityType(str, Enum):
    """Tipos de entidades extraídas."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    EVENT = "event"
    TOPIC = "topic"
    DOCUMENT = "document"
    LAW = "law"  # Para contexto jurídico
    CASE = "case"  # Para casos jurídicos
    SUBJECT = "subject"  # Matéria de concurso


class RelationType(str, Enum):
    """Tipos de relacionamentos."""

    RELATED_TO = "related_to"
    PART_OF = "part_of"
    HAS_PROPERTY = "has_property"
    MENTIONS = "mentions"
    STUDIES = "studies"
    KNOWS = "knows"
    WORKS_AT = "works_at"
    LOCATED_IN = "located_in"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    APPLIES = "applies"


@dataclass
class ExtractedEntity:
    """Entidade extraída de texto."""

    text: str
    entity_type: EntityType
    confidence: float
    properties: dict[str, Any] = field(default_factory=dict)
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass
class ExtractedRelation:
    """Relacionamento extraído de texto."""

    source: str
    target: str
    relation_type: RelationType
    confidence: float
    context: str | None = None


@runtime_checkable
class DatabasePool(Protocol):
    """Protocolo para pool de banco de dados."""

    async def acquire(self): ...

    async def execute(self, query: str, *args) -> str: ...

    async def fetchval(self, query: str, *args) -> Any: ...

    async def fetch(self, query: str, *args) -> list: ...

    async def fetchrow(self, query: str, *args) -> Any: ...


class GraphService:
    """Serviço avançado para operações de Knowledge Graph.

    Fornece:
    - Extração automática de entidades via LLM
    - Criação automática de relacionamentos
    - Consultas avançadas de grafo
    - Métricas de centralidade
    - Exportação para visualização
    """

    def __init__(
        self,
        user_id: str,
        db_pool: DatabasePool,
        openai_client: AsyncOpenAI | None = None,
        isolation_guard: MemoryIsolationGuard | None = None,
    ) -> None:
        """Inicializa o GraphService.

        Args:
            user_id: ID do usuário para isolamento.
            db_pool: Pool de conexão PostgreSQL.
            openai_client: Cliente OpenAI para extração de entidades.
            isolation_guard: Guarda de isolamento (usa global se None).
        """
        self._isolation_guard = isolation_guard or get_isolation_guard()
        self.user_id = self._isolation_guard.validate_user_id(user_id, "GraphService.__init__")

        self.db_pool = db_pool
        self._graph = KnowledgeGraph(
            user_id=self.user_id,
            repository=db_pool,
            openai_client=openai_client,
        )

        if openai_client is not None:
            self.openai = openai_client
        else:
            settings = get_settings()
            self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.extraction_model = "gpt-4o-mini"  # Modelo leve para extração

    async def extract_entities_from_text(
        self,
        text: str,
        context: str | None = None,
    ) -> list[ExtractedEntity]:
        """Extrai entidades de um texto usando LLM.

        Args:
            text: Texto para extrair entidades.
            context: Contexto adicional para ajudar na extração.

        Returns:
            Lista de entidades extraídas.
        """
        prompt = f"""Extraia entidades do texto a seguir.

Texto: {text}

{"Contexto adicional: " + context if context else ""}

Para cada entidade, retorne um JSON com:
- text: texto da entidade
- type: tipo (person, organization, location, concept, event, topic, document, law, case, subject)
- confidence: confiança de 0.0 a 1.0
- properties: propriedades adicionais (opcional)

Retorne APENAS um array JSON válido de entidades, sem texto adicional.
Exemplo: [{{"text": "João", "type": "person", "confidence": 0.9}}]
"""

        try:
            response = await self.openai.chat.completions.create(
                model=self.extraction_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            entities = []
            for item in data.get("entities", data if isinstance(data, list) else []):
                try:
                    entity_type = EntityType(item.get("type", "concept"))
                except ValueError:
                    entity_type = EntityType.CONCEPT

                entities.append(
                    ExtractedEntity(
                        text=item.get("text", ""),
                        entity_type=entity_type,
                        confidence=min(1.0, max(0.0, item.get("confidence", 0.5))),
                        properties=item.get("properties", {}),
                    )
                )

            logger.debug(f"Extraídas {len(entities)} entidades do texto")
            return entities

        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao decodificar resposta de extração: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro na extração de entidades: {e}")
            return []

    async def extract_relations_from_text(
        self,
        text: str,
        entities: list[ExtractedEntity] | None = None,
    ) -> list[ExtractedRelation]:
        """Extrai relacionamentos de um texto.

        Args:
            text: Texto para extrair relacionamentos.
            entities: Entidades já extraídas (opcional).

        Returns:
            Lista de relacionamentos extraídos.
        """
        entity_context = ""
        if entities:
            entity_names = [e.text for e in entities[:10]]  # Limitar para prompt
            entity_context = f"Entidades conhecidas: {', '.join(entity_names)}"

        prompt = f"""Identifique relacionamentos entre entidades no texto.

Texto: {text}

{entity_context}

Para cada relacionamento, retorne um JSON com:
- source: entidade de origem
- target: entidade de destino
- relation: tipo (related_to, part_of, has_property, mentions, studies, knows, works_at, located_in, precedes, follows, depends_on, references, applies)
- confidence: confiança de 0.0 a 1.0
- context: trecho do texto que indica o relacionamento (opcional)

Retorne APENAS um array JSON válido.
Exemplo: [{{"source": "João", "target": "Direito Constitucional", "relation": "studies", "confidence": 0.85}}]
"""

        try:
            response = await self.openai.chat.completions.create(
                model=self.extraction_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            relations = []
            for item in data.get("relations", data if isinstance(data, list) else []):
                try:
                    relation_type = RelationType(item.get("relation", "related_to"))
                except ValueError:
                    relation_type = RelationType.RELATED_TO

                relations.append(
                    ExtractedRelation(
                        source=item.get("source", ""),
                        target=item.get("target", ""),
                        relation_type=relation_type,
                        confidence=min(1.0, max(0.0, item.get("confidence", 0.5))),
                        context=item.get("context"),
                    )
                )

            logger.debug(f"Extraídos {len(relations)} relacionamentos do texto")
            return relations

        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao decodificar resposta de relacionamentos: {e}")
            return []
        except Exception as e:
            logger.error(f"Erro na extração de relacionamentos: {e}")
            return []

    async def add_conversation_to_graph(
        self,
        user_message: str,
        assistant_response: str,
        session_id: str | None = None,
        auto_extract: bool = True,
    ) -> dict[str, Any]:
        """Adiciona uma conversa ao grafo extraindo entidades e relacionamentos.

        Args:
            user_message: Mensagem do usuário.
            assistant_response: Resposta do assistente.
            session_id: ID da sessão (opcional).
            auto_extract: Se deve extrair entidades automaticamente.

        Returns:
            Dict com nós e arestas criados.
        """
        result = {
            "nodes_created": 0,
            "edges_created": 0,
            "entities": [],
            "relations": [],
        }

        if not auto_extract:
            return result

        full_text = f"User: {user_message}\nAssistant: {assistant_response}"

        try:
            # Extrair entidades
            entities = await self.extract_entities_from_text(
                text=full_text,
                context=f"Sessão: {session_id}" if session_id else None,
            )

            # Criar nós para entidades
            node_ids: dict[str, str] = {}
            for entity in entities:
                try:
                    node = await self._graph.add_node(
                        label=entity.text,
                        node_type=entity.entity_type.value,
                        properties={
                            **entity.properties,
                            "confidence": entity.confidence,
                            "session_id": session_id,
                            "source": "conversation",
                        },
                        generate_embedding=True,
                    )
                    node_ids[entity.text] = node.id
                    result["nodes_created"] += 1
                except Exception as e:
                    logger.debug(f"Erro ao criar nó para {entity.text}: {e}")

            # Extrair relacionamentos
            relations = await self.extract_relations_from_text(full_text, entities)

            # Criar arestas
            for relation in relations:
                source_id = node_ids.get(relation.source)
                target_id = node_ids.get(relation.target)

                if source_id and target_id:
                    try:
                        await self._graph.add_edge(
                            source_id=source_id,
                            target_id=target_id,
                            edge_type=relation.relation_type.value,
                            weight=relation.confidence,
                            properties={
                                "context": relation.context,
                                "session_id": session_id,
                            },
                        )
                        result["edges_created"] += 1
                    except Exception as e:
                        logger.debug(f"Erro ao criar aresta: {e}")

            result["entities"] = [
                {"text": e.text, "type": e.entity_type.value, "confidence": e.confidence}
                for e in entities
            ]
            result["relations"] = [
                {
                    "source": r.source,
                    "target": r.target,
                    "type": r.relation_type.value,
                    "confidence": r.confidence,
                }
                for r in relations
            ]

            logger.info(
                f"Grafo atualizado: {result['nodes_created']} nós, {result['edges_created']} arestas"
            )

        except Exception as e:
            logger.error(f"Erro ao adicionar conversa ao grafo: {e}")

        return result

    async def get_subgraph(
        self,
        node_id: str,
        depth: int = 2,
        max_nodes: int = 50,
    ) -> dict[str, Any]:
        """Obtém um subgrafo centrado em um nó.

        Args:
            node_id: ID do nó central.
            depth: Profundidade da expansão.
            max_nodes: Máximo de nós a retornar.

        Returns:
            Dict com nós e arestas do subgrafo.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Recursive CTE para expandir o grafo
                rows = await conn.fetch(
                    """
                    WITH RECURSIVE subgraph AS (
                        -- Nó inicial
                        SELECT id, label, node_type, properties, 0 as depth
                        FROM knowledge_nodes
                        WHERE id = $1::uuid AND user_id = $2

                        UNION ALL

                        -- Nós vizinhos
                        SELECT DISTINCT n.id, n.label, n.node_type, n.properties, s.depth + 1
                        FROM knowledge_nodes n
                        JOIN knowledge_edges e ON (
                            (e.source_id = s.id AND e.target_id = n.id) OR
                            (e.target_id = s.id AND e.source_id = n.id)
                        )
                        JOIN subgraph s ON s.id = e.source_id OR s.id = e.target_id
                        WHERE n.user_id = $2
                            AND s.depth < $3
                    )
                    SELECT DISTINCT id, label, node_type, properties
                    FROM subgraph
                    LIMIT $4
                    """,
                    node_id,
                    self.user_id,
                    depth,
                    max_nodes,
                )

                nodes = [dict(row) for row in rows]
                node_ids = [row["id"] for row in rows]

                # Obter arestas entre os nós
                edge_rows = await conn.fetch(
                    """
                    SELECT e.id, e.source_id, e.target_id, e.edge_type, e.weight, e.properties
                    FROM knowledge_edges e
                    WHERE e.source_id = ANY($1::uuid[])
                        AND e.target_id = ANY($1::uuid[])
                    """,
                    node_ids,
                )

                edges = [
                    {
                        "id": str(row["id"]),
                        "source": str(row["source_id"]),
                        "target": str(row["target_id"]),
                        "type": row["edge_type"],
                        "weight": row["weight"],
                    }
                    for row in edge_rows
                ]

                return {
                    "nodes": [
                        {
                            "id": str(n["id"]),
                            "label": n["label"],
                            "type": n["node_type"],
                            "properties": n["properties"],
                        }
                        for n in nodes
                    ],
                    "edges": edges,
                }

        except Exception as e:
            raise DatabaseError(f"Erro ao obter subgrafo: {e}", operation="query") from e

    async def get_central_nodes(
        self,
        metric: str = "degree",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Obtém nós mais centrais por métrica.

        Args:
            metric: Métrica de centralidade (degree, betweenness, closeness).
            limit: Máximo de nós a retornar.

        Returns:
            Lista de nós com scores de centralidade.
        """
        try:
            async with self.db_pool.acquire() as conn:
                if metric == "degree":
                    # Centralidade de grau (número de conexões)
                    rows = await conn.fetch(
                        """
                        SELECT
                            n.id, n.label, n.node_type,
                            COUNT(e.id) as degree
                        FROM knowledge_nodes n
                        LEFT JOIN knowledge_edges e ON (
                            e.source_id = n.id OR e.target_id = n.id
                        )
                        WHERE n.user_id = $1
                        GROUP BY n.id, n.label, n.node_type
                        ORDER BY degree DESC
                        LIMIT $2
                        """,
                        self.user_id,
                        limit,
                    )
                elif metric == "betweenness":
                    # Aproximação de betweenness por caminhos mais curtos
                    rows = await conn.fetch(
                        """
                        WITH paths AS (
                            SELECT DISTINCT
                                CASE WHEN e.source_id < e.target_id
                                    THEN e.source_id ELSE e.target_id END as node1,
                                CASE WHEN e.source_id < e.target_id
                                    THEN e.target_id ELSE e.source_id END as node2
                            FROM knowledge_edges e
                            JOIN knowledge_nodes n ON e.source_id = n.id
                            WHERE n.user_id = $1
                        )
                        SELECT
                            n.id, n.label, n.node_type,
                            COUNT(*) as betweenness
                        FROM knowledge_nodes n
                        JOIN paths p ON n.id = p.node1 OR n.id = p.node2
                        WHERE n.user_id = $1
                        GROUP BY n.id, n.label, n.node_type
                        ORDER BY betweenness DESC
                        LIMIT $2
                        """,
                        self.user_id,
                        limit,
                    )
                else:
                    # Default: degree centrality
                    rows = await conn.fetch(
                        """
                        SELECT n.id, n.label, n.node_type, 0 as score
                        FROM knowledge_nodes n
                        WHERE n.user_id = $1
                        LIMIT $2
                        """,
                        self.user_id,
                        limit,
                    )

                return [
                    {
                        "id": str(row["id"]),
                        "label": row["label"],
                        "type": row["node_type"],
                        "score": row.get("degree", row.get("betweenness", 0)),
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Erro ao calcular centralidade: {e}")
            return []

    async def find_clusters(
        self,
        min_size: int = 3,
    ) -> list[dict[str, Any]]:
        """Identifica clusters de nós fortemente conectados.

        Args:
            min_size: Tamanho mínimo de cluster.

        Returns:
            Lista de clusters com seus nós.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Usar connected components via BFS
                rows = await conn.fetch(
                    """
                    WITH RECURSIVE components AS (
                        -- Inicializar cada nó como seu próprio componente
                        SELECT id as node_id, id as component_id
                        FROM knowledge_nodes
                        WHERE user_id = $1

                        UNION

                        -- Propagar componente mínimo
                        SELECT
                            n.id as node_id,
                            LEAST(c.component_id, n.id) as component_id
                        FROM knowledge_nodes n
                        JOIN knowledge_edges e ON (
                            e.source_id = n.id OR e.target_id = n.id
                        )
                        JOIN components c ON (
                            c.node_id = e.source_id OR c.node_id = e.target_id
                        )
                        WHERE n.user_id = $1
                    )
                    SELECT
                        component_id,
                        array_agg(node_id) as nodes,
                        COUNT(*) as size
                    FROM components
                    GROUP BY component_id
                    HAVING COUNT(*) >= $2
                    ORDER BY size DESC
                    """,
                    self.user_id,
                    min_size,
                )

                clusters = []
                for row in rows:
                    # Obter detalhes dos nós
                    node_rows = await conn.fetch(
                        """
                        SELECT id, label, node_type
                        FROM knowledge_nodes
                        WHERE id = ANY($1::uuid[])
                        """,
                        row["nodes"],
                    )

                    clusters.append(
                        {
                            "component_id": str(row["component_id"]),
                            "size": row["size"],
                            "nodes": [
                                {"id": str(n["id"]), "label": n["label"], "type": n["node_type"]}
                                for n in node_rows
                            ],
                        }
                    )

                return clusters

        except Exception as e:
            logger.error(f"Erro ao encontrar clusters: {e}")
            return []

    async def export_graph(
        self,
        format: str = "json",
        include_properties: bool = True,
    ) -> str | dict[str, Any]:
        """Exporta o grafo para visualização.

        Args:
            format: Formato de exportação (json, d3, cytoscape, graphml).
            include_properties: Se deve incluir propriedades.

        Returns:
            Grafo no formato especificado.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Obter todos os nós
                node_rows = await conn.fetch(
                    """
                    SELECT id, label, node_type, properties, created_at
                    FROM knowledge_nodes
                    WHERE user_id = $1
                    ORDER BY label
                    """,
                    self.user_id,
                )

                # Obter todas as arestas
                edge_rows = await conn.fetch(
                    """
                    SELECT e.id, e.source_id, e.target_id, e.edge_type, e.weight, e.properties
                    FROM knowledge_edges e
                    JOIN knowledge_nodes n ON e.source_id = n.id
                    WHERE n.user_id = $1
                    """,
                    self.user_id,
                )

            if format == "json" or format == "d3":
                # Formato D3.js
                return {
                    "nodes": [
                        {
                            "id": str(row["id"]),
                            "label": row["label"],
                            "type": row["node_type"],
                            **(
                                {"properties": row["properties"], "created_at": row["created_at"].isoformat()}
                                if include_properties
                                else {}
                            ),
                        }
                        for row in node_rows
                    ],
                    "links": [
                        {
                            "source": str(row["source_id"]),
                            "target": str(row["target_id"]),
                            "type": row["edge_type"],
                            "weight": row["weight"],
                            **({"properties": row["properties"]} if include_properties else {}),
                        }
                        for row in edge_rows
                    ],
                }

            elif format == "cytoscape":
                # Formato Cytoscape.js
                return {
                    "elements": {
                        "nodes": [
                            {
                                "data": {
                                    "id": str(row["id"]),
                                    "label": row["label"],
                                    "type": row["node_type"],
                                }
                            }
                            for row in node_rows
                        ],
                        "edges": [
                            {
                                "data": {
                                    "id": str(row["id"]),
                                    "source": str(row["source_id"]),
                                    "target": str(row["target_id"]),
                                    "label": row["edge_type"],
                                }
                            }
                            for row in edge_rows
                        ],
                    }
                }

            elif format == "graphml":
                # GraphML para ferramentas como Gephi
                lines = [
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
                    '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
                    '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
                    '  <key id="edge_type" for="edge" attr.name="type" attr.type="string"/>',
                    '  <key id="weight" for="edge" attr.name="weight" attr.type="double"/>',
                    '  <graph id="G" edgedefault="directed">',
                ]

                for row in node_rows:
                    lines.append(
                        f'    <node id="{row["id"]}">'
                        f'<data key="label">{row["label"]}</data>'
                        f'<data key="type">{row["node_type"]}</data>'
                        f'</node>'
                    )

                for row in edge_rows:
                    lines.append(
                        f'    <edge source="{row["source_id"]}" target="{row["target_id"]}">'
                        f'<data key="edge_type">{row["edge_type"]}</data>'
                        f'<data key="weight">{row["weight"]}</data>'
                        f'</edge>'
                    )

                lines.extend(["  </graph>", "</graphml>"])
                return "\n".join(lines)

            else:
                raise ValueError(f"Formato não suportado: {format}")

        except Exception as e:
            raise DatabaseError(f"Erro ao exportar grafo: {e}", operation="export") from e

    async def semantic_search(
        self,
        query: str,
        include_context: bool = True,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Busca semântica com contexto de vizinhos.

        Args:
            query: Query de busca.
            include_context: Se deve incluir nós vizinhos.
            limit: Máximo de resultados.

        Returns:
            Lista de resultados com contexto.
        """
        try:
            # Buscar nós por similaridade
            nodes = await self._graph.search_nodes(query=query, limit=limit, threshold=0.5)

            if not include_context:
                return nodes

            # Enriquecer com contexto de vizinhos
            enriched = []
            for node in nodes:
                neighbors = await self._graph.get_neighbors(
                    node_id=node["node_id"],
                    direction="both",
                )

                enriched.append(
                    {
                        **node,
                        "neighbors": [
                            {"id": str(n.id), "label": n.label, "type": n.node_type}
                            for n in neighbors[:5]  # Limitar vizinhos
                        ],
                        "neighbor_count": len(neighbors),
                    }
                )

            return enriched

        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []

    async def get_graph_summary(self) -> dict[str, Any]:
        """Obtém resumo estatístico do grafo.

        Returns:
            Dict com estatísticas do grafo.
        """
        try:
            stats = await self._graph.get_stats()

            # Adicionar métricas extras
            central_nodes = await self.get_central_nodes(limit=5)
            clusters = await self.find_clusters(min_size=2)

            return {
                **stats,
                "top_nodes": central_nodes,
                "cluster_count": len(clusters),
                "clusters": clusters[:5],  # Top 5 clusters
            }

        except Exception as e:
            logger.error(f"Erro ao obter resumo do grafo: {e}")
            return {"error": str(e)}
