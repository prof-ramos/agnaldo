# Sistema de Isolamento de Memória

Este documento descreve o sistema de isolamento de memória implementado para garantir que a memória de um usuário nunca seja acessada por outro.

## Visão Geral

O sistema de isolamento implementa múltiplas camadas de proteção:

1. **Validação de user_id** - Todo user_id é validado antes de operações
2. **Contexto de usuário** - Rastreamento do usuário atual na call stack
3. **Auditoria** - Logs de todas as operações de memória
4. **Guard rails** - Verificações em tempo de execução
5. **Testes** - Testes automatizados de vazamento

## Uso Básico

### Definindo Contexto de Usuário

```python
from src.memory import set_user_context, clear_user_context

# No início de uma requisição
set_user_context("user123")

# ... operações de memória ...

# Ao final da requisição
clear_user_context()
```

### Usando Context Manager

```python
from src.memory import UserContext

async with UserContext("user123"):
    # Todas as operações aqui são validadas contra "user123"
    context = await memory_manager.retrieve_context(query)
```

### Decorator de Isolamento

```python
from src.memory import require_isolation

@require_isolation(user_id_param="user_id")
async def get_user_memory(self, user_id: str, memory_id: str):
    # user_id é automaticamente validado
    ...
```

## Componentes

### MemoryIsolationGuard

Guarda de isolamento que valida todas as operações:

```python
from src.memory import get_isolation_guard

guard = get_isolation_guard()

# Validar user_id
validated_id = guard.validate_user_id(user_id, "operation_name")

# Verificar acesso a recurso
guard.check_resource_access(
    resource_user_id="owner_id",
    requesting_user_id="requester_id",
    resource_type="core",
    resource_id="memory123",
    operation="access",
)

# Validar query SQL
guard.validate_query("SELECT * FROM memories WHERE user_id = $1", "user123")
```

### Modos de Operação

**Strict Mode (padrão):**
- Lança `MemoryIsolationError` em violações
- Recomendado para produção

**Non-Strict Mode:**
- Loga warnings mas continua execução
- Útil para debugging

```python
guard = MemoryIsolationGuard(strict_mode=False)
```

### Desabilitando Isolamento

```bash
# Via environment variable
export MEMORY_ISOLATION_ENABLED=false
```

⚠️ **Não recomendado em produção!**

## Auditoria

### Logs de Auditoria

```python
guard = get_isolation_guard()

# Obter últimos logs
logs = guard.get_audit_logs(limit=100)

# Obter apenas violações
violations = guard.get_isolation_violations()

# Limpar logs
count = guard.clear_audit_logs()
```

### Formato do Log

```json
{
  "timestamp": "2026-02-28T17:30:00Z",
  "operation": "retrieve_context",
  "user_id_hash": "a1b2c3d4",
  "resource_type": "recall",
  "resource_id": "memory123",
  "success": true,
  "isolation_valid": true
}
```

## Testes

### Executando Testes de Isolamento

```bash
pytest tests/test_memory_isolation.py -v
```

### Testes Principais

- `test_check_resource_access_denied_strict` - Acesso cruzado bloqueado
- `test_concurrent_user_contexts_isolated` - Contextos concorrentes isolados
- `test_cross_user_memory_access_blocked` - Simulação de vazamento bloqueado

## Integração com MemoryManager

O `MemoryManager` valida automaticamente o `user_id` no construtor:

```python
# Isso lança MemoryIsolationError se user_id for inválido
manager = MemoryManager(user_id="", db_pool=db_pool)
```

## Boas Práticas

1. **Sempre use UserContext** em requisições:
   ```python
   async with UserContext(user_id):
       await process_message(user_id, message)
   ```

2. **Use o decorator** em métodos de serviço:
   ```python
   @require_isolation(user_id_param="user_id")
   async def get_memories(self, user_id: str):
       ...
   ```

3. **Monitore violações** em produção:
   ```python
   violations = guard.get_isolation_violations()
   if violations:
       alert_team(violations)
   ```

4. **Queries SQL** sempre devem ter `WHERE user_id`:
   ```python
   # ✅ Correto
   "SELECT * FROM memories WHERE user_id = $1"

   # ❌ Errado - será bloqueado
   "SELECT * FROM memories"
   ```

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      Discord Request                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    UserContext("user123")                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MemoryIsolationGuard                      │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ validate_user_id│  │ check_access    │                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ validate_query  │  │ audit_log       │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      MemoryManager                           │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │  CoreMemory   │  │ RecallMemory  │  │ArchivalMemory │   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │           PostgreSQL (WHERE user_id = $1)               ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Erro: MemoryIsolationError

```
MemoryIsolationError: [operation] Violação de isolamento!
user_id='user456' difere do contexto='user123'
```

**Causa:** Tentativa de acessar memória de outro usuário.

**Solução:** Verifique se o user_id está correto e o contexto está definido.

### Erro: Query sem filtro user_id

```
MemoryIsolationError: Query SQL sem filtro user_id!
```

**Causa:** Query SQL não tem `WHERE user_id`.

**Solução:** Adicione filtro de user_id à query.

### Logs de Violação

Verifique os logs para identificar padrões:

```python
violations = guard.get_isolation_violations()
for v in violations:
    print(f"Operação: {v['operation']}, Sucesso: {v['success']}")
```
