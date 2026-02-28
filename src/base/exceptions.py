"""Exceções customizadas do Agnaldo.

Hierarquia de exceções:
    AgnaldoError (base)
    ├── ValidationError
    ├── ConfigurationError
    ├── DatabaseError
    └── ExternalServiceError
        ├── AgentCommunicationError
        ├── MemoryServiceError
        └── EmbeddingGenerationError
"""

from typing import Any


class AgnaldoError(Exception):
    """Exceção base do Agnaldo.

    Todas as exceções customizadas herdam desta classe.

    Attributes:
        message: Mensagem de erro.
        details: Detalhes adicionais do erro.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.details = details or {}

    def __str__(self) -> str:
        result = super().__str__()
        if self.details:
            result += f" | Details: {self.details}"
        return result

    def to_dict(self) -> dict[str, Any]:
        """Converte exceção para dicionário para logs."""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "details": self.details,
        }


class ValidationError(AgnaldoError):
    """Erro de validação de dados."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: Any = None,
    ) -> None:
        details = {"field": field, "value": str(value)} if field else None
        super().__init__(message, details=details)


class ConfigurationError(AgnaldoError):
    """Erro de configuração do sistema."""

    def __init__(
        self,
        message: str,
        *,
        config_key: str | None = None,
    ) -> None:
        details = {"config_key": config_key} if config_key else None
        super().__init__(message, details=details)


class DatabaseError(AgnaldoError):
    """Erro de operação de banco de dados."""

    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        query: str | None = None,
    ) -> None:
        details = {"operation": operation}
        if query:
            details["query"] = query[:200]  # Truncate long queries
        super().__init__(message, details=details)


class ExternalServiceError(AgnaldoError):
    """Erro em serviço externo (API, Discord, etc)."""

    def __init__(
        self,
        message: str,
        *,
        service: str | None = None,
        status_code: int | None = None,
    ) -> None:
        details = {"service": service}
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details=details)


# Exceções específicas (mantendo compatibilidade com src/exceptions.py)
# Nota: Estas são aliases para as exceções existentes em src/exceptions.py
# para manter compatibilidade com código existente.

class AgentCommunicationError(ExternalServiceError):
    """Erro de comunicação entre agentes.

    Alias para compatibilidade.
    """

    def __init__(
        self,
        message: str,
        *,
        source_agent: str | None = None,
        target_agent: str | None = None,
    ) -> None:
        super().__init__(
            message,
            service="agent_communication",
        )
        self.details["source_agent"] = source_agent
        self.details["target_agent"] = target_agent


class MemoryServiceError(AgnaldoError):
    """Erro em serviço de memória.

    Alias para compatibilidade.
    """

    def __init__(
        self,
        message: str,
        *,
        memory_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = {"memory_type": memory_type} if memory_type else {}
        if details:
            merged_details.update(details)
        super().__init__(message, details=merged_details)


class EmbeddingGenerationError(ExternalServiceError):
    """Erro na geração de embeddings.

    Alias para compatibilidade.
    """

    def __init__(
        self,
        message: str,
        *,
        model: str | None = None,
        text_length: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = {"service": "openai_embeddings", "model": model}
        if text_length:
            merged_details["text_length"] = text_length
        if details:
            merged_details.update(details)
        super().__init__(message, details=merged_details)
