# Python Bindings for Gitoxide

This document outlines the implementation plan for creating Python bindings to the Gitoxide library.

## Implementation Plan

### 1. Project Structure

The Python bindings project will follow this structure:
```
python/
├── src/                 # Rust source for Python bindings
│   ├── common/          # Shared functionality between sync/async
│   ├── sync/            # Synchronous API implementation
│   ├── async/           # Asynchronous API implementation
│   └── lib.rs           # Main entry point
├── gitoxide/            # Python package
│   ├── sync/            # Sync Python API
│   ├── asyncio/         # Async Python API
│   └── common/          # Shared Python types/utilities
├── examples/            # Usage examples
├── tests/               # Python tests
└── Cargo.toml           # Rust dependencies and build config
```

### 2. Core Components to Expose

We will prioritize exposing these high-level components, focusing on porcelain functionality:

1. **Core Repository Operations**:
   - Repository discovery, opening, initialization, and cloning
   - Status and diff functionality
   - Commit and checkout operations
   - Reference manipulation

2. **Specific Components to Expose**:
   - **Repository Management**: Open, init, clone operations
   - **Object Manipulation**: Working with blobs, trees, commits, tags
   - **Reference Management**: Branches, tags, HEAD
   - **Diff and Status**: Working directory status and diffing
   - **Index Operations**: Staging and unstaging changes
   - **Configuration**: Reading and writing Git config

3. **Components to Avoid Exposing**:
   - Low-level plumbing crates (gix-pack, gix-odb, etc.)
   - Implementation details (tempfiles, locks)
   - Experimental features

### 3. API Design

We will create a single Python package that provides both synchronous and asynchronous APIs:

#### Synchronous API (`gitoxide.sync`)

```python
from gitoxide.sync import Repository

# Open an existing repository
repo = Repository.open("/path/to/repo")

# Clone a repository
repo = Repository.clone("https://github.com/user/repo", "/path/to/destination")

# Get and print the current branch
branch = repo.head().shorthand()
print(f"Current branch: {branch}")

# Create a commit
author = Signature.now("Author Name", "author@example.com")
committer = Signature.now("Committer Name", "committer@example.com")
repo.commit("Initial commit", [repo.head().target()], author, committer)
```

#### Asynchronous API (`gitoxide.asyncio`)

```python
import asyncio
from gitoxide.asyncio import Repository

async def main():
    # Open an existing repository
    repo = await Repository.open("/path/to/repo")

    # Clone a repository
    repo = await Repository.clone("https://github.com/user/repo", "/path/to/destination")

    # Get and print the current branch
    branch = await repo.head().shorthand()
    print(f"Current branch: {branch}")

asyncio.run(main())
```

### 4. Rust Implementation Strategy

The Rust side of the bindings will be organized as follows:

1. **Split Architecture**:
   - Create separate modules for sync and async implementations
   - Compile with both `blocking-network-client` and `async-network-client-async-std` features
   - Use conditional compilation (`#[cfg(feature = "...")]`) to separate implementations

2. **Common Functionality**:
   - Share data structures and non-I/O code between sync and async
   - Implement thin wrappers for PyO3 for both variants

3. **Core Classes**:
   - `Repository`: Main entry point for repository operations
   - `Object`: Base class for Git objects
   - `Commit`, `Tree`, `Blob`, `Tag`: Object type implementations
   - `Reference`: For managing references
   - `Index`: For working with the Git index
   - `Diff`: For diff operations
   - `Status`: For status operations
   - `Config`: For configuration operations
   - `Signature`: For author/committer information

### 5. Build System

We will use [maturin](https://github.com/PyO3/maturin) to build and distribute the Python package:

#### Development Setup

```bash
# Install maturin in your Python environment
pip install maturin

# Navigate to the python directory
cd python

# Build in development mode (allows for fast iteration)
maturin develop

# Build with specific Python interpreter
maturin develop --interpreter python3.10

# Build with release optimizations
maturin develop --release
```

#### Build Configuration in Cargo.toml

```toml
[package]
name = "gitoxide-python"
version = "0.1.0"
edition = "2021"

[lib]
name = "gitoxide"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.24.2", features = ["extension-module"] }
pyo3-async-runtimes = { version = "0.24.0", features = ["async-std-runtime"] }
gix = { version = "=0.54.0", features = ["blocking-network-client", "async-network-client-async-std"] }

[features]
default = ["blocking-network-client", "async-network-client-async-std"]
blocking-network-client = ["gix/blocking-network-client"]
async-network-client-async-std = ["gix/async-network-client-async-std"]
```

### 6. Testing Strategy

1. **Unit Tests**:
   - Test individual components in isolation
   - Use mock repositories where possible

2. **Integration Tests**:
   - Test against real Git repositories
   - Verify correct behavior for complex operations

3. **Test Coverage**:
   - Aim for high test coverage across all exposed functionality
   - Test both sync and async APIs

4. **Test Structure**:
   ```
   tests/
   ├── unit/                   # Unit tests
   │   ├── test_repository.py
   │   ├── test_commit.py
   │   └── ...
   ├── integration/            # Integration tests
   │   ├── test_clone.py
   │   ├── test_status.py
   │   └── ...
   └── conftest.py             # Test fixtures
   ```

### 7. Documentation Strategy

1. **API Documentation**:
   - Use docstrings with type hints
   - Provide examples for all methods

2. **User Guide**:
   - Create a comprehensive user guide with examples
   - Explain sync vs. async usage

3. **Examples**:
   - Provide examples for common Git operations
   - Include both sync and async examples

### 8. Implementation Phases

#### Phase 1: Foundation
- Set up the project structure
- Implement basic Repository class (open, init, clone)
- Create initial CI pipeline and test framework

#### Phase 2: Core Functionality
- Implement object models (Commit, Tree, Blob, Tag)
- Add reference management
- Implement index operations

#### Phase 3: Advanced Features
- Add diff and status functionality
- Implement configuration access
- Add more complex operations (fetch, merge, etc.)

#### Phase 4: Polish
- Improve error handling
- Complete documentation
- Performance optimizations

### 9. Error Handling Strategy

1. **Python Exception Mapping**:
   - Map Rust errors to appropriate Python exceptions
   - Provide detailed error messages
   - Include context in error messages (file paths, objects, etc.)

2. **Exception Classes**:
   ```python
   class GitoxideError(Exception): pass
   class RepositoryError(GitoxideError): pass
   class ObjectError(GitoxideError): pass
   class ReferenceError(GitoxideError): pass
   # etc.
   ```

### 10. Memory Management Considerations

1. **Object Lifetimes**:
   - Ensure proper lifetime management for Git objects
   - Handle Python GC integration with Rust

2. **Resource Cleanup**:
   - Implement proper `__del__` methods where needed
   - Use context managers for resources that need explicit cleanup

### 11. Performance Considerations

1. **Parallelism**:
   - Leverage Gitoxide's parallel capabilities
   - Release GIL where appropriate for CPU-intensive operations

2. **Memory Usage**:
   - Avoid unnecessary copies of data
   - Use references to large data structures when possible

### 12. Versioning Strategy

1. **Semantic Versioning**:
   - Follow semver for the Python package
   - Clear documentation of compatible Gitoxide versions

2. **Compatibility**:
   - Document minimum supported Python version (3.8+)
   - Test against multiple Python versions