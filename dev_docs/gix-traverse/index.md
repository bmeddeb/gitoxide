# gix-traverse

## Overview

The `gix-traverse` crate provides various algorithms for traversing Git commit graphs and tree structures in the gitoxide ecosystem. It offers efficient iterators for navigating through the history of Git repositories with different traversal orders and filtering capabilities. The crate supports both commit graph traversal and tree traversal with optimized implementations for different use cases.

## Architecture

The crate's architecture is divided into two main modules:

1. **Commit Traversal**: Implements different algorithms for traversing the commit history graph, with specialized traversal strategies for different performance requirements and ordering needs.

2. **Tree Traversal**: Provides algorithms for traversing Git tree objects, with both depth-first and breadth-first approaches.

The design follows these principles:

- **Efficiency**: Implementations are optimized for memory usage and performance.
- **Flexibility**: Multiple traversal algorithms with different characteristics are provided.
- **Laziness**: Information is loaded on-demand to minimize unnecessary work.
- **Acceleration**: Support for the Git commit-graph to speed up traversal operations when available.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `commit::Simple<Find, Predicate>` | A fast, simple iterator over commit ancestors | Basic commit graph traversal with minimal state |
| `commit::Topo<Find, Predicate>` | A topological commit walker | Advanced traversal that maintains topological ordering |
| `commit::Info` | Information about a commit gathered during traversal | Contains commit metadata like ID and parent IDs |
| `tree::Recorder` | Records tree entries during traversal | Tracks changes in tree structure |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `commit::Parents` | Specifies how to handle commit parents | `All`, `First` |
| `commit::simple::Sorting` | Defines the traversal order | `BreadthFirst`, `ByCommitTime`, `ByCommitTimeCutoff` |
| `commit::simple::CommitTimeOrder` | Direction for time-based sorting | `NewestFirst`, `OldestFirst` |
| `commit::topo::Sorting` | Topological sorting modes | `DateOrder`, `TopoOrder` |
| `commit::Either` | Source of commit information | `CommitRefIter`, `CachedCommit` |
| `tree::visit::Action` | Control flow for tree traversal | `Continue`, `Cancel`, `Skip` |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `tree::Visit` | Interface for tree traversal callbacks | `tree::Recorder` and custom implementations |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `commit::find` | Find commit information from either commit-graph or object database | `fn find<'cache, 'buf, Find>(cache: Option<&'cache gix_commitgraph::Graph>, objects: Find, id: &gix_hash::oid, buf: &'buf mut Vec<u8>) -> Result<Either<'buf, 'cache>, Error>` |
| `tree::depthfirst` | Traverse a tree in depth-first order | `fn depthfirst<StateMut, Find, V>(root: ObjectId, state: StateMut, objects: Find, delegate: &mut V) -> Result<(), Error>` |
| `tree::breadthfirst` | Traverse a tree in breadth-first order | `fn breadthfirst<StateMut, Find, V>(root: ObjectId, state: StateMut, objects: Find, delegate: &mut V) -> Result<(), Error>` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For object ID representation and manipulation |
| `gix-object` | For accessing Git object data |
| `gix-date` | For commit timestamp handling |
| `gix-hashtable` | For efficient object ID lookups |
| `gix-revwalk` | For priority queue implementation and graph data structures |
| `gix-commitgraph` | For accelerated commit traversal using the commit-graph |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `smallvec` | For optimized storage of small collections (like parent lists) |
| `thiserror` | For error type definitions |
| `bitflags` | For efficient state tracking in topological traversal |

## Feature Flags

The crate doesn't define specific feature flags.

## Examples

### Simple Commit Traversal

```rust
use gix_hash::ObjectId;
use gix_traverse::commit::{self, simple::Sorting, Parents, Info};

fn traverse_commit_history(
    repo_path: &std::path::Path,
    start_commit: &str
) -> Result<Vec<Info>, Box<dyn std::error::Error>> {
    // Open repository and get object database
    let repo = gix::open(repo_path)?;
    let odb = repo.objects.clone();
    
    // Convert commit hash to ObjectId
    let commit_id = ObjectId::from_hex(start_commit)?;
    
    // Create a commit traversal iterator
    let commits = commit::Simple::new([commit_id], odb)
        // Sort by commit date, newest first
        .sorting(Sorting::ByCommitTime(commit::simple::CommitTimeOrder::NewestFirst))?
        // Follow all parents (not just first parent)
        .parents(Parents::All)
        // Use commit-graph if available for acceleration
        .commit_graph(repo.object_cache.commit_graph());
    
    // Collect commit information
    let commit_info = commits.collect::<Result<Vec<_>, _>>()?;
    
    Ok(commit_info)
}
```

