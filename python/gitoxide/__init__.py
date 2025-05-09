"""
Gitoxide - Python bindings for a pure Rust implementation of Git.

This package provides a Pythonic API for working with Git repositories,
built on top of the Gitoxide library.
"""

# Import directly from the native module
from gitoxide.gitoxide import (
    Repository,
    __version__,
    # All error types
    GitoxideError,
    RepositoryError,
    ObjectError,
    ReferenceError,
    ConfigError,
    IndexError,
    DiffError,
    TraverseError,
    WorktreeError,
    RevisionError,
    RemoteError,
    TransportError,
    ProtocolError,
    PackError,
    FSError
)

# Re-export main symbols
__all__ = [
    "Repository",
    "__version__",
    # Error types
    "GitoxideError",
    "RepositoryError",
    "ObjectError",
    "ReferenceError",
    "ConfigError",
    "IndexError",
    "DiffError",
    "TraverseError",
    "WorktreeError",
    "RevisionError",
    "RemoteError",
    "TransportError",
    "ProtocolError",
    "PackError",
    "FSError"
]
