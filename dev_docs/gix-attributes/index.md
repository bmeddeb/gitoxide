# gix-attributes

## Overview

`gix-attributes` is a crate in the gitoxide ecosystem dedicated to parsing and handling `.gitattributes` files. These files specify attributes for paths in a Git repository, controlling how Git handles files based on their patterns. This includes behavior like text normalization, diff generation, merge strategies, and more.

The crate provides functionality to parse `.gitattributes` files, search for matching attributes for specific paths, and evaluate attribute states based on pattern matching.

## Architecture

The architecture of `gix-attributes` is designed around a flexible and efficient pattern matching system:

1. **Parsing Layer**: Handles the reading and parsing of `.gitattributes` files, including support for comment lines, pattern definitions, and attribute assignments.

2. **Pattern Matching**: Utilizes the `gix-glob` crate for efficient path pattern matching, applying the correct attributes to specific file paths.

3. **Search System**: Implements a search infrastructure to find matching patterns for a given path and determine the effective attribute settings.

4. **Attribute State Management**: Tracks the state of each attribute (set, unset, value, unspecified) and handles attribute macros that can expand to multiple attributes.

5. **Reference-Based Design**: Employs both owned and reference-based types to allow efficient memory usage and avoid unnecessary copying of data.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Name` | Represents a validated attribute name | Used to store attribute names in a validated form |
| `NameRef` | Reference version of `Name` | Used for attribute name comparison without ownership |
| `Assignment` | Holds a name and its assigned state | Represents a complete attribute assignment |
| `AssignmentRef` | Reference version of `Assignment` | Used for assignment comparison without ownership |
| `Search` | The main search infrastructure for patterns | Used to match paths against patterns and find applicable attributes |
| `search::Outcome` | Result of a search operation | Holds all matching attributes for a path |
| `search::MetadataCollection` | Collection of metadata for attributes | Tracks attribute relationships and order |
| `search::Match` | A pattern match with assignment | Represents a matched pattern and its attribute assignment |
| `parse::Lines` | Iterator over attribute lines | Used to parse `.gitattributes` files line by line |
| `parse::Iter` | Iterator over attributes in a line | Used to parse individual attribute assignments in a line |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `State` | The state of an attribute | `Set`, `Unset`, `Value`, `Unspecified` |
| `StateRef` | Reference version of `State` | Same as `State` but with borrowed values |
| `parse::Kind` | Type of parsed attribute line | `Pattern`, `Macro` |
| `Source` | Source of attribute files | `GitInstallation`, `System`, `Git`, `Local` |
| `search::Value` | Value of a pattern mapping | `MacroAssignments`, `Assignments` |
| `search::MatchKind` | Type of attribute match | `Attribute`, `Macro` |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `parse` | Parse attribute assignments from bytes | `fn parse(bytes: &[u8]) -> parse::Lines<'_>` |
| `Search::new_globals` | Create a new search with global attributes | `fn new_globals<P, I>(paths: I, buf: &mut Vec<u8>, collection: &mut search::MetadataCollection) -> Result<Self, std::io::Error>` |
| `Search::add_patterns_file` | Add patterns from a file | `fn add_patterns_file<P>(&mut self, path: P, expect_exists: bool, base: Option<&Path>, buf: &mut Vec<u8>, collection: &mut search::MetadataCollection, allow_macros: bool) -> std::io::Result<()>` |
| `Search::pattern_matching_relative_path` | Find patterns matching a path | `fn pattern_matching_relative_path(&self, rela_path: &BStr, case: Case, containing_dir: Option<&Path>, out: &mut search::Outcome) -> bool` |
| `Outcome::initialize` | Initialize the outcome for search | `fn initialize(&mut self, collection: &search::MetadataCollection)` |
| `Outcome::reset` | Reset the outcome for reuse | `fn reset(&mut self)` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-glob` | Pattern matching for gitattributes patterns |
| `gix-path` | Path handling and manipulation |
| `gix-quote` | Handling of quoted attributes |
| `gix-trace` | Tracing and debugging support |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Binary string handling for non-UTF8 paths |
| `kstring` | Efficient string interning for attribute names |
| `smallvec` | Small vector optimization for attribute lists |
| `unicode-bom` | Handling of byte order mark in files |
| `thiserror` | Error handling |
| `serde` | Serialization support (optional) |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization and deserialization | `serde`, activates `serde` feature on `bstr`, `gix-glob`, and `kstring` |
| `document-features` | Enables feature documentation | `document-features` |

## Examples

### Parsing .gitattributes Files

```rust
use bstr::ByteSlice;
use gix_attributes::{parse, AssignmentRef, StateRef};

// Parse a .gitattributes file
let content = b"*.txt text eol=lf -diff !merge\n";
let lines = parse(content);

