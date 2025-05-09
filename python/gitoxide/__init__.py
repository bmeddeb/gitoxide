"""
Gitoxide - Python bindings for a pure Rust implementation of Git.

This package provides a Pythonic API for working with Git repositories,
built on top of the Gitoxide library.
"""

from . import sync, asyncio, common

__version__ = sync.__version__