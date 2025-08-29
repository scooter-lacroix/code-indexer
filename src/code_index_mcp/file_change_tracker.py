import uuid
import datetime
import hashlib
import difflib
import os
import logging
from typing import Optional, List, Dict

from .incremental_indexer import IncrementalIndexer
from .storage.storage_interface import FileMetadataInterface

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileChangeTracker:
    def __init__(self, storage_backend: FileMetadataInterface, incremental_indexer: IncrementalIndexer):
        """
        Initialize FileChangeTracker with any storage backend that supports file versioning.
        
        Args:
            storage_backend: Storage backend that implements FileMetadataInterface
                           (insert_file_version, get_file_version, etc.)
            incremental_indexer: IncrementalIndexer instance
        """
        self.storage_backend = storage_backend
        self.incremental_indexer = incremental_indexer

    def _capture_pre_edit_state(self, file_path: str) -> Optional[str]:
        """
        Reads the content of file_path, stores its current state as a version, and returns the content.

        Args:
            file_path: Can be either relative or absolute path
        """
        logger.debug(f"_capture_pre_edit_state called with file_path: {file_path}")

        # Convert to absolute path for file system operations
        if os.path.isabs(file_path):
            full_path = file_path
            # Try to convert to relative path for database storage
            try:
                # Get the base path from incremental indexer settings
                base_path = getattr(self.incremental_indexer.settings, 'base_path', '')
                logger.debug(f"Base path from settings: {base_path}")
                if base_path and full_path.startswith(base_path):
                    relative_path = os.path.relpath(full_path, base_path)
                    logger.debug(f"Converted absolute path {full_path} to relative path {relative_path}")
                else:
                    relative_path = file_path  # Use as-is if can't convert
                    logger.debug(f"Could not convert absolute path {full_path} to relative (base_path: {base_path})")
            except (ValueError, AttributeError) as e:
                relative_path = file_path  # Use as-is if conversion fails
                logger.debug(f"Path conversion failed: {e}, using original path {file_path}")
        else:
            relative_path = file_path
            # Convert to absolute path for file operations
            base_path = getattr(self.incremental_indexer.settings, 'base_path', '')
            if base_path:
                full_path = os.path.join(base_path, file_path)
                logger.debug(f"Converted relative path {file_path} to absolute path {full_path} using base_path {base_path}")
            else:
                full_path = os.path.abspath(file_path)
                logger.debug(f"No base_path set, converted relative path {file_path} to absolute path {full_path}")

        logger.debug(f"Final paths - full_path: {full_path}, relative_path: {relative_path}")

        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            version_id = self._generate_version_id()
            logger.debug(f"Capturing pre-edit state for file_path: {full_path}, version_id: {version_id}")
            # Store using relative path for database consistency
            if not self._store_file_version(relative_path, content, version_id):
                logger.error(f"Failed to capture pre-edit state for {relative_path}")
                return None

            # Update the incremental indexer's metadata with the current version ID
            file_metadata = self.incremental_indexer.file_metadata.get(relative_path, {})
            file_metadata['current_version_id'] = version_id
            self.incremental_indexer.file_metadata[relative_path] = file_metadata
            self.incremental_indexer.save_metadata() # Persist the metadata change

            return content
        else:
            logger.debug(f"File does not exist: {full_path}")
        return None

    def _record_post_edit_state(self, file_path: str, old_content: Optional[str], new_content: str, operation_type: Optional[str] = None, new_file_path: Optional[str] = None):
        """
        Calculates the new content's hash, stores it as a new version, generates a diff if content changed,
        and updates the file index.
        """
        # Convert to absolute path for file system operations
        if os.path.isabs(file_path):
            full_path = file_path
            # Try to convert to relative path for database storage
            try:
                # Get the base path from incremental indexer settings
                base_path = getattr(self.incremental_indexer.settings, 'base_path', '')
                if base_path and full_path.startswith(base_path):
                    relative_path = os.path.relpath(full_path, base_path)
                else:
                    relative_path = file_path  # Use as-is if can't convert
            except (ValueError, AttributeError):
                relative_path = file_path  # Use as-is if conversion fails
        else:
            relative_path = file_path
            # Convert to absolute path for file operations
            base_path = getattr(self.incremental_indexer.settings, 'base_path', '')
            if base_path:
                full_path = os.path.join(base_path, file_path)
            else:
                full_path = os.path.abspath(file_path)
        
        current_version_id = self._generate_version_id()
        logger.debug(f"Recording post-edit state for file_path: {file_path}, current_version_id: {current_version_id}, operation_type: {operation_type}, new_file_path: {new_file_path}")
        # Store using relative path for database consistency
        if not self._store_file_version(relative_path, new_content, current_version_id):
            logger.error(f"Failed to record post-edit state for {relative_path}")
            return

        operation_type = "edit" if operation_type is None else operation_type
        previous_version_id = None

        # Get previous version ID from incremental indexer's metadata
        file_metadata = self.incremental_indexer.file_metadata.get(relative_path, {})
        previous_version_id = file_metadata.get('current_version_id')

        if old_content is None:
            operation_type = "create"
        elif not os.path.exists(full_path): # File was deleted
            operation_type = "delete"
            new_content = "" # Ensure new_content is empty for diffing a deletion

        if old_content is not None and old_content != new_content:
            diff_id = self._generate_version_id()
            if not self._store_file_diff(diff_id, relative_path, previous_version_id, current_version_id, old_content, new_content, operation_type):
                logger.error(f"Failed to store diff for modified file {relative_path}")
        elif old_content is None and new_content: # File created
            diff_id = self._generate_version_id()
            if not self._store_file_diff(diff_id, relative_path, None, current_version_id, "", new_content, "create"):
                logger.error(f"Failed to store diff for created file {relative_path}")
        elif old_content and not new_content and operation_type == "delete": # File deleted
            diff_id = self._generate_version_id()
            if not self._store_file_diff(diff_id, relative_path, previous_version_id, current_version_id, old_content, "", "delete"):
                logger.error(f"Failed to store diff for deleted file {relative_path}")

        # Update the incremental indexer's metadata for file_path to include the current_version_id
        file_metadata = self.incremental_indexer.file_metadata.get(relative_path, {})
        file_metadata['current_version_id'] = current_version_id
        file_metadata['last_version_timestamp'] = current_version_id  # Use version_id as timestamp reference
        self.incremental_indexer.file_metadata[relative_path] = file_metadata
        self.incremental_indexer.save_metadata() # Persist the metadata change

        # Also update the file's general metadata (mtime, size, hash) in the incremental indexer
        self.incremental_indexer.update_file_metadata(relative_path, full_path)

        # Force rehash to ensure hash is up to date
        self.incremental_indexer.force_rehash_file(relative_path, full_path)

    def _generate_version_id(self) -> str:
        """Generates a unique ID for versions."""
        return uuid.uuid4().hex

    def _calculate_hash(self, content: str) -> str:
        """Calculates SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _normalize_path(self, file_path: str) -> str:
        """
        Normalizes file paths for consistent storage and retrieval.

        Args:
            file_path: The file path to normalize

        Returns:
            Normalized path with forward slashes and consistent format
        """
        if not file_path:
            return file_path

        # Normalize path separators and remove redundant separators
        normalized = os.path.normpath(file_path).replace('\\', '/')

        # Remove leading/trailing slashes for consistency
        normalized = normalized.strip('/')

        logger.debug(f"Normalized path: {file_path} -> {normalized}")
        return normalized

    def _ensure_file_registered(self, file_path: str) -> bool:
        """
        Ensures a file is registered in the metadata store before tracking versions.

        Args:
            file_path: Path to the file to register

        Returns:
            True if file is registered (either was already or successfully registered), False otherwise
        """
        try:
            # Normalize the path for consistent storage
            normalized_path = self._normalize_path(file_path)

            # Check if file is already registered
            file_info = self.storage_backend.get_file_info(normalized_path)
            if file_info is not None:
                logger.debug(f"File {normalized_path} is already registered")
                return True

            # File not registered, register it
            logger.debug(f"Registering new file: {normalized_path}")

            # Determine file type and extension
            file_type = 'file'
            extension = ''
            if os.path.splitext(normalized_path)[1]:
                extension = os.path.splitext(normalized_path)[1][1:]  # Remove the leading dot

            # Register the file
            success = self.storage_backend.add_file(
                file_path=normalized_path,
                file_type=file_type,
                extension=extension,
                metadata={'auto_registered': True, 'registration_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            )

            if success:
                logger.info(f"Successfully registered file: {normalized_path}")
                return True
            else:
                logger.error(f"Failed to register file: {normalized_path}")
                return False

        except Exception as e:
            logger.error(f"Error ensuring file registration for {file_path}: {e}")
            return False

    def _store_file_version(self, file_path: str, content: str, version_id: str) -> bool:
        """Stores a file version in file_versions table with automatic file registration."""
        try:
            # Normalize the path for consistent storage
            normalized_path = self._normalize_path(file_path)

            # Ensure file is registered before storing version
            if not self._ensure_file_registered(normalized_path):
                logger.error(f"Cannot store version for unregistered file: {normalized_path}")
                return False

            file_hash = self._calculate_hash(content)
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            size = len(content.encode('utf-8'))

            logger.debug(f"Storing file version: version_id={version_id}, file_path={normalized_path}, timestamp={timestamp}")

            # Use the storage backend interface instead of hardcoded sqlite_storage
            success = self.storage_backend.insert_file_version(version_id, normalized_path, content, file_hash, timestamp, size)

            if success:
                logger.debug(f"Successfully stored file version: {version_id}")
                return True
            else:
                logger.error(f"Failed to store file version: {version_id}")
                return False

        except Exception as e:
            logger.error(f"Error storing file version {version_id} for {file_path}: {e}")
            return False

    def _store_file_diff(self, diff_id: str, file_path: str, previous_version_id: Optional[str], current_version_id: str, old_content: str, new_content: str, operation_type: str, operation_details: Optional[str] = None) -> bool:
        """Stores a diff in file_diffs table."""
        try:
            # Normalize the path for consistent storage
            normalized_path = self._normalize_path(file_path)

            diff_content = "\n".join(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=normalized_path + "_old",
                tofile=normalized_path + "_new",
                lineterm='' # Avoid extra newlines
            ))
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            logger.debug(f"Storing file diff: diff_id={diff_id}, file_path={normalized_path}, previous_version_id={previous_version_id}, current_version_id={current_version_id}, operation_type={operation_type}, timestamp={timestamp}")

            # Use the storage backend interface instead of hardcoded sqlite_storage
            success = self.storage_backend.insert_file_diff(diff_id, normalized_path, previous_version_id, current_version_id, diff_content, "unified_diff", operation_type, operation_details, timestamp)

            if success:
                logger.debug(f"Successfully stored file diff: {diff_id}")
                return True
            else:
                logger.error(f"Failed to store file diff: {diff_id}")
                return False

        except Exception as e:
            logger.error(f"Error storing file diff {diff_id} for {file_path}: {e}")
            return False

    def flush(self):
        """Flushes any pending changes to the underlying storage."""
        if hasattr(self.storage_backend, 'flush'):
            self.storage_backend.flush()

    def get_file_version_by_id(self, version_id: str) -> Optional[str]:
        """Retrieves a file version by its ID."""
        version_data = self.storage_backend.get_file_version(version_id)
        if version_data:
            return version_data.get('content')
        return None

    def get_file_history(self, file_path: str) -> List[Dict]:
        """Retrieves the history of changes for a given file path."""
        logger.debug(f"get_file_history called with file_path: {file_path}")

        try:
            # Normalize the path for consistent querying
            normalized_path = self._normalize_path(file_path)
            logger.debug(f"Querying database with normalized path: {normalized_path}")

            # Check if file is registered - if not, it might still have history if it was previously tracked
            file_info = self.storage_backend.get_file_info(normalized_path)
            if file_info is None:
                logger.debug(f"File {normalized_path} is not currently registered, but checking for historical data")

            # Try multiple path variations to find history (handle path normalization inconsistencies)
            search_paths = [normalized_path]

            # Add alternative path formats that might exist in the database
            if normalized_path.startswith('/'):
                search_paths.append(normalized_path[1:])  # Remove leading slash
            else:
                search_paths.append('/' + normalized_path)  # Add leading slash

            # Try Windows path format if on Windows
            if os.name == 'nt':
                alt_path = normalized_path.replace('/', '\\')
                if alt_path != normalized_path:
                    search_paths.append(alt_path)

            versions = []
            diffs = []

            # Search across all path variations
            for search_path in search_paths:
                logger.debug(f"Trying search path: {search_path}")
                path_versions = self.storage_backend.get_file_versions_for_path(search_path)
                path_diffs = self.storage_backend.get_file_diffs_for_path(search_path)

                if path_versions:
                    versions.extend(path_versions)
                    logger.debug(f"Found {len(path_versions)} versions for path {search_path}")
                if path_diffs:
                    diffs.extend(path_diffs)
                    logger.debug(f"Found {len(path_diffs)} diffs for path {search_path}")

                # If we found data, use this path for consistency
                if path_versions or path_diffs:
                    normalized_path = search_path
                    break

            logger.debug(f"Total found: {len(versions)} versions and {len(diffs)} diffs for path {normalized_path}")

            history = []
            for v in versions:
                v['type'] = 'version'
                history.append(v)
            for d in diffs:
                d['type'] = 'diff'
                history.append(d)

            # Sort by timestamp
            history.sort(key=lambda x: x['timestamp'])
            logger.debug(f"Returning {len(history)} history items")
            return history

        except Exception as e:
            logger.error(f"Error retrieving file history for {file_path}: {e}")
            return []

    def reconstruct_file_version(self, full_file_path: str, version_id: str) -> Optional[str]:
        """
        Reconstructs a specific file version by applying diffs if necessary.
        """
        try:
            # 1. Try to retrieve the version directly
            target_version_data = self.storage_backend.get_file_version(version_id)
            if target_version_data:
                return target_version_data.get('content')

            # 2. If not a full version, we need to reconstruct from history
            # Get all versions and diffs for the file path, sorted by timestamp
            history = self.get_file_history(full_file_path)

            # Find the latest full version before or at the target version_id's timestamp
            base_content = None
            base_timestamp = None
            base_version_id = None

            # Find the target version's timestamp first
            target_timestamp = None
            for item in history:
                if item.get('version_id') == version_id or item.get('current_version_id') == version_id:
                    target_timestamp = item['timestamp']
                    break

            if not target_timestamp:
                # If the target version_id is not found in history at all, return None
                return None

            # Find the latest full version before or at the target timestamp
            for item in history:
                if item['type'] == 'version' and item['timestamp'] <= target_timestamp:
                    if base_timestamp is None or item['timestamp'] > base_timestamp:
                        base_content = item['content']
                        base_timestamp = item['timestamp']
                        base_version_id = item['version_id']

            if base_content is None:
                # No full version found before the target, cannot reconstruct
                return None

            current_content = base_content
            # Apply subsequent diffs up to the target version
            for item in history:
                if item['type'] == 'diff' and item['timestamp'] > base_timestamp and item['timestamp'] <= target_timestamp:
                    diff_content = item['diff_content']

                    # Apply the diff
                    # difflib.apply_patch expects a list of lines
                    old_lines = current_content.splitlines(keepends=True)

                    # difflib.parse_unidiff returns an iterator of (filename1, filename2, date1, date2, hunks)
                    # Each hunk is (old_start, old_len, new_start, new_len, lines)
                    # lines are the diff lines with '+', '-', ' ' prefixes

                    # A simpler approach for applying unified diffs is to use a library or manual parsing.
                    # For this implementation, we'll assume a direct application of unified diff format.
                    # This is a simplified application and might need more robust error handling for malformed diffs.

                    # Reconstruct by applying diff lines
                    new_lines = []
                    diff_lines = diff_content.splitlines(keepends=True)

                    # This is a very basic diff application. A real-world scenario might need
                    # a more sophisticated diff parsing and application library.
                    # For unified diff, lines starting with '-' are removed, '+' are added.
                    # Lines starting with ' ' are context.

                    old_idx = 0
                    for line in diff_lines:
                        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                            continue
                        elif line.startswith('-'):
                            # Skip line from old_lines, effectively removing it
                            old_idx += 1
                        elif line.startswith('+'):
                            new_lines.append(line[1:]) # Add new line
                        else: # Context line or unchanged line
                            new_lines.append(old_lines[old_idx])
                            old_idx += 1

                    current_content = "".join(new_lines)

                # If we reached the target version_id, return the current content
                if item.get('version_id') == version_id or item.get('current_version_id') == version_id:
                    return current_content

            return None # Should not reach here if target_timestamp was found and base_content was set

        except Exception as e:
            logger.error(f"Error reconstructing file version {version_id} for {full_file_path}: {e}")
            return None