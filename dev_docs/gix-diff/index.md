# gix-diff

## Overview

The `gix-diff` crate provides highly optimized algorithms for calculating differences between various Git object types and for generating patches. It supports diffing blobs, trees, indices, and provides rewrite tracking functionality (rename and copy detection).

The crate is designed with performance in mind, with modular components that allow for customizing the diff process. It can handle binary files, process Git attributes, and supports various diff formats including unified diffs.

## Architecture

The `gix-diff` crate is organized into several key modules, each addressing a specific aspect of diffing in Git:

1. **Blob Diffing**: Comparison of file content with text diffing and unified diff support
2. **Tree Diffing**: Comparing Git tree objects to determine changes in structure
3. **Index Diffing**: Finding changes between two Git indices
4. **Rewrite Tracking**: Detection of renames and copies with configurable similarity thresholds

The architecture follows a layered approach:
- **Low-level diffing algorithms**: Provided by the external `imara-diff` crate
- **Content conversion**: Transformation of Git objects into diffable content using filters
- **Change detection**: Identification of additions, deletions, modifications, renames, and copies
- **Output formatting**: Generation of human-readable diffs in various formats

Each module provides a high-level entry function with a functional interface, and lower-level components for customization.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `blob::Pipeline` | Conversion pipeline to prepare objects or paths for diffing | Handles filters defined in git-attributes and content conversions |
| `blob::Platform` | Utility for performing diffs of two blobs with caching | Optimized for NxM lookups (such as for detecting renames) |
| `blob::UnifiedDiff` | Generates unified diff format | Formats diff output in the standard unified diff format |
| `Rewrites` | Configuration for rename and copy tracking | Controls similarity thresholds and other copy/rename detection settings |
| `rewrites::Tracker` | Detects rewrites between blobs | Implements rename and copy detection algorithms |
| `tree::State` | State required to run tree diffs | Maintains internal state and buffers for tree diffing |
| `tree::Recorder` | Records observed changes during tree traversal | Useful for debugging or printing diff output |
| `index::Change` | Represents a change between two indices | Describes additions, modifications, and deletions |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `tree::Visit` | Interface for responding to tree traversal events | `tree::Recorder` and custom implementations |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `tree` | Performs a diff between two trees | `fn tree(find: &impl Find, from: Option<&ObjectId>, to: Option<&ObjectId>, state: &mut State, delegate: &mut impl Visit) -> Result<(), Error>` |
| `tree_with_rewrites` | Tree diff with rewrite detection | `fn tree_with_rewrites(/* parameters */) -> Result<(), Error>` |
| `index` | Performs a diff between two indices | `fn index(/* parameters */) -> Result<Vec<Change>, Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `blob::ResourceKind` | Classifies a resource for diffing | `OldOrSource`, `NewOrDestination` |
| `tree::visit::Action` | Controls diff traversal | `Continue`, `Cancel` |
| `tree::visit::Change` | Represents a change in a tree | `Addition`, `Deletion`, `Modification`, `Deletion` |
| `tree::visit::Relation` | Describes item relation in tree | `Ancestor`, `GreatAncestor` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | Object ID handling and hashing |
| `gix-object` | Git object handling and traversal |
| `gix-index` | Git index file handling (with `index` feature) |
| `gix-pathspec` | Path specification handling (with `index` feature) |
| `gix-attributes` | Git attribute handling (with `index` feature) |
| `gix-filter` | Content filtering (with `blob` feature) |
| `gix-worktree` | Worktree operations (with `blob` feature) |
| `gix-path` | Path manipulation (with `blob` feature) |
| `gix-fs` | Filesystem operations (with `blob` feature) |
| `gix-command` | External command execution (with `blob` feature) |
| `gix-tempfile` | Temporary file handling (with `blob` feature) |
| `gix-trace` | Tracing and logging (with `blob` feature) |
| `gix-traverse` | Object graph traversal (with `blob` feature) |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `imara-diff` | Core text diffing algorithm (with `blob` feature) |
| `thiserror` | Error handling and definition |
| `serde` | Serialization/deserialization support (with `serde` feature) |
| `bstr` | Binary string handling |
| `getrandom` | Random number generation (with `wasm` feature) |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `default` | Enables blob and index diffing | `blob`, `index` |
| `blob` | Enables diffing of blobs using imara-diff | `imara-diff`, `gix-filter`, `gix-worktree`, `gix-path`, `gix-fs`, `gix-command`, `gix-tempfile`, `gix-trace`, `gix-traverse` |
| `index` | Enables diffing of two indices and rewrite tracking | `gix-index`, `gix-pathspec`, `gix-attributes` |
| `serde` | Adds serialization/deserialization support | `serde`, plus enables `serde` feature on `gix-hash`, `gix-object`, `gix-index` |
| `wasm` | Makes it possible to compile to wasm32-unknown-unknown target | `getrandom` with js feature |

## Examples

```rust
// Tree diffing example
use gix_diff::tree::{self, Recorder};
use gix_object::find::existing_iter::Find;

