# Plano de Implementação - Bot RAG para Concursos Públicos

**Data**: 2026-02-17
**Status**: v2 (Revisado após Architect + Critic)
**Autores**: Planner Agent (v1) → Revisado (v2)

---

## Changelog v1 → v2

| Issue | Fonte | Correção |
|-------|-------|----------|
| `PDFKnowledgeBase` não existe | Critic 🔴 | Implementar ingestão do zero com PyPDF2 |
| Tabela `legal_documents` vs `archival_memories` | Architect 🔴 | Reutilizar `archival_memories` com `category` |
| Handler `on_message` não registrado | Architect 🔴 | Adicionar tarefa para registrar em `events.py` |
| FR-2 Anti-alucinação não especificado | Critic 🔴 | Adicionar implementação `CitationValidator` |
| `!ask` vs `/ask` inconsistência | Critic 🟡 | Decidir: prefix command `!ask` (imediato) |
| `out_of_scope` handler faltando | Critic 🟡 | Adicionar implementação específica |
| Schema `user_study_preferences` duplicata | Architect 🟡 | Reutilizar `CoreMemory` |
| Integração Study Agent não especificada | Architect 🔴 | Adicionar `AgentType.STUDY` ao enum |

---

## 1. Resumo Executivo

Transformar o bot Agnaldo em um bot especializado em concursos públicos com RAG rigoroso, reutilizando ao máximo a infraestrutura existente (memórias, pgvector, orchestrator) e adicionando componentes específicos para domínio jurídico.

**Métricas de Sucesso**:
- ≥ 95% das respostas `!ask` com fonte citada
- ≤ 1% de alucinações detectadas
- Latência p95 < 5s para `!ask`

---

## 2. Análise Gap - Estado Atual vs PRD

### Componentes Existentes (Reutilizáveis)
| Componente | Status | Como Reutilizar |
|------------|--------|-----------------|
| Discord Bot (discord.py) | ✅ Funcional | Registrar `on_message` em `events.py` |
| Intent Classifier (SentenceTransformer) | ✅ Funcional | Estender `IntentCategory` enum |
| Agent Orchestrator | ✅ Funcional | Adicionar `AgentType.STUDY` |
| ArchivalMemory + pgvector | ✅ Funcional | Usar para docs jurídicos (`category="legal"`) |
| CoreMemory (key-value) | ✅ Funcional | Usar para preferências de estudo |
| RecallMemory (busca semântica) | ✅ Funcional | Manter para contexto conversacional |

### Gaps Principais (Componentes a Criar)
| Gap | Prioridade | Complexidade | Solução |
|-----|------------|--------------|---------|
| Ingestão de PDFs jurídicos | 🔴 Crítica | Alta | Implementar com PyPDF2 + tiktoken |
| Study Agent (RAG rigoroso) | 🔴 Crítica | Alta | Novo `AgentType.STUDY` com T=0.0 |
| CitationValidator (FR-2) | 🔴 Crítica | Alta | Validar citações com regex + RAG |
| `on_message` handler | 🔴 Crítica | Baixa | Adicionar evento em `events.py` |
| SOUL.md dual personality | 🟡 Alta | Média | Reescrever com dois modos |
| `out_of_scope` handler (FR-13) | 🟡 Alta | Baixa | Adicionar rota específica |

---

## 3. Fases de Implementação

### Fase 1: MVP - RAG + `!ask` (2 semanas)

**Objetivo**: Comando `!ask` funcional com RAG rigoroso

#### 1.1 Base de Conhecimento RAG (Reutilizando ArchivalMemory)

**Decisão Arquitetural**: Reutilizar `archival_memories` ao invés de criar nova tabela.

```python
# Em ArchivalMemory (models.py:325-368)
# Usar category para diferenciar tipos de documentos:
category = "legal_legislacao" | "legal_doutrina" | "legal_questoes" | "legal_jurisprudencia"

# Metadados em archival_metadata JSONB:
{
    "fonte": "Código Penal",
    "artigo": "121",
    "pagina": 42,
    "area_direito": "penal",
    "ano_vigencia": 2024
}
```

- [ ] Criar estrutura `data/concursos/` com subpastas
- [ ] Implementar ingestão de PDFs com **PyPDF2** (não existe PDFKnowledgeBase)
- [ ] Chunks de 512-1024 tokens com overlap 128 (tiktoken)
- [ ] Gerar embeddings OpenAI (`text-embedding-3-small`)
- [ ] Inserir em `archival_memories` com `category="legal_*"`

