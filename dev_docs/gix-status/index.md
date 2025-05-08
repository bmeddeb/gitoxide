# gix-status

## Overview

The `gix-status` crate provides functionality for computing the status of a Git repository, similar to `git status`. It implements various forms of status comparisons between different representations of the repository state, including:

- Index (staging area) to working tree comparison
- Support for detecting conflicts
- Symlink safety verification
- Optional rename and copy detection (with the `worktree-rewrites` feature)

Unlike the `gix-diff` crate, which compares similar items (like two trees or two blobs), `gix-status` specializes in comparing dissimilar representations, such as an index and a working tree. It's designed with performance in mind, allowing quick checks to determine if a working tree is dirty and providing detailed information about file status.

## Architecture

The `gix-status` crate follows a modular architecture with a clean separation of concerns:

1. **Core Status Functions**:
   - `index_as_worktree`: Compares the index to the working tree
   - `index_as_worktree_with_renames`: Enhanced comparison with rename detection (when enabled)

2. **Visitor Pattern**:
   - Utilizes a visitor-based approach where a collector processes status changes
   - Allows for different implementations to handle the results

3. **Path Safety**:
   - `SymlinkCheck` component ensures symlink safety, preventing potential security issues
   - Validates paths when they are queried in sort order for efficiency

4. **Parallel Processing**:
   - Employs parallel processing for performance
   - Separate threads for directory walking and index modification checks

The architecture prioritizes performance through careful buffer management, parallel processing, and early termination options when only checking if a repository is dirty.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `SymlinkCheck` | Validates paths to ensure they don't traverse symbolic links | Used to safely build file paths in a repository |
| `index_as_worktree::Context` | Provides context for status computation | Includes pathspec, attributes stack, filters, and interruption flag |
| `index_as_worktree::Options` | Configuration for status computation | Controls filesystem capabilities, thread limits, and stat comparison options |
| `index_as_worktree::Outcome` | Detailed statistics about the status operation | Includes counters for processed entries, skipped entries, and I/O operations |
| `index_as_worktree::Recorder` | Records status changes | Default implementation of `VisitEntry` that collects changes in a vector |
| `index_as_worktree_with_renames::Context` | Enhanced context for status with renames | Adds resource caching for efficient rename detection |
| `index_as_worktree_with_renames::Recorder` | Records status changes with rename information | Collects changes including potential renames |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `index_as_worktree::VisitEntry` | Visitor for processing entry status changes | `index_as_worktree::Recorder`, custom implementations |
| `index_as_worktree::traits::CompareBlobs` | Compares two blobs for equality | Custom implementations providing content comparison logic |
| `index_as_worktree::traits::SubmoduleStatus` | Determines the status of a submodule | Custom implementations for submodule checking |
| `index_as_worktree_with_renames::VisitEntry` | Enhanced visitor that includes rename information | `index_as_worktree_with_renames::Recorder`, custom implementations |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `index_as_worktree` | Compares index to working tree | `fn index_as_worktree<'index, T, U, Find, E>(index: &'index gix_index::State, worktree: &Path, collector: &mut impl VisitEntry<'index, ContentChange = T, SubmoduleStatus = U>, compare: impl CompareBlobs<Output = T> + Send + Clone, submodule: impl SubmoduleStatus<Output = U, Error = E> + Send + Clone, objects: Find, progress: &mut dyn gix_features::progress::Progress, ctx: Context<'_>, options: Options) -> Result<Outcome, Error>` |
| `index_as_worktree_with_renames` | Enhanced comparison with rename detection | `fn index_as_worktree_with_renames<'index, T, U, Find, E>(index: &'index gix_index::State, worktree: &Path, collector: &mut impl VisitEntry<'index, ContentChange = T, SubmoduleStatus = U>, compare: impl CompareBlobs<Output = T> + Send + Clone, submodule: impl SubmoduleStatus<Output = U, Error = E> + Send + Clone, objects: Find, progress: &mut dyn gix_features::progress::Progress, ctx: Context<'_>, options: Options<'_>) -> Result<Outcome, Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `index_as_worktree::Change` | How an index entry differs from the worktree | `Removed`, `Type`, `Modification`, `SubmoduleModification` |
| `index_as_worktree::EntryStatus` | Status of an index entry compared to the worktree | `Conflict`, `Change`, `NeedsUpdate`, `IntentToAdd` |
| `index_as_worktree::Conflict` | Type of conflict for an entry | `BothDeleted`, `AddedByUs`, `DeletedByThem`, `AddedByThem`, `DeletedByUs`, `BothAdded`, `BothModified` |
| `index_as_worktree_with_renames::Entry` | Enhanced entry with rename information | `Modification`, `DirectoryContents`, `Rewrite` |
| `index_as_worktree_with_renames::RewriteSource` | Source of a rewrite operation | `RewriteFromIndex`, `CopyFromDirectoryEntry` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-index` | Index file structure and manipulation |
| `gix-fs` | Filesystem operations and stack for path verification |
| `gix-hash` | Hash operations for object identification |
| `gix-object` | Git object manipulation and identification |
| `gix-path` | Path handling and conversions |
| `gix-features` | Progress reporting and parallel execution |
| `gix-filter` | Content filtering between Git and worktree |
| `gix-worktree` | Worktree attribute handling |
| `gix-pathspec` | Path specification matching |
| `gix-dir` | Directory walking (with `worktree-rewrites` feature) |
| `gix-diff` | Diff algorithms (with `worktree-rewrites` feature) |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `thiserror` | Error handling |
| `filetime` | File time manipulation for stat comparisons |
| `bstr` | Binary string handling |
| `portable-atomic` | Atomic operations for platforms without 64-bit atomics |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `worktree-rewrites` | Adds support for tracking rewrites (renames and copies) along with checking for worktree modifications | `gix-dir`, `gix-diff` |

