# gix-glob

## Overview

The `gix-glob` crate provides glob pattern matching functionality specifically tailored for Git operations. It implements pattern matching similar to Git's globbing syntax used in `.gitignore` files, `.gitattributes` files, and pathspec matching. The crate is designed to efficiently handle path matching using wildcard patterns and supports Git-specific pattern semantics.

## Architecture

The crate is structured around a core `Pattern` type that represents a parsed glob pattern with associated metadata for optimized matching. The architecture consists of several key components:

1. **Pattern Parsing**: Functionality to parse glob patterns from text, extracting additional metadata like whether the pattern is negated, absolute, or must match a directory.

2. **Wildcard Matching**: A powerful and efficient wildcard matcher that implements Git's pattern matching semantics.

3. **Search Utilities**: Tools for organizing and applying multiple patterns to paths, particularly useful for implementing Git's ignore and attribute systems.

The crate's design prioritizes:

- **Performance**: Using optimizations to quickly match or reject paths
- **Compatibility**: Matching Git's own globbing behavior
- **Flexibility**: Supporting various matching modes and options

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Pattern` | Core type representing a parsed glob pattern with metadata | `Pattern::from_bytes("*.rs")` to create a pattern that matches all Rust files |
| `search::List<T>` | A collection of patterns with their associated values and source information | Used to represent patterns from a `.gitignore` or `.gitattributes` file |
| `search::Mapping<T>` | Associates a pattern with a value and sequence number | Used within `List` to track individual patterns and their associated data |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `pattern::Case` | Specifies case sensitivity for pattern matching | `Sensitive` - case matters, `Fold` - ignore case |

### Bitflags

| Bitflag | Description | Values |
|---------|-------------|--------|
| `pattern::Mode` | Metadata about a pattern that aids in matching | `NO_SUB_DIR`, `ENDS_WITH`, `MUST_BE_DIR`, `NEGATIVE`, `ABSOLUTE` |
| `wildmatch::Mode` | Controls how wildcard matching behaves | `NO_MATCH_SLASH_LITERAL`, `IGNORE_CASE` |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `search::Pattern` | Trait for types that can be converted to patterns with associated values | Implemented by users of the crate for `.gitignore` or `.gitattributes` handlers |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `parse` | Create a `Pattern` by parsing text | `fn parse(text: impl AsRef<[u8]>) -> Option<Pattern>` |
| `wildmatch` | Match a pattern against a value using wildcard rules | `fn wildmatch(pattern: &BStr, value: &BStr, mode: Mode) -> bool` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-path` | For path manipulation and conversions between platform-specific paths and Git's unix-style paths |
| `gix-features` | For general utilities and feature flag support |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | For byte string handling, which is crucial for dealing with path data that may not be valid UTF-8 |
| `bitflags` | For defining the `Mode` flags used to optimize pattern matching |
| `serde` | Optional dependency for serialization/deserialization support |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization and deserialization | `serde`, `bstr/serde`, `bitflags/serde` |
| `document-features` | For building documentation with feature descriptions | `document-features` |

## Examples

### Basic Pattern Matching

```rust
use gix_glob::{parse, wildmatch, wildmatch::Mode};
use bstr::ByteSlice;

// Create a pattern
let pattern = parse("*.rs").unwrap();

// Check if it matches a path
assert!(pattern.matches("file.rs".as_bytes().as_bstr(), Mode::empty()));
assert!(!pattern.matches("file.txt".as_bytes().as_bstr(), Mode::empty()));

// Direct wildmatch usage
assert!(wildmatch(
    "src/*.rs".as_bytes().as_bstr(),
    "src/main.rs".as_bytes().as_bstr(), 
    Mode::NO_MATCH_SLASH_LITERAL
));
```

### Path-Specific Matching

```rust
use gix_glob::{parse, Pattern};
use gix_glob::pattern::Case;
use gix_glob::wildmatch::Mode;
use bstr::ByteSlice;

// Create a pattern that matches paths
let pattern = parse("src/*.rs").unwrap();

// Match a repository-relative path
let path = "src/main.rs".as_bytes().as_bstr();
let is_match = pattern.matches_repo_relative_path(
    path,
    Some(4),           // basename starts at position 4
    Some(false),       // not a directory
    Case::Sensitive,   // case-sensitive matching
    Mode::NO_MATCH_SLASH_LITERAL, // Don't match slashes with wildcards
);
assert!(is_match);
```

### Working with Multiple Patterns

```rust
use std::path::Path;
use gix_glob::search::{Pattern, List};
use bstr::BString;

// Define a pattern type that implements the Pattern trait
#[derive(Clone, PartialEq, Eq, Debug, Hash, Ord, PartialOrd, Default)]
struct MyPattern;

impl Pattern for MyPattern {
    type Value = bool;  // Associate boolean values with patterns

    fn bytes_to_patterns(bytes: &[u8], source: &Path) -> Vec<gix_glob::search::pattern::Mapping<bool>> {
        // Parse pattern lines, assign values...
        vec![]
    }
}

// Create a list of patterns from a file
let mut buf = Vec::new();
let patterns = List::<MyPattern>::from_file(
    "path/to/patterns.txt",
    Some(Path::new("repo/root")),
    true,  // follow symlinks
    &mut buf,
).unwrap().unwrap();

// Use the patterns to match against paths
let path = BString::from("src/file.rs");
```

## Implementation Details

### Pattern Parsing

The pattern parsing logic in `parse.rs` extracts valuable information from the pattern text:

1. Detects leading `!` for negated patterns
2. Identifies patterns that start with `/` as absolute
3. Recognizes trailing `/` to mark patterns that must match directories
4. Checks for absence of `/` to identify patterns that don't match subdirectories
5. Identifies patterns of the form `*literal` for optimization
6. Locates the position of the first wildcard character for prefix optimization

These details are stored in the `Mode` flags and used to accelerate matching operations.

### Wildcard Matching Algorithm

The core matching algorithm in `wildmatch.rs` implements a recursive matcher that handles:

- Simple wildcards (`*` and `?`)
- Character classes (`[abc]`, `[!abc]`)
- POSIX character classes (`[:alpha:]`, `[:digit:]`, etc.)
- Range expressions (`[a-z]`)
- Backslash escaping (`\*` to match a literal asterisk)
- Special handling for slash `/` characters when matching paths

The algorithm includes optimizations to handle common cases efficiently:

- Fast path for patterns without wildcards (direct comparison)
- Prefix optimization for patterns that start with a literal prefix
- Special handling for `*suffix` patterns (checking if the string ends with the suffix)
- Limit on recursion depth to prevent stack overflow with malicious patterns

### Search Functionality

The search module provides utilities for handling collections of patterns, particularly useful for implementing Git's hierarchical pattern matching:

- Organizing patterns into lists with their source files
- Tracking the base directory associated with each pattern list
- Handling pattern ordering and precedence
- Stripping base directories from paths for relative pattern matching

## Testing Strategy

The crate is extensively tested through different test modules:

1. **Pattern Parsing Tests**: Verify that patterns are correctly parsed with the appropriate flags and metadata

2. **Pattern Matching Tests**: Ensure patterns match the expected paths according to Git's rules

3. **Wildmatch Tests**: Validate the wildcard matching algorithm against various pattern/string combinations

4. **Search Tests**: Test the pattern list functionality and hierarchical pattern matching

5. **Baseline Tests**: Compare results against Git's own pattern matching behavior using test fixtures