**Arquivos Novos**:
```python
# src/knowledge/legal_pdf_ingestor.py
from pathlib import Path
import pypdf2
from tiktoken import encoding_for_model
from openai import AsyncOpenAI

class LegalPDFIngestor:
    """Ingest PDFs legais into ArchivalMemory."""

    async def ingest_pdf(
        self,
        pdf_path: Path,
        category: str,  # legal_legislacao, legal_doutrina, etc
        metadados: dict
    ) -> int:
        """Extract text, chunk, embed, and store."""
        # 1. Extract text with PyPDF2
        # 2. Chunk with tiktoken (512-1024 tokens, overlap 128)
        # 3. Embed with OpenAI text-embedding-3-small
        # 4. Insert into archival_memories table
```

**Arquivos Modificados**:
- `src/database/models.py` - Adicionar constante `LEGAL_CATEGORIES`

#### 1.2 Study Agent + CitationValidator (FR-2)

- [ ] Adicionar `AgentType.STUDY = "study"` ao enum (orchestrator.py:31-48)
- [ ] Criar `StudyAgent` herdando de `AgnoAgent`:
  ```python
  class StudyAgent(AgnoAgent):
      def __init__(self, ...):
          super().__init__(
              agent_type=AgentType.STUDY,
              temperature=0.0,  # Determinismo
              model="gpt-4o"
          )
  ```
- [ ] Implementar `CitationValidator`:
  ```python
  # src/validators/citation_validator.py
  class CitationValidator:
      async def validate_response(
          self,
          response: str,
          rag_sources: list[dict],
          threshold: float = 0.7
      ) -> ValidationResult:
          """
          1. Extrair citações com regex (Art. \d+, Lei \d+)
          2. Verificar se existe em rag_sources
          3. Retornar warning se similaridade < threshold
          """
  ```
- [ ] Template de resposta padrão (FR-3):
  ```python
  RESPONSE_TEMPLATE = """
  📚 **{titulo}**

  {conteudo}

  💡 **Didática**: {didatica}

  📖 **Fonte**: {fonte}
  """
  ```
- [ ] Resposta de incerteza padrão (US-003):
  ```python
  UNCERTAINTY_RESPONSE = """
  ❌ Não encontrei informação precisa na base de estudos.
  💡 Sugestão: Consulte o Código Penal, arts. 121-122, ou a obra "Curso de Direito Penal" de Rogério Greco.
  """
  ```

**Arquivos Novos**:
- `src/agents/study_agent.py`
- `src/validators/citation_validator.py`

**Arquivos Modificados**:
- `src/agents/orchestrator.py` - Adicionar `AgentType.STUDY`
- `src/intent/router.py` - Roteamento `STUDY_QUESTION` → `STUDY`

#### 1.3 Comando `!ask` + Handler `on_message`

**Decisão**: Usar **prefix command** `!ask` (imediato) ao invés de slash `/ask`.

- [ ] Registrar `on_message` em `src/discord/events.py`:
  ```python
  @bot.event
  async def on_message(message: discord.Message):
      if message.author.bot:
          return
      # Check for !ask prefix
      if message.content.startswith("!ask"):
          await handle_ask_command(message)
      else:
          await handle_general_message(message)
  ```
- [ ] Implementar `handle_ask_command()`:
  ```python
  async def handle_ask_command(message: discord.Message):
      # Extract question after !ask
      question = message.content[5:].strip()
      # Route to StudyAgent directly
      response = await study_agent.process(question, context)
      await message.reply(response)
  ```
- [ ] Rate limiting: 5 req/minuto por usuário (TokenBucket)
- [ ] Logs estruturados (FR-17):
  ```python
  log_entry = {
      "timestamp": datetime.now().isoformat(),
      "user_id": str(message.author.id),
      "command": "!ask",
      "question": question,
      "rag_results": len(sources),
      "sources": [s["fonte"] for s in sources],
      "latency_ms": latency
  }
  ```

**Arquivos Modificados**:
- `src/discord/events.py` - Adicionar `on_message`
- `src/discord/handlers.py` - Adicionar handlers específicos

---

### Fase 2: Dual-Mode + Intent (1 semana)

**Objetivo**: Detecção automática de modo estudo vs conversacional

