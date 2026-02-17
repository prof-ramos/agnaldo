# Quickstart

## Requisitos

- Python `>=3.10,<3.14` (ver `pyproject.toml`)
- `uv` instalado e funcionando
- Token do bot Discord
- Chave OpenAI (chat + embeddings)
- Postgres com extensao `pgvector` (Supabase recomendado)

## Setup

1. Instalar dependencias:

```bash
uv sync
```

Verifique se o venv do projeto esta OK:

```bash
uv run python -V
```

2. Configurar variaveis de ambiente:

```bash
cp .env.example .env
```

Edite `.env` com pelo menos:

- `DISCORD_BOT_TOKEN`
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`

3. Preparar banco

Veja `docs/05-banco-de-dados.md` para criar as tabelas e configurar `asyncpg`.

## Rodando

```bash
uv run python src/main.py
```

## Testes e qualidade

```bash
uv run pytest
uv run mypy src/
```
