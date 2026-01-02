# Code-Indexer Restructuring Plan: Library-First Architecture

**Version:** 1.0  
**Date:** 2025-12-30  
**Status:** Implementation Ready  
**Estimated Duration:** 5 weeks (1 week per phase)

---

## Executive Summary

This plan transforms code-indexer from an MCP-first tool into a versatile library-first architecture that supports multiple integration methods while maintaining backward compatibility. The transformation preserves all existing functionality while opening pathways to native integrations with Claude Code, VS Code, Ollama, and other AI tools through their preferred protocols.

**Core Principle:** The indexing and search engine becomes a shared library that multiple thin interface adapters consume, rather than being tightly coupled to the MCP protocol.

**Key Outcomes:**
- Core library (90% of code) usable by any Python application
- Native extensions for direct integration (10-100x faster than MCP)
- LSP server for universal IDE support
- HTTP API for language-agnostic access
- MCP server maintained for backward compatibility
- One-line installer that auto-configures detected tools

---

## Current State Analysis

### Architecture Snapshot

```
code-indexer/
├── src/code_index_mcp/           # Everything is MCP-coupled
│   ├── server.py                 # 2,800+ lines, MCP + logic mixed
│   ├── core_engine/              # Search backends
│   │   ├── engine.py
│   │   ├── vector_store.py
│   │   ├── local_vector_backend.py
│   │   └── zoekt.py
│   ├── storage/                  # Database backends
│   │   ├── postgresql_storage.py
│   │   ├── elasticsearch_backend.py
│   │   └── dal_factory.py
│   ├── cli.py                    # code-search command
│   └── [40+ other files]
├── plugins/code_indexer/
│   ├── skills/code-search/SKILL.md
│   └── hooks/start_watch.py
└── pyproject.toml

Current Integration: MCP only
Lines of Code: ~15,000
```

### Strengths to Preserve

1. **Mature core functionality** - Hybrid search (vector + symbolic), version tracking, incremental indexing
2. **Robust infrastructure** - PostgreSQL metadata, Elasticsearch search, FAISS vectors, Zoekt integration
3. **9 consolidated mega-tools** - Already reduced from 50+ tools
4. **Comprehensive testing** - Test infrastructure exists
5. **Documentation** - ARCHITECTURE.md, TOOLS_LIST.md, etc.

### Problems to Solve

1. **MCP coupling** - Core logic mixed with MCP protocol handling in server.py
2. **Limited reach** - Only accessible via MCP clients
3. **Performance overhead** - JSON-RPC serialization for every operation
4. **Installation complexity** - Multiple manual steps, no auto-detection
5. **Integration friction** - AI tools must support MCP to use code-indexer

---

## Target Architecture

### Directory Structure (Detailed)

```
code-indexer/
├── src/
│   └── code_indexer/                    # Core library (renamed from code_index_mcp)
│       ├── __init__.py                  # Public API exports
│       ├── version.py                   # Version info
│       │
│       ├── core/                        # Core indexing & search logic
│       │   ├── __init__.py
│       │   ├── indexer.py               # Main CodeIndexer class
│       │   ├── searcher.py              # Unified search interface
│       │   ├── chunker.py               # Code chunking strategies
│       │   ├── file_tracker.py          # File change tracking
│       │   └── operations.py            # Operation tracking
│       │
│       ├── backends/                    # Storage & search backends
│       │   ├── __init__.py
│       │   ├── base.py                  # Abstract base classes
│       │   ├── postgresql.py            # PostgreSQL backend
│       │   ├── elasticsearch.py         # Elasticsearch backend
│       │   ├── faiss_store.py           # Local FAISS vector store
│       │   ├── zoekt.py                 # Zoekt integration
│       │   └── dal.py                   # Data Access Layer
│       │
│       ├── models/                      # Data models
│       │   ├── __init__.py
│       │   ├── file.py                  # File metadata models
│       │   ├── search.py                # Search result models
│       │   └── operation.py             # Operation models
│       │
│       ├── utils/                       # Shared utilities
│       │   ├── __init__.py
│       │   ├── config.py                # Configuration management
│       │   ├── logging.py               # Structured logging
│       │   ├── memory.py                # Memory management
│       │   └── path.py                  # Path utilities
│       │
│       └── exceptions.py                # Custom exceptions
│
├── interfaces/                          # Thin interface adapters
│   ├── mcp/                            # MCP server (backward compat)
│   │   ├── __init__.py
│   │   ├── server.py                   # MCP protocol handler (~200 lines)
│   │   ├── tools.py                    # Tool definitions
│   │   └── README.md
│   │
│   ├── cli/                            # Command-line interface
│   │   ├── __init__.py
│   │   ├── main.py                     # CLI entry point
│   │   ├── commands/                   # CLI commands
│   │   │   ├── search.py
│   │   │   ├── index.py
│   │   │   └── config.py
│   │   └── README.md
│   │
│   ├── extensions/                     # Native AI tool extensions
│   │   ├── __init__.py
│   │   ├── base.py                     # Base extension class
│   │   │
│   │   ├── claude_code/               # Claude Code extension
│   │   │   ├── __init__.py
│   │   │   ├── extension.py           # Direct Python API
│   │   │   ├── manifest.json          # Extension metadata
│   │   │   ├── install.py             # Installation helper
│   │   │   └── README.md
│   │   │
│   │   ├── opencode/                  # OpenCode plugin
│   │   │   ├── __init__.py
│   │   │   ├── plugin.py
│   │   │   ├── plugin.json
│   │   │   └── README.md
│   │   │
│   │   ├── gemini_cli/                # Gemini CLI plugin
│   │   │   ├── __init__.py
│   │   │   ├── plugin.py
│   │   │   └── README.md
│   │   │
│   │   ├── qwen_code/                 # Qwen Code extension
│   │   │   └── [similar structure]
│   │   │
│   │   └── template/                   # Template for new extensions
│   │       ├── extension.py.template
│   │       └── README.md
│   │
│   ├── lsp/                            # Language Server Protocol
│   │   ├── __init__.py
│   │   ├── server.py                   # LSP server (~300 lines)
│   │   ├── handlers.py                 # LSP request handlers
│   │   ├── capabilities.json           # LSP capabilities
│   │   └── README.md
│   │
│   └── api/                            # HTTP REST API
│       ├── __init__.py
│       ├── server.py                   # FastAPI server (~200 lines)
│       ├── routes/                     # API routes
│       │   ├── search.py
│       │   ├── index.py
│       │   └── health.py
│       ├── middleware.py               # Auth, logging, etc.
│       ├── openapi.yaml                # API specification
│       └── README.md
│
├── scripts/                             # Utility scripts
│   ├── install.sh                       # One-line installer (Unix)
│   ├── install.ps1                      # One-line installer (Windows)
│   ├── detect_tools.py                  # Auto-detect AI tools
│   ├── migrate.py                       # Migration helper
│   └── setup_dev.py                     # Development setup
│
├── tests/                               # Test suite
│   ├── unit/                           # Unit tests
│   │   ├── core/
│   │   ├── backends/
│   │   └── utils/
│   ├── integration/                    # Integration tests
│   │   ├── test_mcp.py
│   │   ├── test_extensions.py
│   │   ├── test_lsp.py
│   │   └── test_api.py
│   └── fixtures/                       # Test fixtures
│
├── docs/                                # Documentation
│   ├── architecture/                   # Architecture docs
│   │   ├── OVERVIEW.md
│   │   ├── CORE_LIBRARY.md
│   │   └── INTERFACES.md
│   ├── integration/                    # Integration guides
│   │   ├── CLAUDE_CODE.md
│   │   ├── VSCODE.md
│   │   ├── OLLAMA.md
│   │   └── CUSTOM.md
│   ├── api/                            # API documentation
│   │   ├── CORE_API.md
│   │   ├── LSP_API.md
│   │   └── HTTP_API.md
│   └── migration/                      # Migration guides
│       ├── FROM_MCP_ONLY.md
│       └── BREAKING_CHANGES.md
│
├── examples/                            # Usage examples
│   ├── basic_usage.py                  # Core library usage
│   ├── claude_code_integration.py      # Extension example
│   ├── custom_backend.py               # Custom backend
│   └── notebooks/                      # Jupyter notebooks
│       └── getting_started.ipynb
│
├── config/                              # Configuration templates
│   ├── config.yaml.example
│   ├── claude_code.json.example
│   ├── vscode.json.example
│   └── lsp_settings.json.example
│
├── docker/                              # Docker configurations
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── dev/
│       └── docker-compose.dev.yml
│
├── .github/                             # GitHub workflows
│   ├── workflows/
│   │   ├── test.yml
│   │   ├── release.yml
│   │   └── docs.yml
│   └── ISSUE_TEMPLATE/
│
├── pyproject.toml                       # Project configuration
├── README.md                            # Main readme
├── CHANGELOG.md                         # Version history
├── LICENSE                              # MIT license
└── CONTRIBUTING.md                      # Contribution guide
```

### Core Library API Design

```python
# src/code_indexer/__init__.py
"""
Code-Indexer: Semantic code search and indexing library

Public API exports for direct Python usage.
"""

from .core.indexer import CodeIndexer
from .core.searcher import SearchOptions, SearchResult
from .backends.dal import get_backend
from .models import FileMetadata, SearchQuery, Operation
from .exceptions import (
    CodeIndexerError,
    BackendError,
    IndexingError,
    SearchError
)

__version__ = "4.0.0"
__all__ = [
    "CodeIndexer",
    "SearchOptions",
    "SearchResult",
    "get_backend",
    "FileMetadata",
    "SearchQuery",
    "Operation",
    "CodeIndexerError",
    "BackendError",
    "IndexingError",
    "SearchError",
]
```

```python
# src/code_indexer/core/indexer.py
"""
Main CodeIndexer class - the entry point for all indexing operations.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio

from ..backends.dal import DataAccessLayer
from ..models import FileMetadata, Operation
from .searcher import Searcher, SearchOptions, SearchResult
from .file_tracker import FileChangeTracker
from ..utils.config import Config
from ..exceptions import IndexingError

class CodeIndexer:
    """
    Main entry point for code indexing and search.
    
    Example usage:
        >>> indexer = CodeIndexer("/path/to/project")
        >>> await indexer.initialize()
        >>> results = await indexer.search("authentication logic")
        >>> for result in results:
        ...     print(f"{result.file_path}: {result.score}")
    """
    
    def __init__(
        self,
        workspace_path: str | Path,
        config: Optional[Config] = None,
        **kwargs
    ):
        """
        Initialize indexer for a workspace.
        
        Args:
            workspace_path: Root directory of the codebase
            config: Optional configuration object
            **kwargs: Additional configuration options
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.config = config or Config.from_workspace(self.workspace_path, **kwargs)
        
        # Core components (lazy-loaded)
        self._dal: Optional[DataAccessLayer] = None
        self._searcher: Optional[Searcher] = None
        self._tracker: Optional[FileChangeTracker] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all backends and components."""
        if self._initialized:
            return
        
        # Initialize Data Access Layer (PostgreSQL, ES, FAISS)
        self._dal = DataAccessLayer(self.config)
        await self._dal.connect()
        
        # Initialize searcher
        self._searcher = Searcher(self._dal, self.config)
        
        # Initialize file tracker
        self._tracker = FileChangeTracker(self._dal, self.workspace_path)
        
        self._initialized = True
    
    async def index_workspace(
        self,
        force: bool = False,
        incremental: bool = True
    ) -> Operation:
        """
        Index the entire workspace.
        
        Args:
            force: If True, reindex all files (ignore cache)
            incremental: If True, only index changed files
        
        Returns:
            Operation object for tracking progress
        """
        if not self._initialized:
            await self.initialize()
        
        # Discover files
        files = await self._discover_files()
        
        # Create operation tracker
        operation = Operation.create(
            type="index_workspace",
            total_items=len(files)
        )
        
        # Index files (async batch processing)
        await self._dal.index_batch(files, operation_id=operation.id)
        
        return operation
    
    async def search(
        self,
        query: str,
        options: Optional[SearchOptions] = None
    ) -> List[SearchResult]:
        """
        Search the indexed codebase.
        
        Args:
            query: Search query (natural language or regex)
            options: Search options (filters, ranking, etc.)
        
        Returns:
            List of search results with scores and metadata
        """
        if not self._initialized:
            await self.initialize()
        
        return await self._searcher.search(query, options or SearchOptions())
    
    async def index_file(self, file_path: str | Path) -> None:
        """Index a single file."""
        if not self._initialized:
            await self.initialize()
        
        await self._dal.index_file(Path(file_path))
    
    async def get_file_metadata(self, file_path: str | Path) -> FileMetadata:
        """Get metadata for a file."""
        if not self._initialized:
            await self.initialize()
        
        return await self._dal.get_file_metadata(Path(file_path))
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._dal:
            await self._dal.disconnect()
        self._initialized = False
    
    async def __aenter__(self):
        """Async context manager support."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager cleanup."""
        await self.close()
    
    # Private methods
    async def _discover_files(self) -> List[Path]:
        """Discover indexable files in workspace."""
        # Implementation uses config filters
        pass
```

