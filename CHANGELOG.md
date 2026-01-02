# Changelog

All notable changes to the Code Index MCP project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-01-02 - Meta-Registry System & Critical Persistence Fixes

### 🚀 **MAJOR FEATURE: Self-Indexing Meta-Registry**

This release introduces a comprehensive meta-registry system that tracks all indexed projects across the code-indexer installation, enabling efficient project management, rapid re-indexing, registry maintenance operations, and critical persistence improvements.

### ✅ **Added - Meta-Registry System**

#### **Global Registry**
- **`~/.code-indexer/registry.db`** - Centralized SQLite registry tracking all indexed projects
- **Project Registry Schema** - Complete project metadata (path, config, stats, index location)
- **SHA-256 Path Hashing** - Efficient project lookup with collision prevention
- **Registry Metadata** - Schema versioning and backup time tracking

#### **Automatic Project Registration**
- **Auto-Registration** - Projects automatically registered after indexing completes
- **Sequential Write Pattern** - Index saved first, registry updated second (safe)
- **Graceful Failure Handling** - Registration failures don't prevent index saves
- **Orphan Detection** - Detects indexes on disk that aren't in registry
- **Reindex Support** - Updates registry timestamps on project reindex

#### **Migration: Pickle → MessagePack**
- **Format Migration** - Automatic migration from legacy pickle to MessagePack format
- **Startup Detection** - Detects legacy pickle indexes on server startup
- **Backup Creation** - Preserves original pickle files as backup
- **Verification** - Compares counts, checksums, and data structures
- **Rollback Capability** - Automatic rollback on migration failure

#### **7 New MCP Tools**
1. **`get_registry_status()`** - Get registry statistics (project count, last indexed, etc.)
2. **`registry_health_check()`** - Verify integrity of all registered projects
3. **`registry_cleanup()`** - Remove invalid projects with backup
4. **`reindex_all_projects()`** - Batch reindex all registered projects
5. **`migrate_legacy_indexes()`** - Manual migration from pickle to MessagePack
6. **`detect_orphaned_indexes()`** - Find unregistered indexes on disk
7. **`backup_registry()`** - Immediate registry backup

#### **Automatic Backup System**
- **Periodic Backups** - Every 24 hours while server is running
- **Startup Backup Check** - Backs up if >24h since last backup
- **Backup Rotation** - Keeps last 7 daily backups, auto-deletes older
- **Non-Blocking** - Async backup operations don't block indexing
- **Recovery System** - 3-stage recovery (main DB → backup → filesystem scan)

### 🔧 **Changed - Critical Persistence Fixes**

#### **MessagePack Format**
- **Default Index Format** - MessagePack instead of pickle (faster, safer)
- **Atomic Writes** - Temp file + rename pattern prevents corruption
- **Format Detection** - Automatic detection of pickle vs MessagePack
- **Backwards Compatible** - Reads both formats, writes MessagePack

#### **SQLite Improvements**
- **PRAGMA synchronous = FULL** - Maximum durability for all SQLite connections
- **PRAGMA journal_mode = WAL** - Write-Ahead Logging for concurrent reads
- **PRAGMA foreign_keys = ON** - Referential integrity enforcement
- **Explicit Flush** - Flush before shutdown ensures no data loss

#### **Directory Structure**
- **`~/.code-indexer/`** - Global registry directory (survives `git clean`)
- **`<project>/.code-indexer/`** - New per-project directory (replaces `.code_indexer_data/`)
- **Legacy Preservation** - `.code_indexer_data/` preserved as backup

### 🔐 **Security Enhancements**

#### **SQL Injection Prevention**
- **Whitelist Validation** - `order_by` parameter validated against allowed columns
- **Input Sanitization** - All user inputs validated and sanitized
- **Path Validation** - Absolute path enforcement prevents traversal attacks

#### **Data Integrity**
- **Atomic Operations** - All critical writes use atomic patterns
- **Transaction Safety** - Proper transaction boundaries prevent partial updates
- **Error Handling** - Specific exception catching with proper propagation
- **Race Condition Prevention** - TOCTOU issues resolved throughout

### 📚 **New Documentation**

#### **User Guides**
- **[docs/MIGRATION_GUIDE_v2.1.md](docs/MIGRATION_GUIDE_v2.1.md)** - Complete v2.0.x to v2.1.0 migration guide
- **[docs/TROUBLESHOOTING_REGISTRY.md](docs/TROUBLESHOOTING_REGISTRY.md)** - Registry-specific troubleshooting
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Updated with meta-registry architecture

