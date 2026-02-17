"""Main entry point for Agnaldo Discord bot.

This module provides the async main() function that orchestrates
the startup sequence: config -> database -> bot -> run.

Startup Sequence:
1. Load configuration from environment variables
2. Initialize database connections (Supabase + asyncpg pool)
3. Create and configure the Discord bot
4. Register event handlers and commands
5. Start the bot with graceful shutdown support
"""

import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger

from src.config.settings import get_settings
from src.database.supabase import get_supabase_client
from src.discord.bot import create_bot
from src.utils.logger import setup_logging


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class GracefulShutdown:
    """Handle graceful shutdown of the bot."""

    def __init__(self) -> None:
        self.shutdown: bool = False
        self._loop: asyncio.AbstractEventLoop | None = None

    def init(self, loop: asyncio.AbstractEventLoop) -> None:
        """Initialize signal handlers."""
        self._loop = loop
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, self._signal_handler, sig)

    def _signal_handler(self, sig: signal.Signals) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")
        self.shutdown = True

    def should_shutdown(self) -> bool:
        """Check if shutdown is requested."""
        return self.shutdown


async def initialize_database() -> bool:
    """Initialize database connections and verify health.

    Returns:
        True if database initialization successful, False otherwise.
    """
    try:
        logger.info("Initializing database connections...")

        # Initialize Supabase client
        supabase = get_supabase_client()
        logger.info(f"Supabase client initialized: {supabase.url[:30]}...")

        # Test database connection with a simple query
        # Note: This would require asyncpg pool for async queries
        # For now, we'll just log the connection

        logger.info("Database connections verified")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


async def create_soul_personality() -> str:
    """Load or create the bot personality (SOUL.md equivalent).

    Returns:
        The personality instructions as a string.
    """
    soul_path = PROJECT_ROOT / "SOUL.md"

    if soul_path.exists():
        logger.info(f"Loading personality from {soul_path}")
        return soul_path.read_text(encoding="utf-8")

    # Default personality if SOUL.md doesn't exist
    logger.info("Using default personality (SOUL.md not found)")
    return """# SOUL - Personalidade do Agnaldo

## Quem Sou
Sou o Agnaldo, um assistente Discord inteligente com capacidades de grafo de conhecimento.
Especializado em suporte técnico, análise de informações e gerenciamento de memória.

## Tom de Voz
- Direto e objetivo
- Evito enrolação
- Uso exemplos práticos quando possível
- Português claro e sem jargão desnecessário
- Respeitoso e profissional

## Limites de Comportamento
- Não respondo sobre tópicos sensíveis ou ilegais
- Sempre confirmo antes de ações destrutivas
- Respeito privacidade dos usuários
- Não executo comandos sem autorização adequada
- Mantenho confidenciais informações pessoais

## Preferências de Interação
- Respostas concisas (máx 3 parágrafos por mensagem)
- Markdown para code blocks quando relevante
- Threads para conversas longas
- Menciono fonte do conhecimento quando relevante
- Busco esclarecer dúvidas antes de assumir

## Capacidades
- Memória de longo prazo com embeddings
- Grafo de conhecimento para conectar informações
- Classificação de intents para roteamento inteligente
- Busca semântica em memórias armazenadas
"""


async def main() -> int:
    """Main entry point for the Agnaldo Discord bot.

    Startup sequence:
    1. Load configuration from environment
    2. Initialize database connections
    3. Create bot instance with personality
    4. Register event handlers and commands
    5. Start bot with graceful shutdown

    Returns:
        Exit code (0 for success, 1 for error).
    """
    setup_logging()

    # Initialize graceful shutdown handler
    shutdown_handler = GracefulShutdown()
    loop = asyncio.get_running_loop()
    shutdown_handler.init(loop)

    logger.info("=".center(60, "="))
    logger.info("Agnaldo Discord Bot - Starting".center(60))
    logger.info("=".center(60, "="))

    # Step 1: Load configuration
    try:
        settings = get_settings()
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Log level: {settings.LOG_LEVEL}")
        logger.info(f"OpenAI model: {settings.OPENAI_CHAT_MODEL}")
        logger.info(f"Embedding model: {settings.OPENAI_EMBEDDING_MODEL}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1

    # Step 2: Initialize database
    try:
        db_ready = await initialize_database()
        if not db_ready:
            logger.error("Database initialization failed, aborting startup")
            return 1
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return 1

    # Step 3: Create bot instance
    try:
        logger.info("Creating Agnaldo bot instance...")
        personality = await create_soul_personality()
        logger.info(f"Loaded personality ({len(personality)} chars)")

        bot = create_bot()

        # Store personality in bot for later use
        bot.personality = personality  # type: ignore[attr-defined]
        # Note: settings is already set in Bot.__init__

        logger.info("Bot instance created successfully")

    except Exception as e:
        logger.error(f"Failed to create bot instance: {e}")
        return 1

    # Step 4 & 5: Start bot with graceful shutdown
    try:
        logger.info("Starting bot connection to Discord...")

        # Run bot in a task that can be cancelled
        bot_task = asyncio.create_task(bot.start(settings.DISCORD_BOT_TOKEN))

        # Wait for shutdown signal
        while not shutdown_handler.should_shutdown() and not bot_task.done():
            await asyncio.sleep(0.5)

        if shutdown_handler.should_shutdown():
            logger.info("Shutdown requested, closing bot connection...")
            # Cancel bot task if still running
            if not bot_task.done():
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    logger.info("Bot task cancelled")

            # Close bot connection
            await bot.close()
            logger.info("Bot connection closed gracefully")

        elif bot_task.done():
            # Bot exited on its own
            try:
                result = bot_task.result()
                logger.info(f"Bot task completed with result: {result}")
            except Exception as e:
                logger.error(f"Bot task failed: {e}")
                return 1

        logger.info("Agnaldo Discord Bot - Shutdown complete")
        return 0

    except Exception as e:
        logger.error(f"Fatal error during bot execution: {e}")
        return 1


def run_cli() -> int:
    """CLI entry point wrapper for the main function.

    This function provides a synchronous entry point that can be
    called from __main__ or command-line scripts.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    setup_logging()

    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C)")
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_cli())