---

## Phase-by-Phase Migration Strategy

### Phase 1: Extract Core Library (Week 1)

**Goal:** Separate core logic from MCP-specific code without breaking existing functionality.

#### Day 1-2: Create New Structure & Move Files

```bash
# 1. Create new directory structure
mkdir -p src/code_indexer/{core,backends,models,utils}
mkdir -p interfaces/{mcp,cli,extensions,lsp,api}

# 2. Move core files (preserve git history)
git mv src/code_index_mcp/core_engine src/code_indexer/core/
git mv src/code_index_mcp/storage src/code_indexer/backends/
git mv src/code_index_mcp/search src/code_indexer/core/search

# 3. Move utilities
git mv src/code_index_mcp/config_manager.py src/code_indexer/utils/config.py
git mv src/code_index_mcp/logger_config.py src/code_indexer/utils/logging.py
git mv src/code_index_mcp/memory_profiler.py src/code_indexer/utils/memory.py

# 4. Extract models
# Create new model files from server.py data structures
touch src/code_indexer/models/{file.py,search.py,operation.py}

# 5. Move interface files
git mv src/code_index_mcp/server.py interfaces/mcp/server.py
git mv src/code_index_mcp/cli.py interfaces/cli/main.py
```

#### Day 3-4: Create Core Library Entry Point

**File:** `src/code_indexer/core/indexer.py` (shown in API design above)

**Key decisions:**
- Use async/await for all I/O operations
- Accept workspace path in constructor (not global state)
- Lazy-load backends (PostgreSQL/ES may not be required)
- Support context manager protocol for resource cleanup

#### Day 5: Update All Imports

**Script:** `scripts/update_imports.py`

```python
#!/usr/bin/env python3
"""
Automatically update imports from code_index_mcp to code_indexer.

Usage: python scripts/update_imports.py
"""

import os
import re
from pathlib import Path

# Import mapping
MAPPINGS = {
    "from code_index_mcp.core_engine": "from code_indexer.core",
    "from code_index_mcp.storage": "from code_indexer.backends",
    "from code_index_mcp.config_manager": "from code_indexer.utils.config",
    "from code_index_mcp.logger_config": "from code_indexer.utils.logging",
    "import code_index_mcp": "import code_indexer",
}

def update_file(file_path: Path):
    """Update imports in a single file."""
    content = file_path.read_text()
    original = content
    
    for old, new in MAPPINGS.items():
        content = content.replace(old, new)
    
    if content != original:
        file_path.write_text(content)
        print(f"Updated: {file_path}")

def main():
    """Update all Python files."""
    root = Path("src/code_indexer")
    for file_path in root.rglob("*.py"):
        update_file(file_path)
    
    # Also update interface files
    for interface_dir in ["interfaces/mcp", "interfaces/cli"]:
        for file_path in Path(interface_dir).rglob("*.py"):
            update_file(file_path)

if __name__ == "__main__":
    main()
```

**Run:**
```bash
python scripts/update_imports.py
```

#### Day 6-7: Test & Fix

```bash
# Run existing tests
pytest tests/ -v

# Fix any import errors
# Most common issues:
# - Circular imports (use TYPE_CHECKING)
# - Missing __init__.py files
# - Relative imports that became absolute
```

**Acceptance Criteria for Phase 1:**
- [ ] All core files moved to `src/code_indexer/`
- [ ] MCP server moved to `interfaces/mcp/`
- [ ] All imports updated and working
- [ ] Existing test suite passes (>95% tests passing)
- [ ] MCP server still works (backward compatibility verified)
- [ ] Core library can be imported: `from code_indexer import CodeIndexer`

---

### Phase 2: Claude Code Native Extension (Week 2)

**Goal:** Create a native Python extension for Claude Code that bypasses MCP entirely.

#### Day 1: Research Claude Code Extension API

**Questions to answer:**
1. Does Claude Code support native Python extensions?
2. What's the extension manifest format?
3. How are extensions loaded (entry point, lifecycle)?
4. What capabilities does the extension API expose?

**If Claude Code doesn't have documented extension API:**
- Fall back to creating a "skill" that wraps the core library
- Use subprocess calls to `code-indexer` CLI instead of MCP
- Still faster than MCP JSON-RPC (no serialization overhead)

#### Day 2-3: Implement Extension

**File:** `interfaces/extensions/claude_code/extension.py`

```python
"""
Claude Code native extension for code-indexer.

This provides direct Python API access, bypassing MCP entirely for 10-100x speed improvement.
"""

from typing import List, Dict, Any, Optional
import asyncio
from pathlib import Path

from code_indexer import CodeIndexer, SearchOptions, SearchResult
from code_indexer.exceptions import CodeIndexerError


class ClaudeCodeExtension:
    """
    Native extension for Claude Code.
    
    This class is instantiated once per workspace and provides direct Python
    access to code-indexer functionality without JSON-RPC overhead.
    """
    
    def __init__(self, workspace_path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the extension for a workspace.
        
        Args:
            workspace_path: Absolute path to the workspace root
            config: Optional configuration dictionary
        """
        self.workspace_path = Path(workspace_path)
        self.config = config or {}
        
        # Initialize core indexer
        self.indexer = CodeIndexer(
            workspace_path=self.workspace_path,
            **self.config
        )
        
        # Async initialization happens in setup()
        self._initialized = False
    
    async def setup(self) -> None:
        """
        Called by Claude Code when extension is loaded.
        
        This performs async initialization of backends.
        """
        if not self._initialized:
            await self.indexer.initialize()
            self._initialized = True
    
    async def teardown(self) -> None:
        """Called by Claude Code when extension is unloaded."""
        await self.indexer.close()
        self._initialized = False
    
    # Core API methods (called directly by Claude Code)
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        file_pattern: Optional[str] = None,
        semantic: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search the codebase.
        
        Args:
            query: Search query (natural language or regex)
            max_results: Maximum number of results
            file_pattern: Optional glob pattern to filter files
            semantic: If True, use semantic search; if False, use regex
        
        Returns:
            List of search results as dictionaries
        """
        options = SearchOptions(
            max_results=max_results,
            file_pattern=file_pattern,
            use_semantic=semantic
        )
        
        results = await self.indexer.search(query, options)
        
        # Convert to dict for Claude Code
        return [
            {
                "file_path": str(result.file_path),
                "line_start": result.line_start,
                "line_end": result.line_end,
                "content": result.content,
                "score": result.score,
                "match_type": result.match_type
            }
            for result in results
        ]
    
    async def index_workspace(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Reindex the workspace.
        
        Args:
            incremental: If True, only index changed files
        
        Returns:
            Operation status dictionary
        """
        operation = await self.indexer.index_workspace(incremental=incremental)
        
        return {
            "operation_id": operation.id,
            "status": operation.status,
            "files_queued": operation.total_items,
            "files_completed": operation.completed_items
        }
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for a specific file."""
        metadata = await self.indexer.get_file_metadata(file_path)
        
        return {
            "path": str(metadata.path),
            "size": metadata.size,
            "language": metadata.language,
            "functions": metadata.functions,
            "classes": metadata.classes,
            "imports": metadata.imports
        }
    
    # Utility methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get extension status (synchronous)."""
        return {
            "initialized": self._initialized,
            "workspace": str(self.workspace_path),
            "backends": {
                "postgresql": self.indexer._dal.postgresql_connected if self._initialized else False,
                "elasticsearch": self.indexer._dal.elasticsearch_connected if self._initialized else False,
                "faiss": self.indexer._dal.faiss_loaded if self._initialized else False
            }
        }


# Extension entry point for Claude Code
def create_extension(workspace_path: str, config: Dict[str, Any]) -> ClaudeCodeExtension:
    """
    Factory function called by Claude Code to create extension instance.
    
    Args:
        workspace_path: Workspace root path
        config: Configuration from Claude Code settings
    
    Returns:
        Extension instance
    """
    return ClaudeCodeExtension(workspace_path, config)
```

**File:** `interfaces/extensions/claude_code/manifest.json`

```json
{
  "name": "code-indexer",
  "version": "4.0.0",
  "display_name": "Code Indexer - Semantic Search",
  "description": "Native semantic code search with local vector store (FAISS)",
  "author": "scooter-lacroix",
  "license": "MIT",
  "repository": "https://github.com/scooter-lacroix/code-indexer",
  
  "entry_point": "extension.py",
  "factory_function": "create_extension",
  "extension_class": "ClaudeCodeExtension",
  
  "capabilities": {
    "search": {
      "semantic": true,
      "regex": true,
      "hybrid": true
    },
    "indexing": {
      "incremental": true,
      "real_time": true,
      "version_tracking": true
    },
    "backends": {
      "local_vector": true,
      "elasticsearch": true,
      "zoekt": true
    }
  },
  
  "configuration": {
    "backend_type": {
      "type": "string",
      "default": "postgresql_elasticsearch_only",
      "description": "Backend storage type",
      "enum": ["sqlite_only", "postgresql_elasticsearch_only"]
    },
    "vector_model": {
      "type": "string",
      "default": "BAAI/bge-small-en-v1.5",
      "description": "Embedding model for semantic search",
      "enum": ["BAAI/bge-small-en-v1.5", "microsoft/codebert-base", "all-MiniLM-L6-v2"]
    },
    "max_results": {
      "type": "integer",
      "default": 10,
      "description": "Default maximum search results"
    }
  },
  
  "dependencies": {
    "python": ">=3.10",
    "packages": [
      "faiss-cpu>=1.7.4",
      "sentence-transformers>=2.2.0",
      "psycopg2-binary>=2.9.0",
      "elasticsearch==8.10.0"
    ]
  },
  
  "lifecycle": {
    "setup": "setup",
    "teardown": "teardown"
  }
}
```

#### Day 4: Installation Helper

**File:** `interfaces/extensions/claude_code/install.py`

