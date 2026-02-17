"""Custom exceptions for the Agnaldo Discord bot.

This module defines the hierarchy of custom exceptions used throughout the application,
providing clear error categorization and descriptive error messages.
"""


class AgnaldoError(Exception):
    """Base exception for all Agnaldo-specific errors.

    All custom exceptions in the application should inherit from this base class.
    It provides a consistent interface for error handling and logging.

    Attributes:
        message: Human-readable description of the error.
        details: Optional dictionary with additional error context.

    Example:
        >>> raise AgnaldoError("Something went wrong")
        AgnaldoError: Something went wrong
    """

    def __init__(self, message: str, details: dict | None = None) -> None:
        """Initialize the exception with a message and optional details.

        Args:
            message: Human-readable description of the error.
            details: Optional dictionary with additional error context.
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return the error message."""
        return self.message


class DatabaseError(AgnaldoError):
    """Exception raised for database-related errors.

    This exception is used when operations involving database connections,
    queries, or transactions fail. It encompasses issues with PostgreSQL,
    Supabase, and SQLAlchemy operations.

    Attributes:
        message: Description of the database error.
        operation: The database operation that failed (optional).
        details: Additional error context.

    Example:
        >>> raise DatabaseError("Failed to connect to database", operation="connect")
    """

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize the database error.

        Args:
            message: Description of the database error.
            operation: The database operation that failed.
            details: Additional error context.
        """
        self.operation = operation
        if operation and not details:
            details = {"operation": operation}
        elif operation and details:
            details["operation"] = operation
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return the error message with operation context if available."""
        if self.operation:
            return f"Database error in '{self.operation}': {self.message}"
        return f"Database error: {self.message}"


