# Plan: Unified Core Engine Integration

## Phase 1: Deep Analysis and Architectural Mapping
- [ ] Task: Audit target repository source code for search, semantic indexing, and reranking modules.
- [ ] Task: Map target components to existing `code-indexer` structures (e.g., `src/code_index_mcp/search/`, `src/code_index_mcp/storage/`).
- [ ] Task: Design the Unified Core Engine interface to support both standalone and augmented modes.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Deep Analysis and Architectural Mapping' (Protocol in workflow.md)

## Phase 2: Core Engine Implementation & Rebranding
- [ ] Task: Implement the semantic search and indexing components within `code-indexer`.
- [ ] Task: Port the web search and reranking features into the Core Engine.
- [ ] Task: Merge existing Zoekt functionality into the new Core Engine logic.
- [ ] Task: Perform a global codebase sweep to rename and rebrand all ported components (ensuring no external names remain).
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Core Engine Implementation & Rebranding' (Protocol in workflow.md)

## Phase 3: Intelligent Routing and Integration
- [ ] Task: Implement the intelligent routing logic to prioritize the Core Engine.
- [ ] Task: Enable augmentation logic to pull metadata from PostgreSQL/Elasticsearch when available.
- [ ] Task: Verify "Database-less" standalone operation using only the Core Engine.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Intelligent Routing and Integration' (Protocol in workflow.md)

## Phase 4: Verification and Finalization
- [ ] Task: Achieve >95% test coverage for all new Core Engine components.
- [ ] Task: Perform performance benchmarking to ensure no regressions in indexing or search speed.
- [ ] Task: Final documentation update (strictly avoiding legacy names).
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Verification and Finalization' (Protocol in workflow.md)
