# Specification: Self-Indexing Meta-Registry with Persistence Fixes

**Track ID:** meta-registry_20250101
**Type:** Feature
**Status:** New
**Target Version:** v2.1.0 (breaking changes)

## Overview

Implement a global meta-registry system that tracks all indexed projects across the code-indexer installation. This addresses critical persistence issues identified in v2.0.1 while enabling efficient project management, rapid re-indexing, and registry maintenance operations.

**Key Drivers:**
- Critical persistence fixes required (pickle format, flush issues, atomic saves)
- Need for centralized project tracking across multiple codebases
- Backwards compatibility for existing indexes (pickle → MessagePack migration)
- Operational maintenance (health checks, cleanup)

## Functional Requirements

### 1. Meta-Registry Storage

**FR-1.1:** Global registry SHALL be stored at `~/.code-indexer/registry.db`
- Isolated from project directories (survives `git clean`)
- SQLite database with JSON columns for flexible configuration storage
- Automatic directory creation on first use

**FR-1.2:** Registry schema SHALL include:
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    path_hash TEXT UNIQUE NOT NULL,  -- SHA-256 of absolute path
    indexed_at TIMESTAMP NOT NULL,
    file_count INTEGER NOT NULL,
    config JSON NOT NULL,              -- Backend type, ignored patterns, settings
    stats JSON NOT NULL,               -- Index size, last reindex, health status
    index_location TEXT NOT NULL       -- Path to .code-indexer/ directory
);

CREATE TABLE registry_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**FR-1.3:** Registry metadata SHALL include:
- `schema_version`: For future migrations
- `last_backup_time`: For periodic backup tracking
- `created_at`, `updated_at`: Audit timestamps

### 2. Auto-Registration on Index Completion

**FR-2.1:** When `manage_project` completes successfully, the project SHALL be automatically registered:
- Insert/update record in meta-registry
- Compute SHA-256 hash of absolute project path
- Store configuration snapshot (backend, ignore patterns, settings)
- Calculate and store index statistics (file count, indexed size, timestamp)

**FR-2.2:** Registration SHALL be resilient to partial failures
- MessagePack index saved FIRST using atomic temp+rename
- Registry update in SQLite transaction SECOND
- On registration failure: index remains but is "orphaned" (safe)
- On startup: detect orphaned indexes and offer to register them
- Never leave registry pointing to missing/corrupted index

### 3. Index Migration (Pickle → MessagePack)

**FR-3.1:** On server startup, detect legacy pickle indexes
- Scan `.code_indexer_data/<hash>/file_index.pickle` files
- Offer to migrate to MessagePack format

**FR-3.2:** Migration process:
- Load pickle index
- Convert to MessagePack format
- Save to `.code-indexer/index.msgpack`
- Update registry with new index location
- Keep `.code_indexer_data/` as backup (not deleted automatically)
- Verify migration integrity

**FR-3.3:** Migration SHALL be idempotent and reversible
- Skip already-migrated indexes
- Rollback on failure

### 4. Quick Reindex All Projects

**FR-4.1:** MCP tool `reindex_all_projects()` SHALL:
- Iterate through all registered projects
- Check for file changes (mtime, hash comparison)
- Reindex only changed projects
- Update registry with new timestamps and statistics

**FR-4.2:** Reindex operation SHALL:
- Support `--force` flag to bypass change detection
- Support `--dry-run` flag to preview changes
- Provide progress reporting per project
- Handle project errors gracefully (continue with next project)

### 5. Health Check

**FR-5.1:** MCP tool `registry_health_check()` SHALL verify:
- Project paths exist and are accessible
- Index files exist at registered locations
- Index integrity (valid MessagePack, file count matches)
- Configuration consistency

**FR-5.2:** Health check SHALL return:
- Overall registry status (healthy/warning/critical)
- Per-project health details
- Recommended actions for unhealthy projects

### 6. Project Cleanup

**FR-6.1:** MCP tool `registry_cleanup()` SHALL:
- Remove projects with missing paths
- Remove projects with corrupted indices
- Update registry accordingly
- Create backup before cleanup

**FR-6.2:** Cleanup SHALL require confirmation unless `--force` flag is provided

## Non-Functional Requirements

### NFR-1: Persistence Format

**NFR-1.1:** Meta-registry SHALL use SQLite with JSON columns
- Structured querying support
- Atomic transactions
- JSON flexibility for evolving schema

**NFR-1.2:** Per-project indexes SHALL use MessagePack format
- Compact binary serialization
- Faster than pickle
- Safer (no arbitrary code execution)

**NFR-1.3:** Legacy pickle support for migration only
- No new pickle files created
- Migration path from pickle to MessagePack

### NFR-2: Data Integrity

**NFR-2.1:** All database writes SHALL be atomic
- Use SQLite transactions for registry
- Write to temp file, then rename for MessagePack

