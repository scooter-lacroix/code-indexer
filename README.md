# Code Indexer (MCP) - Complete Edition

<div align="center">

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Performance](https://img.shields.io/badge/Performance-Enterprise_Grade-brightgreen)](CHANGELOG.md)
[![Version](https://img.shields.io/badge/Version-3.0.0-blue)](CHANGELOG.md)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2BElasticsearch-orange)](docs/ARCHITECTURE.md)

**🚀 Large Scale Code Analysis Platform with Hybrid Database Architecture**

*Advanced MCP server with PostgreSQL metadata storage, Elasticsearch search, and comprehensive version tracking*

</div>



## 🚀 Unified Edition - v4.0.0

This version introduces the **Unified Core Engine**, a next-generation search and indexing architecture that seamlessly blends semantic understanding with traditional code search:

### 🌟 **Unified Core Engine**
- **✅ Local Vector Search** - FAISS-based semantic search with zero cloud dependencies, zero cost, and full privacy
- **✅ Hybrid Intelligence** - Intelligently routes queries between Local Vector (Semantic), Zoekt (Regex/Symbolic), and Elasticsearch
- **✅ Semantic Search & Reranking** - Deep understanding of code intent with automatic reranking for high precision
- **✅ Web Search Integration** - Optional capability to augment code search with web results
- **✅ Standalone Power** - Operates efficiently without external databases (PostgreSQL/Elasticsearch) for many use cases
- **✅ Dual-Mode Architecture** - Supports both "Core Engine" (Vector-first) and "Legacy" (ES/PG) backends simultaneously

### 🏗️ **Architecture Transformation**
- **✅ Unified Router** - Centralized dispatch for all search and indexing operations.
- **✅ PostgreSQL Integration** - Robust metadata storage with ACID compliance
- **✅ Elasticsearch Integration** - High-performance full-text search capabilities
- **✅ Hybrid Database Architecture** - Best of both worlds for different data types
- **✅ Version Tracking System** - Complete file change history with diffs
- **✅ Real-time Indexing** - RabbitMQ-based async processing
- **✅ Cross-Platform Compatibility** - Robust path handling for all environments

### 📊 **Migration Achievements**
- **✅ Zero Data Loss** - Complete ETL migration from SQLite
- **✅ Backward Compatibility** - Dual-write/read strategy during transition
- **✅ Performance Gains** - 10x faster search with Elasticsearch & Core Engine
- **✅ Scalability** - Enterprise-grade database backends
- **✅ Version Control** - Full file history tracking with PostgreSQL
- **✅ Real-time Updates** - Instant search index updates

### 🛠️ **New Features**
1. **Local Vector Store** - FAISS + sentence-transformers for zero-cost semantic search (BAAI/bge-small-en-v1.5 default)
2. **Unified Core Engine** - Semantic search, Reranking, Web Search
3. **File Version Tracking** - Complete change history with diffs
4. **PostgreSQL Metadata** - Structured data with relationships
5. **Elasticsearch Search** - Advanced full-text search capabilities
6. **Real-time Indexing** - RabbitMQ message queue processing
7. **ETL Migration Tools** - Seamless data migration utilities
8. **Database Migrations** - Alembic-based schema management
9. **Backup & Recovery** - Comprehensive backup strategies
10. **Monitoring & Logging** - Enterprise-grade observability

### 📋 **Verified Functionality**
- **✅ Unified Search** - Semantic + Regex + Web search capabilities
- **✅ File Operations** - Create, modify, delete with full tracking
- **✅ Search Capabilities** - Basic, advanced, and pattern-based search
- **✅ Version History** - Complete file change tracking and retrieval
- **✅ Database Integration** - PostgreSQL + Elasticsearch + Core Vector Store working seamlessly
- **✅ Migration Tools** - ETL scripts for data migration
- **✅ Backup Systems** - Automated backup and recovery procedures

*See [CHANGELOG.md](CHANGELOG.md) for migration details and [docs/TOOLS_LIST.md](docs/TOOLS_LIST.md) for complete tool documentation.*

---

## What is Code Indexer?

Code Indexer is a specialized MCP server that provides intelligent code indexing and analysis capabilities. It enables Large Language Models to interact with your code repositories, offering real-time insights and navigation through complex codebases.

This server integrates with the [Model Context Protocol](https://modelcontextprotocol.io) (MCP), a standardized way for AI models to interact with external tools and data sources.

## Key Features

### 🚀 Performance & Optimization
- **Incremental Indexing**: Only processes changed files, reducing re-indexing time by 90%+
- **Parallel Processing**: 4x faster indexing with multi-core support
- **Memory Optimization**: 70% memory reduction with lazy loading and intelligent caching
- **High-Performance Search**: 10x faster searches with enterprise-grade tools (Zoekt, ripgrep, ugrep)
- **Smart Filtering**: Advanced gitignore integration and size-based filtering

### 🔍 Advanced Search & Analysis
- **Local Semantic Search**: FAISS-based vector search with zero cloud dependencies (p50 < 20ms after model loaded)
- **Async Search**: Non-blocking search operations with real-time progress tracking
- **Multi-Pattern Search**: Concurrent search across multiple patterns with scoped results
- **Intelligent Caching**: 90% faster repeated searches with LRU cache
- **Fuzzy Search**: Native fuzzy matching with safety checks
- **Search Result Pagination**: Efficient handling of large result sets

### 🛠️ Complete Feature Set
- **Progress Tracking**: Real-time progress events with cancellation support
- **Performance Monitoring**: Comprehensive metrics and Prometheus export
- **Memory Profiling**: Real-time memory usage monitoring and limits
- **Configurable Settings**: YAML-based configuration with per-project overrides
- **Storage Backends**: SQLite and trie-based optimized storage

### 🔧 Plug and Play Experience
- **MCP Tools**: 9 consolidated mega-tools for code analysis and management (replacing 50+ individual tools)
- **Action-Based Routing**: Each mega-tool supports multiple actions for streamlined operations
- **Background Cleanup**: Automatic cache management and garbage collection
- **Error Recovery**: Graceful handling of failures with automatic fallbacks
- **Extensible Architecture**: Pluggable storage and search backends

## Supported File Types

The server supports multiple programming languages and file extensions including:

- Python (.py)
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx, .mjs, .cjs)
- Frontend Frameworks (.vue, .svelte, .astro)
- Java (.java)
- C/C++ (.c, .cpp, .h, .hpp)
- C# (.cs)
- Go (.go)
- Ruby (.rb)
- PHP (.php)
- Swift (.swift)
- Kotlin (.kt)
- Rust (.rs)
- Scala (.scala)
- Shell scripts (.sh, .bash)
- Zig (.zig)
- Web files (.html, .css, .scss, .less, .sass, .stylus, .styl)
- Template engines (.hbs, .handlebars, .ejs, .pug)
- **Database & SQL**:
  - SQL files (.sql, .ddl, .dml)
  - Database-specific (.mysql, .postgresql, .psql, .sqlite, .mssql, .oracle, .ora, .db2)
  - Database objects (.proc, .procedure, .func, .function, .view, .trigger, .index)
  - Migration & tools (.migration, .seed, .fixture, .schema, .liquibase, .flyway)
  - NoSQL & modern (.cql, .cypher, .sparql, .gql)
- Documentation/Config (.md, .mdx, .json, .xml, .yml, .yaml)

## 📦 Installation & Setup

### 🚀 **Quick Start**

**For immediate use with AI applications:**
```bash
uvx git+https://github.com/scooter-lacroix/code-indexer.git
```

**For package installation:**
```bash
uv add code-index-mcp
# or
pip install code-index-mcp
```

**For local vector search support (recommended):**
```bash
# Install FAISS and sentence-transformers dependencies
uv pip install 'faiss-cpu>=1.7.4' 'sentence-transformers>=2.2.0' 'numpy>=1.24.0'
```

### 🏗️ **Comprehensive Setup (PostgreSQL + Elasticsearch)**

**1. Database Setup:**
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or use convenience script
python run.py start-dev-dbs
```

**2. Environment Configuration:**
```bash
# Set environment variables
export DAL_BACKEND_TYPE=postgresql_elasticsearch_only

# Local Vector Store Configuration (optional, has defaults)
export LOCAL_VECTOR_MODEL=BAAI/bge-small-en-v1.5  # Options: BAAI/bge-small-en-v1.5, microsoft/codebert-base, all-MiniLM-L6-v2
export FAISS_INDEX_THRESHOLD=100000  # Switch to IVFFlat after this many vectors
export FAISS_INDEX_PATH=./faiss_index  # Where to store the index

# PostgreSQL Configuration
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=codeindex
export POSTGRES_PASSWORD=your-secure-password
export POSTGRES_DB=code_index_db

# Elasticsearch Configuration
export ELASTICSEARCH_HOSTS=http://localhost:9200
```

**3. Migration (if upgrading from SQLite):**
```bash
# Backup existing data
python backup_script.py

# Run migration
python src/scripts/etl_script.py --mode full

# Verify migration
python src/scripts/etl_script.py --mode verify
```

### 📚 **Complete Installation Guide**

For detailed installation instructions, database setup, and troubleshooting, see:
**[📖 Installation Guide](docs/INSTALLATION.md)**

For Elasticsearch security configuration (authentication, TLS/SSL, API keys), see:
**[🔒 Elasticsearch Security Guide](docs/ELASTICSEARCH_SECURITY.md)**

For local vector store architecture, configuration, and supported models, see:
**[🔍 Local Vector Store Guide](docs/LOCAL_VECTOR_STORE.md)**

## 🤖 Agent Integration

The Unified Core Engine is designed for deep integration with AI agents.

### 🛠️ CLI & Skills
We provide a dedicated CLI tool `code-search` and a Skill definition for agents to autonomously navigate your codebase.

**1. CLI Tool:**
```bash
# Search code (Semantic + Symbolic)
code-search "How does the indexing work?"

# Ask questions (RAG)
code-search --answer "Explain the core engine architecture"
```

**2. Agent Configuration:**
Run the installation helper to get configuration snippets for your agent:
```bash
python src/scripts/install_agent.py [claude-code|openai|vscode|all]
```

**3. Skill Integration:**
For agents that support Skills or System Prompts, refer to `plugins/code_indexer/skills/code-search/SKILL.md` for the optimal prompt to ensure the agent uses the Unified Engine correctly.

## 🔌 MCP Integration

The Code Index MCP server supports multiple integration methods:

### Method 1: Direct Git Integration (Recommended)

For LM Studio, Claude Desktop, VS Code, and other MCP-compatible applications:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "uvx",
      "args": ["git+https://github.com/scooter-lacroix/code-indexer.git"],
      "env": {},
      "start_on_launch": true
    }
  }
}
```

### Method 2: Package Installation

For package manager installed versions:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "code-index-mcp",
      "args": [],
      "env": {},
      "start_on_launch": true
    }
  }
}
```

### Method 3: Local Development

For locally installed versions:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "uv",
      "args": ["run", "code_index_mcp"],
      "env": {},
      "start_on_launch": true
    }
  }
}
```

