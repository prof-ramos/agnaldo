"""Message handlers for Agnaldo Discord bot with Agno agent integration.

This module provides message processing capabilities that:
- Classify user intent using IntentClassifier
- Route to appropriate Agno agent
- Retrieve relevant memory before processing
- Store conversation history in database
- Stream responses back to Discord
"""

import asyncio
import hashlib
import time
from typing import Any

from discord.ext.commands import Bot
from loguru import logger

from discord import Message
from src.agents.orchestrator import AgentOrchestrator, get_orchestrator
from src.agents.study_agent import StudyAgent
from src.exceptions import AgentCommunicationError
from src.intent.classifier import IntentClassifier
from src.schemas.knowledge import StudyAgentRequest


class MessageHandler:
    """Handler for processing Discord messages through Agno agents."""

    def __init__(
        self,
        bot: Bot,
        intent_classifier: IntentClassifier,
        db_pool=None,
    ) -> None:
        """Initialize the message handler.

        Args:
            bot: Discord bot instance.
            intent_classifier: Intent classifier for routing.
            db_pool: Database connection pool.
        """
        self.bot = bot
        self.intent_classifier = intent_classifier
        self.db_pool = db_pool
        self._orchestrator: AgentOrchestrator | None = None
        self._study_agent: StudyAgent | None = None

        # Rate limiting para comando !ask (5 requisições por minuto por usuário)
        self._ask_rate_limit: dict[str, list[float]] = {}  # user_id -> [timestamps]
        self._ask_rate_limit_max_requests = 5
        self._ask_rate_limit_window = 60  # segundos

    async def initialize(self) -> None:
        """Initialize the handler and orchestrator."""
        # Get or create orchestrator with bot personality
        personality = getattr(self.bot, "personality", None)
        personality_instructions = [personality] if personality else []

        self._orchestrator = await get_orchestrator(
            personality_instructions=personality_instructions,
        )

        # Setup StudyAgent se db_pool estiver disponível
        if self.db_pool:
            self._study_agent = self._orchestrator.setup_study_agent(self.db_pool)
            logger.info("MessageHandler initialized with orchestrator and StudyAgent")
        else:
            logger.warning("No db_pool provided, StudyAgent will not be available")

    async def process_message(self, message: Message) -> str | None:
        """Process a Discord message through the agent system.

        Args:
            message: Discord message to process.

        Returns:
            Agent response, or None if message should be ignored.
        """
        # Ignore messages from bots
        if message.author.bot:
            return None

        # Ignore empty messages
        if not message.content or not message.content.strip():
            return None

        # Get user ID for memory isolation
        user_id = str(message.author.id)

        # Build context
        context = {
            "user_id": user_id,
            "username": message.author.name,
            "global_name": message.author.global_name,
            "channel_id": str(message.channel.id),
            "guild_id": str(message.guild.id) if message.guild else None,
            "guild_name": message.guild.name if message.guild else "DM",
            "is_dm": message.guild is None,
        }

        # Detect comando !ask para modo estudo rigoroso
        if message.content.strip().startswith("!ask "):
            return await self._handle_ask_command(message, user_id, context)

        user_token = hashlib.sha256(user_id.encode()).hexdigest()[:12]
        content_hash = hashlib.sha256(message.content.encode()).hexdigest()[:12]
        logger.info(
            "Processing message "
            f"user={user_token} message_id={message.id} "
            f"content_length={len(message.content)} content_hash={content_hash}"
        )

        try:
            # Ensure orchestrator is initialized
            if self._orchestrator is None:
                raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

            # Route and process through orchestrator
            response_chunks = []
            async for chunk in self._orchestrator.route_and_process(
                message=message.content,
                context=context,
                user_id=user_id,
                db_pool=self.db_pool,
            ):
                response_chunks.append(chunk)

            response = "".join(response_chunks)

            # Store conversation in database
            if self.db_pool:
                await self._store_conversation(
                    user_id=user_id,
                    channel_id=str(message.channel.id),
                    guild_id=str(message.guild.id) if message.guild else None,
                    user_message=message.content,
                    assistant_response=response,
                )

            return response

        except AgentCommunicationError as e:
            logger.error(f"Agent communication error: {e}")
            return f"Desculpe, ocorreu um erro ao processar sua mensagem: {e.message}"

        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}")
            return "Desculpe, ocorreu um erro inesperado. Por favor, tente novamente."

    def _check_ask_rate_limit(self, user_id: str) -> bool:
        """Verifica se o usuário excedeu o rate limit do comando !ask.

        Args:
            user_id: ID do usuário Discord.

        Returns:
            True se a requisição deve ser permitida, False se excedeu o limite.
        """
        now = time.time()
        window_start = now - self._ask_rate_limit_window

        # Limpar timestamps antigos
        if user_id in self._ask_rate_limit:
            self._ask_rate_limit[user_id] = [
                ts for ts in self._ask_rate_limit[user_id]
                if ts > window_start
            ]

        # Verificar limite
        request_count = len(self._ask_rate_limit.get(user_id, []))
        if request_count >= self._ask_rate_limit_max_requests:
            logger.warning(
                f"Rate limit excedido para usuário {user_id[:12]}: "
                f"{request_count} requisições em {self._ask_rate_limit_window}s"
            )
            return False

        # Adicionar timestamp atual
        if user_id not in self._ask_rate_limit:
            self._ask_rate_limit[user_id] = []
        self._ask_rate_limit[user_id].append(now)

        return True

    async def _handle_ask_command(
        self,
        message: Message,
        user_id: str,
        context: dict[str, Any],
    ) -> str:
        """Processa comando !ask usando StudyAgent para RAG rigoroso.

        Args:
            message: Discord message.
            user_id: User ID.
            context: Contexto do Discord.

        Returns:
            Resposta do StudyAgent ou mensagem de erro.
        """
        # Verificar rate limit (5 requisições por minuto por usuário)
        if not self._check_ask_rate_limit(user_id):
            remaining_time = self._ask_rate_limit_window  # Simplificado
            return f"❌ Você excedeu o limite de 5 requisições por minuto do comando !ask. Aguarde {remaining_time}s antes de tentar novamente."

        if self._study_agent is None:
            return "❌ StudyAgent não disponível. Verifique se o db_pool foi configurado."

        # Extrair pergunta após o prefixo !ask
        question = message.content.strip()[5:].strip()  # Remove "!ask "
        if not question:
            return "❌ Uso: `!ask <sua pergunta>` - Exemplo: `!ask quais são as qualificadoras do homicídio?`"

        start_time = asyncio.get_event_loop().time()

        try:
            # Criar request para StudyAgent
            request = StudyAgentRequest(
                question=question,
                user_id=user_id,
                category_filter=None,  # Busca em todas as categorias legais
                max_results=5,
                threshold=0.7,
            )

            # Processar com StudyAgent
            response = await self._study_agent.answer(request)

            # Logging estruturado
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"!ask command processed user_id={user_id[:12]} "
                f"question_length={len(question)} "
                f"confidence={response.confidence:.2f} "
                f"sources_count={len(response.sources)} "
                f"duration_ms={int(duration * 1000)}"
            )

            # Store conversation
            if self.db_pool:
                await self._store_conversation(
                    user_id=user_id,
                    channel_id=str(message.channel.id),
                    guild_id=str(message.guild.id) if message.guild else None,
                    user_message=message.content,
                    assistant_response=response.answer,
                )

            return response.answer

        except Exception as e:
            logger.error(f"Error processing !ask command: {e}")
            return f"❌ Erro ao processar pergunta: {e}"

    async def handle_general_message(
        self,
        message: Message,
        user_id: str,
        context: dict[str, Any],
    ) -> str:
        """Processa mensagens gerais (chat livre) usando o AgentOrchestrator.

        Args:
            message: Discord message.
            user_id: User ID.
            context: Contexto do Discord.

        Returns:
            Resposta do agente conversacional.
        """
        # Mensagem sem o prefixo !ask - usa chat livre
        user_message = message.content.strip()
        start_time = asyncio.get_event_loop().time()

        try:
            # Processar através do orchestrator (modo conversacional)
            response_chunks = []
            async for chunk in self._orchestrator.route_and_process(
                message=user_message,
                context=context,
                user_id=user_id,
                db_pool=self.db_pool,
            ):
                response_chunks.append(chunk)

            response = "".join(response_chunks)

            # Logging estruturado para chat livre
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"general_message processed user_id={user_id[:12]} "
                f"message_length={len(user_message)} "
                f"response_length={len(response)} "
                f"duration_ms={int(duration * 1000)}"
            )

            # Store conversation
            if self.db_pool:
                await self._store_conversation(
                    user_id=user_id,
                    channel_id=str(message.channel.id),
                    guild_id=str(message.guild.id) if message.guild else None,
                    user_message=user_message,
                    assistant_response=response,
                )

            return response

        except Exception as e:
            logger.error(f"Error processing general message: {e}")
            return "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."

    async def _store_conversation(
        self,
        user_id: str,
        channel_id: str,
        guild_id: str | None,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Store conversation in database.

        Args:
            user_id: User ID.
            channel_id: Channel ID.
            guild_id: Guild ID (None for DM).
            user_message: User's message.
            assistant_response: Bot's response.
        """
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    # Get or create user
                    user_uuid = await conn.fetchval(
                        """
                        INSERT INTO users (discord_id, created_at, updated_at)
                        VALUES ($1, NOW(), NOW())
                        ON CONFLICT (discord_id) DO UPDATE
                        SET updated_at = NOW()
                        RETURNING id
                        """,
                        user_id,
                    )

                    # Get or create session
                    session_uuid = await conn.fetchval(
                        """
                        INSERT INTO sessions (user_id, channel_id, guild_id, is_active, created_at, updated_at)
                        VALUES ($1::uuid, $2, $3, true, NOW(), NOW())
                        ON CONFLICT (user_id, channel_id) DO UPDATE
                        SET updated_at = NOW(), is_active = true
                        RETURNING id
                        """,
                        user_uuid,
                        channel_id,
                        guild_id,
                    )

                    # Insert user message
                    await conn.execute(
                        """
                        INSERT INTO messages (user_id, session_id, role, content, created_at)
                        VALUES ($1::uuid, $2::uuid, 'user', $3, NOW())
                        """,
                        user_uuid,
                        session_uuid,
                        user_message,
                    )

                    # Insert assistant response
                    await conn.execute(
                        """
                        INSERT INTO messages (user_id, session_id, role, content, created_at)
                        VALUES ($1::uuid, $2::uuid, 'assistant', $3, NOW())
                        """,
                        user_uuid,
                        session_uuid,
                        assistant_response,
                    )

                logger.debug("Stored conversation in database")

        except Exception as e:
            logger.warning(f"Failed to store conversation: {e}")

    async def get_conversation_history(
        self,
        user_id: str,
        channel_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get conversation history for a user/channel.

        Args:
            user_id: User ID.
            channel_id: Channel ID.
            limit: Maximum messages to retrieve.

        Returns:
            List of message dictionaries.
        """
        if not self.db_pool:
            return []

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        m.role,
                        m.content,
                        m.created_at
                    FROM messages m
                    JOIN sessions s ON m.session_id = s.id
                    JOIN users u ON m.user_id = u.id
                    WHERE u.discord_id = $1
                        AND s.channel_id = $2
                    ORDER BY m.created_at DESC
                    LIMIT $3
                    """,
                    user_id,
                    channel_id,
                    limit,
                )

                # Reverse to get chronological order
                return [
                    {
                        "role": row["role"],
                        "content": row["content"],
                        "created_at": row["created_at"],
                    }
                    for row in reversed(rows)
                ]

        except Exception as e:
            logger.warning(f"Failed to get conversation history: {e}")
            return []


# Global message handler instance
_message_handler: MessageHandler | None = None
_message_handler_lock = asyncio.Lock()


async def get_message_handler(
    bot: Bot,
    intent_classifier: IntentClassifier,
    db_pool=None,
) -> MessageHandler:
    """Get or create the global message handler.

    Args:
        bot: Discord bot instance.
        intent_classifier: Intent classifier.
        db_pool: Database connection pool.

    Returns:
        The MessageHandler instance.
    """
    global _message_handler

    if _message_handler is None:
        async with _message_handler_lock:
            if _message_handler is None:
                _message_handler = MessageHandler(bot, intent_classifier, db_pool)
                await _message_handler.initialize()

    return _message_handler
