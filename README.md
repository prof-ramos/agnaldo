# Agnaldo - Discord Bot with Knowledge Graph

A sophisticated Discord bot powered by Agno AI framework, featuring multi-agent orchestration, knowledge graph capabilities, and three-tier memory management using Supabase with pgvector.

## Features

### 🤖 Multi-Agent System
- **Conversational Agent**: Natural chat interactions with personality
- **Knowledge Agent**: RAG-powered knowledge base queries
- **Memory Agent**: Multi-tier memory management
- **Graph Agent**: Knowledge graph operations and reasoning

### 🧠 Three-Tier Memory System
1. **Core Memory**: Fast key-value storage for important facts
2. **Recall Memory**: Semantic search for recent conversations
3. **Archival Memory**: Long-term compressed storage

### 🕸️ Knowledge Graph
- Semantic node and edge creation
- Vector-based similarity search
- Path finding and graph traversal
- Relationship tracking between concepts

### 📊 Context Management
- Automatic token tracking
- Intelligent context reduction
- Offloading to cache
- Metrics dashboard

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Discord                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ IntentClassifier │
            └────────┬─────────┘
                     │
                     ▼
      ┌──────────────────────────────┐
      │    Agent Orchestrator        │
      │  ┌─────────────────────────┐ │
      │  │  Agent Factory Pattern   │ │
      │  └─────────────────────────┘ │
      │                               │
      │ ┌─────┐ ┌──────┐ ┌───┐ ┌───┐│
      │ │Conv │ │Know ││Mem││Grp││
      │ └─────┘ └──────┘ └───┘ └───┘│
      └───────────┬───────────────────┘
                  │
      ┌───────────┴───────────────────────┐
      │      Memory Tiers                  │
      │  ┌─────┐ ┌──────┐ ┌─────────┐   │
      │  │Core ││Recall││Archival │   │
      │  └─────┘ └──────┘ └─────────┘   │
      └───────────┬───────────────────────┘
                  │
                  ▼
      ┌─────────────────────────────────────┐
      │   Supabase + PostgreSQL + pgvector  │
      └─────────────────────────────────────┘
```

## Installation

### Prerequisites
- Python 3.10+
- PostgreSQL with pgvector extension
- Supabase account (recommended)
- OpenAI API key
- Discord bot token

### Setup with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/prof-ramos/agnaldo.git
cd agnaldo

# Install uv
pip install uv

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

### Configuration

Edit `.env` with your credentials:

```bash
# Discord
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_DB_URL=postgresql://...

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Database Setup

```bash
# Run migrations (if using Alembic)
# Or execute the SQL schema in src/database/schema.sql
```

Required tables:
- `users` - User management
- `sessions` - Discord sessions
- `messages` - Conversation history
- `core_memories` - Fast key-value storage
- `recall_memories` - Semantic search memories
- `archival_memories` - Long-term storage
- `knowledge_nodes` - Graph nodes with embeddings
- `knowledge_edges` - Graph relationships
- `agent_metrics` - Agent performance metrics
- `context_metrics` - Context tracking

## Usage

### Running the Bot

```bash
# Development
uv run python src/main.py

# Production
uv run python src/main.py
```

### Discord Commands

#### Basic Commands
- `/ping` - Check bot responsiveness
- `/help` - Show available commands
- `/status` - Show bot status and metrics
- `/sync` - Sync commands (Admin only)

#### Memory Commands
- `/memory add <key> <value> [importance]` - Store a fact in core memory
- `/memory recall <query> [limit]` - Search memories semantically

#### Knowledge Graph Commands
- `/graph add_node <label> [node_type]` - Add a node to the graph
- `/graph add_edge <source> <target> <edge_type> [weight]` - Add a relationship
- `/graph query <search> [limit]` - Search the knowledge graph

## Development

### Project Structure

```
agnaldo/
├── src/
│   ├── agents/          # Multi-agent orchestration
│   │   └── orchestrator.py
│   ├── config/          # Configuration management
│   │   └── settings.py
│   ├── context/         # Context management
│   │   ├── manager.py
│   │   ├── reducer.py
│   │   ├── offloading.py
│   │   └── monitor.py
│   ├── database/        # Database layer
│   │   ├── models.py
│   │   ├── supabase.py
│   │   └── migrations/
│   ├── discord/         # Discord bot
│   │   ├── bot.py
│   │   ├── commands.py
│   │   ├── events.py
│   │   ├── handlers.py
│   │   └── rate_limiter.py
│   ├── intent/          # Intent classification
│   │   ├── classifier.py
│   │   └── models.py
│   ├── knowledge/       # Knowledge graph
│   │   └── graph.py
│   ├── memory/          # Memory tiers
│   │   ├── core.py
│   │   ├── recall.py
│   │   └── archival.py
│   ├── schemas/         # Pydantic schemas
│   ├── utils/           # Utilities
│   │   ├── error_handlers.py
│   │   └── logger.py
│   ├── exceptions.py    # Custom exceptions
│   └── main.py          # Entry point
├── tests/               # Integration tests
├── SOUL.md             # Bot personality
├── .env.example        # Environment template
├── pyproject.toml      # Project configuration
└── README.md           # This file
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/test_memory.py -v
```

### Type Checking

```bash
uv run mypy src/
```

## API Documentation

### Agent Orchestrator

```python
from src.agents.orchestrator import get_orchestrator

orchestrator = await get_orchestrator()

async for chunk in orchestrator.route_and_process(
    message="Hello!",
    context={"username": "user"},
    user_id="123",
    db_pool=db_pool,
):
    print(chunk)
```

### Memory Tiers

```python
from src.memory.core import CoreMemory
from src.memory.recall import RecallMemory
from src.memory.archival import ArchivalMemory

# Core Memory - fast key-value
core = CoreMemory(user_id="123", repository=db_pool)
await core.add("preference", "dark_mode", importance=0.8)
value = await core.get("preference")

# Recall Memory - semantic search
recall = RecallMemory(user_id="123")
results = await recall.search("What did I say about Python?")

# Archival Memory - long-term storage
archival = ArchivalMemory(user_id="123", repository=db_pool)
await archival.add("Important conversation summary", source="discord")
```

### Knowledge Graph

```python
from src.knowledge.graph import KnowledgeGraph

graph = KnowledgeGraph(user_id="123", repository=db_pool)

# Add nodes
python_node = await graph.add_node("Python", node_type="language")
discord_node = await graph.add_node("Discord", node_type="api")

# Add relationship
await graph.add_edge(
    source_id=python_node.id,
    target_id=discord_node.id,
    edge_type="used_with",
    weight=0.9
)

# Semantic search
results = await graph.search_nodes("programming languages", limit=5)

# Path finding
path = await graph.find_path(python_node.id, discord_node.id)
```

## Personality (SOUL.md)

The bot's personality is defined in `SOUL.md` and includes:
- Direct and objective communication
- Concise responses (max 3 paragraphs)
- Markdown for code blocks
- Threads for long conversations
- Portuguese language support

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- **Agno AI Framework** - Multi-agent orchestration
- **OpenClaw** - AI agent patterns and techniques
- **Discord.py** - Discord API wrapper
- **Supabase** - Backend infrastructure
- **OpenAI** - LLM and embedding services
