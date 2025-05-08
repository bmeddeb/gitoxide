# gix-merge

## Overview

The `gix-merge` crate provides facilities for merging Git objects at different levels: blobs, trees, and commits. It implements Git's merge algorithms in a modular and flexible way, allowing for fine-grained control over the merge process. This crate serves as a foundation for implementing Git merge operations in the gitoxide ecosystem.

## Architecture

The crate's architecture follows a layered approach, where each layer builds upon the previous one:

1. **Blob merging**: The lowest level, handling the three-way merge of file contents.
2. **Tree merging**: The middle layer, handling structure-based merges of directory trees, which may trigger blob merges as needed.
3. **Commit merging**: The highest level, handling the merge of commits by first determining their merge base and then performing a tree merge.

Each layer exposes a clean API and follows a modular design that allows for customization through configuration options. The architecture emphasizes:

- **Separation of concerns**: Each merge type (blob, tree, commit) is handled by a dedicated module.
- **Clear resolution semantics**: Explicitly tracks conflicts and resolutions.
- **Extensibility**: Allows for custom merge drivers and resolution strategies.
- **Error handling**: Comprehensive error types that describe what went wrong during the merge.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `blob::Platform` | A utility for gathering and processing state for three-way blob merges | Central point for blob merge functionality |
| `blob::Pipeline` | A conversion pipeline from Git objects to mergeable format | Transforms objects based on Git attributes |
| `blob::Driver` | Defines an external program that performs three-way merges | Used for customizing merge behavior |
| `tree::Outcome` | The result of a tree merge operation | Contains the merged tree and conflict information |
| `tree::Conflict` | Description of a conflict encountered during a tree merge | Tracks conflicts and their potential resolutions |
| `tree::Options` | Configuration options for tree merges | Controls merge behavior and conflict resolution |
| `commit::Outcome` | The result of a commit merge operation | Contains tree merge results and merge base information |
| `commit::Options` | Configuration options for commit merges | Controls merge base selection and tree merge behavior |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `blob::Resolution` | Defines if a merge is conflicted or not | `Complete`, `CompleteWithAutoResolvedConflict`, `Conflict` |
| `blob::ResourceKind` | Classifies the side of a resource for merging | `CurrentOrOurs`, `OtherOrTheirs`, `CommonAncestorOrBase` |
| `blob::BuiltinDriver` | Built-in merge drivers | `Text`, `Binary`, `Union` |
| `tree::Resolution` | Describes how a conflict was resolved | Various specialized resolution types |
| `tree::ResolutionFailure` | Describes a conflict that failed to be resolved | Various failure scenarios |
| `tree::ResolveWith` | Strategy for resolving tree conflicts | `Ancestor`, `Ours` |
| `tree::TreatAsUnresolved` | Determines what is considered an unresolved conflict | Configuration for content and tree merges |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `blob()` | Performs a three-way merge of blob content | Not explicitly exported as a standalone function |
| `tree()` | Performs a three-way merge of trees | `fn tree<Find: gix_object::Find + 'find>(objects: Find, base: &oid, ours: &oid, theirs: &oid, options: Options) -> Result<Outcome<'find>, Error>` |
| `commit()` | Performs a three-way merge of commits | `fn commit<'find, Find: gix_object::Find + 'find>(objects: Find, base_finder: impl MergeBaseFinder, ours: &oid, theirs: &oid, options: Options) -> Result<Outcome<'find>, Error>` |
| `virtual_merge_base()` | Creates a virtual merge base for multiple merge bases | Used internally for handling octopus merges |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For object ID representation and handling |
| `gix-object` | For accessing Git object data and manipulation |
| `gix-filter` | For filtering content based on Git attributes |
| `gix-worktree` | For accessing the working tree and attributes |
| `gix-diff` | For detecting changes between trees |
| `gix-revwalk` | For traversing commit history |
| `gix-revision` | For resolving revisions and finding merge bases |
| `gix-index` | For indexing files and handling merge conflicts |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `imara-diff` | For text-based diffing and merging |
| `bstr` | For efficient byte string handling |
| `thiserror` | For error type definitions |
| `serde` | Optional, for serialization/deserialization support |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enable serialization/deserialization support | `serde`, with serde features for `gix-hash` and `gix-object` |

## Examples

