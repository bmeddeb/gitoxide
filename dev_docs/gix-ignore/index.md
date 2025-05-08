# gix-ignore

## Overview

The `gix-ignore` crate provides functionality for parsing `.gitignore` files and matching file paths against ignore patterns. It implements Git's ignore rules with full compatibility, including support for negated patterns and precious file markers. The crate is designed to be efficient and ergonomic, working with Git's specific pattern matching semantics to determine which files should be excluded from version control operations.

## Architecture

The crate is built on top of the `gix-glob` crate, extending it with specific functionality for Git's ignore rules. The architecture consists of several key components:

1. **Pattern Parsing**: Logic for parsing Git-specific ignore patterns from files or strings, handling comments, blank lines, and special prefixes like negation (`!`) and precious file markers (`$`).

2. **Ignore Searching**: A system for organizing multiple patterns from different sources (like global, repository-level, and directory-specific ignore files) and efficiently matching paths against them while respecting their precedence rules.

3. **Classification**: A mechanism to distinguish between different kinds of ignored files, particularly "expendable" files (regular ignored files) and "precious" files (ignored but should not be deleted during operations like checkout).

The design closely follows Git's behavior, prioritizing:

- **Correctness**: Matching Git's rules exactly, including pattern precedence and directory-specific ignores
- **Performance**: Efficiently handling large repositories with many ignore patterns
- **Flexibility**: Supporting all of Git's ignore features like negation and precious files

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Search` | Main struct organizing patterns from multiple sources | Used to build a hierarchy of ignore patterns and match paths against them |
| `search::Match<'a>` | Represents a pattern that matched a path | Contains pattern, source info, and classification |
| `parse::Lines<'a>` | Iterator over line-wise ignore patterns | Used to parse patterns from a buffer |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Kind` | Classification of ignored files | `Expendable` - Regular ignored files, `Precious` - Ignored but should not be removed |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `parse` | Parse ignore patterns from a byte buffer | `fn parse(bytes: &[u8]) -> parse::Lines<'_>` |
| `search::pattern_matching_relative_path` | Find a pattern matching a path | `fn pattern_matching_relative_path<'a>(...) -> Option<Match<'a>>` |
| `search::pattern_idx_matching_relative_path` | Find index of a pattern matching a path | `fn pattern_idx_matching_relative_path(...) -> Option<usize>` |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `search::Ignore` | Implementation of gix-glob's Pattern trait for ignore patterns | Used to associate ignore patterns with classification |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-glob` | Core pattern matching functionality for gitignore patterns |
| `gix-path` | Path manipulation and conversion between different path formats |
| `gix-trace` | Logging and tracing utilities |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Byte string handling for paths that may not be valid UTF-8 |
| `unicode-bom` | Handling of Unicode Byte Order Marks in ignore files |
| `serde` | Optional serialization/deserialization support |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enable serialization/deserialization support | `serde`, `bstr/serde`, `gix-glob/serde` |
| `document-features` | Documentation for feature flags | `document-features` |

## Examples

### Basic Ignore Pattern Parsing

```rust
use gix_ignore::{parse, Kind};
use bstr::ByteSlice;

// Parse patterns from a .gitignore file
let ignore_content = b"# Comments are ignored\n*.log\n!important.log\n$precious.txt";
let patterns = parse(ignore_content).collect::<Vec<_>>();

// Patterns include the pattern itself, line number, and kind (expendable/precious)
assert_eq!(patterns.len(), 3);

// Check pattern properties
let (pattern1, line1, kind1) = &patterns[0];
assert_eq!(pattern1.text, "*.log");
assert_eq!(*line1, 2);
assert_eq!(*kind1, Kind::Expendable);

let (pattern2, line2, kind2) = &patterns[1];
assert_eq!(pattern2.text, "important.log");
assert_eq!(pattern2.is_negative(), true);
assert_eq!(*line2, 3);
assert_eq!(*kind2, Kind::Expendable);

let (pattern3, line3, kind3) = &patterns[2];
assert_eq!(pattern3.text, "precious.txt");
assert_eq!(*line3, 4);
assert_eq!(*kind3, Kind::Precious);
```

### Using the Search Struct

