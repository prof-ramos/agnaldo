# Plano de Ação - CodeRabbit 64 Findings

**Data:** 2026-03-01
**Status:** Planejamento
**Total de Findings:** 64
**Prioridade:** Crítica

---

## Sumário Executivo

| Categoria | Quantidade | Prioridade | Esforço Estimado |
|-----------|------------|------------|------------------|
| **🔴 Críticos** | 13 | Crítica | 2-3 dias |
| **🟡 Código** | 18 | Alta | 2-3 dias |
| **🟢 Nitpicks** | 22 | Média | 1-2 dias |
| **🔤 PT-BR/Docs** | 11 | Baixa | 1-2 dias |
| **TOTAL** | **64** | - | **6-10 dias** |

---

## FASE 0: Preparação Obrigatória

### 0.1 Adicionar `.omc/` ao `.gitignore` [CRÍTICO]

**Arquivo:** `.gitignore`

**Problema:** Arquivos de estado estão sendo versionados injustificadamente.

**Ação:**
```gitignore
# OMC State - Never commit runtime state
.omc/state/
.omc/sessions/*.json
```

**Arquivos afetados:**
- `.omc/state/idle-notif-cooldown.json`
- `.omc/state/hud-state.json`
- `.omc/state/hud-stdin-cache.json`
- `.omc/state/checkpoints/*.json`
- `.omc/state/agent-replay-*.jsonl`
- `.omc/state/last-tool-error.json`
- `.omc/sessions/*.json`

**Comando para limpar:**
```bash
git rm --cached -r .omc/state/ .omc/sessions/*.json
git commit -m "fix: remover arquivos de estado OMC do versionamento"
```

**Criterio de Aceite:**
- [ ] `.omc/state/` adicionado ao `.gitignore`
- [ ] Arquivos removidos do índice git
- [ ] `git status` não mostra mais arquivos de estado

---

## FASE 1: Correções Críticas (Security + Bugs)

### 1.1 Timestamps Zerados em Replay Files [CRÍTICO]

**Arquivos:**
- `.omc/state/agent-replay-0396780a-373e-4cd4-899b-bcae24910632.jsonl`
- `.omc/state/agent-replay-381fb17f-051c-4997-a1a6-5c9b4c5f3ba8.jsonl`

**Problema:** Todos os timestamps `t=0` e `agent_type="unknown"`

**Ação:**
1. Corrigir rotina que grava eventos para preencher `t` com timestamps reais
2. Garantir `agent_type` seja classificado corretamente
3. Adicionar validação antes de persistir

**Complexidade:** Alta

**Criterio de Aceite:**
- [ ] Eventos são gravados com `t != 0`
- [ ] `agent_type` != "unknown"
- [ ] Validação em lugar antes da gravação

---

### 1.2 Model Loading Bloqueante [CRÍTICO]

**Arquivo:** `src/main.py:192`

**Problema:** `IntentClassifier` carrega modelo bloqueando o event loop

**Ação:**
```python
# ANTES (bloqueante):
intent_classifier = IntentClassifier(model_name=settings.SENTENCE_TRANSFORMER_MODEL)

# DEPOIS (async):
loop = asyncio.get_running_loop()
intent_classifier = await loop.run_in_executor(
    None,  # default executor
    lambda: IntentClassifier(model_name=settings.SENTENCE_TRANSFORMER_MODEL)
)
```

**Complexidade:** Média

**Criterio de Aceite:**
- [ ] Model loading não bloqueia o event loop
- [ ] Startup permanece responsivo
- [ ] Teste de integração passa

---

### 1.3 Dados Sensíveis em Cache [CRÍTICO]

**Arquivo:** `.omc/state/hud-stdin-cache.json`

**Problema:** Contém `user_path`, `session_id`, `transcript_path`

**Ação:**
1. Remover do versionamento (já coberto na FASE 0.1)
2. Adicionar sanitização para não gravar paths absolutos
3. Usar paths relativos ou hashes

**Complexidade:** Média

---

### 1.4 Orphan Agent Events [CRÍTICO]

**Arquivo:** `.omc/state/agent-replay-*.jsonl`

**Problema:** Eventos `agent_stop` sem `agent_start` correspondente (ex: `a3cee34`)

**Ação:**
1. Adicionar validação no pipeline de processamento
2. Criar mapa de `agent_start` vistos
3. Para `agent_stop` órfão: emitir warning + synthetic start OU skip

