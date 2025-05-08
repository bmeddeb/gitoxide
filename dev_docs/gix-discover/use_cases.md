# gix-discover Use Cases

This document describes the main use cases for the gix-discover crate, who its intended audience is, what problems it solves, and how it solves them.

## Intended Audience

The primary audience for the gix-discover crate includes:

1. **Git Tool Developers**: Developers building Git-aware tools that need to locate and identify Git repositories
2. **Git Client Developers**: Developers implementing Git clients that need repository discovery
3. **Gitoxide Component Developers**: Internal users developing other components in the gitoxide ecosystem

## Core Use Cases

### 1. Find a Git Repository from the Current Working Directory

#### Problem

Many Git commands need to locate the repository they're operating on, typically starting from the current working directory and traversing upward until a Git repository is found.

#### Solution

The `upwards` function handles this use case by starting at a specified directory and exploring parent directories until a Git repository is found. It returns the repository path and a trust level.

```rust
use gix_discover::upwards;
use std::path::Path;

fn find_git_repository() -> Result<(), Box<dyn std::error::Error>> {
    let start_dir = Path::new(".");
    match upwards(start_dir) {
        Ok((repo_path, trust_level)) => {
            println!("Found repository at: {:?}", repo_path);
            println!("Trust level: {:?}", trust_level);
            
            // Get the Git directory and worktree paths
            let (git_dir, work_tree) = repo_path.into_repository_and_work_tree_directories();
            println!("Git directory: {:?}", git_dir);
            if let Some(work_tree) = work_tree {
                println!("Work tree: {:?}", work_tree);
            } else {
                println!("No work tree (bare repository)");
            }
        },
        Err(err) => {
            println!("No Git repository found: {:?}", err);
        }
    }
    Ok(())
}
```

### 2. Validate a Git Repository Path

#### Problem

When given a specific path, determine if it is a valid Git repository and what kind of repository it is (bare, worktree, etc.).

#### Solution

The `is_git` function checks if a given path is a valid Git repository and returns its type.

```rust
use gix_discover::{is_git, repository::Kind};
use std::path::Path;

fn validate_git_repository(path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let path = Path::new(path);
    match is_git(path) {
        Ok(kind) => {
            match kind {
                Kind::PossiblyBare => {
                    println!("Found a bare repository at {:?}", path);
                },
                Kind::WorkTree { linked_git_dir } => {
                    if let Some(linked_dir) = linked_git_dir {
                        println!("Found a linked worktree with git dir at {:?}", linked_dir);
                    } else {
                        println!("Found a standard worktree repository");
                    }
                },
                Kind::WorkTreeGitDir { work_dir } => {
                    println!("Found a worktree git directory linked to {:?}", work_dir);
                },
                Kind::Submodule { git_dir } => {
                    println!("Found a submodule with git dir at {:?}", git_dir);
                },
                Kind::SubmoduleGitDir => {
                    println!("Found a submodule git directory");
                },
            }
            Ok(())
        },
        Err(err) => {
            println!("Not a valid Git repository: {:?}", err);
            Err(err.into())
        }
    }
}
```

### 3. Find a Repository with Custom Discovery Options

#### Problem

Standard repository discovery might not be suitable for all situations. Users may need to:
- Set trust requirements to prevent using untrustworthy repositories
- Set ceiling directories to limit upward traversal
- Control filesystem boundary crossing
- Only look for specific types of repositories

#### Solution

The `upwards_opts` function provides customizable repository discovery.

```rust
use gix_discover::{upwards_opts, upwards::Options};
use gix_sec::Trust;
use std::path::Path;

fn find_repository_with_options() -> Result<(), Box<dyn std::error::Error>> {
    let start_dir = Path::new(".");
    
    // Configure discovery options
    let options = Options {
        // Only accept fully trusted repositories
        required_trust: Trust::Full,
        // Set directories that stop the upward search
        ceiling_dirs: vec![PathBuf::from("/home/user")],
        // Stop at the first ceiling directory
        match_ceiling_dir_or_error: true,
        // Don't cross filesystem boundaries
        cross_fs: false,
        // Use the current directory for path normalization
        current_dir: None,
        // Only look for .git directories (ignore bare repos)
        dot_git_only: true,
    };
    
    match upwards_opts(start_dir, options) {
        Ok((repo_path, trust)) => {
            println!("Found repository: {:?} with trust level {:?}", repo_path, trust);
            Ok(())
        },
        Err(err) => {
            println!("Repository discovery failed: {:?}", err);
            Err(err.into())
        }
    }
}
```