**NFR-2.2:** SQLite SHALL operate with full durability:
```sql
PRAGMA synchronous = FULL;
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
```

**NFR-2.3:** Explicit flush before shutdown
- Registry: Commit all SQLite transactions, close connection cleanly
- DAL backends: Call flush() before close() to ensure embedded writes
- Both: Handle SIGTERM/SIGINT gracefully with cleanup handlers

### NFR-3: Performance

**NFR-3.1:** Registry operations SHALL complete in:
- Registration: <100ms per project (registry update only, not indexing)
- Health check: <1 second for 100 projects (stat checks, no reindexing)
- Reindex all: <5 seconds overhead (iteration + change detection, excludes actual re-indexing time)

**NFR-3.2:** Registry SHALL support >1000 projects without performance degradation

### NFR-4: Backwards Compatibility

**NFR-4.1:** Existing pickle indexes MUST be migratable
- No data loss during migration
- Verification after migration

**NFR-4.2:** v2.1.0 MUST read both pickle and MessagePack indexes
- Prefer MessagePack, fall back to pickle
- Migrate on first access

### NFR-5: Concurrent Access

**NFR-5.1:** Registry SHALL handle concurrent writes safely
- SQLite WAL mode enables concurrent reads
- Write locks automatically handled by SQLite
- File-based MessagePack writes use temp+rename (atomic)

**NFR-5.2:** Race condition handling
- If two processes index same project simultaneously:
  - Both write index files atomically (last wins)
  - Both attempt registry update (last wins, no corruption)
  - No data loss, deterministic final state

### NFR-6: Registry Recovery and Backup

**NFR-6.1:** Registry SHALL be backed up automatically
- **Before operations**: cleanup, bulk migrations
- **Periodic**: Every 24 hours while server is running
  - Check on startup: if last backup >24h old, backup immediately
  - Background timer: trigger backup every 24 hours
  - Rotation: Keep last 7 daily backups, delete older
- **Backup naming**: `registry.db-backup-YYYYMMDD-HHMMSS`
- **Cleanup**: Delete backups older than 7 days on each new backup

**NFR-6.2:** If registry.db is corrupted:
- Attempt SQLite recovery using latest `.db-backup`
- If backup also corrupted: rebuild from filesystem scan
  - Scan all `.code-indexer/index.msgpack` files
  - Reconstruct registry from index metadata
  - Log warning about potential metadata loss

## Acceptance Criteria

### AC-1: Meta-Registry Created
- [ ] `~/.code-indexer/registry.db` exists after first project index
- [ ] Schema matches FR-1.2 specification
- [ ] SHA-256 path hashing implemented correctly
- [ ] registry_metadata table populated

### AC-2: Auto-Registration Working
- [ ] Projects automatically registered after `manage_project`
- [ ] Registry contains correct configuration snapshot
- [ ] Registration resilient to partial failures (FR-2.2)
- [ ] Orphaned indexes detected on startup

### AC-3: Migration from Pickle
- [ ] Legacy pickle indexes detected on startup
- [ ] Migration converts to MessagePack successfully
- [ ] New `.code-indexer/index.msgpack` location used
- [ ] Old `.code_indexer_data/` preserved as backup
- [ ] Migrated indexes load correctly
- [ ] Migration is idempotent

### AC-4: Quick Reindex
- [ ] `reindex_all_projects()` iterates all registered projects
- [ ] Changed projects detected correctly
- [ ] Only changed projects are reindexed (unless --force)
- [ ] Registry updated with new timestamps
- [ ] Dry-run mode works correctly

### AC-5: Health Check
- [ ] `registry_health_check()` validates project paths
- [ ] Missing paths detected and reported
- [ ] Corrupted indices detected and reported
- [ ] Overall status computed correctly

### AC-6: Cleanup
- [ ] `registry_cleanup()` removes invalid projects
- [ ] Requires confirmation (unless --force)
- [ ] Backup created before cleanup

### AC-7: Persistence Fixes
- [ ] No new pickle files created
- [ ] SQLite uses FULL synchronous mode + WAL
- [ ] Explicit flush before shutdown (registry + DAL)
- [ ] Atomic saves using temp+rename pattern

### AC-8: Concurrent Access
- [ ] SQLite WAL mode enabled
- [ ] Multiple processes can read registry simultaneously
- [ ] Race conditions handled deterministically

### AC-9: Registry Recovery and Backup
- [ ] Registry backup created before critical operations
- [ ] Automatic periodic backup every 24 hours
- [ ] Backup on startup if last backup >24h old
- [ ] Backup rotation keeps last 7 daily backups
- [ ] Older backups automatically deleted
- [ ] Manual backup tool (TMETA-07) works correctly
- [ ] Corrupted registry can be recovered from latest backup
- [ ] Corrupted registry can be rebuilt from filesystem scan

## MCP Tools

