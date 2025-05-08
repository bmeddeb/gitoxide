# gix-path

## Overview

`gix-path` is a specialized crate in the gitoxide ecosystem that provides path handling utilities specifically designed for Git's path representation requirements. It addresses the nuances of path handling across different platforms, particularly focusing on the differences between Unix and Windows path conventions, and handles edge cases like invalid UTF-8 sequences that can occur in path representations.

The crate provides robust path conversion and manipulation functions that ensure path handling follows Git's conventions while being platform-aware and handling encoding issues gracefully.

## Architecture

`gix-path` follows a modular design that focuses on path conversion, normalization, and platform-specific handling:

### Core Design Principles

1. **Platform-Aware Conversion** - Path conversions between native paths and Git's internal representation are handled differently depending on the platform, with special care for Windows paths.

2. **Lossless Conversions Where Possible** - The crate tries to perform lossless conversions between different path representations, falling back to lossy conversions only when necessary.

3. **Robust Error Handling** - Conversion errors, particularly on Windows with unpaired UTF-16 surrogates, are properly captured and reported rather than silently producing incorrect results.

4. **Git-Compatible Path Normalization** - The crate provides functions to normalize paths according to Git's rules, eliminating unnecessary path components without filesystem access.

### Module Structure

The crate is organized into focused modules:

- **convert.rs** - Core conversion functions between byte strings, OsStrings, and Paths
- **realpath.rs** - Functions for resolving symlinks and producing absolute paths
- **relative_path.rs** - Utilities for working with relative paths
- **util.rs** - General path utility functions
- **env/** - Environment-related path utilities and path lookup functions

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `RelativePath` | A type that manages a path relative to some root directory | Used when working with paths that need to be maintained relative to a specific directory |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `try_into_bstr` | Convert a Path to a byte string, with special handling for Windows UTF-16 to UTF-8 conversion | `fn try_into_bstr<'a>(path: impl Into<Cow<'a, Path>>) -> Result<Cow<'a, BStr>, Utf8Error>` |
| `into_bstr` | Non-failing version of `try_into_bstr` that panics on conversion errors | `fn into_bstr<'a>(path: impl Into<Cow<'a, Path>>) -> Cow<'a, BStr>` |
| `try_from_byte_slice` | Convert a byte slice to a Path, with UTF-8 validation on Windows | `fn try_from_byte_slice(input: &[u8]) -> Result<&Path, Utf8Error>` |
| `from_byte_slice` | Non-failing version of `try_from_byte_slice` that panics on conversion errors | `fn from_byte_slice(input: &[u8]) -> &Path` |
| `normalize` | Resolve relative components in a path without filesystem access | `fn normalize<'a>(path: Cow<'a, Path>, current_dir: &Path) -> Option<Cow<'a, Path>>` |
| `relativize_with_prefix` | Convert a path to be relative to a given prefix | `fn relativize_with_prefix<'a>(relative_path: &'a Path, prefix: &Path) -> Cow<'a, Path>` |
| `realpath` | Resolve a path by following symlinks to get the actual filesystem path | `fn realpath(path: impl AsRef<Path>) -> Result<PathBuf, Error>` |
| `to_native_separators` | Convert path separators to the platform's preferred form | `fn to_native_separators<'a>(path: impl Into<Cow<'a, BStr>>) -> Cow<'a, BStr>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `realpath::Error` | Error type for path resolution failures | `MaxSymlinksExceeded`, `ExcessiveComponentCount`, `ReadLink`, `CurrentWorkingDir`, `EmptyPath`, `MissingParent` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-trace` | Used for tracing execution of path operations for debugging |
| `gix-validate` | Used for validating path components to ensure they follow Git's rules |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Provides byte string types and utilities for working with binary data that may not be valid UTF-8 |
| `thiserror` | Used for defining error types |
| `once_cell` | Used for lazy initialization of static values |
| `home` | Used for finding the user's home directory on non-WASM platforms |

## Feature Flags

The `gix-path` crate doesn't define any specific feature flags of its own, but it does make use of conditional compilation for platform-specific code paths.

## Examples

```rust
use std::borrow::Cow;
use std::path::{Path, PathBuf};
use bstr::{BStr, BString, ByteSlice};
use gix_path::{into_bstr, from_bstr, normalize, relativize_with_prefix, realpath};

// Convert between Path and byte strings
let path = Path::new("/some/path/to/file.txt");
let bytes: Cow<BStr> = into_bstr(path);
assert_eq!(bytes.as_bstr(), b"/some/path/to/file.txt".as_bstr());

// Convert back to Path
let path_again = from_bstr(bytes);
assert_eq!(path_again, path);

// Normalize a path with relative components
let path = Path::new("a/b/../c/./d/../e");
let normalized = normalize(Cow::Borrowed(path), Path::new("/current/dir")).unwrap();
assert_eq!(normalized, Path::new("a/c/e"));

// Make a path relative to a prefix
let path = Path::new("a/b/c/d/e");
let prefix = Path::new("a/b");
let relative = relativize_with_prefix(path, prefix);
assert_eq!(relative, Path::new("c/d/e"));

// Resolve symlinks in a path
match realpath(Path::new("some/path/with/symlinks")) {
    Ok(real_path) => println!("Real path: {:?}", real_path),
    Err(e) => eprintln!("Failed to resolve path: {}", e),
}
```

## Implementation Details

### Platform-Specific Path Handling

The crate includes careful handling of platform differences, particularly for Windows:

```rust
#[cfg(unix)]
let p = {
    use std::os::unix::ffi::OsStrExt;
    path.as_os_str().as_bytes().into()
};

#[cfg(not(any(unix, target_os = "wasi")))]
let p: &BStr = path.to_str().ok_or(Utf8Error)?.as_bytes().into();
```

This ensures that on Unix systems, paths are treated as raw byte sequences, while on Windows they are properly converted to and from UTF-8, with appropriate error handling.

### Path Separators

Git internally uses forward slashes (`/`) as path separators, but Windows uses backslashes (`\`). The crate provides utilities to convert between these:

```rust
pub fn to_native_separators<'a>(path: impl Into<Cow<'a, BStr>>) -> Cow<'a, BStr> {
    #[cfg(not(windows))]
    let p = to_unix_separators(path);
    #[cfg(windows)]
    let p = to_windows_separators(path);
    p
}
```

This allows code to work with Git's internal forward-slash convention but present paths to the user in the platform's native format.

### Symlink Resolution

The `realpath` function provides careful handling of symlinks, with safeguards against symlink loops and excessive path resolution:

```rust
pub fn realpath_opts(path: &Path, cwd: &Path, max_symlinks: u8) -> Result<PathBuf, Error> {
    // ...
    let mut num_symlinks = 0;
    // ...
    while let Some(component) = components.next() {
        // ...
        if real_path.is_symlink() {
            num_symlinks += 1;
            if num_symlinks > max_symlinks {
                return Err(Error::MaxSymlinksExceeded { max_symlinks });
            }
            // ...
        }
    }
    // ...
}
```

This ensures that path resolution is robust even in the presence of complex symlink structures.

### Path Normalization

The `normalize` function performs path normalization without accessing the filesystem, respecting path semantics:

```rust
pub fn normalize<'a>(path: Cow<'a, Path>, current_dir: &Path) -> Option<Cow<'a, Path>> {
    // ...
    for component in components {
        if let ParentDir = component {
            // Handle ".." components by moving up one level
            // ...
        } else {
            path.push(component);
        }
    }
    // ...
}
```

This allows for safe path manipulation even on paths that don't exist in the filesystem.

## Testing Strategy

The crate includes various tests to verify its behavior:

1. **Unit Tests** - Tests for individual functions to verify their behavior in isolation
2. **Edge Case Tests** - Tests for handling of unusual path formats and invalid UTF-8
3. **Platform-Specific Tests** - Tests for platform-specific behavior on Unix and Windows

The tests focus on ensuring that the path handling is consistent with Git's expectations and that edge cases like invalid UTF-8 and symlink loops are handled correctly.