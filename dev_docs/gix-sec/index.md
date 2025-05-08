# gix-sec

## Overview

`gix-sec` provides a shared trust and security model for the gitoxide ecosystem. It handles security-related concerns such as determining trust levels for resources, managing permissions, and validating ownership of files and directories. The crate implements platform-specific checks to determine if resources are owned by the current user, which influences trust decisions.

## Architecture

The crate is organized around three core concepts:

1. **Trust**: A security level model with two states (`Full` and `Reduced`) to indicate how much a resource can be trusted.

2. **Permission**: An access control mechanism with three levels (`Allow`, `Deny`, and `Forbid`) to determine if operations can be performed.

3. **Identity**: Functionality to verify ownership of resources, with platform-specific implementations for Windows, Unix-like systems, and WASI.

The architecture follows a security-first approach, where operations are only permitted when explicitly allowed, and trust is reduced by default unless proven otherwise. This follows the principle of least privilege.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `ReadWrite` | A bitflag for resource access permissions (read/write) | Used to specify which operations are permitted on a resource |
| `Account` | An identity with username and password | Used to represent user credentials |
| `trust::Mapping<T>` | Maps trust levels to values of type T | Used to provide different behaviors depending on trust level |
| `permission::Error<R>` | An error for permission-denied situations | Returned when permission checks fail |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `trust::DefaultForLevel` | Creates default values based on trust level | Used by types that need to provide defaults for different trust levels |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `identity::is_path_owned_by_current_user` | Checks if a path is owned by the current user | `fn is_path_owned_by_current_user(path: &Path) -> std::io::Result<bool>` |
| `Trust::from_path_ownership` | Determines trust level based on path ownership | `fn from_path_ownership(path: &std::path::Path) -> std::io::Result<Self>` |
| `Permission::check` | Validates a permission and returns the resource if allowed | `fn check<R: std::fmt::Debug>(&self, resource: R) -> Result<Option<R>, Error<R>>` |
| `Permission::check_opt` | Validates a permission but coalesces into an Option | `fn check_opt<R: std::fmt::Debug>(&self, resource: R) -> Option<R>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Trust` | Indicates how trusted a resource is | `Reduced`, `Full` |
| `Permission` | Controls access to resources or operations | `Forbid`, `Deny`, `Allow` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-path` | Used on Windows to handle path operations and home directory detection |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bitflags` | Used to implement the `ReadWrite` flag set |
| `serde` | Optional serialization/deserialization of data structures |
| `libc` | Used on non-Windows platforms for system-level user ID checks |
| `windows-sys` | Used on Windows for security API access |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization for data structures | `serde`, `bitflags/serde` |

## Examples

```rust
// Check if the current path is owned by the user
use std::path::Path;
use gix_sec::{Trust, identity};

fn get_trust_for_path(path: &Path) -> std::io::Result<Trust> {
    Trust::from_path_ownership(path)
}

// Using permissions to control access
use gix_sec::Permission;

fn access_resource(permission: Permission, resource: &str) -> Result<(), Box<dyn std::error::Error>> {
    match permission.check(resource) {
        Ok(Some(res)) => {
            println!("Resource '{}' access allowed", res);
            Ok(())
        }
        Ok(None) => {
            println!("Resource access denied, skipping");
            Ok(())
        }
        Err(err) => {
            Err(Box::new(err))
        }
    }
}

// Using trust mapping to provide different behaviors
use gix_sec::trust::{DefaultForLevel, Mapping};

struct SecurityConfig {
    allow_remote: bool,
    allow_external_tools: bool,
}

impl DefaultForLevel for SecurityConfig {
    fn default_for_level(level: Trust) -> Self {
        match level {
            Trust::Full => Self {
                allow_remote: true,
                allow_external_tools: true,
            },
            Trust::Reduced => Self {
                allow_remote: false,
                allow_external_tools: false,
            },
        }
    }
}

fn get_security_config(trust_level: Trust) -> SecurityConfig {
    let mapping = Mapping::<SecurityConfig>::default();
    mapping.into_value_by_level(trust_level)
}
```

## Implementation Details

### Trust Model

The trust model is binary (`Full` or `Reduced`) which simplifies decision-making in security contexts. The primary method for determining trust is through file ownership - if a file is owned by the current user, it's fully trusted; otherwise, it has reduced trust.

### Platform-Specific Implementations

The crate implements platform-specific checks for file ownership:

1. **Unix-like systems**: Uses `libc` calls to compare the file's UID with the current process's effective UID. Also handles the case where a process is running under `sudo` by checking the `SUDO_UID` environment variable.

2. **Windows**: Uses Windows Security APIs to check file ownership and administrator group membership. Special handling for the home directory which is always considered trusted.

3. **WASI**: Since the WebAssembly System Interface doesn't have a concept of users, all paths are considered trusted.

### Permission System

The permission system has three levels:
- `Allow`: Operation is permitted
- `Deny`: Operation is rejected but doesn't cause errors
- `Forbid`: Operation is rejected and an error is raised

This provides flexibility for handling denied operations either by skipping them or by treating them as errors.

## Testing Strategy

The crate uses unit tests to verify:

1. Core functionality of the `Trust` and `Permission` enums including ordering and comparison
2. Path ownership checks using temporary directories that are guaranteed to be owned by the current user
3. Special case handling for the Windows home directory

The tests verify that ownership is correctly determined across platforms and that the permission system functions as expected.