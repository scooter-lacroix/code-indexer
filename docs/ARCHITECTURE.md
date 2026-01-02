# Code Index MCP - Architecture Overview

This document provides a comprehensive overview of the Code Index MCP server architecture, focusing on the enterprise-grade hybrid database system and its components.

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Client Applications                       │
│  (Claude Desktop, VS Code, LM Studio, Jan AI, etc.)            │
└─────────────────┬───────────────────────────────────────────────┘
                  │ MCP Protocol (JSON-RPC over stdio/HTTP)
┌─────────────────▼───────────────────────────────────────────────┐
│                 Code Index MCP Server                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  MCP Tools Layer                            │ │
│  │  • File Operations  • Search Tools  • Version Control     │ │
│  │  • Project Management  • Performance Monitoring           │ │
│  └─────────────────┬───────────────────────────────────────────┘ │
│  ┌─────────────────▼───────────────────────────────────────────┐ │
│  │              Business Logic Layer                          │ │
│  │  • FileChangeTracker  • IncrementalIndexer               │ │
│  │  • PerformanceMonitor  • MemoryProfiler                  │ │
│  └─────────────────┬───────────────────────────────────────────┘ │
│  ┌─────────────────▼───────────────────────────────────────────┐ │
│  │            Data Access Layer (DAL)                         │ │
│  │  • Storage Interface  • Metadata Interface                │ │
│  │  • Search Interface  • Backend Abstraction                │ │
│  └─────────────────┬───────────────────────────────────────────┘ │
└──────────────────┬─┴─────────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐    ┌───▼────┐    ┌───▼────┐
│PostgreSQL│  │Elasticsearch│ │RabbitMQ│
│Metadata  │  │Full-Text    │ │Message │
│Storage   │  │Search       │ │Queue   │
└──────────┘  └──────────┘  └────────┘
```

## 🗄️ Database Architecture

### Hybrid Database Design

The system uses a **hybrid database architecture** optimized for different data types and access patterns:

#### **PostgreSQL - Structured Metadata Storage**
- **Purpose**: ACID-compliant storage for structured data and relationships
- **Data Types**:
  - File metadata (path, type, extension, timestamps)
  - Version history with complete file content
  - Change diffs with operation tracking
  - Relationships between files and versions

#### **Elasticsearch - Full-Text Search Engine**
- **Purpose**: High-performance full-text search and content analysis
- **Data Types**:
  - Indexed file content for fast searching
  - Metadata for search filtering and boosting
  - Search analytics and performance metrics

#### **RabbitMQ - Asynchronous Processing**
- **Purpose**: Real-time indexing and background processing
- **Use Cases**:
  - File change notifications
  - Async Elasticsearch indexing
  - Background maintenance tasks

### Database Schema Design

#### PostgreSQL Schema

```sql
-- Files table - Core file metadata
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR UNIQUE NOT NULL,
    file_type VARCHAR NOT NULL,
    extension VARCHAR,
    metadata_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- File versions table - Complete version history
CREATE TABLE file_versions (
    id VARCHAR PRIMARY KEY,  -- UUID
    file_path VARCHAR NOT NULL,
    file_id INTEGER REFERENCES files(id),
    content TEXT NOT NULL,
    hash VARCHAR NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    size INTEGER NOT NULL
);

