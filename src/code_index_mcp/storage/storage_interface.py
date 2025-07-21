"""
Storage interface for code index backends.

This module defines the interface that all storage backends must implement
to ensure consistent API across different storage implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Iterator, Tuple


class StorageInterface(ABC):
    """Abstract base class for generic key-value storage backends."""
    
    @abstractmethod
    def put(self, key: str, value: Any) -> bool:
        """Store a key-value pair.
        
        Args:
            key: The key to store
            value: The value to store
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The value if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key-value pair.
        
        Args:
            key: The key to delete
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists.
        
        Args:
            key: The key to check
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def keys(self, pattern: Optional[str] = None) -> Iterator[str]:
        """Iterate over keys, optionally filtered by pattern.
        
        Args:
            pattern: Optional pattern to filter keys
            
        Yields:
            Keys matching the pattern
        """
        pass
    
    @abstractmethod
    def items(self, pattern: Optional[str] = None) -> Iterator[Tuple[str, Any]]:
        """Iterate over key-value pairs, optionally filtered by pattern.
        
        Args:
            pattern: Optional pattern to filter keys
            
        Yields:
            Key-value pairs matching the pattern
        """
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all data.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get the number of stored items.
        
        Returns:
            Number of items in storage
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the storage backend and release resources."""
        pass
    
    @abstractmethod
    def flush(self) -> bool:
        """Flush any pending operations to persistent storage.
        
        Returns:
            True if successful, False otherwise
        """
        pass


class FileMetadataInterface(ABC):
    """Abstract interface for file metadata storage, including versions and diffs."""
    
    @abstractmethod
    def add_file(self, file_path: str, file_type: str, extension: str,
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a file's metadata to the index.
        
        Args:
            file_path: Path to the file
            file_type: Type of the file (e.g., 'file', 'directory')
            extension: File extension
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_file(self, file_path: str) -> bool:
        """Remove a file's metadata from the index.
        
        Args:
            file_path: Path to the file to remove
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File information dictionary if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_directory_structure(self, directory_path: str = "") -> Dict[str, Any]:
        """Get the directory structure based on stored file metadata.
        
        Args:
            directory_path: Optional directory path to get structure for
            
        Returns:
            Dictionary representing the directory structure
        """
        pass
    
    @abstractmethod
    def get_all_files(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get all files' metadata in the index.
        
        Returns:
            List of tuples (file_path, file_info)
        """
        pass

    @abstractmethod
    def insert_file_version(self, version_id: str, file_path: str, content: str, hash: str, timestamp: str, size: int) -> bool:
        """Inserts a new file version.
        
        Args:
            version_id: Unique ID for the file version
            file_path: Path of the file
            content: Content of the file version
            hash: Hash of the file content
            timestamp: Timestamp of the version
            size: Size of the file content in bytes
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_file_version(self, version_id: str) -> Optional[Dict]:
        """Retrieves a file version by its ID.
        
        Args:
            version_id: The ID of the file version to retrieve
            
        Returns:
            A dictionary containing file version data if found, None otherwise
        """
        pass

    @abstractmethod
    def get_file_versions_for_path(self, file_path: str) -> List[Dict]:
        """Retrieves all versions for a given file path, ordered by timestamp.
        
        Args:
            file_path: The path of the file
            
        Returns:
            A list of dictionaries, each containing file version data
        """
        pass

    @abstractmethod
    def insert_file_diff(self, diff_id: str, file_path: str, previous_version_id: Optional[str], current_version_id: str, diff_content: str, diff_type: str, operation_type: str, operation_details: Optional[str], timestamp: str) -> bool:
        """Inserts a new file diff.
        
        Args:
            diff_id: Unique ID for the diff
            file_path: Path of the file
            previous_version_id: ID of the previous version (if applicable)
            current_version_id: ID of the current version
            diff_content: The content of the diff
            diff_type: Type of diff (e.g., 'unified', 'json')
            operation_type: Type of operation (e.g., 'modify', 'create', 'delete', 'rename')
            operation_details: Additional details about the operation
            timestamp: Timestamp of the diff
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_file_diffs_for_path(self, file_path: str) -> List[Dict]:
        """Retrieves all diffs for a given file path.
        
        Args:
            file_path: The path of the file
            
        Returns:
            A list of dictionaries, each containing file diff data
        """
        pass


class SearchInterface(ABC):
    """Abstract interface for full-text search capabilities."""

    @abstractmethod
    def search_content(self, query: str) -> List[Tuple[str, Any]]:
        """Search across file content.
        
        Args:
            query: The search query string
            
        Returns:
            A list of (key, value) tuples matching the query
        """
        pass

    @abstractmethod
    def search_file_paths(self, query: str) -> List[str]:
        """Search across file paths.
        
        Args:
            query: The search query string
            
        Returns:
            A list of file paths matching the query
        """
        pass

    @abstractmethod
    def index_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """Index a document for search.
        
        Args:
            doc_id: Unique identifier for the document
            document: Document data to index
            
        Returns:
            True if successful, False otherwise
        """
        pass


class DALInterface(ABC):
    """
    Abstract base class for the Data Access Layer (DAL).
    This interface aggregates all specific storage interfaces, providing a unified
    entry point for interacting with different data backends.
    """

    @property
    @abstractmethod
    def storage(self) -> StorageInterface:
        """
        Returns the generic key-value storage interface.
        """
        pass

    @property
    @abstractmethod
    def metadata(self) -> FileMetadataInterface:
        """
        Returns the file metadata storage interface.
        """
        pass

    @property
    @abstractmethod
    def search(self) -> SearchInterface:
        """
        Returns the full-text search interface.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Closes all underlying storage backends and releases resources.
        """
        pass

    @abstractmethod
    def clear_all(self) -> bool:
        """
        Clears all data from all underlying storage backends.
        
        Returns:
            True if successful, False otherwise
        """
        pass
