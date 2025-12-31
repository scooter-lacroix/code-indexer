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

- [ ] Task: Conductor - Codex-Reviewer Rigor Check 'Phase 2' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent to conduct comprehensive review
  - Review must cover: local vector implementation, search integration, migration docs
  - All findings must be debugged (amp-code or opencode-scaffolder)
  - After fixes, codex-reviewer re-reviews for rigor verification
  - Only proceed to Phase 3 when codex-reviewer approves

---

## Phase 3: Search Integration, Optimization, and Production Readiness

### 3.1 Multi-Backend Search Result Merging
- [ ] Task: Design unified search result merger
  - Define result schemas from Elasticsearch, FAISS, Zoekt
  - Design scoring normalization across backends
  - Define merge strategies (weighted, reciprocal rank fusion, custom)
  - Document configuration options for merge behavior

- [ ] Task: Implement result merger core
  - Create SearchResultMerger class
  - Implement score normalization (min-max, z-score, or percentile)
  - Implement reciprocal rank fusion (RRF) algorithm
  - Implement configurable weighted merging
  - Add deduplication of identical results from multiple backends

- [ ] Task: Write tests for result merging
  - Unit test: score normalization with different score ranges
  - Unit test: RRF merging with mock backend results
  - Unit test: weighted merging with custom weights
  - Unit test: deduplication of identical results
  - Integration test: end-to-end search with all three backends

- [ ] Task: Integrate merger into search pipeline
  - Update search_content router to use merger
  - Add merge configuration to config.yaml
  - Implement merge strategy selection based on query type
  - Add support for backend-specific result filtering

- [ ] Task: Codex-Reviewer Rigor Check 'Multi-Backend Merging'
  - Deploy codex-reviewer to review result merger implementation
  - Review: test coverage, edge cases, performance implications
  - All findings debugged before proceeding

### 3.2 Performance Optimization Suite
- [ ] Task: Implement performance benchmark framework
  - Create benchmark suite with pytest-benchmark or similar
  - Define benchmark scenarios (small/medium/large codebases)
  - Implement latency tracking (p50, p95, p99)
  - Implement throughput tracking (queries per second)
  - Create benchmark result visualization

- [ ] Task: Write performance benchmarks for search
  - Benchmark: Local vector search latency (target: p50 < 20ms, p95 < 50ms)
  - Benchmark: Elasticsearch search latency
  - Benchmark: Zoekt exact search latency
  - Benchmark: Merged multi-backend search latency
  - Benchmark: Cold start vs warm start performance

- [ ] Task: Write benchmarks for indexing
  - Benchmark: FAISS index build time per file
  - Benchmark: Elasticsearch indexing throughput
  - Benchmark: Full reindex time for 1K/10K/100K file projects
  - Benchmark: RabbitMQ message processing rate

- [ ] Task: Implement adaptive batching for indexing
  - Analyze optimal batch sizes for different backends
  - Implement dynamic batch sizing based on file size
  - Add backpressure detection and handling
  - Implement batch size configuration in config.yaml

- [ ] Task: Optimize memory usage
  - Profile memory footprint for 10K/100K file indices
  - Implement FAISS index compression options
  - Add memory limit enforcement and monitoring
  - Document memory requirements per project size

- [ ] Task: Codex-Reviewer Rigor Check 'Performance Optimization'
  - Deploy codex-reviewer to review benchmarks and optimizations
  - Review: benchmark methodology, optimization safety, regression risk
  - All findings debugged before proceeding

### 3.3 Quality Metrics and Monitoring
- [ ] Task: Implement quality metrics tracking
  - Define metrics: recall rate, precision, MRR, latency percentiles
  - Implement metrics storage in PostgreSQL
  - Create metrics aggregation and reporting
  - Add metrics exposure via get_diagnostics tool

- [ ] Task: Implement query type detection enhancement
  - Enhance regex vs semantic detection logic
  - Add support for hybrid queries (regex + semantic)
  - Implement query classification confidence scoring
  - Add query type statistics tracking

- [ ] Task: Write tests for query detection
  - Unit test: pure regex queries detected correctly
  - Unit test: pure semantic queries detected correctly
  - Unit test: hybrid queries handled appropriately
  - Integration test: end-to-end query classification

- [ ] Task: Implement search result quality validation
  - Create automated relevance validation
  - Implement A/B testing framework for search strategies
  - Add user feedback collection mechanism
  - Define quality thresholds and alerts

- [ ] Task: Codex-Reviewer Rigor Check 'Quality Metrics'
  - Deploy codex-reviewer to review metrics implementation
  - Review: metric accuracy, tracking overhead, actionability
  - All findings debugged before proceeding

