# Roadmap — Agnaldo Discord Bot

> Plano de evolução baseado na [revisão de qualidade de código](docs/10-revisao-qualidade-codigo.md) realizada em 2026-02-17.

---

## Fase 0 — Correções Bloqueadoras

> **Prioridade**: Imediata
> **Meta**: Bot funcional com pipeline completo de mensagens

- [ ] **Inicializar pool asyncpg no startup** (`src/main.py`)
  - Criar pool com `asyncpg.create_pool(settings.SUPABASE_DB_URL)`
  - Atribuir a `bot.db_pool` antes de iniciar o bot
  - Implementar health check de conexão
- [ ] **Conectar handler de mensagens** (`src/discord/events.py`)
  - Integrar `on_message` com `MessageHandler.process_message()`
  - Garantir que mensagens passem pelo pipeline de IA (intent → agent → resposta)
- [ ] **Alinhar schemas de migração** (`src/database/migrations/versions/`)
  - Definir Alembic como fonte de verdade
  - Remover ou depreciar `001_create_memory_tables.sql`
  - Validar que modelos SQLAlchemy refletem o schema final

---

## Fase 1 — Segurança

> **Prioridade**: Alta
> **Meta**: Codebase seguro para ambiente de staging

- [ ] **Remover dados sensíveis dos logs**
  - Eliminar URLs do Supabase de mensagens de log (`main.py`, `supabase.py`)
  - Auditar todos os `logger.info/debug` por vazamento de dados
- [ ] **Corrigir construção de JSON path** (`src/memory/archival.py`)
  - Substituir interpolação de string por operadores nativos JSONB do PostgreSQL
- [ ] **Adicionar validação de inputs nos slash commands** (`src/discord/commands.py`)
  - Limites de comprimento: key max 100 chars, value max 2000 chars
  - Sanitização de conteúdo antes de armazenamento
- [ ] **Sanitizar exceções da OpenAI** (`src/memory/recall.py`)
  - Capturar `openai.APIError` e re-lançar sem dados internos
- [ ] **Corrigir race condition no classifier** (`src/intent/classifier.py`)
  - Adicionar `asyncio.Lock()` no carregamento do modelo

---

## Fase 2 — Desempenho e Estabilidade

> **Prioridade**: Alta
> **Meta**: Bot responsivo e estável sob carga

- [ ] **Cache de embeddings** (`src/memory/recall.py`, `src/knowledge/graph.py`)
  - Implementar `@alru_cache(maxsize=256, ttl=300)` para embeddings repetidos
  - Reduzir chamadas à API OpenAI e latência de resposta
- [ ] **Limitar background tasks** (`src/memory/core.py`)
  - Adicionar `asyncio.Semaphore(10)` em `_schedule_access_update()`
  - Ou implementar batch updates com intervalo de 5 segundos
- [ ] **Cleanup de sessões inativas** (`src/context/gestor.py`)
  - TTL de 30 minutos para sessões ociosas
  - Task periódica de limpeza (a cada 5 min)
- [ ] **Criar índices compostos** (`src/database/models.py`)
  - `messages(user_id, session_id, created_at)`
  - `archival_memories(user_id, source, session_id)`
  - `recall_memories(user_id, created_at)`
- [ ] **Usar `time.monotonic()`** no rate limiter (`src/discord/rate_limiter.py`)

---

## Fase 3 — Cobertura de Testes

> **Prioridade**: Média-Alta
> **Meta**: Cobertura de testes ≥ 80%

### Etapa 3.1 — Infraestrutura de Testes
- [ ] Criar `tests/conftest.py` com fixtures compartilhadas
  - Mock pool asyncpg reutilizável
  - Mock OpenAI client
  - Factories de user_id e session_id
- [ ] Configurar marcadores pytest (`unit`, `integration`, `smoke`)
- [ ] Adicionar thresholds de cobertura no `pyproject.toml`

