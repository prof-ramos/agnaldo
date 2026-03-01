# Plano de Implementação: Clean Code e Boas Práticas - Agnaldo

**Versão:** 1.2
**Data:** 28/02/2026
**Status:** Planejamento

---

## 1. Análise do Estado Atual

### 1.1 Métricas Atuais

**Baseline real aferido em 28/02/2026** com `uv run ruff check .`,
`uv run mypy src` e `uv run pytest --cov=src --cov-report=term -q`.

| Métrica | Valor | Meta |
|---------|-------|------|
| Arquivos Python (total / src / tests) | 100 / 61 / 35 | - |
| Ruff (`ruff check .`) | 178 issues (84 autofixáveis) | 0 |
| Mypy (`mypy src`) | 163 erros em 25 arquivos | 0 |
| Pytest (suíte atual) | 208 passed / 4 failed / 12 errors | 100% passando |
| Cobertura de testes | 42% (4565 stmts, 2500 miss) | 80% |
| Débito técnico | Alto (lint + type + testes quebrados) | Baixo |
| Documentação | Parcial | Completa |

### 1.2 Pontos Fortes

- ✅ Estrutura de módulos bem organizada (`src/`, `tests/`, `docs/`)
- ✅ Type hints em boa parte do código
- ✅ Sistema de isolamento de memória implementado
- ✅ GraphService com extração automática
- ✅ Documentação técnica (PRD.md, ARCHITECTURE.md, CLAUDE.md)
- ✅ pyproject.toml com dependências organizadas
- ✅ Ferramentas de dev configuradas (pytest, black, ruff, mypy)
- ✅ Suite de testes relevante já existente (208 testes verdes no baseline)

### 1.3 Pontos a Melhorar

- 🔴 Corrigir primeiro os 12 erros e 4 falhas da suíte para recuperar confiança no pipeline
- 🔴 Reduzir débito de lint (178 issues) e tipagem (163 erros) com abordagem incremental por módulo
- 🟠 Fechar lacunas de cobertura críticas (`main.py`, `discord/events.py`, `context/*`, `database/supabase.py`, `intent/router.py`)
- 🟠 Eliminar duplicação em handlers e funções extensas nos módulos de orquestração
- 🟠 Padronizar tratamento de erro/retry nas operações externas
- 🟡 Uniformizar docstrings e contratos de APIs públicas
- 🟡 Consolidar logging estruturado e telemetria operacional

### 1.4 Escopo do Plano (Baseado em `repomix-output.xml`)

- Escopo principal de execução: `src/`, `tests/`, `docs/`, `pyproject.toml`, `ruff.toml`, `mypy.ini`, `.pre-commit-config.yaml`.
- Escopo secundário: `README.md` e `ARCHITECTURE.md` para atualizar decisões/resultados.
- Fora do foco de clean code funcional: artefatos operacionais/sessão (`.claude/`, `.omc/`) que não impactam runtime do bot.

---

## 2. Objetivos

### 2.1 Objetivo Principal

Transformar o Agnaldo em um projeto de referência em Clean Code, com alta
manutenibilidade, testabilidade e documentação completa.

### 2.2 Objetivos Específicos

1. **Qualidade de Código**
   - Aplicar princípios SOLID
   - Eliminar code smells
   - Padronizar nomenclatura

2. **Testes**
   - Atingir 80% de cobertura
   - Implementar testes de integração
   - Adicionar testes de mutação

3. **Documentação**
   - Docstrings em todos os módulos públicos
   - Exemplos de uso em cada módulo
   - Diagramas de arquitetura

4. **Observabilidade**
   - Logging estruturado
   - Métricas com OpenTelemetry
   - Tracing distribuído

5. **Performance**
   - Identificar e otimizar gargalos
   - Implementar caching inteligente
   - Reduzir latência de operações

### 2.3 Diretrizes Técnicas (Base Context7)

As decisões abaixo seguem práticas recomendadas consultadas no Context7
para `pytest`, `pre-commit` e `OpenTelemetry Python`:

