# Prompts e Personalidade

## `SOUL.md` (raiz do repo)

O arquivo `SOUL.md` na raiz define a personalidade do Agnaldo (tom de voz, limites e preferencias). Ele e carregado no startup (ver `src/main.py`) e anexado ao bot como `bot.personality`.

No modo conversacional, essa personalidade e repassada ao orquestrador e vira parte do "system prompt" (ver `src/discord/handlers.py` e `src/agents/orchestrator.py`).

## Como o prompt e montado

No processamento de mensagens (Agno):

1. `AgnoAgent` recebe `instructions` (lista de strings).
2. O system prompt e composto por instrucoes base (inclui `SOUL.md` quando fornecido), instrucoes especificas do agente (conversacional, knowledge, memory, graph) e contexto de memoria (ex: resultados de recall).
3. A chamada ao modelo ocorre via OpenAI `chat.completions` (ver `src/agents/orchestrator.py`).

## Templates de prompts (OpenClaw)

Em `src/templates/` existem arquivos para bootstrap de um workspace orientado a prompts/arquivos:

- `src/templates/SOUL.md`: filosofia e personalidade (template).
- `src/templates/USER.md`: perfil do usuario.
- `src/templates/IDENTITY.md`: identidade do agente.
- `src/templates/TOOLS.md`: notas locais e integracoes.
- `src/templates/AGENTS.md`: manual operacional.
- `src/templates/MEMORY.md`: memoria curada.
- `src/templates/HEARTBEAT.md`: checklists de heartbeat.

Esses templates sao uteis para padronizar a operacao e reduzir drift de comportamento.

## Onde editar o comportamento

- Tom de voz e limites: `SOUL.md` (raiz).
- Roteamento por intent: `src/intent/classifier.py` e `src/intent/models.py`.
- Instrucoes por agente: `src/agents/orchestrator.py` em `_create_agents()`.
- Temperature, max_tokens: `src/agents/orchestrator.py` em `AgnoAgent.process()`.
