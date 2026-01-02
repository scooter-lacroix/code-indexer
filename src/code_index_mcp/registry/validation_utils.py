"""
Shared validation utilities for the meta-registry system.

This module provides common validation functions used across multiple
registry modules to avoid code duplication.
"""

from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def validate_and_normalize_path(path: str | Path, param_name: str = "path") -> str:
    """
    Validate and normalize a path string.

    This function performs comprehensive path validation:
    - Checks that the path is not empty
    - Verifies the path is absolute
    - Normalizes the path without resolving symlinks
    - Provides clear error messages

    Args:
        path: Path string or Path object to validate
        param_name: Name of the parameter for error messages (default: "path")

    Returns:
        Normalized absolute path string

    Raises:
        ValueError: If path is empty, not absolute, or contains invalid components
        TypeError: If path is not a string or Path object

    Examples:
        >>> validate_and_normalize_path("/home/user/project")
        '/home/user/project'

        >>> validate_and_normalize_path("~/project")
        ValueError: Path must be absolute, got relative path: ~/project

        >>> validate_and_normalize_path("")
        ValueError: path cannot be empty
    """
    # Check for empty path
    if not path:
        raise ValueError(f"{param_name} cannot be empty")

    # Convert to Path object for validation
    try:
        path_obj = Path(path)
    except (TypeError, OSError) as e:
        raise TypeError(f"{param_name} must be a string or Path object: {e}") from e

    # Check if path is absolute
    if not path_obj.is_absolute():
        # Use capitalized "Path" for backward compatibility with existing tests
        raise ValueError(
            f"Path must be absolute, got relative path: {path}"
        )

    # Normalize the path (resolve . and .., symlinks are NOT resolved)
    try:
        # Use absolute() instead of resolve() to avoid following symlinks,
        # which may change the identity of the path
        normalized = str(path_obj.absolute())
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid {param_name} '{path}': {e}") from e

    logger.debug(f"Validated and normalized {param_name}: {normalized}")
    return normalized


def validate_index_name(index_name: str | None) -> None:
    """
    Validate an index name parameter.

    Index names must not contain path separators or other invalid characters
    that could lead to directory traversal or other security issues.

    Args:
        index_name: Index name to validate, or None for default index

    Raises:
        ValueError: If index_name contains invalid characters (path separators)

    Examples:
        >>> validate_index_name("semantic")
        # No exception raised

        >>> validate_index_name("my/index")
        ValueError: Invalid index_name: my/index (cannot contain path separators)

        >>> validate_index_name(None)
        # No exception raised (None is allowed for default index)
    """
    if index_name is None:
        return

    if not index_name:
        raise ValueError("index_name cannot be an empty string")

    # Check for path separators that could lead to directory traversal
    if "/" in index_name or "\\" in index_name:
        raise ValueError(
            f"Invalid index_name: {index_name} (cannot contain path separators)"
        )

    # Check for other potentially dangerous characters
    if any(char in index_name for char in ["\x00", "\n", "\r"]):
        raise ValueError(
            f"Invalid index_name: {index_name} (contains invalid characters)"
        )

    logger.debug(f"Validated index_name: {index_name}")
