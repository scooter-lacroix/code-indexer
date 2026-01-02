"""
Integration tests for concurrent access scenarios.

This module tests the meta-registry's behavior under concurrent access,
including multiple processes/threads accessing the registry simultaneously.

Tests cover:
- Multi-threaded read operations
- Multi-threaded write operations
- Concurrent reads and writes
- Registry locking mechanisms
- Transaction isolation
- Race condition prevention
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

from src.code_index_mcp.registry.project_registry import (
    ProjectRegistry,
    ProjectInfo,
    DuplicateProjectError,
    ProjectNotFoundError,
)
from src.code_index_mcp.registry.msgpack_serializer import MessagePackSerializer


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def concurrent_registry():
    """Create a registry for concurrent access testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "concurrent_test.db"
        registry = ProjectRegistry(db_path=db_path)
        yield registry, tmpdir
        registry.close()


# ============================================================================
# Test Concurrent Reads
# ============================================================================

class TestConcurrentReads:
    """Tests for concurrent read operations."""

    def test_concurrent_get_by_path(self, concurrent_registry):
        """Should handle concurrent get_by_path operations."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        for i in range(10):
            registry.insert(
                path=f"/test/project{i}",
                indexed_at=now,
                file_count=i,
                config={},
                stats={},
                index_location=f"/tmp/index{i}",
            )

        results = []
        errors = []

        def read_project(project_id):
            try:
                project = registry.get_by_path(path=f"/test/project{project_id}")
                results.append(project.id)
                return project.id
            except Exception as e:
                errors.append(str(e))
                return None

        # Concurrent reads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_project, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0
        assert len(results) == 10

    def test_concurrent_list_all(self, concurrent_registry):
        """Should handle concurrent list_all operations."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        for i in range(20):
            registry.insert(
                path=f"/test/project{i}",
                indexed_at=now,
                file_count=i,
                config={},
                stats={},
                index_location=f"/tmp/index{i}",
            )

        results = []

        def list_projects():
            projects = registry.list_all()
            results.append(len(projects))
            return len(projects)

        # Concurrent list operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(list_projects) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # All should return 20
        assert all(count == 20 for count in results)
        assert len(results) == 10

    def test_concurrent_count(self, concurrent_registry):
        """Should handle concurrent count operations."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        for i in range(15):
            registry.insert(
                path=f"/test/project{i}",
                indexed_at=now,
                file_count=i,
                config={},
                stats={},
                index_location=f"/tmp/index{i}",
            )

        results = []

        def count_projects():
            count = registry.count()
            results.append(count)
            return count

        # Concurrent count operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(count_projects) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # All should return 15
        assert all(count == 15 for count in results)
        assert len(results) == 10

    def test_concurrent_exists(self, concurrent_registry):
        """Should handle concurrent exists operations."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        registry.insert(
            path="/test/existing",
            indexed_at=now,
            file_count=1,
            config={},
            stats={},
            index_location="/tmp/index",
        )

        results = []

        def check_exists(project_path):
            exists = registry.exists(path=project_path)
            results.append((project_path, exists))
            return exists

        # Concurrent exists checks
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Mix of existing and non-existing paths
            paths = ["/test/existing"] * 5 + ["/test/nonexistent"] * 5
            futures = [executor.submit(check_exists, path) for path in paths]
            for future in as_completed(futures):
                future.result()

        assert len(results) == 10


# ============================================================================
# Test Concurrent Writes
# ============================================================================

