"""Error handling utilities for the Agnaldo Discord bot.

This module provides decorators and utilities for robust error handling,
including retry logic with exponential backoff, circuit breaker pattern,
and standardized error response formatting.
"""

import asyncio
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

import openai
from loguru import logger
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.exceptions import (
    AgentCommunicationError,
    AgnaldoError,
    DatabaseError,
    EmbeddingGenerationError,
    IntentClassificationError,
    MemoryServiceError,
    RateLimitError,
    SupabaseConnectionError,
)

# Type variables for generic function wrappers
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


# Retry decorators
def retry_on_database_error(func: F) -> F:
    """Decorator to retry database operations with exponential backoff.

    Retries up to 3 times with exponential wait starting at 2 seconds, max 10 seconds.
    Only retries on DatabaseError and its subclasses.

    Args:
        func: The function to decorate.

    Returns:
        The wrapped function with retry logic.

    Example:
        >>> @retry_on_database_error
        ... def fetch_user(user_id: int):
        ...     return db.query(user_id)
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseError),
        before_sleep=before_sleep_log(logger, 30),
        reraise=True,
    )(func)


def retry_on_openai_rate_limit(func: F) -> F:
    """Decorator to retry OpenAI API calls on rate limit errors.

    Retries up to 5 times with exponential wait starting at 4 seconds, max 60 seconds.
    Only retries on openai.RateLimitError.

    Args:
        func: The function to decorate.

    Returns:
        The wrapped function with retry logic.

    Example:
        >>> @retry_on_openai_rate_limit
        ... async def generate_completion(prompt: str):
        ...     return await client.chat.completions.create(messages=prompt)
    """
    return retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(openai.RateLimitError),
        before_sleep=before_sleep_log(logger, 30),
        reraise=True,
    )(func)


def retry_on_memory_error(func: F) -> F:
    """Decorator to retry memory operations with exponential backoff.

    Retries up to 3 times with exponential wait starting at 2 seconds, max 10 seconds.
    Only retries on MemoryServiceError and its subclasses.

    Args:
        func: The function to decorate.

    Returns:
        The wrapped function with retry logic.

    Example:
        >>> @retry_on_memory_error
        ... async def search_embeddings(query: str):
        ...     return await vector_store.search(query)
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(MemoryServiceError),
        before_sleep=before_sleep_log(logger, 30),
        reraise=True,
    )(func)


# Circuit Breaker Pattern
class CircuitState(Enum):
    """States for the circuit breaker pattern.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through.
    - OPEN: Circuit is tripped, requests fail immediately.
    - HALF_OPEN: Testing if service has recovered.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures.

    The circuit breaker monitors failures and trips (opens) after a threshold
    is reached, preventing further calls to a failing service. After a timeout,
    it enters HALF_OPEN state to test if the service has recovered.

    Attributes:
        failure_threshold: Number of failures before tripping the circuit.
        timeout: Seconds to wait before attempting recovery.
        state: Current circuit state (CLOSED, OPEN, HALF_OPEN).
        failure_count: Current number of consecutive failures.
        last_failure_time: Timestamp of the last failure.
        recovery_attempt_count: Number of recovery attempts in HALF_OPEN.

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        >>> @breaker
        ... async def call_external_service():
        ...     return await external_api.request()
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60) -> None:
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before tripping.
            timeout: Seconds to wait before attempting recovery.
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.last_failure_time: float | None = None
        self.recovery_attempt_count: int = 0
        self._lock = threading.Lock()

    def __call__(self, func: F) -> F:
        """Decorator to apply circuit breaker to a function.

        Args:
            func: The function to protect with circuit breaker.

        Returns:
            The wrapped function with circuit breaker logic.
        """

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self._call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self._call_sync(func, *args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    async def _call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async function with circuit breaker protection."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker entering HALF_OPEN state")
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN. Rejecting call to {func.__name__}. "
                        f"Retry after {self._get_remaining_timeout():.1f} seconds."
                    )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _call_sync(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute sync function with circuit breaker protection."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker entering HALF_OPEN state")
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN. Rejecting call to {func.__name__}. "
                        f"Retry after {self._get_remaining_timeout():.1f} seconds."
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout

    def _get_remaining_timeout(self) -> float:
        """Get remaining seconds before recovery attempt."""
        if self.last_failure_time is None:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.timeout - elapsed)

    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker recovered to CLOSED state")
                self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.recovery_attempt_count = 0
            self.last_failure_time = None

    def _on_failure(self) -> None:
        """Handle failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.recovery_attempt_count += 1
                logger.warning(
                    f"Circuit breaker recovery attempt {self.recovery_attempt_count} failed. "
                    f"Returning to OPEN state."
                )
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker tripped after {self.failure_count} failures. "
                    f"Entering OPEN state for {self.timeout} seconds."
                )
                self.state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.recovery_attempt_count = 0
        logger.info("Circuit breaker manually reset to CLOSED state")


class CircuitBreakerError(AgnaldoError):
    """Exception raised when circuit breaker is OPEN."""

    pass


