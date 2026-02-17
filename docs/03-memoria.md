# Memória

O Agnaldo tem dois "mundos" de memória:

- Memória no banco (tiered memory): Core, Recall e Archival.
- Memória em arquivos (templates OpenClaw): `memory/YYYY-MM-DD.md` e `MEMORY.md`.

## Memória no banco (Core, Recall, Archival)

### Core Memory (Tier 1)

Para fatos importantes e acesso rápido por chave.

- Código: `src/memory/core.py`
- Tabela esperada (pelo codigo): `core_memories`
- Comando: `/memory add`

Boas práticas para `key`:

- Use prefixos: `preference-...`, `profile-...`, `project-...`
- Evite PII e segredos em ambientes compartilhados.

### Recall Memory (Tier 2)

Para recuperar trechos por similaridade semântica usando embeddings.

- Código: `src/memory/recall.py`
- Usa embeddings OpenAI (`OPENAI_EMBEDDING_MODEL`)
- Tabela esperada (pelo codigo): `recall_memories` com coluna `embedding vector(1536)`
- Comando: `/memory recall`

Como a busca funciona (resumo):

- Gera embedding do `query`.
- Filtra por `user_id` e `importance`.
- Ordena por distancia coseno usando `pgvector` (`<=>`).

### Archival Memory (Tier 3)

Para longo prazo com compressão e filtros por metadata.

- Código: `src/memory/archival.py`
- Tabela esperada (pelo codigo): `archival_memories`
- Não há slash command dedicado no estado atual.

Principais métodos expostos pelo módulo:

- `add(content, source, metadata, session_id)`
- `compress(session_id)`
- `search_by_metadata(filters)`
- `search_by_content(query)`

## Memória em arquivos (OpenClaw)

O repositório inclui templates em `src/templates/` para um fluxo de operação por arquivos:

- `src/templates/AGENTS.md`: rotina de "toda sessão" e regras de operação.
- `src/templates/MEMORY.md`: memória curada de longo prazo (com alerta de segurança).
- `src/templates/SOUL.md`: filosofia e personalidade do agente.
- `src/templates/TOOLS.md`: notas locais do ambiente.

Uso tipico:

- Em privado/DM: manter `MEMORY.md` como memória curada.
- Diário: registrar contexto em `memory/YYYY-MM-DD.md`.
- Em publico: evite carregar contexto sensivel.

Importante:

- A memória por arquivos é um mecanismo de operação/continuidade (para agentes que leem arquivos).
- A memória no banco é usada pelo bot e pelos comandos (quando `db_pool` está configurado).
