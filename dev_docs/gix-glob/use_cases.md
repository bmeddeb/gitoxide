# gix-glob Use Cases

This document describes the primary use cases for the gix-glob crate, who its intended audience is, what problems it solves, and how it solves them.

## Intended Audience

The gix-glob crate is primarily intended for:

1. **Git Implementation Developers**: Developers building Git clients, servers, or tools that need to match paths using Git's globbing rules
2. **Gitoxide Component Developers**: Internal users developing other components in the gitoxide ecosystem that need path matching capabilities
3. **Version Control System Developers**: Developers of version control systems that want to implement Git-compatible pattern matching
4. **Build Tool Developers**: Developers of build systems or file processing tools that want to use Git-style pattern matching for file inclusion/exclusion

## Core Use Cases

### 1. Implementing `.gitignore` Functionality

#### Problem

Git's `.gitignore` files use a specific globbing syntax to determine which files should be excluded from version control. Implementing this functionality requires parsing and matching patterns according to Git's rules, which include:

- Patterns with leading slashes match only at the repository root
- Patterns with trailing slashes match only directories
- Patterns without slashes match at any directory level
- Patterns can be negated with a leading exclamation mark
- Pattern matching must respect globbing wildcards (`*`, `?`, `[...]`)

#### Solution

The gix-glob crate provides the exact pattern matching behavior needed for implementing `.gitignore` functionality:

```rust
use gix_glob::{parse, Pattern};
use gix_glob::pattern::Case;
use gix_glob::wildmatch::Mode;
use bstr::{BStr, ByteSlice};

fn should_ignore_file(path: &str, is_dir: bool) -> bool {
    // In a real implementation, these patterns would come from .gitignore files
    let patterns = vec![
        parse("*.log").unwrap(),           // Ignore all .log files
        parse("build/").unwrap(),          // Ignore the build directory
        parse("/node_modules/").unwrap(),  // Ignore node_modules at the root
        parse("!important.log").unwrap(),  // Don't ignore important.log
    ];
    
    let path_bytes = path.as_bytes().as_bstr();
    let basename_pos = path.rfind('/').map(|p| p + 1);
    
    // Check each pattern in reverse order (like Git does)
    for pattern in patterns.iter().rev() {
        if pattern.matches_repo_relative_path(
            path_bytes, 
            basename_pos,
            Some(is_dir),
            Case::Sensitive,
            Mode::NO_MATCH_SLASH_LITERAL
        ) {
            // If pattern is negative, don't ignore the file
            return !pattern.is_negative();
        }
    }
    
    // Not matched by any pattern
    false
}

// Usage examples
assert!(should_ignore_file("debug.log", false));
assert!(should_ignore_file("build/output", true));
assert!(!should_ignore_file("important.log", false));
assert!(!should_ignore_file("src/main.rs", false));
```

### 2. Implementing `.gitattributes` Functionality

#### Problem

Git's `.gitattributes` files use the same pattern syntax as `.gitignore` files but associate attributes with matched files. This requires not just matching patterns but also associating values with them.

#### Solution

The gix-glob crate's search module is designed specifically for this use case, allowing patterns to be associated with values:

