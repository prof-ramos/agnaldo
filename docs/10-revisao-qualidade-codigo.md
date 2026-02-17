# Revisão de Qualidade de Código — Agnaldo Discord Bot

> **Data**: 2026-02-17
> **Escopo**: Revisão completa do repositório `agnaldo/` (segurança, performance, arquitetura, testes)
> **Versão analisada**: `0.1.0` (commit `bc50396`)

---

## Resumo Executivo

| Categoria | Crítico | Alto | Médio | Baixo | Total |
|-----------|---------|------|-------|-------|-------|
| Segurança | 2 | 4 | 3 | 3 | 12 |
| Qualidade de Código | — | 4 | 8 | 3 | 15 |
| Performance | 1 | 3 | 7 | 3 | 14 |
| Testes | 1 | — | — | — | 1 |
| **Total** | **4** | **11** | **18** | **9** | **42** |

O codebase demonstra **arquitetura sólida e boas práticas fundamentais** — queries parametrizadas, hierarquia de exceções, async-first, separação de responsabilidades. Porém, existem **lacunas críticas de integração** (pool asyncpg não inicializado, handler de mensagens desconectado) e **cobertura de testes insuficiente (~5-10%)** que impedem o uso em produção.

---

## 1. Segurança

### 1.1 Pontos Fortes

- Todas as queries SQL usam parâmetros posicionais (`$1`, `$2` do asyncpg) — sem SQL injection
- Variáveis de ambiente para configuração sensível, sem segredos hardcoded no código
- Políticas RLS (Row-Level Security) isolam dados por `user_id`
- Sem vetores de command injection (`os.system`, `subprocess` ausentes)
- Rate limiting implementado com token bucket (global + por canal)
- Sanitização de conteúdo em logs (URLs redactadas, emails anonimizados)

### 1.2 Problemas Encontrados

#### CRITICAL — Exposição de URL do Supabase nos logs

**Arquivos**: `src/main.py:64`, `src/database/supabase.py:61`

A URL do projeto Supabase é logada durante o startup, expondo o ID do projeto mesmo com truncamento. Um atacante com acesso aos logs pode identificar a instância Supabase.

**Recomendação**: Remover URLs das mensagens de log. Logar apenas "Supabase client initialized" sem dados de conexão.

#### CRITICAL — Construção de JSON path por interpolação

**Arquivo**: `src/memory/archival.py:230-240`

Filtros de metadata usam interpolação de string para montar path PostgreSQL JSONB. Embora exista validação regex, o padrão é frágil e pode ser contornado.

**Recomendação**: Usar operadores nativos do PostgreSQL com placeholders parametrizados.

#### HIGH — Validação insuficiente de inputs do Discord

**Arquivo**: `src/discord/commands.py:135-175`

Inputs do usuário (`key`, `value`, `label`) nos slash commands não possuem validação de tamanho ou conteúdo. Sem limites de comprimento, um usuário malicioso pode causar DoS por exaustão de memória ou armazenamento.

**Recomendação**: Adicionar limites de comprimento (ex.: key max 100 chars, value max 2000 chars) e sanitização de conteúdo.

#### HIGH — Exceções da OpenAI podem expor API key

**Arquivo**: `src/memory/recall.py:95-103`

Mensagens de erro da API OpenAI são propagadas sem sanitização nos logs e respostas. Em cenários raros de erro de autenticação, a chave parcial pode ser incluída na mensagem.

**Recomendação**: Capturar exceções da OpenAI e re-lançar com mensagem sanitizada, sem dados internos.

#### HIGH — Rate limiter com aritmética de ponto flutuante

**Arquivo**: `src/discord/rate_limiter.py:70-82`

O cálculo de tokens disponíveis usa aritmética float, suscetível a erros de arredondamento que podem permitir requests acima do limite.

**Recomendação**: Usar `Decimal` ou manter contagem inteira de tokens com timestamp de último refill.

#### HIGH — Token Discord exposto em tracebacks

**Arquivo**: `src/main.py:195`

O token é passado diretamente a `bot.start()`. Em caso de exceção não tratada, o token pode aparecer em stack traces e logs.

**Recomendação**: Envolver a chamada em try/except específico que suprime o token do traceback.

#### MEDIUM — Políticas RLS permissivas para service_role

**Arquivo**: `src/database/rls_policies.py:25-28`

A role `service_role` tem acesso irrestrito sem limitar operações por tipo (SELECT, INSERT, UPDATE, DELETE).

#### MEDIUM — Race condition no carregamento do intent classifier

