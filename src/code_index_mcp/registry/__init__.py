"""
Meta-Registry Module for Code Indexer.

This module provides the project registry infrastructure for managing
indexed projects across the system. It includes:

- ProjectRegistry: SQLite-based project registry with metadata tracking
- MessagePackSerializer: Binary serialization for index data with migration support
- IndexMigrator: Migration utilities from pickle to MessagePack format
- StartupMigrationManager: Automatic migration on server startup
- Directory utilities: Global and per-project directory management

Phase 1: Foundation - Registry and MessagePack Infrastructure
Phase 3: Migration - Pickle to MessagePack migration
Track: meta-registry_20250101
Target Version: v2.1.0
"""

from .project_registry import ProjectRegistry, ProjectInfo
from .msgpack_serializer import MessagePackSerializer, FormatType
from .index_migrator import (
    IndexMigrator,
    MigrationStatus,
    MigrationResult,
)
from .startup_migration import (
    StartupMigrationManager,
    MigrationState,
    check_and_migrate_on_startup,
    migrate_project_on_access,
)
from .directories import (
    get_global_registry_dir,
    get_project_registry_dir,
    get_project_index_dir,
    ensure_directories,
)

__all__ = [
    "ProjectRegistry",
    "ProjectInfo",
    "MessagePackSerializer",
    "FormatType",
    "IndexMigrator",
    "MigrationStatus",
    "MigrationResult",
    "StartupMigrationManager",
    "MigrationState",
    "check_and_migrate_on_startup",
    "migrate_project_on_access",
    "get_global_registry_dir",
    "get_project_registry_dir",
    "get_project_index_dir",
    "ensure_directories",
]