```rust
use std::path::{Path, PathBuf};
use gix_glob::search::{Pattern as PatternTrait, pattern::{List, Mapping}};
use gix_glob::Pattern;
use bstr::{BStr, BString, ByteSlice};

// Define an attribute pattern that associates attributes with files
#[derive(Clone, PartialEq, Eq, Debug, Hash, Ord, PartialOrd, Default)]
struct AttributePattern;

// The value associated with each pattern
#[derive(Clone, PartialEq, Eq, Debug, Hash, Ord, PartialOrd)]
struct Attribute {
    name: String,
    value: Option<String>, // None for unset, Some("") for set without value
}

impl PatternTrait for AttributePattern {
    type Value = Vec<Attribute>;
    
    fn bytes_to_patterns(bytes: &[u8], source: &Path) -> Vec<Mapping<Self::Value>> {
        let mut result = Vec::new();
        
        // Parse each line from the attributes file
        for (i, line) in bytes.lines().enumerate() {
            let line = line.trim();
            if line.is_empty() || line.starts_with(b"#") {
                continue;
            }
            
            // Split into pattern and attributes
            let parts: Vec<&[u8]> = line.splitn(2, |&b| b == b' ' || b == b'\t')
                                        .collect();
            if parts.len() != 2 {
                continue;
            }
            
            // Parse the pattern
            let pattern_text = parts[0];
            if let Some(pattern) = Pattern::from_bytes(pattern_text) {
                // Parse attributes
                let attrs_text = parts[1];
                let attributes = parse_attributes(attrs_text);
                
                result.push(Mapping {
                    pattern,
                    value: attributes,
                    sequence_number: i,
                });
            }
        }
        
        result
    }
}

// Helper to parse attributes
fn parse_attributes(attrs_text: &[u8]) -> Vec<Attribute> {
    // In a real implementation, this would parse the attribute specifications
    vec![]
}

// Function to get attributes for a file
fn get_attributes(
    path: &str, 
    is_dir: bool, 
    attributes_lists: &[List<AttributePattern>]
) -> Vec<Attribute> {
    let path_bytes = path.as_bytes().as_bstr();
    let basename_pos = path.rfind('/').map(|p| p + 1);
    
    let mut result = Vec::new();
    
    // Check each list of patterns
    for list in attributes_lists {
        // Skip if path doesn't match the base directory
        if let Some((relative_path, adjusted_basename_pos)) = list.strip_base_handle_recompute_basename_pos(
            path_bytes,
            basename_pos,
            gix_glob::pattern::Case::Sensitive,
        ) {
            // Check each pattern in the list
            for mapping in &list.patterns {
                if mapping.pattern.matches_repo_relative_path(
                    relative_path,
                    adjusted_basename_pos,
                    Some(is_dir),
                    gix_glob::pattern::Case::Sensitive,
                    gix_glob::wildmatch::Mode::NO_MATCH_SLASH_LITERAL,
                ) {
                    // Found matching attributes
                    result.extend(mapping.value.clone());
                }
            }
        }
    }
    
    result
}
```

### 3. Implementing Path Filtering for CLI Commands

#### Problem

Git commands often accept pathspec arguments to filter which files the command should apply to. These pathspecs support glob patterns and need to be efficiently matched against repository files.

#### Solution

The gix-glob crate provides the core matching functionality needed for Git pathspec handling:

```rust
use gix_glob::{parse, Pattern};
use gix_glob::wildmatch::Mode;
use bstr::ByteSlice;
use std::path::Path;

// Command-line pathspecs
let pathspecs = vec![
    "src/*.rs",   // All Rust files in src
    "*.md",       // All Markdown files
    "!README.md", // But not README.md
];

// Parse pathspecs into patterns
let patterns: Vec<Pattern> = pathspecs
    .iter()
    .filter_map(|spec| parse(spec))
    .collect();

// Filter a list of file paths
fn filter_paths<'a>(
    patterns: &[Pattern],
    paths: &'a [&str]
) -> Vec<&'a str> {
    paths.iter()
        .filter(|&&path| {
            // By default, any matching pattern includes the path
            let mut include = patterns.is_empty();
            
            let path_bytes = path.as_bytes().as_bstr();
            for pattern in patterns {
                if pattern.matches(
                    path_bytes,
                    Mode::NO_MATCH_SLASH_LITERAL,
                ) {
                    // If the pattern is negative, it excludes the path
                    include = !pattern.is_negative();
                }
            }
            
            include
        })
        .copied()
        .collect()
}

// Example usage
let files = vec![
    "src/main.rs",
    "src/lib.rs",
    "README.md",
    "CONTRIBUTING.md",
    "doc/guide.txt"
];

let filtered = filter_paths(&patterns, &files);
assert_eq!(filtered, vec!["src/main.rs", "src/lib.rs", "CONTRIBUTING.md"]);
```

### 4. Fast File Tree Traversal with Pattern Exclusion

#### Problem

When traversing large file trees, it's often necessary to skip certain directories or files for performance reasons. Git's globbing patterns provide a familiar and powerful way to specify exclusions.

#### Solution

The gix-glob crate can be used to efficiently skip directories during traversal:

```rust
use gix_glob::{parse, Pattern};
use gix_glob::pattern::Case;
use gix_glob::wildmatch::Mode;
use bstr::ByteSlice;
use std::path::{Path, PathBuf};
use std::fs;

// Patterns to exclude from traversal
let exclude_patterns = vec![
    parse("node_modules/").unwrap(),
    parse("target/").unwrap(),
    parse(".git/").unwrap(),
    parse("*.log").unwrap(),
];

// Traverse a directory, respecting exclusions
fn traverse_directory(
    dir: &Path,
    exclude_patterns: &[Pattern],
    callback: &mut dyn FnMut(&Path)
) -> std::io::Result<()> {
    if !dir.is_dir() {
        return Ok(());
    }
    
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        
        // Check if this path should be excluded
        let path_str = path.to_string_lossy();
        let is_dir = path.is_dir();
        let should_exclude = exclude_patterns.iter().any(|pattern| {
            // If this is a directory and the pattern requires a directory, check for a match
            if is_dir || !pattern.mode.contains(gix_glob::pattern::Mode::MUST_BE_DIR) {
                let path_bytes = path_str.as_bytes().as_bstr();
                let basename_pos = path_str.rfind('/').map(|p| p + 1);
                
                pattern.matches_repo_relative_path(
                    path_bytes,
                    basename_pos,
                    Some(is_dir),
                    Case::Sensitive,
                    Mode::NO_MATCH_SLASH_LITERAL,
                )
            } else {
                false
            }
        });
        
        if !should_exclude {
            callback(&path);
            
            if is_dir {
                traverse_directory(&path, exclude_patterns, callback)?;
            }
        }
    }
    
    Ok(())
}

// Example usage
let mut files = Vec::new();
traverse_directory(
    Path::new("/path/to/repo"),
    &exclude_patterns,
    &mut |path| {
        if path.is_file() {
            files.push(path.to_path_buf());
        }
    }
).unwrap();
```

### 5. Implementing Sparse Checkout Patterns

#### Problem

Git's sparse checkout feature allows users to check out only parts of a repository by specifying patterns of files to include. This requires pattern matching against paths to determine which files should be present in the working directory.

#### Solution

The gix-glob crate can implement this pattern matching efficiently:

```rust
use gix_glob::{parse, Pattern};
use gix_glob::pattern::Case;
use gix_glob::wildmatch::Mode;
use bstr::ByteSlice;

// Sparse checkout patterns (in a real implementation, these would be read from .git/info/sparse-checkout)
let sparse_patterns = vec![
    parse("README.md").unwrap(),    // Include README.md
    parse("src/").unwrap(),         // Include everything in src/
    parse("!src/tests/").unwrap(),  // But not tests
];

// Check if a file should be checked out
fn should_checkout_file(path: &str, is_dir: bool) -> bool {
    // If there are no patterns, include everything
    if sparse_patterns.is_empty() {
        return true;
    }
    
    let path_bytes = path.as_bytes().as_bstr();
    let basename_pos = path.rfind('/').map(|p| p + 1);
    
    // Check each pattern in order
    let mut include = false;
    
    for pattern in &sparse_patterns {
        if pattern.matches_repo_relative_path(
            path_bytes,
            basename_pos,
            Some(is_dir),
            Case::Sensitive,
            Mode::NO_MATCH_SLASH_LITERAL,
        ) {
            include = !pattern.is_negative();
        }
    }
    
    include
}

// Example usage
assert!(should_checkout_file("README.md", false));
assert!(should_checkout_file("src/main.rs", false));
assert!(!should_checkout_file("src/tests/test_utils.rs", false));
assert!(!should_checkout_file("docs/guide.md", false));
```

## Integration with Other Components

The gix-glob crate is integrated with several other components in the gitoxide ecosystem:

### Integration with gix-ignore

