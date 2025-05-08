# gix-index

## Overview

The `gix-index` crate implements Git's index file format, providing functionality to read, modify, and write Git index files. The Git index (often referred to as the "staging area" or "cache") serves as an intermediary between the working directory and the Git repository, tracking file states and changes that will be included in the next commit.

This crate offers a complete implementation of all Git index versions (v2, v3, and v4) with support for all standard extensions.

## Architecture

The crate is structured around two main data structures:

1. `State` - An in-memory representation of the Git index, containing entries and extension data
2. `File` - A wrapper around `State` that provides file I/O capabilities

The crate follows a modular design pattern, separating concerns into distinct modules:

- File operations (read/write/verify)
- Entry management (access/modification)
- Index extensions (tree cache, untracked cache, etc.)
- Decode/encode functionality

The index parsing is implemented as a streaming decoder that efficiently processes the binary format into a structured representation, while the writing process performs the reverse operation with proper checksumming.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `State` | In-memory representation of a Git index | Central data structure containing all index entries and extensions |
| `File` | Index file with I/O operations | Used to read from or write to a Git index file on disk |
| `Entry` | Represents a file in the index | Contains metadata about a tracked file, including paths and object IDs |
| `Stat` | File status information | Contains filesystem metadata like timestamps and size |
| `AccelerateLookup` | Lookup acceleration structure | Provides fast access to entries and directories |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `Deref<Target=State>` | Allows `File` to be used as a `State` | `File` |
| `DerefMut` | Allows mutable access to the underlying `State` | `File` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Version` | Git index file version | `V2`, `V3`, `V4` |
| `Stage` | Merge conflict stage of an entry | `Unconflicted`, `Base`, `Ours`, `Theirs` |
| `Mode` | File mode bits | `DIR`, `FILE`, `FILE_EXECUTABLE`, `SYMLINK`, `COMMIT` |

### Bitflags

| Bitflag | Description | Flags |
|---------|-------------|-------|
| `Flags` | Entry flags including assume-valid, extended, etc. | Various flags controlling entry behavior |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For object ID handling and checksumming |
| `gix-bitmap` | For efficient bit operations |
| `gix-object` | For interfacing with Git objects |
| `gix-validate` | For path validation |
| `gix-traverse` | For tree traversal operations |
| `gix-lock` | For safe file locking during writes |
| `gix-fs` | For filesystem operations |
| `gix-utils` | For utility functions |
| `gix-features` | For progress reporting and feature flags |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `hashbrown` | Efficient hash tables for lookups |
| `fnv` | Fast hashing algorithm for path lookups |
| `memmap2` | Memory mapping for efficient file access |
| `filetime` | File timestamp handling |
| `bstr` | Binary string handling for paths |
| `smallvec` | Small vector optimization |
| `thiserror` | Error handling |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Adds serialization/deserialization support | `serde`, `smallvec/serde`, `gix-hash/serde` |

## Extensions

The Git index can contain various extensions to support advanced features. The `gix-index` crate supports all standard extensions:

| Extension | Description |
|-----------|-------------|
| `Tree` | Cache of the tree structure for fast diff operations |
| `Link` | Handles split index functionality |
| `UntrackedCache` | Caches information about untracked files |
| `FsMonitor` | Integrates with filesystem monitoring services |
| `EndOfIndexEntry` | Extension for the End of Index Entry feature |
| `ResolveUndo` | Information for undoing merge conflict resolution |
| `Sparse` | Support for sparse checkout mode |

## Implementation Details

### Index Format

The Git index file follows a specific binary format:

1. A 12-byte header containing the signature "DIRC", version, and entry count
2. A sequence of index entries, each containing file metadata and paths
3. Extensions, identified by their signature and length
4. A 20-byte SHA-1 checksum (or appropriate length for other hash algorithms)

The crate handles all versions of the index format:
- Version 2: Basic index format with extensions
- Version 3: Adds support for extended flags
- Version 4: Adds support for path compression through skip-worktree flags

### Path Handling

Paths in the index are stored in a single contiguous memory area (`path_backing`), with entries referencing ranges into this storage. This approach:
1. Reduces memory fragmentation
2. Improves cache locality
3. Allows efficient string operations

### Lookup Acceleration

The `AccelerateLookup` structure provides efficient lookup operations for both case-sensitive and case-insensitive filesystems, enabling fast path lookups and directory enumeration.

### Safety Considerations

The crate provides a note on safety regarding index paths. Since index paths constructed from arbitrary user input could potentially point to sensitive locations (like `.git/hooks`), the crate recommends validating paths before using them for filesystem operations, typically through `gix_validate::path::component()` or `gix_worktree::Stack`.

## Testing Strategy

The crate employs several testing approaches:

1. Unit tests for individual components
2. Integration tests with the Git binary to ensure compatibility
3. Tests against index files generated by Git commands
4. Property-based tests for robustness

Test fixtures are often taken directly from Git's own test suite or generated using Git commands, ensuring compatibility with the reference implementation.

## Examples

### Reading an index file

```rust
use gix_index::file;
use std::path::Path;

// Open an existing index file
let index = file::init::from_path(Path::new(".git/index"))?;

// Iterate over all entries
for entry in index.entries() {
    println!(
        "{} {} {}",
        entry.id,
        entry.path(&index),
        if entry.flags.is_assume_valid() { "(assume valid)" } else { "" }
    );
}
```

### Creating and writing a new index file

```rust
use gix_index::{State, file, entry};
use gix_hash::ObjectId;
use std::path::Path;

// Create a new empty index with SHA-1 hashing
let mut state = State::empty(gix_hash::Kind::Sha1);

// Add a new entry (simplified)
state.add_entry(
    Path::new("file.txt"), 
    ObjectId::from_hex("1234567890123456789012345678901234567890").unwrap(),
    entry::Mode::FILE,
    entry::Stat::default(),
    entry::Flags::empty(),
)?;

// Write the index to disk
let index_file = file::init::from_state(state, Path::new(".git/index"));
index_file.write()?;
```

### Working with conflict stages

```rust
use gix_index::{file, entry::Stage};
use std::path::Path;

let index = file::init::from_path(Path::new(".git/index"))?;

// Find entries in conflict
for entry in index.entries() {
    match entry.stage() {
        Stage::Base => println!("Base version: {}", entry.path(&index)),
        Stage::Ours => println!("Our version: {}", entry.path(&index)),
        Stage::Theirs => println!("Their version: {}", entry.path(&index)),
        Stage::Unconflicted => {} // Not in conflict
    }
}
```