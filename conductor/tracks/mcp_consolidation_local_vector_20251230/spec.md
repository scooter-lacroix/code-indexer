# Specification: MCP Tool Consolidation and Local Vector Store

## Overview

This track implements two major improvements to the code-indexer:

1. **MCP Tool Consolidation**: Reduces the current 50+ MCP tools to **9 consolidated "mega-tools"** with action-based parameters, significantly reducing tool-selection overhead while maintaining all functionality.

2. **Local Vector Store**: Implements local semantic search using FAISS + sentence-transformers, replacing the Mixedbread cloud dependency entirely. This provides zero-cost, zero-latency semantic search with full privacy.

## Execution Order

**Phase 1**: Tool Consolidation [Complete: checkpoint 8ef88b4]
**Phase 2**: Local Vector Store Implementation [Complete: checkpoint c0f2c3e]
**Phase 3**: Search Integration, Optimization, and Production Readiness [Pending]

Phases are executed sequentially with a checkpoint between them.

---

## Phase 1: Tool Consolidation

### Functional Requirements

#### 1.1 Consolidated Tool Structure

The following **9 mega-tools** will replace the current 50+ individual tools:

| Mega-Tool | Action/Type Parameter | Consolidated Tools |
|-----------|---------------------|---------------------|
| `manage_project` | action: "set_path" \| "refresh" \| "reindex" \| "clear" \| "reset" | set_project_path, refresh_index, force_reindex, clear_settings, reset_server_state |
| `search_content` | action: "search" \| "find" \| "rank" | search_code_advanced, find_files, rank_search_results |
| `modify_file` | operation: "write" \| "diff" \| "insert" \| "replace" | write_to_file, apply_diff, insert_content, search_and_replace |
| `manage_files` | action: "delete" \| "rename" \| "revert" \| "history" | delete_file, rename_file, revert_file_to_version, get_file_history |
| `get_diagnostics` | type: "memory" \| "index" \| "backend" \| "performance" \| "operations" \| "settings" \| "ignore" \| "filtering" \| "ranking" | get_memory_profile, get_index_statistics, get_backend_health, get_performance_metrics, get_active_operations, get_settings_info, get_ignore_patterns, get_filtering_config, get_ranking_configuration |
| `manage_memory` | action: "cleanup" \| "configure" \| "export" | trigger_memory_cleanup, configure_memory_limits, export_memory_profile |
| `manage_operations` | action: "list" \| "cancel" \| "cleanup" | get_active_operations, cancel_operation, cleanup_completed_operations |
| `read_file` | mode: "smart" \| "chunks" \| "detect_errors" \| "metadata" | analyze_file_with_smart_reader, read_file_chunks, detect_file_errors, get_file_metadata |
| `manage_temp` | action: "create" \| "check" | create_temp_directory, check_temp_directory |

**Note:** `manage_config` was removed to avoid duplication. Its tools are consolidated into `get_diagnostics`.

#### 1.2 Removed Tools

The following tools will be completely removed:
- All API key management tools (list_api_keys, reset_api_key_quota, set_rotation_strategy, get_api_key_statistics)
- Any tools exclusively related to Mixedbread cloud integration

#### 1.3 Breaking Changes

This is a **hard breaking change**. Old tool names will not be supported. Users and agents must update to use the new consolidated API.

### Acceptance Criteria

- [ ] All 9 mega-tools implemented with proper action/type routing
- [ ] Each mega-tool supports all actions from its consolidated tools
- [ ] Old tool names removed from server.py
- [ ] Tool count reduced from 50+ to 9
- [ ] All existing tests updated to use new tools
- [ ] Test coverage maintained at >95%

---

## Phase 2: Local Vector Store Implementation

### Functional Requirements

#### 2.1 Embedding Model Support

**Supported Models:**
- **Primary (Default):** `BAAI/bge-small-en-v1.5` (384 dimensions, ~130MB)
- **Alternative 1:** `microsoft/codebert-base` (768 dimensions, code-specific)
- **Alternative 2:** `all-MiniLM-L6-v2` (384 dimensions, ~80MB, lightweight)

**Configuration:** Model selection via environment variable or configuration file. Default to `bge-small-en-v1.5`.

**Important:** First search will be ~2-3 seconds slower due to model loading. Subsequent searches will be <20ms.

#### 2.2 FAISS Index Implementation

**Adaptive Index Strategy:**
- Start with `IndexFlatIP` (exact search)
- Automatically switch to `IndexIVFFlat` (approximate search) when index exceeds 100,000 vectors
- Threshold should be configurable

