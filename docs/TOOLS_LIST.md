# Code Index MCP - Complete Tools Reference

This document provides a comprehensive reference for all available MCP tools in the Code Index MCP server, including usage examples and system prompt templates.

## 🛠️ Core Project Management Tools

### `set_project_path`
**Purpose**: Sets the base project path for indexing and initializes the project workspace.

**Parameters**:
- `path` (string, required): Absolute or relative path to the project directory

**Usage Example**:
```json
{
  "name": "set_project_path",
  "arguments": {
    "path": "/home/user/projects/my-app"
  }
}
```

**What it does**:
- Validates and normalizes the project path
- Initializes or loads existing file index
- Sets up database connections (PostgreSQL + Elasticsearch)
- Configures search tools and memory management
- Returns project statistics and search capabilities

---

### `refresh_index`
**Purpose**: Refreshes the project index to include new or modified files.

**Parameters**: None

**Usage Example**:
```json
{
  "name": "refresh_index",
  "arguments": {}
}
```

**What it does**:
- Performs incremental indexing of changed files
- Updates PostgreSQL metadata
- Refreshes Elasticsearch search index
- Provides progress tracking for large projects

---

## 🔍 Search and Discovery Tools

### `search_code_advanced`
**Purpose**: Advanced code search with fuzzy matching, highlighting, and filtering capabilities.

**Parameters**:
- `pattern` (string, required): Search pattern or query
- `case_sensitive` (boolean, optional): Case-sensitive search (default: true)
- `context_lines` (integer, optional): Lines of context around matches (default: 0)
- `file_pattern` (string, optional): Glob pattern to filter files (e.g., "*.py")
- `fuzzy` (boolean, optional): Enable fuzzy/regex matching (default: false)
- `fuzziness_level` (string, optional): Elasticsearch fuzziness ("AUTO", "0", "1", "2")
- `content_boost` (float, optional): Boost factor for content field (default: 1.0)
- `filepath_boost` (float, optional): Boost factor for file path field (default: 1.0)
- `highlight_pre_tag` (string, optional): HTML tag for highlighting start (default: "<em>")
- `highlight_post_tag` (string, optional): HTML tag for highlighting end (default: "</em>")
- `page` (integer, optional): Page number for pagination (default: 1)
- `page_size` (integer, optional): Results per page (default: 20)

**Usage Examples**:
```json
// Basic search
{
  "name": "search_code_advanced",
  "arguments": {
    "pattern": "function authenticate",
    "case_sensitive": false
  }
}

// Advanced search with fuzzy matching
{
  "name": "search_code_advanced",
  "arguments": {
    "pattern": "authUser",
    "fuzzy": true,
    "fuzziness_level": "AUTO",
    "file_pattern": "*.js",
    "context_lines": 3
  }
}

// Search with custom highlighting
{
  "name": "search_code_advanced",
  "arguments": {
    "pattern": "API_ENDPOINT",
    "highlight_pre_tag": "<mark>",
    "highlight_post_tag": "</mark>",
    "content_boost": 2.0
  }
}
```

---

### `find_files`
**Purpose**: Find files matching a specific glob pattern.

**Parameters**:
- `pattern` (string, required): Glob pattern to match files

**Usage Examples**:
```json
// Find all Python files
{
  "name": "find_files",
  "arguments": {
    "pattern": "**/*.py"
  }
}

// Find React components
{
  "name": "find_files",
  "arguments": {
    "pattern": "src/components/**/*.tsx"
  }
}

// Find configuration files
{
  "name": "find_files",
  "arguments": {
    "pattern": "**/{*.json,*.yaml,*.yml,*.toml}"
  }
}
```

---

## 📄 File Analysis Tools

### `get_file_summary`
**Purpose**: Get a comprehensive summary of a file including structure, functions, and metadata.

**Parameters**:
- `file_path` (string, required): Path to the file relative to project root

**Usage Example**:
```json
{
  "name": "get_file_summary",
  "arguments": {
    "file_path": "src/utils/helpers.py"
  }
}
```

**Returns**:
- Line count and file size
- Function and class definitions
- Import statements
- Complexity metrics
- File metadata

---

## ✏️ File Modification Tools

### `write_to_file`
**Purpose**: Write content to a file with automatic version tracking.

**Parameters**:
- `path` (string, required): File path relative to project root
- `content` (string, required): Content to write to the file
- `line_count` (integer, required): Expected number of lines in content

**Usage Example**:
```json
{
  "name": "write_to_file",
  "arguments": {
    "path": "src/config.py",
    "content": "# Configuration file\nDEBUG = True\nAPI_URL = 'https://api.example.com'\n",
    "line_count": 3
  }
}
```

**Features**:
- Automatic directory creation
- Version tracking with PostgreSQL
- Real-time Elasticsearch indexing
- Diff generation for changes

---

### `search_and_replace`
**Purpose**: Find and replace text in files with regex support and version tracking.