| Área | Diretriz | Aplicação no projeto |
|------|----------|----------------------|
| Pytest | Centralizar fixtures compartilhadas em `tests/conftest.py` e especializar por subpastas quando necessário | Reduzir duplicação e melhorar isolamento |
| Pytest | Usar `scope` adequado (`function`, `module`, `package`, `session`) para recursos caros | Acelerar suíte sem perder confiabilidade |
| Pytest | Usar marcadores explícitos e validação estrita (`--strict-markers`) | Evitar testes mal categorizados e execução inconsistente |
| Pre-commit | Fixar revisões (`rev`) e executar `pre-commit run --all-files` no CI | Reprodutibilidade e qualidade uniforme |
| Pre-commit | Ordenar hooks por custo (rápidos antes, pesados depois) | Feedback mais rápido em commits locais |
| OpenTelemetry | Configurar tracing/métricas por variáveis `OTEL_*` | Ambientes dev/staging/prod com configuração padronizada |
| OpenTelemetry | Definir sampler explícito (ex.: `parentbased_traceidratio` em produção) | Controle de custo e volume de telemetria |
| OpenTelemetry | Garantir propagação de contexto com propagators globais | Traces ponta a ponta entre serviços |

---

## 3. Fases de Implementação

### FASE 0A: Estabilização do Baseline (Dias 1-3) - BLOQUEANTE

**Objetivo:** sair do estado "vermelho" para um baseline executável e confiável.

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 0A.1 | Corrigir erros de setup de `Settings` em `tests/test_graph_service.py` (fixtures/env defaults) | 🔴 Crítica | 3h | - |
| 0A.2 | Corrigir falhas em `tests/test_memory_isolation.py` e `tests/integration/test_agents/test_orchestrator.py` | 🔴 Crítica | 4h | - |
| 0A.3 | Executar baseline em Docker/Compose e registrar resultado | 🔴 Crítica | 2h | - |
| 0A.4 | Criar regra de ratchet: PR não pode piorar métricas de ruff/mypy/pytest | 🔴 Crítica | 1h | - |

**Entregáveis:**
- [ ] `pytest` sem erros de setup
- [ ] `pytest` com falhas críticas resolvidas
- [ ] Baseline documentado e reproduzível via Docker/Compose
- [ ] Gate de qualidade (ratchet) definido para PRs

### FASE 0: Setup (Semana 0)

**Objetivo:** preparar padrões, observabilidade de qualidade e operação contínua.

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 0.1 | Definir Definition of Done | 🔴 Crítica | 2h | - |
| 0.2 | Configurar SonarQube/CodeClimate | 🔴 Crítica | 2h | - |
| 0.3 | Definir stack Docker/Compose com comandos operacionais comuns (dev, test, lint, type-check) | 🟠 Média | 2h | - |
| 0.4 | Validar ambiente local com `uv` (`uv sync` + checagem de `.venv`) | 🔴 Crítica | 1h | - |
| 0.5 | Setup canais de comunicação | 🟠 Média | 1h | - |
| 0.6 | Mapear riscos completos | 🔴 Crítica | 2h | - |
| 0.7 | Definir SLIs/SLOs | 🟠 Média | 2h | - |

**Entregáveis:**
- [ ] Definition of Done documentada
- [ ] SonarQube/CodeClimate configurado
- [ ] `docker-compose.yml` funcional (com perfis/serviços para desenvolvimento e qualidade)
- [ ] Ambiente local com `uv` validado e reproduzível
- [ ] Risk log completo
- [ ] SLIs/SLOs definidos

### FASE 1: Fundação (Semana 1-2)

**Objetivo:** Estabelecer base de qualidade

#### Semana 1: Configuração e Análise

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 1.1 | Configurar pre-commit hooks (revisões pinadas e execução em CI) | 🔴 Alta | 2h | - |
| 1.2 | Configurar ruff com regras estritas | 🔴 Alta | 1h | - |
| 1.3 | Configurar mypy strict mode | 🔴 Alta | 2h | - |
| 1.4 | Reduzir Ruff de 178 para <= 90 issues (priorizando `scripts/run_tests.py` e imports/args não usados) | 🔴 Alta | 6h | - |
| 1.5 | Reduzir Mypy de 163 para <= 120 erros (foco em `src/base/*` e `src/discord/commands.py`) | 🔴 Alta | 6h | - |
| 1.6 | Definir estratégia de markers/fixtures no pytest (`--strict-markers`) | 🟠 Média | 2h | - |
| 1.7 | Executar análise estática completa (Docker/Compose) e publicar snapshot | 🔴 Alta | 2h | - |
| 1.8 | Mapear code smells existentes por severidade (alto/médio/baixo) | 🟠 Média | 4h | - |

