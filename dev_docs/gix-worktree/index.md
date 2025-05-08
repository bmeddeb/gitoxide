# gix-worktree

## Overview

The `gix-worktree` crate provides utility types and functionality for working with Git worktrees in the gitoxide ecosystem. It offers a powerful caching mechanism for efficiently executing operations on directories and files encountered in sorted order, with support for Git attributes and ignore patterns. This crate is essential for implementing Git commands that interact with the working directory, such as checkout, status, and add operations.

## Architecture

`gix-worktree` follows a stack-based architecture that efficiently tracks the current path and associated state as it traverses a directory hierarchy. The design enables:

1. **Path Traversal**: The crate builds on `gix-fs::Stack` to provide navigation through directory hierarchies, maintaining efficient state tracking.

2. **Attribute Handling**: When the `attributes` feature is enabled, the crate can read and apply `.gitattributes` files found in the repository.

3. **Ignore Pattern Processing**: The crate can read and apply `.gitignore` patterns at various levels (overrides, directory-specific, and global).

4. **Directory Creation**: During checkout operations, it efficiently creates directories as needed, respecting platform-specific requirements and Git's symbolic link rules.

5. **Object Database Integration**: The crate can access attribute and ignore files directly from the Git object database when they aren't in the working directory (for example, when a file has the "skip-worktree" flag set).

The architecture is designed to be memory-efficient by reusing buffers and avoiding redundant paths operations.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Stack` | Central component that maintains state during directory traversal | Used for all operations that need to work with the worktree files |
| `Platform` | Provides access to the state of the current path | Used to check attributes and ignore patterns for a specific path |
| `State` | Configures the stack behavior for different operations | Determines whether the stack handles attributes, ignore patterns, and directory creation |
| `Statistics` | Collects performance metrics during operations | Used for tracking and optimizing performance |
| `State::Attributes` | Manages Git attribute information | Tracks attribute patterns as directories are traversed |
| `State::Ignore` | Manages Git ignore pattern information | Determines which files are excluded from Git operations |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| N/A | The crate primarily uses composition rather than traits for its architecture | N/A |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `Stack::new` | Creates a new stack instance | `fn new(worktree_root: impl Into<PathBuf>, state: State, case: glob::pattern::Case, buf: Vec<u8>, id_mappings: Vec<PathIdMapping>) -> Self` |
| `Stack::from_state_and_ignore_case` | Creates a stack with the correct case sensitivity | `fn from_state_and_ignore_case(root: impl Into<PathBuf>, ignore_case: bool, state: State, index: &gix_index::State, path_backing: &gix_index::PathStorageRef) -> Self` |
| `Stack::at_path` | Navigates to a relative path and provides platform for lookups | `fn at_path(&mut self, relative: impl ToNormalPathComponents, mode: Option<gix_index::entry::Mode>, objects: &dyn gix_object::Find) -> std::io::Result<Platform<'_>>` |
| `Stack::at_entry` | Navigates to an index entry and provides platform for lookups | `fn at_entry<'r>(&mut self, relative: impl Into<&'r BStr>, mode: Option<gix_index::entry::Mode>, objects: &dyn gix_object::Find) -> std::io::Result<Platform<'_>>` |
| `Platform::is_excluded` | Checks if the current path is excluded by ignore patterns | `fn is_excluded(&self) -> bool` |
| `Platform::excluded_kind` | Returns the kind of exclusion if the path is excluded | `fn excluded_kind(&self) -> Option<gix_ignore::Kind>` |
| `Platform::matching_attributes` | Gets attributes for the current path | `fn matching_attributes(&self, out: &mut gix_attributes::search::Outcome) -> bool` |
| `State::for_checkout` | Creates a state configured for checkout operations | `fn for_checkout(unlink_on_collision: bool, validate: gix_validate::path::component::Options, attributes: Attributes) -> Self` |
| `State::for_add` | Creates a state configured for add operations | `fn for_add(attributes: Attributes, ignore: Ignore) -> Self` |
| `State::id_mappings_from_index` | Extracts object IDs for attribute and ignore files | `fn id_mappings_from_index(&self, index: &gix_index::State, paths: &gix_index::PathStorageRef, case: Case) -> Vec<PathIdMapping>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `State` | Configures the stack's behavior | `CreateDirectoryAndAttributesStack`, `AttributesAndIgnoreStack`, `AttributesStack`, `IgnoreStack` |
| `state::ignore::Source` | Controls where ignore files are read from | `IdMapping`, `WorktreeThenIdMappingIfNotSkipped` |
| `state::attributes::Source` | Controls where attribute files are read from | `IdMapping`, `WorktreeThenIdMappingIfNotSkipped` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-fs` | Provides the underlying `Stack` implementation for path traversal |
| `gix-index` | Used for interacting with the Git index and determining file modes |
| `gix-attributes` | Used for processing `.gitattributes` files (with `attributes` feature) |
| `gix-ignore` | Used for processing `.gitignore` files |
| `gix-glob` | Provides pattern matching for attributes and ignore patterns |
| `gix-path` | Used for path manipulation and conversion |
| `gix-hash` | Used for working with Git object identifiers |
| `gix-object` | Used for accessing objects in the Git object database |
| `gix-validate` | Used for validating path components (with `attributes` feature) |
| `gix-features` | Provides feature flag integrations |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Provides binary string handling for paths and pattern matching |
| `serde` | Optional serialization/deserialization support |
| `document-features` | Optional feature documentation generation |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `attributes` | Enables support for `.gitattributes` files | `gix-attributes`, `gix-validate` |
| `serde` | Implements serialization and deserialization for data structures | `serde`, and adds `serde` feature to various dependencies |
| `document-features` | Enables documentation of feature flags | `document-features` |

## Examples

