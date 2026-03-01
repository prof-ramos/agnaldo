"""Testes para o GraphService."""

from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.exceptions import DatabaseError
from src.knowledge.graph_service import (
    EntityType,
    ExtractedEntity,
    ExtractedRelation,
    GraphService,
    RelationType,
)

# Constante fixa para garantir determinismo nos testes
FIXED_DATETIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TestExtractedEntity:
    """Testes para ExtractedEntity."""

    def test_create_entity(self):
        """Cria entidade com valores padrão."""
        entity = ExtractedEntity(
            text="Direito Constitucional",
            entity_type=EntityType.CONCEPT,
            confidence=0.9,
        )
        assert entity.text == "Direito Constitucional"
        assert entity.entity_type == EntityType.CONCEPT
        assert entity.confidence == 0.9
        assert entity.properties == {}

    def test_create_entity_with_properties(self):
        """Cria entidade com propriedades."""
        entity = ExtractedEntity(
            text="STF",
            entity_type=EntityType.ORGANIZATION,
            confidence=0.95,
            properties={"country": "Brasil", "full_name": "Supremo Tribunal Federal"},
        )
        assert entity.properties["country"] == "Brasil"
        assert entity.properties["full_name"] == "Supremo Tribunal Federal"


class TestExtractedRelation:
    """Testes para ExtractedRelation."""

    def test_create_relation(self):
        """Cria relacionamento."""
        relation = ExtractedRelation(
            source="João",
            target="Direito Constitucional",
            relation_type=RelationType.STUDIES,
            confidence=0.85,
        )
        assert relation.source == "João"
        assert relation.target == "Direito Constitucional"
        assert relation.relation_type == RelationType.STUDIES


class TestEntityType:
    """Testes para EntityType."""

    def test_entity_types(self):
        """Verifica tipos disponíveis."""
        assert EntityType.PERSON.value == "person"
        assert EntityType.ORGANIZATION.value == "organization"
        assert EntityType.CONCEPT.value == "concept"
        assert EntityType.LAW.value == "law"
        assert EntityType.CASE.value == "case"
        assert EntityType.SUBJECT.value == "subject"


class TestRelationType:
    """Testes para RelationType."""

    def test_relation_types(self):
        """Verifica tipos disponíveis."""
        assert RelationType.RELATED_TO.value == "related_to"
        assert RelationType.PART_OF.value == "part_of"
        assert RelationType.STUDIES.value == "studies"
        assert RelationType.DEPENDS_ON.value == "depends_on"
        assert RelationType.REFERENCES.value == "references"


