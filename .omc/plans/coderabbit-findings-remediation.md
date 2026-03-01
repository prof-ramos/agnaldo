# Plano de Correcao: CodeRabbit Findings - Agnaldo

**Versao:** 2.0 (Revisado pelo Architect)
**Data:** 01/03/2026
**Status:** Planejamento (Revisado)
**Total de Findings:** 39 - 38 apos remocao

---

## Resumo das Alteracoes (v2.0)

### Alteracoes Criticas aplicadas:
1. **OpenTelemetry (FASE 2.14)** - REMOVIDA - SDK nao instalado, apenas opentelemetry-api
2. **freezegun (FASE 1.3)** - Alterado para usar datetime constante (sem nova dependencia)
3. **Fixture refactoring (FASE 2.8-2.10)** - Especificado padrao de override para valores de retorno
4. **Exception mapping (FASE 1.1)** - Adicionada etapa de verificacao antes da implementacao
5. **datetime.now() (FASE 1.3)** - Movido para PRIORIDADE #1 em FASE 1
6. **PT-BR Scope** - Esclarecido: apenas 3 arquivos mencionados no findings
7. **discord.Interaction import** - Caminho especificado: `from discord import Interaction`
8. **Regression test** - Adicionado teste de regressao para FASE 1.1

---

## Resumo Executivo

Este plano organiza as 38 findings da revisão CodeRabbit em 4 fases de execução, priorizando segurança e bugs antes de questões de qualidade de código e documentação.

### Categorizacao dos Findings

| Categoria | Quantidade | Prioridade |
|-----------|------------|------------|
| **Security/Seguranca** | 2 | Critica |
| **Bugs** | 4 | Alta |
| **Qualidade de Codigo** | 21 | Media |
| **Documentacao** | 8 | Baixa |
| **Refatoracao** | 3 | Baixa |

### Esforco Estimado por Fase

| Fase | Duracao Estimada | Tasks | Complexidade |
|------|------------------|-------|--------------|
| FASE 1: Critical Fixes | 2-3 dias | 6 | Alta |
| FASE 2: Code Quality | 2-3 dias | 21 | Media |
| FASE 3: Documentation | 2-3 dias | 8 | Baixa |
| FASE 4: Refactoring | 2-3 dias | 3 | Media |
| **TOTAL** | **8-12 dias** | **38** | - |

---

## FASE 1: Correcoes Criticas (Security + Bugs)

**Objetivo:** Resolver vulnerabilidades de seguranca e bugs que quebram funcionalidade.

### 1.1 Bug - Teste nao-deterministico com datetime.now() [PRIORIDADE #1]

**Arquivo:** `tests/test_graph_service.py` (linha 215)

**Problema:** Uso de `datetime.now(timezone.utc)` para popular `created_at` torna testes nao-deterministicos e quebra CI.

**Acao Required:**
1. Substituir `datetime.now(timezone.utc)` por constante `FIXED_DATETIME`
2. Definir constante no modulo: `FIXED_DATETIME = datetime(2026, 1, 1, tzinfo=timezone.utc)`
3. NAO adicionar freezegun (nao esta em pyproject.toml)
4. Garantir determinismo nos testes que usam created_at

**Complexidade:** Simples
**Dependencias:** Nenhuma
**Arquivos:**
- `tests/test_graph_service.py`

**Criterio de Aceite:**
- [ ] Teste usa datetime constante `FIXED_DATETIME`
- [ ] Teste e deterministico (reproduzivel)
- [ ] pytest passa consistentemente em CI
- [ ] Nenhuma nova dependencia adicionada

---

### 1.2 Security - Excecao exposta ao usuario (CRITICO)

**Arquivo:** `src/discord/commands.py` (linhas 171-176)

**Problema:** Excecoes brutas sao enviadas ao usuario via `f"Failed to store memory: {e}"`, o que pode expor informacoes sensiveis.

**PASSO 0 - VERIFICACAO OBRIGATORIA:**
1. Verificar se `src/memory/core.py` realmente levanta `DatabaseError` ou `MemoryServiceError`
2. Verificar em `src/exceptions.py` quais excecoes customizadas existem
3. Confirmar que imports sao necessarios

**Acao Required (apos verificacao):**
1. Importar excecoes customizadas de `src.exceptions` (se aplicavel)
2. Criar mapeamento de excecoes para mensagens usuario-friendly em PT-BR
3. Substituir `f"Failed to store memory: {e}"` por mensagem sanitizada
4. Adicionar logging da excecao original para debug
5. **NOVO:** Adicionar teste de regressao para o path de erro

