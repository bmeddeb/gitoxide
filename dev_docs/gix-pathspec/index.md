# gix-pathspec

## Overview

The `gix-pathspec` crate implements Git's pathspec functionality, which provides a powerful pattern matching system for specifying and filtering file paths in a Git repository. Pathspecs go beyond simple glob patterns by supporting special prefixes (magic signatures), attribute-based filtering, and various matching modes. This crate is used throughout gitoxide for commands that operate on subsets of files, such as `git add`, `git checkout`, and `git grep`.

## Architecture

The crate is built around a core `Pattern` type that represents a parsed pathspec and a `Search` type that manages multiple patterns. The architecture consists of several key components:

1. **Pattern Parsing**: Logic for parsing Git's complex pathspec syntax, including magic signatures like `:(icase)`, attribute specifications, and path patterns.

2. **Path Normalization**: Functionality to convert arbitrary paths to repository-relative paths with proper handling of absolute paths, relative components, and different path separators.

3. **Matching System**: Efficient algorithms for matching paths against pathspecs, with support for various matching modes (literal, glob, path-aware glob) and case sensitivity options.

The design prioritizes:

- **Compatibility**: Following Git's pathspec semantics exactly
- **Performance**: Using optimizations like common prefix detection to quickly filter large sets of paths
- **Flexibility**: Supporting all pathspec features including magic signatures, attributes, and different matching modes

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Pattern` | Represents a parsed pathspec with its path, magic signatures, search mode, and attributes | `Pattern::from_bytes("*.rs", defaults)` |
| `Search` | Manages a collection of pathspec patterns | Used to match multiple paths against multiple patterns |
| `search::Match<'a>` | Represents a successful match | Contains matched pattern, sequence number, and match kind |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `SearchMode` | How wildcards in patterns are interpreted | `ShellGlob`, `Literal`, `PathAwareGlob` |
| `search::MatchKind` | How a path matched against a pattern | `Always`, `Prefix`, `WildcardMatch`, `Verbatim` |
| `parse::Error` | Various errors that can occur during parsing | Multiple variants for different parsing errors |
| `normalize::Error` | Errors that can occur during path normalization | `AbsolutePathOutsideOfWorktree`, `OutsideOfWorktree` |

### Bitflags

| Bitflag | Description | Values |
|---------|-------------|--------|
| `MagicSignature` | Flags representing pathspec magic signatures | `TOP`, `ICASE`, `EXCLUDE`, `MUST_BE_DIR` |

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Defaults` | Default settings for pathspec parsing | Configures default signature, search mode, and literalness |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-glob` | Core pattern matching and glob handling |
| `gix-path` | Path manipulation and normalization |
| `gix-attributes` | Handling attribute specifications in pathspecs |
| `gix-config-value` | Parsing configuration values related to pathspecs |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Byte string handling for paths that may not be valid UTF-8 |
| `bitflags` | Defining magic signature flags |
| `thiserror` | Error handling infrastructure |

## Feature Flags

This crate doesn't define its own feature flags but inherits features from its dependencies.

## Examples

### Basic Pathspec Parsing

```rust
use gix_pathspec::{parse, Defaults, MagicSignature, SearchMode};

// Parse a simple pathspec
let defaults = Defaults::default();
let pattern = parse(b"*.rs", defaults).unwrap();
assert_eq!(pattern.path(), "*.rs".as_bytes());
assert_eq!(pattern.search_mode, SearchMode::ShellGlob);

// Parse a pathspec with magic signature
let pattern = parse(b":(icase)*.rs", defaults).unwrap();
assert!(pattern.signature.contains(MagicSignature::ICASE));
assert_eq!(pattern.path(), "*.rs".as_bytes());

// Parse a pathspec with attributes
let pattern = parse(b":(attr:binary -diff)*.bin", defaults).unwrap();
assert_eq!(pattern.attributes.len(), 2);
assert_eq!(pattern.path(), "*.bin".as_bytes());
```

### Path Matching with a Search

