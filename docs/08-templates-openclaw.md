# Templates (OpenClaw)

O diretorio `src/templates/` traz templates para um workflow orientado a arquivos, inspirado em OpenClaw.

Arquivos principais:

- `src/templates/README.md`: explicacao dos templates.
- `src/templates/SOUL.md`: template de personalidade do agente.
- `src/templates/AGENTS.md`: manual operacional (o que ler a cada sessao, seguranca, memoria).
- `src/templates/MEMORY.md`: memoria curada de longo prazo (com aviso de seguranca).
- `src/templates/USER.md`: perfil do usuario.
- `src/templates/IDENTITY.md`: identidade do agente.
- `src/templates/TOOLS.md`: notas locais do ambiente.
- `src/templates/HEARTBEAT.md`: checklists de manutencao.

## Como usar no workspace

Se voce quer adotar esse workflow na raiz do repo:

```bash
cp src/templates/SOUL.md .
cp src/templates/USER.md .
cp src/templates/IDENTITY.md .
cp src/templates/TOOLS.md .
cp src/templates/HEARTBEAT.md .
cp src/templates/AGENTS.md .
cp src/templates/MEMORY.md .
mkdir -p memory
```

## Diferenca entre `SOUL.md` (raiz) e `src/templates/SOUL.md`

- `SOUL.md` na raiz do repo e o que o bot carrega no runtime (ver `src/main.py`).
- `src/templates/SOUL.md` e um template para bootstrap e padronizacao; voce pode copiar para a raiz e depois evoluir.

