"""
Registry Backup for the meta-registry system.

This module provides backup and restore functionality for the project registry,
ensuring data safety during cleanup operations and providing rollback capability.
"""

import shutil
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from .directories import get_global_registry_dir
from .project_registry import ProjectRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BackupMetadata:
    """
    Metadata about a registry backup.

    Attributes:
        backup_path: Path to the backup file
        original_path: Path to the original registry database
        timestamp: When the backup was created
        project_count: Number of projects in the registry at backup time
        backup_size_bytes: Size of the backup file in bytes
        checksum: SHA-256 checksum of the backup file
    """
    backup_path: Path
    original_path: Path
    timestamp: datetime
    project_count: int
    backup_size_bytes: int
    checksum: str

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with all fields
        """
        return {
            "backup_path": str(self.backup_path),
            "original_path": str(self.original_path),
            "timestamp": self.timestamp.isoformat(),
            "project_count": self.project_count,
            "backup_size_bytes": self.backup_size_bytes,
            "checksum": self.checksum,
        }


# ============================================================================
# Registry Backup Manager
# ============================================================================

class RegistryBackupManager:
    """
    Manager for creating and restoring registry backups.

    This class provides:
    - Backup creation with timestamp
    - Backup restoration
    - Backup verification
    - Automatic cleanup of old backups
    - Checksum computation for integrity verification

    Attributes:
        backup_dir: Directory where backups are stored
        max_backups: Maximum number of backups to keep (default: 10)
    """

    def __init__(
        self,
        backup_dir: Optional[str | Path] = None,
        max_backups: int = 10
    ):
        """
        Initialize the backup manager.

        Args:
            backup_dir: Directory for storing backups. If None, uses default.
            max_backups: Maximum number of backups to retain
        """
        if backup_dir is None:
            registry_dir = get_global_registry_dir()
            self.backup_dir = registry_dir / "backups"
        else:
            self.backup_dir = Path(backup_dir)

        self.max_backups = max_backups

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"RegistryBackupManager initialized (backup_dir={self.backup_dir}, "
            f"max_backups={max_backups})"
        )

    def create_backup(
        self,
        registry: Optional[ProjectRegistry] = None,
        registry_path: Optional[str | Path] = None
    ) -> BackupMetadata:
        """
        Create a backup of the registry database.

        Args:
            registry: ProjectRegistry instance. If None, registry_path must be provided.
            registry_path: Path to registry database. If None, uses default.

        Returns:
            BackupMetadata with backup details

        Raises:
            FileNotFoundError: If registry database doesn't exist
            IOError: If backup cannot be created
        """
        # Determine registry path
        if registry is not None:
            registry_path = registry.db_path
        elif registry_path is None:
            raise ValueError("Either registry or registry_path must be provided")
        else:
            registry_path = Path(registry_path)

        registry_path = Path(registry_path)

        # Check registry exists
        if not registry_path.exists():
            raise FileNotFoundError(f"Registry database not found: {registry_path}")

        # Generate backup filename with timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"registry_backup_{timestamp_str}.db"
        backup_path = self.backup_dir / backup_filename

        logger.info(f"Creating registry backup: {backup_path}")

        try:
            # Copy the database file
            shutil.copy2(registry_path, backup_path)

            # Get project count
            if registry is not None:
                project_count = registry.count()
            else:
                # Open temporary connection to get count
                conn = sqlite3.connect(registry_path)
                cursor = conn.execute("SELECT COUNT(*) FROM projects")
                project_count = cursor.fetchone()[0]
                conn.close()

            # Get backup size
            backup_size = backup_path.stat().st_size

            # Compute checksum
            checksum = self._compute_checksum(backup_path)

            metadata = BackupMetadata(
                backup_path=backup_path,
                original_path=registry_path,
                timestamp=datetime.now(),
                project_count=project_count,
                backup_size_bytes=backup_size,
                checksum=checksum
            )

            logger.info(
                f"Backup created successfully: {backup_path} "
                f"({project_count} projects, {backup_size} bytes)"
            )

            # Clean up old backups
            self._cleanup_old_backups()

            return metadata

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            # Clean up partial backup if it exists
            if backup_path.exists():
                backup_path.unlink()
            raise

    def restore_backup(
        self,
        backup_path: str | Path,
        registry_path: Optional[str | Path] = None,
        verify_before_restore: bool = True
    ) -> bool:
        """
        Restore a registry from backup.

        Args:
            backup_path: Path to the backup file
            registry_path: Path where to restore. If None, uses original path.
            verify_before_restore: Whether to verify backup before restoring

        Returns:
            True if restoration succeeded

        Raises:
            FileNotFoundError: If backup doesn't exist
            ValueError: If backup verification fails
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        logger.info(f"Restoring registry from backup: {backup_path}")

        # Verify backup if requested
        if verify_before_restore:
            if not self.verify_backup(backup_path):
                raise ValueError(f"Backup verification failed: {backup_path}")

        # Determine registry path
        if registry_path is None:
            # Try to determine from backup metadata
            registry_path = self._get_original_path_from_backup(backup_path)
            if registry_path is None:
                raise ValueError(
                    "Cannot determine registry path. "
                    "Please specify registry_path parameter."
                )

        registry_path = Path(registry_path)

        try:
            # Create backup of current registry before restoring
            if registry_path.exists():
                safety_backup = self._create_safety_backup(registry_path)
                logger.info(f"Created safety backup: {safety_backup}")

            try:
                # Copy backup to registry location
                shutil.copy2(backup_path, registry_path)

                logger.info(f"Registry restored successfully: {registry_path}")
                return True

            except Exception as e:
                # Restore from safety backup if restoration failed
                logger.error(f"Restoration failed: {e}. Attempting rollback...")
                if safety_backup and safety_backup.exists():
                    shutil.copy2(safety_backup, registry_path)
                    logger.info("Rolled back to pre-restoration state")
                raise

        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            raise

    def verify_backup(self, backup_path: str | Path) -> bool:
        """
        Verify a backup file for integrity.

        Args:
            backup_path: Path to the backup file

        Returns:
            True if backup is valid

        Raises:
            FileNotFoundError: If backup doesn't exist
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        logger.info(f"Verifying backup: {backup_path}")

        try:
            # Check file is readable
            if not backup_path.is_file():
                logger.error(f"Backup is not a file: {backup_path}")
                return False

            # Check file size
            if backup_path.stat().st_size == 0:
                logger.error(f"Backup file is empty: {backup_path}")
                return False

            # Try to open as SQLite database
            conn = sqlite3.connect(backup_path)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            # Check for required tables
            required_tables = {"projects", "registry_metadata"}
            if not required_tables.issubset(set(tables)):
                logger.error(f"Backup missing required tables: {backup_path}")
                return False

            logger.info(f"Backup verified successfully: {backup_path}")
            return True

        except sqlite3.Error as e:
            logger.error(f"Backup verification failed (SQLite error): {e}")
            return False
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def list_backups(self) -> list[BackupMetadata]:
        """
        List all available backups.

        Returns:
            List of BackupMetadata objects, sorted by timestamp (newest first)
        """
        backups = []

        for backup_file in self.backup_dir.glob("registry_backup_*.db"):
            try:
                # Extract timestamp from filename
                stem = backup_file.stem  # e.g., "registry_backup_20250101_120000"
                timestamp_str = stem.replace("registry_backup_", "")
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                # Get file size
                backup_size = backup_file.stat().st_size

                # Compute checksum
                checksum = self._compute_checksum(backup_file)

                # Get project count (from database)
                conn = sqlite3.connect(backup_file)
                cursor = conn.execute("SELECT COUNT(*) FROM projects")
                project_count = cursor.fetchone()[0]
                conn.close()

                metadata = BackupMetadata(
                    backup_path=backup_file,
                    original_path=Path(),  # Unknown
                    timestamp=timestamp,
                    project_count=project_count,
                    backup_size_bytes=backup_size,
                    checksum=checksum
                )
                backups.append(metadata)

            except Exception as e:
                logger.warning(f"Error reading backup {backup_file}: {e}")
                continue

        # Sort by timestamp, newest first
        backups.sort(key=lambda b: b.timestamp, reverse=True)

        logger.info(f"Found {len(backups)} backups")
        return backups

    def delete_backup(self, backup_path: str | Path) -> bool:
        """
        Delete a backup file.

        Args:
            backup_path: Path to the backup to delete

        Returns:
            True if deleted successfully
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            logger.warning(f"Backup file not found: {backup_path}")
            return False

        try:
            backup_path.unlink()
            logger.info(f"Deleted backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_path}: {e}")
            return False

    # ------------------------------------------------------------------------
    # Private Methods
    # ------------------------------------------------------------------------

    def _compute_checksum(self, file_path: Path) -> str:
        """
        Compute SHA-256 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hexadecimal checksum string
        """
        import hashlib

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _cleanup_old_backups(self) -> None:
        """
        Remove old backups, keeping only the most recent max_backups.
        """
        backups = self.list_backups()

        if len(backups) <= self.max_backups:
            return

        # Remove oldest backups
        to_remove = backups[self.max_backups:]
        logger.info(f"Cleaning up {len(to_remove)} old backups")

        for backup in to_remove:
            try:
                self.delete_backup(backup.backup_path)
            except Exception as e:
                logger.warning(f"Failed to delete old backup {backup.backup_path}: {e}")

    def _create_safety_backup(self, registry_path: Path) -> Optional[Path]:
        """
        Create a safety backup before operations.

        Args:
            registry_path: Path to the registry file

        Returns:
            Path to safety backup, or None if creation failed
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safety_backup = self.backup_dir / f"safety_backup_{timestamp_str}.db"

        try:
            shutil.copy2(registry_path, safety_backup)
            return safety_backup
        except Exception as e:
            logger.error(f"Failed to create safety backup: {e}")
            return None

    def _get_original_path_from_backup(self, backup_path: Path) -> Optional[Path]:
        """
        Try to determine the original registry path from a backup.

        This is a best-effort operation - it may not always be possible
        to determine the original path.

        Args:
            backup_path: Path to the backup file

        Returns:
            Original path if determinable, None otherwise
        """
        # We can't reliably determine this from just the backup file
        # Return None to indicate caller should specify the path
        return None
