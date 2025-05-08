# gix-validate

## Overview

`gix-validate` is a foundational crate in the gitoxide ecosystem that provides validation functionality for various git-related entities. It ensures that names, paths, references, and other git components adhere to Git's strict naming rules and safety constraints, protecting against malformed inputs that could lead to security issues or undefined behavior.

The crate serves as a core building block for safely handling user input and internal representations, ensuring that all parts of the gitoxide system operate with valid and safe data structures.

## Architecture

`gix-validate` follows a modular design with distinct validation components for different git entities:

### Core Design Principles

1. **Safety First** - Provides validators that strictly follow Git's rules to prevent security vulnerabilities and ensure compatibility with the Git ecosystem.

2. **Zero External Dependencies** - As a level 0 crate, it depends only on minimal external crates like `bstr` and `thiserror`, keeping it lightweight and maintainable.

3. **Platform-Aware Validation** - Considers platform-specific issues like NTFS/HFS+ filesystem quirks that could lead to security vulnerabilities.

4. **Sanitization Options** - Many validators offer both strict validation (returning errors) and sanitization (correcting problematic inputs) modes.

### Module Structure

The crate is organized into focused modules, each handling validation for a specific kind of git entity:

- **reference.rs** - Validates git reference names (like `refs/heads/main`, `HEAD`, etc.)
- **tag.rs** - Validates git tag names
- **submodule.rs** - Validates submodule names
- **path.rs** - Validates git path components with platform-aware safety checks

Each module typically provides:
1. An error type that describes all the ways validation can fail
2. Validator functions that return either the original input (if valid) or an error
3. Optional sanitizer functions that attempt to make invalid inputs valid

## Core Components

### Reference Validation

```rust
pub fn name(path: &BStr) -> Result<&BStr, name::Error>
```

Validates complete reference names like `refs/heads/main` or `HEAD`, ensuring they follow Git's strict naming rules, including:

- No leading or trailing slashes
- No `.lock` suffix
- No consecutive dots (`..`)
- Standalone references must be uppercase (`HEAD`, not `head`)

```rust
pub fn name_partial(path: &BStr) -> Result<&BStr, name::Error>
```

Validates partial reference names, allowing looser rules for things like:
- Lowercase names without slashes (useful for user input and command-line arguments)

```rust
pub fn name_partial_or_sanitize(path: &BStr) -> BString
```

A sanitizing version that converts invalid references into valid ones by:
- Replacing problematic characters with dashes
- Fixing path issues
- Ensuring empty paths become valid references 

### Tag Validation

```rust
pub fn name(input: &BStr) -> Result<&BStr, name::Error>
```

