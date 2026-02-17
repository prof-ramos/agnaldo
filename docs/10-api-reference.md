# Referência de API - Agnaldo

## Visão Geral

Agnaldo é um bot Discord inteligente construído com o framework Agno AI, implementando orquestração multi-agente, memória de longo prazo em três camadas e grafo de conhecimento semântico.

---

## 1. AgentOrchestrator

### Classe Principal

```python
from src.agents.orchestrator import AgentOrchestrator, get_orchestrator
```

### Métodos

#### `get_orchestrator()`

Obtém a instância global do orquestrador (singleton).

```python
orchestrator = await get_orchestrator(
    personality_instructions=["Você é o Agnaldo..."],
    memory_config=MemoryTierConfig()
)
```

#### `route_and_process(message, context, user_id, db_pool, session_id)`

Roteia mensagem para o agente apropriado e retorna resposta streaming.

**Parâmetros:**
- `message: str` - Mensagem do usuário
- `context: dict[str, Any] | None` - Contexto Discord (username, guild_name, etc)
- `user_id: str | None` - ID do usuário para isolamento de memória
- `db_pool` - Pool de conexão asyncpg
- `session_id: str | None` - ID da sessão para continuidade de aprendizado

**Retorno:**
- `AsyncIterator[str]` - Chunks de resposta

```python
async for chunk in orchestrator.route_and_process(
    message="Qual o meu nome?",
    context={"username": "João"},
    user_id="123456789",
    db_pool=db_pool,
    session_id="user_123_session_abc"
):
    print(chunk)
```

#### `request_approval(action_id, action_description, user_id, channel_id, metadata)`

Solicita aprovação humana para ações críticas (human-in-the-loop).

```python
request_id = await orchestrator.request_approval(
    action_id="delete_memory",
    action_description="Deletar todas as memórias do usuário",
    user_id="123456789",
    channel_id="987654321",
    metadata={"target_user": "987654321"}
)
```

#### `check_approval(request_id)`

Verifica status de aprovação.

**Retorno:** `'pending' | 'approved' | 'denied' | 'timeout' | 'not_found'`

```python
status = await orchestrator.check_approval(request_id)
if status == "approved":
    # Executar ação
    pass
```

#### `approve_action(request_id, approved)`

Aprova ou nega uma ação pendente.

```python
success = await orchestrator.approve_action(request_id, approved=True)
```

#### `get_stats()`

Retorna estatísticas do orquestrador e agentes.

```python
stats = await orchestrator.get_stats()
# {
#   "orchestrator_state": "running",
#   "total_agents": 5,
#   "agents": [...]
# }
```

---

## 2. Sistema de Memória

### Core Memory

Memória rápida de alto valor (máx 100 itens, LRU ponderado).

```python
from src.memory.core import CoreMemory

core = CoreMemory(user_id="123", db_pool=pool)
await core.add("preferencia_linguagem", "Python", importance=0.9)
value = await core.get("preferencia_linguagem")
```

### Recall Memory

Memória de médio prazo com busca semântica (pgvector).

```python
from src.memory.recall import RecallMemory

recall = RecallMemory(user_id="123", db_pool=pool)
await recall.add("Usuário prefere respostas curtas", importance=0.7)
results = await recall.search("preferências", limit=5, threshold=0.6)
```

### Archival Memory

Armazenamento de longo prazo comprimido com metadados JSONB.

```python
from src.memory.archival import ArchivalMemory

archival = ArchivalMemory(user_id="123", db_pool=pool)
await archival.add(
    content="Conversa sobre projeto X",
    source="discord",
    metadata={"project": "X", "priority": "high"}
)
results = await archival.search_by_metadata({"project": "X"})
```

---

## 3. Grafo de Conhecimento

```python
from src.knowledge.graph import KnowledgeGraph

graph = KnowledgeGraph(user_id="123", db_pool=pool)

# Adicionar nó
node = await graph.add_node("Python", node_type="language")

# Adicionar aresta
await graph.add_edge(source_id, target_id, "used_for", weight=1.5)

# Buscar nós
results = await graph.search_nodes("programação", limit=5)
```

---

## 4. Discord Bot

### Comandos Slash

| Comando | Descrição |
|---------|-----------|
| `/ping` | Verifica latência do bot |
| `/help` | Mostra comandos disponíveis |
| `/status` | Status do sistema |
| `/chat` | Conversação natural via agentes |
| `/memory add` | Armazena fato na memória core |
| `/memory recall` | Busca memórias semanticamente |
| `/graph add_node` | Adiciona nó ao grafo |
| `/graph add_edge` | Adiciona relacionamento |
| `/graph query` | Busca no grafo |

### Eventos

- `on_message` - Processa mensagens naturais via agentes
- `on_guild_join` - Log ao entrar em servidor
- `on_command_error` - Tratamento de erros

---

## 5. Rate Limiting

```python
from src.discord.rate_limiter import RateLimiter

limiter = RateLimiter()
await limiter.acquire(channel_id="123")
# ... executar ação ...
```

**Configuração:**
- `RATE_LIMIT_GLOBAL`: 50 req/s (padrão)
- `RATE_LIMIT_PER_CHANNEL`: 5 req/s (padrão)

---

## 6. Classificação de Intents

```python
from src.intent.classifier import IntentClassifier

classifier = IntentClassifier()
await classifier.initialize()

result = await classifier.classify("Como fazer um loop em Python?")
# IntentResult(intent=IntentCategory.KNOWLEDGE_QUERY, confidence=0.85)
```

**Categorias:**
- `KNOWLEDGE_QUERY` - Perguntas sobre conhecimento
- `MEMORY_STORE` - Armazenar memória
- `MEMORY_RETRIEVE` - Recuperar memória
- `GRAPH_QUERY` - Consultar grafo
- `GREETING` - Saudações
- `HELP` - Ajuda
- `STATUS` - Status

---

## 7. Exceções

```python
from src.exceptions import (
    AgnaldoError,
    AgentCommunicationError,
    DatabaseError,
    MemoryServiceError,
)
```

---

## 8. Configuração

Variáveis de ambiente obrigatórias:

```bash
DISCORD_BOT_TOKEN=xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_DB_URL=postgresql://xxx
SUPABASE_SERVICE_ROLE_KEY=xxx
OPENAI_API_KEY=sk-xxx
```

Opcionais:

```bash
ENVIRONMENT=dev
LOG_LEVEL=INFO
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RATE_LIMIT_GLOBAL=50
RATE_LIMIT_PER_CHANNEL=5
```

---

## Changelog

### v0.2.0 (17/02/2026)
- ✅ Conectado `on_message` ao AgentOrchestrator
- ✅ Inicializado pool asyncpg corretamente
- ✅ Adicionado comando `/chat` para conversação natural
- ✅ Implementado `session_id` para aprendizado contínuo
- ✅ Adicionado human-in-the-loop com `request_approval()`
- ✅ Criado agente Core Memory dedicado
- ✅ Corrigidos erros de LSP no orchestrator
