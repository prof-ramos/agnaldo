# Open Questions - Planos do Projeto

Este arquivo rastreia perguntas não resolvidas, decisões adiadas e itens que precisam de esclarecimento antes ou durante a execução dos planos.

---

## [coderabbit-findings-remediation] - 01/03/2026 (REVISO v2.0)

### RESOLVIDOS na Revisão v2.0

- [x] **OpenTelemetry já está configurado no projeto?** — **RESOLVIDO:** FASE 2.14 foi REMOVIDA. Apenas `opentelemetry-api` está instalado, não o SDK. Criar plano separado para feature de observabilidade completa.

- [x] **freezegun já está no pyproject.toml?** — **RESOLVIDO:** NÃO usar freezegun. FASE 1.3 agora usa datetime constante `FIXED_DATETIME = datetime(2026, 1, 1, tzinfo=timezone.utc)` sem nova dependência.

- [x] **discord.Interaction import path** — **RESOLVIDO:** Caminho especificado como `from discord import Interaction` (linha separada de `from discord import app_commands`).

- [x] **Escopo PT-BR** — **RESOLVIDO:** Apenas 3 arquivos mencionados no findings original. Expansão requer plano separado.

### Pendentes - Requer Decisão do Usuário

- [ ] **Quais agentes estão disponíveis no ecossistema multi-agent?** — A FASE 2.22 sobre backend-developer.md pede para documentar fallback behavior quando agentes como api-designer, frontend-developer etc. estão indisponíveis. Preciso saber quais agentes realmente existem no projeto.

- [ ] **Manter ou deletar qual test runner?** — A FASE 3.3 pede para unificar test runners (scripts/run_tests.py vs scripts/run_tests.sh). Precisa de decisão sobre qual manter (preferência: run_tests.py).

- [ ] **Como tratar checkpoint cleanup?** — A FASE 3.1 sobre retention policy requer implementar rotina de cleanup. Deve ser:
  - Executado apenas no startup?
  - Executado periodicamente (cron/job)?
  - Configurável via variáveis de ambiente?

- [ ] **Meta de cobertura de testes:** — FASE 1.5 pede para alinhar documentação sobre branch coverage. Qual é a meta real: 90% ou 95%? E qual é o estado atual real?

### Decisões de Escopo

- [ ] **Revisão de docstrings traduzidas** — As fases 2.1, 2.2, 2.3 envolvem traduzir docstrings para PT-BR. Deve haver revisão por falante nativo para garantir precisão técnica.

### Verificacao Pre-Implementacao

- [ ] **CoreMemory levanta DatabaseError/MemoryServiceError?** — FASE 1.2 requer PASSO 0 de verificacao antes de implementar mapeamento de excecoes. Verificar imports em src/memory/core.py e excecoes em src/exceptions.py.

### Testes

- [ ] **Quais testes usam bot_with_commands fixture?** — A FASE 2.8 requer alterar retorno da fixture de tupla para NamedTuple. Precisa identificar todos os testes que consomem esta fixture para atualiza-los.

- [ ] **Quais testes tem mock setup duplicado?** — A FASE 2.9 e 2.10 buscam eliminar duplicacao. Preciso fazer um grep para encontrar todos os lugares que repetem o mock setup de conexao.

### Documentacao

- [ ] **Arquivos de marco (IMPLEMENTACAO_COMPLETA.md, etc.) devem ser deletados ou arquivados?** — FASE 3.2. Se arquivados, para onde? Pasta `.omc/archives/`?

### Priorizacao

- [ ] **Qual a ordem de prioridade entre as fases?** — Este plano assume FASE 1 > FASE 2 > FASE 3 > FASE 4. Esta priorizacao esta correta para o projeto atual?

---

## Template para Novas Entradas

```
## [Nome do Plano] - Data

### Categoria

- [ ] **Pergunta ou decisao** — [Por que importa]
```