**Complexidade:** Media
**Dependencias:** Verificacao previa do codigo
**Arquivos:**
- `src/discord/commands.py`
- `src/exceptions.py`
- `tests/integration/test_discord/test_handlers.py` (novo teste)

**Criterio de Aceite:**
- [ ] Verificacao: excecoes customizadas sao realmente levantadas
- [ ] Excecoes nao sao mais expostas diretamente aos usuarios
- [ ] Mensagens de erro sao sanitizadas e em PT-BR
- [ ] Excecoes originais sao logadas para debugging
- [ ] **NOVO:** Teste de regressao verifica path de erro
- [ ] **NOVO:** Teste cobre excecao sem exposicao ao usuario

---

### 1.3 Security - Credenciais hardcoded em exemplo (CRITICO)

**Arquivo:** `.claude/agents/mcp-expert.md` (linha 118)

**Problema:** Exemplo de connection string com credenciais hardcoded: `postgresql://user:pass@localhost:5432/db`

**Acao Required:**
1. Adicionar aviso de que exemplo e apenas ilustrativo
2. Mostrar alternativa segura usando variaveis de ambiente
3. Adicionar comentario inline explicando para nunca hardcodar credenciais

**Complexidade:** Simples
**Dependencias:** Nenhuma
**Arquivos:**
- `.claude/agents/mcp-expert.md`

**Criterio de Aceite:**
- [ ] Aviso sobre credenciais hardcoded esta presente
- [ ] Alternativa com variaveis de ambiente e mostrada
- [ ] Comentario inline explica boas praticas

---

### 1.4 Bug - Type hint ausente em handler Discord

**Arquivo:** `src/discord/commands.py` (linhas 231-232)

**Problema:** `chat_command` nao tem type hint para parametro `interaction`.

**Acao Required:**
1. Adicionar type hint `Interaction` ao parametro interaction
2. Adicionar import: `from discord import Interaction` (NAO usar app_commands.Interaction)
3. NOTA: Import atual e `from discord import app_commands` - adicionar linha separada

**Complexidade:** Simples
**Dependencias:** Nenhuma
**Arquivos:**
- `src/discord/commands.py`

**Criterio de Aceite:**
- [ ] Assinatura da funcao tem type hint `Interaction` para interaction
- [ ] Import `from discord import Interaction` esta presente
- [ ] mypy nao reporta erro nesta linha

---

### 1.5 Bug - Inconsistencia em coverage/branch coverage

**Arquivo:** `docs/cleancode-plan.md` (linhas 13-25)

**Problema:** Documentacao menciona `--cov-branch` mas tabela mostra apenas cobertura geral e depois diz "n/d (coletar na Fase 0A)".

**Acao Required:**
1. OU atualizar tabela para incluir branch coverage real
2. OU remover flag `--cov-branch` do comando pytest
3. Remover referencia "branch coverage n/d (coletar na Fase 0A)"

**Complexidade:** Simples
**Dependencias:** Nenhuma
**Arquivos:**
- `docs/cleancode-plan.md`

**Criterio de Aceite:**
- [ ] Comando pytest e tabela sao consistentes
- [ ] Referencia "n/d" foi removida
- [ ] Documentacao esta alinhada com configuracao real

---

### 1.6 Bug - Model downgrade em documentation-engineer

**Arquivo:** `.claude/agents/documentation-engineer.md` (linha 5)

**Problema:** Agent configuration define `model: haiku` que reduz capacidade.

**Acao Required:**
1. Alterar `model: haiku` para `model: sonnet`
2. OU adicionar comentario explicando trade-off se for intencional

**Complexidade:** Simples
**Dependencias:** Nenhuma
**Arquivos:**
- `.claude/agents/documentation-engineer.md`

**Criterio de Aceite:**
- [ ] Model configuration usa sonnet (ou tem justificativa explicita)
- [ ] Comentario de trade-off esta presente se haiku for mantido

---

## FASE 2: Code Quality (Type Hints, Docstrings PT-BR, Formatting)

**Objetivo:** Padronizar qualidade do codigo, traduzir docstrings para PT-BR, corrigir problemas de formatacao.

**NOTA SOBRE ESCOPE PT-BR:** Apenas 3 arquivos sao mencionados no findings originais. Este plano foca nesses 3. Expansao para outros arquivos deve ser tratada em plano separado.

### 2.1 Docstring PT-BR - __getattr__ em knowledge/__init__.py

**Arquivo:** `src/knowledge/__init__.py` (linhas 35-45)

**Acao Required:**
1. Traduzir docstring de __getattr__ para Portugues Brasileiro
2. Manter sentido original sobre lazy load de PDF
3. Preservar referencia a LegalPDFIngestor e get_ingestor

**Complexidade:** Simples
**Arquivos:** `src/knowledge/__init__.py`