**Entregáveis:**
- [ ] `.pre-commit-config.yaml` configurado
- [ ] `ruff.toml` com regras customizadas
- [ ] `pytest.ini` com markers explícitos e `--strict-markers`
- [ ] Ruff <= 90 issues
- [ ] Mypy <= 120 erros
- [ ] Relatório de análise estática
- [ ] Checklist de code review

#### Semana 2: Estrutura Base

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 2.1 | Consolidar `src/base/` (logging/exceptions/decorators/retry) sem aumentar dívida de tipo | 🔴 Alta | 4h | - |
| 2.2 | Implementar logging estruturado com contexto mínimo (request_id, user_id_hash, operation, duration_ms) | 🔴 Alta | 3h | - |
| 2.3 | Criar decoradores utilitários (timeout/retry/telemetria) com testes unitários | 🟠 Média | 3h | - |
| 2.4 | Padronizar exceções customizadas e mapping de erros externos | 🟠 Média | 2h | - |
| 2.5 | Criar fixtures de teste base com escopo explícito (`function/module/session`) | 🟠 Média | 3h | - |
| 2.6 | Reduzir Mypy para <= 80 erros ao final da fase | 🔴 Alta | 4h | - |

**Entregáveis:**
- [ ] Módulo `src/base/` com:
  - `logging.py` - Logger estruturado
  - `exceptions.py` - Exceções padronizadas
  - `decorators.py` - Decoradores úteis
  - `retry.py` - Configuração de retry
- [ ] `tests/conftest.py` com fixtures
- [ ] Mypy <= 80 erros

---

### FASE 2: Refatoração (Semana 3-4)

**Objetivo:** Eliminar débito técnico

#### Semana 3: Code Smells

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 3.1 | Eliminar métodos longos | 🔴 Alta | 8h | - |
| 3.2 | Reduzir duplicação de código | 🔴 Alta | 6h | - |
| 3.3 | Aplicar princípio de responsabilidade única | 🟠 Média | 8h | - |
| 3.4 | Melhorar nomenclatura | 🟡 Baixa | 4h | - |
| 3.5 | Simplificar condicionais complexas | 🟠 Média | 4h | - |

**Foco por módulo:**

```
src/
├── agents/
│   └── orchestrator.py     # Quebrar em classes menores
├── discord/
│   ├── handlers.py         # Reduzir duplicação
│   └── commands.py         # Extrair lógica de negócio
├── memory/
│   ├── manager.py          # Simplificar fluxos
│   └── recall.py           # Melhorar legibilidade
└── knowledge/
    └── graph_service.py    # Aplicar SRP
```

#### Semana 4: Padrões e Princípios

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 4.1 | Aplicar Dependency Inversion | 🟠 Média | 6h | - |
| 4.2 | Implementar Factory Pattern onde apropriado | 🟠 Média | 4h | - |
| 4.3 | Usar Strategy Pattern para intents | 🟡 Baixa | 4h | - |
| 4.4 | Aplicar Repository Pattern consistente | 🟠 Média | 4h | - |
| 4.5 | Revisar e melhorar injeção de dependência | 🟠 Média | 3h | - |

**Entregáveis:**
- [ ] Código refatorado sem code smells críticos
- [ ] Padrões de projeto aplicados
- [ ] Documentação das decisões arquiteturais

---

### FASE 3: Testes (Semana 5-6)

**Objetivo:** elevar cobertura de 42% para 60% e preparar o caminho para 80% na consolidação

#### Semana 5: Testes Unitários

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 5.1 | Cobrir `src/knowledge/graph_service.py` (baseline 28%) com cenários de sucesso/erro/edge | 🔴 Alta | 8h | - |
| 5.2 | Cobrir `src/discord/events.py` (baseline 0%) com testes de handlers/eventos | 🔴 Alta | 6h | - |
| 5.3 | Cobrir `src/intent/router.py` (baseline 0%) com roteamento e fallback | 🔴 Alta | 5h | - |
| 5.4 | Cobrir `src/database/supabase.py` (baseline 0%) com mocks de borda | 🟠 Média | 5h | - |
| 5.5 | Cobrir `src/context/*` e `src/main.py` (baseline 0%) focando bootstrap/fluxos críticos | 🟠 Média | 6h | - |
| 5.6 | Consolidar `pytest-cov` com relatório de tendência semanal | 🔴 Alta | 1h | - |

