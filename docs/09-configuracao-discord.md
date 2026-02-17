# Configuracao do Bot no Discord

## Criar a aplicacao e o bot

1. Acesse o Discord Developer Portal e crie uma aplicacao.
2. No menu "Bot", crie o bot (se ainda nao existir).
3. Gere e copie o token do bot e coloque em `.env` como `DISCORD_BOT_TOKEN`.

## Intents

O bot suporta intents configuraveis via `DISCORD_INTENTS` (ver `src/config/settings.py` e `src/discord/bot.py`).

Se voce pretende habilitar respostas a mensagens (modo conversacional), habilite no portal:

- Message Content Intent

Observacao:

- Sem o intent de message content, o bot pode nao receber `message.content` em eventos.

## Convidar o bot para um servidor

Na pagina de OAuth2 (Discord Developer Portal), gere uma URL com:

Scopes: `bot`, `applications.commands`.

Permissoes:

- As permissoes dependem do que voce quer que ele faca.
- Para slash commands simples, geralmente nao precisa de permissoes elevadas.

## Sincronizacao de slash commands

Os slash commands sao registrados em `src/discord/commands.py`.

No estado atual:

- O bot tenta executar `bot.tree.sync()` no `on_ready` definido dentro de `setup_commands()`.
- Existe um comando `/sync` (admin) para sincronizar manualmente.

Se os comandos nao aparecerem, veja `docs/07-troubleshooting.md`.