```python
#!/usr/bin/env python3
"""
Installation helper for Claude Code extension.

Usage: python -m code_indexer.extensions.claude_code.install
"""

import json
import shutil
from pathlib import Path
import sys


def get_claude_code_extensions_dir() -> Path:
    """Get Claude Code extensions directory."""
    import os
    
    if sys.platform == "darwin":
        base = Path.home() / "Library/Application Support/Claude Code"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", "")) / "Claude Code"
    else:  # Linux
        base = Path.home() / ".config/claude-code"
    
    extensions_dir = base / "extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)
    return extensions_dir


def install_extension():
    """Install extension to Claude Code."""
    # Get extension directory
    ext_dir = get_claude_code_extensions_dir() / "code-indexer"
    
    # Copy extension files
    source_dir = Path(__file__).parent
    
    print(f"Installing to: {ext_dir}")
    
    # Remove existing installation
    if ext_dir.exists():
        shutil.rmtree(ext_dir)
    
    # Copy files
    shutil.copytree(source_dir, ext_dir)
    
    print("✅ Extension installed successfully!")
    print(f"\nExtension location: {ext_dir}")
    print("\nNext steps:")
    print("1. Restart Claude Code")
    print("2. Open a workspace")
    print("3. Use semantic search: 'Search for authentication logic'")
    print("\nConfiguration:")
    print(f"  Settings file: {ext_dir.parent.parent / 'settings.json'}")


def uninstall_extension():
    """Uninstall extension from Claude Code."""
    ext_dir = get_claude_code_extensions_dir() / "code-indexer"
    
    if ext_dir.exists():
        shutil.rmtree(ext_dir)
        print("✅ Extension uninstalled successfully!")
    else:
        print("Extension not installed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall_extension()
    else:
        install_extension()
```

#### Day 5-7: Test & Benchmark

**Benchmark Script:**

```python
# tests/benchmarks/compare_mcp_vs_extension.py
"""
Benchmark MCP vs native extension performance.
"""

import asyncio
import time
from statistics import mean, stdev

from code_indexer import CodeIndexer
from interfaces.mcp.server import CodeIndexMCPServer


async def benchmark_native_extension():
    """Benchmark native extension (direct Python calls)."""
    indexer = CodeIndexer("/path/to/test/project")
    await indexer.initialize()
    
    times = []
    for _ in range(100):
        start = time.perf_counter()
        results = await indexer.search("authentication")
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    
    await indexer.close()
    
    return {
        "mean": mean(times),
        "stdev": stdev(times),
        "min": min(times),
        "max": max(times)
    }


async def benchmark_mcp_server():
    """Benchmark MCP server (JSON-RPC overhead)."""
    server = CodeIndexMCPServer()
    # Simulate MCP call overhead (serialization + RPC)
    
    times = []
    for _ in range(100):
        start = time.perf_counter()
        # Simulate MCP call
        request = {"tool": "search_content", "arguments": {"query": "authentication"}}
        request_json = json.dumps(request)
        result = await server.handle_call(json.loads(request_json))
        result_json = json.dumps(result)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    
    return {
        "mean": mean(times),
        "stdev": stdev(times),
        "min": min(times),
        "max": max(times)
    }


async def main():
    print("Benchmarking Native Extension vs MCP Server\n")
    
    print("Running native extension benchmark...")
    native_stats = await benchmark_native_extension()
    
    print("Running MCP server benchmark...")
    mcp_stats = await benchmark_mcp_server()
    
    print("\n=== Results ===")
    print(f"\nNative Extension:")
    print(f"  Mean: {native_stats['mean']:.2f} ms")
    print(f"  Stdev: {native_stats['stdev']:.2f} ms")
    print(f"  Range: {native_stats['min']:.2f} - {native_stats['max']:.2f} ms")
    
    print(f"\nMCP Server:")
    print(f"  Mean: {mcp_stats['mean']:.2f} ms")
    print(f"  Stdev: {mcp_stats['stdev']:.2f} ms")
    print(f"  Range: {mcp_stats['min']:.2f} - {mcp_stats['max']:.2f} ms")
    
    speedup = mcp_stats['mean'] / native_stats['mean']
    print(f"\n🚀 Speedup: {speedup:.1f}x faster with native extension")


if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance Criteria for Phase 2:**
- [ ] Claude Code extension implemented and working
- [ ] Installation helper tested on macOS, Linux, Windows
- [ ] Benchmark shows >10x speedup vs MCP
- [ ] Documentation complete (README, examples)
- [ ] Manifest.json correctly describes capabilities

---

### Phase 3: LSP Server for Universal IDE Support (Week 3)

**Goal:** Implement Language Server Protocol to support VS Code, Zed, Cursor, Windsurf, and other editors.

#### Day 1: LSP Design

**Capabilities to implement:**

1. **textDocument/definition** - Jump to definition using semantic search
2. **workspace/symbol** - Search symbols across workspace
3. **textDocument/references** - Find all references
4. **textDocument/hover** - Show documentation on hover
5. **workspace/executeCommand** - Custom commands (reindex, etc.)

#### Day 2-4: Implement LSP Server

**File:** `interfaces/lsp/server.py`

```python
"""
Language Server Protocol (LSP) server for code-indexer.

Provides universal IDE integration for VS Code, Zed, Cursor, Windsurf, etc.
"""

import asyncio
from typing import List, Optional
from pathlib import Path

from pygls.server import LanguageServer
from pygls.lsp.types import (
    Location,
    Position,
    Range,
    SymbolInformation,
    SymbolKind,
    InitializeParams,
    TextDocumentIdentifier
)

from code_indexer import CodeIndexer, SearchOptions


class CodeIndexerLSP(LanguageServer):
    """LSP server for code-indexer."""
    
    def __init__(self):
        super().__init__("code-indexer-lsp", "v4.0.0")
        self.indexer: Optional[CodeIndexer] = None
        self.workspace_path: Optional[Path] = None


server = CodeIndexerLSP()


@server.feature("initialize")
async def initialize(params: InitializeParams):
    """Initialize the language server."""
    workspace_folders = params.workspace_folders
    if workspace_folders:
        workspace_path = workspace_folders[0].uri.replace("file://", "")
        server.workspace_path = Path(workspace_path)
        
        # Initialize code indexer
        server.indexer = CodeIndexer(server.workspace_path)
        await server.indexer.initialize()
    
    return {
        "capabilities": {
            "definitionProvider": True,
            "referencesProvider": True,
            "workspaceSymbolProvider": True,
            "hoverProvider": True,
            "executeCommandProvider": {
                "commands": ["codeIndexer.reindex", "codeIndexer.search"]
            }
        }
    }


@server.feature("textDocument/definition")
async def definition(params):
    """
    Find definition using semantic search.
    
    When user Ctrl+clicks on a symbol, search for its definition.
    """
    doc_uri = params.text_document.uri
    position = params.position
    
    # Get the word at cursor position
    document = server.workspace.get_document(doc_uri)
    word = document.word_at_position(position)
    
    # Search for definition
    results = await server.indexer.search(
        f"definition of {word}",
        options=SearchOptions(max_results=1, use_semantic=True)
    )
    
    if results:
        result = results[0]
        return Location(
            uri=f"file://{result.file_path}",
            range=Range(
                start=Position(line=result.line_start, character=0),
                end=Position(line=result.line_end, character=0)
            )
        )
    
    return None


@server.feature("workspace/symbol")
async def workspace_symbol(params):
    """
    Search symbols across workspace.
    
    Triggered by Ctrl+T in VS Code.
    """
    query = params.query
    
    # Search using semantic search
    results = await server.indexer.search(
        query,
        options=SearchOptions(max_results=50, use_semantic=True)
    )
    
    symbols = []
    for result in results:
        symbols.append(
            SymbolInformation(
                name=result.symbol_name or query,
                kind=SymbolKind.Function,  # Could be smarter based on result.chunk_type
                location=Location(
                    uri=f"file://{result.file_path}",
                    range=Range(
                        start=Position(line=result.line_start, character=0),
                        end=Position(line=result.line_end, character=0)
                    )
                )
            )
        )
    
    return symbols


@server.feature("textDocument/hover")
async def hover(params):
    """
    Show documentation on hover.
    
    Use semantic search to find related documentation.
    """
    doc_uri = params.text_document.uri
    position = params.position
    
    document = server.workspace.get_document(doc_uri)
    word = document.word_at_position(position)
    
    # Search for documentation
    results = await server.indexer.search(
        f"documentation for {word}",
        options=SearchOptions(max_results=1, use_semantic=True)
    )
    
    if results:
        result = results[0]
        return {
            "contents": {
                "kind": "markdown",
                "value": f"```python\n{result.content}\n```\n\nScore: {result.score:.2f}"
            }
        }
    
    return None


@server.command("codeIndexer.reindex")
async def reindex_command(params):
    """Custom command to reindex workspace."""
    operation = await server.indexer.index_workspace(incremental=True)
    
    server.show_message(
        f"Reindexing started: {operation.total_items} files queued",
        msg_type=3  # Info
    )
    
    return {"success": True, "operation_id": operation.id}


@server.feature("shutdown")
async def shutdown(params):
    """Cleanup on shutdown."""
    if server.indexer:
        await server.indexer.close()


def main():
    """Start the LSP server."""
    server.start_io()


if __name__ == "__main__":
    main()
```

#### Day 5: VS Code Extension

**File:** `interfaces/lsp/vscode-extension/package.json`

```json
{
  "name": "code-indexer",
  "displayName": "Code Indexer - Semantic Search",
  "description": "Semantic code search with local vector store",
  "version": "4.0.0",
  "publisher": "scooter-lacroix",
  "repository": "https://github.com/scooter-lacroix/code-indexer",
  "engines": {
    "vscode": "^1.80.0"
  },
  "categories": ["Programming Languages", "Other"],
  "activationEvents": ["onStartupFinished"],
  "main": "./out/extension.js",
  "contributes": {
    "configuration": {
      "type": "object",
      "title": "Code Indexer",
      "properties": {
        "codeIndexer.pythonPath": {
          "type": "string",
          "default": "python",
          "description": "Path to Python interpreter"
        },
        "codeIndexer.vectorModel": {
          "type": "string",
          "default": "BAAI/bge-small-en-v1.5",
          "enum": ["BAAI/bge-small-en-v1.5", "microsoft/codebert-base", "all-MiniLM-L6-v2"],
          "description": "Embedding model for semantic search"
        }
      }
    },
    "commands": [
      {
        "command": "codeIndexer.reindex",
        "title": "Code Indexer: Reindex Workspace"
      },
      {
        "command": "codeIndexer.search",
        "title": "Code Indexer: Semantic Search"
      }
    ]
  },
  "scripts": {
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./"
  },
  "devDependencies": {
    "@types/node": "^18.0.0",
    "@types/vscode": "^1.80.0",
    "typescript": "^5.0.0"
  },
  "dependencies": {
    "vscode-languageclient": "^8.0.0"
  }
}
```

**File:** `interfaces/lsp/vscode-extension/src/extension.ts`

```typescript
import * as path from 'path';
import { workspace, ExtensionContext } from 'vscode';
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: ExtensionContext) {
  // Get Python path from configuration
  const config = workspace.getConfiguration('codeIndexer');
  const pythonPath = config.get<string>('pythonPath', 'python');
  
  // Server options
  const serverOptions: ServerOptions = {
    command: pythonPath,
    args: ['-m', 'code_indexer.lsp.server']
  };
  
  // Client options
  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { scheme: 'file', language: 'python' },
      { scheme: 'file', language: 'javascript' },
      { scheme: 'file', language: 'typescript' },
      { scheme: 'file', language: 'go' },
      { scheme: 'file', language: 'rust' },
      // Add more languages as needed
    ],
    synchronize: {
      fileEvents: workspace.createFileSystemWatcher('**/*')
    }
  };
  
  // Create the language client
  client = new LanguageClient(
    'codeIndexer',
    'Code Indexer LSP',
    serverOptions,
    clientOptions
  );
  
  // Start the client (which starts the server)
  client.start();
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  return client.stop();
}
```

#### Day 6-7: Test & Document

**Acceptance Criteria for Phase 3:**
- [ ] LSP server implements core features (definition, symbol search, hover)
- [ ] VS Code extension packaged and tested
- [ ] Works in Zed (via LSP configuration)
- [ ] Works in Cursor (via LSP configuration)
- [ ] Documentation for each editor
- [ ] Performance acceptable (<100ms for symbol search)

---

### Phase 4: HTTP API for Local AI Servers (Week 4)

**Goal:** Create REST API for Ollama, LM Studio, Jan AI, and other tools that prefer HTTP over MCP.

#### Day 1-2: FastAPI Server

**File:** `interfaces/api/server.py`

```python
"""
HTTP REST API for code-indexer.

Provides language-agnostic access for local AI servers (Ollama, LM Studio, Jan AI).
"""