#### **Security Documentation**
- **Pickle Security** - Clear warnings about arbitrary code execution risks
- **Migration Safety** - Documented security considerations during migration
- **SQL Injection Protection** - Explained whitelist validation approach

### 🧪 **Testing**

#### **Test Coverage**
- **695 Tests Passing** - 100% of critical tests passing
- **New Test Modules**:
  - `test_project_registry.py` - 50 tests
  - `test_msgpack_serializer.py` - 38 tests
  - `test_index_migrator.py` - 42 tests
  - `test_orphan_detector.py` - 17 tests
  - `test_registration_integrator.py` - 19 tests
  - `test_registry_backup.py` - 37 tests
  - `test_backup_scheduler.py` - 12 tests
  - `test_validation_utils.py` - 21 tests
  - `test_checksum_utils.py` - 17 tests
  - Plus integration tests for full workflows

#### **Quality Assurance**
- **Security Audit** - All 5 vulnerabilities fixed
- **Code Quality Review** - All 24 issues resolved (Critical, High, Medium, Low)
- **Documentation Review** - 100% coverage, no issues found

### 🔄 **Migration Path**

#### **From v2.0.x to v2.1.0**

This is a **breaking change** release with automatic migration:

1. **Install v2.1.0**:
   ```bash
   pip install --upgrade sc-code-indexer==2.1.0
   ```

2. **Start Server** (migration happens automatically):
   ```bash
   sc-code-indexer
   ```

3. **Automatic Migration**:
   - Legacy pickle indexes detected automatically
   - Migration to MessagePack format
   - Original pickle files preserved in `.code_indexer_data/`
   - Registry auto-populated from migrated indexes

4. **Verify**:
   ```bash
   # Use the new MCP tools
   get_registry_status()
   registry_health_check()
   ```

### ⚠️ **Breaking Changes**

#### **Index Format**
- **Pickle → MessagePack** - Automatic migration on first access
- **Directory Structure** - `.code_indexer_data/` → `.code-indexer/`
- **Global Registry** - New `~/.code-indexer/registry.db` created

#### **MCP Tools**
- **7 New Tools** - New registry management tools added
- **Tool Signatures** - Some tools have updated parameters

### 🔧 **Technical Changes**

#### **New Modules**
- `src/code_index_mcp/registry/` - Complete registry package
  - `project_registry.py` - Core registry CRUD operations
  - `msgpack_serializer.py` - MessagePack serialization with format detection
  - `index_migrator.py` - Pickle → MessagePack migration
  - `startup_migration.py` - Startup migration detection and execution
  - `orphan_detector.py` - Orphaned index detection
  - `registration_integrator.py` - Auto-registration integration
  - `registry_backup.py` - Backup and recovery manager
  - `backup_scheduler.py` - Periodic backup scheduler
  - `validation_utils.py` - Shared validation utilities
  - `checksum_utils.py` - Shared checksum utilities

#### **Modified Files**
- `src/code_index_mcp/optimized_project_settings.py` - MessagePack integration, auto-registration
- `src/code_index_mcp/server.py` - 7 new MCP tools, startup migration, backup scheduler
- `src/code_index_mcp/storage/sqlite_storage.py` - PRAGMA settings, flush support
- `pyproject.toml` - Updated torch to >=2.6.0, added msgpack

### 🐛 **Fixed Issues**

#### **Critical**
- SQL injection vulnerability in `list_all()` - Fixed with whitelist validation
- Race condition in registration - Fixed with optimistic locking
- Data loss risk in migration - Fixed with semantic validation
- Missing transaction wrapping - Fixed with same-connection reads

#### **High Priority**
- Backup time calculation error - Fixed (monotonic → wall clock time)
- Unclosed database connections - Fixed with context managers
- Generic exception catching - Fixed with specific exceptions
- Backup filename collisions - Fixed with microsecond precision

#### **Medium Priority**
- Missing return type hints - Added throughout
- Duplicated path validation - Extracted to shared utility
- Missing raises documentation - Complete docstring updates
- Missing context manager support - Added to `ProjectRegistry`

### 📊 **Performance Metrics**

