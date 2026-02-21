#!/usr/bin/env python3
"""
Script para rodar todos os testes e gerar relatório datado.

Uso:
    uv run testes                    # Roda todos os testes
    uv run testes --unit            # Roda apenas testes unitários
    uv run testes --integration     # Roda apenas testes de integração
    uv run testes --e2e             # Roda apenas testes end-to-end
    uv run testes --coverage        # Gera relatório de cobertura
    uv run testes --help           # Mostra ajuda
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_project_dir() -> Path:
    """Retorna o diretório do projeto."""
    return Path(__file__).parent.parent


def get_reports_dir() -> Path:
    """Retorna o diretório de relatórios."""
    project_dir = get_project_dir()
    reports_dir = project_dir / "reports" / "tests"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def run_tests(
    test_type: str = "all",
    coverage: bool = False,
    verbose: bool = True,
) -> tuple[int, str]:
    """
    Executa os testes com pytest.
    
    Args:
        test_type: Tipo de teste (all, unit, integration, e2e)
        coverage: Se True, gera relatório de cobertura
        verbose: Se True, mostra output detalhado
        
    Returns:
        Tupla com (código de saída, output dos testes)
    """
    project_dir = get_project_dir()
    reports_dir = get_reports_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Construir argumentos do pytest
    pytest_args = [
        "pytest",
        "-v" if verbose else "-q",
        "--tb=short",
        "--color=yes",
        "--strict-markers",
    ]
    
    # Adicionar marcador de tipo de teste
    if test_type == "unit":
        pytest_args.extend(["-m", "unit"])
    elif test_type == "integration":
        pytest_args.extend(["-m", "integration"])
    elif test_type == "e2e":
        pytest_args.extend(["-m", "e2e"])
    
    # Adicionar cobertura se solicitado
    if coverage:
        pytest_args.extend([
            "--cov=src",
            "--cov=agnaldo",
            "--cov-report=term-missing",
            "--cov-report=term",
        ])
    
    # Adicionar caminho dos testes
    pytest_args.append("tests/")
    
    # Executar testes
    result = subprocess.run(
        pytest_args,
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    
    output = result.stdout + result.stderr
    
    # Salvar relatório de texto
    txt_report = reports_dir / f"test_report_{timestamp}.txt"
    txt_report.write_text(output)
    
    # Criar link simbólico para o mais recente
    latest_txt = reports_dir / "latest.txt"
    if latest_txt.exists():
        latest_txt.unlink()
    latest_txt.symlink_to(txt_report.name)
    
    return result.returncode, output, timestamp


def generate_html_report(
    timestamp: str,
    test_type: str,
    exit_code: int,
    output: str,
) -> Path:
    """Gera relatório HTML com os resultados dos testes."""
    reports_dir = get_reports_dir()
    
    # Contar resultados
    passed = output.count(" PASSED")
    failed = output.count(" FAILED")
    skipped = output.count(" SKIPPED")
    errors = output.count(" ERROR")
    
    # Determinar status
    status = "✓ Passou" if exit_code == 0 else "✗ Falhou"
    status_color = "#10b981" if exit_code == 0 else "#ef4444"
    
    # Formatar data
    try:
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        formatted_date = dt.strftime("%d/%m/%Y às %H:%M:%S")
    except ValueError:
        formatted_date = timestamp
    
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Testes - {timestamp}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .timestamp {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            font-weight: 600;
        }}
        .card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .card.passed .value {{ color: #10b981; }}
        .card.failed .value {{ color: #ef4444; }}
        .card.skipped .value {{ color: #f59e0b; }}
        .card.status .value {{ color: {status_color}; }}
        .content {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .content h2 {{
            margin-bottom: 15px;
            color: #333;
        }}
        pre {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 13px;
            max-height: 500px;
            overflow-y: auto;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 14px;
        }}
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Relatório de Testes</h1>
            <div class="timestamp">Executado em: {formatted_date}</div>
            <div class="timestamp">Tipo de teste: {test_type}</div>
        </div>
        
        <div class="summary">
            <div class="card status">
                <h3>Status</h3>
                <div class="value">{status}</div>
            </div>
            <div class="card passed">
                <h3>Passados</h3>
                <div class="value">{passed}</div>
            </div>
            <div class="card failed">
                <h3>Falharam</h3>
                <div class="value">{failed}</div>
            </div>
            <div class="card skipped">
                <h3>Skipped</h3>
                <div class="value">{skipped}</div>
            </div>
        </div>
        
        <div class="content">
            <h2>📋 Saída dos Testes</h2>
            <pre>{output[:50000]}</pre>
        </div>
        
        <div class="footer">
            <p>Gerado automaticamente por <strong>testes</strong> - Agnaldo Project</p>
        </div>
    </div>
</body>
</html>"""
    
    html_report = reports_dir / f"test_report_{timestamp}.html"
    html_report.write_text(html_content)
    
    # Criar link simbólico
    latest_html = reports_dir / "latest.html"
    if latest_html.exists():
        latest_html.unlink()
    latest_html.symlink_to(html_report.name)
    
    return html_report


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Roda testes e gera relatório datado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
    uv run testes                    # Roda todos os testes
    uv run testes --unit            # Roda apenas unitários
    uv run testes --integration     # Roda apenas integração
    uv run testes --e2e             # Roda apenas e2e
    uv run testes --coverage        # Com relatório de cobertura
    uv run testes -v                # Verboso
    uv run testes -q                # Quieto
        """,
    )
    
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Roda apenas testes unitários",
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Roda apenas testes de integração",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Roda apenas testes end-to-end",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Gera relatório de cobertura de código",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="Modo verboso (padrão)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Modo quieto",
    )
    
    args = parser.parse_args()
    
    # Determinar tipo de teste
    if args.unit:
        test_type = "unit"
    elif args.integration:
        test_type = "integration"
    elif args.e2e:
        test_type = "e2e"
    else:
        test_type = "all"
    
    # Ajustar verbosidade
    verbose = not args.quiet
    
    print(f"\n{'='*60}")
    print(f"  🚀 Executando testes ({test_type})")
    print(f"{'='*60}\n")
    
    try:
        exit_code, output, timestamp = run_tests(
            test_type=test_type,
            coverage=args.coverage,
            verbose=verbose,
        )
        
        # Gerar relatório HTML
        html_report = generate_html_report(
            timestamp=timestamp,
            test_type=test_type,
            exit_code=exit_code,
            output=output,
        )
        
        reports_dir = get_reports_dir()
        
        print(f"\n{'='*60}")
        if exit_code == 0:
            print(f"  ✓ Todos os testes passaram!")
        else:
            print(f"  ✗ Alguns testes falharam")
        print(f"{'='*60}")
        print(f"\n📄 Relatórios gerados:")
        print(f"   - TXT: {reports_dir / f'test_report_{timestamp}.txt'}")
        print(f"   - HTML: {html_report}")
        print(f"   - Latest: {reports_dir / 'latest.html'}")
        print()
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Testes cancelados pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Erro ao executar testes: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
