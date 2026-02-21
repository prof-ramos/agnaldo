"""Intent routing handlers for Discord bot."""

import random
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from .models import IntentCategory, IntentResult


class IntentRouter:
    """Route intents to appropriate handlers."""

    def __init__(self) -> None:
        """Initialize the router with empty handler registry."""
        self._handlers: dict[IntentCategory, Callable[[IntentResult], Awaitable[Any]]] = {}
        self._default_handler: Callable[[IntentResult], Awaitable[Any]] | None = None

    def register(
        self, category: IntentCategory, handler: Callable[[IntentResult], Awaitable[Any]]
    ) -> None:
        """Register a handler for an intent category.

        Args:
            category: Intent category to handle.
            handler: Async function that takes IntentResult and returns response.
        """
        self._handlers[category] = handler
        logger.debug(f"Registered handler for intent: {category}")

    def set_default(self, handler: Callable[[IntentResult], Awaitable[Any]]) -> None:
        """Set default handler for unknown intents.

        Args:
            handler: Async function that takes IntentResult and returns response.
        """
        self._default_handler = handler

    async def route(self, result: IntentResult) -> Any:
        """Route intent result to appropriate handler.

        Args:
            result: Intent classification result.

        Returns:
            Handler response or None if no handler found.
        """
        handler = self._handlers.get(result.intent)

        if handler is None:
            if self._default_handler:
                logger.debug(f"Using default handler for: {result.intent}")
                return await self._default_handler(result)
            logger.warning(f"No handler registered for intent: {result.intent}")
            return None

        logger.debug(f"Routing {result.intent} (confidence: {result.confidence:.2f})")
        return await handler(result)

    def has_handler(self, category: IntentCategory) -> bool:
        """Check if a handler is registered for a category."""
        return category in self._handlers

    def list_registered(self) -> list[IntentCategory]:
        """List all registered intent categories."""
        return list(self._handlers.keys())


# Default handlers that can be used as templates

async def handle_knowledge_query(result: IntentResult) -> str:
    """Handle knowledge query intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    topic = result.entities.get("topic", result.raw_text)
    return f"Searching knowledge base for: {topic}"


async def handle_definition(result: IntentResult) -> str:
    """Handle definition intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    return f"Here's a definition for: {result.raw_text}"


async def handle_greeting(result: IntentResult) -> str:
    """Handle greeting intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    responses = [
        "Hello! How can I help you today?",
        "Hi there! What would you like to know?",
        "Hey! I'm here to assist you.",
    ]

    return random.choice(responses)


async def handle_help(result: IntentResult) -> str:
    """Handle help intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    return (
        "I can help you with:\n"
        "- Answering questions\n"
        "- Searching the knowledge base\n"
        "- Analyzing data\n"
        "- Managing the knowledge graph\n\n"
        "Just ask me anything!"
    )


async def handle_status(result: IntentResult) -> str:
    """Handle status intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    return "All systems operational! Ready to assist you."


async def handle_graph_query(result: IntentResult) -> str:
    """Handle graph query intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    nodes = result.entities.get("potential_nodes", [])
    if nodes:
        return f"Querying graph for nodes: {', '.join(map(str, nodes))}"
    return "Querying knowledge graph..."


async def handle_memory_store(result: IntentResult) -> str:
    """Handle memory storage intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    return f"Storing in memory: {result.raw_text[:50]}..."


async def handle_memory_retrieve(result: IntentResult) -> str:
    """Handle memory retrieval intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    return "Retrieving from memory..."


async def handle_search(result: IntentResult) -> str:
    """Handle search intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    query = result.raw_text
    return f"Searching for: {query}"


async def handle_analyze(result: IntentResult) -> str:
    """Handle analysis intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    return f"Analyzing: {result.raw_text[:50]}..."


async def handle_compute(result: IntentResult) -> str:
    """Handle computation intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    return "Computing... (this feature is coming soon)"


async def handle_farewell(result: IntentResult) -> str:
    """Handle farewell intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    responses = [
        "Goodbye! Have a great day!",
        "See you later!",
        "Bye! Feel free to come back anytime.",
    ]

    return random.choice(responses)


async def handle_thanks(result: IntentResult) -> str:
    """Handle thanks intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    responses = [
        "You're welcome!",
        "Happy to help!",
        "Anytime!",
        "Glad I could assist!",
    ]

    return random.choice(responses)


async def handle_explanation(result: IntentResult) -> str:
    """Handle explanation intents.

    Args:
        result: Intent classification result.

    Returns:
        Response message.
    """
    return f"Here's an explanation about: {result.raw_text}"


def setup_default_router(router: IntentRouter) -> None:
    """Configure router with all default handlers.

    Args:
        router: IntentRouter instance to configure.
    """
    router.register(IntentCategory.KNOWLEDGE_QUERY, handle_knowledge_query)
    router.register(IntentCategory.DEFINITION, handle_definition)
    router.register(IntentCategory.GREETING, handle_greeting)
    router.register(IntentCategory.HELP, handle_help)
    router.register(IntentCategory.STATUS, handle_status)
    router.register(IntentCategory.GRAPH_QUERY, handle_graph_query)
    router.register(IntentCategory.MEMORY_STORE, handle_memory_store)
    router.register(IntentCategory.MEMORY_RETRIEVE, handle_memory_retrieve)
    router.register(IntentCategory.SEARCH, handle_search)
    router.register(IntentCategory.ANALYZE, handle_analyze)
    router.register(IntentCategory.COMPUTE, handle_compute)
    router.register(IntentCategory.FAREWELL, handle_farewell)
    router.register(IntentCategory.THANKS, handle_thanks)
    router.register(IntentCategory.EXPLANATION, handle_explanation)
