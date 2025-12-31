# Local Vector Store Guide

## Overview

The Code Indexer now includes a **local-first vector store** using FAISS (Facebook AI Similarity Search) and sentence-transformers. This provides:

- **Zero cloud dependencies** - No API calls, no rate limits, no privacy concerns
- **Zero cost** - No API fees, no per-query charges
- **Fast performance** - p50 < 20ms, p95 < 50ms (after model loaded)
- **Full privacy** - All embeddings generated and stored locally
- **Adaptive indexing** - Automatically scales from exact to approximate search

## Architecture

```
Query -> LocalVectorBackend -> FAISS Index -> Results
         |                       |
         |                       +-> Vector Metadata (JSON)
         |
         +-> sentence-transformers (Embedding Model)
```

### Components

| Component | Purpose |
|-----------|---------|
| **FAISS** | High-performance vector similarity search |
| **sentence-transformers** | Local embedding generation from text |
| **LocalVectorBackend** | Python interface managing the index and model |
| **PostgreSQL** | Metadata storage (file paths, line numbers, chunk types) |

### Adaptive Index Strategy

The vector store automatically scales based on index size:

| Vector Count | Index Type | Search Type | Description |
|--------------|------------|-------------|-------------|
| < 100,000 | IndexFlatIP | Exact | Inner product search, 100% recall |
| >= 100,000 | IndexIVFFlat | Approximate | IVF clustering, fast search with ~95% recall |

The threshold is configurable via `FAISS_INDEX_THRESHOLD` environment variable.

## Supported Models

| Model | Dimensions | Size | Description | Best For |
|-------|------------|------|-------------|----------|
| **BAAI/bge-small-en-v1.5** (default) | 384 | ~130 MB | High-quality general-purpose embeddings | Most codebases |
| **microsoft/codebert-base** | 768 | ~450 MB | Code-specific embeddings | Code-heavy repositories |
| **all-MiniLM-L6-v2** | 384 | ~80 MB | Lightweight general-purpose | Resource-constrained environments |

### Model Selection

Choose your model via the `LOCAL_VECTOR_MODEL` environment variable:

```bash
export LOCAL_VECTOR_MODEL=BAAI/bge-small-en-v1.5  # Default, balanced
export LOCAL_VECTOR_MODEL=microsoft/codebert-base  # Code-specific
export LOCAL_VECTOR_MODEL=all-MiniLM-L6-v2  # Lightweight
```

### Switching Models

**Important:** Switching embedding models requires a **full reindex**. The index stores model metadata and will warn you on startup if there's a mismatch.

```bash
# Reindex after changing models
python -m code_index_mcp.cli reindex --force
```

## Installation

### Prerequisites

Ensure you have Python 3.10+ installed.

### Install Dependencies

```bash
# Using uv (recommended)
uv pip install 'faiss-cpu>=1.7.4' 'sentence-transformers>=2.2.0' 'numpy>=1.24.0'

# Using pip
pip install 'faiss-cpu>=1.7.4' 'sentence-transformers>=2.2.0' 'numpy>=1.24.0'
```

**Note:** `faiss-gpu` is not yet available for Python 3.11+. Use `faiss-cpu` for now.

### Verify Installation

```python
from code_index_mcp.core_engine.local_vector_backend import get_local_vector_backend_status

status = get_local_vector_backend_status()
print(status)
# Output:
# {
#     "available": true,
#     "faiss_available": true,
#     "sentence_transformers_available": true,
#     "numpy_available": true,
#     "supported_models": {...},
#     "faiss_version": "1.7.4",
#     "sentence_transformers_version": "2.2.2",
#     "numpy_version": "1.24.3"
# }
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_VECTOR_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model to use |
| `FAISS_INDEX_THRESHOLD` | `100000` | Vectors before switching to IVFFlat |
| `FAISS_INDEX_PATH` | `./faiss_index` | Directory for index storage |
| `TRANSFORMERS_CACHE` | System default | Cache directory for models |

### Example Configuration

```bash
# .env file or shell configuration
export LOCAL_VECTOR_MODEL=BAAI/bge-small-en-v1.5
export FAISS_INDEX_THRESHOLD=100000
export FAISS_INDEX_PATH=./data/faiss_index
export TRANSFORMERS_CACHE=./data/models
```

## Performance Characteristics

### First Query vs Subsequent Queries

| Metric | First Query | Subsequent Queries |
|--------|-------------|-------------------|
| Latency | ~2-3 seconds (model loading) | < 20ms (p50), < 50ms (p95) |
| Memory | ~200MB (model + index) | Same (cached) |

### Index Build Performance

| Operation | Time (10K file codebase) |
|-----------|-------------------------|
| Index build | ~5-10 minutes |
| Index load from disk | < 1 second |
| Index save to disk | ~2 seconds |

### Memory Footprint

| Component | Memory (approx.) |
|-----------|------------------|
| Model (bge-small-en-v1.5) | ~130 MB |
| Index (10K files) | ~50 MB |
| Metadata | ~20 MB |
| **Total** | ~200 MB |

### Scalability

| Codebase Size | Index Size | Search Latency (p95) |
|---------------|------------|---------------------|
| 1,000 files | ~5 MB | < 20ms |
| 10,000 files | ~50 MB | < 50ms |
| 100,000 files | ~500 MB | < 100ms |
| 1,000,000 files | ~5 GB | < 200ms |

## Code Chunking Strategy

The vector store uses intelligent chunking to preserve code structure:

### Python Files (AST-based)

1. **Parse** Python code with AST
2. **Extract** functions, classes, imports separately
3. **Preserve** metadata:
   - Start/end line numbers
   - Chunk type (function, class, module, import)
   - Parent context (class name for methods)
4. **Split** large chunks (>512 tokens) at logical boundaries

### Non-Python Files (Line-based)

- Split into ~100-line chunks with 10-line overlap
- Preserves context across chunk boundaries

### Chunk Metadata

Each chunk includes:
```python
{
    "file_path": "src/module.py",
    "chunk_index": 0,
    "start_line": 1,
    "end_line": 25,
    "chunk_type": "function",
    "parent_context": "MyClass",
    "embedding_model": "BAAI/bge-small-en-v1.5"
}
```

## Usage Examples

### Basic Semantic Search

```python
from code_index_mcp.core_engine.local_vector_backend import LocalVectorBackend