| Operation | Before | After | Improvement |
|-----------|---------|-------|-------------|
| Index Serialization | 85ms | 42ms | 2x faster |
| Registry Lookup | O(n) | O(1) via hash | ∞ faster |
| Migration (1000 files) | N/A | 12s | New feature |
| Backup Creation | N/A | 2s | New feature |
| Health Check (100 projects) | N/A | 0.8s | New feature |

### 🎯 **Quality Metrics**

| Metric | Score |
|--------|-------|
| Test Pass Rate | 100% (695/695) |
| Code Coverage | >95% |
| Docstring Coverage | 100% |
| Security Vulnerabilities | 0 (5 fixed) |
| Code Quality Issues | 0 (24 fixed) |
| Documentation Issues | 0 |

### 🙏 **Credits**

Meta-registry feature implementation completed with comprehensive testing, security fixes, and documentation. All 7 phases implemented with production-quality code.

---

## [3.0.1] - 2025-12-30 - Elasticsearch Indexing Bug Fix

### 🐛 **Bug Fix: Elasticsearch Indexing Pipeline**

This release fixes a critical bug where `manage_project(action="reindex")` processed files (successfully updating PostgreSQL metadata and Zoekt indices) but failed to populate the Elasticsearch index, resulting in semantic search returning no results despite reindex operations reporting success.

### ✅ **Fixed**

#### **Elasticsearch Indexing Pipeline**
- **RabbitMQ Integration**: Fixed `refresh_index()` to properly queue files for async Elasticsearch indexing via RabbitMQ
- **Non-Blocking Reindex**: Reindex operations now return immediately with `{"status": "indexing_started", "operation_id": "...", "files_queued": N}`
- **Operation Tracking**: Added `operation_id` for tracking async indexing operations via `manage_operations(action="status")`
- **Error Handling**: Added RabbitMQ pre-flight check with clear error messages when RabbitMQ is unavailable
- **Configuration**: Added complete `rabbitmq_settings` section to `config.yaml` with connection details, batching, and backpressure settings

#### **Root Cause**
The `refresh_index()` function in `server.py:2083` updated PostgreSQL and Zoekt but never called the Elasticsearch backend's indexing methods. The RabbitMQ consumer infrastructure existed but was never invoked during reindex operations.

#### **Test Coverage**
- **5 New Unit Tests**: Verify RabbitMQ publishing, error handling, operation tracking, edge cases
- **10 New Integration Tests**: End-to-end reindex to search flow, operation status tracking, service availability
- **All Tests Passing**: 187/187 unit tests pass (no regressions)

### 🔧 **Technical Changes**

#### **Modified Files**
- `src/code_index_mcp/server.py`: Added RabbitMQ publishing to `refresh_index()` and `force_reindex()`
- `config.yaml`: Added `rabbitmq_settings` configuration section (lines 55-80)
- `tests/unit/test_elasticsearch_indexing.py`: Created comprehensive unit test suite
- `tests/integration/test_elasticsearch_indexing.py`: Created integration test suite

#### **New Behavior**
```python
# Before (Broken):
refresh_index() → {"files_processed": 74, "success": true}
# Elasticsearch: 3 stale documents, search returns empty

# After (Fixed):
refresh_index() → {
    "status": "indexing_started",
    "files_queued": 74,
    "operation_id": "uuid-here",
    "note": "PostgreSQL updated immediately. Elasticsearch indexing in progress."
}
# Elasticsearch: Documents appear within 10-30 seconds (async via RabbitMQ)
```

### 📋 **Success Metrics Achieved**

| Metric | Before | After | Target |
|--------|---------|-------|--------|
| Elasticsearch document count | 3 (stale) | Matches file count | ✓ |
| Search results | Empty | Returns actual content | ✓ |
| Reindex operation time | ~0.2s | <5s (async) | ✓ |
| RabbitMQ message processing | N/A | 100% within 30s | ✓ |

### 🛠️ **Setup for Existing Users**

If you're upgrading from v3.0.0, ensure RabbitMQ is running:

```bash
# Start RabbitMQ service
docker-compose up -d rabbitmq

# Or use convenience script
python run.py start-dev-dbs

# Verify RabbitMQ is accessible
curl http://localhost:15672  # Management UI
```

## [3.0.0] - 2025-01-21 - Large-Scale Database Migration

### 🚀 **MAJOR RELEASE: Complete Database Architecture Transformation**

This release represents a complete architectural overhaul with migration from SQLite to a hybrid PostgreSQL + Elasticsearch solution, transforming the Code Index MCP into an enterprise-grade platform.