-- File diffs table - Change tracking
CREATE TABLE file_diffs (
    id VARCHAR PRIMARY KEY,  -- UUID
    file_path VARCHAR NOT NULL,
    previous_version_id VARCHAR REFERENCES file_versions(id),
    current_version_id VARCHAR REFERENCES file_versions(id),
    diff_content TEXT NOT NULL,
    diff_type VARCHAR NOT NULL,
    operation_type VARCHAR NOT NULL,
    operation_details TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_files_path ON files(file_path);
CREATE INDEX idx_versions_path ON file_versions(file_path);
CREATE INDEX idx_versions_timestamp ON file_versions(timestamp);
CREATE INDEX idx_diffs_path ON file_diffs(file_path);
CREATE INDEX idx_diffs_timestamp ON file_diffs(timestamp);
```

#### Elasticsearch Index Mapping

```json
{
  "mappings": {
    "properties": {
      "file_path": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "keyword": {
            "type": "keyword"
          }
        }
      },
      "content": {
        "type": "text",
        "analyzer": "standard"
      },
      "file_type": {
        "type": "keyword"
      },
      "extension": {
        "type": "keyword"
      },
      "size": {
        "type": "long"
      },
      "last_modified": {
        "type": "date"
      },
      "language": {
        "type": "keyword"
      }
    }
  },
  "settings": {
    "analysis": {
      "analyzer": {
        "code_analyzer": {
          "tokenizer": "standard",
          "filter": ["lowercase", "stop"]
        }
      }
    }
  }
}
```

## 🔧 Component Architecture

### Data Access Layer (DAL)

The DAL provides a unified interface for all database operations:

```python
class DALInterface(ABC):
    @property
    def storage(self) -> StorageInterface:
        """Generic key-value storage operations"""
        
    @property
    def metadata(self) -> FileMetadataInterface:
        """File metadata and version tracking"""
        
    @property
    def search(self) -> SearchInterface:
        """Full-text search capabilities"""
```

#### Backend Implementations

1. **SQLiteDAL** - Legacy single-file storage
2. **PostgreSQLElasticsearchDAL** - Enterprise hybrid storage
3. **DualWriteReadDAL** - Migration-safe dual operations

### File Change Tracking System

```python
class FileChangeTracker:
    def __init__(self, storage_backend: FileMetadataInterface, 
                 incremental_indexer: IncrementalIndexer):
        """
        Tracks all file changes with version history
        - Pre-edit state capture
        - Post-edit state recording
        - Diff generation
        - Cross-platform path handling
        """
```

**Key Features**:
- **Atomic Operations**: All changes are transactional
- **Version History**: Complete file evolution tracking
- **Diff Generation**: Unified diff format for all changes
- **Path Normalization**: Cross-platform compatibility
- **Error Recovery**: Rollback capabilities

### Search System Architecture

```python
class SearchInterface(ABC):
    def search_content(self, query: str) -> List[Tuple[str, Any]]:
        """Full-text content search"""
        
    def search_file_paths(self, query: str) -> List[str]:
        """File path pattern matching"""
        
    def index_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """Document indexing for search"""
```

**Search Capabilities**:
- **Elasticsearch DSL**: Advanced query construction
- **Fuzzy Matching**: Configurable fuzziness levels
- **Field Boosting**: Content vs. path relevance weighting
- **Highlighting**: Custom HTML tag insertion
- **Pagination**: Efficient large result handling

## 🔄 Data Flow Architecture

### File Operation Flow

```
1. MCP Tool Call (e.g., write_to_file)
   ↓
2. Business Logic Validation
   ↓
3. FileChangeTracker.capture_pre_edit_state()
   ├─ Read current file content
   ├─ Generate version ID
   └─ Store version in PostgreSQL
   ↓
4. File System Operation
   ├─ Write file to disk
   └─ Update file timestamps
   ↓
5. FileChangeTracker.record_post_edit_state()
   ├─ Generate new version ID
   ├─ Store new version in PostgreSQL
   ├─ Generate unified diff
   └─ Store diff in PostgreSQL
   ↓
6. Real-time Indexing (via RabbitMQ)
   ├─ Publish change event
   ├─ Async Elasticsearch update
   └─ Search index refresh
   ↓
7. Response to MCP Client
```

### Search Operation Flow

```
1. MCP Search Tool Call
   ↓
2. Query Processing & Validation
   ↓
3. Backend Selection (Elasticsearch preferred)
   ↓
