"""Sistema de isolamento de memória entre usuários.

Este módulo garante que a memória de um usuário nunca seja acessada por outro,
implementando múltiplas camadas de proteção:

1. Validação de user_id em todas as operações
2. Decorators para garantir isolamento
3. Auditoria e logs de acessos
4. Testes de vazamento
5. Guard rails em tempo de execução
"""

import functools
import hashlib
import os
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar, ParamSpec

from loguru import logger

# Context variable para rastrear user_id na call stack atual
_current_user_context: ContextVar[str | None] = ContextVar("current_user_context", default=None)

P = ParamSpec("P")
R = TypeVar("R")


class MemoryIsolationError(Exception):
    """Erro de violação de isolamento de memória."""

    def __init__(self, message: str, *, expected_user: str | None = None, actual_user: str | None = None):
        super().__init__(message)
        self.expected_user = expected_user
        self.actual_user = actual_user


@dataclass
class IsolationAuditLog:
    """Log de auditoria para operações de memória."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    operation: str = ""
    user_id: str = ""
    resource_type: str = ""
    resource_id: str = ""
    success: bool = True
    error_message: str | None = None
    context_user: str | None = None  # user_id do contexto atual
    isolation_valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "user_id_hash": self._hash_user_id(self.user_id) if self.user_id else None,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "success": self.success,
            "isolation_valid": self.isolation_valid,
        }

    @staticmethod
    def _hash_user_id(user_id: str) -> str:
        """Hash do user_id para logs (não expõe ID real)."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:8]