from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from code_indexer import CodeIndexer, SearchOptions
from code_indexer.exceptions import CodeIndexerError


# Request/Response models

class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query (natural language or regex)")
    workspace: str = Field(..., description="Workspace path")
    max_results: int = Field(10, ge=1, le=100, description="Maximum results")
    file_pattern: Optional[str] = Field(None, description="Glob pattern for file filtering")
    semantic: bool = Field(True, description="Use semantic search")


class SearchResult(BaseModel):
    """Search result model."""
    file_path: str
    line_start: int
    line_end: int
    content: str
    score: float
    match_type: str


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    results: List[SearchResult]
    total: int
    elapsed_ms: float


class IndexRequest(BaseModel):
    """Index request model."""
    workspace: str
    incremental: bool = True


class IndexResponse(BaseModel):
    """Index response model."""
    operation_id: str
    status: str
    files_queued: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    backends: dict


# Global indexer cache (workspace_path -> indexer)
_indexers: dict[str, CodeIndexer] = {}


async def get_indexer(workspace: str) -> CodeIndexer:
    """Get or create indexer for workspace."""
    if workspace not in _indexers:
        indexer = CodeIndexer(workspace)
        await indexer.initialize()
        _indexers[workspace] = indexer
    
    return _indexers[workspace]


# Lifespan management

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    print("🚀 Code Indexer API starting...")
    yield
    # Shutdown
    print("🛑 Code Indexer API shutting down...")
    for indexer in _indexers.values():
        await indexer.close()
    _indexers.clear()


# Create app

app = FastAPI(
    title="Code Indexer API",
    description="Semantic code search and indexing API",
    version="4.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "4.0.0",
        "backends": {
            "postgresql": True,
            "elasticsearch": True,
            "faiss": True
        }
    }