```rust
use gix_ignore::{Search, Kind};
use gix_glob::pattern::Case;
use bstr::BString;
use std::path::PathBuf;

// Create a Search from Git directory
let git_dir = PathBuf::from(".git");
let mut buf = Vec::new();
let mut search = Search::from_git_dir(&git_dir, None, &mut buf)
    .expect("Failed to load ignore patterns");

// Add more patterns from a .gitignore file
let ignore_content = b"*.log\nnode_modules/\n!important.log";
search.add_patterns_buffer(
    ignore_content, 
    PathBuf::from(".gitignore"), 
    Some(&PathBuf::from("."))
);

// Check if paths match ignore patterns
let path = BString::from("logs/debug.log");
let is_dir = false;

if let Some(matched) = search.pattern_matching_relative_path(
    &path,
    Some(is_dir),
    Case::Sensitive,
) {
    println!("Path matched pattern: {:?}", matched.pattern.text);
    println!("Pattern from: {:?}", matched.source);
    println!("Kind: {:?}", matched.kind);
} else {
    println!("Path is not ignored");
}
```

### Command-Line Overrides

```rust
use gix_ignore::Search;
use gix_glob::pattern::Case;
use bstr::BString;

// Create a Search from command-line override patterns
let search = Search::from_overrides([
    "*.log",          // Ignore all log files
    "!important.log", // Except important.log
    "$config.json",   // Mark config.json as precious
]);

// Check which paths are ignored
let test_paths = [
    "debug.log",
    "important.log",
    "config.json",
    "src/main.rs",
];

for path in test_paths {
    let path_bstr = BString::from(path);
    let result = search.pattern_matching_relative_path(
        &path_bstr,
        Some(false), // Not a directory
        Case::Sensitive,
    );
    
    match result {
        Some(matched) if matched.kind == Kind::Expendable => {
            println!("{} is ignored (expendable)", path);
        }
        Some(matched) if matched.kind == Kind::Precious => {
            println!("{} is ignored but precious", path);
        }
        _ => {
            println!("{} is not ignored", path);
        }
    }
}
```

## Implementation Details

### Precious Files

One of the unique features of Git's ignore system is support for "precious" files, indicated by a leading `$` in the pattern. These are files that are ignored (won't show up in `git status` by default) but should not be removed during operations like checkout that might remove untracked files.

The `gix-ignore` crate represents this distinction with the `Kind` enum:

- `Kind::Expendable` - Regular ignored files that can be removed
- `Kind::Precious` - Ignored files that should be preserved

### Pattern Parsing Rules

The crate implements Git's specific pattern parsing rules:

1. **Comments**: Lines starting with `#` are ignored
2. **Empty Lines**: Blank lines or lines with only whitespace are ignored
3. **Trailing Whitespace**: Removed unless explicitly escaped with backslashes
4. **Negation**: Patterns starting with `!` negate previous matches
5. **Precious Files**: Patterns starting with `$` mark precious files
6. **Escaping**: Backslashes can escape special characters (e.g., `\#` matches a literal `#`)
7. **BOM Handling**: Unicode BOMs are properly skipped

### Pattern Matching Precedence

The pattern matching follows Git's precedence rules:

1. More specific patterns take precedence over less specific ones
2. Later patterns override earlier ones
3. Negative patterns (`!pattern`) override positive ones
4. Patterns from more specific directories override ones from parent directories

### Search Hierarchy

The `Search` struct organizes patterns from multiple sources in a hierarchy:

1. **Global Ignores**: System-wide ignores from configuration
2. **User Ignores**: User-specific ignores from configuration (e.g., `~/.gitignore`)
3. **Repository Ignores**: From `.git/info/exclude`
4. **Working Tree Ignores**: From `.gitignore` files in the repository
5. **Command-Line Overrides**: Patterns specified via command-line arguments

## Testing Strategy

The crate is extensively tested to ensure compatibility with Git's behavior:

1. **Unit Tests**: For individual components like pattern parsing and matching
2. **Fixtures**: Test files with known patterns and expected matches
3. **Baseline Tests**: Comparing results with Git's own output using `git check-ignore`
4. **Edge Cases**: Testing special cases like BOMs, trailing whitespace, and escaped characters

The tests cover various scenarios:

- Basic pattern matching
- Directory-specific ignore files
- Negated patterns
- Precious file markers
- Path case sensitivity
- Pattern ordering and precedence