**GPU Compatibility Note:**
```
Note: faiss-gpu is not yet available for Python 3.11.
Use faiss-cpu for now. GPU support can be added later when compatible wheels are available.
```

**Storage:**
- Vectors stored in memory using FAISS
- Metadata stored in PostgreSQL (file path, line numbers, chunk type, embedding model used)
- Index persisted to disk for fast startup without reindexing
- Model name stored in index metadata for validation

#### 2.3 Code Chunking Strategy

**Hybrid Approach:**
1. Parse file with AST to extract functions, classes, and top-level code blocks
2. For chunks < 512 tokens: Keep as-is
3. For chunks > 512 tokens: Split at logical boundaries (docstrings, nested functions, logical blocks)
4. Store rich metadata: file path, start/end lines, chunk type (function/class/module), parent context (class name, module docstring)

#### 2.4 Backend Integration

**Architecture:**
```
Local Vector (semantic) + Zoekt (regex) = Complete Search Solution
```

**Search Flow:**
1. Detect query type (regex pattern vs semantic)
2. Route to Zoekt OR Local Vector accordingly
3. Or run both and merge results (semantic ranking + exact matches)

**Removals:**
- Mixedbread API client code
- Cloud store upload/management tools
- VectorBackend cloud integration
- All Mixedbread-related dependencies

### Non-Functional Requirements

#### 2.5 Performance Targets

- **Search Latency:** p50 < 20ms, p95 < 50ms (after model loaded)
- **First Search:** ~2-3 seconds (model loading), then <20ms thereafter
- **Index Build Time:** < 100ms per file (embedding generation)
- **Memory Footprint:** < 200MB for model + index (10,000 file codebase)
- **Search Recall:** > 90% of relevant results in top 10

#### 2.6 Quality Metrics

Track and report:
- Search recall rate
- Latency percentiles (p50, p95, p99)
- Index size vs codebase size ratio
- Embedding cache hit rate

### Acceptance Criteria

- [ ] LocalVectorBackend class implemented with FAISS + sentence-transformers
- [ ] All three embedding models supported and configurable
- [ ] Hybrid chunking strategy implemented with AST parsing
- [ ] Adaptive FAISS index (FlatIP → IVFFlat) working
- [ ] Metadata storage in PostgreSQL functional
- [ ] Search integration with Zoekt working
- [ ] All Mixedbread cloud code removed
- [ ] Performance benchmarks meeting targets
- [ ] Unit tests, integration tests, and benchmarks passing
- [ ] Test coverage > 95%
- [ ] **Model detection on startup warns if index uses different model than config**
- [ ] **Index persistence/loading working (fast startup without reindexing)**

---

## Migration Strategy

### Fresh Start Approach

- **All indexes wiped** during migration
- **Full reindex required** with new local vector system
- **No data migration** from old PostgreSQL/Elasticsearch schema
- **Users must reindex** their codebases after upgrade

### Model Switching

- Switching embedding models requires **full reindex**
- Model name stored in index metadata
- Startup validation warns on model mismatch
- User can force reindex if changing models

### Installation Changes

- **New dependencies:** `faiss-cpu`, `sentence-transformers`
- **Removed dependencies:** `mixedbread` SDK
- **Environment variables:**
  - `LOCAL_VECTOR_MODEL` (default: "BAAI/bge-small-en-v1.5")
  - `FAISS_INDEX_THRESHOLD` (default: "100000")

---

## Out of Scope

- Persistent Mixedbread cloud support (being removed entirely)
- Backward compatibility shims for old tool names
- Data migration from old index formats
- Distributed vector search (single-machine only)
- GPU acceleration via faiss-gpu (Python 3.11 compatibility issue)

---

## Phase 3: Search Integration, Optimization, and Production Readiness

### Overview

Phase 3 brings together the Elasticsearch, FAISS, and Zoekt backends into a unified, production-ready search platform. It implements the deferred features from both Phase 2 and the Elasticsearch indexing track, creating a comprehensive solution with multi-backend result merging, performance optimization, quality metrics, and production resilience features.

### Functional Requirements

#### 3.1 Multi-Backend Search Result Merging

**Problem**: Each search backend (Elasticsearch, FAISS, Zoekt) returns results in different formats with different scoring schemes. Users need unified, ranked results from all backends.

**Solution**: Implement `SearchResultMerger` class with:

- **Score Normalization**: Convert heterogeneous scores to normalized space (min-max, z-score, or percentile)
- **Reciprocal Rank Fusion (RRF)**: Combine rankings from multiple backends using RRF algorithm
- **Weighted Merging**: Support custom weights per backend (e.g., FAISS: 0.5, ES: 0.3, Zoekt: 0.2)
- **Deduplication**: Remove duplicate results returned by multiple backends

**Configuration** (`config.yaml`):
```yaml
search:
  merge_strategy: "rrf"  # or "weighted", "custom"
  backend_weights:
    faiss: 0.5
    elasticsearch: 0.3
    zoekt: 0.2
  enable_deduplication: true
```

**Acceptance Criteria**:
- [ ] SearchResultMerger implemented with all strategies
- [ ] Score normalization handles different score ranges
- [ ] RRF produces consistent rankings regardless of score scale
- [ ] Deduplication removes exact duplicates (same file + lines)
- [ ] Configuration options work via config.yaml
- [ ] Integration tests with all three backends passing

#### 3.2 Performance Optimization Suite

**Problem**: Need measurable, documented performance characteristics and optimization strategies for different project sizes.

**Solution**: Implement comprehensive benchmark framework:

**Benchmark Framework** (`pytest-benchmark`):
- Latency tracking: p50, p95, p99 percentiles
- Throughput tracking: queries/second, files/second
- Scenarios: small (1K files), medium (10K), large (100K)
- Visualization: Generate performance reports

**Search Benchmarks**:
- Local vector search latency (target: p50 < 20ms, p95 < 50ms)
- Elasticsearch search latency
- Zoekt exact search latency
- Merged multi-backend search latency
- Cold start vs warm start (first query after model load)

**Indexing Benchmarks**:
- FAISS index build time per file
- Elasticsearch indexing throughput
- Full reindex time for 1K/10K/100K file projects
- RabbitMQ message processing rate

**Adaptive Batching**:
- Dynamic batch sizing based on file size
- Backpressure detection and handling
- Configurable batch sizes per backend
- Optimal defaults determined through benchmarking

**Memory Optimization**:
- Profile memory footprint for 10K/100K file indices
- FAISS index compression options (SQ8, PQ, etc.)
- Memory limit enforcement and monitoring
- Document memory requirements per project size

**Acceptance Criteria**:
- [ ] Benchmark suite executable via `pytest benchmarks/`
- [ ] All search latency targets met
- [ ] Adaptive batching reduces indexing time by >20%
- [ ] Memory footprint documented for 1K/10K/100K file projects
- [ ] Performance tuning guide created

#### 3.3 Quality Metrics and Monitoring

**Problem**: Need to track search quality and detect regressions.

**Solution**: Implement quality metrics framework:

**Metrics**:
- **Recall Rate**: % of relevant results in top-K
- **Precision**: % of results that are relevant
- **Mean Reciprocal Rank (MRR)**: Average rank of first relevant result
- **Latency Percentiles**: p50, p95, p99 search latency
- **Index Size**: Storage and memory footprint

**Query Type Detection Enhancement**:
- Enhanced regex vs semantic detection
- Hybrid query support (regex + semantic)
- Classification confidence scoring
- Query type statistics tracking

**Search Result Quality Validation**:
- Automated relevance validation (using labeled test sets)
- A/B testing framework for search strategies
- User feedback collection mechanism
- Quality thresholds and alerting

**Diagnostics Exposure**:
- Metrics queryable via `get_diagnostics(type="performance")`
- Historical metrics trends
- Per-backend performance breakdown

**Acceptance Criteria**:
- [ ] All quality metrics tracked and stored in PostgreSQL
- [ ] Query type detection accuracy >95%
- [ ] Metrics exposed via get_diagnostics tool
- [ ] A/B testing framework functional
- [ ] Quality alerts trigger on regression

#### 3.4 Production Features: Progress, Retry, and Resilience

**Problem**: Long-running operations need visibility, reliability, and graceful failure handling.

**Solution**: Implement production-grade operation management:

**Operation Progress Tracking**:
- Progress events: `{operation_id, phase, progress_pct, message}`
- Real-time progress updates during indexing
- Progress polling via `manage_operations(action="status")`
- CLI progress bar visualization

**Automatic Retry Logic**:
- Retryable errors: network failures, timeouts, 5xx responses
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s (max)
- Configurable max retry limit (default: 5)
- Dead letter queue for permanently failed items

