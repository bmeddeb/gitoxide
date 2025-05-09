# gix-shallow

## Overview

`gix-shallow` is a crate in the gitoxide ecosystem that handles the shallow boundary specification in Git repositories. It provides functionality to read and write the `.git/shallow` file, which marks commits at the boundary of a shallow repository where history has been truncated. This crate is essential for managing shallow clones, which are Git repositories with incomplete history.

## Architecture

The crate follows a simple and focused architecture with two main operations:
1. **Reading** the shallow file to determine which commits form the shallow boundary
2. **Writing** to the shallow file to update the boundary based on shallow/unshallow operations

The crate uses a straightforward file-based approach, reading and writing commit IDs to the shallow file while providing proper error handling and maintaining the sorted nature of the file contents.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| No dedicated structs are defined. The crate operates on standard types like `Option<Vec<ObjectId>>`. | | |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| No dedicated traits are defined in this crate. | | |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `read` | Reads shallow commits from the shallow file, returning None if the repository isn't shallow | `fn read(shallow_file: &std::path::Path) -> Result<Option<Vec<gix_hash::ObjectId>>, read::Error>` |
| `write` | Updates the shallow file with new shallow commits, potentially removing it if empty | `fn write(file: gix_lock::File, shallow_commits: Option<Vec<gix_hash::ObjectId>>, updates: &[Update]) -> Result<(), write::Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Update` | Represents an instruction to modify the shallow boundary | `Shallow(ObjectId)`: Add a commit to the shallow boundary<br>`Unshallow(ObjectId)`: Remove a commit from the shallow boundary |
| `read::Error` | Error type for reading operations | `Io`: File I/O errors<br>`DecodeHash`: Hash decoding errors |
| `write::Error` | Error type for writing operations | `Commit`: Lock commit errors<br>`RemoveEmpty`: File removal errors<br>`Io`: File I/O errors |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For ObjectId handling and manipulation |
| `gix-lock` | For safe file writing with locking |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `thiserror` | For error type definitions |
| `bstr` | For efficient byte string operations |
| `serde` (optional) | For serialization/deserialization support |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization for data structures | `serde`, `gix-hash/serde` |

## Examples

Reading the shallow file:

```rust
use std::path::Path;
use gix_shallow::read;

fn check_shallow_status(git_dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let shallow_file = git_dir.join("shallow");
    match read(&shallow_file)? {
        Some(commits) => {
            println!("Repository is shallow with {} boundary commits:", commits.len());
            for commit in commits {
                println!("  {}", commit);
            }
        },
        None => println!("Repository is not shallow"),
    }
    Ok(())
}
```

Updating the shallow file:

```rust
use std::path::Path;
use gix_hash::ObjectId;
use gix_lock::File;
use gix_shallow::{read, write, Update};

fn unshallow_commit(git_dir: &Path, commit_hex: &str) -> Result<(), Box<dyn std::error::Error>> {
    let shallow_file = git_dir.join("shallow");
    
    // Read current shallow commits
    let shallow_commits = read(&shallow_file)?;
    
    // Create a lock file for writing
    let lock_file = File::acquire_to_update(&shallow_file, None, None)?;
    
    // Parse the commit to unshallow
    let commit_id = ObjectId::from_hex(commit_hex.as_bytes())?;
    
    // Create update instruction
    let updates = [Update::Unshallow(commit_id)];
    
    // Write the updated shallow file
    write(lock_file, shallow_commits, &updates)?;
    
    println!("Successfully unshallowed commit {}", commit_hex);
    Ok(())
}
```

## Implementation Details

### Shallow File Format

The `.git/shallow` file contains a list of commit IDs (SHA-1 or SHA-256 hashes) that mark the boundary of a shallow repository. Each line in the file contains a single hex-encoded object ID.

The implementation ensures that:
1. Commits in the file are maintained in sorted order
2. Empty shallow files are removed (indicating a fully unshallowed repository)
3. Reading a non-existent shallow file correctly returns `Ok(None)` to indicate the repository is not shallow

### Reading Process

The reading process:
1. Attempts to read the shallow file
2. Returns `Ok(None)` if the file doesn't exist (not a shallow repository)
3. Parses each line as a hex-encoded object ID
4. Sorts the resulting list for consistent ordering
5. Returns `Ok(None)` if the file exists but is empty, otherwise `Ok(Some(commits))`

### Writing Process

The writing process:
1. Applies a series of `Update` instructions to the current list of shallow commits
2. Sorts the resulting list
3. If the list is empty, removes the shallow file
4. Otherwise, writes each commit ID as a hex-encoded string followed by a newline
5. Uses the `gix-lock` crate to ensure atomic file updates

### Deviation from Git

The implementation notes one deviation from Git's behavior:
- Git prunes the set of shallow commits while writing, while this implementation currently doesn't implement pruning

## Testing Strategy

The crate itself doesn't include internal tests, but its functionality should be tested through:

1. **Integration tests**: Testing shallow repository operations end-to-end
2. **Unit tests**: Verifying correct handling of corner cases like:
   - Empty shallow files
   - Non-existent shallow files
   - Conflicting shallow/unshallow operations
   - Invalid file formats
3. **Interoperability tests**: Ensuring compatibility with Git's shallow repository handling