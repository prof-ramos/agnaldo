#!/bin/bash
#
# Script para rodar todos os testes e gerar relatório datado
# Uso: ./scripts/run_tests.sh [opções]
#
# Opções:
#   --unit       Roda apenas testes unitários
#   --integration   Roda apenas testes de integração
#   --e2e        Roda apenas testes end-to-end
#   --all        Roda todos os testes (padrão)
#   --coverage   Gera relatório de cobertura
#   -h, --help   Mostra esta ajuda
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretórios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$PROJECT_DIR/reports/tests"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$REPORTS_DIR/test_report_${TIMESTAMP}.html"
REPORT_TXT="$REPORTS_DIR/test_report_${TIMESTAMP}.txt"
JSON_REPORT="$REPORTS_DIR/test_report_${TIMESTAMP}.json"

# Criar diretório de relatórios se não existir
mkdir -p "$REPORTS_DIR"

# Função para exibir ajuda
show_help() {
    head -30 "$0"
    exit 0
}

# Parsear argumentos
TEST_TYPE="all"
COVERAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            TEST_TYPE="unit"
            shift
            ;;
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --e2e)
            TEST_TYPE="e2e"
            shift
            ;;
        --all)
            TEST_TYPE="all"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo -e "${RED}Opção desconhecida: $1${NC}"
            show_help
            ;;
    esac
done

# Construir argumentos do pytest
PYTEST_ARGS=(
    "-v"
    "--tb=short"
    "--color=yes"
    "--strict-markers"
    f"--json-report"
    f"--json-report-file=$JSON_REPORT"
)

# Adicionar cobertura se solicitado
if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS+=(
        "--cov=src"
        "--cov=agnaldo"
        "--cov-report=term-missing"
        "--cov-report=html:$REPORT_FILE"
        "--cov-report=term"
    )
fi

# Selecionar tipo de teste
case $TEST_TYPE in
    unit)
        PYTEST_ARGS+=("-m" "unit")
        echo -e "${BLUE}Executando testes unitários...${NC}"
        ;;
    integration)
        PYTEST_ARGS+=("-m" "integration")
        echo -e "${BLUE}Executando testes de integração...${NC}"
        ;;
    e2e)
        PYTEST_ARGS+=("-m" "e2e")
        echo -e "${BLUE}Executando testes end-to-end...${NC}"
        ;;
    all)
        echo -e "${BLUE}Executando todos os testes...${NC}"
        ;;
esac

# Executar testes
cd "$PROJECT_DIR"

if uv run pytest "${PYTEST_ARGS[@]}" tests/ 2>&1 | tee "$REPORT_TXT"; then
    EXIT_CODE=0
    echo -e "${GREEN}✓ Todos os testes passaram!${NC}"
else
    EXIT_CODE=$?
    echo -e "${RED}✗ Alguns testes falharam${NC}"
fi

# Criar sumário em HTML
cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Testes - $TIMESTAMP</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 { margin: 0 0 10px 0; }
        .header .timestamp { opacity: 0.9; font-size: 14px; }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; text-transform: uppercase; }
        .card .value { font-size: 32px; font-weight: bold; }
        .success .value { color: #10b981; }
        .failed .value { color: #ef4444; }
        .skipped .value { color: #f59e0b; }
        .content { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        pre { background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status.pass { background: #d1fae5; color: #065f46; }
        .status.fail { background: #fee2e2; color: #991b1b; }
        .status.skip { background: #fef3c7; color: #92400e; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Relatório de Testes</h1>
        <div class="timestamp">Executado em: $(date -r "$TIMESTAMP" "+%d/%m/%Y às %H:%M:%S" 2>/dev/null || date "+%d/%m/%Y às %H:%M:%S")</div>
        <div class="timestamp">Tipo de teste: $TEST_TYPE</div>
    </div>
    
    <div class="summary">
        <div class="card success">
            <h3>Status</h3>
            <div class="value">$(if [ $EXIT_CODE -eq 0 ]; then echo "✓ Passou"; else echo "✗ Falhou"; fi)</div>
        </div>
        <div class="card">
            <h3>Tipo</h3>
            <div class="value">$TEST_TYPE</div>
        </div>
        <div class="card">
            <h3>Data</h3>
            <div class="value" style="font-size: 20px;">$(date +"%d/%m/%Y")</div>
        </div>
    </div>
    
    <div class="content">
        <h2>📋 Saída dos Testes</h2>
        <pre>$(cat "$REPORT_TXT" | head -200)</pre>
    </div>
</body>
</html>
EOF

# Links simbólicos para relatórios mais recentes
ln -sf "$REPORT_FILE" "$REPORTS_DIR/latest.html"
ln -sf "$REPORT_TXT" "$REPORTS_DIR/latest.txt"
ln -sf "$JSON_REPORT" "$REPORTS_DIR/latest.json"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Relatório gerado com sucesso!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  📄 HTML: ${GREEN}$REPORT_FILE${NC}"
echo -e "  📄 TXT:  ${GREEN}$REPORT_TXT${NC}"
echo -e "  📄 JSON: ${GREEN}$JSON_REPORT${NC}"
echo ""
echo -e "  🔗 Latest: ${GREEN}$REPORTS_DIR/latest.html${NC}"
echo ""

exit $EXIT_CODE
