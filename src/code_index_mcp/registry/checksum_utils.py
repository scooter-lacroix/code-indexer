"""
Shared checksum utilities for the meta-registry system.

This module provides common checksum functions used across multiple
registry modules to avoid code duplication.
"""

import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def compute_sha256_checksum(file_path: str | Path) -> str:
    """
    Compute SHA-256 checksum of a file.

    This function reads the file in chunks to handle large files
    efficiently without loading the entire file into memory.

    Args:
        file_path: Path to the file to checksum

    Returns:
        Hexadecimal SHA-256 checksum string (64 characters)

    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If the file cannot be read due to permissions
        IOError: If there's an error reading the file
        OSError: For other filesystem-related errors

    Examples:
        >>> compute_sha256_checksum("/path/to/file.txt")
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

        >>> compute_sha256_checksum(Path("/path/to/file.txt"))
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    """
    file_path = Path(file_path)

    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check if it's a file (not a directory)
    if not file_path.is_file():
        raise IOError(f"Path is not a file: {file_path}")

    sha256 = hashlib.sha256()

    try:
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
    except PermissionError as e:
        logger.error(f"Permission denied reading file {file_path}: {e}")
        raise
    except (IOError, OSError) as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise

    checksum = sha256.hexdigest()
    logger.debug(f"Computed SHA-256 checksum for {file_path}: {checksum}")
    return checksum


def compute_sha256_hash(data: str | bytes) -> str:
    """
    Compute SHA-256 hash of a string or bytes.

    This is useful for hashing small data structures, configuration
    strings, or other in-memory data.

    Args:
        data: String or bytes to hash

    Returns:
        Hexadecimal SHA-256 hash string (64 characters)

    Examples:
        >>> compute_sha256_hash("hello world")
        'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'

        >>> compute_sha256_hash(b"hello world")
        'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    sha256 = hashlib.sha256(data)
    hash_hex = sha256.hexdigest()
    logger.debug(f"Computed SHA-256 hash: {hash_hex}")
    return hash_hex
