"""
Type stubs for the gitoxide Python bindings.

This package provides type hints for working with the gitoxide library.
"""

from .repository import (
    Repository,
    Reference,
    Object,
    Blob,
    Commit,
    Tree,
    Tag,
    Header
)
from .errors import (
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
from typing import Optional
import pathlib

# Version information
__version__: str

# Flag indicating if async support is available
ASYNC_AVAILABLE: bool

# Import errors

# Import repository classes

# Import asyncio module if available
try:
    from . import asyncio
except ImportError:
    pass
