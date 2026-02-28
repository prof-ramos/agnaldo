"""Decoradores utilitários para Agnaldo.

Decoradores comuns usados em todo o projeto:
- measure_time: Medir tempo de execução
- memoize_async: Cache assíncrono com TTL
"""

import asyncio
import functools
import hashlib
import time
from collections import OrderedDict
from typing import Any, Callable, TypeVar

from loguru import logger

P = TypeVar("P")
R = TypeVar("R")


def measure_time(
    operation_name: str | None = None,
    log_level: str = "DEBUG",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorador para medir tempo de execução de funções.

    Args:
        operation_name: Nome da operação (usa nome da função se None).
        log_level: Nível de log (DEBUG, INFO, WARNING).

    Returns:
        Decorador configurado.

    Example:
        >>> @measure_time()
        ... async def fetch_data(user_id: str) -> dict:
        ...     # Logs: "fetch_data completed in 45.23ms"
        ...     return {"data": "value"}
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        name = operation_name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start_time = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    log_func = getattr(logger, log_level.lower(), logger.debug)
                    log_func(f"{name} completed in {elapsed_ms:.2f}ms")

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    log_func = getattr(logger, log_level.lower(), logger.debug)
                    log_func(f"{name} completed in {elapsed_ms:.2f}ms")

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class AsyncMemoize:
    """Cache assíncrono com LRU eviction e TTL.

    Thread-safe com asyncio.Lock.

    Attributes:
        max_size: Tamanho máximo do cache.
        ttl_seconds: Tempo de vida em segundos (0 = sem TTL).
    """

    def __init__(self, max_size: int = 100, ttl_seconds: float = 300) -> None:
        """Inicializa o cache.

        Args:
            max_size: Número máximo de entradas.
            ttl_seconds: TTL em segundos (padrão 5 min).
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    def _hash_key(self, *args: Any, **kwargs: Any) -> str:
        """Gera hash único para argumentos."""
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    async def get(self, key: str) -> Any | None:
        """Obtém valor do cache se não expirou.

        Args:
            key: Chave do cache.

        Returns:
            Valor ou None se expirado/não existe.
        """
        async with self._lock:
            if key not in self._cache:
                return None

            timestamp, value = self._cache[key]

            # Verificar TTL
            if self.ttl_seconds > 0:
                age = time.time() - timestamp
                if age > self.ttl_seconds:
                    del self._cache[key]
                    logger.debug(f"Cache entry expired: {key}")
                    return None

            # Mover para o final (LRU)
            self._cache.move_to_end(key)
            return value

    async def set(self, key: str, value: Any) -> None:
        """Define valor no cache com eviction LRU.

        Args:
            key: Chave do cache.
            value: Valor a armazenar.
        """
        async with self._lock:
            # Remover entrada existente
            if key in self._cache:
                del self._cache[key]

            # Adicionar nova entrada
            self._cache[key] = (time.time(), value)

            # Eviction LRU
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
                logger.debug("Cache LRU eviction")

    async def clear(self) -> None:
        """Limpa todo o cache."""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")


# Cache global para memoize
_memoize_caches: dict[str, AsyncMemoize] = {}


def memoize_async(
    max_size: int = 100,
    ttl_seconds: float = 300,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorador de cache assíncrono com TTL.

    Args:
        max_size: Tamanho máximo do cache por função.
        ttl_seconds: Tempo de vida em segundos.

    Returns:
        Decorador configurado.

    Example:
        >>> @memoize_async(max_size=50, ttl_seconds=60)
        ... async def get_user_data(user_id: str) -> dict:
        ...     # Cache por 60 segundos
        ...     return expensive_db_query(user_id)
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        cache_key = f"{func.__module__}.{func.__name__}"

        if cache_key not in _memoize_caches:
            _memoize_caches[cache_key] = AsyncMemoize(
                max_size=max_size,
                ttl_seconds=ttl_seconds,
            )

        cache = _memoize_caches[cache_key]

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Gerar chave para argumentos
            key = cache._hash_key(*args, **kwargs)

            # Verificar cache
            cached = await cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached

            # Executar função
            result = await func(*args, **kwargs)

            # Armazenar em cache
            await cache.set(key, result)

            return result

        return wrapper

    return decorator


def clear_all_memoize_caches() -> None:
    """Limpa todos os caches de memoize_async.

    Útil para testes ou quando dados mudam.
    """
    for cache in _memoize_caches.values():
        asyncio.get_event_loop().run_until_complete(cache.clear())
    _memoize_caches.clear()
    logger.info("All memoize caches cleared")
