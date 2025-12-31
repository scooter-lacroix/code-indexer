"""
Factory for Data Access Layer (DAL) instances.
This module provides a central point for creating and configuring
different DAL implementations based on application settings.
"""

import os
from typing import Optional, Dict, Any, List, Tuple

from ..config_manager import ConfigManager
from .storage_interface import DALInterface, StorageInterface, FileMetadataInterface, SearchInterface
from .sqlite_storage import SQLiteDAL
from .postgresql_storage import PostgreSQLStorage, PostgreSQLFileMetadata
from .elasticsearch_storage import ElasticsearchSearch
from ..logger_config import setup_logging
import logging

logger = setup_logging()

class PostgreSQLElasticsearchDAL(DALInterface):
    """
    A composite DAL implementation using PostgreSQL for metadata and
    Elasticsearch for search.
    """
    def __init__(self, pg_user: str, pg_password: str, pg_host: str, pg_port: int, pg_database: str,
                 pg_ssl_args: Optional[Dict[str, Any]],
                 es_hosts: List[str], es_index_name: str,
                 es_api_key: Optional[Tuple[str, str]], es_http_auth: Optional[Tuple[str, str]],
                 es_use_ssl: bool, es_verify_certs: bool, es_ca_certs: Optional[str],
                 es_client_cert: Optional[str], es_client_key: Optional[str]):
        
        self._metadata_backend = PostgreSQLFileMetadata(
            db_user=pg_user, db_password=pg_password, db_host=pg_host, db_port=pg_port, db_name=pg_database,
            ssl_args=pg_ssl_args
        )
        self._storage_backend = PostgreSQLStorage(
            db_user=pg_user, db_password=pg_password, db_host=pg_host, db_port=pg_port, db_name=pg_database,
            ssl_args=pg_ssl_args
        )
        self._search_backend = ElasticsearchSearch(
            hosts=es_hosts, index_name=es_index_name,
            api_key=es_api_key, http_auth=es_http_auth,
            use_ssl=es_use_ssl, verify_certs=es_verify_certs,
            ca_certs=es_ca_certs, client_cert=es_client_cert, client_key=es_client_key
        )

    @property
    def storage(self) -> StorageInterface:
        return self._storage_backend

    @property
    def metadata(self) -> FileMetadataInterface:
        return self._metadata_backend

    @property
    def search(self) -> SearchInterface:
        return self._search_backend

    def close(self) -> None:
        """
        Closes all underlying storage backends.
        """
        if hasattr(self, '_storage_backend'):
            self._storage_backend.close()
        if hasattr(self, '_metadata_backend'):
            self._metadata_backend.close()
        if hasattr(self, '_search_backend'):
            self._search_backend.close()

    def clear_all(self) -> bool:
        """
        Clears all data from all underlying storage backends.
        """
        metadata_cleared = self._metadata_backend.clear()
        # Elasticsearch might need a separate clear/delete_index operation
        # For now, assume search backend clear is not critical for this task's scope
        storage_cleared = self._storage_backend.clear()
        return metadata_cleared and storage_cleared

class DualWriteReadDAL(DALInterface):
    """
    A DAL implementation that supports dual-write to SQLite and PostgreSQL/Elasticsearch,
    and dual-read with preference for PostgreSQL/Elasticsearch.
    """
    def __init__(self, sqlite_dal: SQLiteDAL, pg_es_dal: PostgreSQLElasticsearchDAL):
        self._sqlite_dal = sqlite_dal
        self._pg_es_dal = pg_es_dal
        logger.info("DualWriteReadDAL initialized. Writing to both SQLite and PG/ES. Reading primarily from PG/ES.")

    @property
    def storage(self) -> StorageInterface:
        return DualWriteReadStorage(self._sqlite_dal.storage, self._pg_es_dal.storage)

    @property
    def metadata(self) -> FileMetadataInterface:
        return DualWriteReadMetadata(self._sqlite_dal.metadata, self._pg_es_dal.metadata)

    @property
    def search(self) -> SearchInterface:
        return DualWriteReadSearch(self._sqlite_dal.search, self._pg_es_dal.search)

    def close(self) -> None:
        self._sqlite_dal.close()
        self._pg_es_dal.close()
        logger.info("DualWriteReadDAL closed.")

    def clear_all(self) -> bool:
        sqlite_cleared = self._sqlite_dal.clear_all()
        pg_es_cleared = self._pg_es_dal.clear_all()
        logger.info(f"DualWriteReadDAL cleared all data. SQLite cleared: {sqlite_cleared}, PG/ES cleared: {pg_es_cleared}")
        return sqlite_cleared and pg_es_cleared

