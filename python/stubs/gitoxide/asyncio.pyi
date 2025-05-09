"""
Type stubs for the gitoxide.asyncio Python bindings.

This module provides asynchronous variants of the gitoxide functionality.
"""

from typing import Optional, overload
import pathlib
import asyncio

# Async Repository class
class Repository:
    """An asynchronous Git repository interface."""

    @classmethod
    @overload
    async def open(cls, path: str) -> "Repository":
        """
        Asynchronously open an existing repository at the given path.

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
    async def open(cls, path: pathlib.Path) -> "Repository":
        """
        Asynchronously open an existing repository at the given path.

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
    async def init(cls, path: str, bare: bool = False) -> "Repository":
        """
        Asynchronously initialize a new repository at the given path.

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
    async def init(cls, path: pathlib.Path, bare: bool = False) -> "Repository":
        """
        Asynchronously initialize a new repository at the given path.

        Args:
            path: Path where the repository will be created
            bare: If True, create a bare repository without a working directory

        Returns:
            Repository object

        Raises:
            RepositoryError: If the repository cannot be initialized
        """
        ...

    async def git_dir(self) -> str:
        """
        Asynchronously get the path to the repository's .git directory.

        Returns:
            String path to the .git directory
        """
        ...

    async def work_dir(self) -> Optional[str]:
        """
        Asynchronously get the path to the repository's working directory, if it has one.

        Returns:
            String path to the working directory, or None for bare repositories
        """
        ...

    async def is_bare(self) -> bool:
        """
        Asynchronously check if the repository is bare (has no working directory).

        Returns:
            True if the repository is bare, False otherwise
        """
        ...

    async def head(self) -> str:
        """
        Asynchronously get the name of the HEAD reference (e.g., "refs/heads/main") or
        the commit ID if HEAD is detached.

        Returns:
            String with the reference name or commit ID

        Raises:
            RepositoryError: If HEAD is not set or cannot be read
        """
        ...