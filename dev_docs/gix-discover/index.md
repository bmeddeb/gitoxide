# gix-discover

## Overview

The `gix-discover` crate provides functionality for discovering Git repositories, both in a given directory and by traversing parent directories. It also offers utilities to check if a directory is a Git repository and determine its type (bare repository, worktree, etc.). The crate serves as a foundational component for Git repository operations in the gitoxide ecosystem.

## Architecture

`gix-discover` is designed with a simple and focused architecture, primarily centered around repository discovery and validation. The crate follows a modular approach with clear separation of concerns:

1. **Repository Discovery**: Functions to locate Git repositories by traversing directories upward
2. **Repository Validation**: Utilities to check if a directory is a valid Git repository
3. **Repository Type Detection**: Logic to determine the kind of repository (bare, worktree, submodule, etc.)

The crate makes informed decisions based on the presence of certain files and directories without diving too deeply into file contents, prioritizing performance over exhaustive validation. For more thorough validation, other crates in the ecosystem can be used after discovery.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `repository::Path` | Represents a path to a repository, which can be a worktree, linked worktree, or repository | Used to identify the type and location of a discovered repository |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `repository::Kind` | Represents the kind of repository discovered | `PossiblyBare`, `WorkTree`, `WorkTreeGitDir`, `Submodule`, `SubmoduleGitDir` |
| `is_git::Error` | Error types that can occur during Git repository validation | Various error types like `MissingHead`, `MissingObjectsDirectory`, etc. |
| `upwards::Error` | Error types that can occur during upward repository discovery | Errors like `NoGitRepository`, `NoGitRepositoryWithinFs`, etc. |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `is_git` | Checks if a directory is a Git repository | `fn is_git(git_dir: &Path) -> Result<repository::Kind, is_git::Error>` |
| `is_bare` | Checks if a Git directory is a bare repository | `fn is_bare(git_dir_candidate: &Path) -> bool` |
| `is_submodule_git_dir` | Checks if a Git directory is a submodule Git directory | `fn is_submodule_git_dir(git_dir: &Path) -> bool` |
| `upwards` | Discovers a Git repository by traversing upward from a given directory | `fn upwards(directory: &Path) -> Result<(repository::Path, Trust), upwards::Error>` |
| `upwards_opts` | Same as `upwards` but with customizable options | `fn upwards_opts(directory: &Path, options: Options<'_>) -> Result<(repository::Path, Trust), upwards::Error>` |
| `parse::gitdir` | Parses a gitdir file content to extract the path | `fn gitdir(input: &[u8]) -> Result<PathBuf, gitdir::Error>` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-sec` | Used for security and trust validation of discovered repositories |
| `gix-path` | Used for path manipulation and normalization |
| `gix-ref` | Used to check for valid HEAD references |
| `gix-hash` | Used for hash-related operations |
| `gix-fs` | Used for filesystem operations like getting the current directory |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Used for byte string handling in path parsing |
| `thiserror` | Used for error type definitions |
| `dunce` (Windows only) | Used for path simplification on Windows |

## Feature Flags

The crate doesn't define its own feature flags, but inherits features from its dependencies.

## Examples

### Discovering a Git Repository

```rust
use gix_discover::{upwards, repository};
use std::path::Path;

// Discover a git repository starting from the current directory
fn find_repository() -> Result<(), Box<dyn std::error::Error>> {
    let start_dir = Path::new(".");
    match upwards(start_dir) {
        Ok((repo_path, trust)) => {
            println!("Found repository: {:?}", repo_path);
            println!("Trust level: {:?}", trust);
            
            // Check if it's a bare repository
            if repo_path.kind().is_bare() {
                println!("Repository is bare");
            } else {
                println!("Repository has a worktree");
            }
            
            // Get repository and worktree paths
            let (git_dir, work_tree) = repo_path.into_repository_and_work_tree_directories();
            println!("Git directory: {:?}", git_dir);
            println!("Work tree: {:?}", work_tree);
        },
        Err(err) => {
            println!("No repository found: {:?}", err);
        }
    }
    Ok(())
}
```

### Checking if a Directory is a Git Repository

```rust
use gix_discover::is_git;
use std::path::Path;

// Check if a directory is a git repository
fn is_git_repository(dir: &str) -> Result<(), Box<dyn std::error::Error>> {
    let path = Path::new(dir);
    match is_git(path) {
        Ok(kind) => {
            println!("{} is a git repository of kind: {:?}", dir, kind);
            Ok(())
        },
        Err(err) => {
            println!("{} is not a git repository: {:?}", dir, err);
            Err(err.into())
        }
    }
}
```

## Implementation Details

### Repository Discovery

The repository discovery process starts from a given directory and follows these steps:

1. Normalize the directory path to handle relative paths like `..` correctly
2. Check if the current directory is a Git repository
3. If not, check if it contains a `.git` directory or file that points to a Git repository
4. If still not found, move to the parent directory and repeat from step 2
5. Continue until a repository is found, or until:
   - The filesystem root is reached
   - A configured ceiling directory is encountered
   - A filesystem boundary is crossed (if `cross_fs` is disabled)

The discovery process is configurable through `upwards::Options`, which allows:
- Setting a required trust level for the repository
- Defining ceiling directories to limit upward traversal
- Controlling whether to cross filesystem boundaries
- Specifying a custom current directory for path normalization
- Restricting search to only `.git` directories (ignoring bare repositories)

### Repository Validation

A directory is considered a valid Git repository if it:
1. Contains a valid HEAD reference
2. Has an objects directory
3. Has a refs directory

The crate distinguishes between different kinds of repositories:
- Regular worktree repositories (`.git` directory within a working directory)
- Bare repositories (no working directory)
- Linked worktrees (created with `git worktree add`)
- Submodule repositories (in `.git/modules/` directory)

### Security Considerations

The crate integrates with `gix-sec` to provide trust level assessment based on repository ownership:
- `Trust::Full`: The repository is owned by the current user
- `Trust::Reduced`: The repository is owned by someone else but has safe permissions
- `Trust::No`: The repository has unsafe permissions or ownership

This helps protect against potentially malicious repositories controlled by other users.

## Testing Strategy

The crate is tested using a combination of approaches:

1. **Unit Tests**: Tests for individual functions and components
2. **Integration Tests**: Tests for entire discovery flows
3. **Test Fixtures**: Generated repositories with various configurations:
   - Bare repositories
   - Non-bare repositories
   - Repositories with/without index files
   - Repositories with/without config files
   - Linked worktrees
   - Submodules
   - Cross-filesystem repositories (on macOS)
   - Repositories with exotic file systems like exFAT

Tests verify correct repository discovery, proper error handling, and accurate repository type detection across different scenarios.