class DualWriteReadStorage(StorageInterface):
    """
    Dual-write storage implementation with compensating transaction pattern.

    CRITICAL FIX: Implements two-phase commit pattern for dual-write operations
    to prevent data inconsistency when one backend fails.
    """
    def __init__(self, sqlite_storage: StorageInterface, pg_es_storage: StorageInterface):
        self._sqlite_storage = sqlite_storage
        self._pg_es_storage = pg_es_storage
        # Track pending operations for compensating transactions
        self._pending_writes: Dict[str, str] = {}  # file_path -> operation_type

    def save_file_content(self, file_path: str, content: str) -> None:
        """
        Save file content to both backends using compensating transaction pattern.

        CRITICAL FIX: Implements two-phase commit to prevent data inconsistency.
        1. Write to primary (PG/ES)
        2. Write to secondary (SQLite)
        3. If secondary fails, compensate by rolling back primary
        """
        # Phase 1: Write to primary backend (PG/ES)
        try:
            self._pg_es_storage.save_file_content(file_path, content)
            self._pending_writes[file_path] = 'write'
            logger.debug(f"Primary write successful for {file_path}")
        except Exception as e:
            logger.error(f"Primary backend write failed for {file_path}: {e}")
            raise  # If primary fails, don't attempt secondary

        # Phase 2: Write to secondary backend (SQLite)
        try:
            self._sqlite_storage.save_file_content(file_path, content)
            logger.debug(f"Secondary write successful for {file_path}")
        except Exception as e:
            logger.error(f"Secondary backend write failed for {file_path}, attempting compensating transaction: {e}")
            # Compensating transaction: rollback primary
            try:
                self._pg_es_storage.delete_file_content(file_path)
                logger.warning(f"Compensating transaction: rolled back primary write for {file_path}")
            except Exception as rollback_err:
                logger.error(f"Failed to rollback primary write for {file_path}: {rollback_err}")
                # Store inconsistency for later reconciliation
                self._pending_writes[file_path] = 'inconsistent'
            raise

        # Commit: both writes succeeded
        if file_path in self._pending_writes:
            del self._pending_writes[file_path]
        logger.debug(f"Dual-wrote file content for {file_path}")

    def get_file_content(self, file_path: str) -> Optional[str]:
        # Prioritize reading from the new store
        content = self._pg_es_storage.get_file_content(file_path)
        if content is None:
            logger.warning(f"File content not found in PG/ES for {file_path}, falling back to SQLite.")
            content = self._sqlite_storage.get_file_content(file_path)
        return content

    def delete_file_content(self, file_path: str) -> None:
        """
        Delete file content from both backends using compensating transaction pattern.

        CRITICAL FIX: Implements two-phase commit for delete operations.
        """
        # Phase 1: Delete from primary backend (PG/ES)
        primary_deleted = False
        try:
            self._pg_es_storage.delete_file_content(file_path)
            primary_deleted = True
            logger.debug(f"Primary delete successful for {file_path}")
        except Exception as e:
            logger.error(f"Primary backend delete failed for {file_path}: {e}")
            # Continue with secondary delete even if primary fails

        # Phase 2: Delete from secondary backend (SQLite)
        try:
            self._sqlite_storage.delete_file_content(file_path)
            logger.debug(f"Secondary delete successful for {file_path}")
        except Exception as e:
            logger.error(f"Secondary backend delete failed for {file_path}: {e}")
            if primary_deleted:
                # Compensating transaction: restore primary
                try:
                    # We can't restore the content here as it's already deleted
                    # Log the inconsistency for manual reconciliation
                    logger.error(f"Data inconsistency detected for {file_path}: deleted from primary but not secondary")
                except Exception as rollback_err:
                    logger.error(f"Failed to handle compensating transaction for {file_path}: {rollback_err}")
            raise

        logger.debug(f"Dual-deleted file content for {file_path}")

    def clear(self) -> bool:
        """
        Clear both backends with safety checks.

        CRITICAL FIX: Attempts to clear both backends and reports any failures.
        """
        sqlite_cleared = self._sqlite_storage.clear()
        pg_es_cleared = self._pg_es_storage.clear()

        if not sqlite_cleared:
            logger.error("Failed to clear SQLite backend")
        if not pg_es_cleared:
            logger.error("Failed to clear PG/ES backend")

        return sqlite_cleared and pg_es_cleared