**Complexidade:** Alta

---

### 1.5 Credenciais Hardcoded em Exemplo

**Arquivo:** `.claude/agents/mcp-expert.md:118`

**Ação:**
1. Remover `#` inline do JSON (inválido)
2. Substituir `postgresql://user:pass@localhost:5432/db` por placeholder
3. Adicionar warning fora do JSON

**Antes:**
```json
"DATABASE_URL": "postgresql://user:pass@localhost:5432/db" # never hardcode
```

**Depois:**
```json
"DATABASE_URL": "${DATABASE_URL}"
```

> **⚠️ NEVER hardcode credentials** - Use environment variables

**Complexidade:** Simples

---

### 1.6 Token Placeholder Muito Realista

**Arquivo:** `.claude/agents/mcp-expert.md:139`

**Ação:**
- `"GITHUB_TOKEN": "ghp_your_token_here"` → `"GITHUB_TOKEN": ""` ou `"GITHUB_TOKEN_PLACEHOLDER"`

**Complexidade:** Simples

---

### 1.7 Security Best Practices em Inglês

**Arquivo:** `.claude/agents/mcp-expert.md:91-96`

**Ação:** Traduzir bullets para inglês:
- "nunca hardcode credenciais" → "never hardcode credentials"
- "refresh antes de expiry" → "refresh before expiry"
- "armazenar refresh tokens em env vars" → "store refresh tokens in environment variables"
- "limitar requests concorrentes" → "limit concurrent requests"

**Complexidade:** Simples

---

### 1.8 Try/Except Silencioso em Teste

**Arquivo:** `tests/integration/test_discord/test_handlers.py:776`

**Ação:**
```python
# ANTES (inseguro):
try:
    memory_add_cmd.callback(...)
except:
    pass

# DEPOIS (seguro):
with pytest.raises(DatabaseError):
    memory_add_cmd.callback(...)
```

**Complexidade:** Simples

---

### 1.9 Bare try/except Sem Assert

**Arquivo:** `tests/integration/test_discord/test_handlers.py:788`

**Ação:**
```python
# Adicionar antes de extrair error_message:
assert mock_interaction.response.send_message.called
error_message = mock_interaction.response.send_message.call_args[0][0]
```

**Complexidade:** Simples

---

### 1.10 Mock Tree Walk Commands Bug

**Arquivo:** `tests/integration/test_discord/test_handlers.py:765`

**Problema:** `MagicMock` retorna outro `MagicMock`, nunca itera comandos reais

**Ação:**
```python
# Criar mocks explícitos:
mock_memory_group = MagicMock()
mock_memory_group.name = "memory"
mock_memory_add = MagicMock()
mock_memory_add.name = "add"
mock_memory_group.walk_commands.return_value = [mock_memory_add]
mock_bot.tree.walk_commands.return_value = [mock_memory_group]
```

**Complexidade:** Média

---

### 1.11 Duplicated Error Message

**Arquivo:** `.omc/state/last-tool-error.json:4`

**Problema:** Campo `"error"` recebe mesma mensagem duas vezes

**Ação:**
1. Localizar rotina que escreve estado
2. Normalizar e deduplicar linhas antes de gravar
3. Validar que não há concatenação duplicada

**Complexidade:** Média

---

### 1.12 Threshold de Cobertura Inconsistente

**Arquivo:** `.claude/agents/python-pro.md:207`

**Problema:** "≥ 90%" vs "95% test coverage"

**Ação:** Escolher um threshold e aplicar em ambos:
- Opção A: Ambos → `≥ 95%`
- Opção B: Ambos → `≥ 90%` + justificativa

**Complexidade:** Simples

---

### 1.13 Absolute Type Safety Claim

**Arquivo:** `.claude/agents/typescript-pro.md:215`

**Problema:** "Zero runtime type errors possible" é excessivamente absoluto

**Ação:**
```markdown
"Compile-time type safety maximized; runtime type errors may still occur from
external data, user input, type assertions, or untyped libraries."
```

**Complexidade:** Simples

---

## FASE 2: Qualidade de Código

### 2.1 Função Helper no Escopo da Classe

**Arquivo:** `src/schemas/agents.py:36-43`

**Problema:** `_get_utc_now` definido dentro da classe (não é método)

