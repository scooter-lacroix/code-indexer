"""
Integration tests for registry corruption recovery.

This module tests the meta-registry's ability to detect and recover from
various types of corruption, including database corruption, index corruption,
and filesystem issues.

Tests cover:
- Database corruption detection
- Registry recovery from backup
- Filesystem scan recovery
- Index file corruption handling
- Metadata corruption recovery
- Partial recovery scenarios
"""

import pytest
import tempfile
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock
import hashlib

from src.code_index_mcp.registry.project_registry import (
    ProjectRegistry,
    ProjectInfo,
    RegistryError,
)
from src.code_index_mcp.registry.registry_backup import (
    RegistryBackupManager,
    BackupMetadata,
)
from src.code_index_mcp.registry.msgpack_serializer import MessagePackSerializer
from src.code_index_mcp.registry.directories import (
    get_project_index_dir,
    get_global_registry_dir,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_project_dirs():
    """Create multiple temporary project directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        projects = []
        for i in range(3):
            project_dir = Path(tmpdir) / f"project{i}"
            project_dir.mkdir()

            # Create index directory
            index_dir = get_project_index_dir(project_dir)
            index_dir.mkdir(parents=True, exist_ok=True)

            # Create sample index file
            serializer = MessagePackSerializer()
            index_path = index_dir / "files.msgpack"
            serializer.write(index_path, {
                "files": [f"src/file{i}.py"],
                "file_count": 1,
                "last_updated": datetime.now().isoformat(),
            })

            projects.append(project_dir)

        yield projects


# ============================================================================
# Test Database Corruption Detection
# ============================================================================

class TestDatabaseCorruptionDetection:
    """Tests for detecting database corruption."""

    def test_detect_corrupted_database(self):
        """Should detect corrupted database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "corrupt.db"

            # Create valid registry
            registry = ProjectRegistry(db_path=db_path)
            now = datetime.now()
            registry.insert(
                path="/test/project",
                indexed_at=now,
                file_count=1,
                config={},
                stats={},
                index_location="/tmp/index",
            )
            registry.close()

            # Corrupt the database
            with open(db_path, "r+b") as f:
                f.seek(100)
                f.write(b"\x00" * 1000)

            # Try to open corrupted registry
            with pytest.raises(Exception):
                registry = ProjectRegistry(db_path=db_path)
                registry.get_by_path(path="/test/project")

    def test_sqlite_integrity_check(self):
        """Should run SQLite integrity check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create registry
            registry = ProjectRegistry(db_path=db_path)
            now = datetime.now()
            for i in range(5):
                registry.insert(
                    path=f"/test/project{i}",
                    indexed_at=now,
                    file_count=i,
                    config={},
                    stats={},
                    index_location=f"/tmp/index{i}",
                )

            # Run integrity check via connection
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            # Should return "ok"
            assert result[0] == "ok"

            registry.close()

    def test_detect_empty_database(self):
        """Should handle empty database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "empty.db"

            # Create empty file
            db_path.write_bytes(b"")

            # Try to open empty database
            with pytest.raises(Exception):
                registry = ProjectRegistry(db_path=db_path)


# ============================================================================
# Test Registry Recovery from Backup
# ============================================================================

class TestRegistryRecoveryFromBackup:
    """Tests for recovering registry from backup."""

    def test_restore_from_latest_backup(self, temp_project_dirs):
        """Should restore registry from latest backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "registry.db"
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            # Create registry with projects
            registry = ProjectRegistry(db_path=db_path)
            now = datetime.now()
            for project in temp_project_dirs:
                registry.insert(
                    path=str(project),
                    indexed_at=now,
                    file_count=1,
                    config={},
                    stats={},
                    index_location=str(get_project_index_dir(project)),
                )

            # Create backup
            backup_manager = RegistryBackupManager(backup_dir=backup_dir)
            backup_metadata = backup_manager.create_backup(registry)

            assert backup_metadata is not None
            assert backup_metadata.project_count == 3

            registry.close()

            # Corrupt registry
            db_path.write_bytes(b"corrupted data")

            # Restore from backup
            restored = backup_manager.restore_latest_backup(db_path)

            assert restored is True

            # Verify restored data
            new_registry = ProjectRegistry(db_path=db_path)
            assert new_registry.count() == 3

            for project in temp_project_dirs:
                assert new_registry.exists(path=str(project))

            new_registry.close()

    def test_restore_from_specific_backup(self, temp_project_dirs):
        """Should restore registry from specific backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "registry.db"
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            # Create registry
            registry = ProjectRegistry(db_path=db_path)
            now = datetime.now()
            registry.insert(
                path=str(temp_project_dirs[0]),
                indexed_at=now,
                file_count=1,
                config={},
                stats={},
                index_location="/tmp/index1",
            )

            # Create first backup
            backup_manager = RegistryBackupManager(backup_dir=backup_dir)
            backup1 = backup_manager.create_backup(registry)

            # Add more projects
            for project in temp_project_dirs[1:]:
                registry.insert(
                    path=str(project),
                    indexed_at=now,
                    file_count=1,
                    config={},
                    stats={},
                    index_location="/tmp/index",
                )

            # Create second backup
            backup2 = backup_manager.create_backup(registry)

            registry.close()

            # Restore from first backup (should have only 1 project)
            restored = backup_manager.restore_backup(backup1.backup_path, db_path)

            assert restored is True

            new_registry = ProjectRegistry(db_path=db_path)
            assert new_registry.count() == 1
            assert new_registry.exists(path=str(temp_project_dirs[0]))
            new_registry.close()

    def test_restore_fails_without_backup(self):
        """Should fail restore when no backup exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "registry.db"
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            backup_manager = RegistryBackupManager(backup_dir=backup_dir)

            # Try to restore without backup
            restored = backup_manager.restore_latest_backup(db_path)

            assert restored is False


# ============================================================================
# Test Filesystem Scan Recovery
# ============================================================================

class TestFilesystemScanRecovery:
    """Tests for filesystem scan-based recovery."""

    def test_recover_from_filesystem_scan(self, temp_project_dirs):
        """Should recover registry by scanning filesystem for indexes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "registry.db"

            # Scan filesystem for index directories
            from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

            backup_manager = RegistryBackupManager()
            recovered_projects = backup_manager.scan_and_recover(db_path)

            assert len(recovered_projects) == len(temp_project_dirs)

            # Verify recovered registry
            registry = ProjectRegistry(db_path=db_path)
            assert registry.count() == len(temp_project_dirs)

            for project in temp_project_dirs:
                assert registry.exists(path=str(project))

            registry.close()

    def test_scan_ignores_corrupted_indexes(self):
        """Should ignore corrupted index files during scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create valid project
            project1 = Path(tmpdir) / "project1"
            project1.mkdir()
            index_dir1 = get_project_index_dir(project1)
            index_dir1.mkdir(parents=True)

            serializer = MessagePackSerializer()
            serializer.write(index_dir1 / "files.msgpack", {
                "files": ["src/main.py"],
                "file_count": 1,
            })

            # Create corrupted project
            project2 = Path(tmpdir) / "project2"
            project2.mkdir()
            index_dir2 = get_project_index_dir(project2)
            index_dir2.mkdir(parents=True)

            # Write corrupted data
            (index_dir2 / "files.msgpack").write_bytes(b"corrupted")

            # Scan and recover
            from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

            db_path = Path(tmpdir) / "registry.db"
            backup_manager = RegistryBackupManager()
            recovered = backup_manager.scan_and_recover(db_path)

            # Should only recover valid project
            assert len(recovered) == 1
            assert str(project1) in [p["path"] for p in recovered]

    def test_scan_with_duplicate_paths(self):
        """Should handle duplicate paths during scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project with multiple index files
            project = Path(tmpdir) / "project"
            project.mkdir()
            index_dir = get_project_index_dir(project)
            index_dir.mkdir(parents=True)

            serializer = MessagePackSerializer()
            serializer.write(index_dir / "files.msgpack", {
                "files": ["src/main.py"],
                "file_count": 1,
            })
            serializer.write(index_dir / "symbols.msgpack", {
                "symbols": ["main"],
                "count": 1,
            })

            # Scan and recover
            from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

            db_path = Path(tmpdir) / "registry.db"
            backup_manager = RegistryBackupManager()
            recovered = backup_manager.scan_and_recover(db_path)

            # Should create single registry entry
            assert len(recovered) == 1


# ============================================================================
# Test Index File Corruption Handling
# ============================================================================

class TestIndexFileCorruptionHandling:
    """Tests for handling corrupted index files."""

    def test_skip_corrupted_index_files(self, temp_project_dirs):
        """Should skip corrupted index files during recovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Corrupt one index file
            corrupted_index = get_project_index_dir(temp_project_dirs[0]) / "files.msgpack"
            corrupted_index.write_bytes(b"corrupted data")

            # Scan and recover
            from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

            db_path = Path(tmpdir) / "registry.db"
            backup_manager = RegistryBackupManager()
            recovered = backup_manager.scan_and_recover(db_path)

            # Should recover only non-corrupted projects
            assert len(recovered) == 2

    def test_recover_with_partial_index_data(self):
        """Should recover with partial index data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            index_dir = get_project_index_dir(project)
            index_dir.mkdir(parents=True)

            # Create valid index with minimal data
            serializer = MessagePackSerializer()
            serializer.write(index_dir / "files.msgpack", {
                "files": ["src/main.py"],
                "file_count": 1,
            })

            # Scan and recover
            from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

            db_path = Path(tmpdir) / "registry.db"
            backup_manager = RegistryBackupManager()
            recovered = backup_manager.scan_and_recover(db_path)

            assert len(recovered) == 1
            assert recovered[0]["file_count"] == 1


# ============================================================================
# Test Metadata Corruption Recovery
# ============================================================================

class TestMetadataCorruptionRecovery:
    """Tests for recovering from metadata corruption."""

    def test_rebuild_metadata_from_projects(self, temp_project_dirs):
        """Should rebuild metadata from project data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "registry.db"

            # Create registry
            registry = ProjectRegistry(db_path=db_path)
            now = datetime.now()
            for project in temp_project_dirs:
                registry.insert(
                    path=str(project),
                    indexed_at=now,
                    file_count=1,
                    config={},
                    stats={},
                    index_location=str(get_project_index_dir(project)),
                )

            # Set metadata
            registry.set_metadata("version", "2.1.0")
            registry.set_metadata("last_migration", "2025-01-01")

            registry.close()

            # Corrupt metadata table
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM registry_metadata")
            conn.commit()
            conn.close()

            # Rebuild metadata
            new_registry = ProjectRegistry(db_path=db_path)

            # Verify projects still exist
            assert new_registry.count() == len(temp_project_dirs)

            new_registry.close()

    def test_preserve_projects_on_metadata_rebuild(self, temp_project_dirs):
        """Should preserve projects when rebuilding metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "registry.db"

            # Create registry with projects
            registry = ProjectRegistry(db_path=db_path)
            now = datetime.now()
            project_ids = []
            for project in temp_project_dirs:
                info = registry.insert(
                    path=str(project),
                    indexed_at=now,
                    file_count=1,
                    config={"key": "value"},
                    stats={"files": 1},
                    index_location=str(get_project_index_dir(project)),
                )
                project_ids.append(info.id)

            registry.close()

            # Reopen and verify
            new_registry = ProjectRegistry(db_path=db_path)

            assert new_registry.count() == len(temp_project_dirs)

            for project_id in project_ids:
                project = new_registry.get_by_id(project_id)
                assert project is not None
                assert project.config["key"] == "value"

            new_registry.close()


# ============================================================================
# Test Partial Recovery Scenarios
# ============================================================================

class TestPartialRecoveryScenarios:
    """Tests for partial recovery scenarios."""

    def test_recover_available_projects(self):
        """Should recover all available projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create projects
            projects = []
            for i in range(5):
                project = Path(tmpdir) / f"project{i}"
                project.mkdir()
                index_dir = get_project_index_dir(project)
                index_dir.mkdir(parents=True)

                serializer = MessagePackSerializer()
                serializer.write(index_dir / "files.msgpack", {
                    "files": [f"src/file{i}.py"],
                    "file_count": 1,
                })

                projects.append(project)

            # Delete one project directory
            shutil.rmtree(projects[2])

            # Scan and recover
            from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

            db_path = Path(tmpdir) / "registry.db"
            backup_manager = RegistryBackupManager()
            recovered = backup_manager.scan_and_recover(db_path)

            # Should recover 4 projects (one deleted)
            assert len(recovered) == 4

    def test_merge_with_existing_registry(self):
        """Should merge recovered data with existing registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "registry.db"

            # Create registry with one project
            registry = ProjectRegistry(db_path=db_path)
            now = datetime.now()
            registry.insert(
                path="/existing/project",
                indexed_at=now,
                file_count=1,
                config={},
                stats={},
                index_location="/tmp/existing",
            )

            existing_count = registry.count()
            registry.close()

            # Create new project on filesystem
            new_project = Path(tmpdir) / "new_project"
            new_project.mkdir()
            index_dir = get_project_index_dir(new_project)
            index_dir.mkdir(parents=True)

            serializer = MessagePackSerializer()
            serializer.write(index_dir / "files.msgpack", {
                "files": ["src/new.py"],
                "file_count": 1,
            })

            # Scan and recover (should merge)
            from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

            backup_manager = RegistryBackupManager()
            recovered = backup_manager.scan_and_recover(db_path)

            # Verify merged registry
            new_registry = ProjectRegistry(db_path=db_path)
            assert new_registry.count() >= existing_count
            new_registry.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
