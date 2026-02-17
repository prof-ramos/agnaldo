---
allowed-tools: Bash, WebFetch
argument-hint: [data-source] | --xatu | --custom-url <url> | --validate
description: Load and process external documentation context from llms.txt files or custom sources
---

# External Documentation Context Loader

Load external documentation context: `$ARGUMENTS`

## Como `$ARGUMENTS` funciona

`$ARGUMENTS` contém os argumentos passados ao comando.

- `--xatu`: força carregamento do `llms.txt` padrão do Xatu
- `--custom-url <url>`: usa uma URL externa fornecida pelo usuário
- `--validate`: apenas valida e resume o conteúdo, sem integrar
- Sem argumentos: tenta cache/local primeiro e cai para Xatu

## Current Context Status

- Network access: !`curl -sSfL --connect-timeout 5 --max-time 10 https://httpbin.org/status/200 >/dev/null && echo "✅ Available" || echo "❌ Limited"`
- Existing context files:
  - !`[ -f llms.txt ] && echo "✅ local llms.txt encontrado" || echo "ℹ️ local llms.txt não encontrado"`
  - !`[ -d .claude/docs-cache ] && echo "✅ cache .claude/docs-cache encontrado" || echo "ℹ️ cache .claude/docs-cache não encontrado"`
- Project type signals: @package.json or @README.md

## Task

Load and process external documentation context from specified source.

### Download padrão (Xatu)

```bash
set -euo pipefail
XATU_URL="https://raw.githubusercontent.com/ethpandaops/xatu-data/main/llms.txt"
CACHE_DIR=".claude/docs-cache"
mkdir -p "$CACHE_DIR"
TEMP_FILE="$(mktemp)"
trap 'rm -f "$TEMP_FILE"' EXIT

curl -sSfL --connect-timeout 10 --max-time 60 "$XATU_URL" -o "$TEMP_FILE"
cp "$TEMP_FILE" "$CACHE_DIR/xatu-llms.txt"
cat "$TEMP_FILE"
```

### Custom Source Loading

Implemente este fluxo para `--custom-url`:

```bash
validate_url() {
  local url="$1"

  # 1) esquema obrigatório
  case "$url" in
    http://*|https://*) ;;
    *) echo "URL inválida: use http(s)"; return 1 ;;
  esac

  # 2) hosts suspeitos (localhost, loopback, redes internas)
  if echo "$url" | grep -Eiq 'localhost|127\.0\.0\.1|0\.0\.0\.0|::1|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.'; then
    echo "Host bloqueado por segurança"
    return 1
  fi

  # 3) HEAD com timeout e redirecionamento
  curl -sSfIL --connect-timeout 10 --max-time 30 "$url" >/dev/null
}
```

Após validar:

1. baixar para `mktemp`
2. salvar em `.claude/docs-cache/custom-<timestamp>.txt`
3. limitar tamanho (ex.: 5 MB)
4. extrair blocos úteis (`head`, `rg`, seções principais)
5. integrar ao contexto do projeto

### Processing Options

- **Raw loading (`--custom-url <url>`):** baixa e mostra conteúdo bruto.
  - Exemplo: `load-llms-txt --custom-url https://example.com/llms.txt`
- **Validation (`--validate`):** checa formato (título, links, tamanho, encoding) e gera resumo.
  - Exemplo: `load-llms-txt --validate --custom-url https://example.com/llms.txt`
- **Integration (default / `--xatu`):** combina documentação carregada com contexto atual do projeto.
  - Exemplo: `load-llms-txt --xatu`
- **Caching (automático):** sempre salva em `.claude/docs-cache/` para uso offline/repetido.

## Nota sobre `!`

Quando usado como `!\`comando\``, o comando shell é executado dinamicamente e o resultado é incorporado na resposta.