**Criterio de Aceite:**
- [ ] Docstring esta em PT-BR
- [ ] Significado sobre lazy load foi preservado
- [ ] Nomes dos simbolos nao foram alterados

---

### 2.2 Docstring PT-BR - serialize_timestamp em schemas/agents.py

**Arquivo:** `src/schemas/agents.py` (linhas 38-41)

**Acao Required:**
1. Traduzir docstring para PT-BR
2. Manter descricao sobre serializacao ISO-8601
3. Preservar uso de value.isoformat()

**Complexidade:** Simples
**Arquivos:** `src/schemas/agents.py`

**Criterio de Aceite:**
- [ ] Docstring esta em PT-BR
- [ ] Descreve serializacao ISO-8601 corretamente
- [ ] Nome do metodo e decorator foram preservados

---

### 2.3 Docstring PT-BR - process_text em discord/handlers.py

**Arquivo:** `src/discord/handlers.py` (linhas 110-119)

**Acao Required:**
1. Traduzir docstring inteira para PT-BR
2. Atualizar cabecalho, secoes "Args" e "Returns"
3. Preservar assinatura e logica da funcao

**Complexidade:** Simples
**Arquivos:** `src/discord/handlers.py`

**Criterio de Aceite:**
- [ ] Docstring esta em PT-BR
- [ ] Estrutura (Args, Returns) foi preservada
- [ ] Assinatura e logica da funcao nao foram alteradas

---

### 2.4 Line Length - Field timestamp muito longo

**Arquivo:** `src/schemas/agents.py` (linha 35)

**Acao Required:**
1. Extrair default factory em funcao helper nomeada
2. OU quebrar linha Field em multiplas linhas
3. Garantir linha dentro do limite de 100 caracteres

**Complexidade:** Simples
**Arquivos:** `src/schemas/agents.py`

**Criterio de Aceite:**
- [ ] Linha esta dentro do limite de 100 caracteres
- [ ] Funcao helper foi criada OU linha foi quebrada
- [ ] Comportamento original foi preservado

---

### 2.5 Trailing Whitespace - video-editor.md

**Arquivo:** `.claude/agents/video-editor.md` (linha 33)

**Acao Required:**
1. Remover espacos extras no final da linha "Multi-format export configurations  "
2. Executar linter/formatter para garantir nenhum outro trailing space

**Complexidade:** Simples
**Arquivos:** `.claude/agents/video-editor.md`

**Criterio de Aceite:**
- [ ] Linha nao tem espacos no final
- [ ] Linter nao reporta trailing whitespace

---

### 2.6 Helper Fixture - assert_has_violation

**Arquivo:** `tests/test_memory_isolation.py` (linhas 125-131)

**Acao Required:**
1. Criar funcao helper assert_has_violation em tests/fixtures
2. Aceitar (violations, operation, resource_type) como parametros
3. Substituir assert any(...) repetido por chamada ao helper

**Complexidade:** Media
**Arquivos:**
- `tests/fixtures/__init__.py` ou novo arquivo
- `tests/test_memory_isolation.py`

**Criterio de Aceite:**
- [ ] Helper assert_has_violation criado em tests/fixtures
- [ ] Testes usam helper em vez de assert any(...) inline
- [ ] Comportamento e identico ao original

---

### 2.7 Type Hints - MockCommandTree methods

**Arquivo:** `tests/conftest.py` (linhas 30-47)

**Acao Required:**
1. Adicionar type hints para command() parameters: name, description
2. Adicionar type hint para decorator e sync
3. Importar Optional, Any, Callable do typing

**Complexidade:** Simples
**Arquivos:** `tests/conftest.py`

**Criterio de Aceite:**
- [ ] Metodos command(), decorator(), sync() tem type hints
- [ ] Imports necessarios foram adicionados
- [ ] Mypy nao reporta erros nestes metodos

---

### 2.8 Structured Return - bot_with_commands fixture

**Arquivo:** `tests/conftest.py` (linhas 122-124)

**Problema CONHECIDO:** Fixture retorna (bot, pool, conn) posicionalmente, mas valores locais tem retornos especificos (fetchval retorna "mock-uuid") enquanto fixtures globais retornam None.

**Acao Required:**
1. Criar `BotTestContext` (NamedTuple ou dataclass) com atributos .bot, .pool, .conn
2. Criar fixture que RETORNA o contexto estruturado
3. **IMPORTANTE:** Preservar configuracao local de mocks (fetchval="mock-uuid")
4. **PADRAO DE OVERRIDE:** Aceitar parametros opcionais para sobrescrever valores de retorno dos mocks
5. Atualizar testes que consomem fixture para usar .bot, .pool, .conn