**Ação:**
```python
# MOVER para escopo de módulo (fora da classe):
def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class AgentMessage(BaseModel):
    timestamp: datetime = Field(default_factory=_get_utc_now)
```

**Complexidade:** Simples

---

### 2.2 __getattr__ sem Cache

**Arquivo:** `src/knowledge/__init__.py:35-49`

**Problema:** Recria exports dict e re-importa a cada acesso

**Ação:**
```python
def __getattr__(name: str):
    if name in ("LegalPDFIngestor", "get_ingestor"):
        # Importar uma vez e cache em globals
        from .pdf import LegalPDFIngestor, get_ingestor
        globals()["LegalPDFIngestor"] = LegalPDFIngestor
        globals()["get_ingestor"] = get_ingestor
    return globals().get(name, _UNSENT)
```

**Complexidade:** Média

---

### 2.3 Accessos KeyError sem Defensiva

**Arquivo:** `tests/fixtures/__init__.py:75-81`

**Problema:** `v["operation"]` pode levantar `KeyError`

**Ação:**
```python
# ANTES:
assert any(v["operation"] == "create" for v in result)

# DEPOIS:
assert any(v.get("operation") == "create" for v in result)
```

**Complexidade:** Simples

---

### 2.4 Import Awaitable Não Utilizado

**Arquivo:** `tests/conftest.py:7`

**Ação:**
```python
# REMOVER Awaitable se não usado:
from collections.abc import Callable, Generator  # Awaitable removido
```

**Complexidade:** Simples

---

### 2.5 add_command Pode Inserir Duplicatas

**Arquivo:** `tests/conftest.py:67-84`

**Problema:** Insere mesmo comando com `.name` e `.qualified_name`

**Ação:**
```python
def add_command(self, cmd):
    self._commands[cmd.name] = cmd
    if cmd.qualified_name and cmd.qualified_name != cmd.name:
        self._commands[cmd.qualified_name] = cmd
```

**Complexidade:** Simples

---

### 2.6 Setup Duplicado de mock_db_pool

**Arquivo:** `tests/conftest.py:108-123`

**Ação:**
1. Criar fixture reutilizável com parâmetros de override
2. Remover setup duplicado
3. Usar `pytest.param` para valores específicos

**Complexidade:** Média

---

### 2.7 Import MemoryServiceError Não Utilizado

**Arquivo:** `tests/integration/test_discord/test_handlers.py:14`

**Ação:** Remover da lista de imports

**Complexidade:** Simples

---

### 2.8 Import Duplicado datetime/timezone

**Arquivo:** `tests/e2e/test_discord_commands.py:88`

**Ação:** Remover segunda importação

**Complexidade:** Simples

---

### 2.9 Imports Duplicados em Bloco

**Arquivo:** `tests/integration/test_discord/test_handlers.py:734`

**Ação:** Remover bloco duplicado de `AsyncMock, MagicMock, patch, setup_commands, DatabaseError`

**Complexidade:** Simples

---

### 2.10 Fixture com Variável Não Utilizada

**Arquivo:** `tests/test_graph_service.py:92-98`

**Problema:** `acquire_cm` criado mas não usado

**Ação:**
```python
# OU usar corretamente:
acquire_cm = asyncio.asynccontextmanager()
pool.acquire.return_value = acquire_cm
acquire_cm.__aenter__.return_value = conn

# OU remover e atribuir diretamente:
pool.acquire.return_value.__aenter__.return_value = conn
```

**Complexidade:** Simples

---

### 2.11 Teste Local Mock vs Fixtures Compartilhadas

**Arquivo:** `tests/integration/test_discord/test_handlers.py:728`

**Ação:**
1. Migrar para usar `mock_bot` e `mock_db_pool` fixtures
2. Criar `mock_interaction` fixture se não existir
3. Remover setup local duplicado

**Complexidade:** Média

---

### 2.12-2.18 Imports Não Utilizados em E2E

**Arquivo:** `tests/e2e/test_discord_commands.py:54-56`

**Ação:** Remover `mock_conn = ctx.conn` ou usar `_ = ctx.conn`

**Complexidade:** Simples

---

### 2.19 Fixture Pattern Repetido

**Arquivo:** `tests/e2e/test_discord_commands.py:24-26`

