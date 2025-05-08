# gix-fs

## Overview

The `gix-fs` crate provides file system specific utilities for the gitoxide ecosystem. It handles platform-specific file system capabilities, directory operations, path traversal, and file metadata management. This crate is essential for reliable cross-platform file system operations required by Git implementations.

## Architecture

`gix-fs` follows a modular design with focused components addressing different aspects of file system interaction:

1. **Capabilities Detection**: Automatically detects platform-specific file system capabilities like case sensitivity, unicode normalization, and symlink support.

2. **Path Navigation**: Provides a stack-based mechanism for efficiently navigating directory hierarchies with callbacks.

3. **Directory Operations**: Offers reliable creation and removal of directories with retry logic to handle common failure scenarios.

4. **File Snapshots**: Implements a caching mechanism for file content that can detect when files have been modified and need to be refreshed.

5. **Platform Abstraction**: Provides consistent behavior across different operating systems, handling the differences between Unix and Windows file systems.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Capabilities` | Detects and represents file system capabilities like case sensitivity, unicode normalization, symlink support, and executable bit handling | Used to adapt Git operations to the specific file system capabilities |
| `Stack` | A stack of path components that tracks the current path and supports traversal with callbacks | Efficiently navigate directory hierarchies while performing operations at each level |
| `FileSnapshot<T>` | Generic wrapper for any file-based content with modification time tracking | Used to cache file content and detect when it needs refreshing |
| `SharedFileSnapshot<T>` | Thread-safe reference-counted version of `FileSnapshot` | Allows sharing file content across threads |
| `SharedFileSnapshotMut<T>` | Mutable version of `SharedFileSnapshot` with update capabilities | Used when the snapshot needs to be refreshed or modified |
| `Retries` | Configuration for directory creation retry attempts | Controls resilience of directory operations |
| `Iter` | Iterator for directory creation with retry logic | Used by directory creation functions |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `ToNormalPathComponents` | Converts paths into normalized components | Implemented for `&Path`, `PathBuf`, `&BStr`, `&str`, `&BString` |
| `Delegate` | Callbacks for directory traversal operations | Implemented by users of the `Stack` struct |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `current_dir` | Gets current directory with unicode normalization support | `fn current_dir(precompose_unicode: bool) -> std::io::Result<PathBuf>` |
| `is_executable` | Checks if a file has executable permissions | `fn is_executable(metadata: &std::fs::Metadata) -> bool` |
| `read_dir` | Platform-agnostic directory reading | `fn read_dir<P: AsRef<Path>>(path: P) -> std::io::Result<ReadDir>` |
| `dir::create::all` | Create a directory and all parent directories | `fn all(dir: &Path, retries: Retries) -> std::io::Result<&Path>` |
| `dir::remove::all` | Remove a directory and all its contents | `fn all(dir: &Path) -> std::io::Result<()>` |
| `symlink::create` | Create a symbolic link with platform abstraction | `fn create(src: &Path, dst: &Path) -> std::io::Result<()>` |
| `symlink::remove` | Remove a symbolic link with platform abstraction | `fn remove(path: &Path) -> std::io::Result<()>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `dir::create::Error` | Represents directory creation errors | `Intermediate`, `Permanent` |
| `io_err` | IO error classifier | Contains utility functions |
| `to_normal_path_components::Error` | Errors when normalizing path components | `NotANormalComponent`, `IllegalUtf8` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-path` | Used for path manipulation and normalization |
| `gix-features` | Provides threading utilities and feature flags |
| `gix-utils` | Used for string operations like unicode normalization |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Binary string handling for path components |
| `thiserror` | Error type definitions |
| `serde` | Optional serialization/deserialization support |
| `fastrand` | Random number generation for probing file system capabilities |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization support | `serde` with `std` and `derive` features |

## Examples

Here's how to use the capabilities detection:

```rust
use gix_fs::Capabilities;
use std::path::Path;