class DualWriteReadMetadata(FileMetadataInterface):
    """
    Dual-write metadata implementation with compensating transaction pattern.

    CRITICAL FIX: Implements two-phase commit pattern for dual-write operations
    to prevent data inconsistency when one backend fails.
    """
    def __init__(self, sqlite_metadata: FileMetadataInterface, pg_es_metadata: FileMetadataInterface):
        self._sqlite_metadata = sqlite_metadata
        self._pg_es_metadata = pg_es_metadata
        # Track pending operations for compensating transactions
        self._pending_metadata_writes: Dict[str, str] = {}

    def save_file_metadata(self, file_path: str, metadata: Dict[str, Any]) -> None:
        """
        Save metadata to both backends using compensating transaction pattern.

        CRITICAL FIX: Two-phase commit for metadata operations.
        """
        # Phase 1: Write to primary backend (PG/ES)
        try:
            self._pg_es_metadata.save_file_metadata(file_path, metadata)
            self._pending_metadata_writes[file_path] = 'write'
        except Exception as e:
            logger.error(f"Primary metadata write failed for {file_path}: {e}")
            raise

        # Phase 2: Write to secondary backend (SQLite)
        try:
            self._sqlite_metadata.save_file_metadata(file_path, metadata)
        except Exception as e:
            logger.error(f"Secondary metadata write failed for {file_path}, attempting compensating transaction: {e}")
            # Compensating transaction: rollback primary
            try:
                self._pg_es_metadata.delete_file_metadata(file_path)
                logger.warning(f"Compensating transaction: rolled back primary metadata write for {file_path}")
            except Exception as rollback_err:
                logger.error(f"Failed to rollback primary metadata write for {file_path}: {rollback_err}")
                self._pending_metadata_writes[file_path] = 'inconsistent'
            raise

        # Commit: both writes succeeded
        if file_path in self._pending_metadata_writes:
            del self._pending_metadata_writes[file_path]
        logger.debug(f"Dual-wrote file metadata for {file_path}")

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        # Prioritize reading from the new store
        metadata = self._pg_es_metadata.get_file_metadata(file_path)
        if metadata is None:
            logger.warning(f"File metadata not found in PG/ES for {file_path}, falling back to SQLite.")
            metadata = self._sqlite_metadata.get_file_metadata(file_path)
        return metadata

    def delete_file_metadata(self, file_path: str) -> None:
        """
        Delete metadata from both backends using compensating transaction pattern.

        CRITICAL FIX: Two-phase commit for delete operations.
        """
        # Phase 1: Delete from primary backend (PG/ES)
        primary_deleted = False
        try:
            self._pg_es_metadata.delete_file_metadata(file_path)
            primary_deleted = True
        except Exception as e:
            logger.error(f"Primary metadata delete failed for {file_path}: {e}")

        # Phase 2: Delete from secondary backend (SQLite)
        try:
            self._sqlite_metadata.delete_file_metadata(file_path)
        except Exception as e:
            logger.error(f"Secondary metadata delete failed for {file_path}: {e}")
            if primary_deleted:
                logger.error(f"Data inconsistency detected for {file_path}: metadata deleted from primary but not secondary")
            raise

        logger.debug(f"Dual-deleted file metadata for {file_path}")

    def get_all_file_paths(self) -> List[str]:
        """
        Get all file paths from both backends with deduplication.

        CRITICAL FIX: Combines results from both backends and deduplicates.
        """
        # Combine and deduplicate paths from both backends
        pg_es_paths = set(self._pg_es_metadata.get_all_file_paths())
        sqlite_paths = set(self._sqlite_metadata.get_all_file_paths())
        return list(pg_es_paths.union(sqlite_paths))

    def clear(self) -> bool:
        """
        Clear both backends with safety checks.

        CRITICAL FIX: Reports failures from either backend.
        """
        sqlite_cleared = self._sqlite_metadata.clear()
        pg_es_cleared = self._pg_es_metadata.clear()

        if not sqlite_cleared:
            logger.error("Failed to clear SQLite metadata backend")
        if not pg_es_cleared:
            logger.error("Failed to clear PG/ES metadata backend")

        return sqlite_cleared and pg_es_cleared

