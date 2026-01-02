"""
Comprehensive Unit Tests for Phase 5: MCP Registry Tools

This test module provides comprehensive coverage for the Phase 5 MCP tools
that manage the project registry system.

Test Coverage:
- get_registry_status: Statistics and status reporting
- registry_health_check: Health verification for all projects
- registry_cleanup: Removal of invalid projects
- reindex_all_projects: Batch re-indexing with change detection
- migrate_legacy_indexes: Pickle to MessagePack migration
- detect_orphaned_indexes: Orphan detection and recovery
- backup_registry: Registry backup creation

Testing Approach:
- Uses pytest fixtures for Context and registry mocking
- Uses unittest.mock for mocking dependencies
- Uses parametrize for testing multiple scenarios
- Includes docstrings explaining what each test covers
- Uses descriptive test names
- Tests both success and error cases
- Tests edge cases (empty registry, missing paths, etc.)
- Tests return value structure and content
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open, Mock
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
import sys

# Import the MCP tools to test
from src.code_index_mcp.server import (
    get_registry_status,
    registry_health_check,
    registry_cleanup,
    reindex_all_projects,
    migrate_legacy_indexes,
    detect_orphaned_indexes,
    backup_registry,
)
from mcp.server.fastmcp import Context


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_context() -> Context:
    """
    Create a mock MCP Context object for testing.

    The Context fixture provides a mock object that mimics the behavior of
    the real MCP Context, including the request_context and lifespan_context
    attributes that are accessed by the MCP tools.

    Yields:
        Context: A mock context object with proper structure
    """
    ctx = MagicMock(spec=Context)
    ctx.request_context = MagicMock()
    ctx.request_context.lifespan_context = MagicMock()
    return ctx


@pytest.fixture
def temp_registry_dir():
    """
    Create a temporary directory for registry testing.

    This fixture creates a temporary directory that can be used for
    testing registry operations without affecting the real registry.

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
def mock_project_info():
    """
    Create a mock ProjectInfo object for testing.

    Returns:
        MagicMock: Mock ProjectInfo with realistic data
    """
    project = MagicMock()
    project.id = 1
    project.path = "/path/to/project"
    project.path_hash = "abc123"
    project.indexed_at = datetime(2025, 1, 1, 12, 0, 0)
    project.file_count = 100
    project.config = {"test": "config"}
    project.stats = {"test": "stats"}
    project.index_location = "/path/to/project/.code-indexer/index"
    return project


@pytest.fixture
def mock_registry():
    """
    Create a mock ProjectRegistry for testing.

    Returns:
        MagicMock: Mock ProjectRegistry with common methods
    """
    registry = MagicMock()
    registry.db_path = Path("/tmp/test_registry.db")
    registry.list_all = MagicMock(return_value=[])
    registry.count = MagicMock(return_value=0)
    registry.get_by_path = MagicMock(return_value=None)
    registry.insert = MagicMock()
    registry.update = MagicMock()
    registry.delete = MagicMock(return_value=True)
    registry.exists = MagicMock(return_value=False)
    return registry


# =============================================================================
# TEST: get_registry_status
# =============================================================================

class TestGetRegistryStatus:
    """Tests for get_registry_status MCP tool."""

    @pytest.mark.asyncio
    async def test_get_status_empty_registry(self, mock_context, mock_registry):
        """Test get_registry_status with empty registry."""
        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            result = await get_registry_status(mock_context)

            assert result["success"] is True
            assert result["project_count"] == 0
            assert result["last_indexed"] is None
            assert result["oldest_project"] is None
            assert result["newest_project"] is None
            assert result["formats"]["msgpack"] == 0
            assert result["formats"]["pickle"] == 0

    @pytest.mark.asyncio
    async def test_get_status_with_projects(self, mock_context, mock_project_info):
        """Test get_registry_status with multiple projects."""
        mock_registry = MagicMock()
        mock_registry.db_path = Path("/tmp/test_registry.db")
        mock_registry.list_all = MagicMock(return_value=[mock_project_info])

        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            with patch("src.code_index_mcp.server.pathlib.Path.exists", return_value=True):
                with patch("src.code_index_mcp.server.pathlib.Path.rglob", return_value=[]):
                    result = await get_registry_status(mock_context)

                    assert result["success"] is True
                    assert result["project_count"] == 1
                    assert result["last_indexed"] == "2025-01-01T12:00:00"
                    assert result["oldest_project"] == "/path/to/project"
                    assert result["newest_project"] == "/path/to/project"

    @pytest.mark.asyncio
    async def test_get_status_error_handling(self, mock_context):
        """Test get_registry_status error handling."""
        with patch("src.code_index_mcp.registry.ProjectRegistry", side_effect=Exception("DB error")):
            result = await get_registry_status(mock_context)

            assert result["success"] is False
            assert "error" in result


