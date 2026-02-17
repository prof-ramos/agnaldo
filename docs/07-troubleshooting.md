# Troubleshooting

## "Database not available" nos comandos `/memory` e `/graph`

Motivo:

- `bot.db_pool` não foi configurado.

Correção:

- Inicialize um pool `asyncpg` com `SUPABASE_DB_URL` e atribua a `bot.db_pool` no startup.
- Verifique se as tabelas do DDL existem (ver `docs/05-banco-de-dados.md`).

## Comandos slash não aparecem

Possíveis causas:

- O bot não foi convidado com os escopos corretos.
- A sincronização falhou no `on_ready` (ver logs).
- O cache do Discord pode atrasar comandos globais.

Passos:

- Use `/sync` (admin) e confirme no log.
- Garanta que o bot tenha permissões e escopos de application commands.

## Erros de `pgvector` ou embedding

Sintomas:

- Erro ao criar extensão `vector`.
- Erro de cast para `vector` em inserts.
- Dimensão diferente de 1536.

Passos:

- Confirme `CREATE EXTENSION vector`.
- Confirme que `OPENAI_EMBEDDING_MODEL` bate com a dimensão esperada pelo schema.

## Rate limit

Sintomas:

- Respostas lentas em burst de comandos.

Passos:

- Ajuste `RATE_LIMIT_GLOBAL` e `RATE_LIMIT_PER_CHANNEL` em `.env`.
- Considere reduzir chamadas a modelos em comandos frequentes.

## "python: command not found"

Use sempre `uv run` para garantir o Python do venv do projeto:

```bash
uv run python src/main.py
```
