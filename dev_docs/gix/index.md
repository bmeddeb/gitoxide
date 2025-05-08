# gix

## Overview

The `gix` crate is the top-level entry point for the gitoxide ecosystem. It serves as a hub that re-exports functionality from all the specialized plumbing crates (`gix-*`) in a unified, convenient API. It provides the `Repository` abstraction, which is the central concept for interacting with Git repositories.

This crate is designed to offer powerful functionality without sacrificing performance, while still being more convenient than using the sub-crates individually. It's the primary interface that applications should use to interact with Git repositories.

## Architecture

The architecture of the `gix` crate is organized around several key concepts:

1. **Repository Access**: Discovering, opening, and initializing repositories
2. **Trust Model**: Handling security concerns based on repository ownership
3. **Object Access**: Reading and manipulating Git objects (commits, trees, blobs, tags)
4. **Reference Management**: Working with Git references (branches, tags, HEAD)
5. **Remote Operations**: Clone, fetch, and push to remote repositories
6. **Worktree Handling**: Interacting with working trees

The crate uses a layered approach:
- Re-exports from specialized crates for low-level operations
- Adds convenience methods and wrappers for common operations
- Provides a thread-safe variant of the Repository for concurrent access

### Thread Safety

The crate offers two repository types:
- `Repository`: The standard repository that isn't `Sync` and thus can't be used across threads.
- `ThreadSafeRepository`: A thread-safe variant that can be obtained via `.into_sync()`.

### Object-Access Performance

The crate implements several caching mechanisms for efficient object access:
- Memory-capped LRU object cache (optional, must be enabled)
- Small fixed-size cache for delta-base objects
- Configurable cache sizes and behaviors

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Repository` | Main entry point for interacting with a Git repository (not `Sync`) | `let repo = gix::open("path/to/repo").unwrap();` |
| `ThreadSafeRepository` | Thread-safe version of Repository (implements `Sync`) | `let repo = repo.into_sync();` |
| `Commit` | Represents a Git commit | `let commit = repo.head()?.peel_to_commit()?;` |
| `Tree` | Represents a Git tree | `let tree = commit.tree()?;` |
| `Blob` | Represents a Git blob | `let blob = repo.find_object(id)?.into_blob()?;` |
| `Tag` | Represents a Git tag | `let tag = repo.find_reference("refs/tags/v1.0")?;` |
| `Reference` | Represents a Git reference | `let head = repo.head()?;` |
| `Remote` | Handle for a remote repository | `let origin = repo.find_remote("origin")?;` |
| `Id` | A Git object identifier | `let id = commit.id();` |

### Methods

#### Repository Creation/Access

| Method | Description | Example |
|--------|-------------|---------|
| `open()` | Open an existing repository | `let repo = gix::open("path/to/repo")?;` |
| `open_opts()` | Open with custom options | `let repo = gix::open_opts("path", options)?;` |
| `discover()` | Find a repository by searching upward | `let repo = gix::discover("path/to/dir")?;` |
| `init()` | Create a new repository | `let repo = gix::init("path/to/new/repo")?;` |
| `init_bare()` | Create a new bare repository | `let repo = gix::init_bare("path/to/bare.git")?;` |

#### Object Access

| Method | Description | Example |
|--------|-------------|---------|
| `find_object()` | Find an object by ID | `let obj = repo.find_object(id)?;` |
| `head()` | Get the HEAD reference | `let head = repo.head()?;` |
| `find_reference()` | Find a reference by name | `let ref = repo.find_reference("refs/heads/main")?;` |

#### Remote Operations

| Method | Description | Example |
|--------|-------------|---------|
| `remote::find()` | Find a remote | `let origin = repo.remote::find("origin")?;` |
| `prepare_clone()` | Setup for cloning | `let prep = gix::prepare_clone(url, path)?;` |
| `prepare_clone_bare()` | Setup for bare cloning | `let prep = gix::prepare_clone_bare(url, path)?;` |

## Dependencies

The `gix` crate depends on almost all other `gix-*` crates in the workspace. The major dependencies are categorized into feature groups to allow users to select only what they need.

### Major Feature Groups

| Group | Description | Crates Included |
|-------|-------------|----------------|
| `basic` | Fundamental components | `blob-diff`, `revision`, `index` |
| `extras` | Additional capabilities | `worktree-stream`, `mailmap`, `attributes`, etc. |
| `comfort` | Progress-related features | Progress reporting enhancements |
| `max-performance-safe` | Performance optimizations | Threading, caching |

## Feature Flags

The `gix` crate has an extensive feature flag system that allows users to enable only the functionality they need. These are grouped into several categories:

### High-Level Bundles

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `default` | Default features | `max-performance-safe`, `comfort`, `basic`, `extras` |
| `basic` | Core functionality | `blob-diff`, `revision`, `index` |
| `extras` | Additional features | Various additional capabilities |
| `comfort` | Progress reporting improvements | Progress unit formatting features |
| `max-performance-safe` | Performance optimizations | Threading and caching |

### Component Features

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `status` | Repository status functionality | `gix-status`, `dirwalk`, `index`, etc. |
| `index` | Access to `.git/index` files | `gix-index` |
| `revision` | Revision parsing and describing | `gix-revision` |
| `attributes` | Git attributes handling | `gix-attributes`, etc. |
| `blob-diff` | Diff between blobs | `gix-diff` |
| `credentials` | Credentials handling | `gix-credentials`, `gix-prompt` |

### Network Features

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `async-network-client` | Async network client | `gix-protocol/async-client`, etc. |
| `blocking-network-client` | Blocking network client | `gix-protocol/blocking-client`, etc. |
| `blocking-http-transport-curl` | HTTP via curl | `gix-transport/http-client-curl` |
| `blocking-http-transport-reqwest` | HTTP via reqwest | `gix-transport/http-client-reqwest` |

## Examples

### Opening a Repository

```rust
use gix::{Repository, ThreadSafeRepository};