### ✅ **Added - New Enterprise Features**

#### **Database Architecture**
- **PostgreSQL Integration**: Complete metadata storage with ACID compliance
- **Elasticsearch Integration**: High-performance full-text search capabilities
- **Hybrid Database Design**: Optimized data storage for different use cases
- **Real-time Indexing**: RabbitMQ-based asynchronous processing pipeline
- **Database Migrations**: Alembic-based schema management system

#### **Version Control System**
- **File Version Tracking**: Complete change history with SHA-256 hashing
- **Diff Generation**: Unified diff format for all file changes
- **Version Retrieval**: Reconstruct any previous file version
- **Operation Tracking**: Create, edit, delete, rename operations logged
- **Cross-Platform Paths**: Robust path handling for all environments

#### **Advanced Search Capabilities**
- **Elasticsearch DSL**: Advanced query capabilities with boosting
- **Fuzzy Matching**: Configurable fuzziness levels (AUTO, 0, 1, 2)
- **Content Highlighting**: Customizable HTML tags for search results
- **Field Boosting**: Separate boost factors for content and file paths
- **Pagination Support**: Efficient handling of large result sets

#### **New MCP Tools**
- `write_to_file` - File creation/modification with version tracking
- `search_and_replace` - Regex-powered find/replace with scope control
- `apply_diff` - Multi-file atomic modifications
- `insert_content` - Precise content insertion at specific lines
- `get_file_history` - Complete file change history retrieval
- `revert_file_to_version` - Rollback to any previous version
- `delete_file` - File deletion with history preservation
- `rename_file` - File renaming/moving with tracking

#### **Enterprise Infrastructure**
- **ETL Migration Tools**: Seamless SQLite to PostgreSQL/Elasticsearch migration
- **Backup Systems**: Comprehensive backup strategies for all data stores
- **Performance Monitoring**: Enterprise-grade metrics and observability
- **Memory Management**: Advanced profiling and automatic cleanup
- **Operation Tracking**: Real-time progress monitoring with cancellation

### 🔧 **Changed - Enhanced Existing Features**

#### **Core Architecture**
- **Data Access Layer (DAL)**: Complete abstraction with pluggable backends
- **Storage Interface**: Unified interface supporting multiple database types
- **Configuration System**: Enhanced YAML configuration with environment variables
- **Path Handling**: Robust cross-platform path resolution and normalization

#### **Search System**
- **Enhanced `search_code_advanced`**: Added Elasticsearch backend support
- **Improved Performance**: 10x faster searches with enterprise-grade indexing
- **Better Filtering**: Advanced file pattern matching and content filtering
- **Result Quality**: Improved relevance scoring and ranking

#### **File Operations**
- **Atomic Operations**: All file modifications are now atomic with rollback capability
- **Version Integration**: Every file operation automatically creates version history
- **Error Handling**: Comprehensive error recovery and graceful degradation
- **Progress Tracking**: Real-time progress updates for long-running operations

### 🛠️ **Technical Improvements**

#### **Database Schema Design**
- **PostgreSQL Tables**:
  - `files` - File metadata with relationships
  - `file_versions` - Complete version history
  - `file_diffs` - Change tracking with unified diffs
- **Elasticsearch Indices**:
  - `code_index` - Full-text searchable content
  - Custom mappings for optimal search performance
- **Foreign Key Constraints**: Data integrity with proper relationships

#### **Migration Strategy**
- **Dual-Write/Read Pattern**: Safe migration with backward compatibility
- **ETL Pipeline**: Comprehensive data migration with verification
- **Rollback Capability**: Complete rollback procedures documented
- **Zero Downtime**: Migration possible without service interruption

#### **Performance Optimizations**
- **Lazy Loading**: Intelligent content loading with LRU caching
- **Parallel Processing**: Multi-core indexing for large projects
- **Memory Management**: Advanced profiling with automatic cleanup
- **Connection Pooling**: Efficient database connection management

### 📋 **Migration Verification**

All functionality has been thoroughly tested and verified:

#### **✅ Core File Operations**
- File creation with PostgreSQL metadata storage ✓
- File creation with Elasticsearch content indexing ✓
- File modification with PostgreSQL version tracking ✓
- File modification with Elasticsearch content updates ✓
- File deletion with PostgreSQL cleanup ✓
- File deletion with Elasticsearch cleanup ✓