**Ação:**
```python
# Criar fixture reutilizável:
@pytest.fixture
def bot_context(bot_with_commands):
    ctx = bot_with_commands
    return ctx.bot, ctx.conn

# Usar nos testes:
def test_something(bot_context):
    bot, mock_conn = bot_context
```

**Complexidade:** Média

---

### 2.20 Compose OpenTelemetry Spans

**Arquivo:** `src/main.py:184-199`

**Nota:** **BLOQUEADO** - Apenas `opentelemetry-api` instalado, sem SDK

**Ação:** Criar plano separado "Implementar Observabilidade OpenTelemetry" com:
1. Adicionar `opentelemetry-sdk`
2. Configurar tracer provider
3. Adicionar spans

**Complexidade:** Alta (requer novo plano)

---

### 2.21 Retry Pattern em Message Handler

**Arquivo:** `src/main.py:187-198`

**Ação:**
```python
from tenacity import stop_after_attempt, wait_exponential, retry_if_exception_type

async def initialize_message_handler(settings):
    loop = asyncio.get_running_loop()
    intent_classifier = await loop.run_in_executor(
        None,
        lambda: IntentClassifier(model_name=settings.SENTENCE_TRANSFORMER_MODEL)
    )
    return await get_message_handler(intent_classifier)
```

**Complexidade:** Média

---

## FASE 3: Nitpicks e Formatação

### 3.1 Newlines Finais em JSON

**Arquivos:**
- `.omc/sessions/0396780a-373e-4cd4-899b-bcae24910632.json`
- `.omc/sessions/381fb17f-051c-4997-a1a6-5c9b4c5f3ba8.json`
- `.omc/state/checkpoints/checkpoint-2026-03-01T05-49-03-659Z.json`

**Ação:** Adicionar `\n` ao final de cada arquivo

**Complexidade:** Simples

---

### 3.2 Newline Final em MDs

**Arquivos:**
- `.claude/agents/documentation-engineer.md:276`
- `.claude/agents/python-pro.md:277`

**Ação:** Adicionar newline ao final

**Complexidade:** Simples

---

### 3.3 Timestamp de Session Start

**Arquivo:** `.omc/sessions/381fb17f-051c-4997-a1a6-5c9b4c5f3ba8.json`

**Ação:** Adicionar campo `"started_at"` ao lado de `"ended_at"`

**Complexidade:** Simples

---

### 3.4 Repomix Tracking State Files

**Arquivo:** `repomix-output.xml:93-106`

**Ação:** Adicionar ao `.gitignore`:
```gitignore
# State files in repomix output
state/checkpoints/*.json
agent-replay-*.jsonl
```

**Complexidade:** Simples

---

### 3.5 CHANGELOG Data Placeholder

**Arquivo:** `CHANGELOG.md:83`

**Ação:** `2025-XX-XX` → `2026-03-01` ou data real do release

**Complexidade:** Simples

---

### 3.6 YAML Block Scalar para Descriptions

**Arquivos:**
- `.claude/agents/typescript-pro.md:1-6`
- `.claude/agents/cli-developer.md:3`

**Ação:** Converter `\n` literais para block scalar `|` ou `>`

**Complexidade:** Simples

---

### 3.7 Const Type Parameters em Typescript

**Arquivo:** `.claude/agents/typescript-pro.md:27-36`

**Ação:** Adicionar aos "Advanced type patterns":
```markdown
- Const type parameters for preserving literal types in generics (TS 5.0+)
  Example: `function myFunc<const T>(arr: T[])`
```

**Complexidade:** Simples

---

### 3.8 CLI Capitalização Inconsistente

**Arquivo:** `.claude/agents/cli-developer.md:118-119`

**Ação:** Padronizar:
- "NPM global packages" ✓
- "NPM tarball distribution" ✓

**Complexidade:** Simples

---

### 3.9 Video-Editor Cut/Trim Docs

**Arquivo:** `.claude/agents/video-editor.md:31`

**Ação:** Documentar duas abordagens:
1. Rápido: `-ss 00:01:00 -i input.mp4 -t 00:01:00 -c copy`
2. Preciso: `-i input.mp4 -ss 00:01:00 -to 00:02:00 -c copy`

Nota: Primeiro é mais rápido mas pode perder precisão

**Complexidade:** Simples

---

### 3.10 CRF Levels Expandidos

**Arquivo:** `.claude/agents/video-editor.md:35`