class MemoryServiceError(AgnaldoError):
    """Exception raised for memory/knowledge base related errors.

    This exception covers errors in vector operations, embedding generation,
    similarity searches, and knowledge graph operations.

    Attributes:
        message: Description of the memory error.
        memory_type: Type of memory operation (vector, graph, etc).
        details: Additional error context.

    Example:
        >>> raise MemoryServiceError("Failed to generate embeddings", memory_type="vector")
    """

    def __init__(
        self,
        message: str,
        memory_type: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize the memory error.

        Args:
            message: Description of the memory error.
            memory_type: Type of memory operation (vector, graph, etc).
            details: Additional error context.
        """
        self.memory_type = memory_type
        if memory_type and not details:
            details = {"memory_type": memory_type}
        elif memory_type and details:
            details["memory_type"] = memory_type
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return the error message with memory type context if available."""
        if self.memory_type:
            return f"Memory error ({self.memory_type}): {self.message}"
        return f"Memory error: {self.message}"


class IntentClassificationError(AgnaldoError):
    """Exception raised when intent classification fails.

    This exception is raised when the AI model cannot reliably classify
    a user's intent or when the classification process encounters errors.

    Attributes:
        message: Description of the classification error.
        confidence: The confidence score of the failed classification.
        details: Additional error context.

    Example:
        >>> raise IntentClassificationError("Low confidence score", confidence=0.3)
    """

    def __init__(
        self,
        message: str,
        confidence: float | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize the intent classification error.

        Args:
            message: Description of the classification error.
            confidence: The confidence score of the failed classification.
            details: Additional error context.
        """
        self.confidence = confidence
        if confidence is not None and not details:
            details = {"confidence": confidence}
        elif confidence is not None and details:
            details["confidence"] = confidence
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return the error message with confidence context if available."""
        if self.confidence is not None:
            return f"Intent classification error (confidence: {self.confidence:.2f}): {self.message}"
        return f"Intent classification error: {self.message}"


class RateLimitError(AgnaldoError):
    """Exception raised when API rate limits are exceeded.

    This exception is raised when external APIs (OpenAI, Discord, etc.)
    return rate limit errors. It includes retry information.

    Attributes:
        message: Description of the rate limit error.
        retry_after: Seconds to wait before retrying.
        limit: The rate limit that was exceeded.
        details: Additional error context.

    Example:
        >>> raise RateLimitError("Too many requests", retry_after=60, limit=100)
    """

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        limit: int | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Description of the rate limit error.
            retry_after: Seconds to wait before retrying.
            limit: The rate limit that was exceeded.
            details: Additional error context.
        """
        self.retry_after = retry_after
        self.limit = limit
        if not details:
            details = {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        if limit is not None:
            details["limit"] = limit
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return the error message with retry information if available."""
        parts = ["Rate limit error"]
        if self.limit is not None:
            parts.append(f"(limit: {self.limit})")
        parts.append(f": {self.message}")
        if self.retry_after is not None:
            parts.append(f" - Retry after {self.retry_after} seconds")
        return "".join(parts)


class AgentCommunicationError(AgnaldoError):
    """Exception raised for agent-to-agent communication failures.

    This exception is raised when agents in the multi-agent system
    cannot communicate or when message passing fails.

    Attributes:
        message: Description of the communication error.
        source_agent: The agent that sent the message.
        target_agent: The intended recipient agent.
        details: Additional error context.

    Example:
        >>> raise AgentCommunicationError("Message timeout", source_agent="planner", target_agent="executor")
    """

    def __init__(
        self,
        message: str,
        source_agent: str | None = None,
        target_agent: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize the agent communication error.

        Args:
            message: Description of the communication error.
            source_agent: The agent that sent the message.
            target_agent: The intended recipient agent.
            details: Additional error context.
        """
        self.source_agent = source_agent
        self.target_agent = target_agent
        if not details:
            details = {}
        if source_agent is not None:
            details["source_agent"] = source_agent
        if target_agent is not None:
            details["target_agent"] = target_agent
        super().__init__(message, details)

    def __str__(self) -> str:
        """Return the error message with agent context if available."""
        if self.source_agent and self.target_agent:
            return f"Agent communication error ({self.source_agent} -> {self.target_agent}): {self.message}"
        if self.source_agent:
            return f"Agent communication error (from {self.source_agent}): {self.message}"
        if self.target_agent:
            return f"Agent communication error (to {self.target_agent}): {self.message}"
        return f"Agent communication error: {self.message}"


class SupabaseConnectionError(DatabaseError):
    """Exception raised for Supabase-specific connection errors.

    This exception is specialized for Supabase client connection issues,
    authentication failures, and service unavailability.

    Attributes:
        message: Description of the Supabase connection error.
        status_code: HTTP status code from Supabase response.
        details: Additional error context.

    Example:
        >>> raise SupabaseConnectionError("Invalid API key", status_code=401)
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        operation: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize the Supabase connection error.

        Args:
            message: Description of the Supabase connection error.
            status_code: HTTP status code from Supabase response.
            operation: The database operation that failed.
            details: Additional error context.
        """
        self.status_code = status_code
        if not details:
            details = {}
        if status_code is not None:
            details["status_code"] = status_code
        super().__init__(message, operation=operation, details=details)

    def __str__(self) -> str:
        """Return the error message with status code if available."""
        if self.status_code:
            return f"Supabase connection error (HTTP {self.status_code}): {self.message}"
        return f"Supabase connection error: {self.message}"


class EmbeddingGenerationError(MemoryServiceError):
    """Exception raised when embedding generation fails.

    This exception is specialized for errors during vector embedding
    creation using models like OpenAI's text-embedding-3 or sentence-transformers.

    Attributes:
        message: Description of the embedding generation error.
        model: The embedding model that failed.
        text_length: Length of the text that failed to embed.
        details: Additional error context.

    Example:
        >>> raise EmbeddingGenerationError("Token limit exceeded", model="text-embedding-3-large", text_length=10000)
    """

    def __init__(
        self,
        message: str,
        model: str | None = None,
        text_length: int | None = None,
        memory_type: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize the embedding generation error.

        Args:
            message: Description of the embedding generation error.
            model: The embedding model that failed.
            text_length: Length of the text that failed to embed.
            memory_type: Type of memory operation (defaults to "vector").
            details: Additional error context.
        """
        self.model = model
        self.text_length = text_length
        if memory_type is None:
            memory_type = "vector"
        if not details:
            details = {}
        if model is not None:
            details["model"] = model
        if text_length is not None:
            details["text_length"] = text_length
        super().__init__(message, memory_type=memory_type, details=details)

    def __str__(self) -> str:
        """Return the error message with model context if available."""
        parts = ["Embedding generation error"]
        if self.model:
            parts.append(f"({self.model})")
        parts.append(f": {self.message}")
        if self.text_length is not None:
            parts.append(f" (text length: {self.text_length})")
        return "".join(parts)