**Arquivo**: `src/intent/classifier.py:48-54`

O carregamento do modelo sentence-transformers não possui sincronização. Requests concorrentes durante a inicialização podem causar múltiplos carregamentos simultâneos do modelo.

**Recomendação**: Adicionar `asyncio.Lock()` no método de inicialização.

#### MEDIUM — Hash determinístico de mensagens

**Arquivo**: `src/discord/handlers.py:89-95`

SHA256 do conteúdo permite correlação de mensagens idênticas entre usuários diferentes.

**Recomendação**: Usar HMAC com chave secreta para hashing.

---

## 2. Qualidade de Código

### 2.1 Padrões Positivos

- Hierarquia de exceções bem definida com `AgnaldoError` como base e subclasses específicas (`MemoryServiceError`, `IntentClassificationError`, etc.)
- Padrão singleton com async lock no `AgentOrchestrator` e handlers
- Pydantic v2 para validação de schemas em toda a aplicação
- Separação clara de responsabilidades entre módulos (`memory/`, `intent/`, `discord/`, `knowledge/`)
- Uso consistente de `loguru` para logging estruturado
- Graceful shutdown com handlers de sinal (SIGINT/SIGTERM)

### 2.2 Problemas Encontrados

#### HIGH — Pool asyncpg nunca inicializado (BLOQUEADOR)

**Arquivo**: `src/main.py:53-75`

A função `initialize_database()` cria apenas o cliente Supabase REST, mas **não cria o pool asyncpg**. O atributo `bot.db_pool` permanece `None` durante toda a execução. Consequência: **todos os comandos de memória, grafo e busca semântica falham em runtime**.

```python
# src/main.py:53-75 — Problema
async def initialize_database() -> bool:
    supabase = get_supabase_client()  # Apenas REST client
    # FALTA: pool = await asyncpg.create_pool(settings.SUPABASE_DB_URL)
    # FALTA: bot.db_pool = pool
    return True
```

**Impacto**: O bot inicia sem erros mas falha em qualquer operação de banco via asyncpg.

**Recomendação**: Criar pool asyncpg e atribuir a `bot.db_pool` durante o startup.

#### HIGH — Handler de mensagens desconectado (BLOQUEADOR)

**Arquivo**: `src/discord/events.py:62-79`

O evento `on_message` está registrado mas **não invoca** o `MessageHandler.process_message()` definido em `src/discord/handlers.py`. O bot recebe mensagens mas não as processa pelo pipeline de IA.

**Impacto**: O bot não responde a mensagens conversacionais — apenas slash commands funcionam.

**Recomendação**: Conectar `on_message` ao `MessageHandler` no setup de eventos.

#### HIGH — `threading.Lock` em contexto async

**Arquivo**: `src/config/settings.py:86-100`

O singleton `get_settings()` usa `threading.Lock()`, que é bloqueante e pode travar o event loop do asyncio em cenários de alta concorrência.

```python
# settings.py — Problema
_settings_lock = Lock()  # threading.Lock — bloqueia event loop

# orchestrator.py — Padrão correto
_orchestrator_lock = asyncio.Lock()  # asyncio.Lock — non-blocking
```

**Recomendação**: Substituir por `asyncio.Lock()` ou, como `get_settings()` é chamado no startup (antes do event loop estar sob carga), documentar esta limitação.

#### HIGH — Divergência de schemas de migração

**Arquivos**: `src/database/migrations/versions/001_initial.py` vs `001_create_memory_tables.sql`

Os dois arquivos de migração definem schemas diferentes para as mesmas tabelas. Colunas, tipos e constraints divergem entre a versão Alembic e o SQL direto.

**Recomendação**: Escolher uma fonte de verdade (Alembic recomendado) e remover o arquivo conflitante.

#### MEDIUM — Inconsistência de type hints

**Arquivos**: `src/config/settings.py:6`, `src/context/monitor.py:4-6`

Alguns módulos usam `List`, `Dict`, `Optional` (estilo Python 3.9) enquanto o resto do codebase usa sintaxe moderna 3.10+ (`list`, `dict`, `X | None`).

```python
# settings.py:6 — Inconsistente
from typing import List

# Deveria ser:
DISCORD_INTENTS: list[str] = Field(...)
```

#### MEDIUM — Código duplicado entre tiers de memória

**Arquivos**: `src/memory/core.py`, `recall.py`, `archival.py`

O helper `_affected_rows()` e padrões de `acquire()`/`transaction()` estão duplicados nos três módulos.