4. Query Translation
   ├─ Pattern → Elasticsearch DSL
   ├─ Apply filters and boosting
   └─ Configure highlighting
   ↓
5. Search Execution
   ├─ Execute query against Elasticsearch
   ├─ Apply pagination
   └─ Process results
   ↓
6. Result Enhancement
   ├─ Add file metadata from PostgreSQL
   ├─ Apply highlighting
   └─ Format for MCP response
   ↓
7. Response to MCP Client
```

## 🚀 Performance Architecture

### Memory Management

```python
class MemoryAwareLazyContentManager:
    """
    Intelligent memory management with:
    - LRU cache for frequently accessed files
    - Automatic garbage collection
    - Memory limit enforcement
    - Lazy loading strategies
    """
```

**Memory Optimization Features**:
- **Lazy Loading**: Content loaded only when needed
- **LRU Caching**: Most recently used files kept in memory
- **Memory Limits**: Configurable soft/hard limits
- **Automatic Cleanup**: Background garbage collection
- **Memory Profiling**: Real-time usage monitoring

### Parallel Processing

```python
class ParallelIndexer:
    """
    Multi-core indexing with:
    - Worker pool management
    - Task distribution
    - Progress tracking
    - Error handling
    """
```

**Parallel Processing Features**:
- **Multi-core Utilization**: Configurable worker threads
- **Task Distribution**: Intelligent workload balancing
- **Progress Tracking**: Real-time operation monitoring
- **Error Isolation**: Failed tasks don't affect others
- **Resource Management**: CPU and memory aware scheduling

### Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Caching Layers                           │
├─────────────────────────────────────────────────────────────┤
│ L1: In-Memory LRU Cache (Hot Files)                        │
│  • Recently accessed file content                          │
│  • Search result caching                                   │
│  • Metadata caching                                        │
├─────────────────────────────────────────────────────────────┤
│ L2: Database Query Caching                                 │
│  • PostgreSQL query result caching                         │
│  • Elasticsearch query caching                             │
│  • Connection pooling                                      │
├─────────────────────────────────────────────────────────────┤
│ L3: File System Caching                                    │
│  • OS-level file system cache                              │
│  • SSD/NVMe storage optimization                           │
│  • Network storage caching                                 │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 Security Architecture

### Database Security

```yaml
# PostgreSQL Security
postgresql_ssl_args:
  sslmode: "require"
  sslrootcert: "/path/to/ca.pem"
  sslcert: "/path/to/client.crt"
  sslkey: "/path/to/client.key"

# Elasticsearch Security
elasticsearch_use_ssl: true
elasticsearch_verify_certs: true
elasticsearch_ca_certs: "/path/to/ca.pem"
elasticsearch_client_cert: "/path/to/client.crt"
elasticsearch_client_key: "/path/to/client.key"
```

**Security Features**:
- **SSL/TLS Encryption**: All database communications encrypted
- **Certificate Authentication**: Client certificate validation
- **Access Control**: Role-based database permissions
- **Audit Logging**: All operations logged for compliance
- **Data Encryption**: At-rest encryption for sensitive data

### Application Security

```python
class SecurityManager:
    """
    Application-level security with:
    - Path traversal prevention
    - Input validation and sanitization
    - Access control enforcement
    - Audit trail maintenance
    """
```

**Security Measures**:
- **Path Validation**: Prevent directory traversal attacks
- **Input Sanitization**: SQL injection and XSS prevention
- **Access Control**: File system permission enforcement
- **Audit Logging**: Complete operation tracking
- **Error Handling**: Secure error messages without information leakage

## 📊 Monitoring Architecture

### Performance Monitoring

```python
class PerformanceMonitor:
    """
    Comprehensive performance tracking:
    - Operation timing and throughput
    - Resource utilization monitoring
    - Error rate tracking
    - Performance trend analysis
    """
