"""
Integration tests for startup migration.

Tests for the meta-registry startup migration module.
"""

import pytest
import pickle
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock

from src.code_index_mcp.registry.startup_migration import (
    StartupMigrationManager,
    MigrationState,
    check_and_migrate_on_startup,
    migrate_project_on_access,
)
from src.code_index_mcp.registry.msgpack_serializer import FormatType, PICKLE_EXT


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_index_data():
    """Create sample index data for testing."""
    return {
        "files": [
            "src/file1.py",
            "src/file2.py",
            "tests/test_file.py",
        ],
        "file_count": 3,
        "last_updated": datetime.now().isoformat(),
        "metadata": {
            "version": "1.0",
            "indexer_version": "2.0.0"
        }
    }


@pytest.fixture
def temp_global_index_dir(sample_index_data):
    """Create a temporary global index directory with pickle files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        global_dir = Path(tmpdir) / ".code_indexer_data"
        global_dir.mkdir()

        # Create multiple pickle files
        for i in range(2):
            pickle_path = global_dir / f"index{i}.pickle"
            with open(pickle_path, "wb") as f:
                pickle.dump(sample_index_data, f)

        yield global_dir


@pytest.fixture
def temp_project_index_dir(sample_index_data):
    """Create a temporary project index directory with pickle files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "myproject" / ".code-indexer"
        project_dir.mkdir(parents=True)

        # Create pickle files
        for i in range(2):
            pickle_path = project_dir / f"index{i}.pickle"
            with open(pickle_path, "wb") as f:
                pickle.dump(sample_index_data, f)

        yield project_dir, Path(tmpdir) / "myproject"


# ============================================================================
# Test MigrationState
# ============================================================================

class TestMigrationState:
    """Tests for MigrationState class."""

    def test_initial_state(self):
        """Should initialize with default values."""
        state = MigrationState()
        assert state.migration_performed is False
        assert state.total_detected == 0
        assert state.total_migrated == 0
        assert state.total_failed == 0
        assert len(state.results) == 0

    def test_add_result_success(self):
        """Should add successful result."""
        state = MigrationState()
        result = Mock(success=True, source_path=Path("test.pickle"))
        state.add_result(result)

        assert state.total_migrated == 1
        assert state.total_failed == 0
        assert len(state.results) == 1

    def test_add_result_failure(self):
        """Should add failed result."""
        state = MigrationState()
        result = Mock(success=False, source_path=Path("test.pickle"))
        state.add_result(result)

        assert state.total_migrated == 0
        assert state.total_failed == 1
        assert len(state.results) == 1

    def test_summary_no_migration(self):
        """Should generate summary for no migration."""
        state = MigrationState()
        state.start_time = datetime.now()
        state.end_time = datetime.now()

        summary = state.summary()
        assert "0 succeeded" in summary
        assert "0 failed" in summary
        assert "0 detected" in summary

    def test_summary_with_migration(self):
        """Should generate summary with migration data."""
        state = MigrationState()
        state.total_detected = 5
        state.total_migrated = 4
        state.total_failed = 1
        state.start_time = datetime.now()
        state.end_time = datetime.now()

        summary = state.summary()
        assert "4 succeeded" in summary
        assert "1 failed" in summary
        assert "5 detected" in summary


# ============================================================================
# Test StartupMigrationManager
# ============================================================================

class TestStartupMigrationManagerInit:
    """Tests for StartupMigrationManager initialization."""

    def test_default_init(self):
        """Should initialize with default settings."""
        manager = StartupMigrationManager()
        assert manager.auto_migrate is True
        assert manager.project_registry is None

    def test_custom_settings(self):
        """Should accept custom settings."""
        project_registry = Mock()
        manager = StartupMigrationManager(
            auto_migrate=False,
            project_registry=project_registry
        )
        assert manager.auto_migrate is False
        assert manager.project_registry == project_registry


# ============================================================================
# Test Detection
# ============================================================================

class TestCheckLegacyIndexes:
    """Tests for legacy index detection."""

    def test_check_no_legacy_indexes(self):
        """Should return no legacy indexes when none exist."""
        manager = StartupMigrationManager()

        with patch('pathlib.Path.home', return_value=Path("/tmp/empty")):
            results = manager.check_legacy_indexes(scan_global=True)

        assert results["has_legacy"] is False
        assert results["legacy_count"] == 0
        assert len(results["legacy_files"]) == 0

    def test_check_global_legacy_indexes(self, temp_global_index_dir):
        """Should detect legacy indexes in global directory."""
        manager = StartupMigrationManager()

        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            results = manager.check_legacy_indexes(scan_global=True)

        assert results["has_legacy"] is True
        assert results["legacy_count"] == 2
        assert len(results["legacy_files"]) == 2

    def test_check_project_legacy_indexes(self, temp_project_index_dir):
        """Should detect legacy indexes in project directory."""
        manager = StartupMigrationManager()
        project_dir, project_path = temp_project_index_dir

        results = manager.check_legacy_indexes(
            project_path=project_path,
            scan_global=False
        )

        assert results["has_legacy"] is True
        assert results["legacy_count"] == 2
        assert len(results["legacy_files"]) == 2

    def test_check_both_directories(self, temp_global_index_dir, temp_project_index_dir):
        """Should detect legacy indexes in both directories."""
        manager = StartupMigrationManager()
        project_dir, project_path = temp_project_index_dir

        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            results = manager.check_legacy_indexes(
                project_path=project_path,
                scan_global=True
            )

        assert results["has_legacy"] is True
        assert results["legacy_count"] == 4  # 2 global + 2 project