**Complexidade:** Media
**Arquivos:**
- `tests/conftest.py`
- Testes que usam bot_with_commands

**Criterio de Aceite:**
- [ ] BotTestContext NamedTuple ou dataclass criado
- [ ] Fixture retorna BotTestContext ao inves de tupla
- [ ] **PADRAO:** Fixture aceita override_params para valores especificos
- [ ] Configuracao local (fetchval="mock-uuid") preservada
- [ ] Testes consomem usando atributos (.bot, .pool, .conn)

---

### 2.9 Mock Connection Fixture Reuse

**Arquivo:** `tests/test_graph_service.py` (linhas 89-95)

**Problema CONHECIDO:** Fixture local mock_db_pool tem valores especificos. Reutilizar fixture global pode quebrar testes.

**Acao Required:**
1. **OPCAO A:** Modificar fixture global `mock_db_pool` em conftest.py para aceitar override de valores de retorno
2. **OPCAO B:** Criar fixture factory que aceita parametros de configuracao
3. Atualizar testes para usar fixture reutilizavel com override de valores especificos
4. Remover setup duplicado

**Complexidade:** Media
**Arquivos:**
- `tests/conftest.py` (modificar mock_db_pool)
- `tests/test_graph_service.py` (usar com override)

**Criterio de Aceite:**
- [ ] Fixture mock_db_pool aceita override de valores de retorno
- [ ] Setup duplicado foi removido dos testes locais
- [ ] Testes continuam passando com valores especificos

---

### 2.10 Duplicate Mock Setup Elimination

**Arquivo:** `tests/conftest.py` (linhas 86-101)

**Problema CONHECIDO:** Setup local em bot_with_commands tem valores especificos (fetchval="mock-uuid") que diferem da fixture global.

**Acao Required:**
1. **NAO remover simplesmente** - valores locais sao necessarios
2. Criar fixture parametrizada ou factory que aceita override_params
3. Reutilizar estrutura base de mock_db_pool e mock_db_connection
4. Aplicar override de valores especificos apos injecao
5. Exemplo de padrao:
   ```python
   @pytest_asyncio.fixture
   async def bot_with_commands(override_mock_params=None):
       pool = mock_db_pool()
       conn = extract_conn_from_pool(pool)
       if override_mock_params:
           apply_overrides(conn, override_mock_params)
       # ou
       conn.fetchval.return_value = override_mock_params.get("fetchval", "mock-uuid")
   ```

**Complexidade:** Media
**Arquivos:**
- `tests/conftest.py`

**Criterio de Aceite:**
- [ ] Fixture usa base de mock_db_pool/mock_db_connection
- [ ] Padrao de override documentado e implementado
- [ ] Valores especificos (fetchval="mock-uuid") preservados
- [ ] Fixture continua funcionando

---

### 2.11 Test Coverage Inconsistencia - python-pro.md

**Arquivo:** `.claude/agents/python-pro.md` (linha 207)

**Acao Required:**
1. Alinhar "Pytest coverage > 90%" com "95% test coverage"
2. OU mudar para ">=" se meta for 90%
3. Garantir ambos os textos usam mesmo threshold e operador

**Complexidade:** Simples
**Arquivos:** `.claude/agents/python-pro.md`

**Criterio de Aceite:**
- [ ] Threshold de coverage e consistente entre as duas linhas
- [ ] Operador (>, >=) e claro e correto
- [ ] Mensagem esta alinhada com a meta real

---

### 2.12 Security Examples - mcp-expert.md

**Arquivo:** `.claude/agents/mcp-expert.md` (linhas 91-96)

**Acao Required:**
1. Adicionar exemplos concretos em "3. Security Best Practices"
2. Token rotation: refresh antes de expiry, armazenar refresh em env vars
3. Rate limiting: exponential backoff, limitar requests concurrentes
4. Input validation: schema validation, input sanitization
5. Environment variables: nunca hardcodar credentials
6. Logging: evitar logar dados sensíveis

**Complexidade:** Media
**Arquivos:** `.claude/agents/mcp-expert.md`

**Criterio de Aceite:**
- [ ] Exemplos concretos adicionados para cada bullet
- [ ] Token rotation, rate limiting, validation tem exemplos
- [ ] Notas sobre env vars e logging presentes

---

### 2.13 Broken Numbering - mcp-expert.md Integration Testing

**Arquivo:** `.claude/agents/mcp-expert.md` (linhas 191-196)

**Acao Required:**
1. Corrigir numeracao quebrada na lista
2. Mudar segundo "3." para "5."
3. Mudar "4." para "6."
4. Garantir sequencia 1-6 correta

