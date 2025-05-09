# gix-lfs

## Overview

The `gix-lfs` crate is intended to provide Git Large File Storage (LFS) functionality within the gitoxide ecosystem. Git LFS is an extension for Git designed to handle large files more efficiently by storing pointers to the files in the Git repository while storing the actual file contents on a remote server.

**Current Status**: This crate is currently a placeholder. It reserves the name within the gitoxide project but contains no implementation yet. The crate is at version 0.0.0, indicating it's in the early planning stages.

## Architecture

While the crate doesn't have an implementation yet, we can outline the expected architecture based on how Git LFS works:

1. **Filter System Integration**: Git LFS operates through Git's filter system, with "clean" filters that convert files to pointers during staging and "smudge" filters that convert pointers back to actual files during checkout.

2. **Pointer Management**: The system needs to handle LFS pointer files, which are small text files containing metadata about the actual file, including its OID (hash) and size.

3. **Content Storage**: Actual file contents need to be stored separately from the Git repository, either in a local cache or on a remote server.

4. **Transfer Protocol**: A protocol for transferring large files between clients and servers, which typically operates over HTTP(S).

5. **File Locking**: Optional mechanism to prevent concurrent editing of binary files that can't be easily merged.

## Core Components

When implemented, the crate is expected to contain the following components:

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `LfsPointer` | Representation of a Git LFS pointer file | Handling pointer files in the repository |
| `LfsConfig` | LFS configuration parameters | Configuration of LFS behavior |
| `LfsStore` | Interface to the content storage | Managing the storage of large files |
| `LfsFilter` | Implementation of Git's filter system for LFS | Integration with Git's filter mechanism |
| `LfsClient` | HTTP client for LFS server communication | Transferring data to and from LFS servers |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `track` | Mark patterns to be tracked by LFS | `fn track(patterns: &[&str], attributes_file: &Path) -> Result<()>` |
| `untrack` | Remove patterns from LFS tracking | `fn untrack(patterns: &[&str], attributes_file: &Path) -> Result<()>` |
| `push` | Upload LFS objects to a remote server | `fn push(refs: &[&str], remote: &str, options: PushOptions) -> Result<()>` |
| `pull` | Download LFS objects from a remote server | `fn pull(refs: &[&str], remote: &str, options: PullOptions) -> Result<()>` |
| `lock` | Lock a file to prevent concurrent editing | `fn lock(path: &Path, options: LockOptions) -> Result<Lock>` |
| `unlock` | Release a previously acquired lock | `fn unlock(path: &Path, options: UnlockOptions) -> Result<()>` |

## Dependencies

The crate is expected to have the following dependencies when implemented:

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For object ID representation and manipulation |
| `gix-object` | For accessing and manipulating Git objects |
| `gix-filter` | For integrating with Git's filter system |
| `gix-attributes` | For handling .gitattributes files |
| `gix-transport` | For network communication with LFS servers |
| `gix-url` | For parsing and manipulating LFS server URLs |

### External Dependencies

When implemented, the crate might have these external dependencies:

| Crate | Usage |
|-------|-------|
| `reqwest` or similar | For HTTP client functionality |
| `serde` | For serialization/deserialization of LFS pointer files and API responses |
| `async-trait` | For async functionality in traits |
| `thiserror` | For error handling |

## Feature Flags

No feature flags are currently defined as the crate is not yet implemented, but potential ones could include:

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `tokio` | Enable async functionality with Tokio runtime | `tokio`, async versions of other dependencies |
| `file-locking` | Enable file locking functionality | Additional file locking dependencies |
| `progress` | Enable progress reporting for LFS operations | Progress tracking libraries |

## Examples

While there is no implementation yet, here's an example of how the API might look based on Git LFS functionality:

```rust
use gix_lfs::{LfsClient, LfsConfig, LfsStore};
use std::path::Path;

// Configure and initialize LFS for a repository
fn setup_lfs(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Open a repository
    let repo = gix::open(repo_path)?;
    
    // Configure LFS
    let lfs_config = LfsConfig {
        endpoint: "https://example.com/lfs".to_string(),
        local_storage_path: repo_path.join(".git/lfs/objects"),
        ..Default::default()
    };
    
    // Initialize LFS for the repository (sets up filters, etc.)
    gix_lfs::install(&repo, lfs_config)?;
    
    // Track large files by pattern
    gix_lfs::track(&["*.psd", "*.iso", "videos/**"], repo_path.join(".gitattributes"))?;
    
    println!("LFS setup complete");
    Ok(())
}

// Push LFS objects to a remote server
fn push_lfs_objects(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Open a repository
    let repo = gix::open(repo_path)?;
    
    // Create an LFS client
    let lfs_client = LfsClient::new(&repo)?;
    
    // Push LFS objects for the current branch
    lfs_client.push(
        &["HEAD"],
        "origin",
        gix_lfs::PushOptions {
            include_referenced: true,
            ..Default::default()
        }
    )?;
    
    println!("LFS objects pushed successfully");
    Ok(())
}

// Pull LFS objects from a remote server
fn pull_lfs_objects(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Open a repository
    let repo = gix::open(repo_path)?;
    
    // Create an LFS client
    let lfs_client = LfsClient::new(&repo)?;
    
    // Pull LFS objects for the current branch
    lfs_client.pull(
        &["HEAD"],
        "origin",
        gix_lfs::PullOptions {
            include_referenced: true,
            ..Default::default()
        }
    )?;
    
    println!("LFS objects pulled successfully");
    Ok(())
}

// Work with LFS pointers directly
fn manipulate_lfs_pointer(file_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Parse an LFS pointer file
    let pointer = gix_lfs::LfsPointer::from_file(file_path)?;
    
    println!("LFS pointer information:");
    println!("OID: {}", pointer.oid());
    println!("Size: {} bytes", pointer.size());
    
    // Create a new LFS pointer
    let new_pointer = gix_lfs::LfsPointer::new(
        "sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393".parse()?,
        12345
    );
    
    // Write the pointer to a file
    new_pointer.to_file(file_path.with_extension("new"))?;
    
    Ok(())
}
```

## Implementation Details

When implemented, the `gix-lfs` crate will need to address several aspects of Git LFS functionality:

1. **Pointer Format**: The format of LFS pointer files, which typically look like:

   ```
   version https://git-lfs.github.com/spec/v1
   oid sha256:4d7a214614ab2935c943f9e0ff69d22eadbb8f32b1258daaa5e2ca24d17e2393
   size 12345
   ```

2. **Filter Implementation**: Integration with Git's filter system through the `gix-filter` crate, implementing:
   - Clean filter: Converts files to pointers during staging
   - Smudge filter: Converts pointers back to actual files during checkout

3. **Content Storage**: Management of the local cache for LFS objects, typically stored in `.git/lfs/objects`.

4. **Transfer Protocol**: Implementation of the LFS transfer protocol for communicating with LFS servers, which includes:
   - Batch API: For negotiating which objects to transfer
   - Basic transfer adapter: For transferring objects over HTTP(S)

5. **File Locking**: Optional functionality for locking files to prevent concurrent editing, with operations for:
   - Creating locks
   - Listing locks
   - Verifying locks
   - Unlocking files

6. **Integration with gitoxide**: Ensuring seamless integration with other components of the gitoxide ecosystem.

## Testing Strategy

When the crate is implemented, the testing strategy will likely include:

1. **Unit Tests**: Tests for individual components and functions.

2. **Integration Tests**: Tests that verify the correct interaction with other components of the gitoxide ecosystem.

3. **Compatibility Tests**: Tests that verify compatibility with Git LFS and ensure correct handling of pointer files.

4. **Server Communication Tests**: Tests for the LFS client's ability to communicate with LFS servers.

5. **Performance Tests**: Tests for the efficiency of LFS operations, especially with large files.

## Future Development

The `gix-lfs` crate is reserved for future development within the gitoxide project. When implemented, it will provide a Rust-native interface for working with Git LFS, enabling applications to efficiently handle large files in Git repositories. The implementation is likely to follow the Git LFS specification and provide similar functionality to the official Git LFS client, but with the benefits of Rust's safety, performance, and ecosystem integration.