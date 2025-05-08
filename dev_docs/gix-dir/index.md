# gix-dir

The `gix-dir` crate implements Git-style directory walking functionality, providing an efficient way to traverse and classify files and directories in a repository's working directory. This crate is a critical component in gitoxide's ability to implement Git operations like `status`, `clean`, and `checkout`.

## Architecture and Design

`gix-dir` is designed around a model of efficient traversal with flexible filtering, status classification, and directory collapsing. The main components are:

### Core Components

1. **EntryRef and Entry**: Represent files and directories during traversal
   - `EntryRef<'a>`: A borrowed representation with a lifetime
   - `Entry`: An owned representation without lifetime constraints
   - Both track repository-relative paths, status, properties, and types

2. **Walking Function**: The primary `walk()` function that traverses directories
   - Traverses from a specified worktree root
   - Classifies entries using Git-style rules
   - Supports pathspec filtering
   - Can be configured with various options
   - Provides control over recursion and filtering via the Delegate trait

3. **Classification System**: Determines the status of each entry
   - Classifies entries as tracked, untracked, ignored, or pruned
   - Detects special properties like empty directories or `.git` directories
   - Handles pathspec matching

4. **Directory Collapsing**: Optimizes output by collapsing directories
   - Can represent entire directory trees as a single entry when appropriate
   - Configurable via emission mode settings

### Key Types

- **Status**: Classifies entries as `Tracked`, `Untracked`, `Ignored(Kind)`, or `Pruned`
- **Kind**: Identifies the type of entry as `File`, `Directory`, `Symlink`, `Repository`, or `Untrackable`
- **Property**: Tracks special properties like `DotGit`, `EmptyDirectory`, `EmptyDirectoryAndCWD`, or `TrackedExcluded`
- **PathspecMatch**: Describes how pathspecs match entries (`Verbatim`, `WildcardMatch`, `Prefix`, `Excluded`, or `Always`)

### Delegate Pattern

The crate uses a delegate pattern to provide flexibility in how entries are processed:

- `Delegate` trait allows customizing whether to emit entries and whether to recurse into directories
- `Collect` is a ready-made delegate implementation for collecting entries

## Core Functionality

### Directory Walking

The core function `walk()` performs a Git-style directory traversal:

```rust
pub fn walk(
    worktree_root: &Path,
    ctx: Context<'_>,
    options: Options<'_>,
    delegate: &mut dyn Delegate,
) -> Result<(Outcome, PathBuf), Error>
```

This function:
1. Determines the traversal root using pathspec information or explicit path
2. Classifies the root entry
3. Decides whether to recurse based on the root's classification
4. If recursion is warranted, traverses the directory tree
5. Emits entries to the delegate based on configuration options
6. Returns statistics about the traversal and the actual traversal root

### Entry Classification

Entries are classified based on:

1. Index status (tracked or not)
2. Ignore status (matched by `.gitignore` rules)
3. Pathspec matching
4. Special properties (e.g., `.git` directories, empty directories)
5. File system type (file, directory, symlink)

The classification process handles platform-specific details like case sensitivity and Unicode normalization.

### Recursive Traversal

The recursive traversal logic:

1. Reads directory entries efficiently
2. Classifies each entry
3. Determines whether to recurse into subdirectories
4. Optionally collapses directories with consistent status
5. Emits entries to the delegate based on configuration

### Platform Considerations

The crate handles platform-specific considerations:
- Case sensitivity (optional ignore-case mode for case-insensitive file systems)
- Unicode precomposition (important for macOS)
- Symlink handling (configurable treatment of symlinks to directories)
- Current working directory detection (important for deletion safety)

## Typical Use Cases

1. **Git Status Implementation**: Traversing the worktree to determine the status of files
2. **Git Clean Implementation**: Finding untracked files to remove
3. **Checkout Operations**: Walking the directory tree during checkout
4. **Git Add Implementation**: Finding untracked files to add to the index

## Dependencies

`gix-dir` depends on several other gitoxide crates:

- `gix-trace`: For tracing and debugging
- `gix-index`: For accessing Git index information
- `gix-discover`: For repository discovery
- `gix-fs`: For file system operations
- `gix-path`: For path manipulation
- `gix-pathspec`: For pathspec matching
- `gix-worktree`: For working tree operations
- `gix-object`: For access to Git objects
- `gix-ignore`: For `.gitignore` handling
- `gix-utils`: For utility functions

## Feature Flags

The crate doesn't expose its own feature flags but works with the feature flags from its dependencies.

## Performance Considerations

The crate includes comments about potential performance improvements:
- Mentions that parallel directory traversal could be significantly faster
- Notes the possibility of using libraries like `jwalk` for better parallel performance
- Analyzes trade-offs between the current implementation and more sophisticated alternatives

## Error Handling

Comprehensive error handling for various scenarios:
- Interrupted traversals
- Worktree root issues
- Symlinks in traversal path
- Directory reading failures
- File metadata access failures

## Testing

Extensive tests cover many scenarios:
- Special file types (FIFOs, symlinks)
- Empty directories
- Nested repositories
- Ignored files and directories
- Pathspec filtering
- Directory collapsing
- Current working directory considerations
- Platform-specific behaviors