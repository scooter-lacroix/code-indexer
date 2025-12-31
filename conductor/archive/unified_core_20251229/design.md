# Unified Core Engine Design

## Architecture

The "Unified Core Engine" will be a new module in `src/code_index_mcp/core_engine/` (or similar) that acts as the central hub for search and indexing.

### 1. `CoreEngine` Class
- **Responsibility:** Main entry point for search and indexing operations.
- **Methods:**
  - `search(query: str, options: SearchOptions) -> SearchResult`
  - `index_file(file_path: str, content: str, metadata: dict)`
  - `delete_file(file_path: str)`
  - `ask(question: str) -> Answer` (RAG capability)
- **Routing:**
  - Holds references to `VectorBackend` (the ported "mgrep" logic) and `LegacyBackend` (PostgreSQL/Elasticsearch/Zoekt).
  - Implements logic to decide which backend to query (e.g., semantic queries -> Vector, regex -> Legacy/Zoekt).

### 2. `VectorBackend` Class
- **Responsibility:** Interface with the vector storage service (Mixedbread API).
- **Implementation:** Python equivalent of `MixedbreadStore`.
- **Features:**
  - Upload/Delete files.
  - Semantic Search.
  - Reranking.
  - Web Search integration.

### 3. Integration Points

#### Indexing
- Update `src/code_index_mcp/realtime_indexer.py` (and `incremental_indexer.py`) to call `CoreEngine.index_file` in addition to (or instead of) the current DB updates.
- The "Unified" nature means we ideally write to *both* or migrate entirely. For this track, we write to *both* (dual-mode) but prioritize the Core Engine for reading.

#### Search
- Create a new tool/endpoint `unified_search` (or update `search_code_advanced`) to use `CoreEngine.search`.
- The `CoreEngine.search` will:
  1. Check if `VectorBackend` is available and appropriate for the query.
  2. If yes, query it.
  3. If "Web Search" is requested, include it.
  4. If query is purely regex/symbolic and `LegacyBackend` is better suited (e.g., Zoekt), query that.
  5. Merge/Rerank results if needed.

## File Structure

```
src/code_index_mcp/
  ├── core_engine/
  │   ├── __init__.py
  │   ├── engine.py          # CoreEngine class (Router)
  │   ├── vector_store.py    # VectorBackend class (Mixedbread API client)
  │   ├── types.py           # Data models
  │   └── utils.py
  ...
```

## Rebranding
- All internal classes will use generic names (`VectorStore`, `CoreEngine`).
- Configuration will use `CORE_ENGINE_API_KEY` instead of `MIXEDBREAD_API_KEY` (mapped internally).
