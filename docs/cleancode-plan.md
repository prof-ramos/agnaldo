# Plano de Implementação: Clean Code e Boas Práticas - Agnaldo

**Versão:** 1.0
**Data:** 28/02/2026
**Status:** Planejamento

---

## 1. Análise do Estado Atual

### 1.1 Métricas Atuais

| Métrica | Valor | Meta |
|---------|-------|------|
| Linhas de código | ~21.700 | - |
| Arquivos Python | ~50 | - |
| Cobertura de testes | ~15% (estimado) | 80% |
| Débito técnico | Médio | Baixo |
| Documentação | Parcial | Completa |

### 1.2 Pontos Fortes

- ✅ Estrutura de módulos bem organizada (`src/`, `tests/`, `docs/`)
- ✅ Type hints em boa parte do código
- ✅ Sistema de isolamento de memória implementado
- ✅ GraphService com extração automática
- ✅ Documentação técnica (PRD.md, ARCHITECTURE.md, CLAUDE.md)
- ✅ pyproject.toml com dependências organizadas
- ✅ Ferramentas de dev configuradas (pytest, black, ruff, mypy)

### 1.3 Pontos a Melhorar

- 🔴 Cobertura de testes baixa (~15%)
- 🔴 Falta de testes de integração
- 🟠 Alguns métodos longos (>50 linhas)
- 🟠 Código duplicado em handlers
- 🟠 Falta de retry/tenacity em operações críticas
- 🟡 Docstrings inconsistentes
- 🟡 Logging sem estrutura padronizada
- 🟡 Falta de métricas e observabilidade

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

---

## 3. Fases de Implementação

### FASE 0: Setup (Semana 0) - OBRIGATÓRIA

**Objetivo:** Preparar ambiente e critérios antes de começar

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 0.1 | Definir Definition of Done | 🔴 Crítica | 2h | - |
| 0.2 | Configurar SonarQube/CodeClimate | 🔴 Crítica | 2h | - |
| 0.3 | Criar Makefile com comandos comuns | 🟠 Média | 1h | - |
| 0.4 | Setup canais de comunicação | 🟠 Média | 1h | - |
| 0.5 | Mapear riscos completos | 🔴 Crítica | 2h | - |
| 0.6 | Definir SLIs/SLOs | 🟠 Média | 2h | - |

**Entregáveis:**
- [ ] Definition of Done documentada
- [ ] SonarQube/CodeClimate configurado
- [ ] Makefile funcional
- [ ] Risk log completo
- [ ] SLIs/SLOs definidos

### FASE 1: Fundação (Semana 1-2)

**Objetivo:** Estabelecer base de qualidade

#### Semana 1: Configuração e Análise

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 1.1 | Configurar pre-commit hooks | 🔴 Alta | 2h | - |
| 1.2 | Configurar ruff com regras estritas | 🔴 Alta | 1h | - |
| 1.3 | Configurar mypy strict mode | 🔴 Alta | 2h | - |
| 1.4 | Executar análise estática completa | 🔴 Alta | 2h | - |
| 1.5 | Mapear code smells existentes | 🟠 Média | 4h | - |
| 1.6 | Criar checklist de code review | 🟠 Média | 1h | - |

**Entregáveis:**
- [ ] `.pre-commit-config.yaml` configurado
- [ ] `ruff.toml` com regras customizadas
- [ ] Relatório de análise estática
- [ ] Checklist de code review

#### Semana 2: Estrutura Base

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 2.1 | Criar `src/base/` com classes base | 🔴 Alta | 4h | - |
| 2.2 | Implementar logging estruturado | 🔴 Alta | 3h | - |
| 2.3 | Criar decoradores utilitários | 🟠 Média | 2h | - |
| 2.4 | Padronizar exceções customizadas | 🟠 Média | 2h | - |
| 2.5 | Implementar retry com tenacity | 🟠 Média | 2h | - |
| 2.6 | Criar fixtures de teste base | 🟠 Média | 3h | - |

