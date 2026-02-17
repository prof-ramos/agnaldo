# Ferramentas Open Source (MIT) para Prompts/Evals

Ferramentas sob licença MIT que podem ajudar a testar prompts, rodar avaliações, comparar modelos e padronizar chamadas:

## promptfoo

Framework de testes e avaliação de prompts (matriz de casos, asserts, diffs, CI).

- Repo: [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo)
- Licença: MIT (ver o arquivo `LICENSE` do repositório: [LICENSE](https://raw.githubusercontent.com/promptfoo/promptfoo/main/LICENSE))

Uso típico:

- Definir suítes de casos (entradas, variáveis, expectativas).
- Rodar local e no CI para evitar regressão de prompt.

## LiteLLM

Gateway/SDK para unificar chamadas de modelos (multi-provider) e facilitar trocas de modelo sem refatorar toda a base.

- Repo: [BerriAI/litellm](https://github.com/BerriAI/litellm)
- Licença: MIT (com exceções documentadas no repositório, ver: [LICENSE](https://raw.githubusercontent.com/BerriAI/litellm/main/LICENSE))

Uso típico:

- Padronizar interface de completions/embeddings.
- Testar prompts com diferentes provedores/modelos.

## Langfuse

Observabilidade de LLM (traces, prompts, avaliações) para acompanhar qualidade e custo em produção.

- Repo: [langfuse/langfuse](https://github.com/langfuse/langfuse)
- Licença: MIT (com exceções documentadas no repositório, ver: [LICENSE](https://raw.githubusercontent.com/langfuse/langfuse/main/LICENSE))

Uso típico:

- Rastrear conversas e custos.
- Versionar prompts e medir impacto.

## lm-evaluation-harness

Harness de avaliação de LMs (benchmarks e suítes padronizadas). Não é "teste de prompt" no sentido estrito, mas ajuda a medir modelos e regressão.

- Repo: [EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
- Licença: MIT (ver: [LICENSE.md](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/master/LICENSE.md))

## Checklist rápido de "teste de prompt"

- Fixar um conjunto de casos representativos.
- Evitar avaliar só "exemplos bonitos"; inclua edge cases.
- Capturar regressão: quando uma mudança melhora um caso mas piora outro.
- Separar "qualidade" de "custo/latência".