# Initialize
backend = LocalVectorBackend(
    model_name="BAAI/bge-small-en-v1.5",
    index_path="./faiss_index"
)
await backend.initialize()

# Search
results = await backend.search(
    store_ids=["my_project"],
    query="How does authentication work?",
    options=SearchOptions(top_k=10)
)

# Results include file paths, line numbers, and similarity scores
for result in results.data:
    print(f"{result.metadata.path}:{result.generated_metadata['start_line']}")
    print(f"Score: {result.score:.3f}")
```

### Query Routing

The Unified Core Engine automatically routes queries:

| Query Type | Backend |
|------------|---------|
| "function.*auth" (regex) | Zoekt |
| "How does authentication work?" (semantic) | Local Vector |
| "authentication" (hybrid) | Both, merged results |

## Migration from Mixedbread Cloud

### What Changed

| Before | After |
|--------|-------|
| Mixedbread cloud API | Local FAISS index |
| API calls for embeddings | Local sentence-transformers |
| Cloud-based vector store | Local disk-based index |
| API rate limits | No limits |
| Privacy concerns (data sent to cloud) | Full privacy (local only) |

### Migration Steps

1. **Install local dependencies:**
   ```bash
   uv pip install 'faiss-cpu>=1.7.4' 'sentence-transformers>=2.2.0'
   ```

2. **Remove old environment variables:**
   ```bash
   # No longer needed
   unset MIXEDBREAD_API_KEY
   unset CORE_ENGINE_API_KEY
   ```

3. **Set new configuration (optional, has defaults):**
   ```bash
   export LOCAL_VECTOR_MODEL=BAAI/bge-small-en-v1.5
   export FAISS_INDEX_PATH=./faiss_index
   ```

4. **Reindex your codebase:**
   ```bash
   python -m code_index_mcp.cli reindex --force
   ```

### Data Migration

- **No automatic migration** - Index formats are incompatible
- **Full reindex required** - Old indexes cannot be converted
- **Fresh start approach** - All indexes are wiped on migration

## Troubleshooting

### Model Loading Issues

**Problem:** First search takes 2-3 seconds

**Solution:** This is expected behavior. The model is loaded once and cached for subsequent searches.

### Model Mismatch Warning

**Problem:** Warning on startup about model mismatch

**Solution:** Either:
- Use the same model: `export LOCAL_VECTOR_MODEL=<model_from_warning>`
- Reindex with new model: `python -m code_index_mcp.cli reindex --force`

### Out of Memory

**Problem:** System runs out of memory during indexing

**Solution:**
- Use a smaller model: `export LOCAL_VECTOR_MODEL=all-MiniLM-L6-v2`
- Index in smaller batches
- Reduce `FAISS_INDEX_THRESHOLD`

### Slow Search After Index Growth

**Problem:** Search gets slower as index grows

**Solution:** The index automatically upgrades to IndexIVFFlat at 100,000 vectors. Adjust threshold:

```bash
export FAISS_INDEX_THRESHOLD=50000  # Upgrade earlier
```

### Index Corruption

**Problem:** Index fails to load or produces errors

**Solution:** Rebuild the index:

```bash
rm -rf ./faiss_index
python -m code_index_mcp.cli reindex --force
```

## Advanced Topics

### Custom Index Threshold

```python
backend = LocalVectorBackend(
    model_name="BAAI/bge-small-en-v1.5",
    index_threshold=50000  # Upgrade to IVFFlat at 50K vectors
)
```

### Index Persistence

Indexes are automatically saved to disk:

```
faiss_index/
├── index.faiss              # FAISS index file
├── metadata.json            # Index metadata (model, version, counts)
└── vectors_metadata.json    # Per-vector metadata
```

### Model Caching

Models are cached at class level for sharing across instances:

```python
# Multiple backend instances share the same model
backend1 = LocalVectorBackend()
backend2 = LocalVectorBackend()
# Both use the same cached model
```

## Security

The local vector store includes several security features:

- **Path traversal protection** - All file paths validated
- **Resource limits** - Maximum vectors, file sizes, query lengths
- **Input sanitization** - All user inputs validated
- **Model load throttling** - Semaphore limits concurrent model loads

See `src/code_index_mcp/core_engine/local_vector_backend.py` for implementation details.

## References

- [FAISS Documentation](https://github.com/facebookresearch/faiss)
- [sentence-transformers Documentation](https://www.sbert.net/)
- [BGE Embedding Models](https://huggingface.co/BAAI/bge-small-en-v1.5)
- [CodeBERT](https://github.com/microsoft/CodeBERT)

## Future Enhancements

Planned improvements:

- [ ] GPU support via faiss-gpu (when Python 3.11+ compatible)
- [ ] Distributed vector search for multi-machine setups
- [ ] Additional embedding models (multilingual, domain-specific)
- [ ] Automatic model selection based on codebase type
- [ ] Incremental index updates without full rebuild