**Complexidade:** Simples
**Arquivos:** `.claude/agents/mcp-expert.md`

**Criterio de Aceite:**
- [ ] Numeracao esta correta (1, 2, 3, 4, 5, 6)
- [ ] Todos os itens estao presentes

---

### 2.14 CLI Startup Time Contextualizado - cli-developer.md

**Arquivo:** `.claude/agents/cli-developer.md` (linha 16-24)

**Acao Required:**
1. Contextualizar "Startup time < 50ms" para CLIs compiladas (Go/Rust)
2. Adicionar target alternativo para runtimes interpretados: "<200ms for Node.js/Python CLIs"
3. OU tornar item condicional: "<50ms (compiled) / <200ms (interpreted)"

**Complexidade:** Simples
**Arquivos:** `.claude/agents/cli-developer.md`

**Criterio de Aceite:**
- [ ] Startup time distingue entre compiled/interpreted
- [ ] Target para Python/Node.js esta presente
- [ ] Checklist nao e mais absoluto

---

### 2.15 Delivery Notification Metrics - cli-developer.md

**Arquivo:** `.claude/agents/cli-developer.md` (linhas 223-224)

**Acao Required:**
1. Adicionar prefixo "Example delivery notification:"
2. OU substituir numeros por placeholders {command_count}, {startup_time_ms}
3. OU adicionar nota "Metrics shown are illustrative examples"

**Complexidade:** Simples
**Arquivos:** `.claude/agents/cli-developer.md`

**Criterio de Aceite:**
- [ ] Metricas sao explicitamente marcadas como exemplo
- [ ] Leitor sabe que valores nao sao reais

---

### 2.16 Temporal API Stage - typescript-pro.md

**Arquivo:** `.claude/agents/typescript-pro.md` (linhas 107-116)

**Acao Required:**
1. Adicionar nota sobre TC39 stage para "Temporal API types"
2. OU mover para secao "Proposed features"
3. Indicar claramente que e proposal, nao recurso estavel

**Complexidade:** Simples
**Arquivos:** `.claude/agents/typescript-pro.md`

**Criterio de Aceite:**
- [ ] Temporal API types esta marcado como proposal
- [ ] TC39 stage e mencionado
- [ ] Leitores podem distinguir stable vs proposed

---

### 2.17 Backend Description Cleanup - backend-developer.md

**Arquivo:** `.claude/agents/backend-developer.md` (linhas 1-6)

**Acao Required:**
1. Mover exemplos verbosos do description para corpo do documento
2. Substituir description por resumo de uma linha
3. OU usar YAML multi-line block (| ou >)

**Complexidade:** Simples
**Arquivos:** `.claude/agents/backend-developer.md`

**Criterio de Aceite:**
- [ ] Description e concisa (uma linha)
- [ ] Exemplos foram movidos para secao "Usage Examples"
- [ ] Frontmatter e parseavel sem problemas

---

### 2.18 CLI Description Cleanup - cli-developer.md

**Arquivo:** `.claude/agents/cli-developer.md` (linhas 1-6)

**Acao Required:**
1. Mover tres exemplos e tags XML-like do description
2. Criar secao "Examples" ou "Usage Examples" no corpo
3. Limpar tags XML ou converter para Markdown

**Complexidade:** Simples
**Arquivos:** `.claude/agents/cli-developer.md`

**Criterio de Aceite:**
- [ ] Description e uma linha simples
- [ ] Exemplos estao em secao dedicada
- [ ] Frontmatter nao tem XML tags

---

### 2.19 Video-Editor FFmpeg Section - video-editor.md

**Arquivo:** `.claude/agents/video-editor.md` (linhas 1-6)

**Acao Required:**
1. Adicionar secao sobre FFmpeg no corpo
2. Explicar como usar ferramenta anunciada
3. Dar exemplos de comandos FFmpeg comuns
4. Clarificar qual tool entry usar (Bash)

**Complexidade:** Media
**Arquivos:** `.claude/agents/video-editor.md`

**Criterio de Aceite:**
- [ ] Secao FFmpeg ou Tools/FFmpeg existe
- [ ] Exemplos de comandos FFmpeg sao fornecidos
- [ ] Description e corpo sao consistentes

---

### 2.20 Backend Context Query Instructions - backend-developer.md

**Arquivo:** `.claude/agents/backend-developer.md` (linhas 99-114)

**Acao Required:**
1. Apos linha 105, adicionar instrucao clara de como enviar query
2. Especificar request_type "get_backend_context" e requesting_agent "backend-developer"
3. Mostrar tres metodos: CLI, internal API, HTTP POST
4. Explicar fluxo de resposta e tratamento de falhas/retries
5. Documentar tempo maximo de espera

