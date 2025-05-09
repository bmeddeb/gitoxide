# Gitoxide Python Documentation

Welcome to the documentation for the Gitoxide Python bindings. These bindings provide a Python interface to the Gitoxide Git implementation written in Rust.

## Overview

The Gitoxide Python bindings offer:

- A fast and memory-safe Git implementation
- Both synchronous and asynchronous APIs
- Type-hinted API for better editor support
- Pythonic interfaces to Git functionality

## Contents

- [Repository](repository/index.md) - Working with Git repositories
- [Objects](objects/index.md) - Working with Git objects (blobs, commits, trees, tags)
- [References](references/index.md) - Working with Git references (branches, tags)
- [History](history/index.md) - Traversing and analyzing commit history
- [Configuration](config/index.md) - Reading repository configuration
- [Errors](errors/index.md) - Error handling

## Installation

```bash
# Install directly from PyPI
pip install gitoxide

# Install from source (development mode)
pip install -e .

# With async support
pip install -e . --config-settings="-C features=async"
```

## Quick Start

```python
import gitoxide

# Open an existing repository
repo = gitoxide.Repository.open('/path/to/repo')

# Check basic properties
print(f"Git directory: {repo.git_dir()}")
print(f"Working directory: {repo.work_dir()}")
print(f"Is bare: {repo.is_bare()}")
print(f"Is shallow: {repo.is_shallow()}")
print(f"Object hash: {repo.object_hash()}")

# Get HEAD reference
try:
    head = repo.head()
    print(f"HEAD: {head}")
except gitoxide.RepositoryError as e:
    print(f"Error getting HEAD: {e}")

# List references
for ref in repo.references():
    target = ref.target
    if ref.is_symbolic:
        target = f"-> {target} (symbolic)"
    print(f"{ref.name}: {target}")
```

## API Development Status

The Python bindings for Gitoxide are under active development. Currently implemented functionality includes:

- Basic repository operations
- Object access and manipulation
- Reference management and creation

Additional features coming soon:
- Remote operations
- Index and working directory operations
- Command execution context

Implemented features:
- Basic repository operations
- Object access and manipulation
- Reference management and creation
- Revision and history traversal
- Configuration management