# Error Response Model
class ErrorResponse:
    """Standardized error response model.

    Provides consistent error response formatting across the application,
    suitable for API responses and user-facing error messages.

    Attributes:
        error: Human-readable error message.
        error_code: Machine-readable error code identifier.
        details: Optional dictionary with additional error context.
        retry_after: Optional seconds to wait before retrying.
        timestamp: ISO 8601 timestamp when the error occurred.

    Example:
        >>> response = ErrorResponse(
        ...     error="Database connection failed",
        ...     error_code="DB_CONNECTION_ERROR",
        ...     details={"host": "localhost"},
        ...     retry_after=30
        ... )
        >>> print(response.to_dict())
    """

    def __init__(
        self,
        error: str,
        error_code: str,
        details: dict[str, Any] | None = None,
        retry_after: int | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Initialize the error response.

        Args:
            error: Human-readable error message.
            error_code: Machine-readable error code identifier.
            details: Optional dictionary with additional error context.
            retry_after: Optional seconds to wait before retrying.
            timestamp: ISO 8601 timestamp when the error occurred (defaults to now).
        """
        self.error = error
        self.error_code = error_code
        self.details = details or {}
        self.retry_after = retry_after
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert error response to dictionary.

        Returns:
            Dictionary representation of the error response.
        """
        result: dict[str, Any] = {
            "error": self.error,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.details:
            result["details"] = self.details
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
        return result

    def __str__(self) -> str:
        """Return string representation of error response."""
        return f"{self.error_code}: {self.error}"


# Error handler function
def handle_error(error: Exception) -> ErrorResponse:
    """Convert an exception into a standardized ErrorResponse.

    Maps different exception types to appropriate error codes and messages,
    extracting relevant information for debugging and user feedback.

    Args:
        error: The exception to handle.

    Returns:
        An ErrorResponse with appropriate error code and details.

    Example:
        >>> try:
        ...     database.query()
        ... except DatabaseError as e:
        ...     response = handle_error(e)
        ...     return response.to_dict()
    """
    timestamp = datetime.now(timezone.utc)

    # AgnaldoError hierarchy
    if isinstance(error, SupabaseConnectionError):
        return ErrorResponse(
            error=str(error),
            error_code="SUPABASE_CONNECTION_ERROR",
            details={
                **error.details,
                "status_code": error.status_code,
                "operation": error.operation,
            },
            timestamp=timestamp,
        )

    if isinstance(error, EmbeddingGenerationError):
        return ErrorResponse(
            error=str(error),
            error_code="EMBEDDING_GENERATION_ERROR",
            details={
                **error.details,
                "model": error.model,
                "text_length": error.text_length,
            },
            timestamp=timestamp,
        )

    if isinstance(error, DatabaseError):
        return ErrorResponse(
            error=str(error),
            error_code="DATABASE_ERROR",
            details={**error.details, "operation": error.operation},
            timestamp=timestamp,
        )

    if isinstance(error, MemoryServiceError):
        return ErrorResponse(
            error=str(error),
            error_code="MEMORY_ERROR",
            details={**error.details, "memory_type": error.memory_type},
            timestamp=timestamp,
        )

    if isinstance(error, IntentClassificationError):
        return ErrorResponse(
            error=str(error),
            error_code="INTENT_CLASSIFICATION_ERROR",
            details={**error.details, "confidence": error.confidence},
            timestamp=timestamp,
        )

    if isinstance(error, RateLimitError):
        return ErrorResponse(
            error=str(error),
            error_code="RATE_LIMIT_ERROR",
            details={
                **error.details,
                "limit": error.limit,
            },
            retry_after=error.retry_after,
            timestamp=timestamp,
        )

    if isinstance(error, AgentCommunicationError):
        return ErrorResponse(
            error=str(error),
            error_code="AGENT_COMMUNICATION_ERROR",
            details={
                **error.details,
                "source_agent": error.source_agent,
                "target_agent": error.target_agent,
            },
            timestamp=timestamp,
        )

    if isinstance(error, AgnaldoError):
        return ErrorResponse(
            error=str(error),
            error_code="AGNALDO_ERROR",
            details=error.details,
            timestamp=timestamp,
        )

    # OpenAI errors
    if isinstance(error, openai.RateLimitError):
        return ErrorResponse(
            error="OpenAI API rate limit exceeded",
            error_code="OPENAI_RATE_LIMIT_ERROR",
            retry_after=60,
            timestamp=timestamp,
        )

    if isinstance(error, openai.APIConnectionError):
        return ErrorResponse(
            error="Failed to connect to OpenAI API",
            error_code="OPENAI_CONNECTION_ERROR",
            retry_after=10,
            timestamp=timestamp,
        )

    if isinstance(error, openai.AuthenticationError):
        return ErrorResponse(
            error="OpenAI API authentication failed",
            error_code="OPENAI_AUTH_ERROR",
            timestamp=timestamp,
        )

    if isinstance(error, openai.APIError):
        return ErrorResponse(
            error=f"OpenAI API error: {str(error)}",
            error_code="OPENAI_API_ERROR",
            timestamp=timestamp,
        )

    # Circuit breaker
    if isinstance(error, CircuitBreakerError):
        return ErrorResponse(
            error=str(error),
            error_code="CIRCUIT_BREAKER_OPEN",
            retry_after=30,
            timestamp=timestamp,
        )

    # Generic exceptions
    return ErrorResponse(
        error=f"Unexpected error: {type(error).__name__}: {str(error)}",
        error_code="INTERNAL_ERROR",
        timestamp=timestamp,
    )
