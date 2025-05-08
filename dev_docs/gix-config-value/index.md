# gix-config-value

## Overview

The `gix-config-value` crate provides specialized parsers and data types for handling Git configuration values. It focuses on parsing and representing the various value types used in Git configuration files, such as booleans, integers with size suffixes, file paths, and colors.

This crate is designed to be used in conjunction with `gix-config` or any other implementation that needs to handle Git configuration values outside of a config file context, such as from environment variables or command-line arguments.

## Architecture

The crate is structured around a set of specialized value types that encapsulate Git's specific parsing rules and semantics:

1. **Boolean Values** - Handles Git's various boolean representations (`true`, `false`, `yes`, `no`, `on`, `off`, and numeric values)
2. **Integer Values** - Supports integers with size suffixes (`k`, `m`, `g`) for representing sizes
3. **Path Values** - Handles path expansions like `~/` for home directory and `~user/` for specific user directories
4. **Color Values** - Parses Git's complex color syntax including foreground, background, attributes, and RGB values

Each type provides parsing from string representations, consistent error handling, and useful methods for working with the parsed values.

The architecture emphasizes:
- Zero-copy parsing where possible
- Type safety
- Platform-aware path handling
- Comprehensive error handling
- Proper serialization (via optional `serde` support)

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Boolean` | Represents Git boolean values | Parsing and manipulating boolean config values |
| `Integer` | Represents Git integer values with optional suffixes | Handling size and numeric config values |
| `Path` | Represents file system paths with interpolation support | Working with path-based config values |
| `Color` | Represents Git color specifications | Parsing and manipulating color config values |
| `Error` | Error type for value parsing failures | Consistent error handling across all value types |

### Enums and Flags

| Type | Description | Variants/Flags |
|------|-------------|----------------|
| `integer::Suffix` | Size suffixes for integers | `Kibi`, `Mebi`, `Gibi` |
| `color::Name` | Color names and RGB values | Named colors, ANSI codes, RGB values |
| `color::Attribute` | Color text attributes | `BOLD`, `ITALIC`, `REVERSE`, etc. |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-path` | Path handling and conversion |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Binary string handling |
| `thiserror` | Error handling |
| `bitflags` | Flag management for color attributes |
| `libc` | User directory lookup (on Unix platforms) |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Adds serialization/deserialization support | `serde`, `bstr/serde` |

## Value Types in Detail

### Boolean Values

Git supports multiple representations for boolean values:

- Positive: `true`, `yes`, `on`, and any non-zero number
- Negative: `false`, `no`, `off`, empty string, and zero

The `Boolean` type encapsulates this behavior, ensuring consistent parsing across the codebase.

### Integer Values with Suffixes

Git allows integers to have size suffixes to represent large values concisely:

- `k` or `K`: Kibi (× 1024)
- `m` or `M`: Mebi (× 1,048,576)
- `g` or `G`: Gibi (× 1,073,741,824)

The `Integer` type handles these suffixes and provides methods to get both the raw and expanded values.

### Path Values with Expansion

Git supports various path expansions in configuration values:

- `~/`: Expands to the user's home directory
- `~user/`: Expands to the specified user's home directory
- `%(prefix)/`: Expands to Git's installation directory

The `Path` type supports these expansions through its `interpolate()` method, which handles platform-specific differences.

### Color Values

Git has a rich color specification syntax for its UI:

- Named colors: `red`, `blue`, `green`, etc.
- Bright variants: `brightred`, `brightblue`, etc.
- RGB values: `#ff0000` (for red)
- ANSI color codes: Direct numeric values
- Attributes: `bold`, `dim`, `italic`, `ul`, `blink`, `reverse`, `strike`
- Negated attributes: `nobold`, `nodim`, etc.

The `Color` type parses these specifications and represents them in a structured form with foreground, background, and attributes.

## Implementation Details

### Zero-Copy Design

The crate is designed to minimize allocations:

