# CLAUDE.md - Guia do Repositório Agnaldo

## Visão Geral do Projeto

**Agnaldo** é um bot Discord inteligente construído com o **framework Agno AI**, que implementa orquestração multi-agente, memória de longo prazo em três camadas e grafo de conhecimento semântico.

- **Linguagem**: Python 3.10+ (async-first)
- **Framework de IA**: Agno
- **LLM**: OpenAI gpt-4o
- **Embeddings**: text-embedding-3-small (OpenAI) + all-MiniLM-L6-v2 (local)
- **Banco de Dados**: Supabase PostgreSQL + pgvector
- **Gerenciador de Pacotes**: uv

---

## Estrutura do Repositório

```text
agnaldo/
├── src/                           # Código-fonte principal
│   ├── main.py                    # Ponto de entrada (startup + graceful shutdown)
│   ├── exceptions.py              # Hierarquia customizada de exceções
│   ├── agents/
│   │   └── orchestrator.py        # Coordenador multi-agente (4 agentes)
│   ├── config/
│   │   └── settings.py            # Configurações Pydantic via variáveis de ambiente
│   ├── context/
│   │   ├── manager.py             # Gerenciamento de tokens de contexto
│   │   ├── monitor.py             # Monitoramento de métricas
│   │   ├── offloading.py          # Offloading baseado em cache
│   │   └── reducer.py             # Redução de tokens
│   ├── database/
│   │   ├── models.py              # Modelos SQLAlchemy ORM
│   │   ├── supabase.py            # Wrapper do cliente Supabase (singleton)
│   │   ├── rls_policies.py        # Políticas de Row-Level Security
│   │   └── migrations/versions/   # Migrações Alembic e SQL
│   ├── discord/
│   │   ├── bot.py                 # Classe do bot Discord (AgnaldoBot)
│   │   ├── commands.py            # Slash commands (/ping, /help, /status)
│   │   ├── events.py              # Handlers de eventos
│   │   ├── handlers.py            # Processamento de mensagens
│   │   └── rate_limiter.py        # Rate limiter com token bucket
│   ├── intent/
│   │   ├── classifier.py          # Classificação semântica de intents
│   │   ├── models.py              # Enum IntentCategory (13 categorias)
│   │   └── router.py              # Roteamento de intents
│   ├── knowledge/
│   │   └── graph.py               # Grafo de conhecimento com embeddings
│   ├── memory/
│   │   ├── core.py                # Memória Core (key-value rápido, ~100 itens)
│   │   ├── recall.py              # Memória Recall (busca semântica via pgvector)
│   │   └── archival.py            # Memória Archival (armazenamento comprimido)
│   ├── schemas/                   # Schemas Pydantic v2
│   │   ├── agents.py              # Mensagens entre agentes
│   │   ├── context.py             # Schemas de contexto
│   │   ├── discord.py             # Schemas Discord
│   │   └── memory.py              # Schemas dos tiers de memória
│   ├── templates/                 # Templates OpenClaw de personalidade
│   ├── tools/osint/               # Ferramentas OSINT (placeholder)
│   └── utils/
│       ├── logger.py              # Configuração loguru
│       └── error_handlers.py      # Tratamento de erros
├── tests/                         # Testes automatizados
│   ├── test_memory.py             # Testes de integração de memória
│   ├── test_graph.py              # Testes do grafo de conhecimento
│   ├── test_agents/               # Testes de agentes
│   ├── test_intent/               # Testes do classificador de intents
│   ├── test_context/              # Testes do gerenciador de contexto
│   └── fixtures/                  # Fixtures compartilhadas
├── docs/                          # Documentação em PT-BR (9 guias)
├── .claude/                       # Configuração Claude AI (agentes e comandos)
├── SOUL.md                        # Definição de personalidade do bot
├── pyproject.toml                 # Metadados e dependências do projeto
├── uv.lock                        # Versões travadas de dependências
└── .env.example                   # Template de variáveis de ambiente
```

---

## Comandos Essenciais de Desenvolvimento

### Instalação e Setup

```bash
# Instalar dependências com uv
uv sync

# Instalar com dependências de desenvolvimento
uv sync --group dev

# Copiar e configurar variáveis de ambiente
cp .env.example .env
```

### Execução

```bash
# Rodar o bot
uv run python -m src.main

# Ou diretamente
uv run python src/main.py
```