// Simple open
let repo = gix::open("/path/to/repo")?;

// With discovery
let repo = gix::discover("/path/to/file/in/repo")?;

// Thread-safe repository for concurrent access
let repo = gix::open("/path/to/repo")?.into_sync();
```

### Working with Objects

```rust
use gix::objs::tree::EntryMode;

// Get HEAD commit
let repo = gix::open("/path/to/repo")?;
let commit = repo.head()?.peel_to_commit()?;

// Access commit information
println!("Author: {}", commit.author());
println!("Message: {}", commit.message());

// Access the tree
let tree = commit.tree()?;
for entry in tree.entries() {
    let entry = entry?;
    println!("Path: {}, Mode: {:?}", entry.filename, entry.mode());
}

// Create a blob
let id = repo.write_blob("Hello, world!")?;
```

### Working with References

```rust
// Get HEAD reference
let repo = gix::open("/path/to/repo")?;
let head = repo.head()?;
println!("HEAD points to: {}", head.target());

// List all branches
for reference in repo.references()?.prefixed("refs/heads/")? {
    let reference = reference?;
    println!("Branch: {}", reference.name().shorten());
}
```

### Cloning a Repository

```rust
// Prepare a clone operation
let prep = gix::prepare_clone("https://github.com/GitoxideLabs/gitoxide.git", "gitoxide")?;

// Configure and execute the clone
let (repo, _) = prep
    .with_checkout(true)
    .with_remote_name("origin")
    .clone_with_progress(|progress| {
        // Handle progress updates
    })?;
```

## Implementation Details

### The Trust Model

The gix crate implements a trust model based on the ownership of the repository compared to the user running the current process. Trust levels (from `gix_sec::Trust`) are assigned, which can be overridden as needed.

Configuration files track their trust level per section, and sensitive values like paths to executables will be skipped if they're from a source that isn't fully trusted. This allows data to be safely obtained without risking execution of untrusted executables.

### Extension Traits

The crate makes heavy use of extension traits to add functionality to various types. These are available through the `prelude` module:

```rust
use gix::prelude::*;
```

Many extensions to existing objects provide an `obj_with_extension.attach(&repo).an_easier_version_of_a_method()` pattern for simpler call signatures.

### Repository Re-exports

The `Repository` type re-exports and provides convenient access to functionality from many underlying crates:
- Object database access via `gix-odb`
- Reference store handling via `gix-ref`
- Configuration access via `gix-config`
- Working directory handling via `gix-worktree`

## Testing Strategy

The gix crate has extensive tests, including:
1. Unit tests for specific functionality
2. Integration tests that verify correct behavior against real repositories
3. Journey tests that validate CLI operations

Tests can be run with various build configurations using feature flags to ensure that all combinations work correctly:

```bash
# Run all tests
just unit-tests

# Test with specific features
cargo nextest run -p gix --no-default-features --features basic,comfort
```