### Method 4: HTTP Server Mode

For web-based integrations:

```bash
# Start HTTP server
python -m code_index.server --port 8765

# Or using uv
uv run code_index.server --port 8765
```

Then configure your application:

```json
{
  "mcpServers": {
    "code-index": {
      "transport": "http",
      "url": "http://localhost:8765/mcp",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

### Application-Specific Configurations

**VS Code/Cursor/Windsurf** (using MCP extension):
```json
{
  "mcp.servers": {
    "code-index": {
      "command": "code-index-mcp",
      "args": [],
      "env": {},
      "transport": "stdio"
    }
  }
}
```

**Jan AI**:
```json
{
  "mcp_servers": {
    "code-index": {
      "command": "code-index-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

**OpenHands**:
```json
{
  "mcp": {
    "servers": {
      "code-index": {
        "command": "code-index-mcp",
        "args": [],
        "env": {}
      }
    }
  }
}
```

## 🛠️ Usage

### Command Line Interface

```bash
# Start stdio server (MCP integration)
code-index-mcp

# Start HTTP server (web integration)
code-index-mcp --http --port 8765

# Local development (runs the server)
uv run code_index_mcp server
```

### Local Development with Docker Compose

For local development using PostgreSQL and Elasticsearch via Docker Compose:

```bash
# Start PostgreSQL and Elasticsearch containers in detached mode
python run.py start-dev-dbs

# Stop PostgreSQL and Elasticsearch containers and remove their volumes
python run.py stop-dev-dbs

# Restart PostgreSQL and Elasticsearch containers
python run.py restart-dev-dbs

# Run the Code Index MCP server (connects to Dockerized databases if configured)
python run.py server
```

### Debug with MCP Inspector

```bash
# For git installation
npx @modelcontextprotocol/inspector uvx git+https://github.com/scooter-lacroix/code-indexer.git

# For package installation
npx @modelcontextprotocol/inspector code-index-mcp

# For local development
npx @modelcontextprotocol/inspector uv run code_index_mcp
```

## 🛠️ Available Tools

The Code Index MCP server provides **9 consolidated mega-tools** for comprehensive code analysis and management. These mega-tools use action-based routing to streamline operations while preserving all functionality from the original 50+ individual tools.

### 🌟 **Mega-Tools Architecture**

Each mega-tool accepts an `action`, `operation`, or `type` parameter that routes to the specific functionality you need:

| Mega-Tool | Actions/Operations/Modes | Consolidates |
|-----------|------------------------|--------------|
| **manage_project** | set_path, refresh, reindex, clear, reset | 5 tools |
| **search_content** | search, find, rank | 3 tools |
| **modify_file** | write, diff, insert, replace | 4 tools |
| **manage_files** | delete, rename, revert, history | 4 tools |
| **get_diagnostics** | memory, index, backend, performance, operations, settings, ignore, filtering, ranking | 9 tools |
| **manage_memory** | cleanup, configure, export | 3 tools |
| **manage_operations** | list, cancel, cleanup | 4 tools |
| **read_file** | smart, chunks, detect_errors, metadata | 4 tools |
| **manage_temp** | create, check | 2 tools |

### 📋 **Detailed Mega-Tools Reference**

#### 1. **manage_project** - Project Lifecycle Management
```python
# Set project path
manage_project(action="set_path", path="/path/to/project")

# Refresh with incremental indexing
manage_project(action="refresh")

# Force complete reindex
manage_project(action="reindex", clear_cache=True)

# Clear all settings
manage_project(action="clear")

# Reset server state
manage_project(action="reset")
```

#### 2. **search_content** - Content Search and Discovery
```python
# Advanced semantic search
search_content(action="search", pattern="function foo", fuzzy=True)

# Find files by glob pattern
search_content(action="find", pattern="*.py")

# Rank search results by relevance
search_content(action="rank", results=[...], query="authentication")
```

#### 3. **modify_file** - File Content Modifications
```python
# Write complete file
modify_file(operation="write", path="src/main.py", content="...", line_count=10)

# Apply diff with regex
modify_file(operation="diff", path="config.json", search="old", replace="new")

# Insert content at specific line
modify_file(operation="insert", path="README.md", line=10, content="new section")

# Search and replace
modify_file(operation="replace", path="api.py", search="todo", replace="TODO")
```

#### 4. **manage_files** - File System Operations
```python
# Delete a file
manage_files(action="delete", file_path="old_file.py")

# Rename/move a file
manage_files(action="rename", file_path="src/old.py", new_file_path="src/new.py")

# Revert to specific version
manage_files(action="revert", file_path="config.json", version_id="v1.2.3")

# Get file history
manage_files(action="history", file_path="src/main.py")
```

#### 5. **get_diagnostics** - System Diagnostics and Metrics
```python
# Check memory usage
get_diagnostics(type="memory")

# Get index statistics
get_diagnostics(type="index", force_refresh=True)

# Check backend health
get_diagnostics(type="backend")

# Get performance metrics
get_diagnostics(type="performance")

# List active operations
get_diagnostics(type="operations")

# View ignore patterns
get_diagnostics(type="ignore")

# Check ranking configuration
get_diagnostics(type="ranking")
```

#### 6. **manage_memory** - Memory Management
```python
# Trigger memory cleanup
manage_memory(action="cleanup")

# Configure memory limits
manage_memory(action="configure", soft_limit_mb=1024, hard_limit_mb=2048)

# Export memory profile
manage_memory(action="export", file_path="/tmp/memory.json")
```

#### 7. **manage_operations** - Operation Tracking and Control
```python
# List all active operations
manage_operations(action="list")

# Cancel specific operation
manage_operations(action="cancel", operation_id="op-123")

# Cleanup old completed operations
manage_operations(action="cleanup", max_age_hours=2.0)
```

#### 8. **read_file** - File Reading Strategies
```python
# Full smart analysis
read_file(mode="smart", file_path="src/main.py", include_content=True)

# Read large file in chunks
read_file(mode="chunks", file_path="large.json", chunk_size=8388608)

# Detect errors in a file
read_file(mode="detect_errors", file_path="config.py")

# Get file metadata only
read_file(mode="metadata", file_path="README.md")
```

#### 9. **manage_temp** - Temporary Directory Management
```python
# Ensure temp directory exists
manage_temp(action="create")

# Check temp directory status
manage_temp(action="check")
```

### 📚 **Migration from Old Tools**

If you were using the previous 50+ individual tools, see the **[Migration Guide](conductor/tracks/mcp_consolidation_local_vector_20251230/MIGRATION_GUIDE.md)** for a complete mapping of old tool names to the new mega-tools.

**Quick Migration Examples:**
- `set_project_path()` -> `manage_project(action="set_path", path=...)`
- `search_code_advanced()` -> `search_content(action="search", pattern=...)`
- `write_to_file()` -> `modify_file(operation="write", path=..., content=...)`
- `get_file_history()` -> `manage_files(action="history", file_path=...)`

**📖 Complete Documentation**: See [docs/TOOLS_LIST.md](docs/TOOLS_LIST.md) for detailed tool reference with examples and system prompt templates.

## Common Workflows and Examples

Here's a typical workflow for using Code Index MCP with an AI assistant like Claude.

### 1. Set Project Path & Initial Indexing

This is the first and most important step. When you set the project path, the server automatically creates a file index for the first time or loads a previously cached one.

**Example Prompt:**
```
Please set the project path to C:\Users\username\projects\my-react-app
```

**Mega-tool used:**
```python
manage_project(action="set_path", path="C:\\Users\\username\\projects\\my-react-app")
```

### 2. Refresh the Index (When Needed)

If you make significant changes to your project files after the initial setup, you can manually refresh the index to ensure all tools are working with the latest information.

**Example Prompt:**
```
I've just added a few new components, please refresh the project index.
```

**Mega-tool used:**
```python
manage_project(action="refresh")
```

### 3. Explore the Project Structure

Once the index is ready, you can find files using patterns (globs) to understand the codebase and locate relevant files.

**Example Prompt:**
```
Find all TypeScript component files in the 'src/components' directory.
```

**Mega-tool used:**
```python
search_content(action="find", pattern="src/components/**/*.tsx")
```

### 4. Analyze a Specific File

Before diving into the full content of a file, you can get a quick summary of its structure, including functions, classes, and imports.

**Example Prompt:**
```
Can you give me a summary of the 'src/api/userService.ts' file?
```

**Mega-tool used:**
```python
read_file(mode="smart", file_path="src/api/userService.ts", include_content=True)
```

### 5. Search for Code

With an up-to-date index, you can search for code snippets, function names, or any text pattern to find where specific logic is implemented.

**Example: Simple Search**
```
Search for all occurrences of the "processData" function.
```
```python
search_content(action="search", pattern="function processData")
```

**Example: Search with Fuzzy Matching**
```
I'm looking for a function related to user authentication, it might be named 'authUser', 'authenticateUser', or something similar. Can you do a fuzzy search for 'authUser'?
```
```python
search_content(action="search", pattern="authUser", fuzzy=True)
```

**Example: Search within Specific Files**
```
Search for the string "API_ENDPOINT" only in Python files.
```
```python
search_content(action="search", pattern="API_ENDPOINT", file_pattern="*.py")
```

### 6. Modify Files

When you need to make changes to your code, use the modify_file mega-tool with different operations.

**Example: Write a New File**
```
Create a new file 'src/utils/helpers.ts' with utility functions.
```
```python
modify_file(
    operation="write",
    path="src/utils/helpers.ts",
    content="export function formatDate(date: Date): string { ... }",
    line_count=5
)
```

**Example: Search and Replace**
```
Replace all occurrences of 'TODO' with 'FIXME' in the api.ts file.
```
```python
modify_file(
    operation="replace",
    path="src/api.ts",
    search="TODO",
    replace="FIXME"
)
```

### 7. Get System Diagnostics

Monitor the health and performance of your code indexing system.

**Example: Check Memory Usage**
```
How much memory is the indexer currently using?
```
```python
get_diagnostics(type="memory")
```

**Example: View Index Statistics**
```
Show me the current index statistics.
```
```python
get_diagnostics(type="index", force_refresh=True)
```

### 8. Manage File Versions

Track and revert changes to files using the version history system.

**Example: Get File History**
```
Show me the change history for config.json.
```
```python
manage_files(action="history", file_path="config.json")
```

**Example: Revert to Previous Version**
```
Revert main.py to the version from yesterday.
```
```python
manage_files(
    action="revert",
    file_path="main.py",
    timestamp="2024-01-15T10:30:00"
)
```

## Development

### Building from Source

1. Clone the repository:

```bash
git clone https://github.com/scooter-lacroix/code-indexer.git
cd code-index-mcp
```

2. Install dependencies:

```bash
uv sync
```

3. Run the server locally:

```bash
uv run code_index_mcp
```

## Debugging

You can use the MCP inspector to debug the server:

```bash
npx @modelcontextprotocol/inspector uvx code-index-mcp
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Languages

- [繁體中文](README_zh.md)