fn diff_trees(repo: &impl Find, from_tree: &ObjectId, to_tree: &ObjectId) -> Result<Vec<tree::recorder::Change>, tree::Error> {
    // Create state buffer and recorder delegate
    let mut state = tree::State::default();
    let mut recorder = Recorder::default();
    
    // Perform the diff
    tree::diff(repo, Some(from_tree), Some(to_tree), &mut state, &mut recorder)?;
    
    // Return recorded changes
    Ok(recorder.records)
}

// Blob diffing with rewrite detection
use gix_diff::{blob, Rewrites, rewrites::Tracker};

fn detect_renames(platform: &mut blob::Platform, from_paths: &[PathBuf], to_paths: &[PathBuf]) -> Result<Vec<Change>, Error> {
    // Configure rewrite detection settings
    let rewrites = Rewrites {
        copies: None,                // Don't detect copies, only renames
        percentage: Some(0.5),       // 50% similarity threshold
        limit: 1000,                 // Limit to 1000 comparisons (1000*1000 combinations)
        track_empty: false,          // Don't track empty files
    };
    
    // Create tracker and process paths
    let mut tracker = Tracker::new(platform, rewrites);
    // ... process paths and detect renames
}
```

## Implementation Details

### Optimization Strategies

1. **Caching**: The blob diffing platform implements caching to avoid redundant conversions and diffs, which is critical for efficient rewrite detection where many combinations are tested.

2. **Buffer Reuse**: Buffers are reused to minimize memory allocations during diffing operations.

3. **Filtered Comparisons**: The rewrite tracking can limit the number of comparisons to prevent quadratic complexity when dealing with large sets of files.

4. **Attribute-driven Processing**: Git attribute settings are respected to enable specialized diffing for different file types (like binary files or those with custom diff drivers).

### Rewrite Detection Algorithm

The rename and copy detection algorithm works by:

1. Building sets of added and deleted files
2. Computing similarity between deleted and added files (either exact match or percentage-based)
3. Creating a bipartite graph where edges represent potential matches
4. Finding an optimal matching that maximizes total similarity

The similarity threshold (`percentage` field in `Rewrites`) determines how strict the matching is, with higher values requiring more similar files.

### Tree Diffing Approach

Tree diffing uses a recursive traversal approach:

1. Start with root trees from both sides
2. For each entry that exists in either tree:
   - If it exists only in one tree: record addition or deletion
   - If it exists in both: compare object IDs and types
      - If both are trees: recursively diff them
      - If both are blobs: record modification if IDs differ
      - If types differ: record deletion + addition

## Testing Strategy

The crate includes comprehensive tests covering:

1. **Unit Tests**: Testing individual components in isolation
2. **Integration Tests**: Verifying behavior of higher-level functions
3. **Fixture-based Tests**: Using pre-prepared Git repositories for realistic testing
   - `make_blob_repo.sh`: Creates repositories with blob changes
   - `make_diff_repo.sh`: Creates repositories with various diff scenarios
   - `make_diff_for_rewrites_repo.sh`: Repositories for testing rewrite detection

The tests ensure that the diff implementation provides accurate results matching Git's behavior, particularly for edge cases like empty files, binary files, and complex renames.