**Meta de cobertura por arquivo/módulo crítico (baseline real):**

| Arquivo/Módulo | Cobertura Atual | Meta Fase 3 |
|----------------|-----------------|-------------|
| `src/knowledge/graph_service.py` | 28% | 80% |
| `src/discord/events.py` | 0% | 70% |
| `src/intent/router.py` | 0% | 80% |
| `src/database/supabase.py` | 0% | 75% |
| `src/context/*` | 0% | 70% |
| `src/main.py` | 0% | 70% |
| Cobertura total (`src`) | 42% | 60% |

#### Semana 6: Testes de Integração

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 6.1 | Criar suite de integração para fluxo de memória (retrieve -> rank -> recall) | 🔴 Alta | 4h | - |
| 6.2 | Cobrir integração de comandos/eventos Discord com dublês estáveis | 🔴 Alta | 4h | - |
| 6.3 | Cobrir integração de banco (camada repositório) com contratos explícitos | 🟠 Média | 4h | - |
| 6.4 | Configurar CI/CD para executar unit e integration em jobs separados | 🔴 Alta | 2h | - |
| 6.5 | Medir e reduzir flakiness (re-run controlado + relatório semanal) | 🟠 Média | 2h | - |
| 6.6 | Adicionar testes de mutação (mutmut) nos módulos de regra de negócio | 🟡 Baixa | 3h | - |

**Entregáveis:**
- [ ] Cobertura de testes >= 80%
- [ ] Cobertura total >= 60% ao final da Fase 3
- [ ] Suite de testes de integração
- [ ] Pipeline CI/CD com testes
- [ ] Badge de cobertura no README

---

### FASE 4: Documentação (Semana 7-8)

**Objetivo:** Documentação completa e atualizada

#### Semana 7: Docstrings e Exemplos

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 7.1 | Adicionar docstrings em módulos públicos | 🔴 Alta | 8h | - |
| 7.2 | Criar exemplos de uso para cada módulo | 🟠 Média | 6h | - |
| 7.3 | Documentar APIs públicas | 🟠 Média | 4h | - |
| 7.4 | Atualizar README principal | 🟠 Média | 2h | - |
| 7.5 | Criar guia de contribuição (CONTRIBUTING.md) | 🟡 Baixa | 2h | - |

**Padrão de docstring (Google Style):**

```python
"""Descrição breve do módulo/classe/função.

Descrição mais detalhada se necessário.

Args:
    param1: Descrição do primeiro parâmetro.
    param2: Descrição do segundo parâmetro.

Returns:
    Descrição do retorno.

Raises:
    ExceptionType: Quando e por que é lançada.

Example:
    >>> from src.memory import MemoryManager
    >>> manager = MemoryManager(user_id="user123", db_pool=pool)
    >>> context = await manager.retrieve_context("query")
"""
```

#### Semana 8: Arquitetura e Diagramas

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 8.1 | Criar diagrama de arquitetura | 🟠 Média | 3h | - |
| 8.2 | Diagrama de fluxo de dados | 🟠 Média | 2h | - |
| 8.3 | Diagrama de classes principais | 🟡 Baixa | 2h | - |
| 8.4 | Documentar decisões arquiteturais (ADRs) | 🟠 Média | 3h | - |
| 8.5 | Atualizar ARCHITECTURE.md | 🟠 Média | 2h | - |
| 8.6 | Criar changelog (CHANGELOG.md) | 🟡 Baixa | 1h | - |

**Entregáveis:**
- [ ] Docstrings em 100% das APIs públicas
- [ ] Exemplos de uso em cada módulo
- [ ] Diagramas de arquitetura
- [ ] ADRs documentados
- [ ] CONTRIBUTING.md

---

### FASE 5: Observabilidade (Semana 9-10)

**Objetivo:** Sistema observável e monitorável

#### Semana 9: Logging e Métricas

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 9.1 | Implementar logging estruturado (JSON) | 🔴 Alta | 4h | - |
| 9.2 | Adicionar métricas com OpenTelemetry | 🟠 Média | 6h | - |
| 9.3 | Criar dashboard de métricas | 🟡 Baixa | 4h | - |
| 9.4 | Configurar alertas básicos | 🟡 Baixa | 2h | - |
| 9.5 | Documentar esquema de logs | 🟠 Média | 2h | - |