@app.post("/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search code semantically.
    
    Example:
        POST /v1/search
        {
            "query": "authentication logic",
            "workspace": "/path/to/project",
            "max_results": 10,
            "semantic": true
        }
    """
    import time
    
    try:
        start = time.perf_counter()
        
        indexer = await get_indexer(request.workspace)
        
        options = SearchOptions(
            max_results=request.max_results,
            file_pattern=request.file_pattern,
            use_semantic=request.semantic
        )
        
        results = await indexer.search(request.query, options)
        
        elapsed = (time.perf_counter() - start) * 1000  # ms
        
        return {
            "query": request.query,
            "results": [
                {
                    "file_path": str(r.file_path),
                    "line_start": r.line_start,
                    "line_end": r.line_end,
                    "content": r.content,
                    "score": r.score,
                    "match_type": r.match_type
                }
                for r in results
            ],
            "total": len(results),
            "elapsed_ms": elapsed
        }
    
    except CodeIndexerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error:
        {str(e)}")


@app.post("/v1/index", response_model=IndexResponse)
async def index_workspace(request: IndexRequest):
    """
    Index a workspace.
    
    Example:
        POST /v1/index
        {
            "workspace": "/path/to/project",
            "incremental": true
        }
    """
    try:
        indexer = await get_indexer(request.workspace)
        operation = await indexer.index_workspace(incremental=request.incremental)
        
        return {
            "operation_id": operation.id,
            "status": operation.status,
            "files_queued": operation.total_items
        }
    
    except CodeIndexerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/v1/workspaces/{workspace}/status")
async def get_workspace_status(workspace: str):
    """Get indexing status for a workspace."""
    indexer = await get_indexer(workspace)
    
    # Return status info
    return {
        "workspace": workspace,
        "initialized": True,
        "file_count": 0,  # TODO: Get from indexer
        "last_indexed": None  # TODO: Get from indexer
    }


# Authentication middleware (optional)

async def verify_token(authorization: str = Header(None)):
    """Verify API token if provided."""
    if authorization:
        # Implement token verification
        pass
    return True


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
```

#### Day 3: OpenAPI Documentation

**File:** `interfaces/api/openapi.yaml`

```yaml
openapi: 3.0.0
info:
  title: Code Indexer API
  description: Semantic code search and indexing REST API
  version: 4.0.0
  contact:
    name: GitHub Repository
    url: https://github.com/scooter-lacroix/code-indexer

servers:
  - url: http://localhost:8765
    description: Local development server

paths:
  /health:
    get:
      summary: Health check
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

  /v1/search:
    post:
      summary: Search code semantically
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchRequest'
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchResponse'

  /v1/index:
    post:
      summary: Index a workspace
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IndexRequest'
      responses:
        '200':
          description: Indexing started
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IndexResponse'

components:
  schemas:
    SearchRequest:
      type: object
      required:
        - query
        - workspace
      properties:
        query:
          type: string
          description: Search query
        workspace:
          type: string
          description: Workspace path
        max_results:
          type: integer
          default: 10
        semantic:
          type: boolean
          default: true

    SearchResponse:
      type: object
      properties:
        query:
          type: string
        results:
          type: array
          items:
            $ref: '#/components/schemas/SearchResult'
        total:
          type: integer
        elapsed_ms:
          type: number

    SearchResult:
      type: object
      properties:
        file_path:
          type: string
        line_start:
          type: integer
        line_end:
          type: integer
        content:
          type: string
        score:
          type: number
        match_type:
          type: string
```

#### Day 4-5: Client Examples

**Python Client:**

```python
# examples/api_client_python.py
"""
Python client example for Code Indexer API.
"""

import requests
from typing import List, Dict, Any


class CodeIndexerClient:
    """Simple Python client for Code Indexer API."""
    
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
    
    def search(
        self,
        query: str,
        workspace: str,
        max_results: int = 10,
        semantic: bool = True
    ) -> Dict[str, Any]:
        """Search code."""
        response = requests.post(
            f"{self.base_url}/v1/search",
            json={
                "query": query,
                "workspace": workspace,
                "max_results": max_results,
                "semantic": semantic
            }
        )
        response.raise_for_status()
        return response.json()
    
    def index(self, workspace: str, incremental: bool = True) -> Dict[str, Any]:
        """Index workspace."""
        response = requests.post(
            f"{self.base_url}/v1/index",
            json={
                "workspace": workspace,
                "incremental": incremental
            }
        )
        response.raise_for_status()
        return response.json()


# Usage example
if __name__ == "__main__":
    client = CodeIndexerClient()
    
    # Index workspace
    result = client.index("/path/to/project")
    print(f"Indexing started: {result['operation_id']}")
    
    # Search
    results = client.search("authentication logic", "/path/to/project")
    print(f"Found {results['total']} results in {results['elapsed_ms']:.2f}ms")
    
    for r in results['results']:
        print(f"  {r['file_path']}:{r['line_start']} (score: {r['score']:.2f})")
```

**JavaScript/Node.js Client:**

```javascript
// examples/api_client_node.js
/**
 * Node.js client example for Code Indexer API.
 */

const axios = require('axios');

class CodeIndexerClient {
  constructor(baseUrl = 'http://localhost:8765') {
    this.baseUrl = baseUrl;
    this.client = axios.create({ baseURL: baseUrl });
  }

  async search(query, workspace, options = {}) {
    const response = await this.client.post('/v1/search', {
      query,
      workspace,
      max_results: options.maxResults || 10,
      semantic: options.semantic !== false
    });
    return response.data;
  }

  async index(workspace, incremental = true) {
    const response = await this.client.post('/v1/index', {
      workspace,
      incremental
    });
    return response.data;
  }
}

// Usage example
(async () => {
  const client = new CodeIndexerClient();
  
  // Index workspace
  const indexResult = await client.index('/path/to/project');
  console.log(`Indexing started: ${indexResult.operation_id}`);
  
  // Search
  const searchResults = await client.search('authentication logic', '/path/to/project');
  console.log(`Found ${searchResults.total} results in ${searchResults.elapsed_ms}ms`);
  
  searchResults.results.forEach(r => {
    console.log(`  ${r.file_path}:${r.line_start} (score: ${r.score.toFixed(2)})`);
  });
})();
```

#### Day 6-7: Integration Examples

**Ollama Integration:**

```python
# examples/ollama_integration.py
"""
Integrate Code Indexer with Ollama for context-aware code assistance.
"""

import requests
from typing import List


def search_codebase(query: str, workspace: str) -> str:
    """Search codebase and return context for Ollama."""
    indexer_api = "http://localhost:8765"
    
    response = requests.post(
        f"{indexer_api}/v1/search",
        json={
            "query": query,
            "workspace": workspace,
            "max_results": 5,
            "semantic": True
        }
    )
    
    results = response.json()
    
    # Format results as context
    context = f"Relevant code for '{query}':\n\n"
    for r in results['results']:
        context += f"File: {r['file_path']} (lines {r['line_start']}-{r['line_end']})\n"
        context += f"```\n{r['content']}\n```\n\n"
    
    return context


def ask_ollama_with_context(question: str, workspace: str, model: str = "codellama"):
    """Ask Ollama with code context."""
    # Get relevant code
    context = search_codebase(question, workspace)
    
    # Build prompt
    prompt = f"{context}\n\nQuestion: {question}\n\nAnswer:"
    
    # Call Ollama
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }
    )
    
    return response.json()['response']


# Usage
if __name__ == "__main__":
    answer = ask_ollama_with_context(
        "How does the authentication system work?",
        "/path/to/project"
    )
    print(answer)
```

**Acceptance Criteria for Phase 4:**
- [ ] FastAPI server running on port 8765
- [ ] All endpoints tested and documented
- [ ] OpenAPI spec complete
- [ ] Python and Node.js client examples working
- [ ] Ollama integration example working
- [ ] Performance acceptable (<50ms for search)

---

### Phase 5: One-Line Installer & Auto-Configuration (Week 5)

**Goal:** Create installers that detect AI tools and auto-configure them.

#### Day 1-2: Tool Detection System

**File:** `scripts/detect_tools.py`

```python
#!/usr/bin/env python3
"""
Detect installed AI tools and development environments.

This script scans the system for:
- AI coding tools (Claude Code, Cursor, VS Code, etc.)
- AI chat tools (Ollama, LM Studio, Jan AI)
- Development environments (Python, Node.js, etc.)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class DetectedTool:
    """Represents a detected AI tool."""
    name: str
    type: str  # 'editor', 'ai_server', 'cli_tool'
    version: Optional[str]
    config_path: Optional[Path]
    installed: bool
    integration_type: str  # 'extension', 'mcp', 'lsp', 'api'


class ToolDetector:
    """Detect installed AI tools."""
    
    def __init__(self):
        self.detected_tools: List[DetectedTool] = []
    
    def detect_all(self) -> List[DetectedTool]:
        """Detect all supported tools."""
        detectors = [
            self.detect_claude_code,
            self.detect_vscode,
            self.detect_cursor,
            self.detect_zed,
            self.detect_windsurf,
            self.detect_ollama,
            self.detect_lm_studio,
            self.detect_jan_ai,
        ]
        
        for detector in detectors:
            try:
                tool = detector()
                if tool:
                    self.detected_tools.append(tool)
            except Exception as e:
                print(f"Error detecting tool: {e}", file=sys.stderr)
        
        return self.detected_tools
    
    def detect_claude_code(self) -> Optional[DetectedTool]:
        """Detect Claude Code."""
        if sys.platform == "darwin":
            config_dir = Path.home() / "Library/Application Support/Claude Code"
        elif sys.platform == "win32":
            config_dir = Path(os.environ.get("APPDATA", "")) / "Claude Code"
        else:
            config_dir = Path.home() / ".config/claude-code"
        
        if config_dir.exists():
            # Check for config.json
            config_file = config_dir / "config.json"
            
            return DetectedTool(
                name="Claude Code",
                type="editor",
                version=self._get_app_version("claude-code"),
                config_path=config_file,
                installed=True,
                integration_type="extension"  # Native extension preferred
            )
        
        return None
    
    def detect_vscode(self) -> Optional[DetectedTool]:
        """Detect VS Code."""
        # Try to find VS Code executable
        if sys.platform == "darwin":
            vscode_path = Path("/Applications/Visual Studio Code.app")
            config_dir = Path.home() / "Library/Application Support/Code"
        elif sys.platform == "win32":
            vscode_path = Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft VS Code"
            config_dir = Path(os.environ.get("APPDATA", "")) / "Code"
        else:
            vscode_path = Path("/usr/share/code")
            config_dir = Path.home() / ".config/Code"
        
        if vscode_path.exists() or config_dir.exists():
            return DetectedTool(
                name="VS Code",
                type="editor",
                version=self._get_command_version("code", "--version"),
                config_path=config_dir / "User/settings.json",
                installed=True,
                integration_type="lsp"  # LSP server
            )
        
        return None
    
    def detect_cursor(self) -> Optional[DetectedTool]:
        """Detect Cursor."""
        if sys.platform == "darwin":
            cursor_path = Path.home() / "Library/Application Support/Cursor"
        elif sys.platform == "win32":
            cursor_path = Path(os.environ.get("APPDATA", "")) / "Cursor"
        else:
            cursor_path = Path.home() / ".config/Cursor"
        
        if cursor_path.exists():
            return DetectedTool(
                name="Cursor",
                type="editor",
                version=None,
                config_path=cursor_path / "User/settings.json",
                installed=True,
                integration_type="lsp"
            )
        
        return None
    
    def detect_zed(self) -> Optional[DetectedTool]:
        """Detect Zed."""
        if sys.platform == "darwin":
            zed_path = Path.home() / "Library/Application Support/Zed"
        else:
            zed_path = Path.home() / ".config/zed"
        
        if zed_path.exists():
            return DetectedTool(
                name="Zed",
                type="editor",
                version=None,
                config_path=zed_path / "settings.json",
                installed=True,
                integration_type="lsp"
            )
        
        return None
    
    def detect_windsurf(self) -> Optional[DetectedTool]:
        """Detect Windsurf."""
        # Windsurf detection logic
        config_dir = Path.home() / ".windsurf"
        if config_dir.exists():
            return DetectedTool(
                name="Windsurf",
                type="editor",
                version=None,
                config_path=config_dir / "config.json",
                installed=True,
                integration_type="lsp"
            )
        
        return None
    
    def detect_ollama(self) -> Optional[DetectedTool]:
        """Detect Ollama."""
        # Check if ollama command exists
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return DetectedTool(
                    name="Ollama",
                    type="ai_server",
                    version=result.stdout.strip(),
                    config_path=None,
                    installed=True,
                    integration_type="api"  # HTTP API
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return None
    
    def detect_lm_studio(self) -> Optional[DetectedTool]:
        """Detect LM Studio."""
        if sys.platform == "darwin":
            lm_studio_path = Path("/Applications/LM Studio.app")
        elif sys.platform == "win32":
            lm_studio_path = Path(os.environ.get("LOCALAPPDATA", "")) / "LM-Studio"
        else:
            lm_studio_path = Path.home() / ".lm-studio"
        
        if lm_studio_path.exists():
            return DetectedTool(
                name="LM Studio",
                type="ai_server",
                version=None,
                config_path=lm_studio_path / "config.json" if not sys.platform == "darwin" else None,
                installed=True,
                integration_type="mcp"  # MCP support
            )
        
        return None
    
    def detect_jan_ai(self) -> Optional[DetectedTool]:
        """Detect Jan AI."""
        if sys.platform == "darwin":
            jan_path = Path.home() / "Library/Application Support/Jan"
        elif sys.platform == "win32":
            jan_path = Path(os.environ.get("APPDATA", "")) / "Jan"
        else:
            jan_path = Path.home() / ".config/jan"
        
        if jan_path.exists():
            return DetectedTool(
                name="Jan AI",
                type="ai_server",
                version=None,
                config_path=jan_path / "settings.json",
                installed=True,
                integration_type="api"  # HTTP API
            )
        
        return None
    
    def _get_command_version(self, command: str, *args) -> Optional[str]:
        """Get version from a command."""
        try:
            result = subprocess.run(
                [command, *args],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None
    
    def _get_app_version(self, app_name: str) -> Optional[str]:
        """Get application version (platform-specific)."""
        # Simplified version detection
        return None


def main():
    """Detect and print all tools."""
    detector = ToolDetector()
    tools = detector.detect_all()
    
    print("🔍 Detected AI Tools:\n")
    
    if not tools:
        print("No AI tools detected.")
        return
    
    for tool in tools:
        status = "✅" if tool.installed else "❌"
        print(f"{status} {tool.name} ({tool.type})")
        if tool.version:
            print(f"   Version: {tool.version}")
        print(f"   Integration: {tool.integration_type}")
        if tool.config_path:
            print(f"   Config: {tool.config_path}")
        print()
    
    # Export as JSON
    output_file = Path("detected_tools.json")
    with open(output_file, 'w') as f:
        json.dump([asdict(t) for t in tools], f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
```

#### Day 3-4: Unix Installer (install.sh)

**File:** `scripts/install.sh`

```bash
#!/usr/bin/env bash
#
# Code-Indexer One-Line Installer
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/scooter-lacroix/code-indexer/main/scripts/install.sh | bash
#
# Options:
#   SKIP_DEPS=1     Skip dependency installation
#   SKIP_DB=1       Skip database setup
#   SKIP_CONFIG=1   Skip auto-configuration

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/scooter-lacroix/code-indexer.git"
INSTALL_DIR="${HOME}/.local/share/code-indexer"
BIN_DIR="${HOME}/.local/bin"

# Logging functions
info() {
    echo -e "${BLUE}ℹ️  ${1}${NC}"
}

success() {
    echo -e "${GREEN}✅ ${1}${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  ${1}${NC}"
}

error() {
    echo -e "${RED}❌ ${1}${NC}"
    exit 1
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
        else
            OS="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    
    info "Detected OS: $OS"
}

# Install system dependencies
install_dependencies() {
    if [ "${SKIP_DEPS}" = "1" ]; then
        info "Skipping dependency installation"
        return
    fi
    
    info "Installing system dependencies..."
    
    case "$OS" in
        ubuntu|debian)
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv postgresql git
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3 python3-pip postgresql-server git
            ;;
        macos)
            if ! command -v brew &> /dev/null; then
                error "Homebrew not found. Please install: https://brew.sh"
            fi
            brew install python postgresql git
            ;;
        *)
            warning "Unknown OS. Please install manually: python3, pip, postgresql, git"
            ;;
    esac
    
    success "System dependencies installed"
}

# Install Python package
install_package() {
    info "Installing code-indexer..."
    
    # Create directories
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${BIN_DIR}"
    
    # Clone or update repository
    if [ -d "${INSTALL_DIR}/.git" ]; then
        info "Updating existing installation..."
        cd "${INSTALL_DIR}"
        git pull
    else
        info "Cloning repository..."
        git clone "${REPO_URL}" "${INSTALL_DIR}"
        cd "${INSTALL_DIR}"
    fi
    
    # Install with pip
    python3 -m pip install --user -e .
    
    # Install optional dependencies
    info "Installing optional dependencies..."
    python3 -m pip install --user 'faiss-cpu>=1.7.4' 'sentence-transformers>=2.2.0'
    
    success "Code-indexer installed"
}

# Setup PostgreSQL
setup_database() {
    if [ "${SKIP_DB}" = "1" ]; then
        info "Skipping database setup"
        return
    fi
    
    info "Setting up PostgreSQL..."
    
    case "$OS" in
        ubuntu|debian)
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        fedora|rhel|centos)
            sudo postgresql-setup --initdb
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        macos)
            brew services start postgresql
            ;;
    esac
    
    # Create database
    info "Creating database..."
    sudo -u postgres psql -c "CREATE DATABASE code_index_db;" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE USER codeindex WITH PASSWORD 'codeindex';" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE code_index_db TO codeindex;" 2>/dev/null || true
    
    success "Database setup complete"
}

# Auto-configure detected tools
auto_configure() {
    if [ "${SKIP_CONFIG}" = "1" ]; then
        info "Skipping auto-configuration"
        return
    fi
    
    info "Detecting installed AI tools..."
    
    cd "${INSTALL_DIR}"
    python3 scripts/detect_tools.py
    
    if [ ! -f detected_tools.json ]; then
        warning "No tools detected"
        return
    fi
    
    # Read detected tools and configure them
    info "Configuring detected tools..."
    python3 - <<EOF
import json
import sys
from pathlib import Path

with open('detected_tools.json') as f:
    tools = json.load(f)

for tool in tools:
    if not tool['installed']:
        continue
    
    print(f"Configuring {tool['name']}...")
    
    # Add tool-specific configuration logic here
    if tool['integration_type'] == 'extension':
        # Install extension
        print(f"  Installing extension for {tool['name']}")
    elif tool['integration_type'] == 'lsp':
        # Configure LSP
        print(f"  Configuring LSP for {tool['name']}")
    elif tool['integration_type'] == 'mcp':
        # Configure MCP
        print(f"  Configuring MCP for {tool['name']}")
    elif tool['integration_type'] == 'api':
        # Just note that HTTP API is available
        print(f"  HTTP API available for {tool['name']} at http://localhost:8765")

print("\n✅ Configuration complete!")
EOF
    
    success "Auto-configuration complete"
}

