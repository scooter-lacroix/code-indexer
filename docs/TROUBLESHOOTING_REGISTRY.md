# Troubleshooting Guide: Meta-Registry System

This guide helps you diagnose and resolve common issues with the Code Indexer Meta-Registry system introduced in v2.1.0.

## Table of Contents

1. [Registry Issues](#registry-issues)
2. [Migration Issues](#migration-issues)
3. [Backup Issues](#backup-issues)
4. [Performance Issues](#performance-issues)
5. [Corruption Issues](#corruption-issues)
6. [Signal Handling Issues](#signal-handling-issues)
7. [Diagnostic Commands](#diagnostic-commands)

---

## Registry Issues

### Issue: "Registry database locked"

**Symptoms**:
- Error: "database is locked"
- Cannot access projects
- Server fails to start

**Causes**:
- Multiple server instances running
- Previous crash left lock file
- Concurrent write conflict

**Solutions**:

1. **Check for running instances**:
   ```bash
   ps aux | grep code-index-mcp
   ```

2. **Kill other instances**:
   ```bash
   killall code-index-mcp
   # Or force kill
   killall -9 code-index-mcp
   ```

3. **Remove lock files**:
   ```bash
   rm -f ~/.code-indexer/registry/projects.db-wal
   rm -f ~/.code-indexer/registry/projects.db-shm
   ```

4. **Verify WAL mode**:
   ```bash
   sqlite3 ~/.code-indexer/registry/projects.db "PRAGMA journal_mode;"
   # Should return: wal
   ```

---

### Issue: "Project not found in registry"

**Symptoms**:
- Error: "ProjectNotFoundError"
- Project exists but not registered
- Cannot access project metadata

**Causes**:
- Project indexed before registry implementation
- Registry corrupted or deleted
- Orphaned index directory

**Solutions**:

1. **Check if project exists**:
   ```bash
   ls -la <project-path>/.code-indexer/
   ```

2. **Scan for orphans**:
   ```python
   from src.code_index_mcp.registry.orphan_detector import OrphanDetector
   from src.code_index_mcp.registry.project_registry import ProjectRegistry

   registry = ProjectRegistry()
   detector = OrphanDetector(registry=registry)
   orphans = detector.detect_orphans()

   print(f"Found {len(orphans)} orphans")
   for orphan in orphans:
       print(f"  - {orphan.path}")
   ```

3. **Register orphaned project**:
   ```python
   from src.code_index_mcp.registry.registration_integrator import RegistrationIntegrator

   integrator = RegistrationIntegrator(registry=registry)
   project_info = integrator.register_after_indexing(
       project_path="/path/to/project",
       index_location="/path/to/project/.code-indexer",
       file_count=100,
       stats={},
   )
   ```

4. **Rebuild registry from filesystem**:
   ```python
   from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

   backup_manager = RegistryBackupManager()
   recovered = backup_manager.scan_and_recover(
       target_path=Path("~/.code-indexer/registry/projects.db")
   )
   print(f"Recovered {len(recovered)} projects")
   ```

---

### Issue: "Duplicate project path"

**Symptoms**:
- Error: "DuplicateProjectError"
- Cannot register project
- Project already exists in registry

**Causes**:
- Project registered multiple times
- Path case sensitivity issue
- Symlink or mount point confusion

**Solutions**:

1. **Check if project exists**:
   ```python
   from src.code_index_mcp.registry.project_registry import ProjectRegistry

   registry = ProjectRegistry()
   if registry.exists(path="/path/to/project"):
       print("Project already registered")
   ```

2. **Update existing project**:
   ```python
   updated = registry.update(
       path="/path/to/project",
       file_count=200,
       indexed_at=datetime.now(),
   )
   ```

3. **Delete and re-register**:
   ```python
   # Delete old entry
   registry.delete(path="/path/to/project")

   # Re-register
   registry.insert(
       path="/path/to/project",
       indexed_at=datetime.now(),
       file_count=200,
       config={},
       stats={},
       index_location="/path/to/project/.code-indexer",
   )
   ```

---

## Migration Issues

### Issue: "Migration fails with corrupt data"

**Symptoms**:
- Error: "Corrupt data" or "UnpicklingError"
- Migration stops midway
- Some files migrated, others not

**Causes**:
- Pickle file corrupted
- Incompatible pickle protocol
- File system error

**Solutions**:

1. **Skip corrupted files**:
   ```python
   from src.code_index_mcp.registry.index_migrator import IndexMigrator

   migrator = IndexMigrator(skip_corrupted=True)
   results = migrator.migrate_directory(
       directory=Path("~/.code-indexer/indexes")
   )

   for result in results:
       if not result.success:
           print(f"Failed: {result.source_path} - {result.error}")
   ```

2. **Manually inspect corrupted file**:
   ```bash
   # Check file type
   file ~/.code-indexer/indexes/files.pickle

   # Check file size
   ls -lh ~/.code-indexer/indexes/files.pickle

   # Try to read (may fail)
   python -c "import pickle; pickle.load(open('~/.code-indexer/indexes/files.pickle', 'rb'))"
   ```

3. **Restore from backup**:
   ```bash
   # Find backup file
   find ~/.code-indexer -name "*.pickle.backup"

   # Restore from backup
   cp ~/.code-indexer/indexes/files.pickle.backup ~/.code-indexer/indexes/files.pickle

   # Retry migration
   code-index-mcp
   ```

---

### Issue: "Migration stuck or very slow"

**Symptoms**:
- Migration takes very long time
- Progress bar doesn't move
- High CPU but no progress

**Causes**:
- Large number of files to migrate
- Slow disk I/O
- Memory pressure

**Solutions**:

1. **Check migration progress**:
   ```python
   from src.code_index_mcp.registry.startup_migration import StartupMigrationManager

   manager = StartupMigrationManager(auto_migrate=False)
   results = manager.check_legacy_indexes(scan_global=True)

   print(f"Files to migrate: {results['legacy_count']}")
   ```

2. **Migrate in batches**:
   ```python
   from src.code_index_mcp.registry.index_migrator import IndexMigrator

   migrator = IndexMigrator()

   # Migrate one directory at a time
   for pickle_file in Path("~/.code-indexer/indexes").glob("*.pickle"):
       result = migrator.migrate_file(pickle_file)
       print(f"Migrated: {pickle_file.name} - {result.success}")
   ```

3. **Increase resources**:
   ```bash
   # Close other applications
   # Increase swap if needed
   sudo swapon /swapfile

   # Run migration with nice
   nice -n 10 code-index-mcp
   ```

---

## Backup Issues

### Issue: "Backup creation fails"

**Symptoms**:
- Error: "Backup creation failed"
- No backup files created
- Backup metadata missing

**Causes**:
- Insufficient disk space
- Permission denied
- Registry database locked

**Solutions**:

1. **Check disk space**:
   ```bash
   df -h ~/.code-indexer
   ```

2. **Clean up old backups**:
   ```python
   from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

   backup_manager = RegistryBackupManager()
   cleaned = backup_manager.cleanup_old_backups()
   print(f"Cleaned {cleaned} old backups")
   ```

3. **Fix permissions**:
   ```bash
   chmod -R u+rw ~/.code-indexer/registry
   ```

4. **Manual backup**:
   ```python
   from src.code_index_mcp.registry.project_registry import ProjectRegistry
   from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

   registry = ProjectRegistry()
   backup_manager = RegistryBackupManager()

   backup_metadata = backup_manager.create_backup(registry)
   print(f"Backup created: {backup_metadata.backup_path}")
   ```

---

### Issue: "Restore from backup fails"

**Symptoms**:
- Error: "Restore failed"
- Database not recovered
- Checksum mismatch

**Causes**:
- Backup file corrupted
- Checksum mismatch
- Target file locked

**Solutions**:

1. **Verify backup integrity**:
   ```python
   from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

   backup_manager = RegistryBackupManager()
   backups = backup_manager.list_backups()

   for backup in backups:
       is_valid = backup_manager.verify_backup(backup.backup_path)
       print(f"{backup.backup_path.name}: {'Valid' if is_valid else 'Invalid'}")
   ```

2. **Try different backup**:
   ```python
   # List all backups
   backups = backup_manager.list_backups()
   for backup in backups:
       print(f"{backup.timestamp}: {backup.backup_path}")

   # Restore specific backup
   restored = backup_manager.restore_backup(
       backup_path=backups[-2].backup_path,  # Second most recent
       target_path=Path("~/.code-indexer/registry/projects.db")
   )
   ```

3. **Recover from filesystem**:
   ```python
   recovered = backup_manager.scan_and_recover(
       target_path=Path("~/.code-indexer/registry/projects.db")
   )
   print(f"Recovered {len(recovered)} projects from filesystem")
   ```

---

## Performance Issues

### Issue: "Slow project lookups"

**Symptoms**:
- Registry queries take >1 second
- Lag when switching projects
- High CPU during queries

**Causes**:
- Missing indexes
- Large registry
- Fragmented database

**Solutions**:

1. **Check indexes**:
   ```bash
   sqlite3 ~/.code-indexer/registry/projects.db ".schema"
   ```

2. **Rebuild indexes**:
   ```bash
   sqlite3 ~/.code-indexer/registry/projects.db "REINDEX;"
   ```

3. **Vacuum database**:
   ```bash
   sqlite3 ~/.code-indexer/registry/projects.db "VACUUM;"
   ```

4. **Analyze query performance**:
   ```bash
   sqlite3 ~/.code-indexer/registry/projects.db "EXPLAIN QUERY PLAN SELECT * FROM projects WHERE path = '/test';"
   ```

---

### Issue: "High memory usage"

**Symptoms**:
- Server uses >500MB RAM
- Memory grows over time
- Out of memory errors

**Causes**:
- Large registry cached
- Memory leak
- Too many concurrent operations

**Solutions**:

1. **Check memory usage**:
   ```python
   import psutil
   import os

   process = psutil.Process(os.getpid())
   print(f"Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
   ```

2. **Clear cache**:
   ```python
   from src.code_index_mcp.registry.project_registry import ProjectRegistry

   registry = ProjectRegistry()
   # Close and reopen to clear cache
   registry.close()
   registry = ProjectRegistry()
   ```

3. **Limit concurrent operations**:
   ```python
   # Reduce worker threads
   # In your configuration
   MAX_WORKERS = 2  # Reduce from default
   ```

---

## Corruption Issues

### Issue: "Registry database corrupted"

**Symptoms**:
- Error: "database disk image is malformed"
- Cannot open registry
- Queries return errors

**Causes**:
- Disk failure
- Power loss during write
- File system corruption

**Solutions**:

1. **Run integrity check**:
   ```bash
   sqlite3 ~/.code-indexer/registry/projects.db "PRAGMA integrity_check;"
   ```

2. **Restore from backup**:
   ```python
   from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

   backup_manager = RegistryBackupManager()
   restored = backup_manager.restore_latest_backup(
       target_path=Path("~/.code-indexer/registry/projects.db")
   )
   print(f"Restore {'succeeded' if restored else 'failed'}")
   ```

3. **Recover from filesystem**:
   ```python
   # If no backup available
   recovered = backup_manager.scan_and_recover(
       target_path=Path("~/.code-indexer/registry/projects.db")
   )
   print(f"Recovered {len(recovered)} projects")
   ```

4. **Dump and reload**:
   ```bash
   # Dump data
   sqlite3 ~/.code-indexer/registry/projects.db ".dump" > dump.sql

   # Create new database
   sqlite3 projects_new.db < dump.sql

   # Replace old database
   mv projects_new.db ~/.code-indexer/registry/projects.db
   ```

---

### Issue: "Index file corrupted"

**Symptoms**:
- Error: "Invalid MessagePack data"
- Cannot read index
- Search fails for specific project

**Causes**:
- Incomplete write
- Disk corruption
- File modified externally

**Solutions**:

1. **Verify file format**:
   ```bash
   file <project>/.code-indexer/files.msgpack
   # Should show: MessagePack data
   ```

2. **Restore from backup**:
   ```bash
   # Find backup
   ls -la <project>/.code-indexer/backups/

   # Restore from backup
   cp <project>/.code-indexer/backups/files_20250101.msgpack \
      <project>/.code-indexer/files.msgpack
   ```

3. **Rebuild index**:
   ```python
   # Re-index the project
   from src.code_index_mcp.incremental_indexer import IncrementalIndexer

   indexer = IncrementalIndexer(project_path="/path/to/project")
   indexer.reindex_full()
   ```

---

## Signal Handling Issues

### Issue: "SIGTERM during backup causes data loss"

**Symptoms**:
- Backup incomplete after SIGTERM
- Data missing from registry
- Inconsistent state

**Causes**:
- Backup interrupted by signal
- Shutdown before backup completed

**Solutions**:

1. **Wait for backup to complete**:
   ```python
   import asyncio
   from src.code_index_mcp.registry.backup_scheduler import BackupScheduler

   async def graceful_shutdown():
       scheduler = BackupScheduler()
       # Wait for in-progress backup
       await scheduler.shutdown()

   asyncio.run(graceful_shutdown())
   ```

2. **Verify backup after shutdown**:
   ```python
   from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

   backup_manager = RegistryBackupManager()
   backups = backup_manager.list_backups()

   if backups:
       latest = backups[-1]
       is_valid = backup_manager.verify_backup(latest.backup_path)
       print(f"Latest backup valid: {is_valid}")
   ```

3. **Recover if needed**:
   ```python
   # If backup incomplete, restore from previous
   restored = backup_manager.restore_backup(
       backup_path=backups[-2].backup_path,
       target_path=Path("~/.code-indexer/registry/projects.db")
   )
   ```

---

### Issue: "SIGINT during registry write"

**Symptoms**:
- Registry in inconsistent state
- Transaction not rolled back
- Data partially written

**Causes**:
- Write operation interrupted
- Transaction not completed
- Rollback failed

**Solutions**:

1. **Check registry state**:
   ```bash
   sqlite3 ~/.code-indexer/registry/projects.db "PRAGMA integrity_check;"
   ```

2. **Force rollback**:
   ```python
   from src.code_index_mcp.registry.project_registry import ProjectRegistry

   registry = ProjectRegistry()
   # Rollback any pending transaction
   registry._conn.rollback()
   registry.close()
   ```

3. **Restore from backup**:
   ```python
   from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

   backup_manager = RegistryBackupManager()
   restored = backup_manager.restore_latest_backup(
       target_path=Path("~/.code-indexer/registry/projects.db")
   )
   ```

---

## Diagnostic Commands

### Registry Diagnostics

```python
from src.code_index_mcp.registry.project_registry import ProjectRegistry

registry = ProjectRegistry()

# Check registry health
print(f"Total projects: {registry.count()}")
print(f"Registry version: {registry.get_metadata('version')}")

# List all projects
projects = registry.list_all()
for project in projects:
    print(f"  - {project.path}: {project.file_count} files")
```

### Migration Diagnostics

```python
from src.code_index_mcp.registry.startup_migration import StartupMigrationManager

manager = StartupMigrationManager(auto_migrate=False)

# Check for legacy indexes
results = manager.check_legacy_indexes(scan_global=True)
print(f"Has legacy: {results['has_legacy']}")
print(f"Legacy count: {results['legacy_count']}")

# List legacy files
for file_path in results['legacy_files']:
    print(f"  - {file_path}")
```

### Backup Diagnostics

```python
from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

backup_manager = RegistryBackupManager()

# List backups
backups = backup_manager.list_backups()
print(f"Total backups: {len(backups)}")

for backup in backups:
    is_valid = backup_manager.verify_backup(backup.backup_path)
    print(f"  - {backup.timestamp}: {'Valid' if is_valid else 'Invalid'}")
```

### Performance Diagnostics

```python
import sqlite3
import time

conn = sqlite3.connect("~/.code-indexer/registry/projects.db")

# Benchmark queries
start = time.time()
cursor = conn.execute("SELECT * FROM projects")
projects = cursor.fetchall()
end = time.time()

print(f"Query time: {end - start:.3f}s")
print(f"Projects retrieved: {len(projects)}")
```

### System Diagnostics

```bash
# Check disk space
df -h ~/.code-indexer

# Check file counts
find ~/.code-indexer -type f | wc -l

# Check for large files
find ~/.code-indexer -type f -size +10M -exec ls -lh {} \;

# Check database size
ls -lh ~/.code-indexer/registry/projects.db

# Check backup size
du -sh ~/.code-indexer/registry/backups/*
```

---

## Getting Additional Help

If you cannot resolve your issue:

1. **Enable debug logging**:
   ```bash
   export CODE_INDEX_LOG_LEVEL=DEBUG
   code-index-mcp
   ```

2. **Collect diagnostic information**:
   ```bash
   code-index-mcp --diagnose > diagnostics.txt
   ```

3. **Check logs**:
   ```bash
   tail -f ~/.code-indexer/logs/server.log
   ```

4. **Report issue**:
   - GitHub: https://github.com/scooter-lacroix/code-indexer/issues
   - Include diagnostic output
   - Describe steps to reproduce
   - Include error messages

5. **Community forum**:
   - GitHub Discussions: https://github.com/scooter-lacroix/code-indexer/discussions
   - Ask for help from community

---

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Database locked | `killall code-index-mcp` |
| Project not found | Run `scan_and_recover()` |
| Migration fails | Use `skip_corrupted=True` |
| Backup fails | Check disk space and permissions |
| Restore fails | Verify checksum, try older backup |
| Slow queries | Run `VACUUM` and `REINDEX` |
| Corruption | Restore from backup or `scan_and_recover()` |
| Signal issues | Wait for operation to complete |

For more detailed information, see the [Architecture Documentation](ARCHITECTURE.md) or [Migration Guide](MIGRATION_GUIDE_v2.1.md).
