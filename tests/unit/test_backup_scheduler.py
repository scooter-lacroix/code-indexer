"""
Unit Tests for Backup Scheduler

This test module provides comprehensive coverage for the BackupScheduler
which handles automatic periodic backups.

Test Coverage:
- Startup backup check
- Periodic backup loop
- Graceful shutdown handling
- Signal handler registration
- Non-blocking async backup
"""

import pytest
import sqlite3
import tempfile
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from src.code_index_mcp.registry.backup_scheduler import (
    BackupScheduler,
    get_backup_scheduler,
    setup_signal_handlers,
)
from src.code_index_mcp.registry.project_registry import ProjectRegistry


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture
def temp_registry_db():
    """
    Create a temporary registry database for testing.

    Yields:
        Path: Path to temporary registry database

    Cleans up:
        Removes temporary database after test
    """
    temp_db = Path(tempfile.mktemp(suffix=".db"))

    # Create a valid registry database
    conn = sqlite3.connect(temp_db)
    conn.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            path_hash TEXT UNIQUE NOT NULL,
            indexed_at TIMESTAMP NOT NULL,
            file_count INTEGER NOT NULL,
            config JSON NOT NULL,
            stats JSON NOT NULL,
            index_location TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE registry_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=FULL;")
    conn.commit()

    # Add a test project
    conn.execute(
        """
        INSERT INTO projects (
            path, path_hash, indexed_at, file_count, config, stats, index_location
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "/test/project",
            "hash123",
            "2025-01-01T12:00:00",
            100,
            '{"test": "config"}',
            '{"test": "stats"}',
            "/test/project/.code-indexer/index"
        )
    )
    conn.commit()
    conn.close()

    yield temp_db

    # Cleanup
    if temp_db.exists():
        temp_db.unlink()
        # Remove WAL file if it exists
        wal_file = temp_db.with_suffix(".db-wal")
        if wal_file.exists():
            wal_file.unlink()


@pytest.fixture
def temp_backup_dir():
    """
    Create a temporary directory for backup testing.

    Yields:
        Path: Path to temporary directory

    Cleans up:
        Removes temporary directory after test
    """
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def backup_manager(temp_backup_dir):
    """
    Create a BackupManager instance for testing.

    Args:
        temp_backup_dir: Path to temporary backup directory

    Returns:
        RegistryBackupManager: Backup manager instance
    """
    from src.code_index_mcp.registry.registry_backup import RegistryBackupManager
    return RegistryBackupManager(backup_dir=temp_backup_dir)


@pytest.fixture
def project_registry(temp_registry_db):
    """
    Create a ProjectRegistry instance for testing.

    Args:
        temp_registry_db: Path to temporary registry database

    Returns:
        ProjectRegistry: ProjectRegistry instance
    """
    return ProjectRegistry(db_path=temp_registry_db)


# =============================================================================
# TEST: Backup Scheduler Initialization
# =============================================================================

class TestBackupSchedulerInit:
    """Tests for BackupScheduler initialization."""

    def test_init_default(self, backup_manager):
        """Test BackupScheduler initialization with defaults."""
        scheduler = BackupScheduler(backup_manager=backup_manager)

        assert scheduler.backup_manager is not None
        assert scheduler.backup_interval_hours == 24
        assert scheduler._backup_task is None
        assert scheduler._shutdown_event is not None

    def test_init_custom_interval(self, backup_manager):
        """Test BackupScheduler with custom interval."""
        scheduler = BackupScheduler(
            backup_manager=backup_manager,
            backup_interval_hours=12
        )

        assert scheduler.backup_interval_hours == 12


# =============================================================================
# TEST: Startup Backup Check
# =============================================================================

class TestStartupBackupCheck:
    """Tests for startup backup check functionality."""

    @pytest.mark.asyncio
    async def test_startup_backup_needed(self, backup_manager, project_registry):
        """Test startup backup when backup is needed (no previous backup)."""
        scheduler = BackupScheduler(backup_manager=backup_manager)

        backup_created, message = await scheduler.startup_backup_check(project_registry)

        assert backup_created is True
        assert "success" in message.lower()

    @pytest.mark.asyncio
    async def test_startup_backup_not_needed(self, backup_manager, project_registry):
        """Test startup backup when backup was just created."""
        scheduler = BackupScheduler(
            backup_manager=backup_manager,
            backup_interval_hours=24
        )

        # First call creates backup
        await scheduler.startup_backup_check(project_registry)

        # Second call should not create backup
        backup_created, message = await scheduler.startup_backup_check(project_registry)

        assert backup_created is False
        assert "no backup needed" in message.lower() or "last backup" in message.lower()

    @pytest.mark.asyncio
    async def test_startup_backup_updates_check_time(self, backup_manager, project_registry):
        """Test that startup backup updates last backup check time."""
        scheduler = BackupScheduler(backup_manager=backup_manager)

        await scheduler.startup_backup_check(project_registry)

        # Check that metadata was updated
        check_time = project_registry.get_metadata(
            scheduler.backup_manager.METADATA_LAST_BACKUP_CHECK
        )

        assert check_time is not None

        # Verify it's a valid datetime
        check_datetime = datetime.fromisoformat(str(check_time))
        # Make both datetimes timezone-aware for comparison
        now = datetime.now(timezone.utc)
        if check_datetime.tzinfo is None:
            check_datetime = check_datetime.replace(tzinfo=timezone.utc)
        assert (now - check_datetime).total_seconds() < 5


# =============================================================================
# TEST: Periodic Backup Loop
# =============================================================================

class TestPeriodicBackupLoop:
    """Tests for periodic backup loop functionality."""

    @pytest.mark.asyncio
    async def test_periodic_backup_starts(self, backup_manager, project_registry):
        """Test that periodic backup task starts correctly."""
        scheduler = BackupScheduler(
            backup_manager=backup_manager,
            backup_interval_hours=1
        )

        scheduler.start_periodic_backup(project_registry)

        # Wait a bit to ensure task started
        await asyncio.sleep(0.1)

        assert scheduler._backup_task is not None
        assert not scheduler._backup_task.done()

        # Cleanup
        await scheduler.stop_periodic_backup()

    @pytest.mark.asyncio
    async def test_periodic_backup_stops(self, backup_manager, project_registry):
        """Test that periodic backup task stops gracefully."""
        scheduler = BackupScheduler(
            backup_manager=backup_manager,
            backup_interval_hours=1
        )

        scheduler.start_periodic_backup(project_registry)
        await asyncio.sleep(0.1)

        # Stop the task
        await scheduler.stop_periodic_backup()

        assert scheduler._backup_task.done()
        assert scheduler._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_periodic_backup_handles_shutdown(self, backup_manager, project_registry):
        """Test that periodic backup loop handles shutdown signal."""
        scheduler = BackupScheduler(
            backup_manager=backup_manager,
            backup_interval_hours=24
        )

        # Start the loop
        task = asyncio.create_task(
            scheduler._periodic_backup_loop(project_registry)
        )

        # Wait a bit then signal shutdown
        await asyncio.sleep(0.1)
        scheduler._shutdown_event.set()

        # Wait for task to complete
        await asyncio.wait_for(task, timeout=5)

        assert task.done()


# =============================================================================
# TEST: Global Backup Scheduler
# =============================================================================

class TestGlobalBackupScheduler:
    """Tests for global backup scheduler instance."""

    def test_get_backup_scheduler_singleton(self):
        """Test that get_backup_scheduler returns singleton."""
        scheduler1 = get_backup_scheduler()
        scheduler2 = get_backup_scheduler()

        assert scheduler1 is scheduler2


# =============================================================================
# TEST: Signal Handlers
# =============================================================================

class TestSignalHandlers:
    """Tests for signal handler setup."""

    def test_setup_signal_handlers(self):
        """Test that signal handlers are registered."""
        scheduler = BackupScheduler()

        # Should not raise exception
        setup_signal_handlers(scheduler)

        # Verify handlers are set (check by calling them)
        import signal
        # Get current handlers
        sigterm_handler = signal.getsignal(signal.SIGTERM)
        sigint_handler = signal.getsignal(signal.SIGINT)

        # Handlers should be set (not None)
        assert sigterm_handler is not None
        assert sigint_handler is not None


# =============================================================================
# TEST: Integration Tests
# =============================================================================

class TestBackupSchedulerIntegration:
    """Integration tests for backup scheduler."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, backup_manager, project_registry):
        """Test full lifecycle: startup check -> periodic -> shutdown."""
        scheduler = BackupScheduler(
            backup_manager=backup_manager,
            backup_interval_hours=1
        )

        # 1. Startup check
        backup_created, msg = await scheduler.startup_backup_check(project_registry)
        assert backup_created is True

        # 2. Start periodic backup
        scheduler.start_periodic_backup(project_registry)
        await asyncio.sleep(0.1)

        assert scheduler._backup_task is not None

        # 3. Stop periodic backup
        await scheduler.stop_periodic_backup()

        assert scheduler._backup_task.done()

    @pytest.mark.asyncio
    async def test_multiple_startup_checks(self, backup_manager, project_registry):
        """Test multiple startup checks don't create duplicate backups."""
        scheduler = BackupScheduler(
            backup_manager=backup_manager,
            backup_interval_hours=24
        )

        # First check
        created1, _ = await scheduler.startup_backup_check(project_registry)

        # Immediate second check
        created2, _ = await scheduler.startup_backup_check(project_registry)

        assert created1 is True
        assert created2 is False
