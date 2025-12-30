# Specification: Unified Core Engine Integration

## Overview
This track focuses on merging the capabilities from the target external repository into the `code-indexer` project. The goal is to create a unified, high-performance search engine that serves as the primary driver for all search and indexing operations, while maintaining a clear path for deprecating existing PostgreSQL and Elasticsearch dependencies.

## Key Objectives
-   **Deep Analysis:** Perform a comprehensive audit of the target source code to identify critical components for search, semantic indexing, web search, and reranking.
-   **Core Porting:** Integrate these components into the `code-indexer` architecture as a new "Core Engine".
-   **Rebranding:** Ensure absolute removal of all external project names within the codebase and documentation.
-   **Intelligent Routing:** Implement logic that prioritizes the new Core Engine and only leverages PostgreSQL/Elasticsearch for augmentation where they provide unique value.
-   **Standalone Capability:** Ensure `code-indexer` can operate fully with the new Core Engine without any external database dependencies.

## Technical Requirements
-   **Search Engine:** Implement/port the vector/semantic search and indexing logic.
-   **Web Search & Reranking:** Integrate these features as modular components within the Core Engine.
-   **Zoekt Merger:** Blend existing Zoekt-based search capabilities with the new Core Engine for optimal performance.
-   **Routing Layer:** Develop a robust dispatcher that evaluates queries and routes them to the appropriate backend component (Core Engine primary, Legacy Backends for augmentation).

## Success Criteria
-   All target features are functional within `code-indexer`.
-   No regressions in current indexing or search performance.
-   Zero mentions of the external project name in the new codebase.
-   Project can run and search effectively in a "database-less" mode using only the Core Engine.