### 3.4 Production Features: Progress, Retry, and Resilience
- [ ] Task: Implement operation progress tracking
  - Design progress event structure (operation_id, phase, progress_pct)
  - Implement progress update mechanism in indexing pipeline
  - Add progress polling endpoint to manage_operations
  - Create progress bar visualization for CLI

- [ ] Task: Implement automatic retry logic
  - Define retryable error conditions (network, timeout, 5xx)
  - Implement exponential backoff strategy
  - Add max retry limit configuration
  - Implement dead letter queue for permanently failed items

- [ ] Task: Implement hybrid sync/async strategy
  - Define threshold for sync vs async indexing (file count, project size)
  - Implement configuration for hybrid strategy in config.yaml
  - Add automatic strategy selection logic
  - Document trade-offs and when to use each strategy

- [ ] Task: Write tests for production features
  - Unit test: progress tracking accuracy
  - Unit test: retry logic with various failure scenarios
  - Unit test: exponential backoff behavior
  - Integration test: end-to-end sync/async hybrid flow

- [ ] Task: Codex-Reviewer Rigor Check 'Production Features'
  - Deploy codex-reviewer to review production readiness
  - Review: error handling, retry safety, progress accuracy
  - All findings debugged before proceeding

### 3.5 Database Migration (Alembic)
- [ ] Task: Set up Alembic migration infrastructure
  - Install and configure Alembic
  - Initialize migration directory
  - Configure database connection in alembic.ini
  - Document migration workflow

- [ ] Task: Create initial migration for vector metadata
  - Generate initial migration from current schema
  - Add upgrade/downgrade paths
  - Test migration on fresh database
  - Test rollback from migration

- [ ] Task: Create migration for quality metrics tables
  - Design metrics storage schema
  - Create migration for metrics tables
  - Implement metrics aggregation queries
  - Add indexes for performance

- [ ] Task: Write migration tests
  - Test upgrade migration preserves data
  - Test downgrade migration restores state
  - Test migration on large datasets
  - Test migration rollback safety

- [ ] Task: Codex-Reviewer Rigor Check 'Database Migration'
  - Deploy codex-reviewer to review migrations
  - Review: migration safety, rollback capability, data loss risk
  - All findings debugged before proceeding

### 3.6 CLI Enhancements
- [ ] Task: Implement code-search CLI command
  - Create `code-search` CLI entry point
  - Implement interactive search with result display
  - Add support for backend selection and filtering
  - Implement search result highlighting and preview

- [ ] Task: Add search result export
  - Implement JSON/CSV export of search results
  - Add support for custom output formats
  - Create result summarization feature
  - Add batch search from file

- [ ] Task: Write CLI tests
  - Unit test: CLI command parsing and validation
  - Integration test: CLI search with real backends
  - Test: output formatting and export functionality

- [ ] Task: Codex-Reviewer Rigor Check 'CLI Enhancements'
  - Deploy codex-reviewer to review CLI implementation
  - Review: UX, error messages, output quality
  - All findings debugged before proceeding

### 3.7 Documentation and Final Quality Gates
- [ ] Task: Update architecture documentation
  - Document multi-backend search architecture
  - Create diagram of search result merging flow
  - Document performance characteristics and limits
  - Update troubleshooting guide

- [ ] Task: Create performance tuning guide
  - Document configuration options for optimization
  - Create tuning guide for different project sizes
  - Add hardware recommendations
  - Document known bottlenecks and solutions

- [ ] Task: Run full test suite with coverage
  - Execute pytest with coverage reporting
  - Verify >95% coverage maintained
  - Run performance benchmark suite
  - Verify all quality metrics pass thresholds

- [ ] Task: Codex-Reviewer Rigor Check 'Phase 3 Final' (Zero Tolerance - Tsar of Excellence)
  - Deploy codex-reviewer agent for comprehensive Phase 3 review
  - Review must cover: all Phase 3 implementations, test coverage, documentation
  - All findings must be debugged (amp-code or opencode-scaffolder)
  - After fixes, codex-reviewer re-reviews for rigor verification
  - Only proceed to user manual verification when codex-reviewer approves

- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

---

## Phase 3 Success Criteria

Phase 3 is complete when:
- [ ] Multi-backend search result merging implemented and tested
- [ ] Performance benchmarks passing with documented baselines
- [ ] Quality metrics tracking operational with thresholds defined
- [ ] Progress tracking, retry logic, and hybrid strategy all functional
- [ ] Alembic migrations implemented and tested
- [ ] CLI enhancements (code-search command) functional
- [ ] All tests passing with >95% coverage
- [ ] Codex-reviewer approves all Phase 3 rigor checks
- [ ] User manual verification passes