# =============================================================================
# TEST: registry_health_check
# =============================================================================

class TestRegistryHealthCheck:
    """Tests for registry_health_check MCP tool."""

    @pytest.mark.asyncio
    async def test_health_check_empty_registry(self, mock_context, mock_registry):
        """Test health check with empty registry."""
        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            result = await registry_health_check(mock_context)

            assert result["success"] is True
            assert result["overall_status"] == "healthy"
            assert result["message"] == "No projects in registry"
            assert result["summary"]["healthy"] == 0
            assert result["summary"]["warning"] == 0
            assert result["summary"]["critical"] == 0

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, mock_context, mock_project_info):
        """Test health check with all healthy projects."""
        mock_registry = MagicMock()
        mock_registry.list_all = MagicMock(return_value=[mock_project_info])

        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            with patch("src.code_index_mcp.server.pathlib.Path.exists", return_value=True):
                with patch("src.code_index_mcp.server.pathlib.Path.rglob", return_value=[]):
                    # Patch MessagePackSerializer import inside the function
                    with patch("src.code_index_mcp.registry.msgpack_serializer.MessagePackSerializer") as MockSerializer:
                        mock_serializer = Mock()
                        mock_serializer.validate_index_file = Mock(return_value=(True, None))
                        MockSerializer.return_value = mock_serializer

                        result = await registry_health_check(mock_context)

                        assert result["success"] is True
                        # No index files found, so warning status
                        assert result["overall_status"] == "warning"
                        assert result["summary"]["warning"] == 1

    @pytest.mark.asyncio
    async def test_health_check_missing_path(self, mock_context, mock_project_info):
        """Test health check with missing project path."""
        mock_registry = MagicMock()
        mock_registry.list_all = MagicMock(return_value=[mock_project_info])

        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            with patch("src.code_index_mcp.server.pathlib.Path.exists", return_value=False):
                result = await registry_health_check(mock_context)

                assert result["success"] is True
                assert result["overall_status"] == "critical"
                assert result["summary"]["critical"] == 1
                assert "/path/to/project" in result["projects"]
                assert result["projects"]["/path/to/project"]["path_exists"] is False


# =============================================================================
# TEST: registry_cleanup
# =============================================================================

class TestRegistryCleanup:
    """Tests for registry_cleanup MCP tool."""

    @pytest.mark.asyncio
    async def test_cleanup_no_invalid_projects(self, mock_context, mock_registry):
        """Test cleanup when no invalid projects exist."""
        mock_registry.list_all = MagicMock(return_value=[])

        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            with patch("src.code_index_mcp.server.registry_health_check") as mock_health:
                mock_health.return_value = {
                    "success": True,
                    "projects": {},
                    "summary": {"healthy": 0, "warning": 0, "critical": 0}
                }

                result = await registry_cleanup(mock_context)

                assert result["success"] is True
                assert result["removed_count"] == 0
                assert result["removed_projects"] == []

    @pytest.mark.asyncio
    async def test_cleanup_with_invalid_projects(self, mock_context):
        """Test cleanup removes invalid projects."""
        mock_registry = MagicMock()

        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            with patch("src.code_index_mcp.server.registry_health_check") as mock_health:
                mock_health.return_value = {
                    "success": True,
                    "projects": {
                        "/invalid/path": {
                            "status": "critical",
                            "path_exists": False
                        }
                    },
                    "summary": {"healthy": 0, "warning": 0, "critical": 1}
                }

                # Patch RegistryBackupManager import inside the function
                with patch("src.code_index_mcp.registry.RegistryBackupManager") as MockBackupMgr:
                    mock_backup_mgr = Mock()
                    mock_backup_metadata = Mock()
                    mock_backup_metadata.backup_path = Path("/backup.db")
                    # Make create_backup_async return a coroutine
                    async def mock_create_backup_async(*args, **kwargs):
                        return mock_backup_metadata
                    mock_backup_mgr.create_backup_async = mock_create_backup_async
                    MockBackupMgr.return_value = mock_backup_mgr

                    mock_registry.delete.return_value = True

                    result = await registry_cleanup(mock_context)

                    assert result["success"] is True
                    assert result["removed_count"] == 1
                    assert "/invalid/path" in result["removed_projects"]

    @pytest.mark.asyncio
    async def test_cleanup_with_force(self, mock_context):
        """Test cleanup respects force flag."""
        with patch("src.code_index_mcp.server.registry_health_check") as mock_health:
            mock_health.return_value = {
                "success": True,
                "projects": {},
                "summary": {"healthy": 0, "warning": 0, "critical": 0}
            }

            result = await registry_cleanup(mock_context, force=True)

            assert result["success"] is True