**Ação:**
```markdown
- CRF 18-20: Visually lossless/very high quality (large files) - use for masters
- CRF 23: Recommended default (good balance)
- CRF 26-28: Lower quality/smaller files - use for low-bandwidth/preview
```

**Complexidade:** Simples

---

### 3.11 CLI-UI Unicode ⎿ Fallback

**Arquivo:** `.claude/agents/cli-ui-designer.md:41-45`

**Ação:** Adicionar nota sobre `⎿` (U+23BF) pode não renderizar, recomendar `└` (U+2514), `>`, ou `$`

**Complexidade:** Simples

---

### 3.12 CLI-UI Theme Variables Expanded

**Arquivo:** `.claude/agents/cli-ui-designer.md:453-468`

**Ação:** Adicionar `<details>` block com exemplo completo de variáveis por tema

**Complexidade:** Simples

---

### 3.13 CLI-UI Delivery Metrics

**Arquivo:** `.claude/agents/cli-developer.md:223-224`

**Ação:** Adicionar prefixo "Example delivery notification:" ou placeholders

**Complexidade:** Simples

---

### 3.14 CLI Startup Time Contextualizado

**Arquivo:** `.claude/agents/cli-developer.md:16-24`

**Ação:** Mudar para `<50ms (compiled) / <200ms (interpreted)`

**Complexidade:** Simples

---

### 3.15 Temporal API TC39 Stage

**Arquivo:** `.claude/agents/typescript-pro.md:107-116`

**Ação:** Marcar como proposal, não recurso estável

**Complexidade:** Simples

---

### 3.16 Backend Description Cleanup

**Arquivo:** `.claude/agents/backend-developer.md:1-6`

**Ação:** Mover exemplos verbosos para corpo do documento

**Complexidade:** Simples

---

### 3.17 CLI Description Cleanup

**Arquivo:** `.claude/agents/cli-developer.md:1-6`

**Ação:** Mover três exemplos para seção "Usage Examples"

**Complexidade:** Simples

---

### 3.18 Video-Editor FFmpeg Section

**Arquivo:** `.claude/agents/video-editor.md:1-6`

**Ação:** Adicionar seção sobre FFmpeg no corpo

**Complexidade:** Média

---

## FASE 4: Ortografia e Documentação (PT-BR)

### 4.1 Open-Questions Diacritics

**Arquivo:** `.omc/plans/open-questions.md:1-5`

**Correções:**
- `rastreja` → `rastreia`
- `nao` → `não`
- `decisoes` → `decisões`
- `execucao` → `execução`

**Complexidade:** Simples

---

### 4.2 Open-Questions "já está"

**Arquivo:** `.omc/plans/open-questions.md:7-17`

**Ação:** `ja esta` → `já está` (2 ocorrências)

**Complexidade:** Simples

---

### 4.3 Open-Questions Pendentes

**Arquivo:** `.omc/plans/open-questions.md:19-31`

**Correções:**
- `disponiveis` → `disponíveis`
- `e a meta` → `é a meta`
- `Qual e` / `E qual e` → `Qual é` / `E qual é`

**Complexidade:** Simples

---

### 4.4 Open-Questions Seções Adicionais

**Arquivo:** `.omc/plans/open-questions.md:32-53`

**Correções:**
- `precisao` → `precisão`
- `tecnica` → `técnica`
- `excecoes` → `exceções`
- `atualiza-los` → `atualizá-los`
- `priorizacao esta` → `priorização está`

**Complexidade:** Simples

---

### 4.5 CHANGELOG Mixed PT/EN

**Arquivo:** `CHANGELOG.md:10-22`

**Ação:** Padronizar para inglês:
- "Type hints para todos os comandos" → "Type hints for all Discord commands"
- "FIXED_DATETIME constante" → "FIXED_DATETIME constant"

**Complexidade:** Média

---

### 4.6 Coderabbit Remediation "Acao Required"

**Arquivo:** `.omc/plans/coderabbit-findings-remediation.md:60`

**Ação:**
- `Acao Required` → `Ação Requerida`
- `apos` → `após`
- `revisao` → `revisão`
- `seguranca` → `segurança`
- `Categorizacao` → `Categorização`

**Complexidade:** Simples

---

### 4.7 Coderabbit Remediation Test Gate

**Arquivo:** `.omc/plans/coderabbit-findings-remediation.md:902-914`