**Hybrid Sync/Async Strategy**:
- Threshold-based routing: small projects sync, large projects async
- Configurable threshold (default: 1,000 files)
- Automatic strategy selection
- Documented trade-offs

**Configuration** (`config.yaml`):
```yaml
indexing:
  sync_threshold: 1000  # files
  retry_max_attempts: 5
  retry_backoff_base: 1.0  # seconds
  enable_progress_tracking: true
  dead_letter_queue: "failed_indexing"
```

**Acceptance Criteria**:
- [ ] Progress tracking accurate and visible in CLI
- [ ] Retry logic handles transient failures automatically
- [ ] Dead letter queue captures permanently failed items
- [ ] Hybrid strategy respects configured threshold
- [ ] All features tested and documented

#### 3.5 Database Migration (Alembic)

**Problem**: Current schema changes are manual and lack rollback capability.

**Solution**: Implement Alembic-based migration system:

**Migration Infrastructure**:
- Install and configure Alembic
- Initialize migration directory
- Configure database connection
- Document migration workflow

**Initial Migration**:
- Generate from current schema (vector metadata)
- Add upgrade/downgrade paths
- Test migration on fresh database
- Test rollback from migration

**Quality Metrics Migration**:
- Create metrics storage schema
- Add indexes for performance
- Implement aggregation queries

**Migration Tests**:
- Upgrade preserves all data
- Downgrade restores previous state
- Migration works on large datasets (100K+ records)
- Rollback is safe and repeatable

**Acceptance Criteria**:
- [ ] Alembic initialized and configured
- [ ] Initial migration created and tested
- [ ] Quality metrics migration created
- [ ] All migrations tested with upgrade/downgrade
- [ ] Migration workflow documented

#### 3.6 CLI Enhancements

**Problem**: Users need convenient CLI access to search functionality.

**Solution**: Implement `code-search` CLI command:

**Interactive Search**:
```bash
code-search "semantic query about authentication"
code-search --backend=faiss "function signature"
code-search --export=json --output=results.json "async patterns"
```

**Features**:
- Interactive search with result display
- Backend selection (`--backend=faiss|elasticsearch|zoekt|all`)
- Search result highlighting and preview
- Export to JSON/CSV
- Batch search from file

**Acceptance Criteria**:
- [ ] `code-search` command functional
- [ ] All backend selection options work
- [ ] Export formats (JSON, CSV) functional
- [ ] Batch search from file works
- [ ] Result highlighting and preview operational

### Non-Functional Requirements

#### 3.7 Performance Targets

- **Merged Search Latency**: p50 < 100ms, p95 < 200ms (all backends)
- **Progress Update Overhead**: <5% impact on indexing time
- **Retry Overhead**: <10% average latency increase
- **Migration Time**: <1 second per 10K records

#### 3.8 Quality Metrics

Track and report:
- Multi-backend search recall rate (target: >95%)
- Result ranking consistency (target: >90% correlation)
- Operation failure rate (target: <1%)
- Progress tracking accuracy (target: ±5%)

### Acceptance Criteria

Phase 3 is complete when:
- [ ] All 6 functional requirements (3.1 through 3.6) implemented
- [ ] Multi-backend search result merging functional
- [ ] Performance benchmarks passing with documented baselines
- [ ] Quality metrics tracking operational
- [ ] Progress, retry, and hybrid strategy all functional
- [ ] Alembic migrations implemented and tested
- [ ] CLI enhancements (code-search) functional
- [ ] All tests passing with >95% coverage
- [ ] Codex-reviewer approves all rigor checks
- [ ] User manual verification passes

### Integration with Elasticsearch Indexing Track

**Prerequisite**: Phase 3 of this track depends on completion of `elasticsearch_indexing_20251230` track.

**After Both Tracks Complete**:
```
┌─────────────────────────────────────────┐
│   Unified Search Platform               │
├─────────────────────────────────────────┤
│  Multi-Backend Merger                   │
│    ├─ Elasticsearch (full-text)         │
│    ├─ FAISS (semantic vectors)          │
│    └─ Zoekt (exact code search)         │
│                                         │
│  Production Features                    │
│    ├─ Progress Tracking                 │
│    ├─ Retry Logic                       │
│    ├─ Hybrid Sync/Async                 │
│    └─ Quality Metrics                   │
│                                         │
│  CLI & Diagnostics                      │
│    ├─ code-search command               │
│    └─ Performance tuning guide          │
└─────────────────────────────────────────┘
```