```rust
use gix_glob::{Pattern, parse};
use gix_glob::search::{Pattern as PatternTrait, pattern::List};

// Define an ignore pattern that implements the search::Pattern trait
struct IgnorePattern;

impl PatternTrait for IgnorePattern {
    // Ignore patterns don't have associated values
    type Value = ();
    
    fn bytes_to_patterns(bytes: &[u8], source: &std::path::Path) -> Vec<gix_glob::search::pattern::Mapping<()>> {
        // Parse gitignore format lines
        let mut patterns = Vec::new();
        
        for (i, line) in bytes.lines().enumerate() {
            let line = line.trim();
            if line.is_empty() || line.starts_with(b"#") {
                continue;
            }
            
            if let Some(pattern) = Pattern::from_bytes(line) {
                patterns.push(gix_glob::search::pattern::Mapping {
                    pattern,
                    value: (),
                    sequence_number: i,
                });
            }
        }
        
        patterns
    }
}

// In gix-ignore, this is used to build the ignore pattern lists
fn load_ignore_patterns(repo_path: &std::path::Path) -> Vec<List<IgnorePattern>> {
    let mut result = Vec::new();
    let mut buf = Vec::new();
    
    // Global ignores
    if let Ok(Some(global_ignore)) = List::<IgnorePattern>::from_file(
        home_dir().unwrap().join(".gitignore"),
        None,
        true,
        &mut buf,
    ) {
        result.push(global_ignore);
    }
    
    // Repository .gitignore
    if let Ok(Some(repo_ignore)) = List::<IgnorePattern>::from_file(
        repo_path.join(".gitignore"),
        Some(repo_path),
        true,
        &mut buf,
    ) {
        result.push(repo_ignore);
    }
    
    // Directory-specific .gitignore files would be added here
    
    result
}

// Example helper function (in a real implementation, home_dir would be properly implemented)
fn home_dir() -> Option<std::path::PathBuf> {
    Some(std::path::PathBuf::from("/home/user"))
}
```

### Integration with gix-attributes

```rust
use gix_glob::Pattern;
use gix_glob::search::{Pattern as PatternTrait, pattern::List};
use std::path::Path;

// Define an attribute pattern type
struct AttributePattern;

impl PatternTrait for AttributePattern {
    type Value = Vec<(String, Option<String>)>;
    
    fn bytes_to_patterns(bytes: &[u8], source: &Path) -> Vec<gix_glob::search::pattern::Mapping<Self::Value>> {
        // Parse gitattributes format lines
        // This is simplified; real implementation would be more complex
        let mut patterns = Vec::new();
        
        for (i, line) in bytes.lines().enumerate() {
            let line = line.trim();
            if line.is_empty() || line.starts_with(b"#") {
                continue;
            }
            
            let parts: Vec<&[u8]> = line.splitn(2, |&b| b == b' ' || b == b'\t')
                                        .collect();
            if parts.len() != 2 {
                continue;
            }
            
            if let Some(pattern) = Pattern::from_bytes(parts[0]) {
                let attrs = parts[1].split(|&b| b == b' ' || b == b'\t')
                                  .filter(|p| !p.is_empty())
                                  .map(parse_attribute)
                                  .collect();
                
                patterns.push(gix_glob::search::pattern::Mapping {
                    pattern,
                    value: attrs,
                    sequence_number: i,
                });
            }
        }
        
        patterns
    }
}

// Helper to parse a single attribute
fn parse_attribute(attr: &[u8]) -> (String, Option<String>) {
    let attr_str = String::from_utf8_lossy(attr);
    
    if let Some(pos) = attr_str.find('=') {
        let name = attr_str[..pos].to_string();
        let value = attr_str[pos+1..].to_string();
        (name, Some(value))
    } else if attr_str.starts_with('-') {
        (attr_str[1..].to_string(), None)
    } else {
        (attr_str.to_string(), Some(String::new()))
    }
}

// In gix-attributes, this would load the attribute patterns
fn load_attribute_patterns(repo_path: &Path) -> Vec<List<AttributePattern>> {
    let mut result = Vec::new();
    let mut buf = Vec::new();
    
    // Repository .gitattributes
    if let Ok(Some(repo_attrs)) = List::<AttributePattern>::from_file(
        repo_path.join(".gitattributes"),
        Some(repo_path),
        true,
        &mut buf,
    ) {
        result.push(repo_attrs);
    }
    
    result
}
```

## Conclusion

The gix-glob crate provides a critical foundation for many Git operations that involve pattern matching against file paths. Its implementation is carefully designed to match Git's own pattern matching behavior while providing a flexible and efficient API for various use cases.

The key strengths of the crate include:

1. **Git Compatibility**: Accurately implements Git's pattern matching behavior
2. **Performance**: Includes optimizations for common pattern types
3. **Flexibility**: Supports different matching modes and pattern sources
4. **Integration**: Designed to work seamlessly with other gitoxide components

By providing these capabilities, gix-glob enables the implementation of many Git features that rely on pattern matching, from ignore rules to attributes, pathspecs, and more.