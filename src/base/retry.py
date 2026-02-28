"""Configuração de retry com tenacity.

Fornece decoradores e configurações de retry para operações
que podem falhar temporariamente.

Uso:
    from src.base import with_retry, RetryConfig

    @with_retry(RetryConfig(max_attempts=3))
    async def fetch_data():
        ...
"""

import asyncio
import functools
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_random,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

from src.base.logging import get_logger

P = TypeVar("P")
R = TypeVar("R")


@dataclass
class RetryConfig:
    """Configuração de retry.

    Attributes:
        max_attempts: Número máximo de tentativas.
        max_delay_seconds: Tempo máximo total de retry.
        min_wait_seconds: Tempo mínimo de espera entre tentativas.
        max_wait_seconds: Tempo máximo de espera entre tentativas.
        exponential_base: Base para backoff exponencial.
        jitter: Se deve adicionar jitter aleatório.
        retryable_exceptions: Tupla de exceções que devem ser retentadas.
    """

    max_attempts: int = 3
    max_delay_seconds: float = 30.0
    min_wait_seconds: float = 0.5
    max_wait_seconds: float = 5.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )

    def __post_init__(self) -> None:
        """Valida configuração."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.min_wait_seconds < 0:
            raise ValueError("min_wait_seconds must be >= 0")
        if self.max_wait_seconds < self.min_wait_seconds:
            raise ValueError("max_wait_seconds must be >= min_wait_seconds")


def with_retry(
    config: RetryConfig | None = None,
    *,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorador para retry automático com backoff exponencial.

    Args:
        config: Configuração de retry. Usa padrão se None.
        on_retry: Callback chamado a cada retry (attempt_number, exception).

    Returns:
        Função decorada com retry.

    Example:
        >>> @with_retry(RetryConfig(max_attempts=5))
        ... async def fetch_api():
        ...     response = await httpx.get("https://api.example.com")
        ...     return response.json()
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        log = get_logger(func.__module__)

        # Configurar estratégias de espera
        wait_strategy = wait_exponential(
            multiplier=config.min_wait_seconds,
            min=config.min_wait_seconds,
            max=config.max_wait_seconds,
            exp_base=config.exponential_base,
        )
        if config.jitter:
            wait_strategy = wait_strategy + wait_random(0, 1)

        # Configurar condições de parada
        stop_strategy = stop_after_attempt(config.max_attempts)
        if config.max_delay_seconds > 0:
            stop_strategy = stop_strategy | stop_after_delay(config.max_delay_seconds)

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            retryer = AsyncRetrying(
                stop=stop_strategy,
                wait=wait_strategy,
                retry=retry_if_exception_type(config.retryable_exceptions),
                before_sleep=before_sleep_log(log, "WARNING"),
                after=after_log(log, "DEBUG"),
                reraise=True,
            )

            attempt_count = 0

            async def call_func() -> R:
                nonlocal attempt_count
                attempt_count += 1
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if on_retry and attempt_count < config.max_attempts:
                        on_retry(attempt_count, e)
                    raise

            try:
                return await retryer(call_func)
            except RetryError as e:
                log.error(
                    f"Retry failed after {config.max_attempts} attempts",
                    function=func.__name__,
                    error=str(e.last_attempt.exception()),
                )
                raise e.last_attempt.exception() from e

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Para funções síncronas, converter para async e voltar
            async def async_call() -> R:
                return func(*args, **kwargs)

            # Usar event loop existente ou criar um
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(async_wrapper.__wrapped__(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Configurações predefinidas
RETRY_DATABASE = RetryConfig(
    max_attempts=3,
    min_wait_seconds=0.1,
    max_wait_seconds=2.0,
    retryable_exceptions=(ConnectionError, TimeoutError, OSError),
)

RETRY_API = RetryConfig(
    max_attempts=5,
    min_wait_seconds=1.0,
    max_wait_seconds=10.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(ConnectionError, TimeoutError, OSError),
)

RETRY_CRITICAL = RetryConfig(
    max_attempts=10,
    max_delay_seconds=60.0,
    min_wait_seconds=1.0,
    max_wait_seconds=30.0,
    exponential_base=2.0,
    jitter=True,
)