class TestGraphService:
    """Testes para GraphService."""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock do pool de banco de dados."""
        pool = MagicMock()
        # Configurar acquire para retornar um async context manager funcional
        pool.acquire.return_value.__aenter__.return_value = MagicMock()
        pool.acquire.return_value.__aexit__.return_value = None
        return pool

    @pytest.fixture
    def mock_openai(self):
        """Mock do cliente OpenAI."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def graph_service(self, mock_db_pool, mock_openai):
        """Cria GraphService com mocks."""
        return GraphService(
            user_id="test_user_123",
            db_pool=mock_db_pool,
            openai_client=mock_openai,
        )

    def test_init_validates_user_id(self, mock_db_pool, mock_openai):
        """Inicialização valida user_id."""
        service = GraphService(
            user_id="user123",
            db_pool=mock_db_pool,
            openai_client=mock_openai,
        )
        assert service.user_id == "user123"

    @pytest.mark.asyncio
    async def test_extract_entities_from_text(self, graph_service, mock_openai):
        """Extração de entidades funciona."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"entities": [{"text": "João", "type": "person", "confidence": 0.9}]}'
                )
            )
        ]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        entities = await graph_service.extract_entities_from_text(
            "João estuda Direito Constitucional"
        )

        assert len(entities) == 1
        assert entities[0].text == "João"
        assert entities[0].entity_type == EntityType.PERSON

    @pytest.mark.asyncio
    async def test_extract_entities_handles_invalid_json(self, graph_service, mock_openai):
        """Lida com JSON inválido na extração."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="not valid json"))]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        entities = await graph_service.extract_entities_from_text("test")

        assert entities == []

    @pytest.mark.asyncio
    async def test_extract_relations_from_text(self, graph_service, mock_openai):
        """Extração de relacionamentos funciona."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"relations": [{"source": "João", "target": "Direito", "relation": "studies", "confidence": 0.85}]}'
                )
            )
        ]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        relations = await graph_service.extract_relations_from_text(
            "João estuda Direito Constitucional"
        )

        assert len(relations) == 1
        assert relations[0].source == "João"
        assert relations[0].target == "Direito"
        assert relations[0].relation_type == RelationType.STUDIES

    @pytest.mark.asyncio
    async def test_extract_relations_with_entities(self, graph_service, mock_openai):
        """Extração usa entidades conhecidas."""
        entities = [
            ExtractedEntity(text="João", entity_type=EntityType.PERSON, confidence=0.9),
            ExtractedEntity(text="Direito", entity_type=EntityType.CONCEPT, confidence=0.8),
        ]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"relations": [{"source": "João", "target": "Direito", "relation": "studies", "confidence": 0.9}]}'
                )
            )
        ]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        relations = await graph_service.extract_relations_from_text(
            "João estuda Direito",
            entities=entities,
        )

        assert len(relations) == 1

    @pytest.mark.asyncio
    async def test_export_graph_json(self, graph_service, mock_db_pool):
        """Exportação para JSON funciona."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch = AsyncMock(
            side_effect=[
                # Nodes
                [
                    {
                        "id": "node-1",
                        "label": "Test",
                        "node_type": "concept",
                        "properties": {},
                        "created_at": FIXED_DATETIME,
                    }
                ],
                # Edges
                [],
            ]
        )

        result = await graph_service.export_graph(format="json")

        assert "nodes" in result
        assert "links" in result
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["label"] == "Test"

    @pytest.mark.asyncio
    async def test_export_graph_cytoscape(self, graph_service, mock_db_pool):
        """Exportação para Cytoscape funciona."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch = AsyncMock(
            side_effect=[
                [{"id": "node-1", "label": "Test", "node_type": "concept", "properties": {}, "created_at": None}],
                [],
            ]
        )

        result = await graph_service.export_graph(format="cytoscape")

        assert "elements" in result
        assert "nodes" in result["elements"]
        assert "edges" in result["elements"]

    @pytest.mark.asyncio
    async def test_export_graph_graphml(self, graph_service, mock_db_pool):
        """Exportação para GraphML funciona."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch = AsyncMock(
            side_effect=[
                [{"id": "node-1", "label": "Test", "node_type": "concept", "properties": {}, "created_at": None}],
                [],
            ]
        )

        result = await graph_service.export_graph(format="graphml")

        assert isinstance(result, str)
        assert "<?xml" in result
        assert "<graphml" in result

    @pytest.mark.asyncio
    async def test_export_graph_invalid_format(self, graph_service, mock_db_pool):
        """Formato inválido lança erro."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch = AsyncMock(return_value=[])

        with pytest.raises(DatabaseError):
            await graph_service.export_graph(format="invalid")

    @pytest.mark.asyncio
    async def test_get_central_nodes_degree(self, graph_service, mock_db_pool):
        """Centralidade por grau funciona."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch = AsyncMock(
            return_value=[
                {"id": "node-1", "label": "Hub", "node_type": "concept", "degree": 10},
                {"id": "node-2", "label": "Spoke", "node_type": "concept", "degree": 3},
            ]
        )

        nodes = await graph_service.get_central_nodes(metric="degree", limit=10)

        assert len(nodes) == 2
        assert nodes[0]["label"] == "Hub"
        assert nodes[0]["score"] == 10

    @pytest.mark.asyncio
    async def test_find_clusters(self, graph_service, mock_db_pool):
        """Encontrar clusters funciona."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock para query de clusters
        mock_conn.fetch = AsyncMock(
            side_effect=[
                # Clusters query
                [{"component_id": "comp-1", "nodes": ["node-1", "node-2"], "size": 2}],
                # Nodes details query
                [
                    {"id": "node-1", "label": "Node 1", "node_type": "concept"},
                    {"id": "node-2", "label": "Node 2", "node_type": "concept"},
                ],
            ]
        )

        clusters = await graph_service.find_clusters(min_size=2)

        assert len(clusters) == 1
        assert clusters[0]["size"] == 2
        assert len(clusters[0]["nodes"]) == 2

    @pytest.mark.asyncio
    async def test_get_subgraph(self, graph_service, mock_db_pool):
        """Obter subgrafo funciona."""
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetch = AsyncMock(
            side_effect=[
                # Nodes query
                [
                    {"id": "node-1", "label": "Center", "node_type": "concept", "properties": {}},
                    {"id": "node-2", "label": "Neighbor", "node_type": "concept", "properties": {}},
                ],
                # Edges query
                [
                    {
                        "id": "edge-1",
                        "source_id": "node-1",
                        "target_id": "node-2",
                        "edge_type": "related_to",
                        "weight": 1.0,
                        "properties": {},
                    }
                ],
            ]
        )

        subgraph = await graph_service.get_subgraph(node_id="node-1", depth=2)

        assert "nodes" in subgraph
        assert "edges" in subgraph
        assert len(subgraph["nodes"]) == 2
        assert len(subgraph["edges"]) == 1

    @pytest.mark.asyncio
    async def test_add_conversation_to_graph_disabled(self, graph_service):
        """Adicionar conversa sem extração automática."""
        result = await graph_service.add_conversation_to_graph(
            user_message="Hello",
            assistant_response="Hi",
            auto_extract=False,
        )

        assert result["nodes_created"] == 0
        assert result["edges_created"] == 0
        assert result["entities"] == []
        assert result["relations"] == []


class TestGraphServiceIntegration:
    """Testes de integração do GraphService."""

    @pytest.mark.asyncio
    async def test_entity_type_mapping(self):
        """Mapeamento de tipos de entidade funciona."""
        valid_types = ["person", "organization", "location", "concept", "event", "topic", "document", "law", "case", "subject"]

        for type_name in valid_types:
            entity_type = EntityType(type_name)
            assert entity_type.value == type_name

    @pytest.mark.asyncio
    async def test_relation_type_mapping(self):
        """Mapeamento de tipos de relacionamento funciona."""
        valid_types = [
            "related_to",
            "part_of",
            "has_property",
            "mentions",
            "studies",
            "knows",
            "works_at",
            "located_in",
            "precedes",
            "follows",
            "depends_on",
            "references",
            "applies",
        ]

        for type_name in valid_types:
            relation_type = RelationType(type_name)
            assert relation_type.value == type_name
