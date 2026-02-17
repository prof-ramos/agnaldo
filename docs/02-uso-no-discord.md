# Uso no Discord

## Como o bot funciona (alto nível)

- O bot usa `discord.py` (ver `src/discord/bot.py`).
- Comandos são slash commands registrados em `src/discord/commands.py`.
- Existe um pipeline conversacional multi-agente (Agno) em `src/agents/orchestrator.py`, consumido por `src/discord/handlers.py`.

## Slash commands disponíveis

Comandos básicos:

- `/ping`: latência e responsividade.
- `/help`: lista de comandos.
- `/status`: status e rate limit.
- `/sync`: sincroniza comandos (admin).

Memória:

- `/memory add key value importance` (exemplo: `/memory add preference-language pt-br 0.8`)
- `/memory recall query limit` (exemplo: `/memory recall "linguagem preferida" 5`)

Grafo de conhecimento:

- `/graph add_node label node_type` (exemplo: `/graph add_node "Python" language`)
- `/graph add_edge source target edge_type weight` (exemplo: `/graph add_edge "Python" "Discord API" used_with 0.9`)
- `/graph query query limit` (exemplo: `/graph query "linguagens de programação" 5`)

## Pré-requisito para os comandos de memória/grafo

Os comandos `/memory ...` e `/graph ...` dependem de `bot.db_pool` estar configurado (pool `asyncpg`) e das tabelas existirem. Se não estiver, você vai ver "Database not available".

Veja `docs/05-banco-de-dados.md`.

## Modo conversacional (responder mensagens normais)

O código para responder mensagens normais existe (ver `src/discord/handlers.py`), mas no estado atual o `on_message` em `src/discord/events.py` apenas faz logging e processa comandos.

Se você quiser habilitar respostas conversacionais:

- Conecte um `MessageHandler` no `on_message`.
- Garanta que o handler seja inicializado uma vez no startup.
- Garanta que `db_pool` esteja disponível, se quiser memória/registro de conversas.

Notas:

- O orquestrador classifica intent via `SentenceTransformer` (ver `src/intent/classifier.py`).
- O orquestrador roteia para agentes e chama OpenAI (`chat.completions`) (ver `src/agents/orchestrator.py`).

## Rate limiting

O bot aplica token bucket global e por canal (ver `src/discord/rate_limiter.py`). Isso protege contra throttling da API do Discord e reduz spam de comandos.
