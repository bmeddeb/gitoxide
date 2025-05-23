# Gitoxide Python Bindings

Python bindings for [gitoxide](https://github.com/Byron/gitoxide), a pure Rust implementation of Git focused on performance, safety, and clean code.

## Installation

```bash
pip install gitoxide
```

## Usage

### Opening and Initializing Repositories

```python
import gitoxide

# Open an existing repository
repo = gitoxide.Repository.open('/path/to/repo')

# Initialize a new repository
new_repo = gitoxide.Repository.init('/path/to/new/repo', bare=False)
```

### Working with Repositories

```python
# Get repository paths
git_dir = repo.git_dir()  # Path to .git directory
work_dir = repo.work_dir()  # Path to working directory (None for bare repos)

# Check if repository is bare
is_bare = repo.is_bare()

# Get current HEAD
head = repo.head()  # Returns HEAD reference name or commit ID
```

## Type Hints

Gitoxide includes type stub files (.pyi) for better IDE support and static type checking with tools like mypy or pyright.

### Installing Type Stubs

The stubs are included with the package, but you can also install them manually:

```bash
python setup_stubs.py
```

### Using with Mypy

Add the following to your mypy.ini or pyproject.toml:

```ini
# mypy.ini
[mypy]
plugins = gitoxide-stubs
```

Or in pyproject.toml:

```toml
[tool.mypy]
plugins = ["gitoxide-stubs"]
```

## Features

- Pure Rust implementation under the hood
- Both synchronous and asynchronous APIs
- Thread-safe
- Memory efficient
- High performance
- Type hints for better IDE support

## Development

### Building from source

```bash
# Clone the repository
git clone https://github.com/Byron/gitoxide
cd gitoxide/python

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install maturin pytest

# Build and install in development mode
maturin develop
```

## License

This project is licensed under either of

- Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.