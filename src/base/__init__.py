"""Módulo base do Agnaldo.

Este módulo contém classes e utilitários fundamentais usados em todo o projeto:
- Logger estruturado para JSON logging
- Exceções customizadas padronizadas
- Decoradores utilitários
- Configuração de retry
"""

from src.base.decorators import measure_time, memoize_async
from src.base.exceptions import (
    AgnaldoError,
    ConfigurationError,
    DatabaseError,
    ExternalServiceError,
    ValidationError,
)
from src.base.logging import get_logger, setup_logging
from src.base.retry import RetryConfig, with_retry

__all__ = [
    "AgnaldoError",
    "ConfigurationError",
    "DatabaseError",
    "ExternalServiceError",
    "ValidationError",
    "get_logger",
    "setup_logging",
    "measure_time",
    "memoize_async",
    "RetryConfig",
    "with_retry",
]
