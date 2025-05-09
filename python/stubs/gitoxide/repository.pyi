"""
Type stubs for repository-related functionality in gitoxide.
"""

from typing import Optional, List, Dict, Any, Union, Tuple, overload
import pathlib


class Reference:
    """A Git reference."""
    name: str
    target: str
    is_symbolic: bool


class Header:
    """Git object header information."""
    kind: str
    size: int


class Object:
    """A Git object."""
    id: str
    kind: str
    data: bytes


class Blob(Object):
    """A Git blob."""
    pass


class Commit(Object):
    """A Git commit."""
    pass


class Tree(Object):
    """A Git tree."""
    pass


class Tag(Object):
    """A Git tag."""
    pass


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

    def is_shallow(self) -> bool:
        """
        Check if the repository is a shallow clone.

        Returns:
            True if the repository is a shallow clone, False otherwise
        """
        ...

    def shallow_commits(self) -> Optional[List[str]]:
        """
        Get a list of commit IDs that are shallow in this repository.

        Returns:
            List of commit IDs that form the shallow boundary, or None if the repository is not shallow
        """
        ...

    def shallow_file(self) -> str:
        """
        Get the path to the repository's shallow file.

        Returns:
            Path to the shallow file
        """
        ...

    def object_hash(self) -> str:
        """
        Get the object hash algorithm used by the repository.

        Returns:
            String representation of the hash algorithm (e.g., "Sha1")
        """
        ...

    def merge_bases(self, one: str, others: List[str]) -> List[str]:
        """
        Find all merge bases between one commit and multiple other commits.

        Args:
            one: First commit ID as a string
            others: List of other commit IDs to find merge bases with

        Returns:
            List of commit IDs that are merge bases

        Raises:
            RepositoryError: If one of the commit IDs is invalid
        """
        ...

    def merge_base(self, one: str, two: str) -> str:
        """
        Find the best merge base between two commits.

        Args:
            one: First commit ID as a string
            two: Second commit ID as a string

        Returns:
            The commit ID of the merge base

        Raises:
            RepositoryError: If a commit ID is invalid or no merge base exists
        """
        ...

    def rev_parse(self, spec: str) -> str:
        """
        Parse a revision specification and return a single commit/object ID.

        Args:
            spec: The revision specification (e.g., "HEAD", "main~3", "v1.0^{}")

        Returns:
            The object ID that the revision specification resolves to

        Raises:
            RepositoryError: If the specification is invalid or cannot be resolved
        """
        ...

    def find_object(self, id: str) -> Object:
        """
        Find a Git object by its ID.

        Args:
            id: Object ID to find

        Returns:
            The found object

        Raises:
            ObjectError: If the object cannot be found
        """
        ...

    def find_blob(self, id: str) -> Blob:
        """
        Find a Git blob by its ID.

        Args:
            id: Blob ID to find

        Returns:
            The found blob

        Raises:
            ObjectError: If the blob cannot be found
        """
        ...

    def find_commit(self, id: str) -> Commit:
        """
        Find a Git commit by its ID.

        Args:
            id: Commit ID to find

        Returns:
            The found commit

        Raises:
            ObjectError: If the commit cannot be found
        """
        ...

    def find_tree(self, id: str) -> Tree:
        """
        Find a Git tree by its ID.

        Args:
            id: Tree ID to find

        Returns:
            The found tree

        Raises:
            ObjectError: If the tree cannot be found
        """
        ...

    def find_tag(self, id: str) -> Tag:
        """
        Find a Git tag by its ID.

        Args:
            id: Tag ID to find

        Returns:
            The found tag

        Raises:
            ObjectError: If the tag cannot be found
        """
        ...

    def find_header(self, id: str) -> Header:
        """
        Find header information for a Git object.

        Args:
            id: Object ID to find

        Returns:
            Header information for the object

        Raises:
            ObjectError: If the object cannot be found
        """
        ...

    def has_object(self, id: str) -> bool:
        """
        Check if an object exists in the repository.

        Args:
            id: Object ID to check

        Returns:
            True if the object exists, False otherwise
        """
        ...

    def references(self) -> List[Reference]:
        """
        Get all references in the repository.

        Returns:
            List of references
        """
        ...

    def reference_names(self) -> List[str]:
        """
        Get names of all references in the repository.

        Returns:
            List of reference names
        """
        ...

    def find_reference(self, name: str) -> Reference:
        """
        Find a reference by name.

        Args:
            name: Name of the reference to find

        Returns:
            The found reference

        Raises:
            ReferenceError: If the reference cannot be found
        """
        ...

    def create_reference(self, name: str, target: str, is_symbolic: bool, force: bool) -> Reference:
        """
        Create a new reference.

        Args:
            name: Name of the reference to create
            target: Target of the reference (object ID or another reference name)
            is_symbolic: Whether the reference is symbolic
            force: Whether to overwrite an existing reference

        Returns:
            The created reference

        Raises:
            ReferenceError: If the reference cannot be created
        """
        ...
