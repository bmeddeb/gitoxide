# gix-commitgraph

## Overview

The `gix-commitgraph` crate provides read-only access to Git's commit-graph file format. The commit-graph is a performance optimization that accelerates various operations involving commit history traversal, such as calculating merge-bases, finding ancestors, and determining commit generation numbers. It acts as an index over the commits in a repository, allowing for faster lookups and traversals without reading the full commit objects.

The crate supports both single-file and split (multi-file) commit graphs, following the format introduced in Git 2.18 and enhanced in later versions.

## Architecture

The `gix-commitgraph` crate follows a layered architecture:

1. **File Layer**: Low-level access to individual commit-graph file data through the `File` struct, handling binary parsing and lookups within a single file.

2. **Graph Layer**: High-level interface through the `Graph` struct, which manages a collection of commit-graph files (for split commit graphs) and provides a unified view of the entire graph.

3. **Access Layer**: Methods for querying commits and their metadata, traversing the graph, and accessing commit relationships.

4. **Verification Layer**: Functionality to verify the integrity of commit-graph files, including checksums, commit order, and generation numbers.

The architecture is designed to be memory-efficient, using memory-mapped files (`memmap2`) to avoid loading the entire graph into memory and providing zero-copy access to the data where possible.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Graph` | Top-level representation of a complete commit graph, potentially spanning multiple files. | Primary entry point for commit-graph operations. |
| `File` | Representation of a single commit-graph file. | Used for file-specific operations and accessed through a `Graph`. |
| `file::Commit<'_>` | Lazily parsed commit data from the commit-graph. | Accessed via the `Graph` to retrieve commit metadata. |
| `Position` | Represents a position within the overall commit graph. | Used as a handle to reference commits within the graph. |
| `file::Position` | Represents a position within a single commit-graph file. | Used internally for lookups within a single file. |
| `verify::Outcome` | Statistics gathered during verification. | Returned by verification methods. |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `at` | Creates a new `Graph` from a path. | `fn at(path: impl AsRef<Path>) -> Result<Graph, init::Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `init::Error` | Errors that can occur when initializing a `Graph`. | Various error conditions such as `HashVersionMismatch`, `InvalidPath`, etc. |
| `verify::Error` | Errors that can occur during graph verification. | Various verification failures like `BaseGraphCount`, `Generation`, etc. |
| `file::verify::Error` | Errors specific to file verification. | Including `Checksum`, `CommitsOutOfOrder`, etc. |
| `file::commit::Error` | Errors related to commit parsing. | Includes `ExtraEdgesListOverflow`, `MissingExtraEdgesList`, etc. |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | Handling Git object hashes and checksums. |
| `gix-chunk` | Working with the chunked file format used by commit-graphs. |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `memmap2` | Memory-mapped file I/O for efficient access. |
| `bstr` | Binary string handling for non-UTF8 paths and data. |
| `thiserror` | Error handling and formatting. |
| `serde` | Optional serialization/deserialization support. |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization of data structures. | `serde`, and serde features for `gix-hash` and `bstr`. |

## Examples

### Basic Usage

```rust
use gix_commitgraph::{at, Graph};
use std::path::Path;

// Load a commit graph from a repository's .git/objects/info directory
let graph = at(Path::new("/path/to/repo/.git/objects/info"))?;

// Look up a commit by its hash
let oid = hex_to_oid("1234567890abcdef1234567890abcdef12345678");
if let Some(commit) = graph.commit_by_id(&oid) {
    println!("Commit found with generation number: {}", commit.generation());
    println!("Commit timestamp: {}", commit.committer_timestamp());
    
    // Iterate through parents
    for parent_pos_result in commit.iter_parents() {
        let parent_pos = parent_pos_result?;
        let parent = graph.commit_at(parent_pos);
        println!("Parent: {}", parent.id());
    }
}

// Verify the integrity of the commit graph
let stats = graph.verify_integrity(|_commit| Ok(()))?;
println!("Graph contains {} commits", stats.num_commits);
if let Some(length) = stats.longest_path_length {
    println!("Longest path in history: {} commits", length);
}
```

### Iterating Through All Commits

```rust
use gix_commitgraph::at;

// Load a commit graph
let graph = at("/path/to/repo/.git/objects/info")?;

// Iterate over all commits in the graph
for commit in graph.iter_commits() {
    println!("Commit: {} (gen: {})", commit.id(), commit.generation());
    println!("  Tree: {}", commit.root_tree_id());
    println!("  Time: {}", commit.committer_timestamp());
}
```

## Implementation Details

### Commit-Graph File Format

The commit-graph file format consists of the following chunks:

1. **Header**: 8 bytes starting with "CGPH" signature followed by version information.
2. **Chunk Table**: List of chunks in the file with their offsets.
3. **OID Fanout (OIDF)**: 256 entries of 4 bytes each, representing the cumulative count of objects.
4. **OID Lookup (OIDL)**: Sorted list of object IDs in the graph.
5. **Commit Data (CDAT)**: Array of commit metadata entries.
6. **Extra Edge List (EDGE)**: Optional list of additional parent edges for octopus merges.
7. **Base Graphs List (BASE)**: Optional list of base graph checksums (for split graphs).
8. **Checksum**: A trailing checksum of the file contents.

### Commit Data Structure

Each commit entry in the commit data chunk contains:

- Root tree object ID (20 bytes for SHA-1, 32 bytes for SHA-256)
- Parent 1 position (4 bytes)
- Parent 2 position (4 bytes)
- Generation number + commit time (8 bytes)

Special values and bit patterns are used to represent:
- No parent: `0x7000_0000`
- Extra edge list reference: `0x8000_0000` bit set
- Last entry in extra edge list: `0x8000_0000` bit set

### Generation Numbers

Generation numbers are used to optimize commit traversal. They follow these rules:

- Commits without parents have generation number 1
- A commit's generation is max(parents' generations) + 1
- Generation numbers are capped at `GENERATION_NUMBER_MAX` (0x3fff_ffff)
- A special infinity value (0xffff_ffff) is used for unconnected history

### Split Commit Graphs

For repositories with many commits, Git can split the commit-graph into multiple files:

1. A `commit-graph-chain` file lists the hash of each graph file
2. Each graph file is named `graph-<hash>.graph`
3. Each file contains a BASE chunk listing the checksums of its base graphs
4. Files are ordered so each depends only on preceding files in the chain

The `Graph` struct handles the complexities of working with split commit graphs, presenting a unified interface to the client code.

### Memory Efficiency

The implementation is designed to be memory-efficient:

- Uses memory-mapped files to avoid loading the entire graph into memory
- Lazily parses commit data when needed
- Provides iterators for traversal without materializing all commits

### Integrity Verification

The crate provides thorough integrity verification:

- Checksums are verified for each file
- References between split files are validated
- Commit ordering is checked
- Generation numbers are validated
- Parent references are verified to be valid positions
- Root tree IDs are checked to not be null

## Testing Strategy

The crate is tested using multiple approaches:

1. **Unit Tests**: Test individual components and edge cases.
2. **Fixture Tests**: Use scripted fixtures to generate test repositories with specific commit-graph characteristics.
3. **Fuzz Testing**: Uses libfuzzer to find potential issues with malformed inputs.

Test fixtures include:
- Single commits
- Linear history
- Octopus merges
- Split chains
- Generation number edge cases

The verification functionality is used to validate the correctness of the parsed data against the expected repository state.