### Testes

```bash
# Rodar todos os testes
uv run pytest

# Com cobertura
uv run pytest --cov=src --cov-report=term-missing

# Testes específicos
uv run pytest tests/test_memory.py
uv run pytest tests/test_agents/
```

### Linting e Formatação

```bash
# Formatação com Black
uv run black src/ tests/

# Linting com Ruff
uv run ruff check src/ tests/

# Correção automática com Ruff
uv run ruff check --fix src/ tests/

# Type checking com mypy
uv run mypy src/
```

---

## Configuração do Projeto

### Variáveis de Ambiente Obrigatórias

| Variável                    | Descrição                            |
|-----------------------------|--------------------------------------|
| `DISCORD_BOT_TOKEN`        | Token do bot Discord                 |
| `SUPABASE_URL`             | URL do projeto Supabase              |
| `SUPABASE_DB_URL`          | String de conexão PostgreSQL         |
| `SUPABASE_SERVICE_ROLE_KEY`| Chave de serviço do Supabase         |
| `OPENAI_API_KEY`           | Chave da API OpenAI                  |

### Variáveis Opcionais (com defaults)

| Variável                      | Default                  |
|-------------------------------|--------------------------|
| `ENVIRONMENT`                 | `dev`                    |
| `LOG_LEVEL`                   | `INFO`                   |
| `OPENAI_CHAT_MODEL`          | `gpt-4o`                 |
| `OPENAI_EMBEDDING_MODEL`     | `text-embedding-3-small` |
| `SENTENCE_TRANSFORMER_MODEL` | `all-MiniLM-L6-v2`      |
| `CACHE_MAX_SIZE`             | `1000`                   |
| `CACHE_TTL`                  | `300` (segundos)         |
| `RATE_LIMIT_GLOBAL`          | `50` req/s               |
| `RATE_LIMIT_PER_CHANNEL`     | `5` req/s                |

### Ferramentas de Qualidade

- **Black**: Formatação (line-length: 100, Python 3.10-3.12)
- **Ruff**: Linting (regras: E, F, I, N, W, UP; ignora E501)
- **mypy**: Type checking (Python 3.10, `disallow_untyped_defs=false`)
- **pytest**: Testes (asyncio_mode: auto, testpaths: tests/)

---

## Arquitetura e Decisões Técnicas

### Sistema de Memória em Três Camadas

1. **Core Memory** (`src/memory/core.py`): Cache key-value em memória com persistência no banco. Máximo ~100 itens com scoring de importância e eviction LRU ponderada.
2. **Recall Memory** (`src/memory/recall.py`): Busca semântica via embeddings OpenAI + pgvector. Filtragem por threshold de similaridade.
3. **Archival Memory** (`src/memory/archival.py`): Armazenamento comprimido de longo prazo com metadados JSONB e hash de conteúdo.

Todas as memórias são isoladas por `user_id`.

### Orquestração Multi-Agente

O `AgentOrchestrator` (`src/agents/orchestrator.py`) coordena 4 tipos de agentes:
- **Conversational**: Chat natural
- **Knowledge**: RAG e Q&A
- **Memory**: Operações nos três tiers de memória
- **Graph**: Consultas ao grafo de conhecimento

Roteamento baseado em intent classification via sentence-transformers.

### Padrões de Código

- **Singleton com async lock**: Usado para `AgentOrchestrator`, `Settings` e `SupabaseClient`
- **Async/await por todo o codebase**: Sem I/O bloqueante
- **asyncpg** para PostgreSQL (não psycopg)
- **Pydantic v2** para schemas e validação
- **Union types modernos**: `str | None` ao invés de `Optional[str]`
- **Context managers assíncronos**: Para gerenciamento de recursos
- **Hierarquia de exceções**: Base `AgnaldoError` com subclasses específicas

### Sequência de Startup

1. Carregar configuração do `.env` via Pydantic Settings
2. Inicializar conexões com banco de dados (Supabase)
3. Criar instância do bot com personalidade (SOUL.md)
4. Registrar event handlers e slash commands
5. Iniciar bot com suporte a graceful shutdown (SIGINT/SIGTERM)

---

## Convenções e Regras para Assistentes IA

### Linguagem

