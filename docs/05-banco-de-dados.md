# Banco de Dados

## O que o código espera (estado atual)

Os módulos `src/memory/*` e `src/knowledge/graph.py` usam SQL direto com:

- `user_id` como texto (normalmente o Discord ID do usuário).
- `pgvector` com `vector(1536)` e operadores como `<=>`.

Existe uma migration Alembic (`src/database/migrations/versions/001_initial.py`) que cria tabelas com `user_id` como `UUID` e embeddings como `ARRAY(float)`. Isso não bate com o SQL usado em runtime pelos módulos de memória/grafo.

Aviso crítico:

- Se você quer usar as classes atuais (`CoreMemory`, `RecallMemory`, `ArchivalMemory`, `KnowledgeGraph`) sem refatorar SQL, crie as tabelas com `user_id TEXT` e `embedding vector(1536)`.
- Se você quer o schema Alembic com RLS e `UUID`, você vai precisar adaptar as classes de memória/grafo para o novo schema.
- Não misture os dois modelos sem migração de compatibilidade explícita, ou o bot vai falhar em runtime.

## Pool `asyncpg` (obrigatório para slash commands)

Os slash commands usam `bot.db_pool` e fazem `async with db_pool.acquire()`.

Hoje, o `src/main.py` não cria um pool. Você precisa criar e setar em `bot.db_pool` em algum ponto do startup.

Exemplo de inicializacao (conceitual):

```python
import asyncpg
from src.config.settings import get_settings

settings = get_settings()
db_pool = await asyncpg.create_pool(dsn=settings.SUPABASE_DB_URL, min_size=1, max_size=10)
bot.db_pool = db_pool
```

## DDL recomendado (compatibilidade com o código)

Use este DDL como base para um Postgres com `pgvector`.

Observações:

- Ajuste `lists` do IVFFlat conforme volume.
- Em Supabase, verifique permissão para `CREATE EXTENSION vector` e `gen_random_uuid()` (extensões).

```sql
-- Extensoes
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Core memory
CREATE TABLE IF NOT EXISTS core_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  importance FLOAT NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
  metadata JSONB NOT NULL DEFAULT '{}',
  access_count INTEGER NOT NULL DEFAULT 0,
  last_accessed TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, key)
);

CREATE INDEX IF NOT EXISTS core_memories_user_id_idx ON core_memories(user_id);
CREATE INDEX IF NOT EXISTS core_memories_importance_idx ON core_memories(importance);

-- Recall memory (semantic)
CREATE TABLE IF NOT EXISTS recall_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536) NOT NULL,
  importance FLOAT NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
  access_count INTEGER NOT NULL DEFAULT 0,
  last_accessed TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS recall_memories_user_id_idx ON recall_memories(user_id);
CREATE INDEX IF NOT EXISTS recall_memories_importance_idx ON recall_memories(importance);
CREATE INDEX IF NOT EXISTS recall_memories_embedding_idx
  ON recall_memories
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Archival memory
CREATE TABLE IF NOT EXISTS archival_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  content TEXT NOT NULL,
  source TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  session_id TEXT,
  compressed BOOLEAN NOT NULL DEFAULT FALSE,
  compressed_into_id UUID REFERENCES archival_memories(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS archival_memories_user_id_idx ON archival_memories(user_id);
CREATE INDEX IF NOT EXISTS archival_memories_source_idx ON archival_memories(source);
CREATE INDEX IF NOT EXISTS archival_memories_session_id_idx ON archival_memories(session_id);
CREATE INDEX IF NOT EXISTS archival_memories_metadata_idx ON archival_memories USING gin (metadata);
CREATE INDEX IF NOT EXISTS archival_memories_compressed_idx ON archival_memories(compressed);

-- Knowledge graph nodes/edges
CREATE TABLE IF NOT EXISTS knowledge_nodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  label TEXT NOT NULL,
  node_type TEXT,
  properties JSONB NOT NULL DEFAULT '{}',
  embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS knowledge_nodes_user_id_idx ON knowledge_nodes(user_id);
CREATE INDEX IF NOT EXISTS knowledge_nodes_node_type_idx ON knowledge_nodes(node_type);
CREATE INDEX IF NOT EXISTS knowledge_nodes_embedding_idx
  ON knowledge_nodes
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE TABLE IF NOT EXISTS knowledge_edges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
  target_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
  edge_type TEXT NOT NULL,
  weight FLOAT NOT NULL DEFAULT 1.0,
  properties JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS knowledge_edges_source_idx ON knowledge_edges(source_id);
CREATE INDEX IF NOT EXISTS knowledge_edges_target_idx ON knowledge_edges(target_id);
CREATE INDEX IF NOT EXISTS knowledge_edges_type_idx ON knowledge_edges(edge_type);
```

## Supabase e RLS

Se você usar Supabase com RLS, avalie com cuidado:

- `SUPABASE_SERVICE_ROLE_KEY` tem acesso total e deve ficar restrito ao backend.
- Para bots, o caminho mais simples e operar com service role em um ambiente controlado.
