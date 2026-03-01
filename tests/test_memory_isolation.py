"""Testes de isolamento de memória entre usuários.

Este módulo contém testes que garantem que a memória de um usuário
nunca seja acessada por outro usuário.
"""

import asyncio
import pytest

from src.memory.isolation import (
    MemoryIsolationError,
    MemoryIsolationGuard,
    UserContext,
    clear_user_context,
    get_current_user_context,
    get_isolation_guard,
    require_isolation,
    set_user_context,
    validate_sql_query,
)
from tests.fixtures import assert_has_violation


class TestMemoryIsolationGuard:
    """Testes para o MemoryIsolationGuard."""

    def test_validate_user_id_valid(self):
        """Valida user_id válido."""
        guard = MemoryIsolationGuard(strict_mode=True)
        result = guard.validate_user_id("user123", "test_op")
        assert result == "user123"

    def test_validate_user_id_empty_raises(self):
        """user_id vazio deve lançar exceção em strict_mode."""
        guard = MemoryIsolationGuard(strict_mode=True)
        with pytest.raises(MemoryIsolationError):
            guard.validate_user_id("", "test_op")

    def test_validate_user_id_none_raises(self):
        """user_id None deve lançar exceção em strict_mode."""
        guard = MemoryIsolationGuard(strict_mode=True)
        with pytest.raises(MemoryIsolationError):
            guard.validate_user_id(None, "test_op")

    def test_validate_user_id_whitespace_raises(self):
        """user_id com só whitespace deve lançar exceção."""
        guard = MemoryIsolationGuard(strict_mode=True)
        with pytest.raises(MemoryIsolationError):
            guard.validate_user_id("   ", "test_op")

    def test_validate_user_id_empty_warns_in_non_strict(self):
        """Em non-strict mode, deve logar warning e retornar vazio."""
        guard = MemoryIsolationGuard(strict_mode=False)
        result = guard.validate_user_id("", "test_op")
        assert result == ""
        violations = guard.get_isolation_violations()
        assert len(violations) > 0

    def test_check_resource_access_allowed(self):
        """Acesso permitido quando resource_user == requesting_user."""
        guard = MemoryIsolationGuard(strict_mode=True)
        result = guard.check_resource_access(
            resource_user_id="user123",
            requesting_user_id="user123",
            resource_type="core",
            resource_id="memory1",
            operation="test_access",
        )
        assert result is True

    def test_check_resource_access_denied_strict(self):
        """Acesso negado deve lançar exceção em strict_mode."""
        guard = MemoryIsolationGuard(strict_mode=True)
        with pytest.raises(MemoryIsolationError) as exc_info:
            guard.check_resource_access(
                resource_user_id="user123",
                requesting_user_id="user456",
                resource_type="core",
                resource_id="memory1",
                operation="test_access",
            )
        assert exc_info.value.expected_user == "user123"
        assert exc_info.value.actual_user == "user456"

    def test_check_resource_access_denied_non_strict(self):
        """Acesso negado retorna False em non-strict mode."""
        guard = MemoryIsolationGuard(strict_mode=False)
        result = guard.check_resource_access(
            resource_user_id="user123",
            requesting_user_id="user456",
            resource_type="core",
            resource_id="memory1",
            operation="test_access",
        )
        assert result is False
        violations = guard.get_isolation_violations()
        assert_has_violation(violations, "test_access", "core")

    def test_validate_query_with_user_id(self):
        """Query com WHERE user_id deve passar."""
        guard = MemoryIsolationGuard(strict_mode=True)
        query = "SELECT * FROM memories WHERE user_id = $1"
        result = guard.validate_query(query, "user123", "test_query")
        assert result == query

    def test_validate_query_without_user_id_strict(self):
        """Query sem WHERE user_id deve lançar exceção."""
        guard = MemoryIsolationGuard(strict_mode=True)
        query = "SELECT * FROM memories"
        with pytest.raises(MemoryIsolationError):
            guard.validate_query(query, "user123", "test_query")

    def test_validate_query_without_user_id_non_strict(self):
        """Query sem WHERE user_id deve logar warning em non-strict."""
        guard = MemoryIsolationGuard(strict_mode=False)
        query = "SELECT * FROM memories"
        result = guard.validate_query(query, "user123", "test_query")
        assert result == query
        violations = guard.get_isolation_violations()
        assert_has_violation(violations, "test_query", "query_validation")

    def test_audit_logs_are_recorded(self):
        """Logs de auditoria são registrados."""
        guard = MemoryIsolationGuard(strict_mode=False)
        guard.validate_user_id("", "test_op")
        logs = guard.get_audit_logs()
        assert len(logs) > 0
        assert logs[-1]["operation"] == "test_op"

    def test_get_isolation_violations_filters_correctly(self):
        """get_isolation_violations retorna apenas violações."""
        guard = MemoryIsolationGuard(strict_mode=False)

        # Operação válida
        guard.validate_user_id("user123", "valid_op")

        # Operação inválida
        guard.validate_user_id("", "invalid_op")

        violations = guard.get_isolation_violations()
        assert len(violations) == 1
        assert violations[0]["operation"] == "invalid_op"


