# Documentacao do Agnaldo

Manual de uso do bot (Discord) e das ferramentas de personalidade (`SOUL.md`), prompts/templates e memoria (banco + arquivos).

## TL;DR (rodar local)

```bash
uv sync
cp .env.example .env
uv run python src/main.py
```

Observacoes importantes:

- Os slash commands `/memory ...` e `/graph ...` exigem `bot.db_pool` (pool `asyncpg`) configurado. No estado atual do codigo, o pool nao e inicializado no `src/main.py` (veja `docs/05-banco-de-dados.md`).
- O handler conversacional (responder mensagens normais) existe em `src/discord/handlers.py`, mas nao esta conectado ao `on_message` em `src/discord/events.py` (veja `docs/02-uso-no-discord.md`).
- Existe divergencia entre esquemas de banco em `src/database/migrations/versions/001_initial.py` e o SQL com `pgvector` em `src/database/migrations/versions/001_create_memory_tables.sql`. Este manual explica como escolher um caminho e o que precisa bater com o codigo (veja `docs/05-banco-de-dados.md`).

## Conteudo

- [01 - Quickstart](./01-quickstart.md)
- [02 - Uso no Discord](./02-uso-no-discord.md)
- [03 - Memoria](./03-memoria.md)
- [04 - Prompts e Personalidade](./04-prompts-e-personalidade.md)
- [05 - Banco de Dados](./05-banco-de-dados.md)
- [06 - Ferramentas Open Source (MIT) para Prompts/Evals](./06-ferramentas-mit.md)
- [07 - Troubleshooting](./07-troubleshooting.md)
- [08 - Templates (OpenClaw)](./08-templates-openclaw.md)
- [09 - Configuracao do Bot no Discord](./09-configuracao-discord.md)