class MemoryIsolationGuard:
    """Guarda de isolamento de memória.

    Valida todas as operações de memória garantindo que:
    1. user_id está presente e é válido
    2. Operações só acessam dados do user_id especificado
    3. Contexto não está "vazando" user_id de outro usuário
    """

    def __init__(self, strict_mode: bool = True):
        """Inicializa o guarda de isolamento.

        Args:
            strict_mode: Se True, lança exceção em violações.
                        Se False, apenas loga warning.
        """
        self.strict_mode = strict_mode
        self._audit_logs: list[IsolationAuditLog] = []
        self._max_audit_logs = 1000
        self._enabled = os.environ.get("MEMORY_ISOLATION_ENABLED", "true").lower() == "true"

    def validate_user_id(self, user_id: str | None, operation: str) -> str:
        """Valida e retorna um user_id válido.

        Args:
            user_id: ID do usuário a validar.
            operation: Nome da operação para logs.

        Returns:
            user_id validado.

        Raises:
            MemoryIsolationError: Se user_id é inválido e strict_mode=True.
        """
        if not self._enabled:
            return user_id or ""

        if not user_id or not str(user_id).strip():
            error_msg = f"[{operation}] user_id inválido: {user_id!r}"
            self._log_audit(
                operation=operation,
                user_id="",
                resource_type="validation",
                success=False,
                error_message=error_msg,
                isolation_valid=False,
            )
            if self.strict_mode:
                raise MemoryIsolationError(error_msg, expected_user="<valid>", actual_user=str(user_id))
            logger.warning(error_msg)
            return ""

        user_id = str(user_id).strip()

        # Verificar consistência com contexto atual
        context_user = _current_user_context.get()
        if context_user is not None and context_user != user_id:
            error_msg = (
                f"[{operation}] Violação de isolamento! "
                f"user_id={user_id!r} difere do contexto={context_user!r}"
            )
            self._log_audit(
                operation=operation,
                user_id=user_id,
                resource_type="validation",
                success=False,
                error_message=error_msg,
                context_user=context_user,
                isolation_valid=False,
            )
            if self.strict_mode:
                raise MemoryIsolationError(
                    error_msg,
                    expected_user=context_user,
                    actual_user=user_id,
                )
            logger.warning(error_msg)

        return user_id

    def validate_query(self, query: str, user_id: str, operation: str) -> str:
        """Valida que uma query SQL contém o filtro de user_id correto.

        Args:
            query: Query SQL a validar.
            user_id: user_id esperado na query.
            operation: Nome da operação.

        Returns:
            Query validada.

        Raises:
            MemoryIsolationError: Se a query não tem filtro de user_id.
        """
        if not self._enabled:
            return query

        query_lower = query.lower()

        # Verificar se a query tem WHERE com user_id
        if "where" in query_lower and "user_id" in query_lower:
            return query

        # Query sem WHERE user_id - potencial vazamento
        error_msg = (
            f"[{operation}] Query SQL sem filtro user_id! "
            f"Isso pode causar vazamento de memória entre usuários."
        )
        self._log_audit(
            operation=operation,
            user_id=user_id,
            resource_type="query_validation",
            success=False,
            error_message=error_msg,
            isolation_valid=False,
        )

        if self.strict_mode:
            raise MemoryIsolationError(error_msg, expected_user=user_id)

        logger.warning(error_msg)
        return query

    def check_resource_access(
        self,
        resource_user_id: str,
        requesting_user_id: str,
        resource_type: str,
        resource_id: str,
        operation: str,
    ) -> bool:
        """Verifica se um usuário pode acessar um recurso específico.

        Args:
            resource_user_id: user_id do dono do recurso.
            requesting_user_id: user_id de quem está solicitando acesso.
            resource_type: Tipo do recurso (core, recall, archival).
            resource_id: ID do recurso.
            operation: Nome da operação.

        Returns:
            True se o acesso é permitido.

        Raises:
            MemoryIsolationError: Se acesso negado e strict_mode=True.
        """
        if not self._enabled:
            return True

        if resource_user_id == requesting_user_id:
            self._log_audit(
                operation=operation,
                user_id=requesting_user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                success=True,
                isolation_valid=True,
            )
            return True

        # Acesso negado - recurso pertence a outro usuário
        error_msg = (
            f"[{operation}] ACESSO NEGADO! "
            f"Usuário {requesting_user_id!r} tentou acessar recurso "
            f"{resource_type}:{resource_id} do usuário {resource_user_id!r}"
        )
        self._log_audit(
            operation=operation,
            user_id=requesting_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=False,
            error_message=error_msg,
            isolation_valid=False,
        )

        if self.strict_mode:
            raise MemoryIsolationError(
                error_msg,
                expected_user=resource_user_id,
                actual_user=requesting_user_id,
            )

        logger.error(error_msg)
        return False

    def _log_audit(
        self,
        operation: str,
        user_id: str,
        resource_type: str = "",
        resource_id: str = "",
        success: bool = True,
        error_message: str | None = None,
        context_user: str | None = None,
        isolation_valid: bool = True,
    ) -> None:
        """Adiciona entrada ao log de auditoria."""
        log_entry = IsolationAuditLog(
            operation=operation,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            error_message=error_message,
            context_user=context_user,
            isolation_valid=isolation_valid,
        )
        self._audit_logs.append(log_entry)

        # Manter tamanho limitado
        if len(self._audit_logs) > self._max_audit_logs:
            self._audit_logs = self._audit_logs[-self._max_audit_logs :]

        # Log estruturado
        if not isolation_valid:
            logger.warning(f"[ISOLATION_AUDIT] {log_entry.to_dict()}")
        elif not success:
            logger.debug(f"[ISOLATION_AUDIT] {log_entry.to_dict()}")

    def get_audit_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retorna os últimos N logs de auditoria."""
        return [log.to_dict() for log in self._audit_logs[-limit:]]

    def get_isolation_violations(self) -> list[dict[str, Any]]:
        """Retorna apenas logs de violações de isolamento."""
        return [
            log.to_dict()
            for log in self._audit_logs
            if not log.isolation_valid or not log.success
        ]

    def clear_audit_logs(self) -> int:
        """Limpa logs de auditoria e retorna quantidade removida."""
        count = len(self._audit_logs)
        self._audit_logs.clear()
        return count


# Instância global do guarda de isolamento
_isolation_guard = MemoryIsolationGuard()


def get_isolation_guard() -> MemoryIsolationGuard:
    """Retorna a instância global do guarda de isolamento."""
    return _isolation_guard


def set_user_context(user_id: str) -> None:
    """Define o user_id no contexto atual para validação de isolamento.

    Use em contexto de requisição para garantir que operações de memória
    só acessem dados do usuário correto.

    Args:
        user_id: ID do usuário no contexto atual.
    """
    _current_user_context.set(user_id)
    logger.debug(f"[ISOLATION] Contexto definido para usuário {user_id}")


def clear_user_context() -> None:
    """Limpa o user_id do contexto atual."""
    _current_user_context.set(None)
    logger.debug("[ISOLATION] Contexto limpo")


def get_current_user_context() -> str | None:
    """Retorna o user_id do contexto atual."""
    return _current_user_context.get()


def require_isolation(
    user_id_param: str = "user_id",
    resource_user_id_param: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator que garante isolamento de memória em métodos.

    Args:
        user_id_param: Nome do parâmetro que contém o user_id.
        resource_user_id_param: Nome do parâmetro com user_id do recurso (opcional).

    Returns:
        Decorator que valida isolamento.

    Example:
        @require_isolation(user_id_param="user_id")
        async def get_memory(self, user_id: str, memory_id: str):
            ...

        @require_isolation(
            user_id_param="requesting_user_id",
            resource_user_id_param="memory_user_id"
        )
        async def access_memory(self, requesting_user_id: str, memory_user_id: str):
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            guard = get_isolation_guard()

            # Extrair user_id dos argumentos
            user_id = kwargs.get(user_id_param)
            if user_id is None and len(args) > 1:
                # Assumir que self é args[0], user_id é args[1]
                user_id = args[1] if len(args) > 1 else None

            # Validar user_id
            validated_user_id = guard.validate_user_id(user_id, func.__name__)

            # Validar acesso a recurso de outro usuário se especificado
            if resource_user_id_param:
                resource_user_id = kwargs.get(resource_user_id_param)
                if resource_user_id is None and len(args) > 2:
                    resource_user_id = args[2]

                if resource_user_id:
                    guard.check_resource_access(
                        resource_user_id=resource_user_id,
                        requesting_user_id=validated_user_id,
                        resource_type="memory",
                        resource_id="unknown",
                        operation=func.__name__,
                    )

            # Executar função com contexto de usuário
            token = _current_user_context.set(validated_user_id)
            try:
                return await func(*args, **kwargs)
            finally:
                _current_user_context.reset(token)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            guard = get_isolation_guard()

            # Extrair user_id dos argumentos
            user_id = kwargs.get(user_id_param)
            if user_id is None and len(args) > 1:
                user_id = args[1] if len(args) > 1 else None

            # Validar user_id
            validated_user_id = guard.validate_user_id(user_id, func.__name__)

            # Validar acesso a recurso de outro usuário se especificado
            if resource_user_id_param:
                resource_user_id = kwargs.get(resource_user_id_param)
                if resource_user_id is None and len(args) > 2:
                    resource_user_id = args[2]

                if resource_user_id:
                    guard.check_resource_access(
                        resource_user_id=resource_user_id,
                        requesting_user_id=validated_user_id,
                        resource_type="memory",
                        resource_id="unknown",
                        operation=func.__name__,
                    )

            # Executar função com contexto de usuário
            token = _current_user_context.set(validated_user_id)
            try:
                return func(*args, **kwargs)
            finally:
                _current_user_context.reset(token)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def validate_sql_query(query: str, user_id: str) -> str:
    """Valida que uma query SQL tem filtro de user_id.

    Args:
        query: Query SQL.
        user_id: user_id esperado.

    Returns:
        Query validada.

    Raises:
        MemoryIsolationError: Se query não tem filtro user_id.
    """
    return get_isolation_guard().validate_query(query, user_id, "sql_validation")


# Context manager para contexto de usuário
class UserContext:
    """Context manager para definir user_id em um bloco de código.

    Example:
        async with UserContext("user123"):
            # Todas as operações de memória aqui validam contra "user123"
            await memory_manager.retrieve_context(query)
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._token: Any = None

    def __enter__(self) -> "UserContext":
        self._token = _current_user_context.set(self.user_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._token is not None:
            _current_user_context.reset(self._token)

    async def __aenter__(self) -> "UserContext":
        self._token = _current_user_context.set(self.user_id)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._token is not None:
            _current_user_context.reset(self._token)
