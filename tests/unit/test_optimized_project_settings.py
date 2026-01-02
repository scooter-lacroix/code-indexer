"""
Unit tests for OptimizedProjectSettings with MessagePack persistence.

This module tests:
- MessagePack-based index persistence
- Format detection (pickle vs msgpack)
- Migration from pickle to MessagePack
- No new pickle files are created
"""

import os
import tempfile
import shutil
import pickle
import pytest
from pathlib import Path

from code_index_mcp.optimized_project_settings import OptimizedProjectSettings
from code_index_mcp.registry.msgpack_serializer import MessagePackSerializer, FormatType


class TestOptimizedProjectSettingsMessagePack:
    """Test MessagePack integration in OptimizedProjectSettings."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def settings(self, temp_dir):
        """Create an OptimizedProjectSettings instance for testing."""
        return OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=False
        )

    def test_msgpack_serializer_initialized(self, settings):
        """Test that MessagePack serializer is initialized."""
        assert hasattr(settings, 'msgpack_serializer')
        assert isinstance(settings.msgpack_serializer, MessagePackSerializer)

    def test_save_index_creates_msgpack_file(self, settings, temp_dir):
        """Test that save_index creates .msgpack files for Trie index, not .pickle files."""
        # Create settings with Trie index to test MessagePack persistence
        settings_trie = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        # Create test index data
        test_index = {
            'files': ['file1.py', 'file2.py'],
            'metadata': {'count': 2}
        }

        # Save the index
        settings_trie.save_index(test_index)

        # Check that .msgpack file exists
        msgpack_path = str(Path(settings_trie.get_index_path()).with_suffix('.msgpack'))
        assert os.path.exists(msgpack_path), f"MessagePack file not created at {msgpack_path}"

        # Check that .pickle file was NOT created
        pickle_path = settings_trie.get_index_path()
        assert not os.path.exists(pickle_path), f"Pickle file should not exist at {pickle_path}"

    def test_load_index_from_msgpack(self, settings, temp_dir):
        """Test that load_index can read from MessagePack files for Trie index."""
        # Create settings with Trie index
        settings_trie = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        # Create and save test index
        test_index = {
            'files': ['file1.py', 'file2.py', 'file3.py'],
            'metadata': {'count': 3, 'last_updated': '2025-01-01'}
        }
        settings_trie.save_index(test_index)

        # Load the index
        loaded_index = settings_trie.load_index()

        # Verify loaded data matches original
        assert loaded_index == test_index

    def test_format_detection_msgpack(self, settings):
        """Test format detection for MessagePack files."""
        import tempfile

        # Create a temporary MessagePack file
        with tempfile.NamedTemporaryFile(suffix='.msgpack', delete=False) as f:
            temp_path = f.name

        try:
            # Write MessagePack data
            test_data = {'test': 'data'}
            settings.msgpack_serializer.write(temp_path, test_data)

            # Detect format
            format_type = settings.msgpack_serializer.detect_format(temp_path)

            # Should be detected as MessagePack
            assert format_type == FormatType.MSGPACK
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_format_detection_pickle(self, settings):
        """Test format detection for pickle files."""
        import tempfile

        # Create a temporary pickle file
        with tempfile.NamedTemporaryFile(suffix='.pickle', delete=False) as f:
            temp_path = f.name

        try:
            # Write pickle data
            test_data = {'test': 'legacy_data'}
            with open(temp_path, 'wb') as f:
                pickle.dump(test_data, f)

            # Detect format
            format_type = settings.msgpack_serializer.detect_format(temp_path)

            # Should be detected as Pickle
            assert format_type == FormatType.PICKLE
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_pickle_to_msgpack_migration(self, settings, temp_dir):
        """Test migration from pickle to MessagePack format for Trie index."""
        # Create settings with Trie index
        settings_trie = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        # Create a legacy pickle file
        index_path = settings_trie.get_index_path()
        test_data = {'files': ['old_file.py'], 'metadata': {'count': 1}}

        with open(index_path, 'wb') as f:
            pickle.dump(test_data, f)

        # Load index (should trigger migration)
        loaded_index = settings_trie.load_index()

        # Verify data was loaded correctly
        assert loaded_index == test_data

        # Verify MessagePack file was created
        msgpack_path = str(Path(index_path).with_suffix('.msgpack'))
        assert os.path.exists(msgpack_path)

        # Verify MessagePack file contains correct data
        migrated_data = settings_trie.msgpack_serializer.read(msgpack_path)
        assert migrated_data == test_data

    def test_no_pickle_files_created_on_save(self, settings, temp_dir):
        """Test that saving index never creates pickle files for Trie index."""
        # Create settings with Trie index
        settings_trie = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        test_index = {'files': ['test.py'], 'metadata': {}}

        # Save index multiple times
        for i in range(3):
            test_index['metadata']['iteration'] = i
            settings_trie.save_index(test_index)

        # Check that no pickle files exist
        pickle_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.pickle'):
                    pickle_files.append(os.path.join(root, file))

        assert len(pickle_files) == 0, f"Pickle files were created: {pickle_files}"

    def test_load_index_nonexistent(self, settings, temp_dir):
        """Test loading index when no file exists for Trie index."""
        # Create settings with Trie index
        settings_trie = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        # Remove any existing index files
        index_path = settings_trie.get_index_path()
        msgpack_path = str(Path(index_path).with_suffix('.msgpack'))

        if os.path.exists(msgpack_path):
            os.unlink(msgpack_path)
        if os.path.exists(index_path):
            os.unlink(index_path)

        # Load should return empty Trie index
        loaded = settings_trie.load_index()
        # For SQLite with Trie index, returns a TrieFileIndex object
        assert loaded is not None

    def test_msgpack_atomic_write(self, settings, temp_dir):
        """Test that MessagePack writes are atomic (temp file + rename)."""
        import tempfile

        # Create test data
        test_data = {'files': ['atomic_test.py'], 'metadata': {}}

        # Use a temporary path for testing
        test_file = os.path.join(temp_dir, 'atomic_test.msgpack')

        # Write data
        settings.msgpack_serializer.write(test_file, test_data)

        # Verify final file exists
        assert os.path.exists(test_file)

        # Verify no temp file remains
        temp_files = []
        for file in os.listdir(temp_dir):
            if file.endswith('.tmp'):
                temp_files.append(file)

        assert len(temp_files) == 0, f"Temp files remain: {temp_files}"

    def test_index_persistence_across_instances(self, temp_dir):
        """Test that index persists across different OptimizedProjectSettings instances for Trie index."""
        # Create first instance and save index
        settings1 = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        test_index = {
            'files': ['persistent.py'],
            'metadata': {'project': 'test'}
        }
        settings1.save_index(test_index)

        # Create second instance and load index
        settings2 = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        loaded_index = settings2.load_index()

        # Verify data persisted
        assert loaded_index == test_index

    def test_msgpack_serializer_use_bin_type(self, settings):
        """Test that MessagePack serializer uses binary type."""
        assert settings.msgpack_serializer.use_bin_type is True

    def test_complex_data_serialization(self, settings, temp_dir):
        """Test serialization of complex nested data structures for Trie index."""
        # Create settings with Trie index
        settings_trie = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        complex_index = {
            'files': [
                {'path': 'file1.py', 'size': 100, 'metadata': {'lang': 'python'}},
                {'path': 'file2.py', 'size': 200, 'metadata': {'lang': 'python'}}
            ],
            'stats': {
                'total_files': 2,
                'total_size': 300,
                'languages': {'python': 2}
            },
            'nested': {
                'level1': {
                    'level2': {
                        'data': [1, 2, 3]
                    }
                }
            }
        }

        # Save and load
        settings_trie.save_index(complex_index)
        loaded = settings_trie.load_index()

        # Verify complex structure is preserved
        assert loaded == complex_index

    def test_unicode_support(self, settings, temp_dir):
        """Test that Unicode data is properly handled for Trie index."""
        # Create settings with Trie index
        settings_trie = OptimizedProjectSettings(
            base_path=temp_dir,
            skip_load=False,
            storage_backend='sqlite',
            use_trie_index=True
        )

        unicode_index = {
            'files': ['文件.py', 'файл.py', 'datei.py'],
            'metadata': {
                'description': 'Тестовые данные',
                'comments': '测试评论'
            }
        }

        # Save and load
        settings_trie.save_index(unicode_index)
        loaded = settings_trie.load_index()

        # Verify Unicode is preserved
        assert loaded == unicode_index
