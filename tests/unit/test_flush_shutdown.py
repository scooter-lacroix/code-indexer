"""
Unit tests for explicit flush before shutdown.

This module tests:
- DAL flush() method exists and works
- Settings storage backends have flush() methods
- SQLiteDAL flush() calls all underlying storage flush()
- Data is persisted after flush before close
"""

import os
import tempfile
import shutil
import pytest

from code_index_mcp.storage.sqlite_storage import SQLiteStorage, SQLiteFileMetadata, SQLiteDAL
from code_index_mcp.optimized_project_settings import OptimizedProjectSettings


class TestExplicitFlushBeforeShutdown:
    """Test explicit flush functionality before shutdown."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test databases."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_sqlite_storage_has_flush_method(self, temp_dir):
        """Test that SQLiteStorage has a flush method."""
        db_path = os.path.join(temp_dir, 'test_storage.db')
        storage = SQLiteStorage(db_path)

        assert hasattr(storage, 'flush'), "SQLiteStorage should have flush method"
        assert callable(storage.flush), "flush should be callable"

    def test_sqlite_storage_flush_succeeds(self, temp_dir):
        """Test that SQLiteStorage.flush() executes without error."""
        db_path = os.path.join(temp_dir, 'test_storage.db')
        storage = SQLiteStorage(db_path)

        # Add some data
        storage.put('test_key', 'test_value')

        # Flush should not raise
        try:
            storage.flush()
        except Exception as e:
            pytest.fail(f"flush() raised exception: {e}")

    def test_sqlite_file_metadata_has_flush_method(self, temp_dir):
        """Test that SQLiteFileMetadata has a flush method."""
        db_path = os.path.join(temp_dir, 'test_metadata.db')
        metadata = SQLiteFileMetadata(db_path)

        assert hasattr(metadata, 'flush'), "SQLiteFileMetadata should have flush method"
        assert callable(metadata.flush), "flush should be callable"

    def test_sqlite_file_metadata_flush_succeeds(self, temp_dir):
        """Test that SQLiteFileMetadata.flush() executes without error."""
        db_path = os.path.join(temp_dir, 'test_metadata.db')
        metadata = SQLiteFileMetadata(db_path)

        # Add a file
        metadata.add_file('test.py', 'file', '.py', {'size': 100})

        # Flush should not raise
        try:
            metadata.flush()
        except Exception as e:
            pytest.fail(f"flush() raised exception: {e}")

    def test_sqlite_dal_has_flush_method(self, temp_dir):
        """Test that SQLiteDAL has a flush method."""
        db_path = os.path.join(temp_dir, 'test_dal.db')
        dal = SQLiteDAL(db_path)

        assert hasattr(dal, 'flush'), "SQLiteDAL should have flush method"
        assert callable(dal.flush), "flush should be callable"

    def test_sqlite_dal_flush_calls_all_backends(self, temp_dir):
        """Test that SQLiteDAL.flush() calls flush on all underlying storage."""
        db_path = os.path.join(temp_dir, 'test_dal.db')
        dal = SQLiteDAL(db_path)

        # Add data to all backends
        dal.storage.put('test_key', 'test_value')
        dal.metadata.add_file('test.py', 'file', '.py')

        # Mock the flush methods to verify they're called
        original_storage_flush = dal._storage.flush
        original_metadata_flush = dal._metadata.flush

        call_count = {'storage': 0, 'metadata': 0}

        def mock_storage_flush():
            call_count['storage'] += 1
            return original_storage_flush()

        def mock_metadata_flush():
            call_count['metadata'] += 1
            return original_metadata_flush()

        dal._storage.flush = mock_storage_flush
        dal._metadata.flush = mock_metadata_flush

        # Call flush
        dal.flush()

        # Verify both were called
        assert call_count['storage'] == 1, "storage flush not called"
        assert call_count['metadata'] == 1, "metadata flush not called"

    def test_data_persisted_after_flush_before_close(self, temp_dir):
        """Test that data is persisted after flush before close."""
        db_path = os.path.join(temp_dir, 'test_persist.db')
        storage = SQLiteStorage(db_path)

        # Add data
        test_data = {'key': 'value', 'nested': {'data': [1, 2, 3]}}
        storage.put('test_key', test_data)

        # Flush
        storage.flush()

        # Close
        storage.close()

        # Reopen and verify data persisted
        storage2 = SQLiteStorage(db_path)
        loaded_data = storage2.get('test_key')

        assert loaded_data == test_data, "Data not persisted after flush"

    def test_optimized_project_settings_storage_backends_flushable(self, temp_dir):
        """Test that OptimizedProjectSettings storage backends have flush methods."""
        settings = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite'
        )

        # Check cache_storage
        if hasattr(settings, 'cache_storage') and settings.cache_storage:
            assert hasattr(settings.cache_storage, 'flush'), \
                "cache_storage should have flush method"

        # Check metadata_storage
        if hasattr(settings, 'metadata_storage') and settings.metadata_storage:
            assert hasattr(settings.metadata_storage, 'flush'), \
                "metadata_storage should have flush method"

        # Check file_index
        if hasattr(settings, 'file_index') and settings.file_index:
            if hasattr(settings.file_index, 'flush'):
                # Some backends might not have flush (e.g., in-memory)
                assert callable(settings.file_index.flush), \
                    "file_index flush should be callable"

    def test_flush_before_close_no_data_loss(self, temp_dir):
        """Test that flushing before close prevents data loss."""
        db_path = os.path.join(temp_dir, 'test_no_loss.db')
        dal = SQLiteDAL(db_path)

        # Add significant amount of data
        for i in range(100):
            dal.storage.put(f'key_{i}', f'value_{i}')
            dal.metadata.add_file(f'file_{i}.py', 'file', '.py', {'index': i})

        # Flush explicitly
        dal.flush()

        # Close immediately
        dal.close()

        # Reopen and verify all data persisted
        dal2 = SQLiteDAL(db_path)

        # Check storage
        for i in range(100):
            value = dal2.storage.get(f'key_{i}')
            assert value == f'value_{i}', f"Data loss detected for key_{i}"

        # Check metadata
        all_files = dal2.metadata.get_all_files()
        assert len(all_files) == 100, f"Expected 100 files, got {len(all_files)}"

    def test_multiple_flush_calls_safe(self, temp_dir):
        """Test that multiple flush calls are safe (idempotent)."""
        db_path = os.path.join(temp_dir, 'test_multi_flush.db')
        storage = SQLiteStorage(db_path)

        # Add data
        storage.put('test_key', 'test_value')

        # Call flush multiple times
        try:
            storage.flush()
            storage.flush()
            storage.flush()
        except Exception as e:
            pytest.fail(f"Multiple flush() calls raised exception: {e}")

        # Verify data still intact
        value = storage.get('test_key')
        assert value == 'test_value'

    def test_flush_on_empty_database(self, temp_dir):
        """Test that flush works on empty database."""
        db_path = os.path.join(temp_dir, 'test_empty.db')
        storage = SQLiteStorage(db_path)

        # Flush on empty database should not fail
        try:
            storage.flush()
        except Exception as e:
            pytest.fail(f"flush() on empty DB raised exception: {e}")

    def test_close_after_flush_cleanup(self, temp_dir):
        """Test that close after flush properly cleans up resources."""
        db_path = os.path.join(temp_dir, 'test_cleanup.db')
        dal = SQLiteDAL(db_path)

        # Add data and flush
        dal.storage.put('key', 'value')
        dal.flush()

        # Close should work without issues
        try:
            dal.close()
        except Exception as e:
            pytest.fail(f"close() after flush raised exception: {e}")

        # Verify we can reopen
        dal2 = SQLiteDAL(db_path)
        assert dal2.storage.get('key') == 'value'

    def test_flush_preserves_wal_checkpoint(self, temp_dir):
        """Test that flush properly handles WAL checkpoint."""
        db_path = os.path.join(temp_dir, 'test_wal_checkpoint.db')
        storage = SQLiteStorage(db_path)

        # Add data to create WAL
        for i in range(10):
            storage.put(f'key_{i}', f'value_{i}')

        # Flush
        storage.flush()

        # Verify WAL file exists
        wal_path = f"{db_path}-wal"
        assert os.path.exists(wal_path), "WAL file should exist after flush"

        # Close (should checkpoint WAL)
        storage.close()

        # Verify data persisted after WAL checkpoint
        storage2 = SQLiteStorage(db_path)
        for i in range(10):
            value = storage2.get(f'key_{i}')
            assert value == f'value_{i}', f"Data lost after WAL checkpoint for key_{i}"

    def test_concurrent_flush_operations(self, temp_dir):
        """Test that concurrent flush operations are handled correctly."""
        import threading

        db_path = os.path.join(temp_dir, 'test_concurrent.db')
        dal = SQLiteDAL(db_path)

        # Add data from multiple threads
        def worker(thread_id):
            for i in range(10):
                dal.storage.put(f'thread_{thread_id}_key_{i}', f'thread_{thread_id}_value_{i}')
            dal.flush()

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify all data persisted
        for thread_id in range(5):
            for i in range(10):
                value = dal.storage.get(f'thread_{thread_id}_key_{i}')
                assert value == f'thread_{thread_id}_value_{i}', \
                    f"Concurrent flush caused data loss for thread_{thread_id}_key_{i}"
