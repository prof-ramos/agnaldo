"""Integration tests for AgentOrchestrator.

These tests verify the multi-agent coordination system including:
- Agent routing by intent classification
- Individual agent behavior (conversational, knowledge, memory, graph)
- Error handling and edge cases
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.orchestrator import (
    AgentOrchestrator,
    AgentState,
    AgentType,
    AgnoAgent,
    MemoryTierConfig,
)
from src.exceptions import AgentCommunicationError
from src.intent.models import IntentCategory, IntentResult


def _build_mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """Build a mock asyncpg pool with an async context manager for acquire()."""
    mock_pool = MagicMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = mock_conn
    acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = acquire_cm
    return mock_pool


def _build_mock_openai_client(response_text: str = "Test response") -> MagicMock:
    """Build a mock OpenAI client with predefined responses."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = response_text
    mock_response.usage = MagicMock(total_tokens=50)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


def _build_mock_openai_with_embeddings() -> MagicMock:
    """Build a mock OpenAI client with embedding support."""
    mock_client = _build_mock_openai_client()
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)
    return mock_client


def _build_mock_settings() -> MagicMock:
    """Build mock settings for AgentOrchestrator."""
    settings = MagicMock()
    settings.OPENAI_API_KEY = "test_openai_key"
    settings.OPENAI_CHAT_MODEL = "gpt-4o"
    settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
    settings.SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"
    return settings


@pytest.fixture
async def mock_openai_client():
    """Fixture for mock OpenAI client."""
    return _build_mock_openai_client()


@pytest.fixture
async def mock_openai_with_embeddings():
    """Fixture for mock OpenAI client with embeddings."""
    return _build_mock_openai_with_embeddings()


@pytest.fixture
async def mock_asyncpg_pool():
    """Fixture for mock asyncpg pool."""
    mock_conn = AsyncMock()
    # Mock for recall memory search
    mock_conn.fetch.return_value = []
    return _build_mock_pool(mock_conn)