class TestUserContext:
    """Testes para o context manager UserContext."""

    def test_user_context_sets_and_clears(self):
        """Context manager define e limpa o contexto corretamente."""
        assert get_current_user_context() is None

        with UserContext("user123"):
            assert get_current_user_context() == "user123"

        assert get_current_user_context() is None

    @pytest.mark.asyncio
    async def test_user_context_async(self):
        """Context manager funciona com async."""
        assert get_current_user_context() is None

        async with UserContext("user123"):
            assert get_current_user_context() == "user123"

        assert get_current_user_context() is None

    def test_nested_contexts(self):
        """Contextos aninhados funcionam corretamente."""
        with UserContext("user1"):
            assert get_current_user_context() == "user1"

            with UserContext("user2"):
                assert get_current_user_context() == "user2"

            assert get_current_user_context() == "user1"

        assert get_current_user_context() is None


class TestRequireIsolationDecorator:
    """Testes para o decorator @require_isolation."""

    @pytest.mark.asyncio
    async def test_decorator_validates_user_id(self):
        """Decorator valida user_id automaticamente."""

        @require_isolation(user_id_param="user_id")
        async def get_memory(self, user_id: str, memory_id: str) -> str:
            return f"memory_{memory_id}"

        result = await get_memory(None, "user123", "mem1")
        assert result == "memory_mem1"

    @pytest.mark.asyncio
    async def test_decorator_raises_on_invalid_user_id(self):
        """Decorator lança exceção com user_id inválido."""

        @require_isolation(user_id_param="user_id")
        async def get_memory(self, user_id: str, memory_id: str) -> str:
            return f"memory_{memory_id}"

        with pytest.raises(MemoryIsolationError):
            await get_memory(None, "", "mem1")

    @pytest.mark.asyncio
    async def test_decorator_checks_resource_access(self):
        """Decorator valida acesso a recurso de outro usuário."""

        @require_isolation(
            user_id_param="requesting_user_id",
            resource_user_id_param="resource_user_id",
        )
        async def access_resource(
            self, requesting_user_id: str, resource_user_id: str, resource_id: str
        ) -> str:
            return f"resource_{resource_id}"

        # Acesso ao próprio recurso - permitido
        result = await access_resource(None, "user123", "user123", "res1")
        assert result == "resource_res1"

        # Acesso a recurso de outro usuário - negado
        with pytest.raises(MemoryIsolationError):
            await access_resource(None, "user123", "user456", "res1")

    def test_sync_function_support(self):
        """Decorator funciona com funções síncronas."""

        @require_isolation(user_id_param="user_id")
        def sync_get_memory(self, user_id: str, memory_id: str) -> str:
            return f"memory_{memory_id}"

        result = sync_get_memory(None, "user123", "mem1")
        assert result == "memory_mem1"

        with pytest.raises(MemoryIsolationError):
            sync_get_memory(None, "", "mem1")


