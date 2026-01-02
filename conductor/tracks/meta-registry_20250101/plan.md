# Implementation Plan: Self-Indexing Meta-Registry with Persistence Fixes

**Track ID:** meta-registry_20250101
**Status:** New
**Target Version:** v2.1.0 (breaking changes)

## Phase 1: Foundation - Registry and MessagePack Infrastructure [checkpoint: 4bacb11]

### Task: 1.1 Create ProjectRegistry class
- [ ] Subtask: Create `src/code_index_mcp/registry/` directory
- [ ] Subtask: Create `src/code_index_mcp/registry/__init__.py`
- [ ] Subtask: Create `src/code_index_mcp/registry/project_registry.py`
- [ ] Subtask: Implement SQLite connection with WAL mode and FULL synchronous
- [ ] Subtask: Create registry schema:
  - `projects` table (id, path, path_hash, indexed_at, file_count, config JSON, stats JSON, index_location)
  - `registry_metadata` table (key, value) with:
    - `schema_version` (for future migrations)
    - `last_backup_time` (for periodic backup tracking)
    - `created_at`, `updated_at`
- [ ] Subtask: Implement SHA-256 path hashing utility
- [ ] Subtask: Implement CRUD operations (insert, update, delete, query)
- [ ] Subtask: Add JSON column support for config and stats
- [ ] Subtask: Write unit tests for ProjectRegistry
- [ ] Subtask: Verify >95% code coverage

### Task: 1.2 Create MessagePack Index Serializer
- [ ] Subtask: Create `src/code_index_mcp/registry/msgpack_serializer.py`
- [ ] Subtask: Implement format detection (magic bytes/file extension)
- [ ] Subtask: Support reading pickle format (read-only, for migration)
- [ ] Subtask: Support reading MessagePack format
- [ ] Subtask: Always write MessagePack format
- [ ] Subtask: Implement atomic write pattern (temp + rename)
- [ ] Subtask: Write unit tests for MessagePack serialization
- [ ] Subtask: Verify backward compatibility (read pickle, write msgpack)
- [ ] Subtask: Verify >95% code coverage

### Task: 1.3 Global Directory Management
- [ ] Subtask: Implement `~/.code-indexer/` directory creation
- [ ] Subtask: Create `.code-indexer/` per-project directory structure
- [ ] Subtask: Add path utilities for registry and project locations
- [ ] Subtask: Write unit tests for directory management
- [ ] Subtask: Verify >95% code coverage

### Task: Conductor - User Manual Verification 'Phase 1'
- [ ] Verify test coverage meets >95% requirement
- [ ] Verify all tests pass
- [ ] Verify code follows style guidelines
- [ ] Verify no linting errors
- [ ] Create checkpoint commit

## Phase 2: Critical Persistence Fixes [checkpoint: 181a25b]

### Task: 2.1 Fix Pickle Usage
- [ ] Subtask: Replace all pickle usage with MessagePack in `optimized_project_settings.py`
- [ ] Subtask: Update load_index() to use format detection (pickle vs msgpack)
- [ ] Subtask: Update save_index() to always use MessagePack
- [ ] Subtask: Ensure no new pickle files are created
- [ ] Subtask: Write unit tests for format detection
- [ ] Subtask: Verify >95% code coverage

### Task: 2.2 Add SQLite PRAGMA Settings
- [ ] Subtask: Add PRAGMA synchronous = FULL to SQLite initialization
- [ ] Subtask: Add PRAGMA journal_mode = WAL to SQLite initialization
- [ ] Subtask: Add PRAGMA foreign_keys = ON to SQLite initialization
- [ ] Subtask: Apply to both registry and DAL SQLite storage
- [ ] Subtask: Write unit tests for PRAGMA settings
- [ ] Subtask: Verify >95% code coverage

### Task: 2.3 Add Explicit Flush Before Shutdown
- [ ] Subtask: Modify indexer_lifespan finally block in `server.py`
- [ ] Subtask: Add explicit flush for DAL backends before close()
- [ ] Subtask: Add explicit flush for SQLite registry before close()
- [ ] Subtask: Ensure all transactions committed before close
- [ ] Subtask: Write integration tests for shutdown flush
- [ ] Subtask: Verify >95% code coverage