```

**Monitoring Capabilities**:
- **Real-time Metrics**: Live performance data
- **Historical Analysis**: Performance trend tracking
- **Alert System**: Threshold-based notifications
- **Resource Monitoring**: CPU, memory, disk, network
- **Custom Metrics**: Application-specific measurements

### Observability Stack

```
┌─────────────────────────────────────────────────────────────┐
│                  Observability Stack                        │
├─────────────────────────────────────────────────────────────┤
│ Metrics Collection                                          │
│  • Performance counters                                     │
│  • Resource utilization                                     │
│  • Error rates and latency                                  │
├─────────────────────────────────────────────────────────────┤
│ Logging System                                              │
│  • Structured JSON logging                                  │
│  • Log aggregation and analysis                             │
│  • Error tracking and alerting                              │
├─────────────────────────────────────────────────────────────┤
│ Tracing (Future)                                            │
│  • Distributed tracing                                      │
│  • Request flow visualization                               │
│  • Performance bottleneck identification                    │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Migration Architecture

### ETL Pipeline

```python
class ETLPipeline:
    """
    Data migration pipeline with:
    - Source data extraction (SQLite)
    - Data transformation and validation
    - Target data loading (PostgreSQL/Elasticsearch)
    - Migration verification and rollback
    """
```

**Migration Features**:
- **Full Migration**: Complete data transfer
- **Incremental Migration**: Delta synchronization
- **Data Validation**: Integrity verification
- **Rollback Capability**: Safe migration reversal
- **Progress Tracking**: Real-time migration status

### Dual-Write Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                 Dual-Write Architecture                      │
├─────────────────────────────────────────────────────────────┤
│ Write Operations                                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Client    │───▶│    DAL      │───▶│   SQLite    │     │
│  │  Request    │    │  Dual-Write │    │  (Legacy)   │     │
│  └─────────────┘    │             │    └─────────────┘     │
│                     │             │    ┌─────────────┐     │
│                     │             │───▶│ PostgreSQL  │     │
│                     │             │    │Elasticsearch│     │
│                     └─────────────┘    └─────────────┘     │
├─────────────────────────────────────────────────────────────┤
│ Read Operations (Prioritized)                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Client    │◀───│    DAL      │◀───│ PostgreSQL  │     │
│  │  Response   │    │ Dual-Read   │    │Elasticsearch│     │
│  └─────────────┘    │             │    └─────────────┘     │
│                     │             │    ┌─────────────┐     │
│                     │             │◀───│   SQLite    │     │
│                     │             │    │ (Fallback)  │     │
│                     └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 🔮 Future Architecture

### Planned Enhancements

#### **Distributed Architecture**
- **Microservices**: Service decomposition for scalability
- **Load Balancing**: Horizontal scaling capabilities
- **Service Mesh**: Inter-service communication management
- **Container Orchestration**: Kubernetes deployment support

#### **Advanced Analytics**
- **Machine Learning**: Code quality and complexity analysis
- **Predictive Analytics**: Performance optimization suggestions
- **Anomaly Detection**: Unusual pattern identification
- **Trend Analysis**: Long-term code evolution tracking

#### **Integration Ecosystem**
- **API Gateway**: External integration management
- **Webhook System**: Real-time event notifications
- **Plugin Architecture**: Third-party extension support
- **SDK Development**: Client library ecosystem

## 📚 Architecture Decisions

### Key Design Principles

1. **Separation of Concerns**: Clear layer boundaries and responsibilities
2. **Interface Abstraction**: Pluggable backend implementations
3. **Performance First**: Optimized for large-scale code repositories
4. **Cross-Platform**: Consistent behavior across all environments
5. **Enterprise Ready**: Production-grade reliability and security

### Technology Choices

#### **Database Selection**
- **PostgreSQL**: ACID compliance, mature ecosystem, excellent performance
- **Elasticsearch**: Purpose-built for full-text search, horizontal scaling
- **RabbitMQ**: Reliable message queuing, enterprise features