### TMETA-01: `get_registry_status()`
Get overall registry status and statistics.

**Returns:**
```json
{
  "total_projects": 42,
  "healthy_projects": 40,
  "warning_projects": 1,
  "critical_projects": 1,
  "last_backup": "2025-01-01T12:00:00Z",
  "registry_size_bytes": 12345,
  "total_indexed_files": 150000
}
```

### TMETA-02: `reindex_all_projects(force: bool = False, dry_run: bool = False)`
Reindex all registered projects.

**Parameters:**
- `force`: Bypass change detection and reindex all
- `dry_run`: Preview changes without executing

**Returns:**
```json
{
  "total_projects": 42,
  "changed_projects": 5,
  "reindexed_projects": 5,
  "skipped_projects": 37,
  "failed_projects": [],
  "duration_seconds": 45.2
}
```

### TMETA-03: `registry_health_check()`
Verify integrity of all registered projects.

**Returns:**
```json
{
  "overall_status": "warning",
  "projects": [
    {
      "path": "/path/to/project",
      "status": "healthy",
      "issues": []
    },
    {
      "path": "/path/to/missing",
      "status": "critical",
      "issues": ["Path does not exist"]
    }
  ]
}
```

### TMETA-04: `registry_cleanup(force: bool = False)`
Remove invalid projects from registry.

**Parameters:**
- `force`: Skip confirmation prompt

### TMETA-05: `migrate_legacy_indexes()`
Manually trigger migration from pickle to MessagePack.

### TMETA-06: `detect_orphaned_indexes()`
Scan filesystem for `.code-indexer/index.msgpack` files not in registry.

**Returns:**
```json
{
  "orphan_count": 2,
  "orphans": [
    {
      "path": "/path/to/orphan/.code-indexer/index.msgpack",
      "file_count": 1000,
      "recommendation": "register"
    }
  ]
}
```

### TMETA-07: `backup_registry()`
Manually trigger immediate registry backup.

**Returns:**
```json
{
  "backup_path": "/home/user/.code-indexer/registry.db-backup-20250101-120000",
  "size_bytes": 12345,
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## Out of Scope

The following features are explicitly deferred to v2.2.0+:
- Cross-project search (querying multiple indexes simultaneously)
- Registry export/import (backup/portability beyond current backup system)
- Dependency tracking between projects
- Distributed registry synchronization

## Implementation Notes

### Directory Structure Migration

**v2.0.x (old):** `.code_indexer_data/<hash>/file_index.pickle`

**v2.1.0 (new):** `.code-indexer/index.msgpack`

Migration process:
- Create `.code-indexer/` directory if not exists
- Convert pickle → MessagePack
- Save to new location
- Keep `.code_indexer_data/` as backup (not deleted automatically)
- Registry points to new `.code-indexer/index.msgpack` location

### File Structure
```
~/.code-indexer/
├── registry.db                           # Meta-registry (SQLite)
├── registry.db-backup-YYYYMMDD-HHMMSS   # Timestamped backups (keep 7)
├── registry.db-backup                    # Latest backup symlink
└── metadata/                             # Internal metadata
    └── backup_state.json                 # Last backup time tracking

<project>/.code-indexer/
├── index.msgpack                         # NEW: MessagePack file index
├── index.msgpack.backup                  # Backup during migration
├── index.msgpack.tmp                     # Atomic write temp file
└── .code_indexer_data/                   # OLD: Preserved as backup
    └── <hash>/
        └── file_index.pickle             # Legacy (will be migrated)
```

### Key Classes
- `ProjectRegistry`: Manages SQLite registry operations
- `IndexMigrator`: Handles pickle → MessagePack conversion
- `RegistryHealthChecker`: Validates registry integrity
- `MessagePackIndexSerializer`: MessagePack serialization/deserialization with format detection
- `OrphanDetector`: Finds indexes not in registry
- `RegistryBackupManager`: Handles automatic periodic backups, rotation, and recovery

### Dependencies
- `msgpack`: Binary serialization
- `sqlite3`: Registry storage (standard library)
- `hashlib`: SHA-256 path hashing (standard library)
- `signal`: SIGTERM/SIGINT handlers (standard library)
- `asyncio`: Periodic backup background task (standard library)

## Breaking Changes for v2.1.0

1. **Index Format**: Pickle → MessagePack (requires migration)
2. **Directory Structure**: `.code_indexer_data/` → `.code-indexer/`
3. **Global Registry**: New `~/.code-indexer/registry.db` created
4. **Storage Configuration**: New registry backend (in addition to existing DAL)
5. **MCP Tools**: 7 new MCP tools added

## Upgrade Path from v2.0.x

1. Install v2.1.0
2. Server startup detects pickle indexes
3. Automatic migration offered
4. Migration runs (preserves original pickle as backup)
5. Registry auto-populated from migrated indexes
6. Old pickle files preserved in `.code_indexer_data/`