### Task: 2.4 Implement Atomic Saves
- [ ] Subtask: Update MessagePack write to use temp+rename pattern
- [ ] Subtask: Update registry backup to use temp+rename pattern
- [ ] Subtask: Ensure atomic operations for all critical writes
- [ ] Subtask: Write unit tests for atomic operations
- [ ] Subtask: Verify >95% code coverage

### Task: 2.5 Technical Debt: Consolidate Metadata Systems
- [ ] Subtask: Analyze IncrementalIndexer.file_metadata vs SQLiteFileMetadata
- [ ] Subtask: Design unified metadata schema
- [ ] Subtask: Migrate to single source of truth (SQLiteFileMetadata)
- [ ] Subtask: Remove duplicate metadata tracking
- [ ] Subtask: Write migration tests for metadata consolidation
- [ ] Subtask: Verify >95% code coverage
- [ ] Note: Lower priority than spec requirements, implement opportunistically

### Task: Conductor - User Manual Verification 'Phase 2'
- [ ] Verify test coverage meets >95% requirement
- [ ] Verify all tests pass
- [ ] Verify code follows style guidelines
- [ ] Verify no linting errors
- [ ] Create checkpoint commit

## Phase 3: Migration - Pickle to MessagePack

### Task: 3.1 Create IndexMigrator Class
- [ ] Subtask: Create `src/code_index_mcp/registry/index_migrator.py`
- [ ] Subtask: Implement legacy pickle detection (scan `.code_indexer_data/`)
- [ ] Subtask: Implement pickle load and validation using MessagePackSerializer
- [ ] Subtask: Implement MessagePack conversion
- [ ] Subtask: Implement backup creation (preserve original pickle)
- [ ] Subtask: Implement migration verification (compare counts, checksums)
- [ ] Subtask: Implement rollback capability
- [ ] Subtask: Write unit tests for migration logic
- [ ] Subtask: Verify >95% code coverage

### Task: 3.2 Startup Migration Detection
- [ ] Subtask: Add migration check on server startup
- [ ] Subtask: Detect legacy pickle indexes automatically
- [ ] Subtask: Offer migration prompt to user (via log)
- [ ] Subtask: Implement auto-migrate on first access
- [ ] Subtask: Track migration status in registry_metadata
- [ ] Subtask: Write integration tests for startup migration
- [ ] Subtask: Verify >95% code coverage

### Task: Conductor - User Manual Verification 'Phase 3'
- [ ] Verify test coverage meets >95% requirement
- [ ] Verify all tests pass
- [ ] Verify code follows style guidelines
- [ ] Verify no linting errors
- [ ] Create checkpoint commit

## Phase 4: Auto-Registration Integration

### Task: 4.1 Integrate Registration with manage_project
- [ ] Subtask: Modify `manage_project` to call registration after MessagePack index save
- [ ] Subtask: Implement sequential write pattern (index first, registry second)
- [ ] Subtask: Add orphan detection on startup
- [ ] Subtask: Handle registration failures gracefully (log warning, continue)
- [ ] Subtask: Update registry on reindex (update timestamp, stats)
- [ ] Subtask: Write integration tests for auto-registration
- [ ] Subtask: Verify >95% code coverage

### Task: 4.2 Orphan Detection and Recovery
- [ ] Subtask: Create `src/code_index_mcp/registry/orphan_detector.py`
- [ ] Subtask: Implement filesystem scan for orphaned indexes
- [ ] Subtask: Compare filesystem scan against registry
- [ ] Subtask: Offer to register or cleanup orphans
- [ ] Subtask: Write unit tests for orphan detection
- [ ] Subtask: Verify >95% code coverage

### Task: Conductor - User Manual Verification 'Phase 4'
- [ ] Verify test coverage meets >95% requirement
- [ ] Verify all tests pass
- [ ] Verify code follows style guidelines
- [ ] Verify no linting errors
- [ ] Create checkpoint commit

## Phase 5: MCP Tools Implementation

### Task: 5.1 Implement get_registry_status()
- [ ] Subtask: Add MCP tool to `server.py`
- [ ] Subtask: Query registry for statistics
- [ ] Subtask: Return formatted status (project count, last indexed, etc.)
- [ ] Subtask: Write unit tests for tool
- [ ] Subtask: Verify >95% code coverage

