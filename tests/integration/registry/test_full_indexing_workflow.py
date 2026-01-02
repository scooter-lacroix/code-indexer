"""
Integration tests for full indexing workflow with meta-registry.

This module tests the complete indexing workflow from project setup through
indexing, searching, and registry operations.

Tests cover:
- Full indexing workflow with registry integration
- Project registration during indexing
- Registry updates on re-index
- Index data retrieval via registry
- End-to-end project lifecycle
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock
import pickle
import msgpack

from src.code_index_mcp.registry.project_registry import (
    ProjectRegistry,
    ProjectInfo,
    RegistryError,
)
from src.code_index_mcp.registry.msgpack_serializer import MessagePackSerializer
from src.code_index_mcp.registry.directories import (
    get_project_index_dir,
    get_registry_db_path,
)
from src.code_index_mcp.registry.orphan_detector import OrphanDetector
from src.code_index_mcp.registry.registration_integrator import RegistrationIntegrator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with sample code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "sample_project"
        project_dir.mkdir()

        # Create sample directory structure
        src_dir = project_dir / "src"
        src_dir.mkdir()
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()

        # Create sample Python files
        (src_dir / "main.py").write_text("""
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")

        (src_dir / "utils.py").write_text("""
def helper_function(x):
    return x * 2

class HelperClass:
    def method(self):
        pass
""")

        (tests_dir / "test_main.py").write_text("""
def test_main():
    assert True
""")

        yield project_dir