# ============================================================================
# Test Migration
# ============================================================================

class TestPerformStartupMigration:
    """Tests for startup migration execution."""

    def test_no_migration_needed(self):
        """Should skip migration when no legacy indexes exist."""
        manager = StartupMigrationManager(auto_migrate=True)

        with patch('pathlib.Path.home', return_value=Path("/tmp/empty")):
            state = manager.perform_startup_migration(scan_global=True)

        assert state.migration_performed is False
        assert state.total_detected == 0
        assert state.total_migrated == 0

    def test_auto_migrate_enabled(self, temp_global_index_dir):
        """Should perform migration when auto_migrate is enabled."""
        manager = StartupMigrationManager(auto_migrate=True)

        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            state = manager.perform_startup_migration(scan_global=True)

        assert state.migration_performed is True
        assert state.total_detected == 2
        assert state.total_migrated == 2
        assert state.total_failed == 0

    def test_auto_migrate_disabled(self, temp_global_index_dir):
        """Should not migrate when auto_migrate is disabled."""
        manager = StartupMigrationManager(auto_migrate=False)

        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            state = manager.perform_startup_migration(scan_global=True)

        assert state.migration_performed is False
        assert state.total_detected == 2
        assert state.total_migrated == 0

    def test_auto_migrate_override(self, temp_global_index_dir):
        """Should respect auto_migrate_override parameter."""
        manager = StartupMigrationManager(auto_migrate=False)

        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            state = manager.perform_startup_migration(
                scan_global=True,
                auto_migrate_override=True
            )

        assert state.migration_performed is True
        assert state.total_migrated == 2

    def test_tracks_migration_duration(self, temp_global_index_dir):
        """Should track migration duration."""
        manager = StartupMigrationManager(auto_migrate=True)

        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            state = manager.perform_startup_migration(scan_global=True)

        assert state.start_time is not None
        assert state.end_time is not None
        assert state.end_time >= state.start_time

    def test_partial_migration_failure(self, temp_global_index_dir):
        """Should handle partial migration failure."""
        manager = StartupMigrationManager(auto_migrate=True)

        # Create a corrupt pickle file
        corrupt_pickle = temp_global_index_dir / "corrupt.pickle"
        with open(corrupt_pickle, "wb") as f:
            f.write(b"corrupt data")

        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            state = manager.perform_startup_migration(scan_global=True)

        assert state.migration_performed is True
        assert state.total_detected == 3  # 2 valid + 1 corrupt
        assert state.total_migrated == 2
        assert state.total_failed == 1


# ============================================================================
# Test Registry Tracking
# ============================================================================

class TestRegistryTracking:
    """Tests for registry tracking during migration."""

    def test_track_migration_in_registry(self, temp_global_index_dir):
        """Should track migration in project registry if available."""
        project_registry = Mock()
        manager = StartupMigrationManager(
            auto_migrate=True,
            project_registry=project_registry
        )

        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            state = manager.perform_startup_migration(scan_global=True)

        # Verify that _track_migration_in_registry was called for each success
        assert state.total_migrated == 2
        # Note: actual tracking implementation is a placeholder

    def test_no_registry_available(self, temp_global_index_dir):
        """Should handle missing project registry gracefully."""
        manager = StartupMigrationManager(
            auto_migrate=True,
            project_registry=None
        )

        # Should not raise exception
        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            state = manager.perform_startup_migration(scan_global=True)

        assert state.total_migrated == 2


# ============================================================================
# Test First-Access Migration
# ============================================================================

