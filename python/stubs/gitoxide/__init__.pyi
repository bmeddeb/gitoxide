"""
Type stubs for the gitoxide Python bindings.

This package provides type hints for working with the gitoxide library.
"""

from typing import Optional, overload
import os
import pathlib

# Version information
__version__: str

# Base exception classes
class GitoxideError(Exception):
    """Base exception for all gitoxide errors."""
    pass

class RepositoryError(GitoxideError):
    """Repository-related errors."""
    pass

class ObjectError(GitoxideError):
    """Git object-related errors."""
    pass

class ReferenceError(GitoxideError):
    """Git reference-related errors."""
    pass

# Main Repository class
class Repository:
    """A Git repository."""

    @classmethod
    @overload
    def open(cls, path: str) -> "Repository":
        """
        Open an existing repository at the given path.

        Args:
            path: Path to the repository (either .git directory or working directory)

        Returns:
            Repository object

        Raises:
            RepositoryError: If the repository cannot be opened
        """
        ...

    @classmethod
    @overload
    def open(cls, path: pathlib.Path) -> "Repository":
        """
        Open an existing repository at the given path.

        Args:
            path: Path to the repository (either .git directory or working directory)

        Returns:
            Repository object

        Raises:
            RepositoryError: If the repository cannot be opened
        """
        ...

    @classmethod
    @overload
    def init(cls, path: str, bare: bool = False) -> "Repository":
        """
        Initialize a new repository at the given path.

        Args:
            path: Path where the repository will be created
            bare: If True, create a bare repository without a working directory

        Returns:
            Repository object

        Raises:
            RepositoryError: If the repository cannot be initialized
        """
        ...

    @classmethod
    @overload
    def init(cls, path: pathlib.Path, bare: bool = False) -> "Repository":
        """
        Initialize a new repository at the given path.

        Args:
            path: Path where the repository will be created
            bare: If True, create a bare repository without a working directory

        Returns:
            Repository object

        Raises:
            RepositoryError: If the repository cannot be initialized
        """
        ...

    def git_dir(self) -> str:
        """
        Get the path to the repository's .git directory.

        Returns:
            String path to the .git directory
        """
        ...

    def work_dir(self) -> Optional[str]:
        """
        Get the path to the repository's working directory, if it has one.

        Returns:
            String path to the working directory, or None for bare repositories
        """
        ...

    def is_bare(self) -> bool:
        """
        Check if the repository is bare (has no working directory).

        Returns:
            True if the repository is bare, False otherwise
        """
        ...

    def head(self) -> str:
        """
        Get the name of the HEAD reference (e.g., "refs/heads/main") or
        the commit ID if HEAD is detached.

        Returns:
            String with the reference name or commit ID

        Raises:
            RepositoryError: If HEAD is not set or cannot be read
        """
        ...