**Ação:** Consistir "uv run pytest passa sem regressões" vs "100% passando"

**Complexidade:** Simples

---

### 4.8 Coderabbit Remediation Missing 2.14

**Arquivo:** `.omc/plans/coderabbit-findings-remediation.md:13`

**Ação:** Renumerar itens 2.15-2.21 para 2.14-2.20 OU atualizar tabela de 21→20

**Complexidade:** Simples

---

### 4.9 Coderabbit Remediation Riscos Table

**Arquivo:** `.omc/plans/coderabbit-findings-remediation.md:920-927`

**Ação:** Adicionar linhas:
| Risco | Mitigação |
|-------|-----------|
| Sobrecarga de contexto | Fazer pausas entre fases; code review incremental; commits atômicos |
| Drift entre branches | Fazer rebase/merge frequente da branch principal |

**Complexidade:** Simples

---

### 4.10 Coderabbit Remediation 3.1 Docs vs Implementation

**Arquivo:** `.omc/plans/coderabbit-findings-remediation.md:648-671`

**Ação:** Mover implementação de `purgeOldCheckpoints` para fase de implementação (não docs)

**Complexidade:** Média

---

### 4.11 Discord-Async-Command-Test Description

**Arquivo:** `.omc/skills/discord-async-command-test/SKILL.md:1-12`

**Ação:** `description: "Teste de comandos..."` → `description: "Testes de comandos..."`

**Complexidade:** Simples

---

### 4.12 Discord-Async-Command-Test Discordslash

**Arquivo:** `.omc/skills/discord-async-command-test/SKILL.md:38`

**Ação:** `Discordslash` → `Discord slash`

**Complexidade:** Simples

---

## Ordem de Execução Recomendada

### PASSO 1: Preparação (30 min)
1. ✅ FASE 0.1 - Adicionar `.omc/` ao `.gitignore`
2. ✅ Limpar arquivos do índice git

### PASSO 2: Críticos (2-3 dias)
1. FASE 1.2 - Model loading bloqueante
2. FASE 1.1 - Timestamps zerados em replay
3. FASE 1.3 - Dados sensíveis em cache
4. FASE 1.4 - Orphan agent events
5. FASE 1.5-1.7 - Security (credenciais)
6. FASE 1.8-1.10 - Testes seguros
7. FASE 1.11-1.13 - Outros críticos

### PASSO 3: Código (2-3 dias)
1. FASE 2.1-2.3 - Fixes simples de código
2. FASE 2.4-2.9 - Imports e cleanup
3. FASE 2.10-2.21 - Refatoração média

### PASSO 4: Nitpicks (1-2 dias)
1. FASE 3.1-3.6 - Newlines e formatting
2. FASE 3.7-3.18 - Docs e melhorias

### PASSO 5: PT-BR/Docs (1-2 dias)
1. FASE 4.1-4.12 - Ortografia e documentação

---

## Gates de Qualidade

| Gate | Comando | Criteria |
|------|---------|----------|
| Lint | `uv run ruff check .` | 0 novas issues |
| Type | `uv run mypy src` | 0 novos erros |
| Test | `uv run pytest` | 100% passando |
| Format | `uv run black --check` | 0 diferenças |

---

## Checklist Antes de Iniciar

- [ ] Branch criada: `fix/coderabbit-64-findings`
- [ ] Baseline de testes: `uv run pytest` (salvar output)
- [ ] Baseline de lint: `uv run ruff check .` (salvar output)
- [ ] Baseline de type: `uv run mypy src` (salvar output)

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Quebrar funcionalidade | Testes de regressão antes de cada mudança |
| State files voltarem ao commit | Verificar `.gitignore` após merge |
| Replay timestamps quebrarem logs | Validação rigorosa antes de deploy |
| Model loading async causar race condition | Testar startup concorrente |

---

## Notas Especiais

### OpenTelemetry (FASE 2.20)
**BLOQUEADO** - Requer feature plan separado:
1. Adicionar `opentelemetry-sdk` e `opentelemetry-instrumentation`
2. Configurar tracer provider e exporters
3. Implementar spans em handlers críticos

### State Files
Todos os arquivos em `.omc/state/` devem ser gerados em runtime, nunca commitados.

---

**Aprovado por:** _______________
**Data de aprovação:** _______________
**Versão:** 1.0