**Parameters**:
- `path` (string, required): File path relative to project root
- `search` (string, required): Text or pattern to search for
- `replace` (string, required): Replacement text
- `start_line` (integer, optional): Start line for replacement scope
- `end_line` (integer, optional): End line for replacement scope
- `use_regex` (boolean, optional): Use regular expressions (default: false)
- `ignore_case` (boolean, optional): Case-insensitive search (default: false)

**Usage Examples**:
```json
// Simple text replacement
{
  "name": "search_and_replace",
  "arguments": {
    "path": "src/config.py",
    "search": "DEBUG = False",
    "replace": "DEBUG = True"
  }
}

// Regex replacement with scope
{
  "name": "search_and_replace",
  "arguments": {
    "path": "src/api.py",
    "search": "def (\\w+)_handler\\(",
    "replace": "async def $1_handler(",
    "use_regex": true,
    "start_line": 10,
    "end_line": 50
  }
}
```

---

### `apply_diff`
**Purpose**: Apply targeted modifications to multiple files simultaneously.

**Parameters**:
- `args` (array, required): Array of modification objects

**Usage Example**:
```json
{
  "name": "apply_diff",
  "arguments": {
    "args": [
      {
        "path": "src/main.py",
        "search": "import os",
        "replace": "import os\nimport sys"
      },
      {
        "path": "src/utils.py",
        "search": "def helper():",
        "replace": "async def helper():"
      }
    ]
  }
}
```

---

### `insert_content`
**Purpose**: Insert new content into a file at a specific line.

**Parameters**:
- `path` (string, required): File path relative to project root
- `line` (integer, required): Line number to insert before (0 = append to end)
- `content` (string, required): Content to insert

**Usage Example**:
```json
{
  "name": "insert_content",
  "arguments": {
    "path": "src/main.py",
    "line": 5,
    "content": "# New import added\nimport datetime\n"
  }
}
```

---

## 📚 Version Control Tools

### `get_file_history`
**Purpose**: Retrieve the complete change history for a file.

**Parameters**:
- `file_path` (string, required): Path to the file relative to project root

**Usage Example**:
```json
{
  "name": "get_file_history",
  "arguments": {
    "file_path": "src/models/user.py"
  }
}
```

**Returns**:
- Complete version history with timestamps
- Diff content showing exact changes
- Operation types (create, edit, delete)
- Version IDs for specific retrieval

---

### `revert_file_to_version`
**Purpose**: Revert a file to a previous version.

**Parameters**:
- `file_path` (string, required): Path to the file
- `version_id` (string, optional): Specific version ID to revert to
- `timestamp` (string, optional): Timestamp to revert to (alternative to version_id)

**Usage Example**:
```json
{
  "name": "revert_file_to_version",
  "arguments": {
    "file_path": "src/config.py",
    "version_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

---

## 🗂️ File Management Tools

### `delete_file`
**Purpose**: Delete a file with version tracking.

**Parameters**:
- `file_path` (string, required): Path to the file to delete

**Usage Example**:
```json
{
  "name": "delete_file",
  "arguments": {
    "file_path": "src/deprecated/old_module.py"
  }
}
```

---

### `rename_file`
**Purpose**: Rename or move a file with version tracking.

**Parameters**:
- `old_file_path` (string, required): Current file path
- `new_file_path` (string, required): New file path

**Usage Example**:
```json
{
  "name": "rename_file",
  "arguments": {
    "old_file_path": "src/utils.py",
    "new_file_path": "src/helpers/utils.py"
  }
}
```

---

## ⚙️ System Management Tools

### `get_settings_info`
**Purpose**: Get information about project settings and configuration.

**Parameters**: None

**Usage Example**:
```json
{
  "name": "get_settings_info",
  "arguments": {}
}
```

---

### `create_temp_directory`
**Purpose**: Create the temporary directory for index data storage.

**Parameters**: None

---

### `check_temp_directory`
**Purpose**: Check the status of the temporary directory.

**Parameters**: None

---

### `clear_settings`
**Purpose**: Clear all settings and cached data.

**Parameters**: None

---

### `reset_server_state`
**Purpose**: Completely reset the server state including global variables.

**Parameters**: None

---

## 🔧 Performance and Monitoring Tools

### `refresh_search_tools`
**Purpose**: Re-detect available command-line search tools.

**Parameters**: None

---

### `get_ignore_patterns`
**Purpose**: Get information about loaded ignore patterns.

**Parameters**: None

---

### `get_filtering_config`
**Purpose**: Get current filtering configuration.

**Parameters**: None

---

### `get_lazy_loading_stats`
**Purpose**: Get statistics about lazy loading memory management.

**Parameters**: None

---

### `get_incremental_indexing_stats`
**Purpose**: Get statistics about incremental indexing metadata.

**Parameters**: None

---

### `get_memory_profile`
**Purpose**: Get comprehensive memory profiling statistics.

**Parameters**: None

---

### `trigger_memory_cleanup`
**Purpose**: Manually trigger memory cleanup and garbage collection.

**Parameters**: None

---

### `configure_memory_limits`
**Purpose**: Update memory limits configuration.

**Parameters**:
- `soft_limit_mb` (number, optional): Soft memory limit in MB
- `hard_limit_mb` (number, optional): Hard memory limit in MB
- `max_loaded_files` (integer, optional): Maximum files to keep in memory
- `max_cached_queries` (integer, optional): Maximum cached queries

---

### `export_memory_profile`
**Purpose**: Export detailed memory profile to a file.

**Parameters**:
- `file_path` (string, optional): Path to export the profile

---

### `get_performance_metrics`
**Purpose**: Get comprehensive performance monitoring metrics.

**Parameters**: None

---

### `export_performance_metrics`
**Purpose**: Export performance metrics to a JSON file.

**Parameters**:
- `file_path` (string, optional): Path to export metrics

---

## 🔄 Operation Management Tools

### `get_active_operations`
**Purpose**: Get status of all active operations with progress tracking.

**Parameters**: None

---

### `get_operation_status`
**Purpose**: Get detailed status of a specific operation.

**Parameters**:
- `operation_id` (string, required): ID of the operation to check

---

### `cancel_operation`
**Purpose**: Cancel a specific operation.

**Parameters**:
- `operation_id` (string, required): ID of the operation to cancel
- `reason` (string, optional): Reason for cancellation

---

### `cancel_all_operations`
**Purpose**: Cancel all active operations.

**Parameters**:
- `reason` (string, optional): Reason for cancellation

---

### `cleanup_completed_operations`
**Purpose**: Clean up completed operations older than specified hours.

**Parameters**:
- `max_age_hours` (number, optional): Maximum age in hours (default: 1)

---

## 📋 System Prompt Template

Use this template in your AI model's system prompt to ensure proper tool usage:

```markdown
# Code Index MCP Tools Usage Guidelines