**Entregáveis:**
- [ ] Módulo `src/base/` com:
  - `logging.py` - Logger estruturado
  - `exceptions.py` - Exceções padronizadas
  - `decorators.py` - Decoradores úteis
  - `retry.py` - Configuração de retry
- [ ] `tests/conftest.py` com fixtures

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

**Objetivo:** Atingir 80% de cobertura

#### Semana 5: Testes Unitários

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 5.1 | Testes para `src/memory/` | 🔴 Alta | 8h | - |
| 5.2 | Testes para `src/knowledge/` | 🔴 Alta | 6h | - |
| 5.3 | Testes para `src/agents/` | 🔴 Alta | 6h | - |
| 5.4 | Testes para `src/discord/` | 🟠 Média | 4h | - |
| 5.5 | Testes para `src/intent/` | 🟠 Média | 4h | - |
| 5.6 | Configurar pytest-cov | 🔴 Alta | 1h | - |

**Meta de cobertura por módulo:**

| Módulo | Cobertura Atual | Meta |
|--------|-----------------|------|
| `memory/` | ~20% | 90% |
| `knowledge/` | ~10% | 85% |
| `agents/` | ~5% | 80% |
| `discord/` | ~10% | 75% |
| `intent/` | ~15% | 80% |

#### Semana 6: Testes de Integração

| # | Tarefa | Prioridade | Estimativa | Responsável |
|---|--------|------------|------------|-------------|
| 6.1 | Criar suite de testes de integração | 🔴 Alta | 4h | - |
| 6.2 | Testes de fluxo de memória end-to-end | 🔴 Alta | 4h | - |
| 6.3 | Testes de integração Discord | 🟠 Média | 4h | - |
| 6.4 | Testes de banco de dados | 🟠 Média | 3h | - |
| 6.5 | Configurar CI/CD para testes | 🔴 Alta | 2h | - |
| 6.6 | Adicionar testes de mutação (mutmut) | 🟡 Baixa | 2h | - |

**Entregáveis:**
- [ ] Cobertura de testes >= 80%
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
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-asyncpg]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

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

---

## 6. Métricas de Sucesso

### 6.1 KPIs Técnicos

| KPI | Baseline | Meta FASE 3 | Meta Final | Como Medir |
|-----|----------|-------------|------------|------------|
| Cobertura de testes | ~15% | 60% | 80% | pytest-cov |
| Branch coverage | ~10% | 50% | 70% | pytest-cov |
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

1. [ ] **Revisar e aprovar Definition of Done** (Seção 10)
2. [ ] **Configurar SonarQube ou CodeClimate**
3. [ ] Executar análise estática inicial (baseline)
4. [ ] Instalar pre-commit hooks: `pre-commit install`
5. [ ] Criar Makefile com comandos comuns

### Curto Prazo (Próximas 2 semanas - FASE 0 + FASE 1)

1. [ ] Completar FASE 0 (Setup)
2. [ ] Implementar logging estruturado
3. [ ] Criar suite de testes base
4. [ ] Configurar CI/CD com SonarQube
5. [ ] Mapear riscos completos

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
- [ ] Riscos completos mapeados
- [ ] Pirâmide de testes definida
- [ ] SLIs/SLOs acordados
- [ ] Recursos alocados
- [ ] Comunicação configurada

---

## 9. Referências

- [Clean Code - Robert C. Martin](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [The Pragmatic Programmer - Andrew Hunt & David Thomas](https://pragprog.com/titles/tpp20/)
- [Refactoring - Martin Fowler](https://refactoring.com/)
- [Python Clean Code Guide](https://github.com/zedr/clean-code-python)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

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
- [ ] Testes rodam em < 5 segundos (unitários)

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

### 10.5 Qualidade

- [ ] Sem regressões conhecidas
- [ ] Performance não degradada
- [ ] Security scan passa (bandit)
- [ ] Complexidade ciclomática < 10

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
