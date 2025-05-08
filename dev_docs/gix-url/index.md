# gix-url

## Overview

The `gix-url` crate provides Git URL parsing, manipulation, and serialization functionality for the gitoxide ecosystem. It handles various Git URL schemes (such as `git://`, `ssh://`, `file://`, `http://`, and `https://`) with special attention to Git's URL format peculiarities and security considerations. The crate supports both standard URL formats and SCP-like syntax (`user@host:path/to/repo`), which is commonly used with Git.

## Architecture

The crate is designed around a central `Url` struct that represents a parsed Git URL with all its components. It follows these design principles:

1. **Security-focused**: Careful handling of URL components that could be used in command-line attacks
2. **Format compatibility**: Support for all Git URL formats, including SCP-like syntax
3. **Lossless parsing and serialization**: Preserving the original format when possible
4. **Path expansion**: Handling of home directory references (`~` and `~user` syntax)
5. **Extensibility**: Support for plug-in transport protocols via the `Ext` scheme variant

The architecture separates URL parsing from manipulation and serialization, with specialized modules for each concern. The crate also provides path expansion functionality, which is particularly important for local repository paths.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Url` | Core representation of a Git URL with all its components | Used to parse, manipulate, and serialize Git URLs |
| `expand_path::ForUser` | Specifies a user for path expansion | Used when expanding repository paths with home directory references |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `testing::TestUrlExtension` | Provides test-only functionality for URL creation | Implemented for `Url` |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `parse` | Parses a byte string as a Git URL | `fn parse(input: &BStr) -> Result<Url, parse::Error>` |
| `expand_path` | Expands paths with home directory references | `fn expand_path(user: Option<&expand_path::ForUser>, path: &BStr) -> Result<PathBuf, expand_path::Error>` |
| `expand_path::parse` | Parses user information from a path | `fn parse(path: &BStr) -> Result<(Option<ForUser>, BString), Error>` |
| `expand_path::with` | Expands paths with custom home directory resolution | `fn with(user: Option<&ForUser>, path: &BStr, home_for_user: impl FnOnce(&ForUser) -> Option<PathBuf>) -> Result<PathBuf, Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Scheme` | Represents the URL scheme/protocol | `File`, `Git`, `Ssh`, `Http`, `Https`, `Ext(String)` |
| `ArgumentSafety` | Classifies a URL component's safety for command-line usage | `Absent`, `Usable(&str)`, `Dangerous(&str)` |
| `parse::Error` | Represents errors during URL parsing | Various error types |
| `expand_path::Error` | Represents errors during path expansion | Various error types |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-features` | Feature flag support and utilities |
| `gix-path` | Path handling and conversion utilities |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `url` | Core URL parsing functionality |
| `bstr` | Binary string handling for non-UTF8 paths |
| `percent-encoding` | URL encoding/decoding |
| `thiserror` | Error type definitions |
| `serde` | Optional serialization/deserialization support |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization support | `serde`, `bstr/serde` |
| `document-features` | Generates feature documentation | `document-features` |

## Examples

```rust
use bstr::BString;
use gix_url::{parse, Scheme, Url};
use std::path::PathBuf;

// Parse a standard Git URL
let url_str = b"https://github.com/GitoxideLabs/gitoxide.git".as_slice();
let url = parse(url_str.as_ref()).expect("Valid URL");
assert_eq!(url.scheme, Scheme::Https);
assert_eq!(url.host(), Some("github.com"));
assert_eq!(url.path, "/GitoxideLabs/gitoxide.git");

// Parse an SCP-like syntax
let scp_url_str = b"git@github.com:GitoxideLabs/gitoxide.git".as_slice();
let scp_url = parse(scp_url_str.as_ref()).expect("Valid SCP URL");
assert_eq!(scp_url.scheme, Scheme::Ssh);
assert_eq!(scp_url.user(), Some("git"));
assert_eq!(scp_url.host(), Some("github.com"));
assert_eq!(scp_url.path, "GitoxideLabs/gitoxide.git");

// Local file URL
let file_url_str = b"file:///path/to/repo.git".as_slice();
let file_url = parse(file_url_str.as_ref()).expect("Valid file URL");
assert_eq!(file_url.scheme, Scheme::File);
assert_eq!(file_url.path, "/path/to/repo.git");

// Path with home directory reference
let home_path = b"~/repos/gitoxide".as_slice();
if let Ok((Some(user), adjusted_path)) = gix_url::expand_path::parse(home_path.as_ref()) {
    let expanded = gix_url::expand_path(Some(&user), &adjusted_path).expect("Valid path");
    println!("Expanded path: {:?}", expanded);
}

// Modifying a URL
let mut url = parse(b"https://example.com/repo.git".as_ref()).unwrap();
url.set_user(Some("username".to_string()));
url.set_password(Some("password".to_string()));
assert_eq!(
    url.to_bstring().to_str().unwrap(),
    "https://username:password@example.com/repo.git"
);

// Safe command-line usage
let url = parse(b"ssh://user@host.com/path/to/repo".as_ref()).unwrap();
if let Some(safe_host) = url.host_argument_safe() {
    println!("Safe to use host in command: {}", safe_host);
}
```

## Implementation Details

### URL Parsing Strategy

The crate uses a multi-step parsing process:

1. First, it determines the URL format based on patterns like `://` for standard URLs or a colon `:` without slashes for SCP-like syntax
2. For standard URLs, it leverages the `url` crate for core parsing, then extracts Git-specific components
3. For SCP-like syntax, it splits at the first colon and performs custom parsing for Git's specific format
4. For local paths, it handles special cases like `~` expansion and Windows drive letters

The parsing is designed to handle Git's various URL formats correctly, including edge cases like:
- SSH URLs with the format `user@host:path/to/repo`
- Local file paths with Windows drive letters
- URLs with or without protocol specification
- Handling of IPv6 addresses in square brackets

### Security Measures

The crate includes several security measures to prevent command-line injection attacks:

1. **Argument safety checks**: Methods like `host_argument_safe()`, `user_argument_safe()`, and `path_argument_safe()` verify that URL components don't start with dashes which could be interpreted as command-line options
2. **Password redaction**: The standard display implementation redacts passwords to prevent accidental exposure
3. **Safe percent encoding/decoding**: Ensures that malicious input can't break out of URL encoding
4. **URL length limitations**: Prevents DoS attacks with overly long URLs

### URL Serialization

The crate supports both standard URL serialization and alternative forms (like SCP-like syntax for SSH URLs). The serialization preserves the original format when possible, but can also be controlled explicitly:

```rust
// Control serialization format
let url = parse(b"ssh://git@github.com/user/repo.git".as_ref()).unwrap()
    .serialize_alternate_form(true);
assert_eq!(url.to_bstring().to_str().unwrap(), "git@github.com:user/repo.git");
```

## Testing Strategy

The crate employs several testing approaches:

1. **Unit tests**: Individual components are tested for correct behavior
2. **Parsing tests**: Various URL formats are tested to ensure correct parsing
3. **Fuzz testing**: The `fuzz` directory contains targets for fuzzing URL parsing to find edge cases
4. **Baseline tests**: Tests against known-good parsing results to catch regressions
5. **Interoperability tests**: Tests integration with other components in the gitoxide ecosystem
6. **Security tests**: Verifies that security measures like argument safety checks work correctly

The tests include specific fixtures for:
- Special characters in URLs
- Very long URLs
- Illegal UTF-8 sequences
- Various protocol types
- SCP-like syntax
- Home directory references