# =============================================================================
# TEST: reindex_all_projects
# =============================================================================

class TestReindexAllProjects:
    """Tests for reindex_all_projects MCP tool."""

    @pytest.mark.asyncio
    async def test_reindex_empty_registry(self, mock_context, mock_registry):
        """Test reindex with empty registry."""
        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            result = await reindex_all_projects(mock_context)

            assert result["success"] is True
            assert result["total_projects"] == 0
            assert result["reindexed_count"] == 0
            assert result["skipped_count"] == 0

    @pytest.mark.asyncio
    async def test_reindex_dry_run(self, mock_context, mock_project_info):
        """Test reindex in dry-run mode."""
        mock_registry = MagicMock()
        mock_registry.list_all = MagicMock(return_value=[mock_project_info])

        # Patch ProjectRegistry import inside the function
        # Using force=True with dry_run=True to bypass file change detection
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            with patch("src.code_index_mcp.server.pathlib.Path.exists", return_value=True):
                with patch("src.code_index_mcp.server.manage_project") as mock_index:
                    mock_index.return_value = {"success": True}

                    result = await reindex_all_projects(mock_context, dry_run=True, force=True)

                    assert result["success"] is True
                    assert result["dry_run"] is True
                    assert result["reindexed_count"] == 1
                    assert result["results"][0]["reason"] == "dry_run"

    @pytest.mark.asyncio
    async def test_reindex_force(self, mock_context, mock_project_info):
        """Test reindex with force flag."""
        mock_registry = MagicMock()
        mock_registry.list_all = MagicMock(return_value=[mock_project_info])
        mock_registry.update = MagicMock()

        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            with patch("src.code_index_mcp.server.pathlib.Path.exists", return_value=True):
                with patch("src.code_index_mcp.server.manage_project") as mock_index:
                    mock_index.return_value = {"success": True}

                    result = await reindex_all_projects(mock_context, force=True)

                    assert result["success"] is True
                    assert result["reindexed_count"] == 1
                    assert result["results"][0]["reason"] == "reindexed"


# =============================================================================
# TEST: migrate_legacy_indexes
# =============================================================================

class TestMigrateLegacyIndexes:
    """Tests for migrate_legacy_indexes MCP tool."""

    @pytest.mark.asyncio
    async def test_migrate_no_legacy_indexes(self, mock_context):
        """Test migration when no legacy indexes exist."""
        # Patch IndexMigrator import inside the function
        with patch("src.code_index_mcp.registry.IndexMigrator") as MockMigrator:
            mock_instance = Mock()
            mock_instance.detect_legacy_indexes.return_value = []
            MockMigrator.return_value = mock_instance

            result = await migrate_legacy_indexes(mock_context)

            assert result["success"] is True
            assert result["migrated_count"] == 0
            assert result["message"] == "No legacy pickle indexes found"

    @pytest.mark.asyncio
    async def test_migrate_success(self, mock_context):
        """Test successful migration."""
        # Patch IndexMigrator import inside the function
        with patch("src.code_index_mcp.registry.IndexMigrator") as MockMigrator:
            mock_instance = Mock()
            mock_pickle_files = [Path("/index1.pickle"), Path("/index2.pickle")]
            mock_instance.detect_legacy_indexes.return_value = mock_pickle_files

            # Mock migration results
            mock_result1 = Mock()
            mock_result1.success = True
            mock_result1.source_path = Path("/index1.pickle")
            mock_result1.target_path = Path("/index1.msgpack")
            mock_result1.backup_path = Path("/backup1.pickle")
            mock_result1.error_message = None
            mock_result1.duration_seconds = 1.5

            mock_result2 = Mock()
            mock_result2.success = True
            mock_result2.source_path = Path("/index2.pickle")
            mock_result2.target_path = Path("/index2.msgpack")
            mock_result2.backup_path = Path("/backup2.pickle")
            mock_result2.error_message = None
            mock_result2.duration_seconds = 2.0

            mock_instance.migrate_index.side_effect = [mock_result1, mock_result2]
            MockMigrator.return_value = mock_instance

            result = await migrate_legacy_indexes(mock_context)

            assert result["success"] is True
            assert result["migrated_count"] == 2
            assert result["failed_count"] == 0
            assert len(result["results"]) == 2


# =============================================================================
# TEST: detect_orphaned_indexes
# =============================================================================

