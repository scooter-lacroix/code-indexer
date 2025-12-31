# Technology Stack

## Core Technologies
- **Programming Language:** Python (3.10+)
- **Metadata Storage:** PostgreSQL (via SQLAlchemy)
- **Primary Search & Indexing:** New internal engine (merging Zoekt and ported features)
- **Local Vector Store:** FAISS (Facebook AI Similarity Search) + sentence-transformers
- **Augmented Search:** Elasticsearch (Enterprise-grade full-text search)
- **Message Broker:** RabbitMQ (via Pika for asynchronous processing)
- **Legacy/Standalone Fallback:** SQLite (Fallback storage), Ripgrep, Ugrep

## Vector Search Components
- **FAISS:** High-performance vector similarity search (IndexFlatIP, IndexIVFFlat)
- **sentence-transformers:** Local embedding generation (BAAI/bge-small-en-v1.5, microsoft/codebert-base, all-MiniLM-L6-v2)
- **numpy:** Numerical computing for vector operations

## Development & Infrastructure
- **Database Migrations:** Alembic
- **Protocol:** Model Context Protocol (MCP)
- **Agent Integration:** Custom CLI (`code-search`), Skills, and Plugins
- **Containerization:** Docker & Docker Compose
- **Build System:** Setuptools (via pyproject.toml)