**Recomendação**: Extrair classe base `src/memory/base.py` com os métodos comuns.

#### MEDIUM — Exception catching genérico

**Arquivos**: `src/memory/recall.py:48`, `src/discord/events.py:37,117`, `src/knowledge/graph.py:124`

Uso de `except Exception:` sem logging adequado ou re-raise com contexto, engolindo erros silenciosamente.

**Recomendação**: Capturar exceções específicas ou re-lançar com contexto via `raise XError(...) from e`.

#### MEDIUM — Pydantic v2 com Config class legado

**Arquivo**: `src/schemas/discord.py:61`

Usa `class Config:` (padrão Pydantic v1) ao invés de `model_config = ConfigDict(...)` (padrão v2).

#### MEDIUM — Imports não utilizados

**Arquivos**:
- `src/discord/commands.py` — `asyncio` importado mas não utilizado
- `src/knowledge/graph.py` — `AsyncIterator` importado mas não utilizado
- `src/memory/core.py` — `AsyncIterator` importado mas não utilizado

#### MEDIUM — ContextManager com muitas responsabilidades

**Arquivo**: `src/context/manager.py`

A classe acumula token counting, message management, offloading coordination e monitoring. Viola o princípio de responsabilidade única.

**Recomendação**: Delegar responsabilidades ao `ContextReducer` e `ContextMonitor` existentes.

#### LOW — Números mágicos hardcoded

**Arquivos**: `src/knowledge/graph.py:106`, `src/memory/recall.py:45`, `src/context/reducer.py:60,82,98`

Dimensão de embedding (`1536`), limites de token e thresholds hardcoded no código.

**Recomendação**: Extrair para constantes em `settings.py` ou constantes de módulo.

#### LOW — `__pycache__` comitado no repositório

Bytecode Python compilado está no git. Adicionar `__pycache__/` e `*.pyc` ao `.gitignore`.

#### LOW — Arquivo de debug no repositório

O arquivo `analisecoderabbit_debug.md` (238 KB) parece ser output de debug/análise e não deveria estar versionado.

---

## 3. Análise de Performance

### 3.1 Pontos Fortes

- Codebase inteiramente async com `asyncio` — sem I/O bloqueante nas operações principais
- Pool de conexões asyncpg (quando implementado) para reutilização de conexões
- Rate limiting previne sobrecarga do bot
- Cache LRU na Core Memory com eviction por importância

### 3.2 Problemas Encontrados

#### CRITICAL — Operações de banco falham (pool não inicializado)

**Arquivo**: `src/main.py:53-75`

Conforme descrito na seção de qualidade, o pool asyncpg nunca é criado. Todas as operações de banco via asyncpg geram `AttributeError: 'NoneType' object has no attribute 'acquire'`.

#### HIGH — Sem cache de embeddings para queries repetidas

**Arquivos**: `src/memory/recall.py:136-142`, `src/knowledge/graph.py:411-431`

Cada busca semântica gera um novo embedding via API OpenAI, mesmo para queries idênticas. Exemplo: buscar "quem é Agnaldo?" 3 vezes = 3 chamadas à API = latência e custo desnecessários.

**Recomendação**: Implementar cache de embeddings com `async_lru` (já é dependência do projeto) e TTL de 5-10 minutos.

```python
from async_lru import alru_cache

@alru_cache(maxsize=256, ttl=300)
async def _get_embedding(text: str) -> list[float]:
    response = await openai_client.embeddings.create(...)
    return response.data[0].embedding
```

#### HIGH — Background tasks sem limite

**Arquivo**: `src/memory/core.py:71-83`

O método `_schedule_access_update()` cria uma `asyncio.Task` para cada acesso à memória sem limitar concorrência. Com 10.000 acessos rápidos, 10.000 tasks são criadas em `_background_tasks`.

**Recomendação**: Usar `asyncio.Semaphore(10)` para limitar tasks concorrentes, ou batch updates com intervalo.

#### HIGH — Query N+1 no Knowledge Graph

**Arquivo**: `src/knowledge/graph.py:536-578`

O método `get_neighbors()` usa UNION em subqueries que escaneiam a tabela `edges` duas vezes por chamada (uma para edges de saída, outra para entrada).

**Recomendação**: Unificar em uma query com `WHERE source_id = $1 OR target_id = $1`.

#### MEDIUM — I/O bloqueante no startup

**Arquivo**: `src/main.py:88`

`soul_path.read_text()` é operação síncrona de filesystem em contexto async.

