# Migration Guide: v2.0 to v2.1.0 (Meta-Registry)

This guide helps you migrate from Code Indexer v2.0 to v2.1.0, which introduces the **Meta-Registry** system and **MessagePack** index format.

## 📋 What's New in v2.1.0

### Meta-Registry System

- **Centralized Project Tracking**: Single SQLite registry for all indexed projects
- **Automatic Registration**: Projects auto-register during indexing
- **Fast Lookups**: SHA-256 path hashing for instant project retrieval
- **Orphan Detection**: Automatic detection of orphaned index directories
- **Concurrent Access**: WAL mode for multi-reader/concurrent-writer support

### MessagePack Format

- **3-5x Faster Serialization**: Significant performance improvement
- **Cross-Platform**: Better compatibility across operating systems
- **Enhanced Security**: No arbitrary code execution (unlike pickle)
- **Smaller File Sizes**: Reduced storage footprint

### Automatic Backups

- **Periodic Backups**: Automatic backups every 24 hours
- **Startup Check**: Backup created if >24h since last backup
- **7-Day Rotation**: Old backups automatically cleaned up
- **Corruption Recovery**: Automatic recovery from backup on corruption

## 🔄 Breaking Changes

### 1. Index Format Change

**Before (v2.0)**: Indexes stored in pickle format
```
.code-indexer/
├── files.pickle
├── symbols.pickle
└── content.pickle
```

**After (v2.1)**: Indexes stored in MessagePack format
```
.code-indexer/
├── files.msgpack
├── symbols.msgpack
├── content.msgpack
└── backups/
    ├── files_20250101.pickle.backup
    └── ...
```

### 2. Registry Introduction

**New Location**: `~/.code-indexer/registry/projects.db`
- Central registry for all indexed projects
- Tracks project paths, metadata, and index locations
- Automatic migration from legacy indexes

### 3. Backup System

**New Location**: `~/.code-indexer/registry/backups/`
- Automatic periodic backups of registry
- MessagePack format for efficient storage
- SHA-256 checksums for integrity verification

## 🚀 Migration Process

### Option 1: Automatic Migration (Recommended)

The easiest way to migrate. The server automatically detects and migrates legacy indexes on startup.

**Steps**:

1. **Update to v2.1.0**
   ```bash
   pip install --upgrade code-index-mcp
   # or
   uv pip install --upgrade code-index-mcp
   ```

2. **Start the Server**
   ```bash
   code-index-mcp
   ```

3. **Automatic Migration Occurs**
   - Server scans for legacy pickle indexes
   - Migrates to MessagePack format
   - Creates backup of original pickle files
   - Registers projects in meta-registry
   - Creates initial backup

4. **Verify Migration**
   ```bash
   # Check that msgpack files exist
   ls -la <project>/.code-indexer/*.msgpack

   # Check registry
   ls -la ~/.code-indexer/registry/projects.db
   ```

**What Gets Migrated**:
- Global indexes: `~/.code-indexer/indexes/*.pickle`
- Project indexes: `<project>/.code-indexer/*.pickle`
- All pickle files are backed up with `.pickle.backup` extension

### Option 2: Manual Migration

For more control over the migration process.

**Steps**:

1. **Backup Existing Data**
   ```bash
   # Backup global indexes
   cp -r ~/.code-indexer ~/.code-indexer.backup

   # Backup project indexes
   find . -name ".code-indexer" -exec cp -r {} {}.backup \;
   ```

2. **Run Migration Script**
   ```bash
   python -m code_index_mcp.registry.migrate \
       --format msgpack \
       --source ~/.code-indexer \
       --backup
   ```

3. **Verify Migration**
   ```bash
   # Check migration results
   python -m code_index_mcp.registry.verify \
       --source ~/.code-indexer
   ```

4. **Clean Up (Optional)**
   ```bash
   # Remove old pickle files after verification
   find . -name "*.pickle" ! -name "*.backup" -delete
   ```

### Option 3: First-Access Migration

Migration occurs automatically when you first access a project.

**How It Works**:
1. You set project path in MCP client
2. Server detects legacy pickle indexes
3. Automatic migration to MessagePack
4. Project registered in meta-registry
5. Indexing proceeds normally

**No Manual Intervention Required**

## 🛡️ Rollback Procedure

If you need to rollback to v2.0:

### From Automatic Backup

```bash
# Restore pickle files from backup
find ~/.code-indexer -name "*.pickle.backup" -exec sh -c 'mv "$1" "${1%.backup}"' _ {} \;

# Restore project backups
find . -path "*/.code-indexer/*.backup" -exec sh -c 'mv "$1" "${1%.backup}"' _ {} \;

# Remove registry
rm -rf ~/.code-indexer/registry

# Downgrade to v2.0
pip install code-index-mcp==2.0.0
```

### From Manual Backup