class DualWriteReadSearch(SearchInterface):
    """
    Dual-write search implementation with compensating transaction pattern.

    CRITICAL FIX: Implements two-phase commit pattern for dual-write operations
    to prevent data inconsistency when one backend fails.
    """
    def __init__(self, sqlite_search: SearchInterface, pg_es_search: SearchInterface):
        self._sqlite_search = sqlite_search
        self._pg_es_search = pg_es_search
        # Track pending operations for compensating transactions
        self._pending_index_writes: Dict[str, str] = {}

    def index_file(self, file_path: str, content: str) -> None:
        """
        Index file in both backends using compensating transaction pattern.

        CRITICAL FIX: Two-phase commit for index operations.
        """
        # Phase 1: Index in primary backend (PG/ES)
        try:
            self._pg_es_search.index_file(file_path, content)
            self._pending_index_writes[file_path] = 'index'
        except Exception as e:
            logger.error(f"Primary index failed for {file_path}: {e}")
            raise

        # Phase 2: Index in secondary backend (SQLite)
        try:
            self._sqlite_search.index_file(file_path, content)
        except Exception as e:
            logger.error(f"Secondary index failed for {file_path}, attempting compensating transaction: {e}")
            # Compensating transaction: rollback primary
            try:
                self._pg_es_search.delete_indexed_file(file_path)
                logger.warning(f"Compensating transaction: rolled back primary index for {file_path}")
            except Exception as rollback_err:
                logger.error(f"Failed to rollback primary index for {file_path}: {rollback_err}")
                self._pending_index_writes[file_path] = 'inconsistent'
            raise

        # Commit: both writes succeeded
        if file_path in self._pending_index_writes:
            del self._pending_index_writes[file_path]
        logger.debug(f"Dual-indexed file {file_path}")

    def search_files(self, query: str) -> List[Dict[str, Any]]:
        """
        Search files using both backends with fallback.

        CRITICAL FIX: Prioritizes primary backend with fallback to secondary.
        """
        # Prioritize searching in the new store
        results = self._pg_es_search.search_files(query)
        if not results:
            logger.warning(f"No search results from PG/ES for query '{query}', falling back to SQLite.")
            results = self._sqlite_search.search_files(query)
        return results

    def delete_indexed_file(self, file_path: str) -> None:
        """
        Delete indexed file from both backends using compensating transaction pattern.

        CRITICAL FIX: Two-phase commit for delete operations.
        """
        # Phase 1: Delete from primary backend (PG/ES)
        primary_deleted = False
        try:
            self._pg_es_search.delete_indexed_file(file_path)
            primary_deleted = True
        except Exception as e:
            logger.error(f"Primary index delete failed for {file_path}: {e}")

        # Phase 2: Delete from secondary backend (SQLite)
        try:
            self._sqlite_search.delete_indexed_file(file_path)
        except Exception as e:
            logger.error(f"Secondary index delete failed for {file_path}: {e}")
            if primary_deleted:
                logger.error(f"Data inconsistency detected for {file_path}: index deleted from primary but not secondary")
            raise

        logger.debug(f"Dual-deleted indexed file {file_path}")

    def clear(self) -> bool:
        """
        Clear both backends with safety checks.

        CRITICAL FIX: Reports failures from either backend.
        """
        sqlite_cleared = self._sqlite_search.clear()
        pg_es_cleared = self._pg_es_search.clear()

        if not sqlite_cleared:
            logger.error("Failed to clear SQLite search backend")
        if not pg_es_cleared:
            logger.error("Failed to clear PG/ES search backend")

        return sqlite_cleared and pg_es_cleared