### Etapa 3.2 — Testes Prioritários (P0)
- [ ] `tests/test_memory_recall.py` — Busca semântica (0% → 80%)
- [ ] `tests/test_agents/test_orchestrator.py` — Orquestração multi-agente (0% → 70%)
- [ ] `tests/test_intent/test_classifier.py` — Classificação de intents (0% → 80%)

### Etapa 3.3 — Testes Secundários (P1)
- [ ] `tests/test_discord/test_rate_limiter.py` — Rate limiting
- [ ] `tests/test_discord/test_commands.py` — Slash commands
- [ ] `tests/test_config/test_settings.py` — Validação de configuração
- [ ] Completar edge cases em `test_memory.py` e `test_graph.py`

### Etapa 3.4 — Testes de Integração (P2)
- [ ] Testes com banco PostgreSQL real (Docker)
- [ ] Testes de concorrência e race conditions
- [ ] Testes de error handling e recovery

---

## Fase 4 — Qualidade de Código

> **Prioridade**: Média
> **Meta**: Codebase limpo e consistente

- [ ] **Padronizar type hints para Python 3.10+**
  - Substituir `List`, `Dict`, `Optional` por `list`, `dict`, `X | None`
  - Atualizar `src/config/settings.py`, `src/context/monitor.py`
- [ ] **Extrair classe base de memória** (`src/memory/base.py`)
  - Mover `_affected_rows()` e padrões de acquire/transaction
  - `CoreMemory`, `RecallMemory`, `ArchivalMemory` herdam de `BaseMemory`
- [ ] **Substituir `threading.Lock` por `asyncio.Lock`** em `settings.py`
- [ ] **Corrigir Pydantic v2 Config legado** em `src/schemas/discord.py`
- [ ] **Remover imports não utilizados**
  - `asyncio` em `commands.py`
  - `AsyncIterator` em `graph.py` e `core.py`
- [ ] **Limpar repositório**
  - Adicionar `__pycache__/`, `*.pyc` ao `.gitignore`
  - Remover `analisecoderabbit_debug.md` do repositório
  - Remover bytecode comitado

---

## Fase 5 — CI/CD e Observabilidade

> **Prioridade**: Média
> **Meta**: Pipeline automatizado e monitoramento

- [ ] **GitHub Actions**
  - Workflow de CI: `uv sync` → `ruff check` → `mypy` → `pytest --cov`
  - Gate de cobertura mínima (80%)
  - Verificação de segurança com `pip-audit` ou `safety`
- [ ] **Configurar OpenTelemetry** (já é dependência)
  - Traces para requisições end-to-end
  - Métricas de latência por agente
  - Spans para chamadas à API OpenAI
- [ ] **Dashboard de métricas**
  - Tempo de resposta por tipo de intent
  - Uso de memória por tier
  - Taxa de cache hit/miss de embeddings

---

## Fase 6 — Funcionalidades Novas

> **Prioridade**: Baixa (após estabilidade)
> **Meta**: Expandir capacidades do bot

- [ ] **Implementar ferramentas OSINT** (`src/tools/osint/`)
  - Conectar ao pipeline de agentes
- [ ] **Conectar operações de grafo aos slash commands**
  - `/graph search <query>` — busca semântica no grafo
  - `/graph neighbors <node>` — vizinhos de um nó
  - `/graph path <source> <target>` — caminho entre nós
- [ ] **Warm-up do intent classifier no startup**
  - Carregar modelo sentence-transformers durante inicialização
  - Evitar latência na primeira request do usuário
- [ ] **Multi-guild support**
  - Isolamento de memória e contexto por guild
  - Configurações de personalidade por servidor

---

## Métricas de Acompanhamento

| Métrica | Atual | Meta Fase 3 | Meta Fase 5 |
|---------|-------|-------------|-------------|
| Cobertura de testes | ~5% | ≥ 80% | ≥ 85% |
| Módulos com testes | 3/30 | 20/30 | 28/30 |
| Problemas P0 | 3 | 0 | 0 |
| Problemas P1 | 4 | 0 | 0 |
| CI/CD | Nenhum | — | GitHub Actions |
| Tempo de resposta p95 | — | < 3s | < 2s |