### 4. Detect Repository Type for Different Operations

#### Problem

Different repository types require different handling. For example, bare repositories don't have a working directory, and worktrees might have a linked Git directory.

#### Solution

The `repository::Path` and `repository::Kind` types help identify and handle different repository types.

```rust
use gix_discover::{upwards, repository::Path};
use std::path::Path as StdPath;

fn perform_repository_type_specific_operation() -> Result<(), Box<dyn std::error::Error>> {
    let start_dir = StdPath::new(".");
    let (repo_path, _) = upwards(start_dir)?;
    
    match repo_path {
        Path::Repository(path) => {
            println!("Operating on bare repository at {:?}", path);
            // Perform bare repository specific operations
        },
        Path::WorkTree(work_dir) => {
            println!("Operating on worktree at {:?}", work_dir);
            // Perform standard worktree operations
        },
        Path::LinkedWorkTree { work_dir, git_dir } => {
            println!("Operating on linked worktree:");
            println!("  Worktree: {:?}", work_dir);
            println!("  Git dir: {:?}", git_dir);
            // Perform linked worktree specific operations
        }
    }
    
    Ok(())
}
```

### 5. Parse .git File References

#### Problem

Submodules and worktrees use a `.git` file to reference their actual Git directory. This file needs to be parsed to find the real Git directory.

#### Solution

The `parse::gitdir` function extracts the Git directory path from a `.git` file.

```rust
use gix_discover::parse;
use std::{fs, path::Path};

fn find_actual_git_dir(git_file_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let path = Path::new(git_file_path);
    let content = fs::read(path)?;
    
    match parse::gitdir(&content) {
        Ok(git_dir_path) => {
            println!("The actual Git directory is at: {:?}", git_dir_path);
            Ok(())
        },
        Err(err) => {
            println!("Failed to parse .git file: {:?}", err);
            Err(err.into())
        }
    }
}
```

### 6. Check if Repository is Bare

#### Problem

Different operations are needed for bare vs. non-bare repositories. A quick way to determine this is needed.

#### Solution

The `is_bare` function provides a quick check to determine if a Git directory is likely a bare repository.

```rust
use gix_discover::is_bare;
use std::path::Path;

fn check_if_bare(git_dir: &str) -> bool {
    let path = Path::new(git_dir);
    let is_bare_repo = is_bare(path);
    
    println!("Repository at {:?} is bare: {}", path, is_bare_repo);
    is_bare_repo
}
```

### 7. Identify Submodule Git Directories

#### Problem

Submodule Git directories need special handling, and it's useful to identify them quickly.

#### Solution

The `is_submodule_git_dir` function checks if a Git directory is located in a `.git/modules` directory.

```rust
use gix_discover::is_submodule_git_dir;
use std::path::Path;

fn check_if_submodule_git_dir(git_dir: &str) -> bool {
    let path = Path::new(git_dir);
    let is_submodule = is_submodule_git_dir(path);
    
    println!("Directory at {:?} is a submodule git dir: {}", path, is_submodule);
    is_submodule
}
```

## Integration with Other Components

The gix-discover crate is typically one of the first components used in Git operations, as it helps locate and identify the repository to work with. After discovery, other components can take over for specific operations:

1. After finding a repository with `upwards`, the path can be passed to repository opening functions
2. The trust level returned alongside the repository path can be used for security-aware operations
3. The repository kind information can guide which components to use next (e.g., different handling for bare vs. non-bare repositories)

```rust
// Example of integration with other gitoxide components
use gix_discover::upwards;
use std::path::Path;

fn perform_git_operation() -> Result<(), Box<dyn std::error::Error>> {
    // First discover the repository
    let (repo_path, _) = upwards(Path::new("."))?;
    
    // Extract Git directory and possible worktree
    let (git_dir, work_tree) = repo_path.into_repository_and_work_tree_directories();
    
    // Now use other gitoxide components with the discovered paths
    // For example, open the repository, access its refs, objects, etc.
    println!("Ready to operate on repository at {:?}", git_dir);
    
    Ok(())
}
```