"""Agno Agent Orchestrator for Agnaldo Discord bot.

This module provides the central agent coordination system using the Agno framework,
implementing multi-agent memory tiers (Core, Recall, Archival) with OpenAI integration.

Inspired by OpenClaw techniques:
- SOUL.md personality integration
- Multi-layer memory with Mem0
- Agentic memory with automatic retention
- Session summarization
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Callable, Literal, Optional

from loguru import logger
from openai import AsyncOpenAI

from src.config.settings import get_settings
from src.exceptions import AgentCommunicationError, DatabaseError
from src.intent.classifier import IntentClassifier
from src.intent.models import IntentCategory, IntentResult
from src.memory.archival import ArchivalMemory
from src.memory.core import CoreMemory
from src.memory.recall import RecallMemory
from src.schemas.agents import AgentMessage, AgentResponse, AgentMetrics, MessageType
from src.schemas.memory import MemoryStats


class AgentType(str, Enum):
    """Types of agents in the system."""

    CONVERSATIONAL = "conversational"
    """General conversation and chat handling."""

    KNOWLEDGE = "knowledge"
    """Knowledge base queries and RAG."""

    GRAPH = "graph"
    """Knowledge graph operations."""

    MEMORY = "memory"
    """Memory management operations."""

    OSINT = "osint"
    """OSINT tools and research."""


class AgentState(str, Enum):
    """Agent lifecycle states."""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class MemoryTierConfig:
    """Configuration for memory tiers."""

    def __init__(
        self,
        core_max_items: int = 100,
        core_max_tokens: int = 10000,
        recall_max_items: int = 1000,
        recall_max_age_days: int = 30,
        archival_enabled: bool = True,
    ) -> None:
        """Initialize memory tier configuration.

        Args:
            core_max_items: Maximum items in core memory.
            core_max_tokens: Maximum tokens in core memory.
            recall_max_items: Maximum items in recall memory.
            recall_max_age_days: Maximum age for recall memories in days.
            archival_enabled: Whether archival memory is enabled.
        """
        self.core_max_items = core_max_items
        self.core_max_tokens = core_max_tokens
        self.recall_max_items = recall_max_items
        self.recall_max_age_days = recall_max_age_days
        self.archival_enabled = archival_enabled


class AgnoAgent:
    """Individual agent wrapper with lifecycle management.

    Each agent has a specific role and access to memory tiers.
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        name: str,
        description: str,
        instructions: list[str],
        openai_client: AsyncOpenAI,
        model: str = "gpt-4o",
    ) -> None:
        """Initialize an Agno agent.

        Args:
            agent_id: Unique agent identifier.
            agent_type: Type of agent (conversational, knowledge, etc).
            name: Human-readable agent name.
            description: Agent description and purpose.
            instructions: System instructions for the agent.
            openai_client: OpenAI client for LLM calls.
            model: Model name to use.
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.instructions = instructions
        self.openai = openai_client
        self.model = model
        self.state = AgentState.STARTING
        self.metrics: AgentMetrics | None = None
        self.created_at = datetime.now(timezone.utc)

    async def start(self) -> None:
        """Start the agent."""
        logger.info(f"Starting agent {self.agent_id} ({self.name})...")
        self.state = AgentState.RUNNING
        logger.info(f"Agent {self.agent_id} is now RUNNING")

    async def stop(self) -> None:
        """Stop the agent gracefully."""
        logger.info(f"Stopping agent {self.agent_id}...")
        self.state = AgentState.STOPPING
        # Perform cleanup if needed
        self.state = AgentState.STOPPED
        logger.info(f"Agent {self.agent_id} is now STOPPED")

    async def restart(self) -> None:
        """Restart the agent."""
        await self.stop()
        await self.start()

    async def process(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
    ) -> str:
        """Process a message through the agent.

        Args:
            message: User message to process.
            context: Additional context (user_id, channel_id, etc).
            memory_context: Retrieved memories from tiers.

        Returns:
            Agent response as string.
        """
        if self.state != AgentState.RUNNING:
            raise AgentCommunicationError(
                f"Agent {self.agent_id} is not running (state: {self.state})",
                source_agent="system",
                target_agent=self.agent_id,
            )

        start_time = datetime.now(timezone.utc)

        try:
            # Build system prompt with instructions and personality
            system_prompt = self._build_system_prompt(memory_context)

            # Build user message with context
            user_message = self._build_user_message(message, context)

            # Call OpenAI API
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            result = response.choices[0].message.content or ""

            # Update metrics
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.metrics = AgentMetrics(
                agent_name=self.agent_id,
                execution_time=execution_time,
                tokens_used=response.usage.total_tokens if response.usage else None,
            )

            logger.debug(
                f"Agent {self.agent_id} processed message in {execution_time:.2f}s, "
                f"{self.metrics.tokens_used} tokens"
            )

            return result

        except Exception as e:
            logger.error(f"Agent {self.agent_id} failed to process message: {e}")
            raise AgentCommunicationError(
                f"Agent processing failed: {e}",
                source_agent="system",
                target_agent=self.agent_id,
            ) from e

    def _build_system_prompt(self, memory_context: dict[str, Any] | None) -> str:
        """Build the system prompt with instructions and memory."""
        parts = []

        # Add instructions (SOUL.md personality)
        for instruction in self.instructions:
            parts.append(instruction)

        # Add memory context if available
        if memory_context:
            parts.append("\n## Contexto de Memória")
            if memory_context.get("core"):
                parts.append(f"Fatos importantes: {memory_context['core']}")
            if memory_context.get("recent"):
                parts.append(f"Memórias recentes: {memory_context['recent'][:500]}...")

        return "\n\n".join(parts)

    def _build_user_message(self, message: str, context: dict[str, Any] | None) -> str:
        """Build the user message with context."""
        if not context:
            return message

        parts = [message]

        # Add relevant context
        if context.get("username"):
            parts.insert(0, f"Usuário: {context['username']}")
        if context.get("guild_name"):
            parts.insert(1, f"Servidor: {context['guild_name']}")

        return "\n".join(parts)


class AgentOrchestrator:
    """Central orchestrator for multi-agent coordination.

    Manages agent lifecycle, message routing, memory integration,
    and coordination between different agent types.

    Attributes:
        pending_approvals: Dict of pending human-in-the-loop approvals.
    """

    def __init__(
        self,
        personality_instructions: list[str] | None = None,
        memory_config: MemoryTierConfig | None = None,
    ) -> None:
        """Initialize the agent orchestrator.

        Args:
            personality_instructions: Personality instructions (SOUL.md).
            memory_config: Memory tier configuration.
        """
        settings = get_settings()
        self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_CHAT_MODEL

        # Memory configuration
        self.memory_config = memory_config or MemoryTierConfig()

        # Personality (SOUL.md)
        self.personality_instructions = personality_instructions or []

        # Agent registry
        self.agents: dict[str, AgnoAgent] = {}
        self.agent_by_type: dict[AgentType, list[str]] = {
            agent_type: [] for agent_type in AgentType
        }

        # Intent classifier
        self.intent_classifier = IntentClassifier()

        # State
        self.state = AgentState.STARTING
        self.started_at: datetime | None = None

        # Human-in-the-loop
        self.pending_approvals: dict[str, dict[str, Any]] = {}
        self.approval_timeout_seconds = 300

        logger.info("AgentOrchestrator initialized")

    async def initialize(self) -> None:
        """Initialize the orchestrator and all agents."""
        logger.info("Initializing AgentOrchestrator...")

        # Initialize intent classifier
        await self.intent_classifier.initialize()

        # Create agents
        await self._create_agents()

        # Start all agents
        await self._start_all_agents()

        self.state = AgentState.RUNNING
        self.started_at = datetime.now(timezone.utc)

        logger.info("AgentOrchestrator is now RUNNING")

    async def _create_agents(self) -> None:
        """Create all agent instances."""
        # Base instructions from personality
        base_instructions = list(self.personality_instructions)

        # Conversational Agent
        conversational = AgnoAgent(
            agent_id="agent_conversational",
            agent_type=AgentType.CONVERSATIONAL,
            name="Conversational",
            description="Handles general conversation and chat",
            instructions=[
                *base_instructions,
                "Você é o agente conversacional principal do Agnaldo.",
                "Responda de forma natural, amigável e útil.",
                "Mantenha respostas concisas e diretas.",
            ],
            openai_client=self.openai,
            model=self.model,
        )
        self.agents[conversational.agent_id] = conversational
        self.agent_by_type[AgentType.CONVERSATIONAL].append(conversational.agent_id)

        # Knowledge Agent
        knowledge = AgnoAgent(
            agent_id="agent_knowledge",
            agent_type=AgentType.KNOWLEDGE,
            name="Knowledge",
            description="Handles knowledge base queries and RAG",
            instructions=[
                *base_instructions,
                "Você é o agente de conhecimento do Agnaldo.",
                "Acesse a base de conhecimento para responder perguntas.",
                "Use busca semântica para encontrar informações relevantes.",
                "Cite as fontes quando possível.",
            ],
            openai_client=self.openai,
            model=self.model,
        )
        self.agents[knowledge.agent_id] = knowledge
        self.agent_by_type[AgentType.KNOWLEDGE].append(knowledge.agent_id)

        # Memory Agent
        memory = AgnoAgent(
            agent_id="agent_memory",
            agent_type=AgentType.MEMORY,
            name="Memory",
            description="Handles memory management operations",
            instructions=[
                *base_instructions,
                "Você é o agente de memória do Agnaldo.",
                "Gerencie as três camadas de memória: Core, Recall e Archival.",
                "Core: fatos importantes sobre o usuário.",
                "Recall: conversas recentes com busca semântica.",
                "Archival: armazenamento de longo prazo.",
            ],
            openai_client=self.openai,
            model=self.model,
        )
        self.agents[memory.agent_id] = memory
        self.agent_by_type[AgentType.MEMORY].append(memory.agent_id)

        # Graph Agent
        graph = AgnoAgent(
            agent_id="agent_graph",
            agent_type=AgentType.GRAPH,
            name="Graph",
            description="Handles knowledge graph operations",
            instructions=[
                *base_instructions,
                "Você é o agente de grafo de conhecimento do Agnaldo.",
                "Gerencie nós e arestas do grafo semântico.",
                "Conceitos são conectados por relacionamentos.",
                "Use travessia de grafo para inferir conhecimento.",
            ],
            openai_client=self.openai,
            model=self.model,
        )
        self.agents[graph.agent_id] = graph
        self.agent_by_type[AgentType.GRAPH].append(graph.agent_id)

        # Core Memory Agent (NEW!)
        core_memory = AgnoAgent(
            agent_id="agent_core_memory",
            agent_type=AgentType.MEMORY,
            name="Core Memory",
            description="Gerencia memória core rápida e de alto valor",
            instructions=[
                *base_instructions,
                "Você é o agente de memória core do Agnaldo.",
                "Armazene informações críticas e de acesso rápido.",
                "Máximo 100 itens com scoring de importância.",
                "Use cache LRU ponderado para eviction.",
                "Prioriza fatos mais recentes por importância.",
            ],
            openai_client=self.openai,
            model=self.model,
        )
        self.agents[core_memory.agent_id] = core_memory
        self.agent_by_type[AgentType.MEMORY].append(core_memory.agent_id)

        logger.info(f"Created {len(self.agents)} agents")

    async def _start_all_agents(self) -> None:
        """Start all registered agents."""
        for agent in self.agents.values():
            await agent.start()

    async def shutdown(self) -> None:
        """Shutdown the orchestrator and all agents."""
        logger.info("Shutting down AgentOrchestrator...")
        self.state = AgentState.STOPPING

        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()

        self.state = AgentState.STOPPED
        logger.info("AgentOrchestrator shutdown complete")

    async def route_and_process(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        user_id: str | None = None,
        db_pool=None,
        session_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Route message to appropriate agent and stream response.

        Args:
            message: User message to process.
            context: Discord context (user, channel, guild).
            user_id: User ID for memory isolation.
            db_pool: Database pool for memory operations.
            session_id: Session ID for conversation continuity (learning).

        Yields:
            Response chunks as they are generated.
        """
        if self.state != AgentState.RUNNING:
            raise AgentCommunicationError(
                "Orchestrator is not running",
                source_agent="orchestrator",
                target_agent="system",
            )

        # Generate session_id if not provided (for learning continuity)
        if not session_id and user_id:
            import uuid

            session_id = f"{user_id}_{uuid.uuid4().hex[:8]}"

        logger.info(f"Processing message session_id={session_id} user_id={user_id}")

        # Classify intent
        intent_result = await self.intent_classifier.classify(message)
        logger.info(
            f"Intent: {intent_result.intent.value} (confidence: {intent_result.confidence:.2f})"
        )

        # Determine which agent to use
        agent_id = await self._route_to_agent(intent_result)

        # Retrieve memory context if user_id and db_pool provided
        memory_context: dict[str, Any] | None = None
        if user_id and db_pool:
            memory_context = await self._retrieve_memory_context(user_id, message, db_pool)

        # Get the agent
        agent = self.agents.get(agent_id)
        if not agent:
            raise AgentCommunicationError(
                f"Agent not found: {agent_id}",
                source_agent="orchestrator",
                target_agent=agent_id,
            )

        # Process and yield response
        response = await agent.process(message, context, memory_context)
        yield response

        # Store interaction in memory if applicable
        if (
            user_id
            and db_pool
            and intent_result.intent
            not in (
                IntentCategory.GREETING,
                IntentCategory.HELP,
                IntentCategory.STATUS,
            )
        ):
            await self._store_interaction(user_id, message, response, intent_result, db_pool)

    async def _route_to_agent(self, intent_result: IntentResult) -> str:
        """Route to the appropriate agent based on intent."""
        intent = intent_result.intent

        # Map intents to agent types
        intent_agent_map = {
            IntentCategory.KNOWLEDGE_QUERY: AgentType.KNOWLEDGE,
            IntentCategory.DEFINITION: AgentType.KNOWLEDGE,
            IntentCategory.EXPLANATION: AgentType.KNOWLEDGE,
            IntentCategory.GRAPH_QUERY: AgentType.GRAPH,
            IntentCategory.MEMORY_STORE: AgentType.MEMORY,
            IntentCategory.MEMORY_RETRIEVE: AgentType.MEMORY,
        }

        agent_type = intent_agent_map.get(intent, AgentType.CONVERSATIONAL)

        # Get first agent of this type
        agent_ids = self.agent_by_type.get(agent_type, [])
        if not agent_ids:
            # Fallback to conversational
            agent_ids = self.agent_by_type.get(AgentType.CONVERSATIONAL, [])

        if not agent_ids:
            raise AgentCommunicationError(
                "No available agents for requested intent routing",
                source_agent="orchestrator",
                target_agent=agent_type.value,
            )

        selected_agent_id = agent_ids[0]
        if selected_agent_id not in self.agents:
            raise AgentCommunicationError(
                f"Resolved agent is not registered: {selected_agent_id}",
                source_agent="orchestrator",
                target_agent=selected_agent_id,
            )

        return selected_agent_id

    async def _retrieve_memory_context(self, user_id: str, query: str, db_pool) -> dict[str, Any]:
        """Retrieve memory context from all tiers.

        Integrates CoreMemory (fast key-value) with RecallMemory (semantic search)
        to provide comprehensive context for agent responses.
        """
        context: dict[str, Any] = {}

        try:
            core = CoreMemory(user_id, db_pool)
            core_memories = await core.get_all()
            if core_memories:
                context["core"] = [
                    {"key": key, "value": value} for key, value in core_memories.items()
                ]
                logger.debug(f"Retrieved {len(core_memories)} core memories for context")

            recall = RecallMemory(user_id, db_pool)
            recall_results = await recall.search(query, limit=3, threshold=0.6)
            if recall_results:
                context["recent"] = [
                    {"content": r["content"], "similarity": r["similarity"]} for r in recall_results
                ]

        except Exception as e:
            logger.warning(f"Failed to retrieve memory context: {e}")

        return context

    async def _store_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        intent_result: IntentResult,
        db_pool,
    ) -> None:
        """Store interaction in appropriate memory tier."""
        try:
            # Store in recall memory for semantic search
            recall = RecallMemory(user_id, db_pool)
            await recall.add(
                f"User: {message}\nAssistant: {response}",
                importance=0.5 + intent_result.confidence * 0.3,
            )
            logger.debug("Stored interaction in recall memory")

        except Exception as e:
            logger.warning(f"Failed to store interaction: {e}")

    async def request_approval(
        self,
        action_id: str,
        action_description: str,
        user_id: str,
        channel_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Request human approval for a critical action.

        Args:
            action_id: Unique identifier for the action.
            action_description: Human-readable description.
            user_id: User who must approve.
            channel_id: Discord channel for approval.
            metadata: Additional context.

        Returns:
            Approval request ID.
        """
        import uuid
        import time

        request_id = f"approval_{uuid.uuid4().hex[:8]}"

        self.pending_approvals[request_id] = {
            "action_id": action_id,
            "description": action_description,
            "user_id": user_id,
            "channel_id": channel_id,
            "metadata": metadata or {},
            "created_at": time.time(),
            "status": "pending",
        }

        logger.info(f"Created approval request {request_id} for action {action_id}")
        return request_id

    async def check_approval(
        self, request_id: str
    ) -> Literal["pending", "approved", "denied", "timeout", "not_found"]:
        """Check approval status.

        Args:
            request_id: Approval request ID.

        Returns:
            Status: 'pending', 'approved', 'denied', 'timeout'.
        """
        import time
        from typing import cast

        approval = self.pending_approvals.get(request_id)
        if not approval:
            return "not_found"

        status = cast(Literal["pending", "approved", "denied"], approval["status"])
        if status != "pending":
            return status

        elapsed = time.time() - approval["created_at"]
        if elapsed > self.approval_timeout_seconds:
            approval["status"] = "timeout"
            logger.warning(f"Approval request {request_id} timed out")
            return "timeout"

        return "pending"

    async def approve_action(self, request_id: str, approved: bool) -> bool:
        """Approve or deny a pending action.

        Args:
            request_id: Approval request ID.
            approved: True to approve, False to deny.

        Returns:
            True if action was found and updated.
        """
        approval = self.pending_approvals.get(request_id)
        if not approval:
            return False

        approval["status"] = "approved" if approved else "denied"
        logger.info(f"Approval {request_id} {'approved' if approved else 'denied'}")
        return True

    async def get_stats(self) -> dict[str, Any]:
        """Get orchestrator and agent statistics."""
        agent_stats = []
        for agent in self.agents.values():
            agent_stats.append(
                {
                    "id": agent.agent_id,
                    "name": agent.name,
                    "type": agent.agent_type.value,
                    "state": agent.state.value,
                    "metrics": agent.metrics.model_dump() if agent.metrics else None,
                }
            )

        return {
            "orchestrator_state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "total_agents": len(self.agents),
            "agents": agent_stats,
        }


# Global orchestrator instance
_orchestrator: AgentOrchestrator | None = None
_orchestrator_lock = asyncio.Lock()


async def get_orchestrator(
    personality_instructions: list[str] | None = None,
    memory_config: MemoryTierConfig | None = None,
) -> AgentOrchestrator:
    """Get or create the global orchestrator instance.

    Args:
        personality_instructions: Personality instructions (SOUL.md).
        memory_config: Memory tier configuration.

    Returns:
        The global AgentOrchestrator instance.
    """
    global _orchestrator

    if _orchestrator is None:
        async with _orchestrator_lock:
            if _orchestrator is None:
                _orchestrator = AgentOrchestrator(personality_instructions, memory_config)
                await _orchestrator.initialize()

    return _orchestrator


async def shutdown_orchestrator() -> None:
    """Shutdown the global orchestrator."""
    global _orchestrator

    if _orchestrator:
        await _orchestrator.shutdown()
        _orchestrator = None