// Get default capabilities for the current platform
let default_caps = Capabilities::default();

// Or probe the capabilities on the specific filesystem
let git_dir = Path::new("/path/to/repo/.git");
let caps = Capabilities::probe(git_dir);

// Use capabilities to adapt behavior
if caps.ignore_case {
    // Use case-insensitive operations
}

if caps.precompose_unicode {
    // Handle Unicode normalization
}
```

Using the directory path stack:

```rust
use gix_fs::Stack;
use std::path::PathBuf;

struct MyDelegate;

impl gix_fs::stack::Delegate for MyDelegate {
    fn push_directory(&mut self, stack: &Stack) -> std::io::Result<()> {
        println!("Entering directory: {}", stack.current().display());
        Ok(())
    }
    
    fn push(&mut self, is_last_component: bool, stack: &Stack) -> std::io::Result<()> {
        println!("At: {}", stack.current().display());
        Ok(())
    }
    
    fn pop_directory(&mut self) {
        println!("Exiting directory");
    }
}

let root = PathBuf::from("/path/to/root");
let mut stack = Stack::new(root);
let mut delegate = MyDelegate;

// Navigate to a relative path, triggering delegate callbacks
stack.make_relative_path_current("subdir/file.txt", &mut delegate)?;
```

Creating directories with retry logic:

```rust
use gix_fs::dir::create::{all, Retries};
use std::path::Path;

// Use default retry settings
let path = Path::new("/path/to/new/directory");
all(path, Retries::default())?;

// Or customize retry behavior
let custom_retries = Retries {
    to_create_entire_directory: 3,
    on_create_directory_failure: 10,
    on_interrupt: 5,
};
all(path, custom_retries)?;
```

## Implementation Details

### Platform-Specific Behavior

The crate handles several platform-specific behaviors:

1. **Unicode Normalization**: On macOS, Unicode normalization is particularly important as the file system uses decomposed Unicode, while Git prefers precomposed Unicode. The crate detects this and normalizes paths appropriately.

2. **Case Sensitivity**: Windows and macOS file systems are case-insensitive but case-preserving, while most Unix file systems are case-sensitive. The crate detects this and handles file operations accordingly.

3. **Symbolic Links**: Windows has limited symbolic link support, while Unix systems have full support. The crate abstracts this difference.

4. **Executable Bit**: Unix file systems support the executable bit, while Windows doesn't. The crate provides utilities to handle this.

### File Snapshot Implementation

The `FileSnapshot` structure is particularly interesting as it implements a caching mechanism that can detect when files have been modified. It stores both the content and the modification time, allowing efficient refreshing only when needed.

The thread-safe versions (`SharedFileSnapshot` and `SharedFileSnapshotMut`) use interior mutability and reference counting to allow sharing file content across threads safely.

### Directory Creation with Retry Logic

Directory creation is implemented with sophisticated retry logic to handle common failure scenarios:

1. **Race Conditions**: The code handles race conditions where multiple processes might try to create or delete directories simultaneously.

2. **Parent Directory Missing**: If parent directories don't exist, the code creates them recursively.

3. **Interruptions**: The code handles system interruptions, such as those caused by signals.

### Path Component Handling

The `ToNormalPathComponents` trait provides a uniform interface for extracting normalized path components from different path-like types (strings, byte strings, paths). It ensures that all path components are in a consistent format regardless of the input type.

## Testing Strategy

The crate is tested through:

1. **Unit Tests**: Individual components are tested for correctness.

2. **Platform-Specific Tests**: Tests verify the correct behavior on different operating systems.

3. **Integration Tests**: The crate's interaction with the rest of the gitoxide ecosystem is tested in integration scenarios.

4. **Retry Logic Testing**: Special tests verify that the retry logic works correctly in the face of failures and race conditions.

5. **Cross-Platform Compatibility**: Tests ensure consistent behavior across platforms despite underlying file system differences.