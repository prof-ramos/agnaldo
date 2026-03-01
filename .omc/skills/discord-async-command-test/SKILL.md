---
id: discord-async-command-test
name: Discord Async Command Test Pattern
description: Teste de comandos Discord async requer await em setup_commands e mock adequado de bot.tree
source: conversation
triggers:
  - "RuntimeWarning coroutine was never awaited"
  - "setup_commands mock_bot"
  - "discord command test mock"
  - "bot.tree.walk_commands not found"
quality: high
---

# Discord Async Command Test Pattern

## The Insight

`setup_commands` é uma função `async def` em discord.py que registra comandos usando decoradores `@bot.tree.command()`. Em testes com mocks, chamar essa função sem `await` significa que os comandos nunca são registrados, resultando em buscas que falham silenciosamente retornando `None`.

O princípio: **qualquer função async que registra estado deve ser awaited antes de usar esse estado em asserts**.

## Why This Matters

Sem `await setup_commands(mock_bot)`:
- Comandos não são registrados no `bot.tree`
- `walk_commands()` retorna iterator vazio
- Assert `assert command is not None` falha com mensagem enganosa
- RuntimeWarning aparece no output: `coroutine 'setup_commands' was never awaited`

Com `await setup_commands(mock_bot)`:
- Decoradores `@bot.tree.command` são executados
- Mock bot.tree contém os comandos registrados
- Tests podem encontrar e invocar comandos corretamente

## Recognition Pattern

Quando aplicar esta skill:
- Testando comandos Discordslash em `tests/integration/test_discord/`
- Usando `unittest.mock.MagicMock()` para mockar `Bot`
- Chamando `setup_commands()` ou funções similares de registro
- Vendo `RuntimeWarning: coroutine 'X' was never awaited`
- Buscando comandos com `bot.tree.walk_commands()`

## The Approach

Heurística para testar comandos Discord async:

1. **Sempre await funções de registro**:
   ```python
   # ERRADO - Função retorna coroutine não executada
   setup_commands(mock_bot)

   # CORRETO - Executa a coroutine e espera registro
   await setup_commands(mock_bot)
   ```

2. **Mock bot.tree corretamente**:
   ```python
   mock_bot = MagicMock()
   mock_bot.tree = MagicMock()  # Necessário para walk_commands funcionar
   mock_bot.tree.walk_commands = MagicMock(return_value=[])
   mock_bot.get_rate_limiter.return_value.acquire = AsyncMock()
   ```

3. **Verifique que comando foi registrado antes de usar**:
   ```python
   await setup_commands(mock_bot)

   command = None
   for cmd in mock_bot.tree.walk_commands():
       if cmd.name == "memory":
           command = cmd
           break

   assert command is not None, "Comando não encontrado - setup falhou?"
   ```

## Example

**Código problemático:**
```python
# tests/integration/test_discord/test_handlers.py
async def test_memory_add_exception_not_exposed_to_user():
    mock_bot = MagicMock()
    mock_bot.db_pool = mock_db_pool

    # Sem await - comandos não são registrados!
    setup_commands(mock_bot)

    # Isso vai falhar: command sempre é None
    memory_add_cmd = None
    for command in mock_bot.tree.walk_commands():
        if command.name == "memory":
            for subcommand in command.walk_commands():
                if subcommand.name == "add":
                    memory_add_cmd = subcommand

    assert memory_add_cmd is not None  # ❌ FALHA
```

**Código corrigido:**
```python
async def test_memory_add_exception_not_exposed_to_user():
    mock_bot = MagicMock()
    mock_bot.db_pool = mock_db_pool

    # Com await - comandos são registrados corretamente
    await setup_commands(mock_bot)  # ✓

    memory_add_cmd = None
    for command in mock_bot.tree.walk_commands():
        # ... busca funciona

    assert memory_add_cmd is not None  # ✓ PASSA
```

## Gotchas

- **Mock bot.tree deve existir**: `MagicMock()` cria atributos dinamicamente, mas `walk_commands()` pode não funcionar como esperado
- **Subcommands requerem iteração aninhada**: Comandos com grupos precisam de `command.walk_commands()` recursivamente
- **Rate limiter mock**: Mock `get_rate_limiter().acquire()` como `AsyncMock()` para evitar warnings
- **Interaction mock**: Certifique-se que `interaction.response.is_done()` está configurado para mock state
