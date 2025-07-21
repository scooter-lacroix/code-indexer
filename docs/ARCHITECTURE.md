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