#### 2.1 Expansão do Intent Classifier

- [ ] Adicionar categorias ao `IntentCategory` (models.py):
  ```python
  class IntentCategory(str, Enum):
      # ... existentes ...
      STUDY_QUESTION = "study_question"
      CASUAL_CHAT = "casual_chat"
      MOTIVATIONAL_SUPPORT = "motivational_support"
      OUT_OF_SCOPE = "out_of_scope"
  ```
- [ ] Criar dataset zero-shot em `data/intent_dataset/legal_intents.json`:
  ```json
  {
    "study_question": [
      "quais qualificadoras existem no homicídio",
      "explica princípio da legalidade",
      "diferença entre dolo eventual e culpa consciente"
    ],
    "casual_chat": [
      "e aí como vai",
      "tô cansado hoje",
      "viu o jogo ontem"
    ],
    "motivational_support": [
      "tô pensando em desistir",
      "não aguento mais estudar"
    ],
    "out_of_scope": [
      "qual o sentido da vida",
      "como faço bolo de cenoura"
    ]
  }
  ```
- [ ] Implementar `out_of_scope` handler (FR-13):
  ```python
  async def handle_out_of_scope() -> str:
      return (
          "Não consigo ajudar com isso, mas posso te ajudar com "
          "dúvidas de estudo (!ask) ou bater um papo sobre a rotina de concurseiro!"
      )
  ```

**Arquivos Modificados**:
- `src/intent/models.py`
- `src/intent/router.py`
- `data/intent_dataset/legal_intents.json` (novo)

#### 2.2 SOUL.md Dual Personality

- [ ] Reescrever `SOUL.md` completamente com estrutura dual:
  ```markdown
  # SOUL - Assistente de Concursos Públicos

  ## Identidade
  Sou um assistente especializado em concursos públicos brasileiros,
  focado em **precisão e didática**.

  ## Modo Operacional

  ### 🎯 Modo Estudo (comando `!ask`)
  - **Prioridade**: Precisão e minimização de alucinações (meta: ≤1%)
  - **Base**: Apenas RAG (legislação, doutrina, questões)
  - **Tom**: Técnico, didático, objetivo
  - **Formato**: Resposta + Didática + Fonte obrigatória
  - **Limites**: Se não sei, digo "Não encontrei na base"

  ### 💬 Modo Conversacional (chat livre)
  - **Prioridade**: Apoio e motivação
  - **Tom**: Amigável, empático, encorajador
  - **Limites**: Não dou respostas técnicas (só em !ask)
  ```

**Arquivos Modificados**:
- `SOUL.md` - Reescrita completa

#### 2.3 Chat Agent (Modo Conversacional)

- [ ] Criar `ChatAgent` separado do `ConversationalAgent`:
  ```python
  chat_agent = AgnoAgent(
      agent_id="agent_chat",
      agent_type=AgentType.CONVERSATIONAL,
      temperature=0.7,  # Mais criativo
      instructions=[SOUL_CHAT_MODE]  # Personalidade amigável
  )
  ```
- [ ] Quando detectar pergunta técnica em modo casual:
  ```python
  TECHNICAL_QUESTION_PROMPT = (
      "Essa é uma dúvida técnica interessante! "
      "Para uma resposta precisa com fontes, usa !ask com sua pergunta. "
      "Quer que eu te ajuda a formular a pergunta?"
  )
  ```

---

### Fase 3: Memória + Observability (1 semana)

**Objetivo**: User preferences, métricas e feedback

#### 3.1 User Memory (Reutilizando CoreMemory)

**Decisão Arquitetural**: Reutilizar `CoreMemory` ao invés de nova tabela.

```python
# Armazenar preferências em CoreMemory
await core_memory.set("study_preferences", {
    "areas": ["direito_penal", "direito_constitucional"],
    "nivel": "avancado",
    "preferencias": ["respostas_concisas", "exemplos_questoes"],
    "ultima_duvida": "qualificadoras homicídio"
})
```

- [ ] Schema Pydantic em `src/schemas/study.py`:
  ```python
  class StudyPreferences(BaseModel):
      areas: list[str] = []
      nivel: Literal["iniciante", "intermediario", "avancado"] = "intermediario"
      preferencias: list[str] = []
  ```
- [ ] Comandos: `!minhas-preferencias`, `!limpar-preferencias`