You have access to a comprehensive Code Index MCP server with the following capabilities:

## 🚀 **ALWAYS START WITH PROJECT SETUP**
1. **FIRST**: Use `set_project_path` to initialize the project workspace
2. **THEN**: Use other tools as needed for analysis and modification

## 🔍 **Search and Discovery Best Practices**
- Use `search_code_advanced` for code searches with fuzzy matching and filtering
- Use `find_files` for file discovery with glob patterns
- Use `get_file_summary` before modifying files to understand structure

## ✏️ **File Modification Guidelines**
- **ALWAYS** use MCP tools for file operations (never direct file system access)
- Use `write_to_file` for creating or completely rewriting files
- Use `search_and_replace` for targeted modifications with regex support
- Use `apply_diff` for multi-file modifications
- Use `insert_content` for adding content at specific locations

## 📚 **Version Control Integration**
- Use `get_file_history` to view complete change history
- Use `revert_file_to_version` to undo changes
- All file modifications automatically create version history

## 🎯 **Tool Selection Logic**
- **File Discovery**: `find_files` → `get_file_summary` → detailed analysis
- **Code Search**: `search_code_advanced` with appropriate filters and fuzzy matching
- **File Modification**: Choose based on scope:
  - Single file, complete rewrite: `write_to_file`
  - Single file, targeted changes: `search_and_replace`
  - Multiple files: `apply_diff`
  - Insert at specific location: `insert_content`

## ⚡ **Performance Optimization**
- Use `refresh_index` after major project changes
- Monitor operations with `get_active_operations`
- Use memory management tools for large projects

## 🛡️ **Error Handling**
- Always check tool responses for success/error status
- Use version control tools to recover from mistakes
- Monitor system resources with performance tools

## 📝 **Example Workflow**
1. `set_project_path` - Initialize project
2. `find_files` - Discover relevant files
3. `get_file_summary` - Understand file structure
4. `search_code_advanced` - Find specific code patterns
5. `write_to_file` or `search_and_replace` - Make modifications
6. `get_file_history` - Verify changes if needed

Remember: This is an enterprise-grade system with PostgreSQL metadata storage, Elasticsearch search, and comprehensive version tracking. All operations are logged and tracked for complete auditability.
```

## 🔧 Configuration Examples

### Basic MCP Configuration
```json
{
  "mcpServers": {
    "code-index": {
      "command": "uvx",
      "args": ["git+https://github.com/your-repo/code-index-mcp.git"],
      "env": {
        "DAL_BACKEND_TYPE": "postgresql_elasticsearch_only",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "codeindex",
        "POSTGRES_PASSWORD": "your-password",
        "POSTGRES_DB": "code_index_db",
        "ELASTICSEARCH_HOSTS": "http://localhost:9200"
      }
    }
  }
}
```

### Development Configuration with Docker
```json
{
  "mcpServers": {
    "code-index-dev": {
      "command": "uv",
      "args": ["run", "code_index_mcp"],
      "env": {
        "DAL_BACKEND_TYPE": "dual_write_read",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "ELASTICSEARCH_HOSTS": "http://localhost:9200"
      }
    }
  }
}
```

This comprehensive tool reference provides everything needed to effectively use the Code Index MCP server in your AI workflows.