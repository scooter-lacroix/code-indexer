"""
Unit tests for IndexMigrator.

Tests for the meta-registry index migration module.
"""

import pytest
import pickle
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock

from src.code_index_mcp.registry.index_migrator import (
    IndexMigrator,
    MigrationStatus,
    MigrationResult,
)
from src.code_index_mcp.registry.msgpack_serializer import FormatType, PICKLE_EXT, MSGPACK_EXT


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def migrator():
    """Create an IndexMigrator instance for testing."""
    return IndexMigrator(create_backups=True, verify_after_migration=True)


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
def temp_pickle_file(sample_index_data):
    """Create a temporary pickle file with sample data."""
    with tempfile.NamedTemporaryFile(suffix=PICKLE_EXT, delete=False) as f:
        pickle.dump(sample_index_data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


# ============================================================================
# Test IndexMigratorInit
# ============================================================================

class TestIndexMigratorInit:
    """Tests for IndexMigrator initialization."""

    def test_default_init(self):
        """Should initialize with default settings."""
        migrator = IndexMigrator()
        assert migrator.create_backups is True
        assert migrator.verify_after_migration is True

    def test_custom_settings(self):
        """Should accept custom settings."""
        migrator = IndexMigrator(create_backups=False, verify_after_migration=False)
        assert migrator.create_backups is False
        assert migrator.verify_after_migration is False


# ============================================================================
# Test Legacy Detection
# ============================================================================

class TestDetectLegacyIndexes:
    """Tests for legacy pickle index detection."""

    def test_detect_pickle_in_global_directory(self, migrator, temp_pickle_file):
        """Should detect pickle file in global directory."""
        # Create a fake global directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            global_dir = Path(tmpdir) / ".code_indexer_data"
            global_dir.mkdir()

            # Copy pickle file to global directory
            test_pickle = global_dir / "index.pickle"
            shutil.copy(temp_pickle_file, test_pickle)

            # Patch Path.home() to return temp directory
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                detected = migrator.detect_legacy_indexes(scan_global=True)

            assert len(detected) == 1
            assert detected[0] == test_pickle

    def test_detect_pickle_in_project_directory(self, migrator, temp_pickle_file):
        """Should detect pickle file in project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject" / ".code-indexer"
            project_dir.mkdir(parents=True)

            # Copy pickle file to project directory
            test_pickle = project_dir / "index.pickle"
            shutil.copy(temp_pickle_file, test_pickle)

            detected = migrator.detect_legacy_indexes(
                project_path=Path(tmpdir) / "myproject",
                scan_global=False
            )

            assert len(detected) == 1
            assert detected[0] == test_pickle

    def test_detect_no_pickle_files(self, migrator):
        """Should return empty list when no pickle files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory with no pickle files
            test_dir = Path(tmpdir) / "empty"
            test_dir.mkdir()

            with patch('pathlib.Path.home', return_value=test_dir):
                detected = migrator.detect_legacy_indexes(scan_global=True)

            assert len(detected) == 0

    def test_detect_recursive_scan(self, migrator, temp_pickle_file):
        """Should recursively scan directories for pickle files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / ".code_indexer_data"
            base_dir.mkdir()

            # Create nested structure
            subdir = base_dir / "project1" / "indexes"
            subdir.mkdir(parents=True)

            test_pickle = subdir / "index.pickle"
            shutil.copy(temp_pickle_file, test_pickle)

            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                detected = migrator.detect_legacy_indexes(scan_global=True)

            assert len(detected) == 1
            assert detected[0] == test_pickle


# ============================================================================
# Test Validation
# ============================================================================

class TestValidatePickleFile:
    """Tests for pickle file validation."""

    def test_validate_valid_pickle(self, migrator, temp_pickle_file):
        """Should validate a correct pickle file."""
        is_valid, error = migrator.validate_pickle_file(temp_pickle_file)
        assert is_valid is True
        assert error is None

    def test_validate_nonexistent_file(self, migrator):
        """Should fail validation for nonexistent file."""
        is_valid, error = migrator.validate_pickle_file("/nonexistent/file.pickle")
        assert is_valid is False
        assert "does not exist" in error

    def test_validate_corrupt_pickle(self, migrator):
        """Should fail validation for corrupt pickle file."""
        with tempfile.NamedTemporaryFile(suffix=PICKLE_EXT, delete=False) as f:
            f.write(b"corrupt pickle data")
            temp_path = Path(f.name)

        try:
            is_valid, error = migrator.validate_pickle_file(temp_path)
            assert is_valid is False
            assert "Invalid pickle file" in error
        finally:
            temp_path.unlink()

    def test_validate_non_dict_data(self, migrator):
        """Should fail validation for non-dict pickle data."""
        with tempfile.NamedTemporaryFile(suffix=PICKLE_EXT, delete=False) as f:
            # Pickle a list instead of dict
            pickle.dump([1, 2, 3], f)
            temp_path = Path(f.name)

        try:
            is_valid, error = migrator.validate_pickle_file(temp_path)
            assert is_valid is False
            assert "not dict-like" in error
        finally:
            temp_path.unlink()

    def test_validate_unreadable_file(self, migrator, temp_pickle_file):
        """Should fail validation for unreadable file."""
        # Make file unreadable (if permissions allow)
        try:
            temp_pickle_file.chmod(0o000)
            is_valid, error = migrator.validate_pickle_file(temp_pickle_file)
            assert is_valid is False
            assert "not readable" in error
        finally:
            # Restore permissions for cleanup
            temp_pickle_file.chmod(0o644)


# ============================================================================
# Test Migration
# ============================================================================

class TestMigrateIndex:
    """Tests for single index migration."""

    def test_migrate_pickle_to_msgpack(self, migrator, temp_pickle_file):
        """Should successfully migrate pickle to MessagePack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "index.msgpack"

            result = migrator.migrate_index(
                temp_pickle_file,
                target_path=target_path
            )

            assert result.success is True
            assert result.target_path == target_path
            assert result.source_format == FormatType.PICKLE
            assert result.file_count > 0
            assert result.error_message is None
            assert target_path.exists()

    def test_migrate_creates_backup(self, migrator, temp_pickle_file):
        """Should create backup when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "index.msgpack"

            result = migrator.migrate_index(
                temp_pickle_file,
                target_path=target_path,
                create_backup=True
            )

            assert result.success is True
            assert result.backup_path is not None
            assert result.backup_path.exists()
            assert "backup" in result.backup_path.name
            assert result.backup_path.suffix == PICKLE_EXT

    def test_migrate_without_backup(self, migrator, temp_pickle_file):
        """Should not create backup when disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "index.msgpack"

            result = migrator.migrate_index(
                temp_pickle_file,
                target_path=target_path,
                create_backup=False
            )

            assert result.success is True
            assert result.backup_path is None

    def test_migrate_auto_generate_target(self, migrator, temp_pickle_file):
        """Should auto-generate target path if not provided."""
        result = migrator.migrate_index(temp_pickle_file)

        assert result.success is True
        assert result.target_path.suffix == MSGPACK_EXT
        assert result.target_path.stem == temp_pickle_file.stem

    def test_migrate_invalid_file(self, migrator):
        """Should fail migration for invalid file."""
        with tempfile.NamedTemporaryFile(suffix=PICKLE_EXT, delete=False) as f:
            f.write(b"invalid")
            temp_path = Path(f.name)

        try:
            result = migrator.migrate_index(temp_path)
            assert result.success is False
            assert result.error_message is not None
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_migrate_preserves_data(self, migrator, temp_pickle_file, sample_index_data):
        """Should preserve data during migration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "index.msgpack"

            result = migrator.migrate_index(
                temp_pickle_file,
                target_path=target_path
            )

            assert result.success is True

            # Read migrated data and compare
            migrated_data = migrator.serializer.read(target_path)
            assert migrated_data == sample_index_data

    def test_migrate_records_duration(self, migrator, temp_pickle_file):
        """Should record migration duration."""
        result = migrator.migrate_index(temp_pickle_file)

        assert result.success is True
        assert result.duration_seconds >= 0
        assert isinstance(result.duration_seconds, float)

    def test_migrate_records_timestamp(self, migrator, temp_pickle_file):
        """Should record migration timestamp."""
        before_migration = datetime.now()
        result = migrator.migrate_index(temp_pickle_file)
        after_migration = datetime.now()

        assert result.success is True
        assert isinstance(result.timestamp, datetime)
        assert before_migration <= result.timestamp <= after_migration


# ============================================================================
# Test Batch Migration
# ============================================================================

class TestMigrateAll:
    """Tests for batch migration."""

    def test_migrate_all_indexes(self, migrator, sample_index_data):
        """Should migrate all detected indexes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple pickle files
            project_dir = Path(tmpdir) / "project" / ".code-indexer"
            project_dir.mkdir(parents=True)

            pickle_files = []
            for i in range(3):
                pickle_path = project_dir / f"index{i}.pickle"
                with open(pickle_path, "wb") as f:
                    pickle.dump(sample_index_data, f)
                pickle_files.append(pickle_path)

            # Migrate all
            results = migrator.migrate_all(
                project_path=Path(tmpdir) / "project",
                scan_global=False
            )

            assert len(results) == 3
            assert all(r.success for r in results)

    def test_migrate_all_no_indexes(self, migrator):
        """Should handle case with no indexes to migrate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = migrator.migrate_all(
                project_path=tmpdir,
                scan_global=False
            )

            assert len(results) == 0

    def test_migrate_all_partial_failure(self, migrator, sample_index_data):
        """Should continue migration even if some files fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project" / ".code-indexer"
            project_dir.mkdir(parents=True)

            # Create valid pickle
            valid_pickle = project_dir / "valid.pickle"
            with open(valid_pickle, "wb") as f:
                pickle.dump(sample_index_data, f)

            # Create invalid pickle
            invalid_pickle = project_dir / "invalid.pickle"
            with open(invalid_pickle, "wb") as f:
                f.write(b"invalid data")

            # Migrate all
            results = migrator.migrate_all(
                project_path=Path(tmpdir) / "project",
                scan_global=False
            )

            assert len(results) == 2
            assert sum(1 for r in results if r.success) == 1
            assert sum(1 for r in results if not r.success) == 1


# ============================================================================
# Test Rollback
# ============================================================================

class TestRollback:
    """Tests for migration rollback."""

    def test_rollback_restores_original(self, migrator, temp_pickle_file):
        """Should restore original file from backup."""
        with tempfile.NamedTemporaryFile(suffix=MSGPACK_EXT, delete=False) as f:
            # Write some data that will be replaced
            f.write(b"old data")
            target_path = Path(f.name)

        try:
            # Migrate
            result = migrator.migrate_index(
                temp_pickle_file,
                target_path=target_path,
                create_backup=True
            )

            # Modify the migrated file
            with open(target_path, "wb") as f:
                f.write(b"modified data")

            # Get original checksum before rollback
            original_checksum = result.source_checksum

            # Rollback
            success = migrator.rollback_migration(result, remove_target=True)

            assert success is True
            assert not target_path.exists()  # Target removed

            # Verify original file is restored
            restored_checksum = migrator.serializer.compute_hash(temp_pickle_file)
            assert restored_checksum == original_checksum

        finally:
            if target_path.exists():
                target_path.unlink()

    def test_rollback_without_backup(self, migrator, temp_pickle_file):
        """Should fail rollback when no backup exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "index.msgpack"

            result = migrator.migrate_index(
                temp_pickle_file,
                target_path=target_path,
                create_backup=False
            )

            # Try to rollback without backup
            success = migrator.rollback_migration(result)

            assert success is False

    def test_rollback_after_failure(self, migrator, sample_index_data):
        """Should have backup available even after failed migration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a pickle file that will cause issues
            project_dir = Path(tmpdir) / ".code-indexer"
            project_dir.mkdir()

            pickle_path = project_dir / "index.pickle"
            with open(pickle_path, "wb") as f:
                pickle.dump(sample_index_data, f)

            # Mock serializer.write to fail
            with patch.object(
                migrator.serializer,
                'write',
                side_effect=IOError("Write failed")
            ):
                result = migrator.migrate_index(pickle_path)

            assert result.success is False
            assert result.backup_path is not None
            assert result.backup_path.exists()


# ============================================================================
# Test Verification
# ============================================================================

class TestVerifyMigration:
    """Tests for migration verification."""

    def test_verify_successful_migration(self, migrator, temp_pickle_file):
        """Should verify successful migration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "index.msgpack"

            result = migrator.migrate_index(
                temp_pickle_file,
                target_path=target_path
            )

            assert result.success is True
            verification = migrator.verify_migration(result)
            assert verification is True

    def test_verify_failed_migration(self, migrator):
        """Should fail verification for failed migration."""
        with tempfile.NamedTemporaryFile(suffix=PICKLE_EXT, delete=False) as f:
            f.write(b"invalid")
            temp_path = Path(f.name)

        try:
            result = migrator.migrate_index(temp_path)
            verification = migrator.verify_migration(result)
            assert verification is False
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_verify_missing_target(self, migrator, temp_pickle_file):
        """Should fail verification if target is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "index.msgpack"

            result = migrator.migrate_index(
                temp_pickle_file,
                target_path=target_path
            )

            # Remove target file
            target_path.unlink()

            verification = migrator.verify_migration(result)
            assert verification is False


# ============================================================================
# Test Status Tracking
# ============================================================================

class TestGetMigrationStatus:
    """Tests for migration status tracking."""

    def test_status_with_legacy_files(self, migrator, temp_pickle_file):
        """Should detect legacy files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject" / ".code-indexer"
            project_dir.mkdir(parents=True)

            # Copy pickle file
            test_pickle = project_dir / "index.pickle"
            shutil.copy(temp_pickle_file, test_pickle)

            status = migrator.get_migration_status(Path(tmpdir) / "myproject")

            assert status["has_legacy"] is True
            assert status["migration_needed"] is True
            assert status["migration_complete"] is False
            assert len(status["legacy_files"]) == 1

    def test_status_with_msgpack_files(self, migrator, sample_index_data):
        """Should detect MessagePack files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject" / ".code-indexer"
            project_dir.mkdir(parents=True)

            # Write MessagePack file
            msgpack_path = project_dir / "index.msgpack"
            migrator.serializer.write(msgpack_path, sample_index_data)

            status = migrator.get_migration_status(Path(tmpdir) / "myproject")

            assert status["has_msgpack"] is True
            assert len(status["msgpack_files"]) == 1

    def test_status_complete_migration(self, migrator, sample_index_data):
        """Should detect complete migration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject" / ".code-indexer"
            project_dir.mkdir(parents=True)

            # Only MessagePack file exists
            msgpack_path = project_dir / "index.msgpack"
            migrator.serializer.write(msgpack_path, sample_index_data)

            status = migrator.get_migration_status(Path(tmpdir) / "myproject")

            assert status["migration_complete"] is True
            assert status["migration_needed"] is False

    def test_status_no_registry_dir(self, migrator):
        """Should handle project without registry directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()

            status = migrator.get_migration_status(project_path)

            assert status["migration_complete"] is True  # Nothing to migrate
            assert status["migration_needed"] is False

    def test_status_invalid_project_path(self, migrator):
        """Should handle invalid project path."""
        status = migrator.get_migration_status("")

        # Should return defaults without crashing
        assert "project_path" in status
        # Empty string is not a valid path, so migration_needed is False
        assert status["migration_needed"] is False


# ============================================================================
# Test Helper Methods
# ============================================================================

class TestHelperMethods:
    """Tests for internal helper methods."""

    def test_count_files_in_index_dict(self, migrator):
        """Should count files in dict with 'files' key."""
        data = {"files": ["file1.py", "file2.py", "file3.py"]}
        count = migrator._count_files_in_index(data)
        assert count == 3

    def test_count_files_in_index_file_list(self, migrator):
        """Should count files in dict with 'file_list' key."""
        data = {"file_list": ["a.py", "b.py"]}
        count = migrator._count_files_in_index(data)
        assert count == 2

    def test_count_files_in_index_no_files_key(self, migrator):
        """Should count dict keys when no files key present."""
        data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        count = migrator._count_files_in_index(data)
        assert count == 3

    def test_count_files_in_index_non_dict(self, migrator):
        """Should return 0 for non-dict data."""
        count = migrator._count_files_in_index("not a dict")
        assert count == 0

    def test_compare_data_structures_equal(self, migrator):
        """Should return True for equal structures."""
        data1 = {"key": "value", "list": [1, 2, 3]}
        data2 = {"key": "value", "list": [1, 2, 3]}
        assert migrator._compare_data_structures(data1, data2) is True

    def test_compare_data_structures_not_equal(self, migrator):
        """Should return False for different structures."""
        data1 = {"key": "value1"}
        data2 = {"key": "value2"}
        assert migrator._compare_data_structures(data1, data2) is False

    def test_compare_data_structures_different_types(self, migrator):
        """Should return False for different types."""
        assert migrator._compare_data_structures({"key": "value"}, [1, 2, 3]) is False

    def test_compare_data_structures_nested(self, migrator):
        """Should compare nested structures correctly."""
        data1 = {"nested": {"key": "value"}, "list": [1, 2]}
        data2 = {"nested": {"key": "value"}, "list": [1, 2]}
        assert migrator._compare_data_structures(data1, data2) is True

    def test_create_backup(self, migrator, temp_pickle_file):
        """Should create backup with timestamp."""
        backup = migrator._create_backup(temp_pickle_file)

        assert backup.exists()
        assert backup.parent == temp_pickle_file.parent
        assert "backup" in backup.stem
        assert backup.suffix == PICKLE_EXT

        # Cleanup
        backup.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