**Arquivos Novos**:
- `src/schemas/study.py`
- `src/memory/study_preferences.py` (wrapper sobre CoreMemory)

#### 3.2 Comando `!report` (Feedback)

- [ ] Implementar `!report [tipo] [comentario]`:
  ```python
  async def handle_report(message: discord.Message):
      # Resolve message ID:
      # 1. If reply, use reference.message_id
      # 2. Else, fetch last bot message in channel
      # 3. Store in feedback_reports table
      # 4. Notify admins
  ```
- [ ] Schema da tabela `feedback_reports`:
  ```sql
  CREATE TABLE feedback_reports (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      message_id BIGINT NOT NULL,
      user_id VARCHAR(255) NOT NULL,
      rating VARCHAR(20) NOT NULL,  -- correto, incorreto, incompleto
      comment TEXT,
      original_sources JSONB,
      created_at TIMESTAMP DEFAULT NOW()
  );
  ```
- [ ] Notificar admins com role "BotAdmin"

**Arquivos Novos**:
- `src/feedback/report_handler.py`
- `src/database/migrations/versions/002_feedback_reports.py`

#### 3.3 Observabilidade

- [ ] Extender `HeartbeatMetric` para métricas RAG:
  ```python
  await heartbeat_metric.log(
      metric_type="rag",
      metric_name="ask_completed",
      value=1,
      metadata={
          "with_source": 1,
          "low_confidence": 0,
          "latency_ms": 2340
      }
  )
  ```
- [ ] Command `/health` para exibir status

**Arquivos Modificados**:
- `src/discord/commands.py`

---

### Fase 4: Otimização + Expansão (Ongoing)

- [ ] Context reduction (resumir sessões > 50 mensagens)
- [ ] Reranking avançado (legislação > doutrina > questões)
- [ ] Expandir base de PDFs

---

## 4. Decisões Arquiteturais Críticas

| Decisão | Opção Escolhida | Justificativa |
|---------|----------------|---------------|
| Tabela documentos legais | Reusar `archival_memories` | Já tem pgvector, menos migrações |
| User preferences | Reusar `CoreMemory` | Exatamente para key-value rápido |
| `!ask` vs `/ask` | Prefix `!ask` | Imediato, sem 1h de sync |
| Intent classification | Zero-shot com exemplos | Mais simples, fine-tuning posterior |
| Study Agent | Novo `AgentType.STUDY` | Comportamento distinto (T=0.0) |

---

## 5. Riscos e Mitigações (Atualizado)

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Ingestão PDFs complexa | Média | 🔴 Alto | Começar com 2-3 PDFs simples, expandir gradualmente |
| Alucinação crítica | Média | 🔴 Alto | CitationValidator + threshold dinâmico |
| `on_message` não registrado | Baixa | 🔴 Alto | Tarefa explícita em Fase 1.3 |
| Custo embeddings OpenAI | Média | 🟡 Médio | Batching de chunks, cache |
| Performance pgvector | Baixa | 🟢 Baixo | Índices HNSW já configurados |

---

## 6. Cronograma

| Fase | Semana | Entregáveis |
|------|--------|-------------|
| Fase 1 | 1-2 | `!ask` + ingestão PDFs + StudyAgent |
| Fase 2 | 3 | Intent detection + SOUL.md dual |
| Fase 3 | 4 | `!report` + preferences |
| Fase 4 | 5+ | Otimizações incrementais |

---

## 7. Checklist de Consenso

- [x] ✅ Arquitetura consistente com código existente
- [x] ✅ Reutilizando tabelas existentes (archival_memories, core_memories)
- [x] ✅ `on_message` handler especificado
- [x] ✅ CitationValidator especificado
- [x] ✅ `!ask` vs `/ask` decidido
- [x] ✅ FR-2 (anti-alucinação) endereçado
- [x] ✅ `out_of_scope` handler especificado
- [x] ✅ Decisões arquiteturais documentadas

---

## 8. Próximos Passos

1. ✅ Plano revisado (v2)
2. ⏭️ Validação final com stakeholders
3. ⏭️ Implementar Fase 1.1 (ingestão PDFs)
4. ⏭️ Implementar Fase 1.2 (StudyAgent + CitationValidator)
5. ⏭️ Implementar Fase 1.3 (on_message + !ask)

---

**Status do Plano**: ✅ Revisado e pronto para implementação
