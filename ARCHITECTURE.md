# Architecture Overview

This document serves as a critical, living template designed to equip agents with a rapid and comprehensive understanding of the codebase's architecture, enabling efficient navigation and effective contribution from day one. Update this document as the codebase evolves.

## 1. Project Structure

This section provides a high-level overview of the project's directory and file structure, categorised by architectural layer or major functional area. It is essential for quickly navigating the codebase, locating relevant files, and understanding the overall organization and separation of concerns.

```text
[Project Root]/
├── src/                          # Main backend code for the bot
│   ├── agents/                   # Multi-agent orchestration and intent routing
│   │   └── orchestrator.py      # Agent orchestration system
│   ├── config/                  # Configuration (env vars and settings)
│   │   └── settings.py          # Application settings
│   ├── context/                 # Context management, reduction and monitoring
│   │   ├── manager.py           # Context manager
│   │   ├── monitor.py           # Context monitoring
│   │   ├── offloading.py        # Context offloading
│   │   └── reducer.py           # Context reduction
│   ├── database/                # ORM models, Supabase client and migrations
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── rls_policies.py      # Row-Level Security policies
│   │   ├── supabase.py          # Supabase client
│   │   └── migrations/          # Database migrations
│   ├── discord/                 # Discord integration (bot, events, commands)
│   │   ├── bot.py               # Main Discord bot
│   │   ├── commands.py          # Slash commands
│   │   ├── events.py            # Discord events
│   │   ├── handlers.py          # Message handlers
│   │   └── rate_limiter.py      # Rate limiting (TokenBucket)
│   ├── intent/                  # Intent classification and routing
│   │   ├── classifier.py        # Intent classifier (SentenceTransformer)
│   │   ├── models.py            # Intent models and categories
│   │   └── router.py            # Intent router
│   ├── knowledge/               # Knowledge graph and semantic search
│   │   └── graph.py             # Knowledge graph (nodes/edges)
│   ├── memory/                  # Layered memory (core, recall, archival)
│   │   ├── core.py              # Core memory (long-term)
│   │   ├── recall.py            # Recall memory (semantic search)
│   │   └── archival.py          # Archival memory
│   ├── schemas/                 # Pydantic schemas
│   │   ├── agents.py            # Agent schemas
│   │   ├── context.py           # Context schemas
│   │   ├── discord.py           # Discord schemas
│   │   └── memory.py            # Memory schemas
│   ├── templates/               # Documentation/memory templates
│   │   ├── AGENTS.md            # Agent definitions
│   │   ├── HEARTBEAT.md         # Heartbeat configuration
│   │   ├── IDENTITY.md          # Bot identity
│   │   ├── MEMORY.md            # Memory configuration
│   │   ├── SOUL.md              # Bot personality/soul
│   │   └── TOOLS.md             # Available tools
│   ├── tools/                   # Auxiliary tools
│   │   └── osint/               # OSINT tools
│   ├── utils/                   # Logging and general utilities
│   │   ├── error_handlers.py    # Error handling
│   │   └── logger.py            # Logging configuration
│   ├── exceptions.py             # Custom exceptions
│   └── main.py                  # System entry point
├── agnaldo/                     # Root Python package
├── tests/                       # Unit, integration and e2e tests
│   ├── e2e/                     # End-to-end tests
│   ├── fixtures/                 # Test fixtures
│   ├── integration/              # Integration tests
│   └── unit/                     # Unit tests
├── docs/                        # Technical documentation
├── .github/                     # GitHub Actions CI/CD
├── .env.example                 # Environment variables template
├── pyproject.toml               # Dependencies (uv)
├── README.md                    # Overview and quick start
├── PRD.md                       # Product Requirements Document
└── ARCHITECTURE.md              # This document
```

## 2. High-Level System Diagram

Provide a simple block diagram (e.g., a C4 Model Level 1: System Context diagram, or a basic component diagram) or a clear text-based description of the major components and their interactions. Focus on how data flows, services communicate, and key architectural boundaries.

