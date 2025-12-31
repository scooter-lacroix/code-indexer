# Migration Guide: MCP Tool Consolidation

## Breaking Change Notice

This is a **HARD BREAKING CHANGE**. The code-indexer MCP server is consolidating from 42 individual tools to 9 consolidated "mega-tools". All old tool names have been removed and are no longer supported.

**Migration Required:** All agents, scripts, and integrations using the old tool names must be updated to use the new mega-tools.

---

## Tool Mapping Reference

### 1. manage_project (Consolidates 5 tools)

| Old Tool | New Tool + Action |
|----------|-------------------|
| `set_project_path` | `manage_project(action="set_path", path=...)` |
| `refresh_index` | `manage_project(action="refresh")` |
| `force_reindex` | `manage_project(action="reindex", clear_cache=True)` |
| `clear_settings` | `manage_project(action="clear")` |
| `reset_server_state` | `manage_project(action="reset")` |

### 2. search_content (Consolidates 3 tools)

| Old Tool | New Tool + Action |
|----------|-------------------|
| `search_code_advanced` | `search_content(action="search", pattern=...)` |
| `find_files` | `search_content(action="find", pattern=...)` |
| `rank_search_results` | `search_content(action="rank", results=..., query=...)` |

### 3. modify_file (Consolidates 4 tools)

| Old Tool | New Tool + Operation |
|----------|---------------------|
| `write_to_file` | `modify_file(operation="write", path=..., content=..., line_count=...)` |
| `apply_diff` | `modify_file(operation="diff", path=..., search=..., replace=...)` |
| `insert_content` | `modify_file(operation="insert", path=..., line=..., content=...)` |
| `search_and_replace` | `modify_file(operation="replace", path=..., search=..., replace=...)` |

### 4. manage_files (Consolidates 4 tools)

| Old Tool | New Tool + Action |
|----------|-------------------|
| `delete_file` | `manage_files(action="delete", file_path=...)` |
| `rename_file` | `manage_files(action="rename", old_file_path=..., new_file_path=...)` |
| `revert_file_to_version` | `manage_files(action="revert", file_path=..., version_id=...)` |
| `get_file_history` | `manage_files(action="history", file_path=...)` |

### 5. get_diagnostics (Consolidates 9 tools)

| Old Tool | New Tool + Type |
|----------|----------------|
| `get_memory_profile` | `get_diagnostics(type="memory")` |
| `get_index_statistics` | `get_diagnostics(type="index")` |
| `get_backend_health` | `get_diagnostics(type="backend")` |
| `get_performance_metrics` | `get_diagnostics(type="performance")` |
| `get_active_operations` | `get_diagnostics(type="operations")` |
| `get_settings_info` | `get_diagnostics(type="settings")` |
| `get_ignore_patterns` | `get_diagnostics(type="ignore")` |
| `get_filtering_config` | `get_diagnostics(type="filtering")` |
| `get_ranking_configuration` | `get_diagnostics(type="ranking")` |

### 6. manage_memory (Consolidates 3 tools)

| Old Tool | New Tool + Action |
|----------|-------------------|
| `trigger_memory_cleanup` | `manage_memory(action="cleanup")` |
| `configure_memory_limits` | `manage_memory(action="configure", soft_limit_mb=..., hard_limit_mb=...)` |
| `export_memory_profile` | `manage_memory(action="export", file_path=...)` |

### 7. manage_operations (Consolidates 4 tools)

| Old Tool | New Tool + Action |
|----------|-------------------|
| `get_active_operations` | `manage_operations(action="list")` |
| `get_operation_status` | `manage_operations(action="list", operation_id=...)` |
| `cancel_operation` | `manage_operations(action="cancel", operation_id=...)` |
| `cleanup_completed_operations` | `manage_operations(action="cleanup", max_age_hours=...)` |

### 8. read_file (Consolidates 4 tools)

| Old Tool | New Tool + Mode |
|----------|----------------|
| `analyze_file_with_smart_reader` | `read_file(mode="smart", file_path=...)` |
| `read_file_chunks` | `read_file(mode="chunks", file_path=..., chunk_size=...)` |
| `detect_file_errors` | `read_file(mode="detect_errors", file_path=...)` |
| `get_file_metadata` | `read_file(mode="metadata", file_path=...)` |

### 9. manage_temp (Consolidates 2 tools)

| Old Tool | New Tool + Action |
|----------|-------------------|
| `create_temp_directory` | `manage_temp(action="create")` |
| `check_temp_directory` | `manage_temp(action="check")` |

---

## Removed Tools

The following tools have been **completely removed** without replacement:

### API Key Management (4 tools)
- `list_api_keys` - No longer needed (removing Mixedbread cloud dependency)
- `reset_api_key_quota` - No longer needed (removing Mixedbread cloud dependency)
- `set_rotation_strategy` - No longer needed (removing Mixedbread cloud dependency)
- `get_api_key_statistics` - No longer needed (removing Mixedbread cloud dependency)

### Analytics (2 tools)
- `get_user_behavior_stats` - Behavior analytics removed
- `clear_user_behavior_history` - Behavior analytics removed

### Utility (1 tool)
- `compare_file_reading_strategies` - Internal debugging tool, no longer exposed

---

## Migration Examples

### Example 1: Simple Tool Call

**Before:**
```python
result = await mcp.call_tool("set_project_path", {"path": "/home/user/project"})
```

**After:**
```python
result = await mcp.call_tool("manage_project", {
    "action": "set_path",
    "path": "/home/user/project"
})
```

### Example 2: Tool with Optional Parameters

**Before:**
```python
result = await mcp.call_tool("force_reindex", {"clear_cache": True})
```

**After:**
```python
result = await mcp.call_tool("manage_project", {
    "action": "reindex",
    "clear_cache": True
})
```

### Example 3: Complex Tool with Multiple Options

**Before:**
```python
result = await mcp.call_tool("search_code_advanced", {
    "pattern": "function foo",
    "backend": "zoekt",
    "case_sensitive": False,
    "max_results": 50
})
```

**After:**
```python
result = await mcp.call_tool("search_content", {
    "action": "search",
    "pattern": "function foo",
    "backend": "zoekt",
    "case_sensitive": False,
    "max_results": 50
})
```

---

## Return Type Compatibility

All mega-tools return the same data types as the original tools:
- `manage_project`: Returns `str` or `Dict[str, Any]` (same as original)
- `search_content`: Returns `List[Dict[str, Any]]` or `List[str]`
- `modify_file`: Returns `Dict[str, Any]`
- `manage_files`: Returns `Dict[str, Any]`
- `get_diagnostics`: Returns `Dict[str, Any]`
- `manage_memory`: Returns `Dict[str, Any]`
- `manage_operations`: Returns `Dict[str, Any]`
- `read_file`: Returns `Dict[str, Any]`
- `manage_temp`: Returns `Dict[str, Any]`

---

## Step-by-Step Migration Process

1. **Audit Current Usage**
   ```bash
   # Search for uses of old tool names in your codebase
   grep -r "set_project_path\|refresh_index\|force_reindex" .
   grep -r "search_code_advanced\|find_files\|rank_search_results" .
   grep -r "write_to_file\|apply_diff\|insert_content" .
   # ... continue for all old tool names
   ```

2. **Update Tool Calls**
   - Replace old tool names with new mega-tool names
   - Add the appropriate `action`, `operation`, or `type` parameter
   - Keep all other parameters the same

3. **Test Changes**
   - Run your integration tests
   - Verify all tool calls work correctly
   - Check return values match expectations

4. **Update Documentation**
   - Update any internal documentation referencing old tool names
   - Update user guides with new tool names
   - Update examples in README files

---

## Common Migration Patterns

### Pattern 1: Adding Action Parameter

Most migrations simply require adding an action parameter:

```python
# Before
await mcp.call_tool("refresh_index", {})

# After
await mcp.call_tool("manage_project", {"action": "refresh"})
```

### Pattern 2: Renaming Parameters

Some tools have renamed parameters for clarity:

```python
# Before
await mcp.call_tool("delete_file", {"file_path": "/path/to/file"})

# After
await mcp.call_tool("manage_files", {
    "action": "delete",
    "file_path": "/path/to/file"  # Same parameter name
})
```

### Pattern 3: Multiple Parameters

Some tools combine multiple parameters:

```python
# Before
await mcp.call_tool("configure_memory_limits", {
    "soft_limit_mb": 1024,
    "hard_limit_mb": 2048
})

# After
await mcp.call_tool("manage_memory", {
    "action": "configure",
    "soft_limit_mb": 1024,
    "hard_limit_mb": 2048  # Same parameters
})
```

---

## Rollback Plan

If you encounter issues after migration:

1. **Temporary Rollback**: You can temporarily revert to an older version of code-indexer
2. **Permanent Fix**: Update your code to use the new mega-tools
3. **Get Help**: Open an issue on GitHub with your specific use case

---

## Timeline

- **Release Date**: TBD
- **Support End for Old Tools**: Immediate (hard break)
- **Migration Window**: N/A (no support period for old tools)

---

## Questions?

If you have questions about this migration:

1. Check the [GitHub Issues](https://github.com/your-repo/issues) for similar questions
2. Open a new issue with the tag `migration-help`
3. Include your current tool call and what you've tried