**Recomendação**: Usar `aiofiles` ou aceitar o bloqueio apenas no startup (documentar decisão).

#### MEDIUM — Sessões de contexto sem cleanup

**Arquivo**: `src/context/manager.py:57`

O dicionário `self.sessions` cresce indefinidamente sem TTL ou limpeza de sessões inativas. Em cenários de uso prolongado, consome memória crescente.

**Recomendação**: Implementar cleanup periódico de sessões inativas (> 30 min).

#### MEDIUM — Índices compostos ausentes

**Arquivo**: `src/database/models.py`

Faltam índices compostos para queries frequentes:
- `messages(user_id, session_id, created_at)` — busca de histórico
- `archival_memories(user_id, source, session_id)` — busca por sessão
- `recall_memories(user_id, created_at)` — ordenação temporal

#### MEDIUM — Cliente Supabase REST é síncrono

**Arquivo**: `src/database/supabase.py:11`

A biblioteca `supabase-py` faz requests HTTP síncronos, podendo bloquear o event loop quando usada para operações de dados.

**Recomendação**: Usar `supabase-py` apenas para autenticação e RPC. Para queries, usar exclusivamente `asyncpg`.

#### MEDIUM — `time.time()` no rate limiter

**Arquivo**: `src/discord/rate_limiter.py:44-85`

Usa `time.time()` que é afetado por ajustes de relógio (NTP sync). Pode causar intervalos negativos.

**Recomendação**: Usar `time.monotonic()` para medições de intervalo.

#### MEDIUM — Eviction de cache com lógica incremental

**Arquivo**: `src/context/offloading.py:112-126`

A eviction do cache remove apenas 1 item por vez, mas `offload()` adiciona novos itens antes de verificar capacidade.

**Recomendação**: Verificar capacidade antes de adicionar e remover em batch se necessário.

#### MEDIUM — Modelo sentence-transformers carregado sem lazy loading

**Arquivo**: `src/intent/classifier.py:48-54`

O modelo `all-MiniLM-L6-v2` (~90 MB) é carregado na memória durante a primeira classificação. Pode causar spike de memória e latência na primeira request.

**Recomendação**: Carregar durante o startup (warm-up) para evitar latência na primeira request do usuário.

---

## 4. Cobertura de Testes

### 4.1 Status Atual: CRITICAL (~5-10%)

| Métrica | Valor |
|---------|-------|
| Módulos com testes | 3 / 30 (10%) |
| Funções de teste | 8 |
| Cobertura estimada | ~5-10% |
| Meta do projeto | 80%+ |

### 4.2 Matriz de Cobertura por Módulo

| Camada | Módulos | Testados | Nível |
|--------|---------|----------|-------|
| Memória | `core.py`, `recall.py`, `archival.py` | core (~20%), archival (~15%) | recall = **0%** |
| Knowledge Graph | `graph.py` | ~30% | Parcial |
| Agentes | `orchestrator.py` | — | **0%** |
| Intent | `classifier.py`, `models.py`, `router.py` | — | **0%** |
| Contexto | `manager.py`, `reducer.py`, `offloading.py`, `monitor.py` | — | **0%** |
| Discord | `bot.py`, `commands.py`, `events.py`, `handlers.py`, `rate_limiter.py` | — | **0%** |
| Database | `models.py`, `supabase.py`, `rls_policies.py` | — | **0%** |
| Config/Utils | `settings.py`, `logger.py`, `error_handlers.py`, `exceptions.py` | — | **0%** |
| Schemas | `agents.py`, `memory.py`, `context.py`, `discord.py` | — | **0%** |

### 4.3 Problemas de Qualidade dos Testes Existentes

1. **Helper `_build_mock_pool()` duplicado** em `test_memory.py` e `test_graph.py` — deveria estar em `tests/fixtures/conftest.py`
2. **Sem testes de edge cases**: inputs vazios, valores inválidos, concorrência
3. **Sem testes negativos**: validação de erros, SQL injection, timeouts
4. **Diretórios vazios**: `test_agents/`, `test_context/`, `test_intent/`, `fixtures/` existem mas não contêm testes
5. **Sem testes de integração real**: todos os testes usam mocks, nenhum testa contra banco real

### 4.4 Prioridade de Testes a Implementar

| Prioridade | Módulo | Justificativa |
|------------|--------|---------------|
| P0 | `src/memory/recall.py` | Core da busca semântica, 0% cobertura |
| P0 | `src/agents/orchestrator.py` | Centro do sistema multi-agente, 0% |
| P1 | `src/intent/classifier.py` | Roteamento depende disto, 0% |
| P1 | `src/discord/rate_limiter.py` | Proteção contra abuso, 0% |
| P2 | `src/config/settings.py` | Validação de configuração |
| P2 | `src/discord/commands.py` | Interface principal do usuário |