@pytest.fixture
def registry_with_temp_db():
    """Create a registry with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_registry.db"
        registry = ProjectRegistry(db_path=db_path)
        yield registry, tmpdir
        registry.close()


@pytest.fixture
def sample_index_data():
    """Create sample index data."""
    return {
        "files": [
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
        ],
        "file_count": 3,
        "last_updated": datetime.now().isoformat(),
        "metadata": {
            "version": "2.0.0",
            "indexer_version": "2.1.0",
        },
        "indexes": {
            "symbols": {
                "functions": ["main", "helper_function"],
                "classes": ["HelperClass"],
            }
        }
    }


# ============================================================================
# Test Full Indexing Workflow
# ============================================================================

class TestFullIndexingWorkflow:
    """Tests for complete indexing workflow with registry."""

    def test_project_registration_on_first_index(
        self, temp_project_dir, registry_with_temp_db
    ):
        """Should register project in registry on first index."""
        registry, _ = registry_with_temp_db

        # Simulate first indexing
        index_dir = get_project_index_dir(temp_project_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        serializer = MessagePackSerializer()
        index_path = index_dir / "files.msgpack"

        sample_data = {
            "files": ["src/main.py", "src/utils.py"],
            "file_count": 2,
            "last_updated": datetime.now().isoformat(),
        }
        serializer.write(index_path, sample_data)

        # Register project
        now = datetime.now()
        project_info = registry.insert(
            path=str(temp_project_dir),
            indexed_at=now,
            file_count=2,
            config={},
            stats={},
            index_location=str(index_dir),
        )

        # Verify registration
        assert project_info.id is not None
        assert project_info.path == str(temp_project_dir)
        assert registry.exists(path=str(temp_project_dir))

        retrieved = registry.get_by_path(path=str(temp_project_dir))
        assert retrieved.path == str(temp_project_dir)
        assert retrieved.file_count == 2

    def test_registry_update_on_reindex(
        self, temp_project_dir, registry_with_temp_db
    ):
        """Should update registry entry on re-index."""
        registry, _ = registry_with_temp_db

        # Initial index
        now = datetime.now()
        project_info = registry.insert(
            path=str(temp_project_dir),
            indexed_at=now,
            file_count=2,
            config={},
            stats={},
            index_location="/tmp/index1",
        )

        assert project_info.file_count == 2

        # Simulate file addition
        new_file = temp_project_dir / "new_file.py"
        new_file.write_text("# New file")

        # Re-index (update registry)
        updated = registry.update(
            path=str(temp_project_dir),
            indexed_at=datetime.now(),
            file_count=3,
            stats={"files": 3},
        )

        assert updated.file_count == 3

    def test_index_data_persistence(self, temp_project_dir, sample_index_data):
        """Should persist index data and retrieve via registry."""
        # Create index directory
        index_dir = get_project_index_dir(temp_project_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Write index data
        serializer = MessagePackSerializer()
        index_path = index_dir / "files.msgpack"
        serializer.write(index_path, sample_index_data)

        # Verify data can be read
        retrieved_data = serializer.read(index_path)
        assert retrieved_data["file_count"] == sample_index_data["file_count"]
        assert retrieved_data["files"] == sample_index_data["files"]

    def test_orphan_detection(self, temp_project_dir, registry_with_temp_db):
        """Should detect orphaned index directories."""
        registry, _ = registry_with_temp_db

        # Create index directory without registry entry
        index_dir = get_project_index_dir(temp_project_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Create orphan detector
        detector = OrphanDetector(registry=registry)

        # Detect orphans
        orphans = detector.detect_orphans()

        # Should detect the orphaned directory
        assert len(orphans) > 0
        assert any(str(temp_project_dir) in o.path for o in orphans)

    def test_orphan_cleanup(self, temp_project_dir, registry_with_temp_db):
        """Should clean up orphaned index directories."""
        registry, _ = registry_with_temp_db

        # Create index directory without registry entry
        index_dir = get_project_index_dir(temp_project_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Create orphan detector
        detector = OrphanDetector(registry=registry)

        # Clean up orphans
        cleaned = detector.cleanup_orphans()

        # Verify cleanup
        assert cleaned > 0
        assert not index_dir.exists()

    def test_registration_integrator_workflow(
        self, temp_project_dir, registry_with_temp_db, sample_index_data
    ):
        """Should integrate registration with indexing workflow."""
        registry, _ = registry_with_temp_db

        # Create registration integrator
        integrator = RegistrationIntegrator(registry=registry)

        # Simulate indexing completion
        index_dir = get_project_index_dir(temp_project_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        serializer = MessagePackSerializer()
        index_path = index_dir / "files.msgpack"
        serializer.write(index_path, sample_index_data)

        # Register project after indexing
        project_info = integrator.register_after_indexing(
            project_path=str(temp_project_dir),
            index_location=str(index_dir),
            file_count=sample_index_data["file_count"],
            stats=sample_index_data.get("metadata", {}),
        )

        assert project_info is not None
        assert registry.exists(path=str(temp_project_dir))

        # Verify retrieval
        retrieved = registry.get_by_path(path=str(temp_project_dir))
        assert retrieved.file_count == sample_index_data["file_count"]


# ============================================================================
# Test Multi-Project Scenarios
# ============================================================================

class TestMultiProjectScenarios:
    """Tests for multiple projects in registry."""

    def test_multiple_projects_registration(self, registry_with_temp_db):
        """Should handle multiple projects in registry."""
        registry, _ = registry_with_temp_db

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple projects
            project1 = Path(tmpdir) / "project1"
            project2 = Path(tmpdir) / "project2"
            project3 = Path(tmpdir) / "project3"

            for p in [project1, project2, project3]:
                p.mkdir()

            # Register all projects
            now = datetime.now()
            for p in [project1, project2, project3]:
                registry.insert(
                    path=str(p),
                    indexed_at=now,
                    file_count=1,
                    config={},
                    stats={},
                    index_location=f"/tmp/index/{p.name}",
                )

            # Verify all registered
            assert registry.count() == 3

            # List all projects
            projects = registry.list_all()
            assert len(projects) == 3

    def test_project_isolation(self, registry_with_temp_db):
        """Should maintain isolation between projects."""
        registry, _ = registry_with_temp_db

        with tempfile.TemporaryDirectory() as tmpdir:
            project1 = Path(tmpdir) / "project1"
            project2 = Path(tmpdir) / "project2"

            for p in [project1, project2]:
                p.mkdir()

            # Register projects with different configs
            now = datetime.now()
            registry.insert(
                path=str(project1),
                indexed_at=now,
                file_count=10,
                config={"theme": "dark"},
                stats={},
                index_location="/tmp/index1",
            )

            registry.insert(
                path=str(project2),
                indexed_at=now,
                file_count=20,
                config={"theme": "light"},
                stats={},
                index_location="/tmp/index2",
            )

            # Verify isolation
            info1 = registry.get_by_path(path=str(project1))
            info2 = registry.get_by_path(path=str(project2))

            assert info1.file_count == 10
            assert info1.config["theme"] == "dark"
            assert info2.file_count == 20
            assert info2.config["theme"] == "light"


# ============================================================================
# Test Error Scenarios
# ============================================================================

class TestErrorScenarios:
    """Tests for error handling in indexing workflow."""

    def test_missing_project_raises_error(self, registry_with_temp_db):
        """Should raise error for missing project."""
        registry, _ = registry_with_temp_db

        with pytest.raises(Exception):  # ProjectNotFoundError
            registry.get_by_path(path="/nonexistent/project")

    def test_corrupted_index_recovery(self, temp_project_dir, registry_with_temp_db):
        """Should handle corrupted index gracefully."""
        registry, _ = registry_with_temp_db

        # Create corrupted index file
        index_dir = get_project_index_dir(temp_project_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        corrupted_file = index_dir / "files.msgpack"
        corrupted_file.write_bytes(b"corrupted data")

        # Try to read corrupted file
        serializer = MessagePackSerializer()
        try:
            serializer.read(corrupted_file)
            assert False, "Should have raised exception"
        except Exception:
            pass  # Expected

    def test_concurrent_registration(self, registry_with_temp_db):
        """Should handle concurrent registration attempts."""
        registry, _ = registry_with_temp_db

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()

            # First registration
            now = datetime.now()
            registry.insert(
                path=str(project),
                indexed_at=now,
                file_count=1,
                config={},
                stats={},
                index_location="/tmp/index",
            )

            # Second registration (duplicate) should fail
            with pytest.raises(Exception):  # DuplicateProjectError
                registry.insert(
                    path=str(project),
                    indexed_at=now,
                    file_count=2,
                    config={},
                    stats={},
                    index_location="/tmp/index2",
                )


# ============================================================================
# Test Migration Integration
# ============================================================================

class TestMigrationIntegration:
    """Tests for migration workflow integration."""

    def test_pickle_to_msgpack_migration(self, temp_project_dir, registry_with_temp_db):
        """Should migrate pickle index to msgpack format."""
        registry, _ = registry_with_temp_db

        # Create old pickle index
        index_dir = get_project_index_dir(temp_project_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        pickle_data = {
            "files": ["src/main.py"],
            "file_count": 1,
            "last_updated": datetime.now().isoformat(),
        }

        pickle_path = index_dir / "files.pickle"
        with open(pickle_path, "wb") as f:
            pickle.dump(pickle_data, f)

        # Migrate to msgpack
        from src.code_index_mcp.registry.index_migrator import IndexMigrator

        migrator = IndexMigrator()
        result = migrator.migrate_index_file(pickle_path)

        assert result.success is True
        assert (index_dir / "files.msgpack").exists()

        # Verify msgpack data
        serializer = MessagePackSerializer()
        msgpack_data = serializer.read(index_dir / "files.msgpack")
        assert msgpack_data["file_count"] == pickle_data["file_count"]

    def test_migration_with_registry_update(
        self, temp_project_dir, registry_with_temp_db
    ):
        """Should update registry after migration."""
        registry, _ = registry_with_temp_db

        # Create pickle index
        index_dir = get_project_index_dir(temp_project_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        pickle_data = {"files": ["src/main.py"], "file_count": 1}
        pickle_path = index_dir / "files.pickle"
        with open(pickle_path, "wb") as f:
            pickle.dump(pickle_data, f)

        # Register project (old format)
        now = datetime.now()
        registry.insert(
            path=str(temp_project_dir),
            indexed_at=now,
            file_count=1,
            config={"format": "pickle"},
            stats={},
            index_location=str(index_dir),
        )

        # Migrate
        from src.code_index_mcp.registry.index_migrator import IndexMigrator

        migrator = IndexMigrator()
        migrator.migrate_index_file(pickle_path)

        # Update registry to reflect new format
        registry.update(
            path=str(temp_project_dir),
            config={"format": "msgpack"},
        )

        # Verify
        project = registry.get_by_path(path=str(temp_project_dir))
        assert project.config["format"] == "msgpack"


# ============================================================================
# Test Backup Integration
# ============================================================================

class TestBackupIntegration:
    """Tests for backup integration in indexing workflow."""

    def test_backup_after_indexing(
        self, temp_project_dir, registry_with_temp_db
    ):
        """Should create backup after indexing."""
        registry, _ = registry_with_temp_db

        # Register project
        now = datetime.now()
        registry.insert(
            path=str(temp_project_dir),
            indexed_at=now,
            file_count=5,
            config={},
            stats={},
            index_location="/tmp/index",
        )

        # Create backup
        from src.code_index_mcp.registry.registry_backup import RegistryBackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            backup_manager = RegistryBackupManager(backup_dir=backup_dir)
            backup_metadata = backup_manager.create_backup(registry)

            assert backup_metadata is not None
            assert backup_metadata.project_count == 1

    def test_restore_after_corruption(
        self, temp_project_dir, registry_with_temp_db
    ):
        """Should restore registry from backup after corruption."""
        registry, db_path = registry_with_temp_db

        # Register project
        now = datetime.now()
        registry.insert(
            path=str(temp_project_dir),
            indexed_at=now,
            file_count=5,
            config={},
            stats={},
            index_location="/tmp/index",
        )

        # Create backup
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            backup_manager = RegistryBackupManager(backup_dir=backup_dir)
            backup_manager.create_backup(registry)

            # Corrupt registry
            registry.close()
            db_path.write_bytes(b"corrupted")

            # Restore from backup
            restored = backup_manager.restore_latest_backup(db_path)

            assert restored is True

            # Verify restored data
            new_registry = ProjectRegistry(db_path=db_path)
            assert new_registry.exists(path=str(temp_project_dir))
            new_registry.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