```rust
use std::path::Path;
use gix_pathspec::{parse, Defaults, Search};
use bstr::{BStr, ByteSlice};
use gix_attributes::search::Outcome;

// Create a search with multiple patterns
let defaults = Defaults::default();
let patterns = [
    parse(b"src/*.rs", defaults).unwrap(),
    parse(b":(exclude)test/*.rs", defaults).unwrap(),
    parse(b":(icase)README.md", defaults).unwrap(),
];
let search = Search::new(patterns);

// Match paths against the search
let path = "src/main.rs".as_bytes().as_bstr();
let is_dir = false;

// Define a function to handle attributes (simple version that always returns true)
let mut attribute_handler = |_: &BStr, _, _, _: &mut Outcome| true;

if let Some(matched) = search.pattern_matching_relative_path(
    path, 
    Some(is_dir),
    &mut attribute_handler,
) {
    println!("Path matched: {:?}", matched.pattern.path());
    println!("Match kind: {:?}", matched.kind);
    println!("Is excluded: {}", matched.is_excluded());
} else {
    println!("Path did not match any pattern");
}

// Check if a directory might contain matching files
let dir_path = "src".as_bytes().as_bstr();
if search.can_match_relative_path(dir_path, Some(true)) {
    println!("Directory might contain matching files");
}
```

### Normalizing Paths Against a Working Directory

```rust
use std::path::{Path, PathBuf};
use gix_pathspec::{parse, Defaults, Pattern};

// Parse a pathspec
let defaults = Defaults::default();
let mut pattern = parse(b"subdir/*.rs", defaults).unwrap();

// Normalize the pattern against a working directory
let prefix = Path::new("current/dir");  // Current directory relative to repo root
let root = Path::new("/path/to/repo");  // Absolute path to repo root

pattern.normalize(prefix, root).unwrap();

// Now the pattern is properly normalized relative to the repository root
println!("Normalized pattern: {}", pattern);  // Outputs: ":(glob)current/dir/subdir/*.rs"
println!("Prefix directory: {:?}", pattern.prefix_directory()); // The part to match case-sensitively
```

## Implementation Details

### Pathspec Magic Signatures

Git pathspecs support "magic signatures" that modify how pattern matching works:

- `TOP` (written as `/` or `:(top)`) - Match from the root of the repository
- `ICASE` (written as `:(icase)`) - Match case-insensitively
- `EXCLUDE` (written as `^`, `!`, or `:(exclude)`) - Negate the match
- `MUST_BE_DIR` (written as a trailing `/`) - Match only directories

These are represented in the crate as bitflags in the `MagicSignature` type, and they can be combined in various ways.

### Search Modes

The crate supports three distinct search modes:

1. **ShellGlob**: The default mode, similar to shell glob patterns
2. **Literal**: Treats special characters literally, turning off glob matching
3. **PathAwareGlob**: Special mode where `*` doesn't match `/` but `**` does

These can be specified in pathspecs using the `:(literal)` and `:(glob)` prefixes.

### Attribute-Based Filtering

Git pathspecs can include attribute specifications like `:(attr:binary -diff)`, which filter files based on their Git attributes. The `gix-pathspec` crate fully supports this feature, integrating with the `gix-attributes` crate to check if files have the required attributes.

### Optimization Techniques

The crate uses several optimizations to match paths efficiently:

1. **Common Prefix Detection**: The `Search` struct identifies common prefixes among patterns to quickly filter out non-matching paths.

2. **Prefix Directory Matching**: Special handling for directory prefixes allows early rejection of paths that cannot match any pattern.

3. **Match Kind Classification**: Different kinds of matches (verbatim, wildcard, prefix) are tracked to allow for more precise filtering.

4. **Fast Path for Literal Patterns**: Patterns without wildcards use a more efficient direct comparison algorithm.

### Path Normalization

The `normalize` method of `Pattern` handles several complex cases:

- Converting absolute paths to repository-relative paths
- Handling paths with `..` components
- Setting the `prefix_len` field to optimize case-sensitive matching
- Converting backslashes to forward slashes on Windows

## Testing Strategy

The crate uses a comprehensive testing approach:

1. **Parsing Tests**: Extensive tests for both valid and invalid pathspec syntax
2. **Normalization Tests**: Tests for path normalization edge cases
3. **Search Tests**: Tests for matching paths against single and multiple patterns
4. **Default Value Tests**: Tests for environment variable-based default settings

These tests ensure the crate's behavior matches Git's expected behavior across all supported platforms and edge cases.