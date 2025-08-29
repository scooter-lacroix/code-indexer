"""
PostgreSQL-based storage backend for file metadata.
"""

import logging
from typing import Any, Dict, Optional, List, Tuple, Iterator
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from .storage_interface import StorageInterface, FileMetadataInterface, DALInterface, SearchInterface

logger = logging.getLogger(__name__)

Base = declarative_base()

class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False, index=True)
    file_type = Column(String, nullable=False)
    extension = Column(String)
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<File(file_path='{self.file_path}', file_type='{self.file_type}')>"

class FileVersion(Base):
    __tablename__ = 'file_versions'
    id = Column(String, primary_key=True) # version_id
    file_path = Column(String, nullable=False, index=True)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=False)
    content = Column(Text, nullable=False)
    hash = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    size = Column(Integer, nullable=False)

    file = relationship("File", back_populates="versions")
    
    def __repr__(self):
        return f"<FileVersion(id='{self.id}', file_path='{self.file_path}')>"

class FileDiff(Base):
    __tablename__ = 'file_diffs'
    id = Column(String, primary_key=True) # diff_id
    file_path = Column(String, nullable=False, index=True)
    previous_version_id = Column(String, ForeignKey('file_versions.id'), nullable=True)
    current_version_id = Column(String, ForeignKey('file_versions.id'), nullable=False)
    diff_content = Column(Text, nullable=False)
    diff_type = Column(String, nullable=False)
    operation_type = Column(String, nullable=False)
    operation_details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    previous_version = relationship("FileVersion", foreign_keys=[previous_version_id])
    current_version = relationship("FileVersion", foreign_keys=[current_version_id])

    def __repr__(self):
        return f"<FileDiff(id='{self.id}', file_path='{self.file_path}', operation='{self.operation_type}')>"


