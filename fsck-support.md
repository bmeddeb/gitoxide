# FSCK Support in Gitoxide

Gitoxide provides repository integrity checking functionality similar to Git's `fsck` command. This document explains how to use the `gix-fsck` crate to verify the integrity of Git repositories.

## Overview of FSCK Functionality

The `gix-fsck` library in gitoxide provides tools to check the integrity and connectivity of Git object databases. The primary functionality is implemented through the `Connectivity` struct, which:

1. Performs connectivity checks on Git repository objects
2. Verifies that all objects referenced by commits, trees, and blobs exist
3. Reports missing objects through a callback mechanism
4. Traverses the object graph to ensure integrity

## Required Crates

To use the FSCK functionality, you need:

- `gix-fsck` - The core FSCK implementation
- `gix-hash` - For object ID handling
- `gix-object` - For object manipulation
- `gix-hashtable` - For efficient set operations

## Example Usage

Here's a basic example of using the FSCK functionality to check a repository's integrity:

```rust
use std::io::{self, Write};
use gix::{objs::Kind, ObjectId};
use gix_fsck::Connectivity;
use anyhow::Result;

fn check_repo_integrity(repo_path: &str) -> Result<()> {
    // Open the repository
    let mut repo = gix::open(repo_path)?;
    
    // Prepare output for reporting missing objects
    let mut output = io::stdout();
    
    // Set up the callback function for missing objects
    let on_missing = |oid: &ObjectId, kind: Kind| {
        writeln!(output, "Missing object: {oid} (type: {kind})").unwrap();
    };
    
    // Create a connectivity checker
    let mut checker = Connectivity::new(&repo.objects, on_missing);
    
    // Get HEAD commit or any reference point
    let head_id = repo.head()?.peel_to_id_in_place()?.detach();
    
    // Check the commit and all its referenced objects
    checker.check_commit(&head_id)?;
    
    println!("Repository integrity check complete");
    Ok(())
}
```

## Advanced Usage: Checking All Commits

To perform a full repository check similar to `git fsck`, you can traverse all commits:

```rust
fn check_all_commits(repo_path: &str) -> Result<()> {
    let mut repo = gix::open(repo_path)?;
    let mut output = io::stdout();
    
    // Configure for better performance with many objects
    repo.object_cache_size_if_unset(4 * 1024 * 1024);
    
    // We expect to find missing objects, so don't refresh the ODB
    repo.objects.refresh_never();
    
    // Find all commits
    let commits = repo
        .rev_parse_single("--all")?
        .object()?
        .peel_to_kind(gix::object::Kind::Commit)?
        .id()
        .ancestors()
        .all()?;
    
    let on_missing = |oid: &ObjectId, kind: Kind| {
        writeln!(output, "Missing object: {oid} (type: {kind})").unwrap();
    };
    
    let mut checker = Connectivity::new(&repo.objects, on_missing);
    
    // Check each commit
    for commit_result in commits {
        let commit = commit_result?;
        checker.check_commit(&commit.id)?;
    }
    
    println!("Complete repository integrity check finished");
    Ok(())
}
```

## Including FSCK in Your Extraction

To include the FSCK functionality in your extraction from gitoxide, add the following to your `Cargo.toml`:

```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["revision"] }
gix-fsck = { version = "0.47.1" }
```

If you're using the direct source copy approach, you'll need to copy these additional directories:
```bash
cp -r /path/to/gitoxide/gix-fsck .
cp -r /path/to/gitoxide/gix-hashtable .  # Required by gix-fsck
```

And update your workspace Cargo.toml:
```toml
[workspace]
members = [
    # other members
    "gix-fsck",
    "gix-hashtable",
    # ...
]
```

## Integration with Other Gitoxide Features

The FSCK functionality works well with other gitoxide features:

1. **Combined with Cloning**: Verify the integrity of a repository after cloning it
2. **Combined with Log**: Check that the commit history is properly connected
3. **Prior to Operations**: Ensure repository health before performing operations

## Notes on Performance

The FSCK operation can be resource-intensive for large repositories:

1. Set an appropriate object cache size to improve performance:
   ```rust
   repo.object_cache_size(32 * 1024 * 1024); // 32 MB cache
   ```

2. For very large repositories, consider checking only a subset of commits:
   ```rust
   let commits = repo.rev_walk([head_id])
       .sorting(gix::revision::walk::Sorting::ByCommitTime(Default::default()))
       .all()?
       .map_while(Result::ok)
       .take(100);  // Check only the 100 most recent commits
   ```

3. The `Connectivity` struct is designed to efficiently track seen objects to avoid checking the same object multiple times.