# gix-shallow Use Cases

This document describes common use cases for the `gix-shallow` crate, focusing on how it can be used to manage shallow repositories in Git.

## Intended Audience

- Git client developers implementing shallow repository functionality
- Library consumers managing Git repositories with different depths
- Developers of Git repository management tools
- CI/CD system maintainers optimizing Git operations

## Use Case 1: Detecting Shallow Repository Status

### Problem

A Git client needs to detect whether a repository is shallow and identify which commits form the shallow boundary.

### Solution

The `gix-shallow` crate provides a simple `read()` function to check shallow status and retrieve boundary commits.

```rust
use std::path::Path;
use gix_shallow::read;

fn is_shallow_repository(git_dir: &Path) -> Result<bool, Box<dyn std::error::Error>> {
    let shallow_file = git_dir.join("shallow");
    match read(&shallow_file)? {
        Some(commits) => {
            println!("Repository is shallow with {} boundary commits", commits.len());
            Ok(true)
        },
        None => {
            println!("Repository is not shallow");
            Ok(false)
        }
    }
}

fn get_shallow_boundary(git_dir: &Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let shallow_file = git_dir.join("shallow");
    match read(&shallow_file)? {
        Some(commits) => {
            // Convert ObjectIds to hex strings
            let commit_hexes = commits.iter()
                .map(|id| id.to_hex().to_string())
                .collect();
            Ok(commit_hexes)
        },
        None => Ok(Vec::new()) // Not a shallow repository
    }
}
```

## Use Case 2: Making a Repository Shallow

### Problem

After cloning a full repository, a developer wants to convert it to a shallow repository to save disk space.

### Solution

The `gix-shallow` crate can be used to create and manage a shallow boundary.

```rust
use std::path::Path;
use gix_hash::ObjectId;
use gix_lock::File;
use gix_shallow::{read, write, Update};

fn make_repository_shallow(
    git_dir: &Path, 
    boundary_commit: &str
) -> Result<(), Box<dyn std::error::Error>> {
    let shallow_file = git_dir.join("shallow");
    
    // Read current shallow commits (likely None for a full repository)
    let shallow_commits = read(&shallow_file)?;
    
    // Create a lock file for writing
    let lock_file = File::acquire_to_update(&shallow_file, None, None)?;
    
    // Parse the commit that will form the shallow boundary
    let commit_id = ObjectId::from_hex(boundary_commit.as_bytes())?;
    
    // Create update instruction to make this commit shallow
    let updates = [Update::Shallow(commit_id)];
    
    // Write the updated shallow file
    write(lock_file, shallow_commits, &updates)?;
    
    println!("Repository is now shallow with boundary at commit {}", boundary_commit);
    Ok(())
}
```

## Use Case 3: Deepening a Shallow Repository

### Problem

A developer working with a shallow repository needs to access more history, but doesn't want to fully unshallow the repository.

### Solution

The `gix-shallow` crate can update the shallow boundary by removing certain commits and adding others.

```rust
use std::path::Path;
use gix_hash::ObjectId;
use gix_lock::File;
use gix_shallow::{read, write, Update};

fn deepen_repository(
    git_dir: &Path, 
    remove_from_boundary: &[&str],
    add_to_boundary: &[&str]
) -> Result<(), Box<dyn std::error::Error>> {
    let shallow_file = git_dir.join("shallow");
    
    // Read current shallow commits
    let shallow_commits = read(&shallow_file)?;
    
    // Check if repository is shallow
    if shallow_commits.is_none() {
        return Err("Repository is not shallow".into());
    }
    
    // Create updates for deepening
    let mut updates = Vec::new();
    
    // Commits to unshallow (remove from boundary)
    for commit_hex in remove_from_boundary {
        let commit_id = ObjectId::from_hex(commit_hex.as_bytes())?;
        updates.push(Update::Unshallow(commit_id));
    }
    
    // New commits to add to boundary
    for commit_hex in add_to_boundary {
        let commit_id = ObjectId::from_hex(commit_hex.as_bytes())?;
        updates.push(Update::Shallow(commit_id));
    }
    
    // Create a lock file for writing
    let lock_file = File::acquire_to_update(&shallow_file, None, None)?;
    
    // Write the updated shallow file
    write(lock_file, shallow_commits, &updates.as_slice())?;
    
    println!("Successfully deepened the repository");
    Ok(())
}
```

## Use Case 4: Fully Unshallowing a Repository

### Problem

A developer needs to convert a shallow repository to a full repository with complete history.

### Solution