### Task: 5.2 Implement registry_health_check()
- [ ] Subtask: Add MCP tool to `server.py`
- [ ] Subtask: Verify project paths exist
- [ ] Subtask: Verify index files exist
- [ ] Subtask: Verify MessagePack integrity
- [ ] Subtask: Return per-project health details
- [ ] Subtask: Calculate overall status (healthy/warning/critical)
- [ ] Subtask: Write unit tests for health check
- [ ] Subtask: Verify >95% code coverage

### Task: 5.3 Implement registry_cleanup()
- [ ] Subtask: Add MCP tool to `server.py`
- [ ] Subtask: Implement force flag support
- [ ] Subtask: Create backup before cleanup
- [ ] Subtask: Remove invalid projects from registry
- [ ] Subtask: Require confirmation unless --force
- [ ] Subtask: Write unit tests for cleanup
- [ ] Subtask: Verify >95% code coverage

### Task: 5.4 Implement reindex_all_projects()
- [ ] Subtask: Add MCP tool to `server.py`
- [ ] Subtask: Implement iteration through all registered projects
- [ ] Subtask: Implement change detection (mtime, hash)
- [ ] Subtask: Support --force and --dry-run flags
- [ ] Subtask: Implement progress reporting
- [ ] Subtask: Handle errors gracefully (continue with next project)
- [ ] Subtask: Update registry with new timestamps
- [ ] Subtask: Write unit tests for reindex
- [ ] Subtask: Verify >95% code coverage

### Task: 5.5 Implement migrate_legacy_indexes()
- [ ] Subtask: Add MCP tool to `server.py`
- [ ] Subtask: Expose migration functionality as MCP tool
- [ ] Subtask: Support individual project or full migration
- [ ] Subtask: Return migration status and results
- [ ] Subtask: Write unit tests for tool
- [ ] Subtask: Verify >95% code coverage

### Task: 5.6 Implement detect_orphaned_indexes()
- [ ] Subtask: Add MCP tool to `server.py`
- [ ] Subtask: Expose orphan detection as MCP tool
- [ ] Subtask: Offer registration or cleanup options
- [ ] Subtask: Return orphan list and recommendations
- [ ] Subtask: Write unit tests for tool
- [ ] Subtask: Verify >95% code coverage

### Task: 5.7 Implement backup_registry()
- [ ] Subtask: Add MCP tool to `server.py`
- [ ] Subtask: Implement immediate backup trigger
- [ ] Subtask: Return backup file path
- [ ] Subtask: Write unit tests for tool
- [ ] Subtask: Verify >95% code coverage

### Task: Conductor - User Manual Verification 'Phase 5'
- [ ] Verify test coverage meets >95% requirement
- [ ] Verify all tests pass
- [ ] Verify code follows style guidelines
- [ ] Verify no linting errors
- [ ] Create checkpoint commit

## Phase 6: Automatic Backup System

### Task: 6.1 Create RegistryBackupManager Class
- [ ] Subtask: Create `src/code_index_mcp/registry/backup_manager.py`
- [ ] Subtask: Implement backup creation (SQLite VACUUM into backup)
- [ ] Subtask: Implement timestamped backup naming
- [ ] Subtask: Implement backup rotation (keep 7, delete older)
- [ ] Subtask: Track last_backup_time in registry_metadata
- [ ] Subtask: Implement SQLite recovery:
  - Try loading registry.db
  - On corruption: try registry.db-backup
  - On both corrupted: call filesystem scan recovery
- [ ] Subtask: Implement registry corruption recovery from filesystem scan:
  - Scan for all `.code-indexer/index.msgpack` files
  - Extract metadata from each index file
  - Reconstruct registry from discovered indexes
  - Log warnings about potential metadata loss
- [ ] Subtask: Write unit tests for backup manager
- [ ] Subtask: Write unit tests for recovery logic
- [ ] Subtask: Verify >95% code coverage

### Task: 6.2 Implement Periodic Backup Timer
- [ ] Subtask: Add async background task for 24-hour timer
- [ ] Subtask: Implement startup check (backup if >24h since last)
- [ ] Subtask: Implement background task with asyncio.create_task
- [ ] Subtask: Handle graceful shutdown (cancel task, wait for completion)
- [ ] Subtask: Add signal handlers (SIGTERM, SIGINT) for cleanup
- [ ] Subtask: Write unit tests for periodic backup
- [ ] Subtask: Write integration tests for shutdown handling
- [ ] Subtask: Verify >95% code coverage

