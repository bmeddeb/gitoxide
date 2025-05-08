# gitoxide-core

## Overview

The `gitoxide-core` crate is the implementation library behind the CLI commands for the `gitoxide` project. It abstracts the user interface of the command-line tools from the actual implementation, which allows for potential alternative frontends in the future.

This crate serves as the bridge between the command-line interface and the `gix` library, implementing the various Git commands and functionality that are exposed through the `gix` and `ein` binaries.

As noted in the crate's documentation, it considers itself an internal implementation detail of the `gix` CLI and is not meant to be used for external consumption as a Cargo dependency. It's not intended to be stabilized as an API.

## Architecture

The crate is organized around a modular architecture that mirrors common Git commands and functionality:

1. **Repository Operations**: Implementation of repository-level commands like clone, fetch, status
2. **Object Operations**: Commands that work with Git objects like commit, tree, blob
3. **Reference Operations**: Commands for working with refs and the ref store
4. **Pack Operations**: Commands for working with pack files and object databases
5. **Utility Operations**: Various utility commands and features

Each module typically provides functions that:
1. Take command-line arguments and options
2. Process them into appropriate calls to the `gix` library
3. Handle errors and output formatting
4. Report progress to the user

The crate also defines an `OutputFormat` enum to handle different output formats like human-readable text or JSON.

## Core Components

### Main Modules

| Module | Description |
|--------|-------------|
| `repository` | Repository-level operations (clone, fetch, status, etc.) |
| `commitgraph` | Operations related to the commit graph |
| `pack` | Pack file operations (create, explode, verify) |
| `index` | Index file operations |
| `net` | Network-related functionality |
| `hours` | Estimate time invested into a repository |
| `organize` | Repository discovery and organization |
| `query` | Database querying functionality |
| `corpus` | Operations on a corpus of repositories |

### Repository Module

The repository module is the largest and most comprehensive, containing implementations for many Git commands:

| Submodule | Description |
|-----------|-------------|
| `archive` | Creating archives from repositories |
| `blame` | Git blame implementation |
| `cat` | Cat-file functionality |
| `clean` | Clean repository working directory |
| `clone` | Clone repositories |
| `commit` | Create commits |
| `config` | Access and manipulate Git config |
| `diff` | Diff functionality |
| `fetch` | Fetch from remotes |
| `fsck` | Repository integrity checking |
| `log` | Git log functionality |
| `mailmap` | Mailmap handling |
| `merge` | Merge functionality |
| `status` | Working directory status |
| `tree` | Tree manipulation |
| `worktree` | Worktree handling |

### Output Format

The crate defines an `OutputFormat` enum to handle different output formats:

```rust
#[derive(Debug, Eq, PartialEq, Hash, Clone, Copy)]
pub enum OutputFormat {
    Human,
    #[cfg(feature = "serde")]
    Json,
}
```

This allows commands to output in different formats depending on user preference.

## Dependencies

### Main Dependencies

| Crate | Usage |
|-------|-------|
| `gix` | The main Git implementation library |
| `anyhow` | Error handling |
| `thiserror` | Error definitions |
| `bytesize` | Working with byte sizes |
| `tempfile` | Temporary file handling |

### Optional Dependencies

| Crate | Usage | Feature Flag |
|-------|-------|-------------|
| `gix-archive` | Archive creation | `archive` |
| `jwalk` | Parallel directory walking | `organize` |
| `rusqlite` | SQLite database access | `query`, `corpus` |
| `serde`, `serde_json` | Serialization/deserialization | `serde` |
| `async-trait`, etc. | Async networking support | `async-client` |

## Feature Flags

The crate provides several feature flags to control which functionality is available:

### Command Features

| Flag | Description |
|------|-------------|
| `organize` | Repository discovery functionality |
| `estimate-hours` | Functionality to estimate time invested in repositories |
| `query` | Database querying functionality |
| `corpus` | Corpus operations |
| `archive` | Archive creation functionality |
| `clean` | Repository cleaning functionality |

### Networking Features

| Flag | Description |
|------|-------------|
| `blocking-client` | Use blocking network client (default) |
| `async-client` | Use async network client (experimental) |

### Other Features

| Flag | Description |
|------|-------------|
| `serde` | Enable serialization/deserialization support |

## Examples

### Repository Status

The repository status functionality is implemented in `repository/status.rs` and provides information about the state of the working directory:

```rust
// Implementation in gitoxide-core
pub fn status(
    repo: &gix::Repository,
    exclude_standard: bool,
    include_ignored: bool,
    output_format: OutputFormat,
    mut out: impl std::io::Write,
) -> anyhow::Result<()> {
    // Implementation details...
}

// Usage from CLI
let repo = gix::open(path)?;
gitoxide_core::repository::status(
    &repo,
    exclude_standard,
    include_ignored, 
    output_format,
    std::io::stdout(),
)?;
```

### Repository Clone

The clone functionality is implemented in `repository/clone.rs`:

```rust
// Implementation in gitoxide-core
pub async fn clone(
    url: &str,
    directory: &std::path::Path,
    bare: bool,
    mut progress: impl gix::Progress,
    out: impl std::io::Write,
) -> anyhow::Result<()> {
    // Implementation details...
}

// Usage from CLI
gitoxide_core::repository::clone(
    &url,
    &directory,
    bare,
    progress,
    std::io::stdout(),
).await?;
```

## Implementation Details

### Progress Reporting

The crate makes extensive use of the `gix::Progress` trait to report progress for long-running operations. Many functions take a progress parameter that allows the CLI to display progress information to users.

### Error Handling

The crate uses `anyhow::Result` for most public functions, which allows for rich error context and chain building. Internal errors are typically defined using `thiserror`.

### Output Formatting

The `OutputFormat` enum allows commands to output in different formats (human-readable or JSON). This is implemented by having each command check the output format and format its results accordingly.

### Feature-Gated Functionality

Many features are conditionally compiled based on feature flags. This allows the CLI to be built with only the needed functionality, reducing binary size and compilation time.

## Testing Strategy

The crate is primarily tested through:

1. **Journey tests**: End-to-end tests of CLI commands in the parent repository
2. **Integration tests**: Tests that verify the behavior of entire commands
3. **Unit tests**: Tests for specific functionality within commands

The journey tests are particularly important as they validate the entire flow from command-line parsing to execution and output formatting.