---

## 5. Arquitetura e Design

### 5.1 Avaliação Geral

A arquitetura é **bem concebida** para o problema proposto:

- **Memória em 3 camadas**: Core (rápida), Recall (semântica), Archival (longo prazo) — padrão inspirado no MemGPT
- **Orquestração multi-agente**: 4 agentes especializados coordenados por intent
- **Classificação de intents**: Modelo local (sentence-transformers) sem dependência de API externa
- **Grafo de conhecimento**: networkx + pgvector para relações semânticas

### 5.2 Pontos de Atenção

- **Integração incompleta**: Componentes individuais estão bem escritos, mas a integração entre eles está faltando (pool asyncpg, event handlers)
- **Sem CI/CD**: Nenhuma pipeline configurada para testes automatizados ou deploy
- **Falta observabilidade end-to-end**: OpenTelemetry está como dependência mas não configurado

---

## 6. Plano de Ação Priorizado

### P0 — Bloqueadores (corrigir antes de qualquer deploy)

| # | Problema | Arquivo | Ação |
|---|----------|---------|------|
| 1 | Pool asyncpg não inicializado | `src/main.py` | Criar pool e atribuir a `bot.db_pool` no startup |
| 2 | Handler de mensagens desconectado | `src/discord/events.py` | Conectar `on_message` ao `MessageHandler` |
| 3 | Schema de migração divergente | `migrations/versions/` | Alinhar Alembic com SQL direto, remover duplicata |

### P1 — Segurança (corrigir antes de produção)

| # | Problema | Arquivo | Ação |
|---|----------|---------|------|
| 4 | URL do Supabase nos logs | `main.py`, `supabase.py` | Remover dados de conexão dos logs |
| 5 | JSON path injection | `archival.py` | Usar operadores JSONB nativos |
| 6 | Inputs sem validação | `commands.py` | Adicionar limites de comprimento |
| 7 | API key em exceções | `recall.py` | Sanitizar mensagens de erro |

### P2 — Performance (impacto na experiência do usuário)

| # | Problema | Arquivo | Ação |
|---|----------|---------|------|
| 8 | Sem cache de embeddings | `recall.py`, `graph.py` | Cache com `async_lru` e TTL |
| 9 | Background tasks ilimitadas | `core.py` | Semáforo com max 10 concurrent |
| 10 | Sessões sem cleanup | `manager.py` | TTL de 30 min com cleanup periódico |
| 11 | Índices compostos ausentes | `models.py` | Criar índices para queries frequentes |

### P3 — Qualidade de Código (melhoria contínua)

| # | Problema | Ação |
|---|----------|------|
| 12 | Cobertura de testes ~5% | Implementar testes P0 e P1 (recall, orchestrator, classifier) |
| 13 | `threading.Lock` em async | Trocar por `asyncio.Lock` em `settings.py` |
| 14 | Type hints inconsistentes | Padronizar para sintaxe 3.10+ em todo o codebase |
| 15 | Código duplicado nos tiers | Extrair classe base `memory/base.py` |
| 16 | `__pycache__` no repositório | Adicionar ao `.gitignore` |
| 17 | Configurar CI/CD | GitHub Actions com pytest + ruff + mypy |

---

## 7. Conclusão

O Agnaldo possui uma **base arquitetural excelente** com padrões modernos e decisões técnicas bem fundamentadas. Os **3 bloqueadores P0** são a prioridade imediata — sem corrigi-los, o bot não funciona além de slash commands básicos (`/ping`, `/help`, `/status`).

Após resolver P0 e P1, o projeto estará pronto para testes em ambiente de staging. A **cobertura de testes** é o maior débito técnico para sustentabilidade a longo prazo — alcançar 80% deve ser meta antes do primeiro release.

| Aspecto | Nota | Comentário |
|---------|------|------------|
| Arquitetura | A | Bem pensada, padrões modernos |
| Segurança | B- | Boas práticas mas com lacunas |
| Qualidade de Código | B | Sólido mas com débitos técnicos |
| Performance | C+ | Bom design mas problemas de integração |
| Testes | D | Cobertura crítica (~5-10%) |
| Documentação | A- | Completa em PT-BR, 9 guias |
| **Geral** | **B-** | **Pronto para staging após P0/P1** |
