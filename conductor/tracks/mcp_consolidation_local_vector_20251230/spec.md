# Specification: MCP Tool Consolidation and Local Vector Store

## Overview

This track implements two major improvements to the code-indexer:

1. **MCP Tool Consolidation**: Reduces the current 50+ MCP tools to **9 consolidated "mega-tools"** with action-based parameters, significantly reducing tool-selection overhead while maintaining all functionality.

2. **Local Vector Store**: Implements local semantic search using FAISS + sentence-transformers, replacing the Mixedbread cloud dependency entirely. This provides zero-cost, zero-latency semantic search with full privacy.

## Execution Order

**Phase 1**: Tool Consolidation
**Phase 2**: Local Vector Store Implementation

Both phases will be executed sequentially with a checkpoint between them.

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
