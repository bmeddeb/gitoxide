# Gitoxide Python API

This document outlines the current API exposed by the Gitoxide Python bindings.

## Installation

```bash
# Install directly from the repository (development mode)
pip install -e .

# Or build and install the wheel
pip install .

# For async support
pip install -e . --config-settings="-C features=async"
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

**Basic Repository Methods:**

- `open(path)` (classmethod) - Open an existing Git repository at the given path
- `init(path, bare=False)` (classmethod) - Initialize a new Git repository
- `git_dir()` - Get the path to the repository's .git directory
- `work_dir()` - Get the path to the repository's working directory (None for bare repos)
- `is_bare()` - Check if the repository is bare
- `head()` - Get the current HEAD reference as a string
- `is_shallow()` - Check if the repository is a shallow clone
- `shallow_commits()` - Get list of shallow commits (None if not a shallow clone)
- `shallow_file()` - Get path to the shallow file
- `object_hash()` - Get hash algorithm used in this repository (e.g., "Sha1")
- `config()` - Access the repository's configuration

**Revision and History Methods:**

- `merge_bases(one, others)` - Find all merge bases between one commit and multiple others
- `merge_base(one, two)` - Find the best merge base between two commits
- `merge_base_octopus(commits)` - Find the best merge base among multiple commits
- `rev_parse(spec)` - Parse a revision specification (e.g., "HEAD~3") to an object ID

**Object Manipulation Methods:**

- `find_object(id)` - Find any Git object by its ID
- `find_blob(id)` - Find a blob object by its ID
- `find_commit(id)` - Find a commit object by its ID
- `find_tree(id)` - Find a tree object by its ID
- `find_tag(id)` - Find a tag object by its ID
- `find_header(id)` - Get header information for an object without loading its data
- `has_object(id)` - Check if an object exists in the repository

**Reference Management Methods:**

- `references()` - Get all references in the repository
- `reference_names()` - Get all reference names in the repository
- `find_reference(name)` - Find a reference by name
- `create_reference(name, target, is_symbolic, force)` - Create a new reference

### Return Types

Several dedicated types are returned from repository methods:

#### `GitObject`

Represents a Git object (blob, commit, tree, tag):
- `id` - The object's ID (SHA hash)
- `kind` - The type of the object (Blob, Commit, Tree, Tag)
- `data` - Raw binary data of the object

#### `ObjectHeader`

Contains metadata about a Git object:
- `kind` - The type of the object (Blob, Commit, Tree, Tag)
- `size` - The size of the object's data in bytes

#### `GitReference`

Represents a Git reference (branch, tag, etc.):
- `name` - The full name of the reference (e.g., "refs/heads/main")
- `target` - The target (either an object ID or symbolic reference name)
- `is_symbolic` - Whether the reference is symbolic

#### `Config`

Provides access to Git repository configuration:
- `boolean(key)` - Get a boolean value from the configuration
- `integer(key)` - Get an integer value from the configuration
- `string(key)` - Get a string value from the configuration
- `values(key)` - Get a list of values from a multi-valued configuration key
- `entries()` - Get a dictionary of all configuration entries
- `has_key(key)` - Check if a configuration key exists

### Exception Types

The module defines several exception types for error handling:

- `GitoxideError` - Base exception for all gitoxide errors
- `RepositoryError` - Repository-related errors
- `ObjectError` - Git object-related errors
- `ReferenceError` - Reference-related errors

### Constants

- `__version__` - The version of the gitoxide Python bindings

## Asynchronous API

When built with the `async` feature, the package also provides asynchronous versions of some API functions:

```python
import asyncio
from gitoxide.asyncio import Repository

async def main():
    # Async repository operations
    repo = await Repository.open('/path/to/repo')

    # Access properties
    git_dir = repo.git_dir()
    is_bare = repo.is_bare()
    is_shallow = repo.is_shallow()
    object_hash = repo.object_hash()

    # Async methods
    head = await repo.head()
    shallow_commits = await repo.shallow_commits()

asyncio.run(main())
```

Currently, only the basic repository operations are available in the async API. Work is ongoing to add the full feature set to the async API.

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

1. Revision and history operations (merge_bases, revparse)
2. Remote operations (fetch, push)
3. Diff and status functionality
4. Index operations
5. Configuration handling