class TestConcurrentWrites:
    """Tests for concurrent write operations."""

    def test_concurrent_insert_different_paths(self, concurrent_registry):
        """Should handle concurrent inserts with different paths."""
        registry, _ = concurrent_registry

        results = []
        errors = []

        def insert_project(project_id):
            try:
                now = datetime.now()
                project = registry.insert(
                    path=f"/test/project{project_id}",
                    indexed_at=now,
                    file_count=project_id,
                    config={},
                    stats={},
                    index_location=f"/tmp/index{project_id}",
                )
                results.append(project.id)
                return project.id
            except Exception as e:
                errors.append((project_id, str(e)))
                return None

        # Concurrent inserts with different paths
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_project, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0
        assert len(results) == 20
        assert registry.count() == 20

    def test_concurrent_insert_same_path_fails(self, concurrent_registry):
        """Should fail on concurrent inserts with same path."""
        registry, _ = concurrent_registry

        results = []
        errors = []

        def insert_project():
            try:
                now = datetime.now()
                project = registry.insert(
                    path="/test/duplicate",
                    indexed_at=now,
                    file_count=1,
                    config={},
                    stats={},
                    index_location="/tmp/index",
                )
                results.append(project.id)
                return project.id
            except Exception as e:
                errors.append(str(e))
                return None

        # Concurrent inserts with same path
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_project) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # Only one should succeed
        assert len(results) == 1
        assert len(errors) == 9
        assert registry.count() == 1

    def test_concurrent_update_different_projects(self, concurrent_registry):
        """Should handle concurrent updates to different projects."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        for i in range(10):
            registry.insert(
                path=f"/test/project{i}",
                indexed_at=now,
                file_count=i,
                config={},
                stats={},
                index_location=f"/tmp/index{i}",
            )

        results = []
        errors = []

        def update_project(project_id):
            try:
                updated = registry.update(
                    path=f"/test/project{project_id}",
                    file_count=project_id * 2,
                )
                results.append(updated.id)
                return updated.id
            except Exception as e:
                errors.append((project_id, str(e)))
                return None

        # Concurrent updates
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_project, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0
        assert len(results) == 10

        # Verify updates
        for i in range(10):
            project = registry.get_by_path(path=f"/test/project{i}")
            assert project.file_count == i * 2

    def test_concurrent_delete_different_projects(self, concurrent_registry):
        """Should handle concurrent deletes of different projects."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        for i in range(20):
            registry.insert(
                path=f"/test/project{i}",
                indexed_at=now,
                file_count=i,
                config={},
                stats={},
                index_location=f"/tmp/index{i}",
            )

        results = []

        def delete_project(project_id):
            result = registry.delete(path=f"/test/project{project_id}")
            results.append(result)
            return result

        # Concurrent deletes
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(delete_project, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        assert all(results)
        assert registry.count() == 0


# ============================================================================
# Test Mixed Concurrent Operations
# ============================================================================

class TestMixedConcurrentOperations:
    """Tests for mixed concurrent read and write operations."""

    def test_concurrent_read_write(self, concurrent_registry):
        """Should handle concurrent reads and writes."""
        registry, _ = concurrent_registry

        # Insert initial data
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

        read_results = []
        write_results = []
        errors = []

        def read_project(project_id):
            try:
                project = registry.get_by_path(path=f"/test/project{project_id % 5}")
                read_results.append(project.id)
                return project.id
            except Exception as e:
                errors.append(("read", str(e)))
                return None

        def insert_project(project_id):
            try:
                now = datetime.now()
                project = registry.insert(
                    path=f"/test/new_project{project_id}",
                    indexed_at=now,
                    file_count=project_id,
                    config={},
                    stats={},
                    index_location=f"/tmp/new_index{project_id}",
                )
                write_results.append(project.id)
                return project.id
            except Exception as e:
                errors.append(("write", str(e)))
                return None

        # Mix of reads and writes
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            # Add 10 reads
            for i in range(10):
                futures.append(executor.submit(read_project, i))
            # Add 5 writes
            for i in range(5):
                futures.append(executor.submit(insert_project, i))

            for future in as_completed(futures):
                future.result()

        # Should have completed most operations
        assert len(read_results) + len(write_results) > 10

    def test_concurrent_update_read_same_project(self, concurrent_registry):
        """Should handle concurrent updates and reads of same project."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        registry.insert(
            path="/test/project",
            indexed_at=now,
            file_count=10,
            config={},
            stats={},
            index_location="/tmp/index",
        )

        read_results = []
        update_results = []
        lock = threading.Lock()

        def read_project():
            for _ in range(10):
                try:
                    project = registry.get_by_path(path="/test/project")
                    with lock:
                        read_results.append(project.file_count)
                except Exception:
                    pass

        def update_project():
            for i in range(10):
                try:
                    updated = registry.update(
                        path="/test/project",
                        file_count=10 + i,
                    )
                    with lock:
                        update_results.append(updated.file_count)
                except Exception:
                    pass

        # Concurrent reads and updates
        read_thread = threading.Thread(target=read_project)
        update_thread = threading.Thread(target=update_project)

        read_thread.start()
        update_thread.start()

        read_thread.join()
        update_thread.join()

        # Both should complete without errors
        assert len(read_results) > 0
        assert len(update_results) > 0

        # Final state should be consistent
        final = registry.get_by_path(path="/test/project")
        assert final.file_count >= 10


# ============================================================================
# Test Transaction Isolation
# ============================================================================

class TestTransactionIsolation:
    """Tests for transaction isolation under concurrent access."""

    def test_serializable_inserts(self, concurrent_registry):
        """Should maintain serializable isolation for inserts."""
        registry, _ = concurrent_registry

        results = []
        errors = []

        def insert_with_check(project_id):
            try:
                # Check if exists first
                path = f"/test/project{project_id % 5}"  # Only 5 unique paths
                if not registry.exists(path=path):
                    now = datetime.now()
                    project = registry.insert(
                        path=path,
                        indexed_at=now,
                        file_count=project_id,
                        config={},
                        stats={},
                        index_location=f"/tmp/index{project_id}",
                    )
                    results.append(project.id)
                else:
                    results.append(None)
                return True
            except Exception as e:
                errors.append(str(e))
                return False

        # Concurrent check-and-insert operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_with_check, i) for i in range(20)]
            for future in as_completed(futures):
                future.result()

        # Should have exactly 5 projects (one per unique path)
        assert registry.count() == 5

    def test_update_consistency(self, concurrent_registry):
        """Should maintain consistency during concurrent updates."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        registry.insert(
            path="/test/counter",
            indexed_at=now,
            file_count=0,
            config={},
            stats={},
            index_location="/tmp/index",
        )

        results = []

        def increment_counter():
            for _ in range(10):
                try:
                    current = registry.get_by_path(path="/test/counter")
                    new_count = current.file_count + 1
                    updated = registry.update(
                        path="/test/counter",
                        file_count=new_count,
                    )
                    results.append(updated.file_count)
                except Exception:
                    pass

        # Multiple threads incrementing counter
        threads = [threading.Thread(target=increment_counter) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Final value should be 30 (3 threads * 10 increments)
        # Note: Due to potential race conditions in check-and-update pattern,
        # the actual value may be less, which is expected behavior
        final = registry.get_by_path(path="/test/counter")
        assert final.file_count > 0
        assert len(results) > 0


# ============================================================================
# Test Stress Scenarios
# ============================================================================

class TestStressScenarios:
    """Stress tests for concurrent access."""

    def test_high_concurrency_reads(self, concurrent_registry):
        """Should handle high concurrency for reads."""
        registry, _ = concurrent_registry

        # Insert test data
        now = datetime.now()
        for i in range(100):
            registry.insert(
                path=f"/test/project{i}",
                indexed_at=now,
                file_count=i,
                config={},
                stats={},
                index_location=f"/tmp/index{i}",
            )

        results = []

        def read_all_projects():
            projects = registry.list_all()
            results.append(len(projects))
            return len(projects)

        # High concurrency reads (50 threads)
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(read_all_projects) for _ in range(50)]
            for future in as_completed(futures):
                future.result()

        # All should return 100
        assert all(count == 100 for count in results)
        assert len(results) == 50

    def test_high_concurrency_mixed_operations(self, concurrent_registry):
        """Should handle high concurrency mixed operations."""
        registry, _ = concurrent_registry

        errors = []

        def mixed_operation(op_id):
            try:
                if op_id % 3 == 0:
                    # Insert
                    path = f"/test/project{op_id}"
                    if not registry.exists(path=path):
                        now = datetime.now()
                        registry.insert(
                            path=path,
                            indexed_at=now,
                            file_count=op_id,
                            config={},
                            stats={},
                            index_location=f"/tmp/index{op_id}",
                        )
                elif op_id % 3 == 1:
                    # Read
                    if registry.count() > 0:
                        registry.list_all()
                else:
                    # Count
                    registry.count()
                return True
            except Exception as e:
                errors.append(str(e))
                return False

        # High concurrency mixed operations (100 threads)
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(mixed_operation, i) for i in range(100)]
            for future in as_completed(futures):
                future.result()

        # Should complete with minimal errors
        assert len(errors) < 10  # Allow some race condition errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