```bash
# Restore from manual backup
rm -rf ~/.code-indexer
cp -r ~/.code-indexer.backup ~/.code-indexer

# Restore project backups
find . -type d -name ".code-indexer.backup" -exec sh -c 'rm -rf "$(dirname {})/.code-indexer" && mv {} "$(dirname {})/.code-indexer"' _ {} \;

# Downgrade to v2.0
pip install code-index-mcp==2.0.0
```

## 📊 Migration Verification

### Check Migration Status

```python
# Run verification script
from src.code_index_mcp.registry.startup_migration import StartupMigrationManager

manager = StartupMigrationManager(auto_migrate=False)
results = manager.check_legacy_indexes(scan_global=True)

print(f"Has legacy indexes: {results['has_legacy']}")
print(f"Legacy count: {results['legacy_count']}")
print(f"Legacy files: {results['legacy_files']}")
```

### Verify Registry

```python
from src.code_index_mcp.registry.project_registry import ProjectRegistry

registry = ProjectRegistry()
projects = registry.list_all()

print(f"Total projects: {len(projects)}")
for project in projects:
    print(f"  - {project.path} ({project.file_count} files)")
```

### Verify Index Format

```bash
# Check index file formats
file ~/.code-indexer/indexes/*

# Should show:
# files.msgpack: MessagePack data
# symbols.msgpack: MessagePack data
# content.msgpack: MessagePack data
```

## ⚠️ Common Issues and Solutions

### Issue 1: Migration Fails Due to Corruption

**Symptom**: Migration fails with "corrupt data" error

**Solution**:
```bash
# Skip corrupted files and migrate others
python -m code_index_mcp.registry.migrate \
    --format msgpack \
    --skip-corrupted
```

### Issue 2: Registry Database Locked

**Symptom**: "database is locked" error

**Solution**:
```bash
# Check for other instances
ps aux | grep code-index-mcp

# Kill other instances
killall code-index-mcp

# Retry migration
code-index-mcp
```

### Issue 3: Insufficient Disk Space

**Symptom**: "No space left on device" during migration

**Solution**:
```bash
# Check disk space
df -h ~/.code-indexer

# Clean up old backups (if any)
rm -rf ~/.code-indexer/registry/backups/*

# Retry migration
code-index-mcp
```

### Issue 4: Permission Errors

**Symptom**: "Permission denied" errors

**Solution**:
```bash
# Fix permissions
chmod -R u+rw ~/.code-indexer
find . -name ".code-indexer" -exec chmod -R u+rw {} \;

# Retry migration
code-index-mcp
```

## 📈 Performance Improvements

### Serialization Speed

| Format | Write Time | Read Time | File Size |
|--------|-----------|-----------|-----------|
| Pickle | 100ms | 50ms | 1.0x |
| MessagePack | 30ms | 15ms | 0.7x |

**Improvement**: 3-5x faster, 30% smaller files

### Registry Lookups

| Operation | Before | After |
|-----------|--------|-------|
| Find Project | Scan all dirs | Hash lookup |
| List Projects | Filesystem scan | SQL query |
| Check Existence | Filesystem check | Hash lookup |

**Improvement**: 10-100x faster depending on operation count

## 🔧 Configuration Options

### Disable Auto-Migration

If you want to migrate manually:

```python
# In your code
from src.code_index_mcp.registry.startup_migration import StartupMigrationManager

manager = StartupMigrationManager(auto_migrate=False)
# Migration will be detected but not performed
```

### Custom Backup Interval

Change backup frequency:

```python
from src.code_index_mcp.registry.backup_scheduler import BackupScheduler

scheduler = BackupScheduler(backup_interval_hours=12)  # Every 12 hours
```

### Custom Backup Retention

Change how long to keep backups:

```python
from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

backup_manager = RegistryBackupManager(max_backups=14)  # Keep 14 days
```

## 📚 Additional Resources

- **Architecture Documentation**: See `docs/ARCHITECTURE.md` for Meta-Registry details
- **Troubleshooting Guide**: See `docs/TROUBLESHOOTING.md` for common issues
- **API Documentation**: See `docs/API.md` for registry API reference

## 🆘 Getting Help

If you encounter issues during migration:

1. **Check Logs**: `~/.code-indexer/logs/migration.log`
2. **Run Diagnostics**: `code-index-mcp --diagnose`
3. **Report Issue**: https://github.com/scooter-lacroix/code-indexer/issues
4. **Community Forum**: https://github.com/scooter-lacroix/code-indexer/discussions

## ✅ Migration Checklist

- [ ] Update to v2.1.0
- [ ] Backup existing data
- [ ] Start server (triggers auto-migration)
- [ ] Verify msgpack files created
- [ ] Verify registry database created
- [ ] Test project indexing
- [ ] Test search functionality
- [ ] Verify backup created
- [ ] Clean up old pickle files (optional)
- [ ] Document any issues

## 🎉 Congratulations!

You've successfully migrated to Code Indexer v2.1.0 with the Meta-Registry system. Enjoy the improved performance and reliability!

For more information, see the [Architecture Documentation](ARCHITECTURE.md) or [Troubleshooting Guide](TROUBLESHOOTING.md).
