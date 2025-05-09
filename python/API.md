# Gitoxide Python API

This document outlines the current API exposed by the Gitoxide Python bindings.

## Installation

```bash
# Install directly from the repository (development mode)
pip install -e .

# Or build and install the wheel
pip install .
```

## Main Module

The main `gitoxide` module directly exposes the following:

### Classes

#### `Repository`

For working with Git repositories.

```python
import gitoxide

# Open an existing repository
repo = gitoxide.Repository.open('/path/to/repo')

# Initialize a new repository
repo = gitoxide.Repository.init('/path/to/new/repo', bare=False)
```

**Methods:**

- `open(path)` (classmethod) - Open an existing Git repository at the given path
- `init(path, bare=False)` (classmethod) - Initialize a new Git repository
- `git_dir()` - Get the path to the repository's .git directory
- `work_dir()` - Get the path to the repository's working directory (None for bare repos)
- `is_bare()` - Check if the repository is bare
- `head()` - Get the current HEAD reference as a string

### Exception Types

The module defines several exception types for error handling:

- `GitoxideError` - Base exception for all gitoxide errors
- `RepositoryError` - Repository-related errors
- `ObjectError` - Git object-related errors
- `ReferenceError` - Reference-related errors

### Constants

- `__version__` - The version of the gitoxide Python bindings

## Type Stubs

Type stubs are provided for better IDE autocompletion and static type checking. The stubs are distributed with the package and defined in `.pyi` files.

### Available Type Definitions

- `Repository` - Fully typed with parameter and return type annotations
- Exception classes - All properly typed as subclasses of Python's built-in `Exception` class
- `asyncio` module - Type stubs for the async API variants

### Path Support

The API supports both string paths and `pathlib.Path` objects:

```python
import pathlib
import gitoxide

# Using string paths
repo1 = gitoxide.Repository.open('/path/to/repo')

# Using pathlib.Path objects
repo2 = gitoxide.Repository.open(pathlib.Path('/path/to/repo'))
```

## Build Configuration

The Python bindings can be built with different feature sets:

- `sync` (default) - Synchronous API only
- `async` - Includes asynchronous API support

Configure in `pyproject.toml`:

```toml
[tool.maturin]
features = ["sync"]  # or ["sync", "async"] for both APIs
```

## Future Additions

Planned additions to the API include:

1. Object handling (commit, tree, blob)
2. Reference management
3. Remote operations (fetch, push)
4. Diff and status functionality
5. Index operations
6. Configuration handling
7. Async versions of all operations