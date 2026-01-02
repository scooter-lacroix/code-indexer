# Code Index MCP Server Configuration Guide

## Overview

The Code Index MCP Server provides code indexing and search capabilities, making it easy to find symbols and references across large codebases.

## Key Features

- **Fast Code Search**: Efficiently search code using indexed data
- **Symbol Indexing**: Automatic indexing of symbols and references
- **Seamless Integration**: Integrates with multiple tools and editors
- **Remote Access**: Accessible via HTTP or local stdio transport
- **Comprehensive Logging**: Detailed logging for search and indexing activities

## Installation

### Local Installation
```bash
# Clone and install
git clone https://github.com/scooter-lacroix/code-indexer.git
cd code-indexer
uv pip install -e .

# Or install from package
pip install sc-code-indexer
```

### Direct UV Installation
```bash
uvx git+https://github.com/scooter-lacroix/code-indexer.git
```

## Configuration Examples

### 1. LM Studio

```json
{
  "mcpServers": {
    "code-index": {
      "command": "uvx",
      "args": ["git+https://github.com/scooter-lacroix/code-indexer.git"],
      "env": {},
      "start_on_launch": true
    }
  }
}
```

### 2. VS Code / Cursor / Windsurf

#### Using MCP Extension
```json
{
  "mcp.servers": {
    "code-index": {
      "command": "code-index-mcp",
      "args": [],
      "env": {},
      "transport": "stdio"
    }
  }
}
```

#### Using Continue Extension
```json
{
  "mcpServers": [
    {
      "name": "code-index",
      "command": "code-index-mcp",
      "args": [],
      "env": {}
    }
  ]
}
```

### 3. Jan AI

```json
{
  "mcp_servers": {
    "code-index": {
      "command": "code-index-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

### 4. OpenHands

```json
{
  "mcp": {
    "servers": {
      "code-index": {
        "command": "code-index-mcp",
        "args": [],
        "env": {}
      }
    }
  }
}
```

### 5. HTTP/HTTPS Server Mode

For web-based integrations:

```bash
# Start HTTP server
python -m code_index.server --port 8765

# Or using the convenience script
uvx code-index-mcp --http
```

Configuration:
```json
{
  "mcpServers": {
    "code-index": {
      "transport": "http",
      "url": "http://localhost:8765/mcp",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

### 6. Git Link Installation

For environments that support git installation:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "uvx",
      "args": [
        "git+https://github.com/scooter-lacroix/code-index-mcp.git"
      ],
      "env": {}
    }
  }
}
```

## Environment Variables

### Required
- `VIRTUAL_ENV`: Path to Python virtual environment (auto-detected)

### Optional
- `CODE_INDEX_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `CODE_INDEX_MAX_MEMORY`: Maximum memory usage in MB
- `CODE_INDEX_PORT`: Port number for HTTP server (default: 8765)

## Available Commands

### Core Indexing
- `index_repository`: Index a repository for symbols and references
- `search_symbols`: Search symbols within the indexed data
- `clear_index`: Clear existing index data

### Integration
- `integrate_with_lm_studio`: Set up LM Studio integration
- `integrate_with_vscode`: Configure VS Code integration
- `configure_remote_access`: Set up remote HTTP access

### Monitoring
- `get_indexing_status`: Get current indexing progress
- `get_search_statistics`: Retrieve search performance metrics

## Usage Examples

### Basic Search
```bash
# Search for a function
code-index search_symbols "function_name"

# Search with path filter
code-index search_symbols "function_name" --path "src/*"
```

### Indexing Operations
```bash
# Index a local repository
index_repository --path "/home/user/my_project"

# Re-index with remote repository
index_repository --url "https://github.com/scooter-lacroix/code-indexer.git"
```

### HTTP Server Mode

Enable HTTP Mode for remote access:
```bash
uvx code-index-mcp --http --port 8765
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Verify HTTP server is running and correct port
   ```bash
   python -m code_index.server --port 8765
   ```

2. **Index Not Found**: Ensure repository is indexed before searching
   ```bash
   uvx code-index-mcp --index
   ```

### Debug Mode

Enable debug logging:
```bash
export CODE_INDEX_LOG_LEVEL=DEBUG
uvx code-index-mcp
```

## Advanced Configuration

### Custom Port
```json
{
  "code-index": {
    "env": {
      "CODE_INDEX_PORT": "8080"
    }
  }
}
```

### Memory Limit
```json
{
  "code-index": {
    "env": {
      "CODE_INDEX_MAX_MEMORY": "1024"
    }
  }
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