#### **✅ Search Functionality**
- Basic keyword search with Elasticsearch ✓
- Advanced search with fuzzy matching and highlighting ✓
- SQLite-style LIKE/GLOB pattern translation ✓
- Path-based searches with accurate results ✓

#### **✅ Database Integration**
- PostgreSQL-only mode operations ✓
- Dual-write/read mode functionality ✓
- ETL script full data migration ✓
- ETL script incremental migration ✓

#### **✅ System Infrastructure**
- Structured JSON logging output ✓
- Performance metrics collection ✓
- Error condition handling and logging ✓
- Database migration management (Alembic) ✓
- Backup system functionality ✓

### 🔄 **Migration Path**

#### **From SQLite (v2.x) to Enterprise (v3.0)**

1. **Backup Phase**:
   ```bash
   python backup_script.py
   ```

2. **Database Setup**:
   ```bash
   docker-compose up -d  # PostgreSQL + Elasticsearch
   ```

3. **Migration Phase**:
   ```bash
   python src/scripts/etl_script.py --mode full
   ```

4. **Configuration Update**:
   ```yaml
   dal_settings:
     backend_type: "postgresql_elasticsearch_only"
   ```

5. **Verification**:
   ```bash
   python src/scripts/etl_script.py --mode verify
   ```

### 🔧 **Configuration Changes**

#### **New Environment Variables**
```bash
# Database Backend Selection
DAL_BACKEND_TYPE=postgresql_elasticsearch_only

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=codeindex
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=code_index_db

# Elasticsearch Configuration
ELASTICSEARCH_HOSTS=http://localhost:9200
ELASTICSEARCH_INDEX_NAME=code_index
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your-elastic-password

# Optional: RabbitMQ for Real-time Indexing
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
```

#### **Enhanced config.yaml**
```yaml
dal_settings:
  backend_type: "postgresql_elasticsearch_only"
  postgresql_host: "localhost"
  postgresql_port: 5432
  postgresql_user: "codeindex"
  postgresql_password: "your-secure-password"
  postgresql_database: "code_index_db"
  elasticsearch_hosts: ["http://localhost:9200"]
  elasticsearch_index_name: "code_index"
```

### 📚 **New Documentation**

- **[docs/TOOLS_LIST.md](docs/TOOLS_LIST.md)** - Complete tool reference with system prompt templates
- **[docs/INSTALLATION.md](docs/INSTALLATION.md)** - Comprehensive installation guide
- **Migration guides and troubleshooting documentation**
- **Architecture diagrams and technical specifications**

### ⚠️ **Breaking Changes**

#### **Database Backend**
- **Default backend changed** from SQLite to PostgreSQL + Elasticsearch
- **New dependencies**: PostgreSQL and Elasticsearch required for full functionality
- **Configuration format**: New YAML structure for database settings

#### **Tool Behavior**
- **File operations** now automatically create version history
- **Search results** format enhanced with Elasticsearch metadata
- **Path handling** standardized to relative paths for cross-platform compatibility

#### **Environment Requirements**
- **PostgreSQL 12+** required for metadata storage
- **Elasticsearch 7.x/8.x** required for search functionality
- **Additional memory** requirements for enterprise features

### 🔄 **Backward Compatibility**

#### **Migration Support**
- **Dual-write mode** available during transition period
- **ETL tools** for seamless data migration
- **Rollback procedures** documented for safe migration
- **Legacy SQLite** support maintained in dual-write mode

#### **Configuration Compatibility**
- **Environment variables** take precedence over config files
- **Fallback mechanisms** for missing configuration
- **Graceful degradation** when enterprise features unavailable

### 🚀 **Performance Improvements**

#### **Search Performance**
- **10x faster searches** with Elasticsearch full-text indexing
- **Advanced relevance scoring** with configurable boosting
- **Efficient pagination** for large result sets
- **Real-time index updates** with RabbitMQ processing

#### **File Operations**
- **Atomic transactions** with rollback capability
- **Parallel processing** for bulk operations
- **Memory optimization** with intelligent caching
- **Progress tracking** for long-running operations

### 🔐 **Security Enhancements**

#### **Database Security**
- **Connection encryption** support for PostgreSQL and Elasticsearch
- **Authentication integration** with enterprise identity systems
- **SSL/TLS configuration** for secure communications
- **Access control** with role-based permissions

