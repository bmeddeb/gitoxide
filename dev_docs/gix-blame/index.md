# gix-blame

## Overview

The `gix-blame` crate implements an algorithm to annotate lines in tracked Git files with the commits that changed them. This functionality is similar to the `git blame` command, allowing users to determine which commit introduced each line in a file, along with commit metadata. It analyzes a file's history to identify which commit and author is responsible for each line of code.

## Architecture

The blame algorithm in `gix-blame` works by traversing the commit history and tracking the origin of each line in a file. It uses a "hunk-based" approach, where regions of the file (hunks) are gradually attributed to the commits that introduced them.

The crate follows a modular design with these main components:
- Core algorithm implementation in `file/function.rs`
- Data structures and types for tracking blame information in `types.rs`
- Error handling for various failure modes in `error.rs`
- Utilities for working with line ranges and processing diffs

### Key Concepts

- **Blamed File**: The file as it exists in `HEAD` or a specified commit, with all lines that need attribution
- **Source File**: A file at a specific version (commit) that introduced hunks into the final 'image' of the blamed file
- **Suspects**: Versions of files that might contain hunks used in the final 'image'
- **Unblamed Hunks**: Portions of the file not yet associated with their originating commits

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `BlameRanges` | Represents one or more line ranges to blame in a file | Used to specify which lines to blame, with 1-based inclusive ranges (matching git's behavior) |
| `Options` | Configuration options for blame operations | Configures the diff algorithm, line ranges, and time filtering |
| `Outcome` | The result of a blame operation | Contains blame entries, file content, and statistics |
| `BlameEntry` | Maps a section of the blamed file to the source file that introduced it | Core output unit that maps regions to commits |
| `Statistics` | Performance metrics about the blame operation | Tracks traversed commits, decoded trees, etc. |
| `UnblamedHunk` | Tracks regions in the blamed file not yet associated with commits | Internal type used during processing |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Error` | Error conditions that can occur during blame operations | `EmptyTraversal`, `FileMissing`, `InvalidLineRange`, etc. |
| `Offset` | Describes line offsets between versions | `Added`, `Deleted` |
| `Change` | Represents a change between two blobs | `Unchanged`, `AddedOrReplaced`, `Deleted` |
| `Either` | Generic type for representing one of two possibilities | `Left`, `Right` |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `file` | Main entry point for blaming a file | `fn file(odb, suspect, cache, resource_cache, file_path, options) -> Result<Outcome, Error>` |
| `process_changes` | Processes changes between versions to track blame | `fn process_changes(hunks_to_blame, changes, suspect, parent) -> Vec<UnblamedHunk>` |
| `process_change` | Core algorithm function that handles a single change | `fn process_change(new_hunks_to_blame, offset, suspect, parent, hunk, change) -> (Option<UnblamedHunk>, Option<Change>)` |
| `coalesce_blame_entries` | Merges adjacent blame entries from the same commit | `fn coalesce_blame_entries(lines_blamed: Vec<BlameEntry>) -> Vec<BlameEntry>` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-commitgraph` | Accessing commit graph information for efficient traversal |
| `gix-revwalk` | Walking through commit history in the correct order |
| `gix-trace` | Tracing and performance tracking |
| `gix-date` | Handling Git dates for time-based filtering |
| `gix-diff` | Computing differences between file versions |
| `gix-object` | Working with Git objects like commits, trees, and blobs |
| `gix-hash` | Manipulating Git object IDs |
| `gix-worktree` | Accessing worktree attributes for file handling |
| `gix-traverse` | Traversing Git object graphs, especially the commit graph |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `smallvec` | Efficient storage of small vector data (optimization for suspect lists) |
| `thiserror` | Error type definitions and handling |

## Feature Flags

This crate does not define its own feature flags, but inherits features from its dependencies, particularly `gix-diff`.

## Examples

```rust
use gix_blame::{BlameRanges, Options, file};
use gix_diff::blob::Algorithm;

// Open a repository
let repo = gix::open("/path/to/repo").unwrap();

// Set up options for blame
let mut options = Options::default();
options.diff_algorithm = Algorithm::Patience; // Choose a diff algorithm
options.range = BlameRanges::from_range(10..=20); // Blame lines 10-20 inclusive

// Run blame on a file
let file_path = "src/main.rs";
let resource_cache = &mut gix_diff::blob::Platform::default();
let outcome = file(
    repo.objects(), 
    repo.head_commit().unwrap().id, 
    repo.cache.commit_graph(),
    resource_cache,
    file_path.as_bytes().into(),
    options
).unwrap();

// Process the results
for (entry, lines) in outcome.entries_with_lines() {
    println!("Commit: {}", entry.commit_id);
    println!("Lines: {}", entry.len);
    for line in lines {
        println!("{}", String::from_utf8_lossy(&line));
    }
}
```

## Implementation Details

### The Blame Algorithm

The blame algorithm works as follows:

1. Start with the entire file to blame as an "unblamed hunk" and the starting commit as the "suspect"
2. Traverse the commit graph from the starting point (usually HEAD)
3. For each commit:
   - Check if it modified the file of interest
   - If modified, compute the diff between this version and its parent(s)
   - For each change in the diff:
     - If the change intersects with an unblamed hunk, split the hunk and/or create blame entries
     - Attribute parts of the file to the appropriate commits based on the diff
   - Pass remaining unblamed hunks to parent commits for further analysis
4. Continue until all hunks are blamed or the traversal is complete

### Optimizations

- Uses `SmallVec` for suspect lists, optimizing for the common case where there are few suspects
- Leverages commit graph information when available for faster traversal
- Uses early termination of tree diffs when the file of interest is found, avoiding full tree traversals
- Implements efficient merging of adjacent blame entries from the same commit

### Current Limitations

Based on the crate-status.md file, the current implementation has several limitations that are being worked on:

1. **Performance Improvements Needed**:
   - Custom graph walk which won't run down parents that don't have the path in question
   - Access of trees from commit-graph and fill that information into the traversal info
   - Commit-graph with bloom filter to quickly check if a commit has a path

2. **Missing Features**:
   - Progress reporting
   - Interruptibility
   - Streaming support
   - Support for worktree changes (creating virtual commit on top of HEAD)
   - Shallow-history support
   - Rename tracking (tracking different paths through history)
   - Support for commits to ignore
   - Handling of all blame corner cases from Git

## Testing Strategy

The crate uses a combination of unit tests and integration tests:

- Unit tests focus on the core algorithm functions like `process_change` and the behavior of data structures
- Integration tests use real Git repositories (created in test fixtures) to verify the blame results match expected behavior
- Comparisons with git's own blame implementation to ensure correctness