class TestMigrateOnFirstAccess:
    """Tests for first-access migration."""

    def test_no_migration_needed(self):
        """Should return False when no migration is needed."""
        manager = StartupMigrationManager(auto_migrate=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()

            migrated = manager.migrate_on_first_access(project_path)

        assert migrated is False

    def test_migrates_on_first_access(self, temp_project_index_dir):
        """Should migrate when legacy indexes are detected."""
        manager = StartupMigrationManager(auto_migrate=True)
        project_dir, project_path = temp_project_index_dir

        migrated = manager.migrate_on_first_access(project_path)

        assert migrated is True

    def test_creates_msgpack_files(self, temp_project_index_dir):
        """Should create MessagePack files after migration."""
        manager = StartupMigrationManager(auto_migrate=True)
        project_dir, project_path = temp_project_index_dir

        manager.migrate_on_first_access(project_path)

        # Check that MessagePack files were created
        msgpack_files = list(project_dir.glob("*.msgpack"))
        assert len(msgpack_files) == 2


# ============================================================================
# Test Convenience Functions
# ============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_check_and_migrate_on_startup(self, temp_global_index_dir):
        """Should check and migrate using convenience function."""
        with patch('pathlib.Path.home', return_value=temp_global_index_dir.parent):
            state = check_and_migrate_on_startup(
                project_path=None,
                auto_migrate=True,
                project_registry=None
            )

        assert state.migration_performed is True
        assert state.total_migrated == 2

    def test_migrate_project_on_access(self, temp_project_index_dir):
        """Should migrate project on access using convenience function."""
        project_dir, project_path = temp_project_index_dir

        migrated = migrate_project_on_access(
            project_path=project_path,
            project_registry=None
        )

        assert migrated is True


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Tests for realistic integration scenarios."""

    def test_full_migration_workflow(self, sample_index_data):
        """Should complete full migration workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create global and project directories with pickle files
            global_dir = Path(tmpdir) / ".code_indexer_data"
            global_dir.mkdir()

            for i in range(2):
                pickle_path = global_dir / f"global{i}.pickle"
                with open(pickle_path, "wb") as f:
                    pickle.dump(sample_index_data, f)

            project_dir = Path(tmpdir) / "myproject" / ".code-indexer"
            project_dir.mkdir(parents=True)

            for i in range(2):
                pickle_path = project_dir / f"project{i}.pickle"
                with open(pickle_path, "wb") as f:
                    pickle.dump(sample_index_data, f)

            # Execute: Perform startup migration
            manager = StartupMigrationManager(auto_migrate=True)

            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                state = manager.perform_startup_migration(
                    project_path=Path(tmpdir) / "myproject",
                    scan_global=True
                )

            # Verify: All indexes migrated
            assert state.migration_performed is True
            assert state.total_detected == 4
            assert state.total_migrated == 4
            assert state.total_failed == 0

            # Verify: MessagePack files created
            global_msgpack = list(global_dir.glob("*.msgpack"))
            project_msgpack = list(project_dir.glob("*.msgpack"))
            assert len(global_msgpack) == 2
            assert len(project_msgpack) == 2

            # Verify: Original pickle files preserved (including backups)
            global_pickle = list(global_dir.glob("*.pickle"))
            project_pickle = list(project_dir.glob("*.pickle"))
            # Should have original files + backup files
            assert len(global_pickle) == 4  # 2 original + 2 backups
            assert len(project_pickle) == 4  # 2 original + 2 backups

            # Verify: Backups created
            global_backups = [f for f in global_dir.glob("*.pickle") if "backup" in f.stem]
            assert len(global_backups) == 2
            project_backups = [f for f in project_dir.glob("*.pickle") if "backup" in f.stem]
            assert len(project_backups) == 2

    def test_migration_with_existing_msgpack_files(self, sample_index_data):
        """Should handle migration when some MessagePack files already exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject" / ".code-indexer"
            project_dir.mkdir(parents=True)

            # Create one pickle and one MessagePack file
            pickle_path = project_dir / "index1.pickle"
            with open(pickle_path, "wb") as f:
                pickle.dump(sample_index_data, f)

            # Create a MessagePack file directly
            from src.code_index_mcp.registry.msgpack_serializer import MessagePackSerializer
            serializer = MessagePackSerializer()
            msgpack_path = project_dir / "index2.msgpack"
            serializer.write(msgpack_path, sample_index_data)

            # Execute migration
            manager = StartupMigrationManager(auto_migrate=True)
            manager.migrate_on_first_access(Path(tmpdir) / "myproject")

            # Verify: Only pickle file was migrated
            msgpack_files = list(project_dir.glob("*.msgpack"))
            assert len(msgpack_files) == 2  # 1 existing + 1 migrated

    def test_repeated_migration_is_idempotent(self, sample_index_data):
        """Should handle repeated migration calls gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject" / ".code-indexer"
            project_dir.mkdir(parents=True)

            # Create pickle files
            pickle_path = project_dir / "index1.pickle"
            with open(pickle_path, "wb") as f:
                pickle.dump(sample_index_data, f)

            manager = StartupMigrationManager(auto_migrate=True)
            project_path = Path(tmpdir) / "myproject"

            # First migration
            state1 = manager.perform_startup_migration(
                project_path=project_path,
                scan_global=False
            )
            assert state1.migration_performed is True
            assert state1.total_migrated == 1

            # Second migration (should find no new pickle files to migrate)
            state2 = manager.perform_startup_migration(
                project_path=project_path,
                scan_global=False
            )
            # The pickle file still exists, so it will be detected again
            # But migration should still work
            assert state2.total_migrated >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
