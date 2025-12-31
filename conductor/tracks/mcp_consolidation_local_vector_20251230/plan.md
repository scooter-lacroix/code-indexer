# Implementation Plan: MCP Tool Consolidation and Local Vector Store

## Phase 1: Tool Consolidation [checkpoint: 8ef88b4]

### 1.1 Consolidation Design and Planning
- [x] Task: Analyze current 50+ tools and map consolidation groups
- [x] Task: Design action/type parameter schemas for each mega-tool
- [x] Task: Document breaking changes and migration guide
- [x] Task: Create consolidated tool interface definitions

### 1.2 Implement Consolidated Tools
- [x] Task: Write tests for `manage_project` mega-tool
- [x] Task: Implement `manage_project` with action routing
- [x] Task: Write tests for `search_content` mega-tool
- [x] Task: Implement `search_content` with action routing
- [x] Task: Write tests for `modify_file` mega-tool
- [x] Task: Implement `modify_file` with operation routing
- [x] Task: Write tests for `manage_files` mega-tool
- [x] Task: Implement `manage_files` with action routing
- [x] Task: Write tests for `get_diagnostics` mega-tool
- [x] Task: Implement `get_diagnostics` with type routing
- [x] Task: Write tests for `manage_memory` mega-tool
- [x] Task: Implement `manage_memory` with action routing
- [x] Task: Write tests for `manage_operations` mega-tool
- [x] Task: Implement `manage_operations` with action routing
- [x] Task: Write tests for `read_file` mega-tool
- [x] Task: Implement `read_file` with mode routing
- [x] Task: Write tests for `manage_temp` mega-tool
- [x] Task: Implement `manage_temp` with action routing

### 1.3 Remove Deprecated Tools
- [x] Task: Remove all API key management tools (list_api_keys, reset_api_key_quota, set_rotation_strategy, get_api_key_statistics)
- [x] Task: Remove Mixedbread cloud-specific tools
- [x] Task: Remove old tool implementations from server.py
- [x] Task: Update MCP tool registry to reflect new 9-tool structure

### 1.4 Update Tests and Documentation
- [x] Task: Update all existing tests to use new consolidated tools
- [x] Task: Update CLI to use new tool interfaces
- [x] Task: Update README and documentation with new tool names
- [x] Task: Create migration guide for users

### 1.5 Quality Assurance
- [x] Task: Verify tool count reduced from 50+ to 9
- [x] Task: Run full test suite and ensure >95% coverage
- [x] Task: Verify all mega-tools support actions from consolidated tools
- [x] Task: Integration testing with real-world usage scenarios

- [x] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

---

## Phase 2: Local Vector Store Implementation [checkpoint: c0f2c3e]

### 2.1 Core Infrastructure Setup
- [x] Task: Add dependencies (faiss-cpu, sentence-transformers) to pyproject.toml
- [x] Task: Create LocalVectorBackend class structure
- [x] Task: Implement model loading and caching with startup optimization
- [x] Task: Write tests for model loading and cache behavior

### 2.2 Embedding Model Integration
- [x] Task: Write tests for embedding generation with all three models
- [x] Task: Implement BAAI/bge-small-en-v1.5 integration (default)
- [x] Task: Implement microsoft/codebert-base integration
- [x] Task: Implement all-MiniLM-L6-v2 integration
- [x] Task: Add model configuration via environment variable
- [x] Task: Implement model name storage in index metadata
- [x] Task: Implement model mismatch detection and warning on startup
- [x] Task: Write tests for first-query model loading latency (~2-3s)
- [x] Task: Document expected first-query delay in user guide

### 2.3 Code Chunking Strategy
- [x] Task: Write tests for AST-based chunking
- [x] Task: Implement AST parser for function/class extraction
- [x] Task: Implement hybrid chunking (semantic splitting for large chunks)
- [x] Task: Implement context metadata (parent class, module docstring)
- [x] Task: Write tests for chunk splitting logic

### 2.4 FAISS Index Implementation
- [x] Task: Write tests for FAISS index operations (add, search, persistence)
- [x] Task: Implement IndexFlatIP for exact search
- [x] Task: Implement adaptive switching to IndexIVFFlat at threshold
- [x] Task: Implement index persistence to disk for fast startup
- [x] Task: Implement index loading from persisted state
- [x] Task: Add faiss-gpu compatibility note and fallback to faiss-cpu

### 2.5 Metadata Storage
- [x] Task: Design PostgreSQL schema for vector index metadata
- [x] Task: Write tests for metadata storage operations
- [x] Task: Implement metadata storage (file path, lines, chunk type, model)
- [ ] Task: Add Alembic migration for new schema (deferred - using JSON file storage)
- [x] Task: Implement metadata queries for search results

### 2.6 Search Integration
- [ ] Task: Write tests for search routing (semantic vs regex detection) (deferred - uses existing search routing)
- [ ] Task: Implement query type detection (regex pattern vs semantic) (deferred - uses existing search routing)
- [x] Task: Implement Local Vector + Zoekt search routing (via existing CoreEngine)
- [x] Task: Implement result merging (semantic + exact matches) (via existing CoreEngine)
- [x] Task: Write integration tests for full search pipeline

### 2.7 Remove Mixedbread Cloud Dependencies
- [x] Task: Remove Mixedbread SDK dependency from pyproject.toml
- [x] Task: Remove VectorBackend cloud integration code
- [x] Task: Remove cloud store upload/management tools
- [x] Task: Remove all Mixedbread-related configuration and environment variables
- [x] Task: Update imports and remove dead code

### 2.8 Performance and Quality
- [ ] Task: Write performance benchmarks for search latency (deferred - requires real model)
- [ ] Task: Write benchmarks for index build time (deferred - requires real model)
- [ ] Task: Implement quality metrics tracking (recall, latency percentiles, index size) (deferred)
- [ ] Task: Verify search latency targets (p50 < 20ms, p95 < 50ms) (deferred - requires real model)
- [ ] Task: Verify memory footprint target (< 200MB for 10K files) (deferred - requires real model)
- [x] Task: Run full test suite and ensure >95% coverage (178 tests passing)

### 2.9 Migration and Documentation
- [x] Task: Document fresh start migration approach
- [x] Task: Document model switching requirements (full reindex)
- [x] Task: Update installation documentation with new dependencies
- [x] Task: Update README with local vector store architecture
- [x] Task: Create user guide for local semantic search (docs/LOCAL_VECTOR_STORE.md)

- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)