Validates git tag names, ensuring they:
- Contain no control characters or special characters (`\`, `^`, `:`, etc.)
- Don't start with a dot (`.`)
- Don't contain consecutive dots (`..`)
- Don't contain other git-specific patterns that would cause issues

### Submodule Validation

```rust
pub fn name(name: &BStr) -> Result<&BStr, name::Error>
```

Validates submodule names, checking for:
- Non-empty names
- No parent directory components (`..`)

### Path Component Validation

```rust
pub fn component(
    input: &BStr,
    mode: Option<component::Mode>,
    options: component::Options,
) -> Result<&BStr, component::Error>
```

Provides extensive validation for path components in git repositories, with:
- Platform-aware checks (Windows, MacOS HFS+, NTFS)
- Detection of special git paths like `.git`
- Prevention of path traversal attacks
- Protection against filesystem quirks that could lead to security issues

```rust
pub fn component_is_windows_device(input: &BStr) -> bool
```

Detects Windows device names like `CON`, `LPT1`, etc., which could cause security issues if used as filenames.

### Validation Options

The path component validation provides configurable options:

```rust
pub struct Options {
    pub protect_windows: bool,
    pub protect_hfs: bool,
    pub protect_ntfs: bool,
}
```

These options allow fine-tuning validation based on the target platform and security requirements.

## Dependencies

`gix-validate` has minimal external dependencies:

- **bstr** - For handling byte strings in a safe and efficient manner
- **thiserror** - For ergonomic error handling

As a level 0 crate, it doesn't depend on any other gitoxide crates, keeping it at the foundation of the dependency tree.

## Feature Flags

`gix-validate` doesn't define any feature flags of its own, maintaining simplicity and focusing on its core validation functionality.

## Examples

### Validating Reference Names

```rust
use bstr::ByteSlice;
use gix_validate::reference;

// Validate a complete reference name
let ref_name = b"refs/heads/main".as_bstr();
match reference::name(ref_name) {
    Ok(valid_name) => println!("Valid reference: {}", valid_name),
    Err(err) => println!("Invalid reference: {}", err),
}

// Validate a partial reference name (allows lowercase standalone names)
let partial_ref = b"feature-branch".as_bstr();
match reference::name_partial(partial_ref) {
    Ok(valid_name) => println!("Valid partial reference: {}", valid_name),
    Err(err) => println!("Invalid partial reference: {}", err),
}

// Sanitize an invalid reference name
let invalid_ref = b"refs/heads/feature branch".as_bstr();
let sanitized = reference::name_partial_or_sanitize(invalid_ref);
println!("Sanitized reference: {}", sanitized); // "refs/heads/feature-branch"
```

### Validating Path Components

```rust
use bstr::ByteSlice;
use gix_validate::path::{self, component};

// Default options (maximum safety)
let options = component::Options::default();

// Validate a path component
let path_component = b"normal-filename.txt".as_bstr();
match path::component(path_component, None, options) {
    Ok(valid_path) => println!("Valid path component: {}", valid_path),
    Err(err) => println!("Invalid path component: {}", err),
}

// Check for potentially dangerous Windows device names
let device_name = b"CON".as_bstr();
if path::component_is_windows_device(device_name) {
    println!("Warning: {} is a Windows device name", device_name);
}

// Validate a symlink path
use component::Mode;
let symlink_path = b".gitmodules".as_bstr();
match path::component(symlink_path, Some(Mode::Symlink), options) {
    Ok(_) => println!("Valid symlink path"),
    Err(err) => println!("Invalid symlink path: {}", err),
}
```

### Validating Tag Names

```rust
use bstr::ByteSlice;
use gix_validate::tag;

// Validate a tag name
let tag_name = b"v1.0.0".as_bstr();
match tag::name(tag_name) {
    Ok(valid_name) => println!("Valid tag name: {}", valid_name),
    Err(err) => println!("Invalid tag name: {}", err),
}

// Invalid tag names
let invalid_tags = [
    b"v1.0.0/".as_bstr(), // Ends with slash
    b".v1.0.0".as_bstr(), // Starts with dot
    b"v1..0".as_bstr(),   // Contains consecutive dots
];

for tag in invalid_tags {
    match tag::name(tag) {
        Ok(_) => println!("Unexpectedly valid: {}", tag),
        Err(err) => println!("Invalid as expected: {} - {}", tag, err),
    }
}
```

### Validating Submodule Names

```rust
use bstr::ByteSlice;
use gix_validate::submodule;

// Valid submodule name
let valid_name = b"external/lib".as_bstr();
assert!(submodule::name(valid_name).is_ok());

// Invalid: contains parent directory component
let invalid_name = b"external/../lib".as_bstr();
match submodule::name(invalid_name) {
    Ok(_) => println!("Unexpectedly valid"),
    Err(err) => println!("Invalid as expected: {}", err),
}
```

## Implementation Details

### Platform-Specific Protections

The path validation includes sophisticated protections against filesystem quirks:

#### HFS+ (macOS) Protection

The validation accounts for HFS+ case-insensitivity and Unicode normalization quirks, including:
- Special handling for `.git` and other reserved names that might be bypassed with Unicode tricks
- Filtering out specific code points that HFS+ ignores during filename comparison

```rust
fn is_dot_hfs(input: &BStr, search_case_insensitive: &str) -> bool {
    // Filters out Unicode control characters that HFS+ ignores
    // when comparing filenames, then checks for potentially dangerous patterns
    // ...
}
```

#### NTFS (Windows) Protection

The validation handles NTFS-specific filename features that could lead to security issues:
- 8.3 filename aliasing (where `longfi~1` can reference `longfilename.txt`)
- Alternate data streams
- Reserved device names like `CON`, `PRN`, etc.
- Trailing dots and spaces, which Windows silently removes

```rust
fn is_dot_ntfs(input: &BStr, search_case_insensitive: &str, ntfs_shortname_prefix: &str) -> bool {
    // Checks for NTFS-specific patterns that could be used to bypass security checks
    // ...
}
```

### Validation versus Sanitization

The crate distinguishes between two modes of operation:

1. **Validation** - Strict checking that returns errors for any invalid input
2. **Sanitization** - Converting invalid inputs into valid ones by replacing problematic characters

This dual approach allows applications to:
- Strictly reject invalid inputs in security-critical contexts
- Automatically fix issues in user-friendly interfaces

### Error Types

Each module defines its own error type that clearly describes all possible validation failures:

```rust
pub enum Error {
    InvalidByte { byte: BString },
    StartsWithSlash,
    RepeatedSlash,
    RepeatedDot,
    LockFileSuffix,
    ReflogPortion,
    Asterisk,
    StartsWithDot,
    EndsWithDot,
    EndsWithSlash,
    Empty,
}
```

These errors provide clear, actionable information about why validation failed and what needs to be fixed.

### Internal Use in gitoxide

While `gix-validate` can be used directly, it's primarily consumed by higher-level gitoxide crates like:

- `gix-ref` - For validating references
- `gix-object` - For validating tags and other object names
- `gix-worktree` - For validating paths before they're written to the filesystem

This foundational role makes it a critical component for gitoxide's safety and correctness.