#### **Architecture Patterns**
- **Repository Pattern**: Data access abstraction
- **Factory Pattern**: Backend implementation selection
- **Observer Pattern**: Real-time change notifications
- **Strategy Pattern**: Configurable algorithm selection

### Performance Considerations

#### **Scalability Targets**
- **File Count**: 1M+ files per project
- **Project Size**: 100GB+ code repositories
- **Concurrent Users**: 100+ simultaneous operations
- **Search Performance**: Sub-second response times

#### **Resource Optimization**
- **Memory Usage**: Configurable limits with automatic management
- **CPU Utilization**: Multi-core parallel processing
- **Storage Efficiency**: Optimized indexing and compression
- **Network Bandwidth**: Efficient data transfer protocols

This architecture provides a solid foundation for enterprise-grade code analysis and management, with clear paths for future enhancement and scaling.

## 🗂️ Meta-Registry Architecture (v2.1.0)

### Overview

The **Meta-Registry** is a centralized project tracking system that manages metadata for all indexed projects across the Code Indexer. It provides a single source of truth for project locations, index formats, and indexing history.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Meta-Registry System                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Project Registry (SQLite)                   │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ projects table                                  │    │   │
│  │  │  • id (PK)                                      │    │   │
│  │  │  • path (unique, indexed)                        │    │   │
│  │  │  • path_hash (SHA-256, indexed)                  │    │   │
│  │  │  • indexed_at (timestamp)                        │    │   │
│  │  │  • file_count                                    │    │   │
│  │  │  • config (JSON)                                 │    │   │
│  │  │  • stats (JSON)                                  │    │   │
│  │  │  • index_location                                │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ registry_metadata table                          │    │   │
│  │  │  • key (unique)                                  │    │   │
│  │  │  • value (JSON)                                  │    │   │
│  │  │  Tracks: version, migrations, backups            │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Index Storage (MessagePack Format)            │   │
│  │  • Project-specific indexes                             │   │
│  │  • Symbol indexes                                       │   │
│  │  • Content indexes                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Backup & Recovery                          │   │
│  │  • Automatic periodic backups (24h)                     │   │
│  │  • Backup rotation (7 days)                             │   │
│  │  • Corruption detection & recovery                      │   │
│  │  • Filesystem scan recovery                             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Registry Components

#### 1. Project Registry (`project_registry.py`)

The core registry that maintains project metadata:

```python
class ProjectRegistry:
    """
    Central registry for all indexed projects.

    Key Operations:
    - insert(): Register new project
    - update(): Update project metadata
    - delete(): Remove project from registry
    - get_by_path(): Retrieve project by path
    - get_by_path_hash(): Retrieve project by hash
    - list_all(): List all projects (with pagination)
    - count(): Get total project count
    - exists(): Check if project is registered
    - set_metadata(): Set registry metadata
    - get_metadata(): Get registry metadata
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize registry with:
        - SQLite database with WAL mode
        - Automatic schema creation
        - Path hashing for fast lookups
        """

    def _hash_path(path: str) -> str:
        """
        Generate SHA-256 hash for path.
        Used for indexed lookups and deduplication.
        """
```

**Key Features**:
- **Path Hashing**: SHA-256 hashes for fast lookups and deduplication
- **WAL Mode**: Write-Ahead Logging for concurrent access
- **Atomic Operations**: All changes are transactional
- **Foreign Keys**: Referential integrity enforcement

#### 2. Index Migrator (`index_migrator.py`)

Handles migration from pickle to MessagePack format:

```python
class IndexMigrator:
    """
    Migrates index files from pickle to MessagePack format.

    Benefits:
    - 3-5x faster serialization
    - Cross-platform compatibility
    - Better security (no arbitrary code execution)
    - Smaller file sizes
    """

    def migrate_file(source_path: Path) -> MigrationResult:
        """
        Migrate single index file.

        Process:
        1. Detect format (pickle/msgpack)
        2. Read and validate data
        3. Create MessagePack version
        4. Create backup of original
        5. Verify migration success
        """

    def migrate_directory(directory: Path) -> List[MigrationResult]:
        """Migrate all index files in directory."""
```