The `gix-shallow` crate can be used to remove all commits from the shallow boundary.

```rust
use std::path::Path;
use gix_lock::File;
use gix_shallow::{read, write, Update};

fn unshallow_repository(git_dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let shallow_file = git_dir.join("shallow");
    
    // Read current shallow commits
    let shallow_commits = match read(&shallow_file)? {
        Some(commits) => commits,
        None => {
            println!("Repository is already not shallow");
            return Ok(());
        }
    };
    
    // Create unshallow instructions for all boundary commits
    let updates: Vec<Update> = shallow_commits.iter()
        .map(|commit_id| Update::Unshallow(*commit_id))
        .collect();
    
    // Create a lock file for writing
    let lock_file = File::acquire_to_update(&shallow_file, None, None)?;
    
    // Write the updated shallow file (should remove it since it will be empty)
    write(lock_file, Some(shallow_commits), &updates)?;
    
    println!("Repository has been fully unshallowed");
    Ok(())
}
```

## Use Case 5: Synchronizing Shallow Information Between Repositories

### Problem

A Git tool needs to transfer shallow boundary information between repositories, such as during a partial fetch or push operation.

### Solution

`gix-shallow` can be used to read, transfer, and write shallow boundary information.

```rust
use std::path::Path;
use gix_lock::File;
use gix_shallow::{read, write};

fn synchronize_shallow_boundary(
    source_git_dir: &Path,
    target_git_dir: &Path
) -> Result<(), Box<dyn std::error::Error>> {
    // Read shallow boundary from source
    let source_shallow_file = source_git_dir.join("shallow");
    let shallow_commits = read(&source_shallow_file)?;
    
    // If source is not shallow, no need to synchronize
    if shallow_commits.is_none() {
        println!("Source repository is not shallow, nothing to synchronize");
        return Ok(());
    }
    
    // Create lock file for target
    let target_shallow_file = target_git_dir.join("shallow");
    let lock_file = File::acquire_to_update(&target_shallow_file, None, None)?;
    
    // Write the same shallow boundary to target (no updates needed)
    write(lock_file, shallow_commits, &[])?;
    
    println!("Shallow boundary synchronized successfully");
    Ok(())
}
```

## Use Case 6: Integrating with Repository Management Tools

### Problem

A Git management tool needs to read and modify shallow information as part of repository maintenance operations.

### Solution

`gix-shallow` can be integrated with repository management workflows for advanced operations.

```rust
use std::path::Path;
use gix_hash::ObjectId;
use gix_lock::File;
use gix_shallow::{read, write, Update};

fn optimize_shallow_boundary(
    git_dir: &Path,
    check_reachability: impl Fn(&ObjectId) -> Result<bool, Box<dyn std::error::Error>>
) -> Result<(), Box<dyn std::error::Error>> {
    let shallow_file = git_dir.join("shallow");
    
    // Read current shallow commits
    let shallow_commits = match read(&shallow_file)? {
        Some(commits) => commits,
        None => return Ok(()),
    };
    
    // Analyze which boundary commits should be unshallowed
    let mut updates = Vec::new();
    for commit_id in &shallow_commits {
        // If commit is now reachable through other means, we can unshallow it
        if check_reachability(commit_id)? {
            updates.push(Update::Unshallow(*commit_id));
        }
    }
    
    // If no updates needed, we're done
    if updates.is_empty() {
        println!("No optimization needed for shallow boundary");
        return Ok(());
    }
    
    // Create lock file for writing
    let lock_file = File::acquire_to_update(&shallow_file, None, None)?;
    
    // Update the shallow file
    write(lock_file, Some(shallow_commits), &updates)?;
    
    println!("Optimized shallow boundary by removing {} unreachable commits", updates.len());
    Ok(())
}
```

## Summary

The `gix-shallow` crate provides essential functionality for managing shallow repositories in Git, enabling:

1. **Detection**: Determining if a repository is shallow and identifying boundary commits
2. **Modification**: Adding or removing commits from the shallow boundary
3. **Conversion**: Making full repositories shallow or fully unshallowing repositories
4. **Synchronization**: Transferring shallow boundary information between repositories
5. **Optimization**: Maintaining efficient shallow boundaries for repository operations

These capabilities make the crate valuable for implementing Git clients, repository management tools, and CI/CD systems that need to work with repositories of different depths. By providing simple, focused functionality for reading and writing the `.git/shallow` file, the crate enables precise control over shallow repository boundaries while maintaining compatibility with Git's shallow repository implementation.