- Values that don't need transformation are stored as references
- `Cow` (Clone-on-Write) is used extensively for efficient handling of both owned and borrowed data
- Parse functions return references to input data when possible

### Error Handling

A consistent error handling approach is used across all value types:

- All parsing functions return a `Result<T, Error>`
- The `Error` type provides context about what went wrong, including the original input
- UTF-8 conversion errors are properly propagated when relevant

### Platform Considerations

Path handling takes into account platform differences:

- Home directory expansion works differently on different operating systems
- User home directory lookup is implemented for Unix-like systems
- Windows and Android have special handling for unsupported features

## Examples

### Working with Boolean Values

```rust
use gix_config_value::Boolean;
use std::convert::TryFrom;
use bstr::ByteSlice;

// Parse various boolean representations
let true_value = Boolean::try_from("yes".as_bytes().as_bstr()).unwrap();
let false_value = Boolean::try_from("off".as_bytes().as_bstr()).unwrap();
let numeric_bool = Boolean::try_from("1".as_bytes().as_bstr()).unwrap();

assert!(true_value.is_true());
assert!(!false_value.is_true());
assert!(numeric_bool.is_true());

// Convert to native bool
let native: bool = true_value.into();
assert!(native);
```

### Working with Integer Values

```rust
use gix_config_value::Integer;
use std::convert::TryFrom;
use bstr::ByteSlice;

// Parse simple integer
let simple = Integer::try_from("42".as_bytes().as_bstr()).unwrap();
assert_eq!(simple.value, 42);
assert_eq!(simple.suffix, None);

// Parse integer with suffix
let with_suffix = Integer::try_from("5k".as_bytes().as_bstr()).unwrap();
assert_eq!(with_suffix.value, 5);
assert_eq!(with_suffix.suffix, Some(gix_config_value::integer::Suffix::Kibi));

// Get decimal value with suffix applied
let large = Integer::try_from("2g".as_bytes().as_bstr()).unwrap();
assert_eq!(large.to_decimal(), Some(2 * 1024 * 1024 * 1024));
```

### Working with Path Values

```rust
use gix_config_value::Path;
use bstr::ByteSlice;
use std::path::PathBuf;

// Create a path value
let path = Path::from(("~/projects/git".as_bytes().as_bstr()).into());

// Interpolate with context
let home_dir = PathBuf::from("/home/user");
let interpolated = path.interpolate(gix_config_value::path::interpolate::Context {
    git_install_dir: None,
    home_dir: Some(&home_dir),
    home_for_user: None,
}).unwrap();

assert_eq!(interpolated.to_string_lossy(), "/home/user/projects/git");
```

### Working with Color Values

```rust
use gix_config_value::Color;
use std::convert::TryFrom;
use bstr::ByteSlice;

// Parse a simple color
let simple = Color::try_from("red".as_bytes().as_bstr()).unwrap();
assert_eq!(simple.foreground, Some(gix_config_value::color::Name::Red));
assert!(simple.background.is_none());
assert!(simple.attributes.is_empty());

// Parse a complex color with attributes
let complex = Color::try_from("bold blue".as_bytes().as_bstr()).unwrap();
assert_eq!(complex.foreground, Some(gix_config_value::color::Name::Blue));
assert!(complex.attributes.contains(gix_config_value::color::Attribute::BOLD));

// Parse color with background
let bg = Color::try_from("red green".as_bytes().as_bstr()).unwrap();
assert_eq!(bg.foreground, Some(gix_config_value::color::Name::Red));
assert_eq!(bg.background, Some(gix_config_value::color::Name::Green));
```

## Testing Strategy

The crate is tested through:

1. **Unit tests** - Testing individual value parsers with various inputs
2. **Edge case tests** - Testing unusual or boundary cases to ensure robust parsing
3. **Integration with gix-config** - Ensuring value parsing works correctly in the context of config files
4. **Fuzzing** - To protect against panics with malformed inputs

The tests focus particularly on ensuring compatible behavior with Git's own parsing rules, using Git's behavior as a reference.