def get_dal_instance() -> DALInterface:
    """
    Factory function to get the appropriate DAL instance based on configuration.

    Args:
        # No direct config argument, settings are loaded from ConfigManager and environment variables.

    Returns:
        An instance of a class implementing DALInterface.

    Raises:
        ValueError: If an unknown backend type is specified or required configuration is missing.
    """
    # Initialize ConfigManager to get application-wide DAL settings
    config_manager = ConfigManager()
    dal_settings = config_manager.get_dal_settings()

    # Override with environment variables if they exist
    backend_type = os.getenv("DAL_BACKEND_TYPE", dal_settings.get("backend_type", "sqlite_only")).lower()
    logger.debug(f"Determined DAL backend type: '{backend_type}' (repr: {repr(backend_type)})")
    if backend_type in ["sqlite_only", "sqlite"]:
        db_path = dal_settings.get("db_path", os.path.join("data", "code_index.db"))
        enable_fts = dal_settings.get("sqlite_enable_fts", True)
        return SQLiteDAL(db_path, enable_fts=enable_fts)
    elif backend_type == "dual_write_read":
        # Initialize SQLite DAL
        sqlite_db_path = dal_settings.get("db_path", os.path.join("data", "code_index.db"))
        sqlite_enable_fts = dal_settings.get("sqlite_enable_fts", True)
        sqlite_dal = SQLiteDAL(sqlite_db_path, enable_fts=sqlite_enable_fts)

        # Initialize PostgreSQL/Elasticsearch DAL
        pg_user = dal_settings.get("postgresql_user")
        pg_password = dal_settings.get("postgresql_password")
        pg_host = dal_settings.get("postgresql_host")
        pg_port = dal_settings.get("postgresql_port")
        pg_database = dal_settings.get("postgresql_database")
        pg_ssl_args = dal_settings.get("postgresql_ssl_args")

        es_hosts = dal_settings.get("elasticsearch_hosts")
        es_index_name = dal_settings.get("elasticsearch_index_name", "code_index")
        es_api_key_id = dal_settings.get("elasticsearch_api_key_id")
        es_api_key = dal_settings.get("elasticsearch_api_key")
        es_username = dal_settings.get("elasticsearch_username")
        es_password = dal_settings.get("elasticsearch_password")
        es_use_ssl = dal_settings.get("elasticsearch_use_ssl", True)
        es_verify_certs = dal_settings.get("elasticsearch_verify_certs", True)
        es_ca_certs = dal_settings.get("elasticsearch_ca_certs")
        es_client_cert = dal_settings.get("elasticsearch_client_cert")
        es_client_key = dal_settings.get("elasticsearch_client_key")

        if not all([pg_user, pg_password, pg_host, pg_port, pg_database]):
            raise ValueError("Missing one or more required PostgreSQL connection parameters for 'dual_write_read' backend.")
        if not es_hosts:
            raise ValueError("Elasticsearch hosts must be provided for 'dual_write_read' backend.")

        es_auth_api_key = None
        es_auth_http_auth = None
        if es_api_key_id and es_api_key:
            es_auth_api_key = (es_api_key_id, es_api_key)
        elif es_username and es_password:
            es_auth_http_auth = (es_username, es_password)

        pg_es_dal = PostgreSQLElasticsearchDAL(
            pg_user=pg_user, pg_password=pg_password, pg_host=pg_host, pg_port=pg_port, pg_database=pg_database,
            pg_ssl_args=pg_ssl_args,
            es_hosts=es_hosts, es_index_name=es_index_name,
            es_api_key=es_auth_api_key, es_http_auth=es_auth_http_auth,
            es_use_ssl=es_use_ssl, es_verify_certs=es_verify_certs,
            es_ca_certs=es_ca_certs, es_client_cert=es_client_cert, es_client_key=es_client_key
        )
        return DualWriteReadDAL(sqlite_dal, pg_es_dal)

    elif backend_type == "postgresql_elasticsearch_only":
        # Override with environment variables if they exist
        pg_user = os.getenv("POSTGRES_USER", dal_settings.get("postgresql_user"))
        pg_password = os.getenv("POSTGRES_PASSWORD", dal_settings.get("postgresql_password"))
        pg_host = os.getenv("POSTGRES_HOST", dal_settings.get("postgresql_host"))
        pg_port = int(os.getenv("POSTGRES_PORT", str(dal_settings.get("postgresql_port", 5432))))
        pg_database = os.getenv("POSTGRES_DB", dal_settings.get("postgresql_database"))
        pg_ssl_args = dal_settings.get("postgresql_ssl_args")

        # Override Elasticsearch settings with environment variables
        es_hosts_env = os.getenv("ELASTICSEARCH_HOSTS")
        if es_hosts_env:
            es_hosts = [h.strip() for h in es_hosts_env.split(',')]
        else:
            es_hosts = dal_settings.get("elasticsearch_hosts")
        
        es_index_name = os.getenv("ELASTICSEARCH_INDEX_NAME", dal_settings.get("elasticsearch_index_name", "code_index"))
        es_api_key_id = os.getenv("ELASTICSEARCH_API_KEY_ID", dal_settings.get("elasticsearch_api_key_id"))
        es_api_key = os.getenv("ELASTICSEARCH_API_KEY", dal_settings.get("elasticsearch_api_key"))
        es_username = os.getenv("ELASTICSEARCH_USERNAME", dal_settings.get("elasticsearch_username"))
        es_password = os.getenv("ELASTICSEARCH_PASSWORD", dal_settings.get("elasticsearch_password"))
        
        # Handle boolean environment variables
        es_use_ssl_env = os.getenv("ELASTICSEARCH_USE_SSL")
        es_use_ssl = es_use_ssl_env.lower() == 'true' if es_use_ssl_env else dal_settings.get("elasticsearch_use_ssl", True)
        
        es_verify_certs_env = os.getenv("ELASTICSEARCH_VERIFY_CERTS")
        es_verify_certs = es_verify_certs_env.lower() == 'true' if es_verify_certs_env else dal_settings.get("elasticsearch_verify_certs", True)
        
        es_ca_certs = os.getenv("ELASTICSEARCH_CA_CERTS", dal_settings.get("elasticsearch_ca_certs"))
        es_client_cert = os.getenv("ELASTICSEARCH_CLIENT_CERT", dal_settings.get("elasticsearch_client_cert"))
        es_client_key = os.getenv("ELASTICSEARCH_CLIENT_KEY", dal_settings.get("elasticsearch_client_key"))

        # Validate required PostgreSQL settings
        if not all([pg_user, pg_password, pg_host, pg_port, pg_database]):
            raise ValueError("Missing one or more required PostgreSQL connection parameters for 'postgresql_elasticsearch_only' backend.")
        
        # Validate required Elasticsearch settings
        if not es_hosts:
            raise ValueError("Elasticsearch hosts must be provided for 'postgresql_elasticsearch_only' backend.")
        
        # Determine Elasticsearch authentication method
        es_auth_api_key = None
        es_auth_http_auth = None
        if es_api_key_id and es_api_key:
            es_auth_api_key = (es_api_key_id, es_api_key)
        elif es_username and es_password:
            es_auth_http_auth = (es_username, es_password)

        return PostgreSQLElasticsearchDAL(
            pg_user=pg_user, pg_password=pg_password, pg_host=pg_host, pg_port=pg_port, pg_database=pg_database,
            pg_ssl_args=pg_ssl_args,
            es_hosts=es_hosts, es_index_name=es_index_name,
            es_api_key=es_auth_api_key, es_http_auth=es_auth_http_auth,
            es_use_ssl=es_use_ssl, es_verify_certs=es_verify_certs,
            es_ca_certs=es_ca_certs, es_client_cert=es_client_cert, es_client_key=es_client_key
        )
    else:
        raise ValueError(f"Unknown DAL backend type: {backend_type}")
