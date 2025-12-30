# Technology Stack

## Core Technologies
- **Programming Language:** Python (3.10+)
- **Metadata Storage:** PostgreSQL (via SQLAlchemy)
- **Primary Search & Indexing:** New internal engine (merging Zoekt and ported features)
- **Augmented Search:** Elasticsearch (Enterprise-grade full-text search)
- **Message Broker:** RabbitMQ (via Pika for asynchronous processing)
- **Legacy/Standalone Fallback:** SQLite (Fallback storage), Ripgrep, Ugrep

## Development & Infrastructure
- **Database Migrations:** Alembic
- **Protocol:** Model Context Protocol (MCP)
- **Containerization:** Docker & Docker Compose
- **Build System:** Setuptools (via pyproject.toml)