### Topological Commit Traversal

```rust
use gix_hash::ObjectId;
use gix_traverse::commit::{Topo, topo, Info};

fn traverse_in_topological_order(
    repo_path: &std::path::Path,
    start_commit: &str
) -> Result<Vec<Info>, Box<dyn std::error::Error>> {
    // Open repository and get object database
    let repo = gix::open(repo_path)?;
    let odb = repo.objects.clone();
    
    // Convert commit hash to ObjectId
    let commit_id = ObjectId::from_hex(start_commit)?;
    
    // Create a topological traversal iterator
    let commits = topo::Builder::new([commit_id], odb.clone())
        // Use true topological order (--topo-order in git)
        .sorting(topo::Sorting::TopoOrder)
        // Use commit-graph if available
        .commit_graph(repo.object_cache.commit_graph())
        .build()?;
    
    // Collect commits in topological order
    let commit_info = commits.collect::<Result<Vec<_>, _>>()?;
    
    Ok(commit_info)
}
```

### Tree Traversal with Recording

```rust
use gix_hash::ObjectId;
use gix_traverse::tree::{self, recorder};

fn traverse_tree_structure(
    repo_path: &std::path::Path,
    tree_id: &str
) -> Result<Vec<recorder::Entry>, Box<dyn std::error::Error>> {
    // Open repository and get object database
    let repo = gix::open(repo_path)?;
    let odb = repo.objects.clone();
    
    // Convert tree hash to ObjectId
    let id = ObjectId::from_hex(tree_id)?;
    
    // Create a recorder for tree traversal
    let mut recorder = tree::Recorder::from_recording_paths();
    
    // Traverse the tree in depth-first order
    tree::depthfirst(id, tree::depthfirst::State::default(), odb, &mut recorder)?;
    
    // Get the recorded entries
    let entries = recorder.records;
    
    Ok(entries)
}
```

## Implementation Details

### Commit Traversal Algorithms

#### Simple Traversal

The `commit::Simple` implementation provides a fast, memory-efficient traversal of the commit graph with several sorting options:

1. **Breadth-First**: Visits commits in the order they are discovered in the graph, similar to a breadth-first search.

2. **By Commit Time**: Orders commits by their commit timestamp, with options for newest-first or oldest-first traversal.

3. **By Commit Time with Cutoff**: Similar to time-based sorting but stops traversal at commits older than a specified time.

The simple traversal maintains minimal state, making it efficient for large repositories.

#### Topological Traversal

The `commit::Topo` implementation provides a more sophisticated traversal that ensures parent commits are not visited before all their children. It supports two sorting modes:

1. **Date Order**: Similar to `git log --date-order`, showing commits in commit timestamp order but ensuring children are visited before parents.

2. **Topo Order**: Similar to `git log --topo-order`, ensuring children are visited before parents while also avoiding mixing commits from different lines of development.

The topological traversal maintains more state but provides better ordering guarantees, especially for complex branching histories.

### Tree Traversal Algorithms

#### Depth-First Traversal

The depth-first traversal (`tree::depthfirst`) immediately descends into subtrees as they are encountered, providing a natural tree structure traversal. This is useful for operations that need to process directories before moving to siblings.

#### Breadth-First Traversal

The breadth-first traversal (`tree::breadthfirst`) processes all entries at the current level before descending into subtrees. This is useful for operations that need to process all files at a given level before moving deeper.

### Optimization Techniques

1. **Commit-Graph Integration**: Both traversal algorithms can use the Git commit-graph file if available, which provides a significant performance boost by:
   - Avoiding object database lookups
   - Providing fast access to parent relationships
   - Offering pre-computed generation numbers for efficient topological sorting

2. **Memory Reuse**: The implementations reuse buffers and other memory allocations to minimize garbage collection overhead.

3. **SmallVec Usage**: Parent lists and other small collections use `SmallVec` to avoid heap allocations for the common case of commits with few parents.

4. **Filtering**: Both traversal algorithms support predicates that can filter commits during traversal, avoiding unnecessary work for commits that aren't of interest.

## Testing Strategy

The crate is tested through a combination of:

1. **Unit Tests**: Tests for individual components and algorithms.

2. **Integration Tests**: Tests that verify the traversal algorithms produce correct results on real repository data.

3. **Scripted Repository Tests**: Tests using scripted repositories that create specific commit graphs and tree structures to validate traversal behavior.

4. **Performance Tests**: Tests that measure the performance of different traversal strategies under varying conditions.

Tests especially focus on:
- Correct handling of complex commit histories with merges and branches
- Proper ordering according to the chosen sorting method
- Correct behavior with and without the commit-graph
- Handling of edge cases like shallow repositories or grafted commits