for result in lines {
    let (kind, iter, line_number) = result.expect("Valid attributes line");
    
    match kind {
        gix_attributes::parse::Kind::Pattern(pattern) => {
            println!("Pattern: {}", pattern.as_bstr());
            
            // Process attributes for this pattern
            for attr_result in iter {
                let attr = attr_result.expect("Valid attribute");
                println!("  Attribute: {} = {:?}", attr.name.as_str(), attr.state);
            }
        }
        gix_attributes::parse::Kind::Macro(name) => {
            println!("Macro: {}", name.as_str());
            
            // Process macro attributes
            for attr_result in iter {
                let attr = attr_result.expect("Valid attribute");
                println!("  Defines: {} = {:?}", attr.name.as_str(), attr.state);
            }
        }
    }
}
```

### Searching for Matching Attributes

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search};
use gix_glob::pattern::Case;
use std::path::Path;

// Create a new search with global attributes
let mut collection = MetadataCollection::default();
let mut buf = Vec::new();
let mut search = Search::new_globals(
    [Path::new("/path/to/global/gitattributes")].into_iter(),
    &mut buf,
    &mut collection,
)?;

// Add repository-specific attributes
search.add_patterns_file(
    Path::new("/path/to/repo/.gitattributes"),
    true,
    None,
    &mut buf,
    &mut collection,
    true, // allow macros
)?;

// Initialize search outcome
let mut outcome = gix_attributes::search::Outcome::default();
outcome.initialize(&collection);

// Find attributes for a specific path
let path = "src/main.rs".as_bytes().as_bstr();
let has_match = search.pattern_matching_relative_path(
    path,
    Case::Sensitive,
    None,
    &mut outcome,
);

if has_match {
    // Iterate through matching attributes
    for m in outcome.iter() {
        if !m.assignment.state.is_unspecified() {
            println!(
                "Attribute: {} = {:?}",
                m.assignment.name.as_str(),
                m.assignment.state
            );
        }
    }
}
```

### Handling Attribute Macros

```rust
use bstr::ByteSlice;
use gix_attributes::{parse, search::MetadataCollection, Search};
use gix_glob::pattern::Case;
use std::path::Path;

// Content with a macro definition
let content = b"[attr]binary -diff -merge -text\n*.bin binary\n";

// Set up search infrastructure
let mut collection = MetadataCollection::default();
let mut search = Search::default();
let mut buf = Vec::new();

// Add patterns from memory buffer
search.add_patterns_buffer(
    content,
    Path::new("<memory>"),
    None,
    &mut collection,
    true, // allow macros
);

// Initialize search outcome
let mut outcome = gix_attributes::search::Outcome::default();
outcome.initialize(&collection);

// Search for attributes for a .bin file
let path = "example.bin".as_bytes().as_bstr();
search.pattern_matching_relative_path(
    path,
    Case::Sensitive,
    None,
    &mut outcome,
);

// Iterate through matches to see expanded macro
for m in outcome.iter() {
    if m.kind.is_macro() {
        println!("Macro: {}", m.assignment.name.as_str());
    } else {
        println!(
            "Attribute: {} = {:?}",
            m.assignment.name.as_str(),
            m.assignment.state
        );
    }
}
```

## Implementation Details

### Attribute States

Attributes in Git can be in several states:

1. **Set**: The attribute is explicitly set (`attr`)
2. **Unset**: The attribute is explicitly unset (`-attr`)
3. **Value**: The attribute has a specific value (`attr=value`)
4. **Unspecified**: The attribute is not mentioned or explicitly marked as unspecified (`!attr`)

The `State` and `StateRef` enums in this crate represent these states.

### Attribute Macros

Git attributes support macros, which are attribute names that expand to multiple other attributes. For example:

```
[attr]binary -diff -merge -text
```

Defines a `binary` macro that, when used, applies three other attributes. This crate handles macro resolution through the `MetadataCollection` and tracks the expansion hierarchy to prevent circular references.

### Pattern Matching Order

When determining attributes for a path, multiple patterns may match. The precedence is determined by:

1. Pattern specificity (more specific patterns take precedence)
2. Pattern order in files (later patterns override earlier ones)
3. File precedence (repository attributes > global attributes)

The crate handles this precedence logic through the search system and outcome tracking.

### Performance Considerations

1. **Reference Types**: The crate uses reference types (`NameRef`, `StateRef`, `AssignmentRef`) to avoid unnecessary cloning of data.

2. **SmallVec**: Small vectors optimize for the common case of few attributes per pattern.

3. **KString**: Efficient string interning for attribute names reduces memory usage.

4. **Reusable Outcome**: The `Outcome` type can be reset and reused to avoid allocation costs when searching for multiple paths.

5. **Efficient Pattern Matching**: Leverages `gix-glob` for optimized pattern matching against file paths.

## Testing Strategy

The crate employs several testing approaches:

1. **Unit Tests**: Verify individual components like parsing, state handling, and search functionality.

2. **Baseline Tests**: Use fixtures to compare against expected baseline results.

3. **Integration Tests**: Ensure proper integration with other components of the gitoxide ecosystem.

4. **Memory Tests**: Verify memory efficiency and size constraints on key data structures.

Tests are structured to cover:
- Parsing of attribute files
- Pattern matching behavior
- Macro resolution
- Attribute precedence rules
- Handling of special cases (case sensitivity, path normalization)
- Compatibility with Git's attribute behavior