@pytest.fixture
async def mock_asyncpg_pool_with_memories():
    """Fixture for mock asyncpg pool with pre-existing memories."""
    mock_conn = AsyncMock()
    # Mock for recall memory search with results
    # Note: _retrieve_memory_context expects a different format than search returns
    # We need to match what RecallMemory.search returns
    mock_conn.fetch.return_value = [
        {
            "id": "mem-1",
            "key": "ai_context",
            "value": "Previous conversation about AI",
            "content": "Previous conversation about AI",
            "importance": 0.7,
            "similarity": 0.85,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_accessed": datetime.now(timezone.utc),
            "access_count": 1,
            "metadata": {"source": "test"},
        }
    ]
    # Mock for add operation
    mock_conn.fetchval.return_value = "new-mem-id"
    # Mock for execute (access count update)
    mock_conn.execute.return_value = "UPDATE 1"
    return _build_mock_pool(mock_conn)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_initialization(mock_openai_client):
    """Test orchestrator initialization and agent creation."""
    mock_settings = _build_mock_settings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        with patch("src.agents.orchestrator.AsyncOpenAI", return_value=mock_openai_client):
            # Mock IntentClassifier with proper async initialize method
            mock_classifier = AsyncMock()
            mock_classifier.initialize = AsyncMock()

            with patch("src.agents.orchestrator.IntentClassifier", return_value=mock_classifier):
                orchestrator = AgentOrchestrator(
                    personality_instructions=["You are a helpful bot."],
                    memory_config=MemoryTierConfig(core_max_items=50),
                )

                # Mock the OpenAI client in the orchestrator
                orchestrator.openai = mock_openai_client

                await orchestrator.initialize()

                # Verify state
                assert orchestrator.state == AgentState.RUNNING
                assert orchestrator.started_at is not None

                # Verify all agents were created
                assert len(orchestrator.agents) == 5
                assert "agent_conversational" in orchestrator.agents
                assert "agent_knowledge" in orchestrator.agents
                assert "agent_memory" in orchestrator.agents
                assert "agent_graph" in orchestrator.agents
                assert "agent_core_memory" in orchestrator.agents

                # Verify agent types are mapped correctly
                assert len(orchestrator.agent_by_type[AgentType.CONVERSATIONAL]) == 1
                assert len(orchestrator.agent_by_type[AgentType.KNOWLEDGE]) == 1
                assert len(orchestrator.agent_by_type[AgentType.MEMORY]) == 2
                assert len(orchestrator.agent_by_type[AgentType.GRAPH]) == 1

                # Verify all agents are running
                for agent in orchestrator.agents.values():
                    assert agent.state == AgentState.RUNNING


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_routing_by_intent():
    """Test agent routing based on intent classification."""
    mock_settings = _build_mock_settings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        orchestrator = AgentOrchestrator()
        orchestrator.state = AgentState.RUNNING

        # Create mock agents
        mock_agent = MagicMock()
        mock_agent.process = AsyncMock(return_value="Response")

        orchestrator.agents = {
            "agent_conversational": mock_agent,
            "agent_knowledge": mock_agent,
            "agent_memory": mock_agent,
            "agent_graph": mock_agent,
        }
        orchestrator.agent_by_type = {
            AgentType.CONVERSATIONAL: ["agent_conversational"],
            AgentType.KNOWLEDGE: ["agent_knowledge"],
            AgentType.MEMORY: ["agent_memory"],
            AgentType.GRAPH: ["agent_graph"],
            AgentType.OSINT: [],
        }

        # Test routing for different intents
        test_cases = [
            (IntentCategory.KNOWLEDGE_QUERY, "agent_knowledge"),
            (IntentCategory.DEFINITION, "agent_knowledge"),
            (IntentCategory.EXPLANATION, "agent_knowledge"),
            (IntentCategory.GRAPH_QUERY, "agent_graph"),
            (IntentCategory.MEMORY_STORE, "agent_memory"),
            (IntentCategory.MEMORY_RETRIEVE, "agent_memory"),
            (IntentCategory.GREETING, "agent_conversational"),  # Fallback
            (IntentCategory.FAREWELL, "agent_conversational"),  # Fallback
        ]

        for intent, expected_agent_id in test_cases:
            intent_result = IntentResult(
                intent=intent, confidence=0.9, entities={}, raw_text="test"
            )
            agent_id = await orchestrator._route_to_agent(intent_result)
            assert agent_id == expected_agent_id, (
                f"Intent {intent} should route to {expected_agent_id}"
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversational_agent():
    """Test conversational agent processing."""
    mock_openai = _build_mock_openai_client("Olá! Como posso ajudar?")

    agent = AgnoAgent(
        agent_id="test_conversational",
        agent_type=AgentType.CONVERSATIONAL,
        name="Test Conversational",
        description="Test agent",
        instructions=["You are helpful."],
        openai_client=mock_openai,
        model="gpt-4o",
    )

    await agent.start()
    assert agent.state == AgentState.RUNNING

    response = await agent.process("Olá!")
    assert response == "Olá! Como posso ajudar?"

    # Verify metrics were updated
    assert agent.metrics is not None
    assert agent.metrics.agent_name == "test_conversational"
    assert agent.metrics.execution_time > 0
    assert agent.metrics.tokens_used == 50


@pytest.mark.integration
@pytest.mark.asyncio
async def test_knowledge_agent():
    """Test knowledge agent processing with RAG context."""
    mock_openai = _build_mock_openai_client(
        "Baseado em minha base de conhecimento, Python é uma linguagem de programação..."
    )

    agent = AgnoAgent(
        agent_id="test_knowledge",
        agent_type=AgentType.KNOWLEDGE,
        name="Test Knowledge",
        description="Test knowledge agent",
        instructions=["You are a knowledge assistant."],
        openai_client=mock_openai,
        model="gpt-4o",
    )

    await agent.start()

    memory_context = {
        "core": "User likes programming",
        "recent": "User asked about Python before",
    }

    response = await agent.process(
        "O que é Python?", context={"username": "Gabriel"}, memory_context=memory_context
    )

    assert "Python" in response

    # Verify OpenAI was called with proper context
    mock_openai.chat.completions.create.assert_called_once()
    call_args = mock_openai.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]

    # Check system prompt contains memory context
    system_prompt = messages[0]["content"]
    assert "Fatos importantes" in system_prompt
    assert "Memórias recentes" in system_prompt


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_agent():
    """Test memory agent processing."""
    mock_openai = _build_mock_openai_client(
        "Memória armazenada com sucesso. Lembrei que você gosta de café."
    )

    agent = AgnoAgent(
        agent_id="test_memory",
        agent_type=AgentType.MEMORY,
        name="Test Memory",
        description="Test memory agent",
        instructions=["You manage memory."],
        openai_client=mock_openai,
        model="gpt-4o",
    )

    await agent.start()

    response = await agent.process("Lembre que eu gosto de café")
    assert response is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_agent():
    """Test graph agent processing."""
    mock_openai = _build_mock_openai_client(
        "No grafo de conhecimento, Python está conectado a programação e desenvolvimento."
    )

    agent = AgnoAgent(
        agent_id="test_graph",
        agent_type=AgentType.GRAPH,
        name="Test Graph",
        description="Test graph agent",
        instructions=["You manage the knowledge graph."],
        openai_client=mock_openai,
        model="gpt-4o",
    )

    await agent.start()

    response = await agent.process("Quais são os conceitos relacionados a Python?")
    assert response is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_route_and_process(
    mock_openai_with_embeddings, mock_asyncpg_pool_with_memories
):
    """Test complete route_and_process flow with memory integration."""
    mock_settings = _build_mock_settings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        orchestrator = AgentOrchestrator()
        orchestrator.state = AgentState.RUNNING
        orchestrator.openai = mock_openai_with_embeddings

        # Create a real agent for testing
        agent = AgnoAgent(
            agent_id="agent_conversational",
            agent_type=AgentType.CONVERSATIONAL,
            name="Conversational",
            description="Handles conversation",
            instructions=["You are helpful."],
            openai_client=mock_openai_with_embeddings,
            model="gpt-4o",
        )
        await agent.start()

        orchestrator.agents = {"agent_conversational": agent}
        orchestrator.agent_by_type = {
            AgentType.CONVERSATIONAL: ["agent_conversational"],
            AgentType.KNOWLEDGE: [],
            AgentType.MEMORY: [],
            AgentType.GRAPH: [],
            AgentType.OSINT: [],
        }

        # Mock the intent classifier
        with patch.object(
            orchestrator.intent_classifier,
            "classify",
            return_value=IntentResult(
                intent=IntentCategory.GREETING, confidence=0.95, entities={}, raw_text="Olá"
            ),
        ):
            # Process message
            responses = []
            async for chunk in orchestrator.route_and_process(
                message="Olá!",
                context={"username": "TestUser"},
                user_id="user-123",
                db_pool=mock_asyncpg_pool_with_memories,
            ):
                responses.append(chunk)

            assert len(responses) == 1
            assert responses[0] == "Test response"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_retrieve_memory_context(mock_asyncpg_pool_with_memories):
    """Test memory context retrieval before agent processing."""
    mock_settings = _build_mock_settings()
    mock_openai = _build_mock_openai_with_embeddings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        with patch("src.memory.recall.get_settings", return_value=mock_settings):
            with patch("src.memory.recall.AsyncOpenAI", return_value=mock_openai):
                orchestrator = AgentOrchestrator()
                orchestrator.state = AgentState.RUNNING

                context = await orchestrator._retrieve_memory_context(
                    user_id="user-123",
                    query="AI conversation",
                    db_pool=mock_asyncpg_pool_with_memories,
                )

                assert "recent" in context
                assert len(context["recent"]) == 1
                assert context["recent"][0]["content"] == "Previous conversation about AI"
                assert context["recent"][0]["similarity"] == 0.85


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_store_interaction(mock_asyncpg_pool_with_memories):
    """Test storing interaction in recall memory."""
    mock_settings = _build_mock_settings()
    mock_openai = _build_mock_openai_with_embeddings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        with patch("src.memory.recall.get_settings", return_value=mock_settings):
            with patch("src.memory.recall.AsyncOpenAI", return_value=mock_openai):
                orchestrator = AgentOrchestrator()
                orchestrator.state = AgentState.RUNNING

                intent_result = IntentResult(
                    intent=IntentCategory.KNOWLEDGE_QUERY,
                    confidence=0.8,
                    entities={},
                    raw_text="test",
                )

                # Should not raise exception
                await orchestrator._store_interaction(
                    user_id="user-123",
                    message="What is AI?",
                    response="AI is artificial intelligence",
                    intent_result=intent_result,
                    db_pool=mock_asyncpg_pool_with_memories,
                )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_does_not_store_trivial_intents(mock_asyncpg_pool_with_memories):
    """Test that trivial intents (greeting, help, status) are not stored."""
    mock_settings = _build_mock_settings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        orchestrator = AgentOrchestrator()
        orchestrator.state = AgentState.RUNNING

        trivial_intents = [
            IntentCategory.GREETING,
            IntentCategory.HELP,
            IntentCategory.STATUS,
        ]

        for intent in trivial_intents:
            intent_result = IntentResult(
                intent=intent, confidence=0.9, entities={}, raw_text="test"
            )

            # Mock the intent classifier to return the trivial intent
            with patch.object(
                orchestrator.intent_classifier,
                "classify",
                return_value=intent_result,
            ):
                # Mock the agent process
                with patch.object(
                    orchestrator, "_route_to_agent", return_value="agent_conversational"
                ):
                    mock_store = AsyncMock()
                    with patch.object(orchestrator, "_store_interaction", new=mock_store):
                        agent = MagicMock()
                        agent.process = AsyncMock(return_value="Response")
                        orchestrator.agents = {"agent_conversational": agent}

                        # Process - _store_interaction should NOT be called
                        async for _ in orchestrator.route_and_process(
                            message="test",
                            user_id="user-123",
                            db_pool=mock_asyncpg_pool_with_memories,
                        ):
                            pass

                        # Verify _store_interaction was not called for trivial intents
                        # (It should be skipped in the route_and_process method)
                        mock_store.assert_not_called()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_not_running_error():
    """Test error when trying to process with a stopped agent."""
    mock_openai = _build_mock_openai_client()

    agent = AgnoAgent(
        agent_id="test_agent",
        agent_type=AgentType.CONVERSATIONAL,
        name="Test",
        description="Test",
        instructions=["Test"],
        openai_client=mock_openai,
    )
    # Don't start the agent - state should be STARTING

    with pytest.raises(AgentCommunicationError) as exc_info:
        await agent.process("Hello")

    assert "not running" in str(exc_info.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_not_running_error():
    """Test error when trying to route with orchestrator not running."""
    mock_settings = _build_mock_settings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        orchestrator = AgentOrchestrator()
        # State is STARTING, not RUNNING

        with pytest.raises(AgentCommunicationError) as exc_info:
            async for _ in orchestrator.route_and_process("test"):
                pass

        assert "not running" in str(exc_info.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_openai_failure_handling():
    """Test error handling when OpenAI API fails."""
    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

    agent = AgnoAgent(
        agent_id="test_agent",
        agent_type=AgentType.CONVERSATIONAL,
        name="Test",
        description="Test",
        instructions=["Test"],
        openai_client=mock_openai,
    )

    await agent.start()

    with pytest.raises(AgentCommunicationError) as exc_info:
        await agent.process("Hello")

    assert "processing failed" in str(exc_info.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_get_stats():
    """Test getting orchestrator statistics."""
    mock_settings = _build_mock_settings()
    mock_openai = _build_mock_openai_client()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        orchestrator = AgentOrchestrator()
        orchestrator.state = AgentState.RUNNING
        orchestrator.openai = mock_openai

        # Create a test agent
        agent = AgnoAgent(
            agent_id="test_agent",
            agent_type=AgentType.CONVERSATIONAL,
            name="Test Agent",
            description="Test",
            instructions=["Test"],
            openai_client=mock_openai,
        )
        await agent.start()
        await agent.process("Test message")  # Generate some metrics

        orchestrator.agents = {"test_agent": agent}

        stats = await orchestrator.get_stats()

        assert stats["orchestrator_state"] == "running"
        assert stats["total_agents"] == 1
        assert len(stats["agents"]) == 1
        assert stats["agents"][0]["id"] == "test_agent"
        assert stats["agents"][0]["state"] == "running"
        assert stats["agents"][0]["metrics"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_shutdown():
    """Test graceful shutdown of orchestrator and agents."""
    mock_settings = _build_mock_settings()
    mock_openai = _build_mock_openai_client()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        orchestrator = AgentOrchestrator()
        orchestrator.state = AgentState.RUNNING
        orchestrator.openai = mock_openai

        # Create test agents
        for i in range(3):
            agent = AgnoAgent(
                agent_id=f"agent_{i}",
                agent_type=AgentType.CONVERSATIONAL,
                name=f"Agent {i}",
                description="Test",
                instructions=["Test"],
                openai_client=mock_openai,
            )
            await agent.start()
            orchestrator.agents[f"agent_{i}"] = agent

        await orchestrator.shutdown()

        assert orchestrator.state == AgentState.STOPPED
        for agent in orchestrator.agents.values():
            assert agent.state == AgentState.STOPPED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_restart():
    """Test agent restart functionality."""
    mock_openai = _build_mock_openai_client()

    agent = AgnoAgent(
        agent_id="test_agent",
        agent_type=AgentType.CONVERSATIONAL,
        name="Test",
        description="Test",
        instructions=["Test"],
        openai_client=mock_openai,
    )

    await agent.start()
    assert agent.state == AgentState.RUNNING

    await agent.restart()
    # After restart, should be RUNNING again
    assert agent.state == AgentState.RUNNING


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_fallback_to_conversational():
    """Test fallback to conversational agent when no specific agent is available."""
    mock_settings = _build_mock_settings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        orchestrator = AgentOrchestrator()
        orchestrator.state = AgentState.RUNNING

        # Only conversational agent available
        agent = MagicMock()
        agent.process = AsyncMock(return_value="Fallback response")

        orchestrator.agents = {"agent_conversational": agent}
        orchestrator.agent_by_type = {
            AgentType.CONVERSATIONAL: ["agent_conversational"],
            AgentType.KNOWLEDGE: [],  # Empty - should fallback
            AgentType.MEMORY: [],
            AgentType.GRAPH: [],
            AgentType.OSINT: [],
        }

        # Test with KNOWLEDGE_QUERY intent (should fallback to conversational)
        intent_result = IntentResult(
            intent=IntentCategory.KNOWLEDGE_QUERY, confidence=0.8, entities={}, raw_text="test"
        )

        agent_id = await orchestrator._route_to_agent(intent_result)
        assert agent_id == "agent_conversational"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_no_agents_error():
    """Test error when no agents are available."""
    mock_settings = _build_mock_settings()

    with patch("src.agents.orchestrator.get_settings", return_value=mock_settings):
        orchestrator = AgentOrchestrator()
        orchestrator.state = AgentState.RUNNING
        orchestrator.agents = {}
        orchestrator.agent_by_type = {agent_type: [] for agent_type in AgentType}

        intent_result = IntentResult(
            intent=IntentCategory.KNOWLEDGE_QUERY, confidence=0.8, entities={}, raw_text="test"
        )

        with pytest.raises(AgentCommunicationError) as exc_info:
            await orchestrator._route_to_agent(intent_result)

        assert "no available agents" in str(exc_info.value).lower()
