# gix-revwalk

## Overview

The `gix-revwalk` crate provides utility types for traversing the Git commit graph. It is designed as a plumbing crate intended for consumption by other plumbing crates in the gitoxide ecosystem. The crate enables efficient traversal of commit history, associating custom data with commits, and prioritizing commits during graph traversal operations.

## Architecture

The crate's architecture is built around two primary components:

1. **Graph**: A data structure for storing and traversing commit information, with the ability to associate arbitrary data with each commit.
2. **PriorityQueue**: A utility for ordering commits based on custom criteria, typically used for time-based sorting during graph traversal.

The design follows these principles:

- **Laziness**: Commit information is loaded on-demand to minimize memory usage.
- **Caching**: Accessed commits are cached to avoid redundant loading from the object database.
- **Flexibility**: Custom data can be associated with commits to support various algorithms.
- **Performance**: Optimized for efficient graph traversal with support for accelerating traversal using the commit-graph if available.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Graph<'find, 'cache, T>` | A commit graph that allows associating arbitrary data of type `T` with commits | Used for commit traversal while tracking custom state information |
| `Commit<T>` | An owned commit with parents, commit time, generation, and associated data | Stores commit information extracted from the graph |
| `LazyCommit<'graph, 'cache>` | A handle to commit information that's loaded on-demand | Provides access to commit data without eagerly loading everything |
| `Parents<'graph, 'cache>` | An iterator over a commit's parents | Used to traverse parent-child relationships |
| `PriorityQueue<K, T>` | A queue that orders items by a key | Used for prioritizing commits during graph traversal |

### Traits

The crate doesn't define any public traits.

### Functions

Most functionality is provided as methods on the core structs rather than standalone functions.

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `get_or_insert_default::Error` | Error during lookup or insertion of commit data | `Lookup`, `ToOwned` |
| `insert_parents::Error` | Error during parent insertion | `Lookup`, `Decode`, `Parent` |
| `iter_parents::Error` | Error while iterating over commit parents | `DecodeCommit`, `DecodeCommitGraph` |
| `to_owned::Error` | Error during conversion to owned commit | `Decode`, `CommitGraphParent`, `CommitGraphTime` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | Used for object ID representation and manipulation |
| `gix-object` | Provides functionality for working with Git objects, particularly commits |
| `gix-date` | Handles Git date/time operations for commit timestamps |
| `gix-hashtable` | Used to implement the internal mapping between object IDs and associated data |
| `gix-commitgraph` | Accelerates commit graph operations when available |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `thiserror` | Error type definitions and derivation |
| `smallvec` | Optimized vector storage for small collections like parent lists |

## Feature Flags

The crate doesn't define specific feature flags.

## Examples

```rust
use gix_hash::ObjectId;
use gix_object::Find;
use gix_revwalk::{Graph, PriorityQueue};
use gix_date::SecondsSinceUnixEpoch;

// Create a graph with commit tracking
let repo_objects: Box<dyn Find> = /* ... */;
let commitgraph_cache = None; // Or provide a commitgraph for acceleration
let mut graph = Graph::<()>::new(repo_objects, commitgraph_cache);

// Start with a specific commit
let commit_id = ObjectId::from_hex("abcdef1234567890abcdef1234567890abcdef12").unwrap();
let _ = graph.try_lookup_or_insert(commit_id, |_data| {
    // Initialize or update data associated with this commit
});

// Insert parents recursively
let _ = graph.insert_parents(
    &commit_id, 
    &mut |id, timestamp| (), // Create new data for parents
    &mut |id, data| {}, // Update existing parent data
    false // Process all parents, not just the first
);

// Use a priority queue for time-based traversal
let mut queue = PriorityQueue::new();
for (id, commit_data) in graph.detach() {
    // Add commits to queue ordered by timestamp (newest first)
    queue.insert(std::cmp::Reverse(commit_data.commit_time), id);
}

// Process commits in timestamp order
while let Some((time, id)) = queue.pop() {
    // Process each commit...
}
```

## Implementation Details

### Commit Access Optimization

The Graph structure employs two approaches to access commit information:

1. **Object Database**: When a commit isn't in the commit-graph, it's loaded from the object database.
2. **Commit-Graph**: When available, commit information is retrieved from this highly optimized structure.

This dual approach ensures fast access while maintaining compatibility with all repositories.

### Lazy Loading

Commits are loaded lazily and cached in the Graph's internal map. This ensures:
- Memory efficiency by only loading necessary commits
- Performance optimization by caching already processed commits

### Parent Traversal

The crate handles the complexity of parent access with special consideration for:
- Octopus merges (commits with multiple parents)
- Handling shallow repositories where some commits might be missing
- First-parent traversal for linear history

### Queue Implementation

The PriorityQueue implementation provides efficient prioritization for commit traversal algorithms. It uses a binary heap internally and offers operations to:
- Insert items with priority keys
- Extract highest-priority items
- Iterate through items in priority order

## Testing Strategy

The crate's tests focus on verifying:
1. Correct traversal of the commit graph
2. Proper handling of commit data associations
3. Correct implementation of priority queue operations
4. Error handling for edge cases like missing commits

Tests typically use small, well-defined repository structures to validate traversal algorithms.