```rust
use gix_hash::{oid, ObjectId};
use gix_merge::{commit, tree};
use gix_object::Find;

// Perform a tree merge
fn merge_trees<F: Find + 'static>(
    objects: F,
    base_id: &ObjectId,
    our_id: &ObjectId,
    their_id: &ObjectId,
) -> Result<(), Box<dyn std::error::Error>> {
    // Configure merge options
    let options = tree::Options {
        rewrites: Some(gix_diff::Rewrites::default()),
        ..Default::default()
    };
    
    // Perform the merge
    let merge_result = tree(objects, base_id, our_id, their_id, options)?;
    
    // Check if there are unresolved conflicts
    if merge_result.has_unresolved_conflicts(tree::TreatAsUnresolved::default()) {
        println!("Merge has conflicts that need manual resolution");
        for conflict in &merge_result.conflicts {
            println!("Conflict: {:?}", conflict.resolution);
        }
    } else {
        println!("Merge completed successfully!");
        // Use the merged tree
        let merged_tree = merge_result.tree;
        println!("Merged tree has {} entries", merged_tree.len());
    }
    
    Ok(())
}

// Perform a commit merge
fn merge_commits<F: Find + 'static>(
    objects: F,
    our_commit: &ObjectId,
    their_commit: &ObjectId,
) -> Result<(), Box<dyn std::error::Error>> {
    // Configure merge options
    let options = commit::Options {
        allow_missing_merge_base: false,
        use_first_merge_base: false,
        tree_merge: tree::Options::default(),
    };
    
    // Create a function to find merge bases
    let base_finder = |ours, theirs| {
        gix_revision::merge_base::all(objects.clone(), ours, theirs)
    };
    
    // Perform the merge
    let merge_result = commit(objects, base_finder, our_commit, their_commit, options)?;
    
    println!("Merge base tree: {}", merge_result.merge_base_tree_id);
    
    if let Some(bases) = &merge_result.merge_bases {
        println!("Found {} merge base(s)", bases.len());
        if !merge_result.virtual_merge_bases.is_empty() {
            println!("Created {} virtual merge base(s)", merge_result.virtual_merge_bases.len());
        }
    }
    
    // Check tree merge result for conflicts
    if merge_result.tree_merge.has_unresolved_conflicts(tree::TreatAsUnresolved::default()) {
        println!("Merge has conflicts that need manual resolution");
    } else {
        println!("Merge completed successfully!");
    }
    
    Ok(())
}
```

## Implementation Details

### Blob Merging

Blob merging in `gix-merge` is implemented through several mechanisms:

1. **Built-in Drivers**: The crate provides several built-in merge drivers:
   - `Text`: For text files, with configurable conflict style
   - `Binary`: For binary files, resolving by selecting one side
   - `Union`: For text files, combining conflicting changes without markers

2. **External Drivers**: Custom merge drivers can be defined and used through `blob::Driver`, which specifies a command to execute for the merge.

3. **Conversion Pipeline**: The `blob::Pipeline` handles converting objects between Git storage format and mergeable format, respecting Git attributes.

4. **Merge Platform**: The `blob::Platform` coordinates the entire blob merge process, handling resources, drivers, and attribute lookup.

### Tree Merging

Tree merging combines both structural changes and content changes:

1. **Structural Merge**: The algorithm first identifies structural changes (additions, deletions, renames) using `gix-diff`.

2. **Rename Detection**: Tree merging can optionally perform rename detection to handle file renames appropriately.

3. **Conflict Resolution**: When conflicts occur, the algorithm provides detailed information about the conflict and may attempt automatic resolution based on configured strategies.

4. **Tree Building**: The final merged tree is constructed by applying non-conflicting changes and resolved conflicts to the base tree.

5. **Index Updates**: The crate provides functionality to update the Git index with conflict information for unresolved conflicts.

### Commit Merging

Commit merging extends tree merging with merge base determination:

1. **Merge Base Finding**: Uses `gix-revision` to find the common ancestor(s) of the commits being merged.

2. **Virtual Merge Base**: When multiple merge bases exist, the algorithm can recursively merge them to create a single virtual merge base.

3. **Tree Extraction**: Extracts the trees from commits for tree merging.

4. **Tree Merging**: Performs the actual tree merge using the determined merge base.

### Conflict Handling

The crate provides comprehensive conflict tracking and resolution:

1. **Conflict Types**: Different conflict types are modeled explicitly through enums like `tree::Resolution` and `tree::ResolutionFailure`.

2. **Resolution Strategies**: Configurable strategies for resolving different types of conflicts.

3. **Index Integration**: Support for updating the Git index with conflict information, enabling tools to present conflicts to users.

4. **Conflict Markers**: Text conflicts can include configurable conflict markers, with support for recursively increasing marker size.

## Testing Strategy

The crate is tested through a combination of:

1. **Unit Tests**: Testing individual components like merge drivers and algorithms.

2. **Integration Tests**: Testing the entire merge process with different types of changes and conflicts.

3. **Fixture-Based Tests**: Using pre-constructed Git repositories with known merge scenarios.

4. **Comparison with Git**: Verifying merge results match Git's output for the same inputs.

The test coverage focuses on:

- Common merge scenarios (additions, modifications, deletions)
- Edge cases (renames, type changes, nested conflicts)
- Different resolution strategies
- Handling of binary and text content
- Integration with Git attributes and filters