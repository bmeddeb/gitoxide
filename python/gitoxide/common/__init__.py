"""
Common utilities and types for Gitoxide.

This module provides shared functionality used by both the synchronous and asynchronous APIs.
"""

from gitoxide.common.errors import (
    GitoxideError,
    RepositoryError,
    ObjectError,
    ReferenceError,
    ConfigError,
    CheckoutError,
    RemoteError,
    IndexError,
)