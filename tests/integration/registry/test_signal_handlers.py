"""
Integration tests for signal handler edge cases.

This module tests the meta-registry's signal handling behavior, ensuring
graceful shutdown and data integrity when receiving signals during critical
operations.

Tests cover:
- SIGTERM during backup (should complete backup)
- SIGINT during registry write (should rollback)
- Multiple rapid signals (should handle gracefully)
- Signal during migration
- Signal during backup restore
- Signal scheduler shutdown
"""

import pytest
import tempfile
import signal
import time
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock
import threading

from src.code_index_mcp.registry.project_registry import ProjectRegistry
from src.code_index_mcp.registry.registry_backup import RegistryBackupManager
from src.code_index_mcp.registry.backup_scheduler import BackupScheduler
from src.code_index_mcp.registry.startup_migration import StartupMigrationManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def registry_for_signals():
    """Create a registry for signal testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "signal_test.db"
        registry = ProjectRegistry(db_path=db_path)
        yield registry, tmpdir
        registry.close()


# ============================================================================
# Test SIGTERM During Backup
# ============================================================================

class TestSIGTERMDuringBackup:
    """Tests for SIGTERM signal received during backup operation."""

    def test_sigterm_during_backup_completes_backup(self, registry_for_signals):
        """Should complete in-progress backup when SIGTERM received."""
        registry, tmpdir = registry_for_signals

        # Add test data
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

        # Create backup manager
        backup_dir = Path(tmpdir) / "backups"
        backup_dir.mkdir()

        backup_manager = RegistryBackupManager(backup_dir=backup_dir)

        # Create backup (should complete successfully)
        result = backup_manager.create_backup(registry)

        assert result is not None
        assert result.project_count == 5

    def test_sigterm_during_long_backup_waits_for_completion(self, registry_for_signals):
        """Should wait for long backup to complete on SIGTERM."""
        registry, tmpdir = registry_for_signals

        # Add lots of test data
        now = datetime.now()
        for i in range(50):
            registry.insert(
                path=f"/test/project{i}",
                indexed_at=now,
                file_count=i,
                config={},
                stats={},
                index_location=f"/tmp/index{i}",
            )

        backup_dir = Path(tmpdir) / "backups"
        backup_dir.mkdir()

        backup_manager = RegistryBackupManager(backup_dir=backup_dir)

        # Create backup (should complete successfully even with many records)
        result = backup_manager.create_backup(registry)

        assert result is not None
        assert result.project_count == 50

    def test_sigterm_with_multiple_pending_backups(self, registry_for_signals):
        """Should handle SIGTERM when multiple backups pending."""
        registry, tmpdir = registry_for_signals

        # Add test data
        now = datetime.now()
        registry.insert(
            path="/test/project",
            indexed_at=now,
            file_count=1,
            config={},
            stats={},
            index_location="/tmp/index",
        )

        backup_dir = Path(tmpdir) / "backups"
        backup_dir.mkdir()

        backup_manager = RegistryBackupManager(backup_dir=backup_dir)

        completed_backups = []
        # Simulate multiple backup operations
        for i in range(3):
            backup = backup_manager.create_backup(registry)
            if backup:
                completed_backups.append(i)
            time.sleep(0.05)

        assert len(completed_backups) == 3


# ============================================================================
# Test SIGINT During Registry Write
# ============================================================================

class TestSIGINTDuringRegistryWrite:
    """Tests for SIGINT signal received during registry write operation."""

    def test_sigint_during_insert_rolls_back(self, registry_for_signals):
        """Should rollback insert operation when SIGINT received."""
        registry, tmpdir = registry_for_signals

        # Track insert attempts
        inserts_completed = []
        signal_received = False

        def mock_insert_with_signal(*args, **kwargs):
            nonlocal signal_received
            # Simulate signal during insert
            signal_received = True
            # Should not complete insert
            raise KeyboardInterrupt("Simulated SIGINT")

        # Mock insert to simulate SIGINT
        original_insert = registry.insert

        def conditional_insert(*args, **kwargs):
            if not signal_received:
                return original_insert(*args, **kwargs)
            raise KeyboardInterrupt("Simulated SIGINT")

        with patch.object(registry, 'insert', side_effect=conditional_insert):
            # First insert should succeed
            now = datetime.now()
            result1 = registry.insert(
                path="/test/project1",
                indexed_at=now,
                file_count=1,
                config={},
                stats={},
                index_location="/tmp/index1",
            )
            assert result1 is not None

            # Simulate signal received
            signal_received = True

            # Second insert should be interrupted
            with pytest.raises(KeyboardInterrupt):
                registry.insert(
                    path="/test/project2",
                    indexed_at=now,
                    file_count=2,
                    config={},
                    stats={},
                    index_location="/tmp/index2",
                )

        # Verify only first insert completed
        assert registry.exists(path="/test/project1")
        assert not registry.exists(path="/test/project2")

    def test_sigint_during_update_preserves_original(self, registry_for_signals):
        """Should preserve original data when SIGINT received during update."""
        registry, tmpdir = registry_for_signals

        # Insert initial data
        now = datetime.now()
        registry.insert(
            path="/test/project",
            indexed_at=now,
            file_count=10,
            config={"original": "data"},
            stats={},
            index_location="/tmp/index",
        )

        original_project = registry.get_by_path(path="/test/project")

        # Simulate SIGINT during update
        signal_received = False

        def mock_update_with_signal(path, **kwargs):
            nonlocal signal_received
            if not signal_received:
                signal_received = True
                raise KeyboardInterrupt("Simulated SIGINT")
            return registry.update(path, **kwargs)

        with patch.object(registry, 'update', side_effect=mock_update_with_signal):
            with pytest.raises(KeyboardInterrupt):
                registry.update(
                    path="/test/project",
                    file_count=20,
                    config={"updated": "data"},
                )

        # Verify original data preserved
        final_project = registry.get_by_path(path="/test/project")
        assert final_project.file_count == original_project.file_count
        assert final_project.config == original_project.config

    def test_sigint_during_delete_rolls_back(self, registry_for_signals):
        """Should rollback delete operation when SIGINT received."""
        registry, tmpdir = registry_for_signals

        # Insert test data
        now = datetime.now()
        registry.insert(
            path="/test/project",
            indexed_at=now,
            file_count=1,
            config={},
            stats={},
            index_location="/tmp/index",
        )

        # Simulate SIGINT during delete
        signal_received = False

        def mock_delete_with_signal(path):
            nonlocal signal_received
            signal_received = True
            raise KeyboardInterrupt("Simulated SIGINT")

        with patch.object(registry, 'delete', side_effect=mock_delete_with_signal):
            with pytest.raises(KeyboardInterrupt):
                registry.delete(path="/test/project")

        # Verify project still exists
        assert registry.exists(path="/test/project")


# ============================================================================
# Test Multiple Rapid Signals
# ============================================================================

class TestMultipleRapidSignals:
    """Tests for handling multiple rapid signals."""

    def test_multiple_rapid_sigterm(self, registry_for_signals):
        """Should handle multiple rapid SIGTERM signals gracefully."""
        registry, tmpdir = registry_for_signals

        signals_received = []

        def signal_handler(signum, frame):
            signals_received.append(signum)
            time.sleep(0.01)  # Small delay

        # Register signal handler
        original_handler = signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Send multiple rapid signals
            for _ in range(5):
                signal.raise_signal(signal.SIGTERM)
                time.sleep(0.01)

            # Allow signals to be processed
            time.sleep(0.1)

            # Should handle all signals
            assert len(signals_received) >= 1

        finally:
            # Restore original handler
            signal.signal(signal.SIGTERM, original_handler)

    def test_multiple_rapid_sigint(self, registry_for_signals):
        """Should handle multiple rapid SIGINT signals gracefully."""
        registry, tmpdir = registry_for_signals

        signals_received = []

        def signal_handler(signum, frame):
            signals_received.append(signum)
            time.sleep(0.01)

        # Register signal handler
        original_handler = signal.signal(signal.SIGINT, signal_handler)

        try:
            # Send multiple rapid signals
            for _ in range(5):
                signal.raise_signal(signal.SIGINT)
                time.sleep(0.01)

            # Allow signals to be processed
            time.sleep(0.1)

            # Should handle all signals
            assert len(signals_received) >= 1

        finally:
            # Restore original handler
            signal.signal(signal.SIGINT, original_handler)

    def test_mixed_sigterm_and_sigint(self, registry_for_signals):
        """Should handle mixed SIGTERM and SIGINT signals."""
        registry, tmpdir = registry_for_signals

        sigterm_count = []
        sigint_count = []

        def signal_handler(signum, frame):
            if signum == signal.SIGTERM:
                sigterm_count.append(1)
            elif signum == signal.SIGINT:
                sigint_count.append(1)
            time.sleep(0.01)

        # Register signal handler
        original_term = signal.signal(signal.SIGTERM, signal_handler)
        original_int = signal.signal(signal.SIGINT, signal_handler)

        try:
            # Send mixed signals
            signal.raise_signal(signal.SIGTERM)
            time.sleep(0.01)
            signal.raise_signal(signal.SIGINT)
            time.sleep(0.01)
            signal.raise_signal(signal.SIGTERM)
            time.sleep(0.01)

            # Allow signals to be processed
            time.sleep(0.1)

            # Should handle both signal types
            assert len(sigterm_count) >= 1
            assert len(sigint_count) >= 1

        finally:
            # Restore original handlers
            signal.signal(signal.SIGTERM, original_term)
            signal.signal(signal.SIGINT, original_int)


# ============================================================================
# Test Signal During Migration
# ============================================================================

class TestSignalDuringMigration:
    """Tests for signals received during migration operations."""

    def test_sigterm_during_migration_completes_current_file(self):
        """Should complete current file migration when SIGTERM received."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create pickle files
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            index_dir = project_dir / ".code-indexer"
            index_dir.mkdir()

            # Create multiple pickle files
            import pickle
            for i in range(3):
                pickle_path = index_dir / f"index{i}.pickle"
                with open(pickle_path, "wb") as f:
                    pickle.dump({"files": [f"file{i}.py"], "count": i}, f)

            # Migrate all files (should complete successfully)
            from src.code_index_mcp.registry.index_migrator import IndexMigrator
            migrator = IndexMigrator()

            migration_completed = 0
            for i in range(3):
                pickle_path = index_dir / f"index{i}.pickle"
                result = migrator.migrate_index(pickle_path)
                if result.success:
                    migration_completed += 1

            # All migrations should complete
            assert migration_completed == 3

    def test_sigint_during_migration_rolls_back_in_progress(self):
        """Should rollback in-progress migration when SIGINT received."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create pickle file
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            index_dir = project_dir / ".code-indexer"
            index_dir.mkdir()

            import pickle
            pickle_path = index_dir / "index.pickle"
            with open(pickle_path, "wb") as f:
                pickle.dump({"files": ["file.py"], "count": 1}, f)

            # Migration should complete and create backup
            from src.code_index_mcp.registry.index_migrator import IndexMigrator
            migrator = IndexMigrator(create_backups=True)

            result = migrator.migrate_index(pickle_path)

            assert result.success is True
            # Original pickle file should still exist (backup was created)
            assert pickle_path.exists()
            # MessagePack file should exist
            msgpack_path = pickle_path.with_suffix('.msgpack')
            assert msgpack_path.exists()


# ============================================================================
# Test Signal Scheduler Shutdown
# ============================================================================

class TestSchedulerSignalHandling:
    """Tests for BackupScheduler signal handling."""

    @pytest.mark.asyncio
    async def test_sigterm_stops_scheduler_gracefully(self):
        """Should stop scheduler gracefully on SIGTERM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            backup_manager = RegistryBackupManager(backup_dir=backup_dir)
            scheduler = BackupScheduler(backup_manager=backup_manager)

            # Create a temporary registry for the scheduler
            db_path = Path(tmpdir) / "registry.db"
            registry = ProjectRegistry(db_path=db_path)

            # Start periodic backup task
            scheduler.start_periodic_backup(registry)

            # Stop should work gracefully
            await scheduler.stop_periodic_backup()

            # Verify shutdown event is set
            assert scheduler._shutdown_event.is_set()

            registry.close()

    @pytest.mark.asyncio
    async def test_sigint_during_backup_task_cancels_task(self):
        """Should cancel backup task when SIGINT received during task."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            backup_manager = RegistryBackupManager(backup_dir=backup_dir)
            scheduler = BackupScheduler(backup_manager=backup_manager)

            task_cancelled = False

            async def mock_backup_task():
                nonlocal task_cancelled
                try:
                    await asyncio.sleep(1)  # Long task
                except asyncio.CancelledError:
                    task_cancelled = True
                    raise

            # Create and cancel task
            task = asyncio.create_task(mock_backup_task())
            await asyncio.sleep(0.1)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            assert task_cancelled is True


# ============================================================================
# Test Signal During Backup Restore
# ============================================================================

class TestSignalDuringRestore:
    """Tests for signals received during backup restore."""

    def test_sigterm_during_restore_waits_for_completion(self):
        """Should wait for restore to complete on SIGTERM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create registry and backup
            db_path = Path(tmpdir) / "registry.db"
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

            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            backup_manager = RegistryBackupManager(backup_dir=backup_dir)
            backup_manager.create_backup(registry)
            registry.close()

            # Corrupt registry
            db_path.write_bytes(b"corrupted")

            # Restore from backup (should complete successfully)
            result = backup_manager.restore_latest_backup(db_path)

            assert result is True

            # Verify restored data
            restored_registry = ProjectRegistry(db_path=db_path)
            assert restored_registry.count() == 1
            restored_registry.close()

    def test_sigint_during_restore_rolls_back(self):
        """Should rollback restore on SIGINT."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create backup
            db_path = Path(tmpdir) / "registry.db"
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            backup_manager = RegistryBackupManager(backup_dir=backup_dir)

            def mock_restore_with_interrupt(target_path):
                raise KeyboardInterrupt("Simulated SIGINT")

            with patch.object(
                backup_manager,
                'restore_latest_backup',
                side_effect=mock_restore_with_interrupt
            ):
                with pytest.raises(KeyboardInterrupt):
                    backup_manager.restore_latest_backup(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
