"""
Type stubs for error types in gitoxide.
"""


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


class ConfigError(GitoxideError):
    """Configuration-related errors."""
    pass


class IndexError(GitoxideError):
    """Git index-related errors."""
    pass


class DiffError(GitoxideError):
    """Diff-related errors."""
    pass


class TraverseError(GitoxideError):
    """Traverse-related errors."""
    pass


class WorktreeError(GitoxideError):
    """Working tree related errors."""
    pass


class RevisionError(GitoxideError):
    """Revision specification parsing errors."""
    pass


class RemoteError(GitoxideError):
    """Remote operations errors."""
    pass


class TransportError(GitoxideError):
    """Transport protocol errors."""
    pass


class ProtocolError(GitoxideError):
    """Git protocol errors."""
    pass


class PackError(GitoxideError):
    """Pack file related errors."""
    pass


class FSError(GitoxideError):
    """I/O and file system errors."""
    pass