**Complexidade:** Media
**Arquivos:** `.claude/agents/backend-developer.md`

**Criterio de Aceite:**
- [ ] Instrucao de envio de query esta clara
- [ ] Tres metodos sao descritos (CLI, API, HTTP)
- [ ] Tratamento de falhas e timeout sao explicados

---

### 2.21 Backend Integration Fallback Note - backend-developer.md

**Arquivo:** `.claude/agents/backend-developer.md` (linhas 182-220)

**Acao Required:**
1. Adicionar nota antes de "Integration with other agents"
2. Explicar que integracoes assumem ecossistema multi-agent
3. Descrever comportamento fallback se agent estiver indisponível
4. Recomendar coordenacao com time ou ajuste de workflow

**Complexidade:** Simples
**Arquivos:** `.claude/agents/backend-developer.md`

**Criterio de Aceite:**
- [ ] Nota sobre fallback esta presente
- [ ] Comportamento quando agent falta e descrito
- [ ] Nota esta ligada ao heading de integracao

---

## FASE 3: Documentation Improvements

**Objetivo:** Melhorar documentacao de agentes e arquitetura.

### 3.1 Checkpoint Retention Policy

**Arquivo:** `repomix-output.xml` (linhas 93-97) - documentacao

**Problema:** Pasta state/checkpoints armazena indefinidamente.

**Acao Required:**
1. Implementar rotina cleanup (purgeOldCheckpoints ou cleanCheckpoints)
2. Executar no startup e/ou periodicamente
3. Deletar arquivos checkpoint-*.json antigos ou quando count excede max
4. Tornar configuravel via env/config (retentionDays, maxFiles)
5. Loggar deletoes para auditoria

**Complexidade:** Media
**Arquivos:**
- `src/` (modulo apropriado para cleanup)
- `.env.example` (novas vars)

**Criterio de Aceite:**
- [ ] Rotina de cleanup implementada
- [ ] Configuravel via retentionDays e maxFiles
- [ ] Logs de deletao sao auditaveis
- [ ] Executa no startup/periodicamente

---

### 3.2 Consolidar Marcos de Implementacao

**Arquivo:** `repomix-output.xml` (linhas 102-106)

**Problema:** Tres documentos de marco duplicados (IMPLEMENTACAO_COMPLETA.md, MVP_COMPLETE.md, MVP_PHASE_1_COMPLETE.md).

**Acao Required:**
1. Criar CHANGELOG.md com secoes cronologicas (versao/data/descricao)
2. Migrar conteudo relevante dos tres arquivos
3. Remover ou arquivar arquivos individuais
4. Atualizar referencias em prd.json e progress.txt para CHANGELOG.md

**Complexidade:** Media
**Arquivos:**
- `CHANGELOG.md` (novo)
- `IMPLEMENTACAO_COMPLETA.md`, `MVP_COMPLETE.md`, `MVP_PHASE_1_COMPLETE.md` (arquivar)
- `prd.json`, `progress.txt` (atualizar refs)

**Criterio de Aceite:**
- [ ] CHANGELOG.md criado com secoes cronologicas
- [ ] Conteudo dos tres arquivos foi migrado
- [ ] Arquivos antigos foram arquivados ou deletados
- [ ] Referencias foram atualizadas

---

### 3.3 Unificar Test Runners

**Arquivo:** `repomix-output.xml` (linhas 127-131)

**Problema:** Dupla confusao entre scripts/run_tests.py e scripts/run_tests.sh.

**Acao Required:**
1. Escolher abordagem consistente (preferivelmente run_tests.py Python)
2. Deletar runner redundante
3. Atualizar CI/README que invocam nome removido
4. Garantir interface/argumentos sao mantidos

**Complexidade:** Simples
**Arquivos:**
- `scripts/run_tests.py` ou `scripts/run_tests.sh` (deletar um)
- CI configs, README (atualizar referencias)

**Criterio de Aceite:**
- [ ] Apenas um runner de teste existe
- [ ] Referencias foram atualizadas
- [ ] Interface do runner mantida

---

### 3.4 Accessibility Section Expand - cli-ui-designer.md

**Arquivo:** `.claude/agents/cli-ui-designer.md` (linhas 258-262)

**Acao Required:**
1. Expandir "### 4. Accessibility" com exemplos concretos
2. Adicionar exemplos ARIA (aria-label, aria-describedby, role)
3. Listar atalhos de teclado (Tab, Enter, Escape, Arrow keys)
4. Documentar padroes de focus management (trap focus, return focus)
5. Incluir exemplo de skip-link
6. Adicionar checklist com ferramentas de teste (NVDA, JAWS, VoiceOver)