# Add to PATH
setup_path() {
    info "Setting up PATH..."
    
    # Determine shell config file
    if [ -n "$BASH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    else
        SHELL_CONFIG="$HOME/.profile"
    fi
    
    # Add to PATH if not already there
    if ! grep -q "${BIN_DIR}" "${SHELL_CONFIG}" 2>/dev/null; then
        echo "" >> "${SHELL_CONFIG}"
        echo "# Code-Indexer" >> "${SHELL_CONFIG}"
        echo "export PATH=\"${BIN_DIR}:\$PATH\"" >> "${SHELL_CONFIG}"
        
        success "Added to PATH in ${SHELL_CONFIG}"
        warning "Please restart your shell or run: source ${SHELL_CONFIG}"
    fi
}

# Main installation flow
main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║                                                       ║"
    echo "║          Code-Indexer Installation Script             ║"
    echo "║                                                       ║"
    echo "║  Semantic code search with local vector store         ║"
    echo "║                                                       ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo ""
    
    detect_os
    install_dependencies
    install_package
    setup_database
    setup_path
    auto_configure
    
    echo ""
    success "Installation complete! 🎉"
    echo ""
    info "Next steps:"
    echo "  1. Restart your shell or run: source ~/.bashrc (or ~/.zshrc)"
    echo "  2. Test installation: code-indexer --version"
    echo "  3. Index a project: code-indexer index /path/to/project"
    echo "  4. Search: code-indexer search 'authentication logic'"
    echo ""
    info "Documentation: https://github.com/scooter-lacroix/code-indexer"
    echo ""
}

# Run main installation
main
```

#### Day 5: Windows Installer (install.ps1)

**File:** `scripts/install.ps1`

```powershell
#
# Code-Indexer Windows Installer
#
# Usage:
#   iwr -useb https://raw.githubusercontent.com/scooter-lacroix/code-indexer/main/scripts/install.ps1 | iex
#

$ErrorActionPreference = "Stop"

# Configuration
$RepoUrl = "https://github.com/scooter-lacroix/code-indexer.git"
$InstallDir = "$env:LOCALAPPDATA\code-indexer"
$BinDir = "$env:LOCALAPPDATA\Programs\code-indexer"

# Colors
function Write-Info {
    Write-Host "ℹ️  $args" -ForegroundColor Blue
}

function Write-Success {
    Write-Host "✅ $args" -ForegroundColor Green
}

function Write-Warning {
    Write-Host "⚠️  $args" -ForegroundColor Yellow
}

function Write-Error {
    Write-Host "❌ $args" -ForegroundColor Red
    exit 1
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python not found. Please install Python 3.10+ from python.org"
    }
    
    $pythonVersion = python --version
    Write-Info "Found: $pythonVersion"
    
    # Check Git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Error "Git not found. Please install Git from git-scm.com"
    }
    
    Write-Success "Prerequisites OK"
}

# Install package
function Install-Package {
    Write-Info "Installing code-indexer..."
    
    # Create directories
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    
    # Clone or update
    if (Test-Path "$InstallDir\.git") {
        Write-Info "Updating existing installation..."
        Set-Location $InstallDir
        git pull
    } else {
        Write-Info "Cloning repository..."
        git clone $RepoUrl $InstallDir
        Set-Location $InstallDir
    }
    
    # Install with pip
    python -m pip install --user -e .
    
    # Install optional dependencies
    Write-Info "Installing optional dependencies..."
    python -m pip install --user faiss-cpu sentence-transformers
    
    Write-Success "Package installed"
}

# Setup database (use Docker or skip on Windows)
function Setup-Database {
    Write-Info "Checking for Docker..."
    
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Info "Docker found. Starting PostgreSQL container..."
        
        docker run -d `
            --name code-indexer-postgres `
            -e POSTGRES_PASSWORD=codeindex `
            -e POSTGRES_USER=codeindex `
            -e POSTGRES_DB=code_index_db `
            -p 5432:5432 `
            postgres:16-alpine
        
        Write-Success "PostgreSQL container started"
    } else {
        Write-Warning "Docker not found. Please install PostgreSQL manually or use Docker Desktop"
        Write-Info "Download: https://www.postgresql.org/download/windows/"
    }
}

# Add to PATH
function Add-ToPath {
    Write-Info "Adding to PATH..."
    
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    if ($currentPath -notlike "*$BinDir*") {
        $newPath = "$currentPath;$BinDir"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        
        # Also add to current session
        $env:Path = "$env:Path;$BinDir"
        
        Write-Success "Added to PATH"
    } else {
        Write-Info "Already in PATH"
    }
}

# Auto-configure tools
function Configure-Tools {
    Write-Info "Detecting AI tools..."
    
    Set-Location $InstallDir
    python scripts\detect_tools.py
    
    if (Test-Path "detected_tools.json") {
        Write-Info "Configuring detected tools..."
        # Configuration logic here
        Write-Success "Tools configured"
    } else {
        Write-Warning "No tools detected"
    }
}

# Main installation
function Main {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════╗"
    Write-Host "║                                                       ║"
    Write-Host "║          Code-Indexer Installation Script             ║"
    Write-Host "║                                                       ║"
    Write-Host "║  Semantic code search with local vector store         ║"
    Write-Host "║                                                       ║"
    Write-Host "╚═══════════════════════════════════════════════════════╝"
    Write-Host ""
    
    Test-Prerequisites
    Install-Package
    Setup-Database
    Add-ToPath
    Configure-Tools
    
    Write-Host ""
    Write-Success "Installation complete! 🎉"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. Restart your terminal"
    Write-Host "  2. Test: code-indexer --version"
    Write-Host "  3. Index: code-indexer index C:\path\to\project"
    Write-Host "  4. Search: code-indexer search 'authentication logic'"
    Write-Host ""
}

# Run
Main
```

#### Day 6-7: Testing & Documentation

**Test Plan:**

```bash
# Test Unix installer
docker run -it ubuntu:22.04 /bin/bash
curl -sSL https://raw.githubusercontent.com/scooter-lacroix/code-indexer/main/scripts/install.sh | bash

# Test Windows installer
# (Manual testing in Windows VM)

