# Changelog - Agnaldo

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Clean Code initiative - FASE 1: Critical fixes for security and reliability
- Type hints para todos os comandos do Discord em `src/discord/commands.py`
- FIXED_DATETIME constante em testes para garantir determinismo
- Segurança melhorada com exceções customizadas no código

### Changed
- Atualizada documentação de agentes `.claude/agents/` com melhorias de clareza
- Consistência de métricas de coverage entre documentações

### Fixed
- Uso de `datetime.now(timezone.utc)` em testes substituído por constante fixa
- Inconsistência de threshold de coverage (90% vs 95%) documentalmente alinhada

---

## [0.1.0] - 2026-02-17

### Added - MVP FASE 1

#### User Stories
- **US-001**: Ingestão de PDFs Jurídicos
  - `LegalPDFIngestor` com PyPDF2 para processamento de PDFs
  - Chunking com tiktoken (512-1024 tokens, overlap 128)
  - Embeddings OpenAI text-embedding-3-small
  - Script CLI `scripts/ingest_legal_pdfs.py`

- **US-002**: StudyAgent com RAG Rigoroso
  - `StudyAgent` com temperatura 0.0 para respostas consistentes
  - `CitationValidator` com regex para citações jurídicas
  - Thresholds dinâmicos por categoria:
    - Legislação: ≥ 0.85
    - Doutrina: ≥ 0.75
  - 21 testes unitários para CitationValidator

- **US-003**: Comando !ask e Handler de Mensagens
  - `_handle_ask_command()` em handlers.py
  - `handle_general_message()` para chat livre
  - Rate limiting: 5 req/min por usuário
  - Logging estruturado completo

#### Arquivos Criados (9)
- `src/validators/__init__.py` - Módulo de validators
- `src/validators/citation_validator.py` (8KB) - Validação de citações
- `src/agents/study_agent.py` (14KB) - StudyAgent rigoroso
- `src/knowledge/legal_pdf_ingestor.py` (11KB) - Ingestor de PDFs
- `src/knowledge/__init__.py` - Módulo knowledge
- `src/schemas/knowledge.py` (4.3KB) - Schemas Pydantic
- `tests/test_citation_validator.py` - Testes do validator
- `tests/integration/test_agents/test_study_agent.py` - Testes de integração
- `scripts/ingest_legal_pdfs.py` - Script CLI de ingestão

#### Arquivos Modificados (7)
- `src/discord/handlers.py` - Adicionado handler !ask
- `src/agents/orchestrator.py` - Adicionado StudyAgent
- `src/schemas/agents.py` - Schemas para RAG e StudyAgent
- `tests/conftest.py` - Fixtures para testes de agentes
- `pyproject.toml` - Dependências PyPDF2, tiktoken
- `tests/test_agents/test_orchestrator.py` - Testes do orchestrator
- `tests/integration/test_discord/test_handlers.py` - Testes do handler

#### Testes
- **Total**: 176 testes passando
- **Originais**: 155
- **Novos**: 21 (CitationValidator)

#### Notas
- Arquitetura standalone confirmada como mais adequada pelo arquiteto
- Temperatura 0.0 no StudyAgent garante respostas determinísticas
- Rate limiting previne abuse do comando !ask

---

## [0.0.1] - 2025-XX-XX

### Added
- Initial project setup
- Discord bot integration with Agno framework
- Memory system (Core, Recall, Archival)
- Knowledge graph service
- Multi-agent orchestration