**Estrutura de log:**

```json
{
  "timestamp": "2026-02-28T17:00:00Z",
  "level": "INFO",
  "logger": "src.memory.manager",
  "message": "Context retrieved",
  "user_id_hash": "a1b2c3d4",
  "operation": "retrieve_context",
  "duration_ms": 45,
  "context": {
    "core_items": 10,
    "recall_items": 5
  }
}
```

#### Semana 10: Tracing e Performance

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 10.1 | Implementar tracing distribuído | 🟠 Média | 6h | - |
| 10.2 | Identificar gargalos de performance | 🔴 Alta | 4h | - |
| 10.3 | Otimizar queries SQL | 🟠 Média | 4h | - |
| 10.4 | Implementar caching onde necessário | 🟠 Média | 4h | - |
| 10.5 | Benchmarking de operações críticas | 🟡 Baixa | 2h | - |

**Entregáveis:**
- [ ] Sistema de logging estruturado
- [ ] Métricas exportadas via OpenTelemetry
- [ ] Tracing distribuído funcional
- [ ] Relatório de performance

---

### FASE 6: Consolidação (Semana 11-12)

**Objetivo:** Revisão e ajustes finais

#### Semana 11: Code Review Final

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 11.1 | Code review completo do projeto | 🔴 Alta | 8h | - |
| 11.2 | Validar cobertura de testes | 🔴 Alta | 2h | - |
| 11.3 | Validar documentação | 🟠 Média | 4h | - |
| 11.4 | Corrigir issues encontrados | 🔴 Alta | 8h | - |
| 11.5 | Atualizar dependências | 🟡 Baixa | 2h | - |

#### Semana 12: Finalização

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 12.1 | Criar release v1.0 | 🔴 Alta | 2h | - |
| 12.2 | Atualizar ROADMAP.md | 🟠 Média | 1h | - |
| 12.3 | Documentar lições aprendidas | 🟡 Baixa | 2h | - |
| 12.4 | Apresentar resultados | 🔴 Alta | 2h | - |
| 12.5 | Planejar próxima iteração | 🟠 Média | 2h | - |

---

## 4. Checklist de Clean Code

### 4.1 Nomenclatura

- [ ] Nomes revelam intenção
- [ ] Nomes são pronunciáveis
- [ ] Nomes são buscáveis
- [ ] Sem abreviações desnecessárias
- [ ] Encoding hungarian proibido

### 4.2 Funções

- [ ] Funções são pequenas (< 30 linhas)
- [ ] Funções fazem uma coisa só
- [ ] Funções têm um nível de abstração
- [ ] Parâmetros limitados (max 3-4)
- [ ] Sem efeitos colaterais surpresa
- [ ] Preferir retorno cedo (early return)

### 4.3 Comentários

- [ ] Código é autoexplicativo
- [ ] Comentários explicam "por que", não "o que"
- [ ] TODOs têm issue associado
- [ ] Sem código comentado

### 4.4 Formatação

- [ ] Formatação consistente (black)
- [ ] Imports organizados (isort)
- [ ] Linhas em branco separam conceitos
- [ ] Regra 120 colunas

### 4.5 Tratamento de Erros

- [ ] Exceções em vez de códigos de erro
- [ ] Mensagens de erro informativas
- [ ] Exceções específicas
- [ ] Retry com backoff exponencial
- [ ] Logs estruturados em erros

### 4.6 Testes

- [ ] Testes são legíveis
- [ ] Um conceito por teste
- [ ] Padrão AAA (Arrange, Act, Assert)
- [ ] Testes são independentes
- [ ] Nomes descritivos de testes

---

## 5. Ferramentas e Configurações

### 5.1 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
minimum_pre_commit_version: "3.6.0"
repos:
  # Hooks rápidos e genéricos primeiro
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: debug-statements

  # Lint/format Python
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # Type checking (hook mais pesado depois dos rápidos)
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-asyncpg]
```

**Operação recomendada:**

- Local: `pre-commit install`
- Verificação completa local: `pre-commit run --all-files`
- CI: executar o mesmo comando (`pre-commit run --all-files`) para paridade local/CI
- Manutenção: `pre-commit autoupdate` quinzenal com PR dedicado

### 5.2 Ruff Configuration

```toml
# ruff.toml
target-version = "py310"
line-length = 120

[lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "ERA",    # eradicate
    "RUF",    # Ruff-specific rules
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # function call in default argument
]

[lint.per-file-ignores]
"tests/*" = ["ARG", "S101"]
```

### 5.3 Mypy Configuration

```toml
# mypy.ini
[mypy]
python_version = 3.10
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
plugins = pydantic.mypy

[pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
```

### 5.4 Pytest Configuration (Markers, Scope e Execução)

```toml
# pyproject.toml (tool.pytest.ini_options) ou pytest.ini
[tool.pytest.ini_options]
addopts = [
  "--strict-markers",
  "--strict-config",
  "--cov=src",
  "--cov-report=term-missing",
]
markers = [
  "unit: Unit tests (fast, isolated)",
  "integration: Integration tests (deps reais/mocks de borda)",
  "e2e: End-to-end tests (fluxos críticos)"
]
```

**Diretriz de fixtures:**

- Recursos caros em `scope="module"` ou `scope="session"`.
- Fixtures compartilhadas em `tests/conftest.py`; especializações em subpastas.
- Evitar `autouse=True` global, exceto setup transversal e seguro (ex.: limpeza de cache).

### 5.5 OpenTelemetry (Configuração de Produção)

Configurar telemetria por variáveis de ambiente para evitar acoplamento de código:

- `OTEL_TRACES_EXPORTER`, `OTEL_TRACES_SAMPLER`, `OTEL_TRACES_SAMPLER_ARG`
- `OTEL_PROPAGATORS`, `OTEL_PYTHON_TRACER_PROVIDER`, `OTEL_PYTHON_METER_PROVIDER`
- Limites: `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`, `OTEL_SPAN_EVENT_COUNT_LIMIT`

**Padrão sugerido:**

- Dev: sampler `always_on`
- Produção: `parentbased_traceidratio` (ajustado por `OTEL_TRACES_SAMPLER_ARG`)
- Propagação de contexto obrigatória entre serviços usando propagators globais

### 5.6 Workflow Docker/Compose (Fonte de Verdade Operacional)

Todos os checks de qualidade devem possuir comando equivalente em Docker/Compose:

```bash
# Qualidade completa
docker compose run --rm app pre-commit run --all-files
docker compose run --rm app uv run ruff check .
docker compose run --rm app uv run mypy src
docker compose run --rm app uv run pytest -m "not e2e"

# Suíte completa (incluindo e2e)
docker compose run --rm app uv run pytest
```

### 5.7 Workflow Local com `uv` (paridade com Compose)

```bash
# Validar ambiente local
uv sync
test -d .venv && echo ".venv OK"

# Qualidade local (mesmos checks da pipeline)
uv run ruff check .
uv run mypy src
uv run pytest --cov=src --cov-report=term -q
```

---

## 6. Métricas de Sucesso

### 6.1 KPIs Técnicos

| KPI | Baseline | Meta FASE 3 | Meta Final | Como Medir |
|-----|----------|-------------|------------|------------|
| Cobertura de testes | 42% | 60% | 80% | pytest-cov |
| Branch coverage | 35% | 50% | 70% | pytest-cov --cov-branch |
| Ruff issues | 178 | <= 40 | 0 | `uv run ruff check .` |
| Mypy errors (`src`) | 163 | <= 40 | 0 | `uv run mypy src` |
| Status da suíte | 208P / 4F / 12E | 0E e <= 2F | 100% passando | `uv run pytest ...` |
| Complexidade ciclomática | - | < 10 | < 8 | radon/mccabe |
| Cognitive complexity | - | < 15 | < 10 | SonarQube |
| Duplicação de código | ~5% | < 3% | < 1% | SonarQube/jscpd |
| Maintainability Index | - | > 65 | > 75 | radon |
| Débito técnico | - | Médio | Baixo | SonarQube |
| Security rating | - | B | A | SonarQube/bandit |
| Documentação | ~50% | 80% | 100% | Manual |

### 6.2 KPIs de Processo

| KPI | Meta | Como Medir |
|-----|------|------------|
| Tempo médio de PR review | < 24h | GitHub metrics |
| Build time | < 5 min | CI logs |
| Test execution time | < 2 min | pytest duration |
| Pre-commit pass rate no CI | > 95% | CI logs (`pre-commit run --all-files`) |
| Ratchet de qualidade por PR | 100% dos PRs sem piorar Ruff/Mypy/Pytest | Comparação baseline no CI |
| Code review approval rate | > 90% | GitHub metrics |
| Lead time para PRs | < 3 dias | GitHub metrics |
| Defect escape rate | < 5% | Bug tracking |
| Flaky test rate | < 1% | Test reports |
| Mutation score | > 80% | mutmut |

### 6.3 SLIs/SLOs

| SLI | SLO | Janela |
|-----|-----|--------|
| Availability | 99.5% | Mensal |
| Latência p50 | < 200ms | Semanal |
| Latência p99 | < 1s | Semanal |
| Error rate | < 1% | Semanal |
| Throughput | > 100 req/s | Mensal |
| Taxa de spans com contexto propagado | > 95% | Semanal |

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar funcionalidades existentes | Média | Alto | Testes de regressão |
| Atraso na entrega | Média | Médio | Priorização rigorosa |
| Resistência a mudanças | Baixa | Médio | Documentação clara |
| Dependências desatualizadas | Baixa | Baixo | Atualização gradual |

---

## 8. Próximos Passos

### Imediato (Esta semana)

1. [ ] Corrigir blockers da Fase 0A: 12 erros de setup + 4 falhas da suíte
2. [ ] Publicar baseline oficial (Ruff 178, Mypy 163, Pytest 208P/4F/12E, Cobertura 42%)
3. [ ] Instalar/validar `pre-commit` com paridade local/CI (`pre-commit run --all-files`)
4. [ ] Consolidar comandos Docker/Compose para qualidade e testes
5. [ ] Validar ambiente local com `uv sync` e `.venv` operacional
6. [ ] Ativar ratchet no CI: PR não pode piorar métricas de qualidade

### Curto Prazo (Próximas 2 semanas - FASE 0 + FASE 1)

1. [ ] Completar FASE 0 (Setup) e FASE 1 (fundação de qualidade)
2. [ ] Reduzir Ruff para <= 90 e Mypy para <= 120
3. [ ] Estruturar backlog de refatoração por severidade e módulo
4. [ ] Configurar CI/CD com gates de lint/type/test/cobertura
5. [ ] Definir matriz `OTEL_*` por ambiente (dev/staging/prod)
6. [ ] Fechar checklist de risco e DoD com validação do time

### Médio Prazo (Próximas 6 semanas - FASE 2 + FASE 3)

1. [ ] Refatorar módulos críticos
2. [ ] Atingir 60% de cobertura
3. [ ] Documentação de APIs
4. [ ] Testes de integração
5. [ ] Primeiro benchmark de performance

### Longo Prazo (Próximas 12 semanas - FASE 4 + FASE 5 + FASE 6)

1. [ ] Atingir 80% de cobertura
2. [ ] Documentação completa
3. [ ] Sistema de observabilidade
4. [ ] Release v1.0
5. [ ] Post-mortem do projeto

### Checklist de Aprovação do Plano

Antes de iniciar, confirmar:

- [ ] Definition of Done revisada e aprovada
- [ ] Cronograma aceito com buffer de 30%
- [ ] Baseline oficial publicado (com data e comando de coleta)
- [ ] Riscos completos mapeados
- [ ] Pirâmide de testes definida
- [ ] SLIs/SLOs acordados
- [ ] Gate de ratchet ativo no CI
- [ ] Recursos alocados
- [ ] Comunicação configurada

---

## 9. Referências

- [Clean Code - Robert C. Martin](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [The Pragmatic Programmer - Andrew Hunt & David Thomas](https://pragprog.com/titles/tpp20/)
- [Refactoring - Martin Fowler](https://refactoring.com/)
- [Python Clean Code Guide](https://github.com/zedr/clean-code-python)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Pytest Documentation (fixtures/conftest/markers)](https://docs.pytest.org/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [OpenTelemetry Python Documentation](https://opentelemetry-python.readthedocs.io/)

---

**Aprovado por:** _______________
**Data de aprovação:** _______________

---

## 10. Definition of Done (DoD)

Uma tarefa só é considerada "Done" quando **TODOS** os critérios abaixo são atendidos:

### 10.1 Código

- [ ] Código implementado e funcionando
- [ ] Type hints completos (mypy passa sem erros)
- [ ] Linting passa (ruff sem erros)
- [ ] Sem código comentado
- [ ] Sem console.log/print de debug
- [ ] Imports organizados (isort/ruff)

### 10.2 Testes

- [ ] Testes unitários passando
- [ ] Cobertura do código novo >= 80%
- [ ] Testes de integração (se aplicável)
- [ ] Sem testes flaky
- [ ] `pytest` executado com `--strict-markers`
- [ ] Testes rodam em < 5 segundos (unitários) em ambiente local
- [ ] Comandos de teste validados também via Docker/Compose

### 10.3 Documentação

- [ ] Docstrings em APIs públicas
- [ ] Exemplos de uso (se módulo novo)
- [ ] README atualizado (se necessário)
- [ ] Changelog atualizado (se breaking change)

### 10.4 Revisão

- [ ] Self-review realizada
- [ ] Code review aprovado por 1+ revisor
- [ ] Sem comentários não resolvidos
- [ ] CI/CD passando
- [ ] `pre-commit run --all-files` passando localmente e no CI
- [ ] Ratchet respeitado: PR não piora Ruff/Mypy/Pytest em relação ao baseline

### 10.5 Qualidade

- [ ] Sem regressões conhecidas
- [ ] Performance não degradada
- [ ] Security scan passa (bandit)
- [ ] Complexidade ciclomática < 10
- [ ] Telemetria OpenTelemetry ativa com sampler definido para o ambiente
- [ ] Cobertura do módulo alterado não reduz

---

## 11. Pirâmide de Testes

### 11.1 Estratégia

```
         /\
        /  \       E2E Tests (5-10%)
       /----\      - Fluxo Discord completo
      /      \     - Cenários críticos
     /--------\    Integration Tests (20-30%)
    /          \   - DB operations (testcontainers)
   /            \  - API calls (mocked)
  /--------------\ Unit Tests (60-70%)
 /                \ - Business logic
/__________________\ - Pure functions
```

### 11.2 Critérios por Tipo

| Tipo | Cobertura | Velocidade | Isolamento |
|------|-----------|------------|------------|
| Unit | 60-70% | < 100ms | Total |
| Integration | 20-30% | < 1s | Parcial |
| E2E | 5-10% | < 30s | Nenhum |

### 11.3 Governança de Markers e Fixtures

- `unit`, `integration`, `e2e` devem ser os markers base obrigatórios.
- Novos markers exigem atualização do `pytest.ini` e justificativa no PR.
- Fixtures compartilhadas devem viver em `tests/conftest.py`.
- Fixtures específicas de domínio devem ficar na subpasta do domínio.
- Evitar fixture com `scope="session"` quando houver estado mutável.

---

## 12. Riscos Completos

| Risco | Prob | Impacto | Mitigação | Contingência |
|-------|------|---------|-----------|--------------|
| Quebrar funcionalidades | Média | Alto | Testes regressão | Rollback |
| Atraso na entrega | Média | Médio | Buffer 30% | Cortar escopo |
| OpenAI API down | Alta | Crítico | Retry + fallback | Modo degraded |
| Discord API changes | Média | Alto | Adapter pattern | Versionar |
| Performance degradation | Média | Alto | Benchmarks | Reverter |
| Scope creep | Alta | Médio | DoD clara | Rejeitar |
| Knowledge silos | Média | Médio | Pair programming | Docs |
| Technical debt | Alta | Médio | Débito max 5%/sprint | Sprint dedicada |
| Dependências outdated | Baixa | Baixo | Atualização gradual | Pin versão |
| Resistência mudanças | Baixa | Médio | Comunicação | Workshops |

---

## 13. Comunicação

### 13.1 Canais

| Frequência | Tipo | Duração |
|------------|------|---------|
| Diário | Standup async | 5 min |
| Semanal | Sprint review | 30 min |
| Quinzenal | Retrospectiva | 45 min |
| Mensal | Relatório | - |

### 13.2 Reporte de Progresso

- Dashboard de métricas (cobertura, débito, bugs)
- Sprint board atualizado
- Risk log mantido atualizado