- **Toda documentação e comentários em código devem ser em PT-BR** (português brasileiro)
- Nomes de variáveis, funções e classes em **inglês** (padrão Python)
- Docstrings podem ser em inglês (padrão existente) ou PT-BR

### Estilo de Código

- Linha máxima de **100 caracteres** (Black + Ruff)
- Python **3.10+** com type hints modernos (`X | Y` ao invés de `Union[X, Y]`)
- Todas as operações de I/O devem ser **async**
- Usar `loguru` para logging (nunca `print()` ou `logging` padrão)
- Seguir a hierarquia de exceções existente (`src/exceptions.py`)
- Parâmetros SQL sempre parametrizados (prevenção de SQL injection)

### Estrutura de Novos Módulos

- Todo novo módulo deve ter `__init__.py`
- Schemas Pydantic v2 em `src/schemas/`
- Modelos de banco em `src/database/models.py`
- Testes correspondentes em `tests/` espelhando a estrutura de `src/`
- Usar fixtures compartilhadas em `tests/fixtures/`

### Testes

- Framework: **pytest** com **pytest-asyncio** (mode: auto)
- Usar `AsyncMock` para funções assíncronas
- Mocks de pool asyncpg para isolamento de banco
- Alvo de cobertura: mínimo 80%

### Banco de Dados

- **Supabase** para API REST e autenticação
- **asyncpg** para queries diretas ao PostgreSQL
- **pgvector** para colunas de embeddings
- Migrações via **Alembic** (`src/database/migrations/`)
- RLS (Row-Level Security) para isolamento de dados por usuário

### Git e Fluxo de Trabalho

- Branch principal: `main`
- Commits em português ou inglês, concisos e descritivos
- Sem CI/CD configurado no momento

---

## Problemas Conhecidos e Áreas Incompletas

1. **Pool asyncpg não inicializado**: `bot.db_pool` não é configurado em `src/main.py` — afeta comandos de memória
2. **Handler desconectado**: `on_message` existe em `handlers.py`, mas NÃO está conectado em `events.py`
3. **Divergência de schemas**: Diferenças entre `001_initial.py` (Alembic) e `001_create_memory_tables.sql` (SQL direto) — necessário alinhar
4. **Ferramentas OSINT**: `src/tools/osint/` é apenas um placeholder
5. **Operações de grafo**: Não completamente conectadas aos slash commands do Discord

---

## Documentação Existente

A pasta `docs/` contém documentação completa em PT-BR:

| Arquivo                           | Conteúdo                              |
|-----------------------------------|---------------------------------------|
| `docs/01-quickstart.md`           | Pré-requisitos, setup e execução      |
| `docs/02-uso-no-discord.md`       | Guia de uso no Discord                |
| `docs/03-memoria.md`             | Arquitetura de memória em 3 camadas   |
| `docs/04-prompts-e-personalidade.md` | Personalidade e engenharia de prompts |
| `docs/05-banco-de-dados.md`      | Schema do banco, migrações, asyncpg   |
| `docs/06-ferramentas-mit.md`     | Ferramentas MIT para prompts/evals    |
| `docs/07-troubleshooting.md`     | Problemas comuns e soluções           |
| `docs/08-templates-openclaw.md`  | Padrões de memória OpenClaw           |
| `docs/09-configuracao-discord.md`| Configuração do bot Discord           |

---

## Stack Tecnológica Resumida

| Camada           | Tecnologia                                        |
|------------------|---------------------------------------------------|
| Bot              | discord.py 2.4+                                   |
| Orquestração IA  | Agno framework                                    |
| LLM              | OpenAI gpt-4o                                     |
| Embeddings       | text-embedding-3-small + all-MiniLM-L6-v2         |
| Banco de Dados   | Supabase PostgreSQL + pgvector                    |
| Driver Async     | asyncpg                                           |
| ORM              | SQLAlchemy 2.0+                                   |
| Migrações        | Alembic                                           |
| Validação        | Pydantic v2                                       |
| HTTP             | httpx (async)                                     |
| Grafos           | networkx                                          |
| Tokens           | tiktoken                                          |
| Retry            | tenacity                                          |
| Logging          | loguru                                             |
| Observabilidade  | OpenTelemetry                                     |
| Testes           | pytest + pytest-asyncio + pytest-cov + pytest-mock |
| Formatação       | Black                                              |
| Linting          | Ruff                                               |
| Type Check       | mypy                                               |