```bash
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Discord   │────▶│  Discord Bot │────▶│ Message Handler │────▶│ Intent Classifier│
│   Client    │     │  (discord.py)│     │  (handlers.py)  │     │(SentenceTransform)│
└─────────────┘     └──────────────┘     └─────────────────┘     └─────────────────┘
                                                                              │
                                                                              ▼
                      ┌─────────────────────────────────────────────────────────────┐
                      │                    Agent Orchestrator                      │
                      │  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌───────┐│
                      │  │Conversational│ │   Knowledge  │ │   Memory  │ │ Graph ││
                      │  │    Agent     │ │    Agent     │ │   Agent   │ │ Agent ││
                      │  └─────────────┘ └──────────────┘ └────────────┘ └───────┘│
                      └─────────────────────────────────────────────────────────────┘
                                             │
                    ┌──────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
          ┌──────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
          │  Recall Memory   │    │   Knowledge Graph    │    │  OpenAI API     │
          │ (pgvector search)│    │   (nodes/edges)     │    │(LLM + Embeddings)│
          └──────────────────┘    └──────────────────────┘    └─────────────────┘
                    │
                    ▼
          ┌──────────────────────────────────────┐
          │      PostgreSQL (Supabase) + pgvector │
          │  - users, sessions, messages          │
          │  - core_memories, recall_memories    │
          │  - knowledge_nodes, knowledge_edges   │
          └──────────────────────────────────────┘
```

## 3. Core Components

(List and briefly describe the main components of the system. For each, include its primary responsibility and key technologies used.)

### 3.1. Frontend

Name: Discord Client Interface

Description: The main user interface for interacting with the system, allowing users to execute slash commands (`/memory add`, `/memory recall`, `/graph add_node`, etc.), send natural language messages, and receive AI-powered responses from the bot in Discord channels and DMs.

Technologies: Discord Client (Web/Desktop/Mobile) + Discord Interactions API (discord.py)

Deployment: Hosted by Discord platform

### 3.2. Backend Services

#### 3.2.1. Discord Bot Service

Name: Discord Bot Service

Description: Handles Discord event ingestion, slash command registration and execution, rate limiting, and the message processing pipeline entry point. Manages bot lifecycle, connection to Discord Gateway, and command tree synchronization.

Technologies: Python (asyncio), discord.py, loguru

Deployment: Python service process (container/VM compatible)

#### 3.2.2. Intent Classification Service

Name: Intent Classification Service

Description: Classifies user messages into categories (greeting, farewell, knowledge_query, memory_store, memory_retrieve, graph_query, etc.) using a local SentenceTransformer model to determine the appropriate agent for response routing.

Technologies: Python, sentence-transformers (all-MiniLM-L6-v2), NumPy

Deployment: Embedded in Python service process

#### 3.2.3. Agent Orchestration Service

Name: Agent Orchestration Service

Description: Routes intents to specialized agents (conversational, knowledge, memory, graph), enriches responses with memory context, performs semantic retrieval from recall memory, and manages knowledge graph operations. Coordinates multi-agent communication and maintains conversation context.

Technologies: Python, Agno (multi-agent framework), OpenAI SDK

Deployment: Python service process

#### 3.2.4. Memory Management Service

Name: Memory Management Service

Description: Implements a layered memory architecture with three tiers: (1) Core Memory for critical long-term information, (2) Recall Memory for semantic search with pgvector, and (3) Archival Memory for compressed historical data. Handles embedding generation and similarity search.

Technologies: Python, OpenAI SDK (text-embedding-3-small), asyncpg, pgvector

Deployment: Python service process with PostgreSQL backend

#### 3.2.5. Knowledge Graph Service

Name: Knowledge Graph Service

Description: Manages a graph database of entities and relationships for semantic knowledge representation. Supports adding nodes (concepts, entities), edges (relationships), and querying the graph with similarity search.

Technologies: Python, OpenAI SDK, PostgreSQL with custom graph queries

Deployment: Python service process with PostgreSQL backend

## 4. Data Stores

(List and describe the databases and other persistent storage solutions used.)

### 4.1. Primary Application Database

Name: Primary Application Database