**Complexidade:** Media
**Arquivos:** `.claude/agents/cli-ui-designer.md`

**Criterio de Aceite:**
- [ ] Exemplos ARIA estao presentes
- [ ] Atalhos de teclado sao listados
- [ ] Focus management esta documentado
- [ ] Skip-link example incluido
- [ ] Checklist de ferramentas presente

---

### 3.5 WCAG Contrast Calculation - cli-ui-designer.md

**Arquivo:** `.claude/agents/cli-ui-designer.md` (linhas 46-65)

**Acao Required:**
1. Calcular ratio de contraste WCAG para --text-secondary (#a0a0a0) contra --bg-primary (#0f0f0f)
2. Documentar resultado em comentario perto das :root variables
3. Se ratio < AA, sugerir alternativa acessivel
4. Incluir hex sugerido no comentario

**Complexidade:** Simples
**Arquivos:** `.claude/agents/cli-ui-designer.md`

**Criterio de Aceite:**
- [ ] Ratio de contraste esta documentado
- [ ] Indica se atende AA/AAA
- [ ] Alternativa sugerida se necessario

---

### 3.6 Testing Checklist Expansion - cli-ui-designer.md

**Arquivo:** `.claude/agents/cli-ui-designer.md` (linhas 364-370)

**Acao Required:**
1. Adicionar itens sugeridos ao "3. Testing Checklist"
2. Cross-browser testing (Chrome, Firefox, Safari, Edge)
3. Animation performance validation
4. State management tests (command history, theme persistence)
5. Long-content scroll behavior
6. Copy/paste em code elements
7. Page zoom levels (125%, 150%, 200%)

**Complexidade:** Simples
**Arquivos:** `.claude/agents/cli-ui-designer.md`

**Criterio de Aceite:**
- [ ] Novos itens de checklist estao presentes
- [ ] Formato checkbox mantido
- [ ] Itens sao acionaveis/testaveis

---

### 3.7 Theme Variable Comment - cli-ui-designer.md

**Arquivo:** `.claude/agents/cli-ui-designer.md` (linhas 393-403)

**Acao Required:**
1. Adicionar comentario acima de [data-theme="dark"] e [data-theme="light"]
2. Explicar que sao exemplos simplificados
3. Notar que cada variavel deve ser redefinida para cada tema
4. Referenciar data-theme e lembrar de espelhar lista completa

**Complexidade:** Simples
**Arquivos:** `.claude/agents/cli-ui-designer.md`

**Criterio de Aceite:**
- [ ] Comentario sobre exemplos simplificados esta presente
- [ ] Nota sobre redefinir todas as variaveis
- [ ] Referencia a data-theme esta incluida

---

### 3.8 Unicode Character Fallback - cli-ui-designer.md

**Arquivo:** `.claude/agents/cli-ui-designer.md` (linha 40)

**Acao Required:**
1. Adicionar nota sobre "" (U+23BF) pode nao renderizar
2. Recomendar "└" (U+2514) ou ASCII alternativo (">", "$")
3. Incluir codepoints Unicode (U+23BF, U+2514)
4. Adicionar dica sobre testar suporte de fonte/terminal

**Complexidade:** Simples
**Arquivos:** `.claude/agents/cli-ui-designer.md`

**Criterio de Aceite:**
- [ ] Nota sobre renderizacao esta presente
- [ ] Alternativas sao recomendadas
- [ ] Unicode codepoints sao mencionados

---

## FASE 4: Refactoring Suggestions

**Objetivo:** Abordar padroes de codigo que podem ser melhorados.

### 4.1 CLI Requirements Spec - cli-developer.md

**Arquivo:** `.claude/agents/cli-developer.md` (linhas 126-141)

**Acao Required:**
1. Completar "Communication Protocol" / "CLI Requirements Assessment"
2. Listar todos os request_type suportados ("get_cli_context", etc.)
3. Definir schema de resposta para cada request_type
4. Definir schema de erro (status: "error", error.code, error.message)
5. Adicionar exemplo completo de interacao (request + success + error)

**Complexidade:** Media
**Arquivos:** `.claude/agents/cli-developer.md`

**Criterio de Aceite:**
- [ ] Request_types estao listados
- [ ] Schema de resposta definido
- [ ] Schema de erro definido
- [ ] Exemplo completo de interacao presente

---

### 4.2 Distribution Methods Priority - cli-developer.md

**Arquivo:** `.claude/agents/cli-developer.md` (linhas 36-125)

**Acao Required:**
1. Remover simetria artificial de 8 itens por lista
2. Priorizar completude tecnica sobre formato
3. Adicionar targets faltantes (apt/deb, winget)
4. Consolidar itens menos relevantes
5. Manter formatacao consistente

**Complexidade:** Media
**Arquivos:** `.claude/agents/cli-developer.md`

**Criterio de Aceite:**
- [ ] Listas nao sao forçadas a 8 itens
- [ ] Targets de distribuicao completos estao presentes
- [ ] Items menos relevantes foram consolidados
- [ ] Formatacao e consistente

---

### 4.3 API Paradigm Selection - backend-developer.md

**Arquivo:** `.claude/agents/backend-developer.md` (linhas 18-96)

**Acao Required:**
1. Adicionar secao "API paradigm selection:" antes de "API design requirements:"
2. Listar REST, GraphQL, gRPC, WebSocket com uma linha cada
3. Explicar quando escolher cada paradigma

**Complexidade:** Simples
**Arquivos:** `.claude/agents/backend-developer.md`

**Criterio de Aceite:**
- [ ] Secao "API paradigm selection:" existe
- [ ] Quatro paradigmas sao listados
- [ ] Guidance de escolha esta claro

---

## Estrategia de Verificacao

### Para cada fase, verificar:

1. **Linting**: `uv run ruff check .` retorna 0 issues modificadas
2. **Type Checking**: `uv run mypy src` retorna 0 erros novos
3. **Testes**: `uv run pytest` passa sem regressoes
4. **Formatacao**: `uv run black --check` nao encontra problemas

### Gates de Qualidade:

| Gate | Comando | Criteria |
|------|---------|----------|
| Lint | `uv run ruff check .` | 0 novas issues |
| Type | `uv run mypy src` | 0 novos erros |
| Test | `uv run pytest` | 100% passando |
| Format | `uv run black --check` | 0 diferencas |

---

## Riscos e Dependencias

### Riscos:

| Risco | Mitigação |
|-------|-----------|
| Quebrar funcionalidade existente | Testes de regressão antes de cada mudança |
| Tradução PT-BR perder precisão | Revisar com falante nativo |
| Testes não-determinísticos | Usar datetime constante (FIXED_DATETIME) |
| Fixture override pattern complexo | Documentar padrão claramente |
| Sobrecarga de contexto | Fazer pausas entre fases; code review incremental; commits atômicos |
| Drift entre branches | Fazer rebase/merge frequente da branch principal |

### Dependencias Externas:

- NENHUMA nova dependencia (freezegun nao sera adicionado)
- `uv` para gerenciamento de pacotes

---

## Ordem de Execucao Recomendada

1. **FASE 1.1** (Bug - datetime.now) - Maior prioridade, quebra CI
2. **FASE 1.2** (Security - Excecao) - Passo 0: verificar primeiro
3. **FASE 1.4** (Bug - type hint) - Rapido de corrigir
4. **FASE 1.3** (Security - credenciais) - Importante
5. **FASE 2.4** (Line length) - Pode bloquear outros
6. **FASE 2.1-2.3** (Docstrings PT-BR) - Pode ser feito em paralelo
7. **Restante da FASE 2** - Em ordem de dependencia (2.8-2.10 requerem cuidado com override)
8. **FASE 3** - Documentacao (baixo risco)
9. **FASE 4** - Refatoracao (pode ser adiada)

---

## Checklist Final

### Antes de iniciar:
- [ ] Baseline de testes passando: `uv run pytest`
- [ ] Baseline de lint: `uv run ruff check .`
- [ ] Baseline de type: `uv run mypy src`
- [ ] Backup/branch criado
- [ ] **NOVO:** Verificar se CoreMemory levanta DatabaseError/MemoryServiceError

### Apos cada fase:
- [ ] Testes passam
- [ ] Lint limpo
- [ ] Type check ok
- [ ] Changes commitadas

### Ao final:
- [ ] Todos os 38 findings foram enderecados
- [ ] Documentacao atualizada
- [ ] Code review completo
- [ ] Release notes preparadas

---

## Notas sobre OpenTelemetry (REMOVIDO)

**FASE 2.14 foi removida deste plano porque:**
- Apenas `opentelemetry-api` esta instalado em pyproject.toml
- `opentelemetry.trace.get_tracer` requer SDK implementation
- Adicionar spans sem SDK vai falhar silenciosamente ou causar crash

**Para implementar OpenTelemetry corretamente:**
1. Criar plano separado de feature "Implementar Observabilidade com OpenTelemetry"
2. Adicionar dependencias: `opentelemetry-sdk`, `opentelemetry-instrumentation`
3. Configurar tracer provider e exporters
4. Entao adicionar spans aos handlers

---

**Aprovado por:** _______________
**Data de aprovacao:** _______________
**Versao:** 2.0 (Revisado pelo Architect)