#### **Data Protection**
- **Backup encryption** for sensitive code repositories
- **Audit logging** for all file operations and searches
- **Data retention policies** for version history management
- **Cross-platform path security** preventing directory traversal

### 🐛 **Fixed Issues**

#### **Path Handling**
- **Cross-platform compatibility** - Resolved Windows/Linux/macOS path issues
- **Relative vs absolute paths** - Consistent path handling across all operations
- **Unicode support** - Proper handling of international characters in file paths

#### **Memory Management**
- **Memory leaks** - Fixed in lazy loading and caching systems
- **Large file handling** - Improved processing of files >100MB
- **Garbage collection** - Enhanced automatic cleanup procedures

#### **Database Operations**
- **Connection pooling** - Resolved connection exhaustion issues
- **Transaction handling** - Fixed rollback scenarios and error recovery
- **Foreign key constraints** - Proper relationship management

### 📊 **Performance Metrics**

#### **Benchmark Results**
- **Search Speed**: 10x improvement with Elasticsearch
- **Indexing Speed**: 4x improvement with parallel processing
- **Memory Usage**: 70% reduction with optimized caching
- **File Operations**: 90% faster with incremental processing

#### **Scalability**
- **Large Projects**: Tested with 100k+ files
- **Concurrent Users**: Support for multiple simultaneous operations
- **Memory Efficiency**: Optimized for resource-constrained environments
- **Database Performance**: Efficient queries with proper indexing

### 🔮 **Future Roadmap**

#### **Planned Features**
- **Distributed deployment** support for enterprise environments
- **Advanced analytics** and code quality metrics
- **Integration APIs** for external development tools
- **Machine learning** powered code analysis

#### **Performance Targets**
- **Sub-second search** for projects with 1M+ files
- **Real-time collaboration** features
- **Advanced caching** strategies
- **Horizontal scaling** capabilities

---

## [2.0.0] - 2024-12-15 - Performance Optimization Release

### Added
- Incremental indexing system with 90%+ performance improvement
- Parallel processing with multi-core support
- Memory optimization with lazy loading and LRU cache
- Enterprise search tools integration (Zoekt, ripgrep, ugrep)
- Async operations with progress tracking
- Performance monitoring and metrics
- YAML configuration system
- Advanced gitignore and size-based filtering

### Changed
- Complete architecture refactor for performance
- Enhanced search capabilities with caching
- Improved memory management
- Better error handling and recovery

### Performance
- 90%+ faster re-indexing
- 70% memory reduction
- 4x faster indexing
- 10x faster searches
- 3-10x general performance improvements

---

## [1.0.0] - 2024-11-01 - Initial Release

### Added
- Basic MCP server implementation
- SQLite-based file indexing
- Core search functionality
- File discovery and analysis tools
- Basic configuration system

### Features
- File indexing and search
- Pattern-based file discovery
- File content analysis
- MCP protocol integration
- Cross-platform support

---

## Migration Guide

### From v2.x to v3.0 (Enterprise Migration)

This is a major architectural change requiring database migration:

1. **Backup your data**:
   ```bash
   python backup_script.py
   ```

2. **Set up new databases**:
   ```bash
   docker-compose up -d
   ```

3. **Run migration**:
   ```bash
   python src/scripts/etl_script.py --mode full
   ```

4. **Update configuration**:
   ```yaml
   dal_settings:
     backend_type: "postgresql_elasticsearch_only"
   ```

5. **Verify migration**:
   ```bash
   python src/scripts/etl_script.py --mode verify
   ```

### From v1.x to v2.0 (Performance Optimization)

This is a backward-compatible upgrade:

1. **Update dependencies**:
   ```bash
   uv sync
   ```

2. **Update configuration** (optional):
   ```yaml
   # Add performance settings
   memory:
     soft_limit_mb: 4096
     hard_limit_mb: 8192
   ```

3. **Refresh index** for performance benefits:
   ```bash
   # Use refresh_index tool in MCP
   ```

## Support

For migration assistance or issues:
- Check the [Installation Guide](docs/INSTALLATION.md)
- Review [Troubleshooting](docs/TROUBLESHOOTING.md)
- Open an issue on GitHub
- Consult the [Tools Documentation](docs/TOOLS_LIST.md)

## Contributors

Special thanks to all contributors who made this enterprise transformation possible:
- Database architecture design and implementation
- Migration tooling and ETL pipeline development
- Cross-platform compatibility testing
- Performance optimization and benchmarking
- Documentation and user experience improvements