class TestGlobalFunctions:
    """Testes para funções globais de isolamento."""

    def test_set_and_clear_user_context(self):
        """set_user_context e clear_user_context funcionam."""
        set_user_context("user123")
        assert get_current_user_context() == "user123"

        clear_user_context()
        assert get_current_user_context() is None

    def test_get_isolation_guard_returns_singleton(self):
        """get_isolation_guard retorna a mesma instância."""
        guard1 = get_isolation_guard()
        guard2 = get_isolation_guard()
        assert guard1 is guard2

    def test_validate_sql_query_valid(self):
        """validate_sql_query passa com query válida."""
        query = "SELECT * FROM memories WHERE user_id = $1"
        result = validate_sql_query(query, "user123")
        assert result == query

    def test_validate_sql_query_invalid(self):
        """validate_sql_query lança exceção com query inválida."""
        query = "SELECT * FROM memories"
        with pytest.raises(MemoryIsolationError):
            validate_sql_query(query, "user123")


class TestIsolationIntegration:
    """Testes de integração de isolamento."""

    @pytest.mark.asyncio
    async def test_cross_user_memory_access_blocked(self):
        """Simula cenário de vazamento de memória entre usuários."""
        guard = MemoryIsolationGuard(strict_mode=True)

        # Usuário 1 armazena memória
        user1_id = "user1_abc123"
        user1_context = UserContext(user1_id)

        # Usuário 2 tenta acessar memória do usuário 1
        user2_id = "user2_xyz789"

        # Deve bloquear
        with pytest.raises(MemoryIsolationError):
            guard.check_resource_access(
                resource_user_id=user1_id,
                requesting_user_id=user2_id,
                resource_type="recall",
                resource_id="memory123",
                operation="cross_user_access",
            )

    @pytest.mark.asyncio
    async def test_concurrent_user_contexts_isolated(self):
        """Contextos de usuários concorrentes são isolados."""
        results = {}

        async def user_operation(user_id: str, delay: float) -> str:
            async with UserContext(user_id):
                await asyncio.sleep(delay)
                # Verificar se contexto não foi alterado por outra corrotina
                current = get_current_user_context()
                return current

        # Executar operações de múltiplos usuários em paralelo
        tasks = [
            user_operation("user1", 0.01),
            user_operation("user2", 0.02),
            user_operation("user3", 0.005),
        ]
        results_list = await asyncio.gather(*tasks)

        # Cada tarefa deve ter visto seu próprio user_id
        assert results_list == ["user1", "user2", "user3"]


class TestMemoryIsolationDisabled:
    """Testes com isolamento desabilitado."""

    def test_guard_disabled_skips_validation(self, monkeypatch):
        """Com isolamento desabilitado, validações são puladas."""
        monkeypatch.setenv("MEMORY_ISOLATION_ENABLED", "false")

        # Criar novo guarda para pegar env var atualizada
        guard = MemoryIsolationGuard(strict_mode=True)

        # Deve passar sem erro mesmo com user_id vazio
        result = guard.validate_user_id("", "test_op")
        # Nota: quando disabled, retorna o valor original
        assert result == ""

    def test_guard_disabled_allows_cross_user_access(self, monkeypatch):
        """Com isolamento desabilitado, acesso cruzado é permitido."""
        monkeypatch.setenv("MEMORY_ISOLATION_ENABLED", "false")

        guard = MemoryIsolationGuard(strict_mode=True)

        # Deve retornar True mesmo com usuários diferentes
        result = guard.check_resource_access(
            resource_user_id="user1",
            requesting_user_id="user2",
            resource_type="core",
            resource_id="memory1",
            operation="test_access",
        )
        assert result is True