Type: PostgreSQL (Supabase) + pgvector

Purpose: Stores user/session/message data, memory tiers (core, recall, archival), knowledge graph entities/relations, and operational metrics. Provides vector similarity search capabilities through pgvector extension.

Key Schemas/Collections: users, sessions, messages, core_memories, recall_memories (with vector embeddings), archival_memories, knowledge_nodes, knowledge_edges, heartbeat_metrics, context_metrics

### 4.2. Runtime Cache

Name: Runtime Cache

Type: In-memory Python dict

Purpose: Used for caching frequently accessed data, rate limiter token buckets, and reducing latency in context/memory access during bot runtime. Not persisted across restarts.

## 5. External Integrations / APIs

(List any third-party services or external APIs the system interacts with.)

### Service Name 1: Discord API

Purpose: Bot connectivity, events (message create, interaction create), message exchange, and slash command interactions.

Integration Method: SDK (discord.py)

### Service Name 2: OpenAI API

Purpose: LLM responses (GPT-4o) for conversational agent and embedding generation (text-embedding-3-small) for semantic memory/graph operations.

Integration Method: SDK (openai Python)

### Service Name 3: Supabase

Purpose: Managed PostgreSQL access, authentication, and service-level database operations.

Integration Method: REST/SDK (supabase-py) + direct PostgreSQL connections (asyncpg)

### Service Name 4: Hugging Face Hub

Purpose: Local embedding model for intent classification (SentenceTransformer).

Integration Method: Direct download (sentence-transformers library)

## 6. Deployment & Infrastructure

Cloud Provider: Supabase (database) + GitHub-hosted runners for CI

Key Services Used: PostgreSQL, pgvector, GitHub Actions, Codecov

CI/CD Pipeline: GitHub Actions (`.github/workflows/test.yml`) - runs pytest with coverage

Monitoring & Logging: Loguru logs + context/heartbeat metrics in database

## 7. Security Considerations

(Highlight any critical security aspects, authentication mechanisms, or data encryption practices.)

Authentication: API Keys and bot tokens via environment variables

Authorization: Row-Level Security (RLS) policies for multi-tenant data isolation + role checks for sensitive operations

Data Encryption: TLS in transit (API/database endpoints); encryption at rest managed by Supabase infrastructure

Key Security Tools/Practices: Rate limiting (TokenBucket algorithm), RLS policies, dependency vulnerability scanning in CI (`uv pip check`, `pip-audit`)

## 8. Development & Testing Environment

Local Setup Instructions: `uv sync` → configure `.env` from `.env.example` → `uv run python src/main.py`

Testing Frameworks: Pytest, pytest-asyncio, pytest-cov, pytest-mock

Code Quality Tools: Ruff (linting), Black (formatting), MyPy (type checking)

## 9. Future Considerations / Roadmap

(Briefly note any known architectural debts, planned major changes, or significant future features that might impact the architecture.)

- Add RAG (Retrieval-Augmented Generation) for knowledge base queries
- Implement context reduction for long conversations
- Add user preference memory persistence
- Expand intent classifier with more categories
- Add support for more Discord slash commands
- Implement feedback/reporting system for answer quality

## 10. Project Identification

Project Name: Agnaldo

Repository URL: <https://github.com/prof-ramos/agnaldo.git>

Primary Contact/Team: prof-ramos (owner) / Agnaldo maintainers

Date of Last Update: 2026-02-17

## 11. Glossary / Acronyms

Define any project-specific terms or acronyms.

RLS: Row-Level Security - PostgreSQL security feature for multi-tenant data isolation.

pgvector: PostgreSQL extension for vector embeddings and similarity search.

HNSW: Approximate nearest-neighbor index method used for vector search in pgvector.

Intent Classifier: Component that classifies user messages using SentenceTransformer to route agent execution.

Agent Orchestrator: Central coordinator that manages multiple specialized agents (conversational, knowledge, memory, graph) and routes intents accordingly.

Recall Memory: Memory tier that uses semantic vector search to retrieve relevant past interactions.

Core Memory: Memory tier for critical long-term information that should always be remembered.
