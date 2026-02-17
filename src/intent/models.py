"""Intent detection models."""

from enum import Enum
from dataclasses import dataclass
from typing import Any


class IntentCategory(str, Enum):
    """Intent categories for Discord bot commands."""

    # Knowledge & Information
    KNOWLEDGE_QUERY = "knowledge_query"
    DEFINITION = "definition"
    EXPLANATION = "explanation"

    # Actions & Operations
    SEARCH = "search"
    COMPUTE = "compute"
    ANALYZE = "analyze"

    # Conversational
    GREETING = "greeting"
    FAREWELL = "farewell"
    THANKS = "thanks"

    # Bot Management
    HELP = "help"
    STATUS = "status"

    # Graph & Memory
    GRAPH_QUERY = "graph_query"
    MEMORY_STORE = "memory_store"
    MEMORY_RETRIEVE = "memory_retrieve"


@dataclass
class IntentResult:
    """Result of intent classification."""

    intent: IntentCategory
    confidence: float
    entities: dict[str, Any]
    raw_text: str

    def __post_init__(self) -> None:
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