#### 3. Startup Migration Manager (`startup_migration.py`)

Manages automatic migration on server startup:

```python
class StartupMigrationManager:
    """
    Automatic migration on startup.

    Features:
    - Scans global and project directories
    - Detects legacy pickle files
    - Migrates to MessagePack format
    - Tracks migration in registry
    - Supports first-access migration
    """

    def check_legacy_indexes(scan_global: bool = True) -> Dict:
        """Scan for legacy index files."""

    def perform_startup_migration(auto_migrate: bool = True) -> MigrationState:
        """Perform migration with progress tracking."""

    def migrate_on_first_access(project_path: Path) -> bool:
        """Migrate specific project on first access."""
```

#### 4. Backup Manager (`registry_backup.py`)

Provides backup and restore functionality:

```python
class RegistryBackupManager:
    """
    Backup and restore registry.

    Features:
    - Timestamped backups
    - SHA-256 checksums for integrity
    - 7-day backup rotation
    - Filesystem scan recovery
    - Corruption detection
    """

    def create_backup(registry: ProjectRegistry) -> BackupMetadata:
        """
        Create timestamped backup.

        Returns:
            BackupMetadata with:
            - backup_path
            - project_count
            - checksum
            - timestamp
        """

    def restore_latest_backup(target_path: Path) -> bool:
        """Restore from most recent backup."""

    def scan_and_recover(target_path: Path) -> List[Dict]:
        """
        Recover registry by scanning filesystem.

        Scans for index directories and rebuilds registry
        from discovered projects.
        """
```

#### 5. Backup Scheduler (`backup_scheduler.py`)

Manages automatic periodic backups:

```python
class BackupScheduler:
    """
    Automatic periodic backup scheduling.

    Features:
    - Startup backup check (backup if >24h)
    - Background periodic task (24h intervals)
    - Graceful shutdown handling
    - Signal handlers (SIGTERM, SIGINT)
    """

    async def startup_backup_check(registry: ProjectRegistry) -> Tuple[bool, str]:
        """
        Check and create backup on startup if needed.

        Returns:
            (backup_created: bool, message: str)
        """

    async def start_periodic_backups(registry: ProjectRegistry):
        """Start background periodic backup task."""

    async def shutdown():
        """Graceful shutdown - completes in-progress backup."""
```

#### 6. Registration Integrator (`registration_integrator.py`)

Integrates registration with indexing workflow:

```python
class RegistrationIntegrator:
    """
    Integrates project registration with indexing.

    Automatically registers projects:
    - After initial indexing
    - On re-index with changes
    - During migration
    """

    def register_after_indexing(
        project_path: str,
        index_location: str,
        file_count: int,
        stats: Dict,
    ) -> ProjectInfo:
        """Register project after indexing completes."""

    def update_on_reindex(
        project_path: str,
        file_count: int,
        stats: Dict,
    ) -> ProjectInfo:
        """Update project info after re-index."""
```

#### 7. Orphan Detector (`orphan_detector.py`)

Detects and cleans up orphaned index directories:

```python
class OrphanDetector:
    """
    Detect orphaned index directories.

    Orphan: Index directory without registry entry.

    Features:
    - Scans index directories
    - Compares with registry
    - Reports orphans
    - Cleanup options
    """

    def detect_orphans() -> List[OrphanedIndex]:
        """
        Detect orphaned index directories.

        Returns:
            List of OrphanedIndex with:
            - path
            - size
            - last_modified
            - reason for orphan status
        """

    def cleanup_orphans() -> int:
        """Remove orphaned directories. Returns count cleaned."""
```

#### 8. MessagePack Serializer (`msgpack_serializer.py`)

Handles MessagePack serialization:

```python
class MessagePackSerializer:
    """
    MessagePack serialization for index data.

    Benefits:
    - Fast serialization (3-5x vs pickle)
    - Cross-platform compatibility
    - Secure (no arbitrary code execution)
    - Compact file size
    """

    def write(path: Path, data: Dict) -> None:
        """Write data to MessagePack file."""

    def read(path: Path) -> Dict:
        """Read data from MessagePack file."""

    def write_stream(path: Path, data: Iterator) -> None:
        """Write streaming data for large indexes."""

    def read_stream(path: Path) -> Iterator:
        """Read streaming data for large indexes."""
```

### Directory Structure

```
~/.code-indexer/
├── registry/
│   ├── projects.db              # Main registry database
│   └── backups/                 # Registry backups
│       ├── projects_20250101.msgpack
│       ├── projects_20250102.msgpack
│       └── ...
└── indexes/                     # Legacy global indexes (deprecated)
```

```
<project>/.code-indexer/
├── files.msgpack               # File index
├── symbols.msgpack             # Symbol index
├── content.msgpack             # Content index
└── backups/                    # Index backups
    ├── files_20250101.msgpack
    └── ...
```

### Data Flow

#### Project Registration Flow

```
1. User sets project path
   ↓
2. IncrementalIndexer indexes project
   ↓
3. Indexes written to .code-indexer/
   ↓
4. RegistrationIntegrator.register_after_indexing()
   ↓
5. ProjectRegistry.insert()
   ├─ Hash project path (SHA-256)
   ├─ Check for duplicates
   └─ Insert into projects table
   ↓
6. Backup created (if >24h since last)
   ↓
7. Registration complete
```

#### Migration Flow

```
1. Server startup
   ↓
2. StartupMigrationManager.check_legacy_indexes()
   ├─ Scan ~/.code-indexer/ for pickle files
   ├─ Scan project directories for pickle files
   └─ Return list of legacy files
   ↓
3. If auto_migrate=True:
   └─ IndexMigrator.migrate_file()
       ├─ Read pickle file
       ├─ Validate data
       ├─ Write .msgpack version
       ├─ Create .pickle.backup
       └─ Verify success
   ↓
4. Track migration in registry metadata
   ↓
5. Ready for operation
```

#### Backup Flow

```
1. BackupScheduler.startup_backup_check()
   ↓
2. Check last backup time (from registry_metadata)
   ↓
3. If >24h since last backup:
   ├─ RegistryBackupManager.create_backup()
   │   ├─ Begin transaction
   │   ├─ Read all projects
   │   ├─ Serialize to MessagePack
   │   ├─ Calculate SHA-256 checksum
   │   ├─ Write to timestamped file
   │   └─ Update last_backup_time metadata
   └─ Rotate old backups (>7 days)
   ↓
4. Start background periodic task (24h interval)
   ↓
5. On shutdown:
   └─ Complete in-progress backup
       └─ Close registry
```

#### Recovery Flow

```
1. Detect corruption (SQLite integrity check fails)
   ↓
2. RegistryBackupManager.restore_latest_backup()
   ├─ Find most recent valid backup
   ├─ Verify checksum
   ├─ Close corrupted registry
   ├─ Restore from backup
   └─ Reopen registry
   ↓
3. If no backup available:
   └─ scan_and_recover()
       ├─ Scan filesystem for index directories
       ├─ Rebuild registry from discovered projects
       └─ Register all found projects
   ↓
4. Registry recovered
```

### Error Handling

#### Corruption Detection

```python
# SQLite integrity check
cursor.execute("PRAGMA integrity_check")
result = cursor.fetchone()

if result[0] != "ok":
    # Corruption detected
    logger.error(f"Registry corrupted: {result[0]}")
    # Trigger recovery
    backup_manager.restore_latest_backup(db_path)
```

#### Signal Handling