Here's an example of using the `Stack` to create directories during a checkout operation:

```rust
use gix_worktree::{Stack, stack::State};
use gix_index::entry::Mode;
use std::path::Path;

// Initialize the stack for a checkout operation
fn initialize_checkout_stack(repo_root: &Path, index: &gix_index::State) -> Stack {
    // Check if the filesystem is case-insensitive
    let fs_caps = gix_fs::Capabilities::probe(repo_root);
    
    // Create attributes state for checkout
    let attributes = gix_worktree::stack::state::Attributes::default();
    
    // Configure state for checkout
    let state = State::for_checkout(
        true, // unlink on collision
        gix_validate::path::component::Options::default(),
        attributes,
    );
    
    // Initialize path backing
    let path_backing = index.path_backing();
    
    // Create the stack
    Stack::from_state_and_ignore_case(
        repo_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    )
}

// Example of creating directories during checkout
fn checkout_file(
    stack: &mut Stack,
    entry_path: &str,
    mode: Mode,
    objects: &dyn gix_object::Find
) -> std::io::Result<()> {
    // Navigate to the entry path
    let platform = stack.at_entry(entry_path, Some(mode), objects)?;
    
    // At this point, all necessary directories have been created
    // and we can work with the file at path
    let dest_path = platform.path();
    
    // Now we can write the file content, etc.
    println!("Ready to write to: {}", dest_path.display());
    
    Ok(())
}
```

Here's an example of using the `Stack` to check if a file is ignored:

```rust
use gix_worktree::{Stack, stack::State};
use gix_ignore::Search as IgnoreSearch;
use std::path::Path;

// Initialize the stack for status operations
fn initialize_status_stack(repo_root: &Path, index: &gix_index::State) -> std::io::Result<Stack> {
    // Check if the filesystem is case-insensitive
    let fs_caps = gix_fs::Capabilities::probe(repo_root);
    
    // Get Git directory
    let git_dir = repo_root.join(".git");
    
    // A buffer for reading files
    let mut buf = Vec::with_capacity(512);
    
    // Create ignore state
    let ignore = gix_worktree::stack::state::Ignore::new(
        IgnoreSearch::default(), // overrides
        IgnoreSearch::from_git_dir(&git_dir, None, &mut buf)?, // git-dir ignores
        None, // exclude file name override
        gix_worktree::stack::state::ignore::Source::WorktreeThenIdMappingIfNotSkipped,
    );
    
    // Create state for status operations
    let state = State::IgnoreStack(ignore);
    
    // Initialize path backing
    let path_backing = index.path_backing();
    
    // Create the stack
    Ok(Stack::from_state_and_ignore_case(
        repo_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    ))
}

// Check if a file is ignored
fn is_file_ignored(
    stack: &mut Stack,
    file_path: &str,
    objects: &dyn gix_object::Find
) -> std::io::Result<bool> {
    // Navigate to the file path
    let is_file = Some(gix_index::entry::Mode::FILE);
    let platform = stack.at_entry(file_path, is_file, objects)?;
    
    // Check if the file is excluded by any ignore pattern
    Ok(platform.is_excluded())
}
```

## Implementation Details

### Path Traversal Strategy

The `Stack` uses a stack-based approach to track the current path during traversal. As it moves into and out of directories, it updates the state appropriately. This approach is more efficient than repeatedly parsing full paths for each file, especially when processing files in a sorted order (which is common in Git operations).

### Object ID Mappings

One notable optimization is the use of object ID mappings. When files like `.gitattributes` or `.gitignore` have the skip-worktree flag set in the index, they may not be present in the working directory. In these cases, the crate can fetch the content directly from the object database using the object ID stored in the index.

The `State::id_mappings_from_index` function creates these mappings, and they're used throughout the traversal process to efficiently access files.

### Attribute and Ignore Stacks

Both attributes and ignore patterns follow Git's hierarchical rules:

1. For attributes:
   - Global patterns (outside the repository)
   - Root patterns (repository-wide)
   - Directory-specific patterns (for the current directory)

2. For ignore patterns:
   - Override patterns (typically from command line)
   - Directory-specific patterns (from `.gitignore` files)
   - Global patterns (user-wide or system-wide)

The implementation maintains separate stacks for each level, pushing and popping patterns as directories are traversed.

### Case Sensitivity Handling

Git behavior can differ based on whether the filesystem is case-sensitive or case-insensitive. The crate handles this by taking case sensitivity into account during pattern matching, allowing Git-like behavior across different platforms.

### Creation and Validation of Directories

During checkout operations, the crate can create directories as needed, with several important capabilities:

1. **Path Component Validation**: Ensures that path components follow Git's rules for valid paths.
2. **Symlink Handling**: Can optionally unlink files or symlinks that conflict with directories that need to be created.
3. **Recursive Creation**: Creates parent directories as needed.

### Statistics Collection

The crate collects detailed statistics during operations, which can be useful for performance analysis and debugging. Statistics include counts of directory operations, pattern matches, and other performance-relevant metrics.

## Testing Strategy

The crate's testing focuses on comparing its behavior with Git's reference implementation:

1. **Baseline Tests**: Tests compare the crate's behavior with the output of Git commands like `git check-ignore`.

2. **Fixture Tests**: Scripted fixtures create test repositories with specific characteristics for testing various scenarios.

3. **Edge Cases**: Tests include edge cases like nested ignores, attribute inheritance, and case sensitivity issues.

4. **Integration Tests**: Tests ensure the crate works correctly within the larger gitoxide ecosystem.

5. **Platform-Specific Tests**: Some tests validate behavior on different platforms with varying filesystem capabilities.

The tests are particularly important for ensuring compatible behavior with Git, as both attribute and ignore pattern handling can be complex and have subtle edge cases.