## Examples

```rust
use gix_hash::ObjectId;
use gix_index::State as IndexState;
use gix_status::{
    index_as_worktree::{self, Recorder},
    SymlinkCheck,
};
use std::path::Path;
use std::sync::atomic::AtomicBool;

// Simple blob comparison that records if blobs are different
struct BlobCompare;
impl index_as_worktree::traits::CompareBlobs for BlobCompare {
    type Output = bool;
    
    fn compare_blobs(
        &self,
        _a_id: &ObjectId,
        a_data: &[u8],
        _b_id: &ObjectId,
        b_data: &[u8],
    ) -> Self::Output {
        a_data != b_data
    }
}

// Simple submodule status checker
struct SubmoduleChecker;
impl index_as_worktree::traits::SubmoduleStatus for SubmoduleChecker {
    type Output = ();
    type Error = std::io::Error;
    
    fn check_submodule(
        &self,
        _worktree_path: &Path,
        _rela_path: &bstr::BStr,
    ) -> Result<Self::Output, Self::Error> {
        Ok(())
    }
}

// Function to check if the working tree is dirty
fn is_worktree_dirty(
    index: &IndexState,
    worktree_path: &Path,
    objects: &impl gix_object::Find,
) -> Result<bool, Box<dyn std::error::Error>> {
    // Create a recorder for status changes
    let mut recorder = Recorder::default();
    
    // Create attribute stack and filter pipeline
    let stack = gix_worktree::Stack::from_attributes(None);
    let filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    
    // Setup context and interruption flag
    let interrupt = AtomicBool::new(false);
    let context = index_as_worktree::Context {
        pathspec: gix_pathspec::Search::new(Vec::new()),
        stack,
        filter,
        should_interrupt: &interrupt,
    };
    
    // Configure options for early termination on first change
    let mut options = index_as_worktree::Options::default();
    options.early_termination_on_first_change = true;
    
    // Run the status check
    let outcome = index_as_worktree(
        index,
        worktree_path,
        &mut recorder,
        BlobCompare,
        SubmoduleChecker,
        objects,
        &mut gix_features::progress::Discard,
        context,
        options,
    )?;
    
    // Repository is dirty if any change was recorded
    Ok(!recorder.records.is_empty())
}
```

## Implementation Details

### Path Safety with Symlinks

The `SymlinkCheck` struct is a critical security component that ensures paths don't traverse through symbolic links, which could potentially lead to accessing files outside the repository. It builds on the `gix_fs::Stack` to verify path components:

1. On Unix-like systems, it checks if any component along the path is a symlink (except the leaf)
2. On Windows, symlink verification is skipped as Windows handles symlinks differently

This defense is particularly important for operations like `git checkout` where an attacker could potentially create malicious symlinks to access sensitive files.

### Status Computation Performance

The crate employs several optimizations for performance:

1. **Hierarchical Directory Scanning**:
   - Uses an optimized directory walker that can skip entire subtrees
   - Efficiently processes files in depth-first order

2. **Parallel Processing**:
   - Directory walking and index modification checks run in separate threads
   - Optional thread limits for environments with resource constraints

3. **Early Termination**:
   - Can terminate processing as soon as any change is found
   - Useful for quickly checking if a repository is dirty

4. **Stat Caching**:
   - Tracks file stats to avoid unnecessary content comparisons
   - Identifies "racy clean" entries that need further verification

5. **Pathspec Optimization**:
   - Utilizes common prefix optimization to skip entries that don't match pathspec
   - Reduces the number of entries processed

### Handling of "Racy Clean" Entries

Git status has to deal with "racy clean" files - files whose modification time is close to the index's mtime. The crate handles these by:

1. Identifying potentially racy entries based on mtime comparison
2. Performing full content comparison for these entries
3. Updating the entry's stat information to avoid the race condition in future calls

## Testing Strategy

The crate includes comprehensive tests covering various aspects of status computation:

1. **Fixture-based Tests**:
   - Uses prepared Git repositories for testing specific scenarios
   - Includes fixtures for conflicts, submodules, and various file states

2. **Integration Tests**:
   - Tests that verify correct status computation for different repository states
   - Covers edge cases like intent-to-add files, conflicts, and submodules

3. **Symlink Safety Tests**:
   - Tests specifically for the `SymlinkCheck` functionality
   - Verifies that symlink traversal is properly prevented

The tests ensure that the status computation matches Git's behavior, particularly for edge cases and security-sensitive operations.