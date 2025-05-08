# gix-config

## Overview

The `gix-config` crate is a high-performance library for reading, parsing, and writing Git configuration files. It provides a complete implementation of the Git config format with support for all standard features, including section and subsection handling, value normalization, multiple value support, conditional includes, and more.

The crate offers multiple abstraction levels, from low-level parsing events to high-level APIs for convenient reading and manipulation of config values, while maintaining zero-copy parsing where possible for optimal performance.

## Architecture

The crate is structured around several key components:

1. **File Representation** - The core `File` struct serves as the main interface for interacting with Git config files, handling reading, writing, and manipulating config data.

2. **Value Parsing and Representation** - The parser and various value types (Boolean, Integer, Path, Color) handle the specific format rules of Git configuration values.

3. **Event-based Parser** - A low-level event parser that tokenizes the configuration file into a stream of events, allowing efficient traversal and manipulation.

4. **Section Management** - A system for tracking sections, subsections, and their values, maintaining order and comments for round-trip editing.

5. **Value Lookup and Access** - Optimized methods to access configuration values with proper precedence rules and filtering capabilities.

The design focuses on:
- Performance through zero-copy operations where possible
- Memory efficiency with shared references
- Round-trip parsing that preserves formatting and comments
- Flexible manipulation of configuration values

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `File` | Primary interface for Git config files | Reading, writing, and manipulating Git configuration |
| `KeyRef` | Representation of a config key with section, subsection and value name | Parsed from strings like "core.editor" or "remote.origin.url" |
| `Source` | Enum representing the origin of configuration values | Tracks precedence for overlapping values |
| `parse::Events` | Stream of parser events from config files | Low-level access to the raw config structure |
| `section::Name` | Represents a section name in the config | Used in lookup operations |
| `section::Subsection` | Represents a subsection name in the config | Used in lookup operations |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `AsKey` | Convert a string-like value to a parsed `KeyRef` | `String`, `&str`, `BString`, `&BStr`, `KeyRef` |

### Value Types

| Type | Description | Example Values |
|------|-------------|---------------|
| `Boolean` | Boolean value with Git semantics | true, false, yes, no, on, off |
| `Integer` | Integer with size suffixes | 1K, 5M, 2G |
| `Path` | File path with expansion | ~/file, ~user/file |
| `Color` | Git color specification | auto, red, bold red, #ff0000 |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-config-value` | Value type definitions and parsing |
| `gix-path` | Path handling and expansion |
| `gix-sec` | Security and trust model |
| `gix-ref` | Reference handling (for branch configuration) |
| `gix-glob` | Glob pattern matching (for conditional includes) |
| `gix-features` | Feature flags and utilities |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `winnow` | Parser combinator framework |
| `memchr` | Fast byte searching |
| `bstr` | Binary string handling |
| `smallvec` | Small vector optimization |
| `thiserror` | Error handling |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Adds serialization/deserialization support | `serde`, `bstr/serde`, `gix-sec/serde`, `gix-ref/serde`, `gix-glob/serde`, `gix-config-value/serde` |

## Configuration Sources

Git configuration values can come from multiple sources with a defined precedence order. The `gix-config` crate models this with the `Source` enum, which includes:

1. `GitInstallation` - Configuration shipped with Git
2. `System` - System-wide Git configuration 
3. `Git` - User's application-specific configuration
4. `User` - User's global Git configuration
5. `Local` - Repository-specific configuration
6. `Worktree` - Worktree-specific configuration
7. `Env` - Environment variables (`GIT_CONFIG_*`)
8. `Cli` - Command-line specified values
9. `Api` - Programmatically set values
10. `EnvOverride` - Environment variables that override specific config values

These sources represent the standard precedence order in Git, where later sources override earlier ones. The crate properly handles this precedence model.

## Implementation Details

### Zero-Copy Parsing

The crate implements a highly optimized parser that avoids memory allocations where possible:

- Values that don't need normalization (unescaping or quote removal) are returned as direct slices
- Section and key names are stored as references when possible
- The parser is designed to minimize allocations during the parse phase

### Multivar Support

Git allows keys to be specified multiple times in the same or different sections, known as "multivars." The crate handles these with:

- Methods to access single values (following Git's "last one wins" rule)
- Methods to access all values of a multivar
- Proper order preservation for writing

### Includes and Conditional Includes

The crate supports Git's include mechanisms:

- `include.path` directive for including other files
- `includeIf.<condition>.path` for conditional inclusion
- Proper metadata tracking to maintain the source of included values

### Section Headers

The crate properly handles both legacy and modern section header formats:

- Legacy format: `[section.subsection]`
- Modern format: `[section "subsection"]`

Both are supported for reading, with proper interpretation according to Git's rules.

## Examples

### Reading Configuration Values

```rust
use gix_config::File;
use std::convert::TryFrom;

// Parse a config string
let config = File::try_from("[core]\n\teditor = vim\n[user]\n\tname = John Doe").unwrap();

// Get a simple value
let editor = config.raw_value("core.editor").unwrap();
assert_eq!(editor.as_ref(), "vim");

// Parse as a specific type
let bool_value = config.boolean("some.boolean").unwrap_or_default();

// Get all values for a multivar key
let emails = config.raw_values("user.email");
```

### Writing Configuration

```rust
use gix_config::File;
use std::path::Path;

// Start with an empty config or read an existing one
let mut config = File::default();

// Set a simple value
config.set_raw_value("core.editor", "nvim").unwrap();

// Set a type-specific value
config.set_boolean("core.bare", true).unwrap();

// Remove a value
config.remove_value("core.editor").unwrap();

// Write to a file
config.write_to_path(Path::new(".git/config")).unwrap();
```

### Working with Sections

```rust
use gix_config::File;
use std::convert::TryFrom;

let mut config = File::default();

// Add a section with subsection
config.set_raw_value("remote.origin.url", "https://github.com/user/repo.git").unwrap();
config.set_raw_value("remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*").unwrap();

// Add another instance of the same section (for a different remote)
config.set_raw_value("remote.upstream.url", "https://github.com/upstream/repo.git").unwrap();

// Iterate over all remotes
for section in config.sections_with_name("remote") {
    if let Some(subsection) = section.subsection() {
        println!("Remote: {}", subsection);
        if let Some(url) = config.raw_value(&format!("remote.{}.url", subsection)) {
            println!("  URL: {}", url);
        }
    }
}
```

### Filtering Configuration by Source

```rust
use gix_config::{File, Source};

// Read configuration from various sources
let system_config = File::system().unwrap();
let user_config = File::user().unwrap();
let repo_config = File::local(".git/config").unwrap();

// Combine them with proper precedence
let mut combined = File::default();
combined.overlay(&system_config);
combined.overlay(&user_config);
combined.overlay(&repo_config);

// Only consider trusted sources for security-sensitive values
let credential_helper = combined.raw_value_filter(
    "credential.helper", 
    |meta| meta.source != Source::Cli && meta.source != Source::Env
);
```

## Testing Strategy

The crate employs several testing approaches:

1. **Unit Tests** - For individual components like parsers and value types
2. **Round-trip Tests** - Ensuring config can be read and written without information loss
3. **Compatibility Tests** - Using real-world Git config files to ensure compatibility
4. **Benchmarks** - Performance tests to ensure efficient parsing of large config files
5. **Fuzzing** - To ensure the parser is robust against malformed input

The crate includes a benchmark for parsing large config files, demonstrating its focus on performance.