class TestDetectOrphanedIndexes:
    """Tests for detect_orphaned_indexes MCP tool."""

    @pytest.mark.asyncio
    async def test_detect_no_orphans(self, mock_context):
        """Test orphan detection when no orphans exist."""
        # Patch OrphanDetector import inside the function
        with patch("src.code_index_mcp.registry.OrphanDetector") as MockDetector:
            mock_instance = Mock()
            mock_instance.scan_for_orphans.return_value = []
            MockDetector.return_value = mock_instance

            result = await detect_orphaned_indexes(mock_context)

            assert result["success"] is True
            assert result["orphan_count"] == 0
            assert result["orphans"] == []
            assert result["message"] == "No orphaned indexes found"

    @pytest.mark.asyncio
    async def test_detect_with_orphans(self, mock_context):
        """Test orphan detection with orphans found."""
        # Patch OrphanDetector import inside the function
        with patch("src.code_index_mcp.registry.OrphanDetector") as MockDetector:
            mock_instance = Mock()

            # Create mock orphan
            mock_orphan = Mock()
            mock_orphan.path = "/orphan/project"
            mock_orphan.index_location = "/orphan/project/.code-indexer/index"
            mock_orphan.index_exists = True
            mock_orphan.index_size = 1000
            mock_orphan.last_modified = datetime(2025, 1, 1, 12, 0, 0)
            mock_orphan.reason = "Not registered"

            mock_instance.scan_for_orphans.return_value = [mock_orphan]
            mock_instance.suggest_actions.return_value = {
                "register": ["/orphan/project"],
                "cleanup": []
            }
            MockDetector.return_value = mock_instance

            result = await detect_orphaned_indexes(mock_context)

            assert result["success"] is True
            assert result["orphan_count"] == 1
            assert len(result["orphans"]) == 1
            assert result["orphans"][0]["path"] == "/orphan/project"
            assert "/orphan/project" in result["suggestions"]["register"]


# =============================================================================
# TEST: backup_registry
# =============================================================================

class TestBackupRegistry:
    """Tests for backup_registry MCP tool."""

    @pytest.mark.asyncio
    async def test_backup_success(self, mock_context):
        """Test successful backup creation."""
        mock_registry = MagicMock()
        mock_registry.count = MagicMock(return_value=5)

        # Patch ProjectRegistry import inside the function
        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            # Patch RegistryBackupManager import inside the function
            with patch("src.code_index_mcp.registry.RegistryBackupManager") as MockBackupMgr:
                mock_instance = Mock()

                mock_metadata = Mock()
                mock_metadata.backup_path = Path("/backup/registry_20250101_120000.db")
                mock_metadata.project_count = 5
                mock_metadata.timestamp = datetime(2025, 1, 1, 12, 0, 0)
                mock_metadata.backup_size_bytes = 1024
                mock_metadata.checksum = "abc123"

                mock_instance.create_backup.return_value = mock_metadata
                MockBackupMgr.return_value = mock_instance

                result = await backup_registry(mock_context)

                assert result["success"] is True
                assert result["backup_path"] == "/backup/registry_20250101_120000.db"
                assert result["project_count"] == 5
                assert result["timestamp"] == "2025-01-01T12:00:00"

    @pytest.mark.asyncio
    async def test_backup_error_handling(self, mock_context):
        """Test backup error handling."""
        with patch("src.code_index_mcp.registry.ProjectRegistry", side_effect=Exception("DB error")):
            result = await backup_registry(mock_context)

            assert result["success"] is False
            assert "error" in result


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_registry_corrupted(self, mock_context):
        """Test behavior when registry is corrupted."""
        with patch("src.code_index_mcp.registry.ProjectRegistry", side_effect=Exception("Corrupted")):
            result = await get_registry_status(mock_context)

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_permission_denied(self, mock_context):
        """Test behavior when permission is denied."""
        mock_registry = MagicMock()
        mock_registry.list_all = MagicMock(side_effect=PermissionError("Denied"))

        with patch("src.code_index_mcp.registry.ProjectRegistry", return_value=mock_registry):
            result = await get_registry_status(mock_context)

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_disk_full(self, mock_context):
        """Test behavior when disk is full."""
        with patch("src.code_index_mcp.registry.ProjectRegistry") as MockRegistry:
            mock_instance = Mock()
            MockRegistry.return_value = mock_instance

            # Patch RegistryBackupManager import inside the function
            with patch("src.code_index_mcp.registry.RegistryBackupManager") as MockBackupMgr:
                mock_backup_instance = Mock()
                mock_backup_instance.create_backup.side_effect = OSError("No space left")
                MockBackupMgr.return_value = mock_backup_instance

                result = await backup_registry(mock_context)

                assert result["success"] is False