# Verify installations
code-indexer --version
code-indexer search --help
```

**Acceptance Criteria for Phase 5:**
- [ ] Unix installer tested on Ubuntu, Fedora, macOS
- [ ] Windows installer tested on Windows 10/11
- [ ] Auto-detection finds all installed tools
- [ ] Auto-configuration works for detected tools
- [ ] One-line install completes in <5 minutes
- [ ] Documentation includes troubleshooting guide

---

## Clarifying Questions & Pre-Answers

### Architecture Questions

**Q1: Should the core library be sync or async?**

**A:** Async-first (using asyncio). Rationale:
- All I/O operations (DB, filesystem) benefit from async
- Modern Python best practice for I/O-bound libraries
- Easier to add sync wrapper than vice versa
- Provides sync convenience methods: `indexer.search_sync()` wraps `asyncio.run(indexer.search())`

**Q2: How do we handle breaking changes in the core library API?**

**A:** Semantic versioning with deprecation warnings:
- Major version (4.0.0 → 5.0.0) for breaking changes
- Deprecated methods kept for 1 major version with warnings
- Clear migration guide in CHANGELOG.md
- Old MCP interface maintains backward compatibility through adapter layer

**Q3: Should we support Python 3.8 or require 3.10+?**

**A:** Require Python 3.10+. Rationale:
- 3.8 reaches end-of-life October 2024
- 3.10+ gives us pattern matching, better type hints, better async
- FAISS wheels available for 3.10+
- Most AI tools already require 3.10+

### Extension Questions

**Q4: What if Claude Code doesn't have a documented extension API?**

**A:** Fallback strategy (in order of preference):
1. Check for undocumented API through reverse engineering
2. Create "Enhanced Skill" that uses subprocess to call CLI (faster than MCP)
3. Optimize MCP server to be as fast as possible
4. Document this and advocate for native extension API

**Q5: How do we handle extension versioning with core library updates?**

**A:** Pin extension to core library version:
- Extension manifest specifies: `"core_version": "^4.0.0"`
- Extension installation checks core library version
- Auto-update extension when core library updates
- Breaking changes require manual update with migration guide

### LSP Questions

**Q6: Which LSP features should we prioritize?**

**A:** Priority order (implement in phases):
1. **Phase 1 (Week 3):** Definition, Symbol Search, Hover (80% value)
2. **Phase 2 (Future):** References, Completion, Rename
3. **Phase 3 (Future):** Code Actions, Diagnostics

**Q7: How do we handle multiple language servers for the same language?**

**A:** Namespace our capabilities:
- Register as `code-indexer-lsp` (not replacing language-specific LSPs)
- Provide additive capabilities (semantic search across languages)
- Play nice with existing LSPs (Python, TypeScript, etc.)
- Document how to configure alongside other LSPs

### API Questions

**Q8: Should the HTTP API require authentication?**

**A:** Optional authentication with sane defaults:
- **Development:** No auth required (localhost only)
- **Production:** Support API keys, JWT tokens
- **Configuration:** `AUTH_REQUIRED=true` environment variable
- **Documentation:** Security best practices guide

**Q9: How do we handle API versioning?**

**A:** URL versioning with backward compatibility:
- Current: `/v1/search`
- Future: `/v2/search` with different parameters
- Maintain `/v1/` for at least 1 year after `/v2/` release
- Deprecation warnings in response headers

### Installation Questions

**Q10: What if PostgreSQL/Elasticsearch aren't available?**

**A:** Graceful degradation:
- **Minimal install:** SQLite + Zoekt only (no semantic search)
- **Standard install:** PostgreSQL + Elasticsearch + FAISS
- **Full install:** All backends + RabbitMQ
- Auto-detect and offer appropriate installation based on system

**Q11: How do we handle dependency conflicts?**

**A:** Isolated installation:
- Install in virtual environment by default
- Use pipx for CLI isolation
- Docker image as fallback option
- Document common conflicts (e.g., numpy versions)

### Testing Questions

**Q12: What's the minimum test coverage?**

**A:** Tiered coverage requirements:
- **Core library:** 90%+ coverage (critical path)
- **Interfaces:** 80%+ coverage (adapters)
- **Integration tests:** Key workflows covered
- **Performance tests:** Regression benchmarks

**Q13: How do we test across all platforms?**

**A:** GitHub Actions CI/CD:
- Matrix: [Ubuntu 22.04, macOS 13, Windows 2022] × [Python 3.10, 3.11, 3.12]
- Run on every PR
- Performance benchmarks on main branch only (expensive)

### Migration Questions

**Q14: Can users migrate gradually or must they do it all at once?**

**A:** Gradual migration supported:
- **Phase 1:** Install new version, keep MCP working (no changes needed)
- **Phase 2:** Try native extension or LSP (optional)
- **Phase 3:** Deprecate MCP (1 year notice)
- **Phase 4:** Remove MCP (v5.0.0)

**Q15: What happens to existing MCP configurations?**

**A:** Automatic migration:
- Installer detects old MCP config
- Offers to migrate to new format
- Creates backup of old config
- Both configs work during transition period

### Performance Questions

**Q16: What are the performance targets for each interface?**

**A:**
| Interface        | Target Latency (p95) | Rationale           |
|------------------|----------------------|---------------------|
| Native Extension | <20ms                | Direct Python calls |
| LSP              | <100ms               | IDE responsiveness  |
| HTTP API         | <50ms                | Network overhead    |
| MCP              | <200ms               | JSON-RPC overhead   |

**Q17: How do we benchmark against the old system?**

**A:** Automated benchmark suite:
- Run before every release
- Compare against baseline (current MCP)
- Fail CI if regression >20%
- Document performance in CHANGELOG

### Documentation Questions

**Q18: What documentation is essential vs. nice-to-have?**

**A:** Essential (blocking release):
- README with quick start
- Installation guide for each platform
- API reference (core library)
- Migration guide from MCP-only
- Troubleshooting guide

Nice-to-have (post-release):
- Architecture deep-dive
- Performance tuning guide
- Extension development guide
- Video tutorials

**Q19: How do we keep docs in sync with code?**

**A:** Automated documentation:
- API docs generated from docstrings (Sphinx)
- Code examples tested in CI (doctest)
- Changelog generated from git commits (conventional commits)
- Docs built and deployed on every release

---

## Migration Path for Existing Users

### Strategy: Transparent Upgrade

The restructuring is designed to be **non-breaking** for existing MCP users while opening new integration methods.

### Migration Phases

**Phase 0: Current State (v3.0.0)**
```
User has: MCP server with 50+ tools → 9 mega-tools
Works with: Claude Desktop, VS Code (via MCP extension)
```

**Phase 1: Library Extraction (v4.0.0-alpha)**
```
✅ Install: pip install code-indexer==4.0.0a1
❌ No changes needed to existing MCP config
✅ MCP still works (now as thin wrapper)
✨ New: Can import core library directly
```

**Phase 2: Native Extensions Available (v4.0.0-beta)**
```
✅ MCP still works (unchanged)
✨ New: Native Claude Code extension available
✨ New: LSP server for VS Code/Zed/Cursor
📚 Documentation: "Try native extension for 10x speed"
```

**Phase 3: Full Release (v4.0.0)**
```
✅ MCP still works (backward compatible)
✨ All interfaces ready: Extension, LSP, API, MCP
✨ One-line installer auto-configures detected tools
⚠️ Deprecation notice: "MCP will be removed in v5.0.0 (12 months)"
```

**Phase 4: Deprecation (v4.5.0)**
```
✅ MCP still works but marked deprecated
⚠️ Warning on every MCP request: "Please migrate to native extension"
📚 Migration tools provided
🗓️ Timeline: v5.0.0 releases in 6 months
```

**Phase 5: MCP Removal (v5.0.0)**
```
❌ MCP server removed from default installation
✅ Available as optional package: pip install code-indexer[mcp-legacy]
📚 Final migration guide
🎯 Focus: Native integrations only
```

### Automatic Migration Script

**File:** `scripts/migrate.py`

```python
#!/usr/bin/env python3
"""
Migrate from MCP-only to new architecture.

This script:
1. Detects current MCP configuration
2. Offers to install native integration
3. Updates config files
4. Tests new integration
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

def detect_mcp_config() -> Dict[str, Any]:
    """Detect existing MCP configuration."""
    # Check Claude Desktop config
    if sys.platform == "darwin":
        config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif sys.platform == "win32":
        config_path = Path(os.environ.get("APPDATA", "")) / "Claude/claude_desktop_config.json"
    else:
        config_path = Path.home() / ".config/claude/claude_desktop_config.json"
    
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        
        # Check for code-indexer MCP server
        if "mcpServers" in config and "code-index" in config["mcpServers"]:
            return {
                "found": True,
                "config_path": config_path,
                "config": config["mcpServers"]["code-index"]
            }
    
    return {"found": False}

def offer_native_extension():
    """Offer to install native extension."""
    print("\n" + "="*60)
    print("🚀 Native Extension Available!")
    print("="*60)
    print("\nYour current setup uses MCP (Model Context Protocol).")
    print("We now offer a native extension that is 10-100x faster!")
    print("\nBenefits of native extension:")
    print("  • 10-100x faster than MCP")
    print("  • No JSON serialization overhead")
    print("  • Direct Python API access")
    print("  • Better error messages")
    print("\nYour MCP configuration will still work,")
    print("but we recommend migrating to the native extension.")
    print()
    
    response = input("Would you like to install the native extension? [Y/n]: ")
    return response.lower() != 'n'

def install_native_extension():
    """Install native extension for detected tool."""
    print("\n📦 Installing native extension...")
    
    # Run installation
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "code_indexer.extensions.claude_code.install"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Native extension installed!")
        print("\nNext steps:")
        print("  1. Restart Claude Code")
        print("  2. Your existing MCP config will still work")
        print("  3. To use native extension, just start using code-indexer!")
        print("     (Claude Code will automatically use the faster native extension)")
        return True
    else:
        print("❌ Installation failed:")
        print(result.stderr)
        return False

def main():
    """Main migration script."""
    print("Code-Indexer Migration Tool")
    print("="*60)
    
    # Detect current setup
    mcp_config = detect_mcp_config()
    
    if not mcp_config["found"]:
        print("\n⚠️ No existing MCP configuration found.")
        print("This script is for users migrating from MCP.")
        print("\nFor new installation, use:")
        print("  curl -sSL https://... | bash")
        return
    
    print(f"\n✅ Found MCP configuration:")
    print(f"   Config: {mcp_config['config_path']}")
    print(f"   Command: {mcp_config['config']['command']}")
    
    # Offer native extension
    if offer_native_extension():
        success = install_native_extension()
        
        if success:
            print("\n" + "="*60)
            print("🎉 Migration Complete!")
            print("="*60)
            print("\nYou now have BOTH:")
            print("  • Native extension (fast) ← recommended")
            print("  • MCP server (backward compatible)")
            print("\nTo fully remove MCP in the future:")
            print("  1. Verify native extension works")
            print("  2. Remove MCP config from claude_desktop_config.json")
            print("  3. Run: pip uninstall code-indexer[mcp]")
        else:
            print("\n⚠️ Migration failed, but your MCP config still works!")
    else:
        print("\n👍 No problem! Your MCP configuration will continue to work.")
        print("You can migrate later by running this script again.")

if __name__ == "__main__":
    main()
```

---

## Timeline & Resource Estimates

### Per-Phase Breakdown

| Phase                          | Duration | Developer Time | Key Deliverables                                       |
|--------------------------------|----------|----------------|--------------------------------------------------------|
| Phase 1: Core Library          | 1 week   | 40 hours       | Core library extracted, imports updated, tests passing |
| Phase 2: Claude Code Extension | 1 week   | 40 hours       | Native extension, benchmark showing >10x speedup       |
| Phase 3: LSP Server            | 1 week   | 40 hours       | LSP server, VS Code extension, multi-editor support    |
| Phase 4: HTTP API              | 1 week   | 40 hours       | FastAPI server, client libraries, Ollama integration   |
| Phase 5: Installer             | 1 week   | 40 hours       | One-line installers, auto-config, documentation        |

**Total:** 5 weeks, 200 developer hours

### Parallel Work Opportunities

Phases can overlap if multiple developers available:
- **Week 1-2:** Phase 1 (core) + Phase 2 (extension) can run in parallel after Day 3
- **Week 3-4:** Phase 3 (LSP) + Phase 4 (API) independent
- **Week 5:** Integration testing while Phase 5 (installer) development

With 2 developers: **3-4 weeks total**

---

## Success Metrics

### Quantitative Metrics

| Metric                  | Current        | Target                       | Measurement                 |
|-------------------------|----------------|------------------------------|-----------------------------|
| Integration methods     | 1 (MCP)        | 4 (Extension, LSP, API, MCP) | Count of working interfaces |
| Search latency (native) | N/A            | <20ms (p95)                  | Benchmark suite             |
| Search latency (MCP)    | ~100ms         | Same                         | No regression               |
| Installation time       | ~10 min manual | <2 min automated             | Timer in installer          |
| Test coverage           | 85%            | >90%                         | pytest --cov                |
| Supported AI tools      | ~5             | >10                          | Detection script count      |
| Documentation pages     | 10             | 25+                          | Docs file count             |

### Qualitative Metrics

- **Developer experience:** Can import and use core library in <5 minutes
- **User experience:** One-line install works on all platforms
- **Community adoption:** >50 GitHub stars in first month
- **Issue rate:** <5 new issues per week (stability)

---

## Risk Mitigation

### Technical Risks

| Risk                        | Probability | Impact | Mitigation                                  |
|-----------------------------|-------------|--------|---------------------------------------------|
| Extension API doesn't exist | Medium      | High   | Fallback to optimized MCP or subprocess CLI |
| LSP conflicts with existing | Low         | Medium | Namespace capabilities, document conflicts  |
| Performance regression      | Low         | High   |
| Automated benchmarks in CI  |
| Breaking changes in core    | Low         | High   | Semantic versioning, deprecation warnings   |
| Platform-specific bugs      | Medium      | Medium | CI matrix testing, platform-specific tests  |

### Project Risks

| Risk                | Probability | Impact | Mitigation                                                  |
|---------------------|-------------|--------|-------------------------------------------------------------|
| Scope creep         | High        | Medium | Strict adherence to 5-week plan, defer features to Phase 6+ |
| Timeline slippage   | Medium      | Medium | Weekly checkpoints, parallel work streams                   |
| Documentation debt  | Medium      | Low    | Documentation as acceptance criteria per phase              |
| Community confusion | Low         | Medium | Clear communication, migration guides                       |

### Rollback Plans

**If Phase 1 fails:**
- Revert git changes
- Keep using current code-index-mcp
- No user impact (internal restructure)

**If Phase 2-4 fail:**
- MCP still works (backward compatible)
- Users not affected
- Release v4.0.0 without failed interface

**If Phase 5 fails:**
- Users install manually (current method)
- No blocking issue for v4.0.0

---

## Post-Restructuring Roadmap

### Phase 6: Community Extensions (Month 2)

**Goal:** Enable community to build extensions for other tools

**Deliverables:**
- Extension template and generator
- Developer documentation
- Community showcase page
- Extension marketplace (GitHub topics)

**Example extensions community could build:**
- Gemini CLI plugin
- Qwen Code extension
- Codex skill
- Mistral-Vibe integration
- Custom LSP capabilities

### Phase 7: Performance & Scale (Month 3)

**Goal:** Optimize for massive codebases (1M+ files)

**Deliverables:**
- Distributed indexing (multi-machine)
- Advanced caching strategies
- GPU acceleration for FAISS (when faiss-gpu supports Python 3.11+)
- Incremental vector updates
- Smart batch sizing

**Targets:**
- Index 1M files in <30 minutes
- Search latency <100ms even at 1M files
- Memory usage <2GB for 1M files

### Phase 8: Enterprise Features (Month 4)

**Goal:** Make code-indexer enterprise-ready

**Deliverables:**
- SSO/LDAP authentication
- Audit logging
- Multi-tenant support
- Cloud deployment guides (AWS, GCP, Azure)
- Kubernetes Helm charts
- Monitoring dashboards (Grafana)
- SLA documentation

### Phase 9: Advanced AI Features (Month 5-6)

**Goal:** Leverage embeddings for deeper code understanding

**Deliverables:**
- Code clone detection (find similar code)
- Semantic code review suggestions
- Automatic test generation
- Code quality scoring
- Change impact analysis
- Documentation generation

---

## Complete File Manifest

### Critical Files to Create

```
# Core Library (40 files)
src/code_indexer/__init__.py
src/code_indexer/version.py
src/code_indexer/exceptions.py
src/code_indexer/core/indexer.py          # Main entry point
src/code_indexer/core/searcher.py         # Unified search
src/code_indexer/core/chunker.py          # Code chunking
src/code_indexer/core/file_tracker.py     # File changes
src/code_indexer/core/operations.py       # Operation tracking
src/code_indexer/backends/base.py         # Abstract interfaces
src/code_indexer/backends/postgresql.py   # PostgreSQL backend
src/code_indexer/backends/elasticsearch.py # ES backend
src/code_indexer/backends/faiss_store.py  # FAISS backend
src/code_indexer/backends/zoekt.py        # Zoekt integration
src/code_indexer/backends/dal.py          # DAL factory
src/code_indexer/models/file.py           # File models
src/code_indexer/models/search.py         # Search models
src/code_indexer/models/operation.py      # Operation models
src/code_indexer/utils/config.py          # Configuration
src/code_indexer/utils/logging.py         # Structured logging
src/code_indexer/utils/memory.py          # Memory management
src/code_indexer/utils/path.py            # Path utilities

# MCP Interface (5 files)
interfaces/mcp/server.py                   # MCP server (thin wrapper)
interfaces/mcp/tools.py                    # Tool definitions
interfaces/mcp/README.md

# CLI Interface (8 files)
interfaces/cli/main.py                     # CLI entry point
interfaces/cli/commands/search.py
interfaces/cli/commands/index.py
interfaces/cli/commands/config.py
interfaces/cli/README.md

# Claude Code Extension (10 files)
interfaces/extensions/claude_code/extension.py
interfaces/extensions/claude_code/manifest.json
interfaces/extensions/claude_code/install.py
interfaces/extensions/claude_code/README.md
interfaces/extensions/base.py              # Base extension class
interfaces/extensions/template/extension.py.template

# LSP Server (8 files)
interfaces/lsp/server.py                   # LSP server
interfaces/lsp/handlers.py                 # Request handlers
interfaces/lsp/capabilities.json
interfaces/lsp/vscode-extension/package.json
interfaces/lsp/vscode-extension/src/extension.ts
interfaces/lsp/README.md

# HTTP API (10 files)
interfaces/api/server.py                   # FastAPI server
interfaces/api/routes/search.py
interfaces/api/routes/index.py
interfaces/api/routes/health.py
interfaces/api/middleware.py
interfaces/api/openapi.yaml
interfaces/api/README.md

# Scripts (15 files)
scripts/install.sh                         # Unix installer
scripts/install.ps1                        # Windows installer
scripts/detect_tools.py                    # Tool detection
scripts/migrate.py                         # Migration helper
scripts/update_imports.py                  # Import updater
scripts/setup_dev.py                       # Dev setup

# Tests (50+ files)
tests/unit/core/test_indexer.py
tests/unit/core/test_searcher.py
tests/unit/backends/test_postgresql.py
tests/integration/test_mcp.py
tests/integration/test_extensions.py
tests/integration/test_lsp.py
tests/integration/test_api.py
tests/benchmarks/compare_mcp_vs_extension.py

# Documentation (30+ files)
docs/architecture/OVERVIEW.md
docs/architecture/CORE_LIBRARY.md
docs/architecture/INTERFACES.md
docs/integration/CLAUDE_CODE.md
docs/integration/VSCODE.md
docs/integration/OLLAMA.md
docs/api/CORE_API.md
docs/api/LSP_API.md
docs/api/HTTP_API.md
docs/migration/FROM_MCP_ONLY.md
docs/migration/BREAKING_CHANGES.md

# Examples (15 files)
examples/basic_usage.py
examples/claude_code_integration.py
examples/custom_backend.py
examples/api_client_python.py
examples/api_client_node.js
examples/ollama_integration.py

# Configuration (10 files)
config/config.yaml.example
config/claude_code.json.example
config/vscode.json.example
config/lsp_settings.json.example

# Root files
pyproject.toml                             # Updated with new structure
README.md                                  # Updated with new features
CHANGELOG.md                               # Version 4.0.0 changes
CONTRIBUTING.md                            # Contribution guide
LICENSE                                    # MIT license
```

**Total:** ~200 files (current: ~100 files)

---

## Key Decisions & Rationale

### Decision 1: Async-First API

**Decision:** Core library uses async/await for all I/O operations

**Rationale:**
- PostgreSQL, Elasticsearch, file I/O are inherently I/O-bound
- Async provides better concurrency without threads
- Modern Python best practice
- Easy to add sync wrapper: `def search_sync(self, *args): return asyncio.run(self.search(*args))`

**Impact:** All interfaces must handle async (but they all do already)

### Decision 2: Keep MCP for Backward Compatibility

**Decision:** Maintain MCP server as thin wrapper, deprecate slowly (12 months)

**Rationale:**
- Existing users shouldn't break on upgrade
- Gives time for ecosystem to mature
- Shows we respect existing users
- Clear migration path

**Impact:** Must maintain MCP wrapper until v5.0.0

### Decision 3: Library-First, Not Framework

**Decision:** Core is a library you import, not a framework that calls you

**Rationale:**
- Maximum flexibility for integrators
- Easy to embed in other applications
- No "magic" - explicit is better than implicit
- Users control the main loop

**Impact:** All interfaces explicitly create and manage `CodeIndexer` instance

### Decision 4: Multi-Interface Strategy

**Decision:** Support 4 integration methods (extension, LSP, API, MCP) not just one

**Rationale:**
- Different tools prefer different protocols
- No single protocol dominates AI tool ecosystem
- Maximize reach and adoption
- Future-proof against protocol changes

**Impact:** More code to maintain, but 95% shared (core library)

### Decision 5: One-Line Installer

**Decision:** Invest heavily in installation experience

**Rationale:**
- First impression matters
- Reduces support burden
- Increases adoption rate
- Shows we care about UX

**Impact:** Significant upfront work (Week 5) but massive long-term payoff

---

## Communication Plan

### Internal Communication (Team)

**Weekly checkpoints:**
- Monday: Plan for the week
- Wednesday: Mid-week sync
- Friday: Demo + retrospective

**Tools:**
- GitHub Projects for task tracking
- Slack/Discord for async communication
- GitHub Issues for bugs/features
- Pull Requests for code review

### External Communication (Users)

**Before restructuring:**
- Blog post: "Code-Indexer v4.0 Preview"
- Explain motivation and benefits
- Invite feedback on architecture

**During restructuring:**
- Weekly progress updates on GitHub Discussions
- Alpha/beta releases for early adopters
- Maintain CHANGELOG.md

**After restructuring:**
- Blog post: "Code-Indexer v4.0 Release"
- Migration guide prominently featured
- Video tutorial for new features
- AMA (Ask Me Anything) session

### Community Engagement

**Channels:**
- GitHub Discussions (primary)
- Discord server (real-time help)
- Twitter/X (announcements)
- Reddit r/LocalLLaMA (showcase)

**Content:**
- Benchmark comparisons (MCP vs native)
- Integration tutorials
- Performance tips
- Community showcase

---

## Acceptance Criteria for Complete Restructuring

### Phase 1: Core Library ✅
- [ ] All core files moved to `src/code_indexer/`
- [ ] Public API defined in `__init__.py`
- [ ] All imports updated and working
- [ ] Existing test suite passes (>95%)
- [ ] MCP server still works (backward compatible)
- [ ] Core library can be imported independently
- [ ] AsyncIO interface fully functional
- [ ] Documentation: Core API reference

### Phase 2: Native Extension ✅
- [ ] Claude Code extension implemented
- [ ] Extension installs successfully on all platforms
- [ ] Benchmark shows >10x speedup vs MCP
- [ ] Extension handles errors gracefully
- [ ] Lifecycle methods (setup/teardown) working
- [ ] Documentation: Extension development guide
- [ ] Example: Basic extension usage

### Phase 3: LSP Server ✅
- [ ] LSP server implements core features
- [ ] VS Code extension packaged and published
- [ ] Works in Zed (via LSP config)
- [ ] Works in Cursor (via LSP config)
- [ ] Performance <100ms for symbol search
- [ ] Documentation: Editor integration guides
- [ ] Example: Custom LSP configuration

### Phase 4: HTTP API ✅
- [ ] FastAPI server running on port 8765
- [ ] All endpoints tested and documented
- [ ] OpenAPI spec complete and accurate
- [ ] Python client library working
- [ ] Node.js client library working
- [ ] Ollama integration example working
- [ ] Performance <50ms for search
- [ ] Documentation: API reference

### Phase 5: Installer ✅
- [ ] Unix installer tested on Ubuntu, Fedora, macOS
- [ ] Windows installer tested on Windows 10/11
- [ ] Auto-detection finds all installed tools
- [ ] Auto-configuration works for detected tools
- [ ] One-line install completes in <5 minutes
- [ ] Rollback mechanism works
- [ ] Documentation: Installation guide
- [ ] Documentation: Troubleshooting guide

### Overall Success Criteria ✅
- [ ] All 5 phases complete
- [ ] Zero regression in existing MCP functionality
- [ ] Test coverage >90% for core library
- [ ] All documentation complete
- [ ] Migration guide published
- [ ] Release notes comprehensive
- [ ] Community announcement posted
- [ ] v4.0.0 tagged and released

---

## One-Line Install Examples

### Unix/Linux/macOS
```bash
curl -sSL https://raw.githubusercontent.com/scooter-lacroix/code-indexer/main/scripts/install.sh | bash
```

### Windows (PowerShell)
```powershell
iwr -useb https://raw.githubusercontent.com/scooter-lacroix/code-indexer/main/scripts/install.ps1 | iex
```

### Python (cross-platform)
```bash
pip install code-indexer && code-indexer setup
```

### With specific features
```bash
# Install with all backends
curl -sSL https://... | bash -s -- --full

# Install CLI only (minimal)
curl -sSL https://... | bash -s -- --minimal

# Install and configure for Claude Code
curl -sSL https://... | bash -s -- --claude-code
```

---

## Final Checklist Before Implementation

### Pre-Flight Checks

- [ ] Current codebase committed and pushed
- [ ] Create feature branch: `git checkout -b restructure/library-first-v4`
- [ ] Backup current state: `git tag pre-restructure-backup`
- [ ] Review this plan with team
- [ ] Allocate 5 weeks on calendar
- [ ] Set up project board with tasks
- [ ] Prepare test environments (Ubuntu VM, macOS, Windows VM)

### Communication Checklist

- [ ] Draft blog post: "Code-Indexer v4.0 Preview"
- [ ] Create GitHub Discussion: "RFC: Library-First Architecture"
- [ ] Notify current users of upcoming changes
- [ ] Set up Discord/Slack for questions
- [ ] Prepare FAQ document

### Infrastructure Checklist

- [ ] CI/CD pipeline supports matrix testing
- [ ] Documentation site ready (Read the Docs or GitHub Pages)
- [ ] Benchmark infrastructure set up
- [ ] Test PyPI account for publishing
- [ ] Domain for API docs (optional)

### When to Start

✅ **Start when:**
- All pre-flight checks complete
- Team agrees on plan
- Calendar has 5 consecutive weeks available
- No major holidays/events in timeline

❌ **Don't start if:**
- Critical bugs in current version
- Major feature release pending
- Key team members unavailable
- Infrastructure not ready

---

## Summary

This restructuring plan transforms code-indexer from an MCP-first tool into a versatile library-first architecture over 5 weeks, with each week delivering a complete, testable milestone:

1. **Week 1:** Core library extracted and working
2. **Week 2:** Native extensions provide 10-100x speedup
3. **Week 3:** LSP server enables universal IDE support
4. **Week 4:** HTTP API opens language-agnostic access
5. **Week 5:** One-line installer auto-configures everything

The result: A robust, performant code indexing library that integrates seamlessly with any AI tool through its preferred protocol, while maintaining backward compatibility and providing a smooth migration path for existing users.

**Key Success Factors:**
- Preserves all existing functionality (zero regression)
- Maintains backward compatibility (MCP still works)
- Provides superior alternatives (native extensions, LSP)
- Makes installation effortless (one-line installer)
- Documents everything thoroughly (migration guides, API docs)

**Risk Mitigation:**
- Each phase is independently testable
- MCP fallback ensures users never break
- Gradual deprecation (12 months) gives time to migrate
- Rollback plans for every phase

**Post-Restructuring:**
- Community can build extensions for other tools
- Enterprise features can be added incrementally
- Advanced AI features become possible
- Platform becomes foundation for ecosystem

This plan balances ambition with pragmatism, providing a clear path from current state to desired future while respecting existing users and maintaining code quality throughout the transformation.