```python
# SIGTERM: Complete in-progress operations
def sigterm_handler(signum, frame):
    logger.info("SIGTERM received")
    # Complete backup
    if backup_in_progress:
        wait_for_backup_completion()
    # Close registry
    registry.close()
    sys.exit(0)

# SIGINT: Rollback in-progress writes
def sigint_handler(signum, frame):
    logger.info("SIGINT received")
    # Rollback transaction
    if transaction_in_progress:
        registry.rollback()
    # Close registry
    registry.close()
    sys.exit(0)
```

### Performance Considerations

#### Index Optimization

```sql
-- Key indexes for performance
CREATE INDEX idx_projects_path ON projects(path);
CREATE INDEX idx_projects_path_hash ON projects(path_hash);
CREATE INDEX idx_projects_indexed_at ON projects(indexed_at);
```

#### Connection Pooling

```python
# WAL mode allows concurrent readers
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")
```

#### Bulk Operations

```python
# Efficient bulk insert
def bulk_insert(projects: List[Dict]):
    with registry._conn:
        registry._conn.executemany(
            "INSERT INTO projects (...) VALUES (...)",
            [p.values() for p in projects]
        )
```

### Security Considerations

#### Path Validation

```python
# Normalize and validate paths
def validate_path(path: str) -> Path:
    path = Path(path).resolve()
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    return path
```

#### Input Sanitization

```python
# Sanitize metadata before storage
def sanitize_metadata(metadata: Dict) -> Dict:
    # Remove potentially dangerous keys
    dangerous_keys = ['__class__', '__reduce__', 'eval', 'exec']
    return {k: v for k, v in metadata.items()
            if k not in dangerous_keys}
```

#### Backup Integrity

```python
# Verify backup with checksum
def verify_backup(backup_path: Path) -> bool:
    metadata = read_backup_metadata(backup_path)

    # Calculate checksum
    with open(backup_path, 'rb') as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    return checksum == metadata.checksum
```

### Migration from v2.0 to v2.1

#### Breaking Changes

1. **Registry Introduction**: New centralized project tracking
2. **MessagePack Format**: Indexes now use MessagePack instead of pickle
3. **Automatic Migration**: Legacy pickle files migrated on startup
4. **Backup System**: New automatic backup and recovery

#### Migration Process

```bash
# Automatic migration on startup
code-index-mcp

# Manual migration (if needed)
python -m code_index_mcp.registry.migrate --format msgpack
```

#### Rollback

```bash
# Restore from backup
python -m code_index_mcp.registry.restore --backup <backup_path>
```

### Testing

#### Test Coverage

- **Unit Tests**: All registry components (>95% coverage)
- **Integration Tests**: Full workflow tests
- **Concurrent Access**: Multi-threaded operations
- **Corruption Recovery**: Backup and restore scenarios
- **Signal Handling**: SIGTERM/SIGINT edge cases

#### Test Files

```
tests/
├── unit/registry/
│   ├── test_project_registry.py
│   ├── test_index_migrator.py
│   ├── test_msgpack_serializer.py
│   ├── test_backup_scheduler.py
│   └── test_registry_backup.py
└── integration/registry/
    ├── test_full_indexing_workflow.py
    ├── test_concurrent_access.py
    ├── test_corruption_recovery.py
    └── test_signal_handlers.py
```

### Future Enhancements

#### Planned Features

1. **Distributed Registry**: Multi-machine registry synchronization
2. **Registry Replication**: Master-slave replication for high availability
3. **Advanced Analytics**: Project usage statistics and trends
4. **Registry API**: REST API for registry operations
5. **Web Dashboard**: Registry management UI

#### Performance Improvements

1. **Caching Layer**: Redis cache for frequently accessed projects
2. **Batch Operations**: Bulk insert/update operations
3. **Async Operations**: Async I/O for better concurrency
4. **Compression**: Compressed backup storage

The Meta-Registry system provides a robust foundation for managing large-scale code analysis operations with built-in reliability, performance, and security features.