### Task: 6.3 Integrate Backup with Critical Operations
- [ ] Subtask: Add backup before registry_cleanup
- [ ] Subtask: Add backup before bulk migration
- [ ] Subtask: Ensure backup is non-blocking
- [ ] Subtask: Write integration tests for backup triggers
- [ ] Subtask: Verify >95% code coverage

### Task: Conductor - User Manual Verification 'Phase 6'
- [ ] Verify test coverage meets >95% requirement
- [ ] Verify all tests pass
- [ ] Verify code follows style guidelines
- [ ] Verify no linting errors
- [ ] Create checkpoint commit

## Phase 7: Testing, Documentation, and Quality Gates

### Task: 7.1 Integration Testing
- [ ] Subtask: Write end-to-end test for full indexing workflow with registry
- [ ] Subtask: Write test for migration workflow (pickle → msgpack)
- [ ] Subtask: Write test for backup and recovery workflow
- [ ] Subtask: Write test for concurrent access scenarios
- [ ] Subtask: Write test for registry corruption recovery
- [ ] Subtask: Write signal handler edge case tests:
  - SIGTERM during backup (should complete backup)
  - SIGINT during registry write (should rollback)
  - Multiple rapid signals (should handle gracefully)
- [ ] Subtask: Verify >95% code coverage

### Task: 7.2 Documentation Updates
- [ ] Subtask: Update README.md with new features
- [ ] Subtask: Document registry architecture in ARCHITECTURE.md
- [ ] Subtask: Add API documentation for new MCP tools
- [ ] Subtask: Document migration process for existing users
- [ ] Subtask: Add troubleshooting guide for registry issues
- [ ] Subtask: Document breaking changes for v2.1.0 upgrade

### Task: 7.3 Quality Gates Verification
- [ ] Subtask: Verify all tests pass
- [ ] Subtask: Verify code coverage >95%
- [ ] Subtask: Verify no linting errors
- [ ] Subtask: Verify no security vulnerabilities
- [ ] Subtask: Verify type hints complete
- [ ] Subtask: Verify docstrings complete

### Task: Conductor - User Manual Verification 'Phase 7'
- [ ] Verify test coverage meets >95% requirement
- [ ] Verify all tests pass
- [ ] Verify code follows style guidelines
- [ ] Verify no linting errors
- [ ] Create checkpoint commit

## Phase 8: Version Bump and PyPI Publish

### Task: 8.1 Version Bump to v2.1.0
- [ ] Subtask: Update pyproject.toml version from 2.0.2 to 2.1.0
- [ ] Subtask: Update CHANGELOG.md with new features and breaking changes
- [ ] Subtask: Document upgrade path from v2.0.x to v2.1.0
- [ ] Subtask: Commit version bump

### Task: 8.2 Build and Test Distribution
- [ ] Subtask: Build distribution package with uv build
- [ ] Subtask: Test package installation in clean environment
- [ ] Subtask: Test migration from v2.0.x pickle indexes
- [ ] Subtask: Verify all MCP tools work after installation

### Task: 8.3 Publish to PyPI
- [ ] Subtask: Publish package to PyPI
- [ ] Subtask: Verify installation from PyPI works
- [ ] Subtask: Tag release as v2.1.0 in git

### Task: Conductor - User Manual Verification 'Phase 8'
- [ ] Verify test coverage meets >95% requirement
- [ ] Verify all tests pass
- [ ] Verify code follows style guidelines
- [ ] Verify no linting errors
- [ ] Create checkpoint commit

## Summary

This plan implements a complete meta-registry system with:
- **8 Phases** covering all aspects from foundation to release
- **Critical persistence fixes** before any new features (Phase 2)
- **Backwards compatibility** through automatic migration (Phase 3)
- **7 new MCP tools** for registry management (Phase 5)
- **Automatic backup system** with recovery (Phase 6)
- **Comprehensive testing** >95% coverage requirement
- **Breaking changes** properly documented for v2.1.0 upgrade