class PostgreSQLStorage(StorageInterface):
    """
    PostgreSQL-based generic key-value storage.
    This implements the StorageInterface.
    """
    def __init__(self, db_user: str, db_password: str, db_host: str, db_port: int, db_name: str,
                 ssl_args: Optional[Dict[str, Any]] = None):
        # Connection details should ideally come from a secure secrets management system (e.g., HashiCorp Vault, AWS Secrets Manager)
        # and not be hardcoded or passed directly from insecure sources.
        self.connection_string = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        connect_args = {}
        if ssl_args:
            # Example ssl_args: {'sslmode': 'require', 'sslrootcert': '/path/to/ca.pem', 'sslcert': '/path/to/client.crt', 'sslkey': '/path/to/client.key'}
            connect_args['ssl'] = ssl_args

        self.engine = create_engine(self.connection_string, poolclass=QueuePool, pool_size=10, max_overflow=20, connect_args=connect_args)
        Base.metadata.create_all(self.engine) # Create tables if they don't exist
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Initializing PostgreSQLStorage for database: {db_name} on {db_host}:{db_port}")

    def put(self, key: str, value: Any) -> bool:
        """Store a key-value pair in PostgreSQL."""
        try:
            with self.Session() as session:
                # Assuming a simple key-value table named 'kv_store'
                # with columns 'key' TEXT PRIMARY KEY and 'value_json' JSONB
                # This is a placeholder, actual implementation might vary
                # based on the specific schema for generic storage.
                # For now, we'll just log and return True as this is not the primary focus.
                logger.warning("Generic key-value put not fully implemented for PostgreSQLStorage.")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error putting key-value pair: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key from PostgreSQL."""
        try:
            with self.Session() as session:
                logger.warning("Generic key-value get not fully implemented for PostgreSQLStorage.")
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting key-value pair: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a key-value pair from PostgreSQL."""
        try:
            with self.Session() as session:
                logger.warning("Generic key-value delete not fully implemented for PostgreSQLStorage.")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting key-value pair: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists in PostgreSQL."""
        try:
            with self.Session() as session:
                logger.warning("Generic key-value exists not fully implemented for PostgreSQLStorage.")
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error checking key existence: {e}")
            return False

    def keys(self, pattern: Optional[str] = None) -> Iterator[str]:
        """Iterate over keys in PostgreSQL, optionally filtered by pattern."""
        logger.warning("Generic key-value keys iteration not fully implemented for PostgreSQLStorage.")
        yield from []

    def items(self, pattern: Optional[str] = None) -> Iterator[Tuple[str, Any]]:
        """Iterate over key-value pairs in PostgreSQL, optionally filtered by pattern."""
        logger.warning("Generic key-value items iteration not fully implemented for PostgreSQLStorage.")
        yield from []

    def clear(self) -> bool:
        """Clear all data from the PostgreSQL key-value store."""
        try:
            with self.Session() as session:
                logger.warning("Generic key-value clear not fully implemented for PostgreSQLStorage.")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error clearing key-value store: {e}")
            return False

    def size(self) -> int:
        """Get the number of stored items in PostgreSQL."""
        try:
            with self.Session() as session:
                logger.warning("Generic key-value size not fully implemented for PostgreSQLStorage.")
                return 0
        except SQLAlchemyError as e:
            logger.error(f"Error getting key-value store size: {e}")
            return 0

    def close(self) -> None:
        """Close the PostgreSQL key-value storage backend."""
        logger.info("PostgreSQLStorage closed. Engine disposed.")
        self.engine.dispose()
    
    def flush(self) -> bool:
        """Flush any pending operations to PostgreSQL."""
        logger.debug("PostgreSQL: Flushing operations (no-op for SQLAlchemy sessions, commit handles it)")
        return True


class PostgreSQLFileMetadata(FileMetadataInterface):
    """
    PostgreSQL-based file metadata storage.
    This implements the FileMetadataInterface.
    """
    def __init__(self, db_user: str, db_password: str, db_host: str, db_port: int, db_name: str,
                 ssl_args: Optional[Dict[str, Any]] = None):
        # Connection details should ideally come from a secure secrets management system (e.g., HashiCorp Vault, AWS Secrets Manager)
        # and not be hardcoded or passed directly from insecure sources.
        self.connection_string = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        connect_args = {}
        if ssl_args:
            # Example ssl_args: {'sslmode': 'require', 'sslrootcert': '/path/to/ca.pem', 'sslcert': '/path/to/client.crt', 'sslkey': '/path/to/client.key'}
            connect_args['ssl'] = ssl_args

        self.engine = create_engine(self.connection_string, poolclass=QueuePool, pool_size=10, max_overflow=20, connect_args=connect_args)
        Base.metadata.create_all(self.engine) # Ensure tables exist
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Initializing PostgreSQLFileMetadata for database: {db_name} on {db_host}:{db_port}")

    def add_file(self, file_path: str, file_type: str, extension: str,
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a file's metadata to PostgreSQL."""
        try:
            with self.Session() as session:
                file_record = session.query(File).filter_by(file_path=file_path).first()
                if file_record:
                    file_record.file_type = file_type
                    file_record.extension = extension
                    file_record.metadata_json = metadata
                    logger.debug(f"PostgreSQL: Updated file {file_path}")
                else:
                    file_record = File(file_path=file_path, file_type=file_type, extension=extension, metadata_json=metadata)
                    session.add(file_record)
                    logger.debug(f"PostgreSQL: Added file {file_path}")
                session.commit()
                return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error adding/updating file {file_path}: {e}")
            return False

    def remove_file(self, file_path: str) -> bool:
        """Remove a file's metadata from PostgreSQL."""
        try:
            with self.Session() as session:
                file_record = session.query(File).filter_by(file_path=file_path).first()
                if file_record:
                    session.delete(file_record)
                    session.commit()
                    logger.debug(f"PostgreSQL: Removed file {file_path}")
                    return True
                logger.debug(f"PostgreSQL: File {file_path} not found for removal.")
                return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error removing file {file_path}: {e}")
            return False

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a file from PostgreSQL."""
        try:
            with self.Session() as session:
                file_record = session.query(File).filter_by(file_path=file_path).first()
                if file_record:
                    return {
                        "id": file_record.id,
                        "file_path": file_record.file_path,
                        "file_type": file_record.file_type,
                        "extension": file_record.extension,
                        "metadata": file_record.metadata_json,
                        "created_at": file_record.created_at.isoformat(),
                        "updated_at": file_record.updated_at.isoformat()
                    }
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None

    def get_directory_structure(self, directory_path: str = "") -> Dict[str, Any]:
        """Get the directory structure from PostgreSQL."""
        try:
            with self.Session() as session:
                # This is a simplified implementation. A full directory structure
                # would require more complex tree traversal logic.
                # For now, it returns a flat list of files within the given path.
                query = session.query(File)
                if directory_path:
                    query = query.filter(File.file_path.like(f"{directory_path}%"))
                
                structure = {}
                for file_record in query.all():
                    path_parts = file_record.file_path.split('/')
                    current_level = structure
                    for part in path_parts[:-1]:
                        if part not in current_level:
                            current_level[part] = {}
                        current_level = current_level[part]
                    current_level[path_parts[-1]] = {
                        "type": file_record.file_type,
                        "extension": file_record.extension,
                        "metadata": file_record.metadata_json
                    }
                return structure
        except SQLAlchemyError as e:
            logger.error(f"Error getting directory structure for {directory_path}: {e}")
            return {}

    def get_all_files(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get all files' metadata from PostgreSQL."""
        try:
            with self.Session() as session:
                all_files = []
                for file_record in session.query(File).all():
                    all_files.append((
                        file_record.file_path,
                        {
                            "id": file_record.id,
                            "file_path": file_record.file_path,
                            "file_type": file_record.file_type,
                            "extension": file_record.extension,
                            "metadata": file_record.metadata_json,
                            "created_at": file_record.created_at.isoformat(),
                            "updated_at": file_record.updated_at.isoformat()
                        }
                    ))
                return all_files
        except SQLAlchemyError as e:
            logger.error(f"Error getting all files: {e}")
            return []

    def insert_file_version(self, version_id: str, file_path: str, content: str, hash: str, timestamp: str, size: int) -> bool:
        """Inserts a new file version into PostgreSQL."""
        try:
            with self.Session() as session:
                file_record = session.query(File).filter_by(file_path=file_path).first()
                if not file_record:
                    logger.error(f"File {file_path} not found when trying to insert version {version_id}.")
                    return False
                
                # Convert timestamp string to datetime object
                try:
                    dt_timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    logger.error(f"Invalid timestamp format for version {version_id}: {timestamp}")
                    return False

                file_version = FileVersion(
                    id=version_id,
                    file_path=file_path,
                    file_id=file_record.id,
                    content=content,
                    hash=hash,
                    timestamp=dt_timestamp,
                    size=size
                )
                session.add(file_version)
                session.commit()
                logger.debug(f"PostgreSQL: Inserted file version {version_id} for {file_path}")
                return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting file version {version_id} for {file_path}: {e}")
            return False

    def get_file_version(self, version_id: str) -> Optional[Dict]:
        """Retrieves a file version by its ID from PostgreSQL."""
        try:
            with self.Session() as session:
                file_version = session.query(FileVersion).filter_by(id=version_id).first()
                if file_version:
                    return {
                        "version_id": file_version.id,
                        "file_path": file_version.file_path,
                        "content": file_version.content,
                        "hash": file_version.hash,
                        "timestamp": file_version.timestamp.isoformat(),
                        "size": file_version.size
                    }
                return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting file version {version_id}: {e}")
            return None

    def get_file_versions_for_path(self, file_path: str) -> List[Dict]:
        """Retrieves all versions for a given file path from PostgreSQL."""
        logger.debug(f"PostgreSQL get_file_versions_for_path called with file_path: {file_path}")
        try:
            with self.Session() as session:
                versions = session.query(FileVersion).filter_by(file_path=file_path).order_by(FileVersion.timestamp).all()
                logger.debug(f"Found {len(versions)} versions for path {file_path}")
                result = [
                    {
                        "version_id": v.id,
                        "file_path": v.file_path,
                        "content": v.content,
                        "hash": v.hash,
                        "timestamp": v.timestamp.isoformat(),
                        "size": v.size
                    } for v in versions
                ]
                if versions:
                    logger.debug(f"Sample version data: version_id={versions[0].id}, timestamp={versions[0].timestamp}")
                return result
        except SQLAlchemyError as e:
            logger.error(f"Error getting file versions for path {file_path}: {e}")
            return []

    def insert_file_diff(self, diff_id: str, file_path: str, previous_version_id: Optional[str], current_version_id: str, diff_content: str, diff_type: str, operation_type: str, operation_details: Optional[str], timestamp: str) -> bool:
        """Inserts a new file diff into PostgreSQL."""
        try:
            with self.Session() as session:
                # Check if current_version_id exists
                current_version = session.query(FileVersion).filter_by(id=current_version_id).first()
                if not current_version:
                    logger.error(f"Current version ID {current_version_id} not found for diff {diff_id}.")
                    return False

                # Check if previous_version_id exists if provided
                if previous_version_id:
                    previous_version = session.query(FileVersion).filter_by(id=previous_version_id).first()
                    if not previous_version:
                        logger.error(f"Previous version ID {previous_version_id} not found for diff {diff_id}.")
                        return False
                
                # Convert timestamp string to datetime object
                try:
                    dt_timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    logger.error(f"Invalid timestamp format for diff {diff_id}: {timestamp}")
                    return False

                file_diff = FileDiff(
                    id=diff_id,
                    file_path=file_path,
                    previous_version_id=previous_version_id,
                    current_version_id=current_version_id,
                    diff_content=diff_content,
                    diff_type=diff_type,
                    operation_type=operation_type,
                    operation_details=operation_details,
                    timestamp=dt_timestamp
                )
                session.add(file_diff)
                session.commit()
                logger.debug(f"PostgreSQL: Inserted file diff {diff_id} for {file_path}")
                return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error inserting file diff {diff_id} for {file_path}: {e}")
            return False

    def get_file_diffs_for_path(self, file_path: str) -> List[Dict]:
        """Retrieves all diffs for a given file path from PostgreSQL."""
        logger.debug(f"PostgreSQL get_file_diffs_for_path called with file_path: {file_path}")
        try:
            with self.Session() as session:
                diffs = session.query(FileDiff).filter_by(file_path=file_path).order_by(FileDiff.timestamp).all()
                logger.debug(f"Found {len(diffs)} diffs for path {file_path}")
                result = [
                    {
                        "diff_id": d.id,
                        "file_path": d.file_path,
                        "previous_version_id": d.previous_version_id,
                        "current_version_id": d.current_version_id,
                        "diff_content": d.diff_content,
                        "diff_type": d.diff_type,
                        "operation_type": d.operation_type,
                        "operation_details": d.operation_details,
                        "timestamp": d.timestamp.isoformat()
                    } for d in diffs
                ]
                if diffs:
                    logger.debug(f"Sample diff data: diff_id={diffs[0].id}, operation_type={diffs[0].operation_type}")
                return result
        except SQLAlchemyError as e:
            logger.error(f"Error getting file diffs for path {file_path}: {e}")
            return []
    
    def clear(self) -> bool:
        """Clear all file metadata, versions, and diffs from PostgreSQL."""
        try:
            with self.Session() as session:
                # Order of deletion matters due to foreign key constraints
                session.query(FileDiff).delete()
                session.query(FileVersion).delete()
                session.query(File).delete()
                session.commit()
                logger.debug("PostgreSQL: Cleared all file metadata, versions, and diffs.")
                return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error clearing all file metadata: {e}")
            return False
    
    def size(self) -> int:
        """Get the number of files in the PostgreSQL metadata store."""
        try:
            with self.Session() as session:
                count = session.query(File).count()
                logger.debug(f"PostgreSQL: File metadata size is {count}")
                return count
        except SQLAlchemyError as e:
            logger.error(f"Error getting file metadata size: {e}")
            return 0
    
    def flush(self) -> bool:
        """Flush any pending operations to PostgreSQL."""
        logger.debug("PostgreSQL: Flushing operations (no-op for SQLAlchemy sessions, commit handles it)")
        return True
    
    def close(self) -> None:
        """Close the PostgreSQL file metadata backend."""
        logger.info("PostgreSQLFileMetadata closed. Engine disposed.")
        self.engine.dispose()