# gix-fetchhead Use Cases

This document describes the intended use cases for the gix-fetchhead crate, who its target audience is, what problems it solves, and how it will solve them once fully implemented.

## Intended Audience

The primary audience for the gix-fetchhead crate includes:

1. **Git Tool Developers**: Developers building Git-aware tools that need to interact with or manipulate a repository's FETCH_HEAD file
2. **Git Client Developers**: Developers implementing Git clients that need to handle fetch operations
3. **Gitoxide Ecosystem Developers**: Developers of other crates in the gitoxide ecosystem that need to interact with FETCH_HEAD

## Core Use Cases

### 1. Reading FETCH_HEAD After a Fetch Operation

#### Problem

After fetching from a remote repository, Git stores information about the fetched references in the FETCH_HEAD file. Applications often need to read this information to determine what was fetched and make decisions based on that data.

#### Solution

The gix-fetchhead crate will provide a simple API to parse the FETCH_HEAD file and access its contents in a structured way.

```rust
use gix_fetchhead::FetchHead;
use std::path::Path;

fn examine_fetch_results(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Parse the FETCH_HEAD file
    let fetch_head = FetchHead::from_file(&repo_path.join(".git/FETCH_HEAD"))?;
    
    // Check if a specific branch was fetched and if it's marked for merge
    if let Some(entry) = fetch_head.find_entry("refs/heads/main", "origin") {
        println!("Main branch was fetched with ID: {}", entry.object_id());
        
        if entry.for_merge() {
            println!("The branch is marked for merge");
        } else {
            println!("The branch is not marked for merge");
        }
    }
    
    // Count how many references were fetched
    println!("Total fetched references: {}", fetch_head.entries().count());
    
    Ok(())
}
```

### 2. Updating FETCH_HEAD During a Custom Fetch Operation

#### Problem

When implementing custom fetch operations outside of Git's standard tools, developers need to properly update the FETCH_HEAD file to maintain compatibility with other Git tools and operations.

#### Solution

The gix-fetchhead crate will provide functionality to create and write properly formatted FETCH_HEAD entries.

```rust
use gix_fetchhead::{FetchHead, Entry};
use gix_hash::ObjectId;
use std::path::Path;

fn update_fetch_head_after_custom_fetch(
    repo_path: &Path,
    fetched_refs: &[(String, ObjectId, bool)], // (ref_name, object_id, for_merge)
    remote_name: &str,
    remote_url: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let fetch_head_path = repo_path.join(".git/FETCH_HEAD");
    
    // Create a new FETCH_HEAD structure
    let mut fetch_head = FetchHead::new();
    
    // Add entries for each fetched reference
    for (ref_name, object_id, for_merge) in fetched_refs {
        fetch_head.add_entry(
            Entry::new()
                .with_object_id(*object_id)
                .with_ref_name(ref_name)
                .with_remote_name(remote_name)
                .with_remote_url(remote_url)
                .with_for_merge(*for_merge)
        );
    }
    
    // Write to the FETCH_HEAD file
    fetch_head.write_to_file(&fetch_head_path)?;
    
    Ok(())
}
```

### 3. Determining Merge Candidates from FETCH_HEAD

#### Problem

When performing a merge without specifying a branch (e.g., `git merge`), Git uses the FETCH_HEAD to determine what should be merged. Applications mimicking this behavior need to analyze the FETCH_HEAD file to find appropriate merge candidates.

#### Solution

The gix-fetchhead crate will provide methods to filter and find entries marked for merge in the FETCH_HEAD file.

```rust
use gix_fetchhead::FetchHead;
use std::path::Path;

fn find_merge_candidates(repo_path: &Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Parse the FETCH_HEAD file
    let fetch_head = FetchHead::from_file(&repo_path.join(".git/FETCH_HEAD"))?;
    
    // Collect all references marked for merge
    let merge_candidates = fetch_head.entries()
        .filter(|entry| entry.for_merge())
        .map(|entry| format!("{} ({} from {})", 
                             entry.ref_name(), 
                             entry.object_id(), 
                             entry.remote_name().unwrap_or("unknown")))
        .collect();
    
    Ok(merge_candidates)
}
```

### 4. Finding the Latest Fetched Version of a Reference

#### Problem

Applications sometimes need to determine the latest fetched version of a specific reference, regardless of whether it was marked for merge.

#### Solution

The gix-fetchhead crate will provide methods to search for specific references in the FETCH_HEAD file.

```rust
use gix_fetchhead::FetchHead;
use gix_hash::ObjectId;
use std::path::Path;

fn get_latest_fetched_ref(
    repo_path: &Path, 
    ref_name: &str
) -> Result<Option<ObjectId>, Box<dyn std::error::Error>> {
    // Parse the FETCH_HEAD file
    let fetch_head = FetchHead::from_file(&repo_path.join(".git/FETCH_HEAD"))?;
    
    // Find entries matching the reference name, regardless of remote
    let matching_entries = fetch_head.entries()
        .filter(|entry| entry.ref_name() == ref_name)
        .collect::<Vec<_>>();
    
    // Return the object ID of the first matching entry, if any
    let result = matching_entries.first().map(|entry| entry.object_id());
    
    Ok(result)
}
```

### 5. Validating the Format of FETCH_HEAD

#### Problem

The FETCH_HEAD file can become corrupted or malformed, causing issues with Git operations. Applications might need to validate its format to ensure compatibility.

#### Solution

The gix-fetchhead crate will provide validation functionality to check if a FETCH_HEAD file is correctly formatted.

```rust
use gix_fetchhead::FetchHead;
use std::path::Path;

fn validate_fetch_head(repo_path: &Path) -> Result<bool, Box<dyn std::error::Error>> {
    let fetch_head_path = repo_path.join(".git/FETCH_HEAD");
    
    // Check if the file exists
    if !fetch_head_path.exists() {
        println!("FETCH_HEAD file doesn't exist");
        return Ok(false);
    }
    
    // Attempt to parse the file
    match FetchHead::from_file(&fetch_head_path) {
        Ok(fetch_head) => {
            // Perform additional validation if needed
            println!("FETCH_HEAD is valid with {} entries", fetch_head.entries().count());
            Ok(true)
        },
        Err(err) => {
            println!("FETCH_HEAD is invalid: {}", err);
            Ok(false)
        }
    }
}
```

### 6. Supporting Custom Registry Index Updates (cargo/crates.io)

#### Problem

As mentioned in the development reports, cargo's registry index stores the most recent HEAD in FETCH_HEAD. Tools interacting with crates.io registry need to correctly interpret and update this file.

#### Solution

The gix-fetchhead crate will provide specialized functions for handling registry-specific FETCH_HEAD patterns.

```rust
use gix_fetchhead::{FetchHead, Entry};
use gix_hash::ObjectId;
use std::path::Path;

fn update_registry_fetch_head(
    registry_path: &Path,
    latest_commit_id: ObjectId,
    registry_url: &str
) -> Result<(), Box<dyn std::error::Error>> {
    let fetch_head_path = registry_path.join(".git/FETCH_HEAD");
    
    // Create a new FETCH_HEAD with a single entry for the registry
    let mut fetch_head = FetchHead::new();
    
    // Add an entry for the registry's HEAD reference
    fetch_head.add_entry(
        Entry::new()
            .with_object_id(latest_commit_id)
            .with_ref_name("HEAD")
            .with_remote_url(registry_url)
            .with_for_merge(true) // Registry updates are typically marked for merge
    );
    
    // Write to the FETCH_HEAD file
    fetch_head.write_to_file(&fetch_head_path)?;
    
    Ok(())
}
```

### 7. Efficiently Reading FETCH_HEAD in Large Repositories

#### Problem

In large repositories with many remotes and branches, the FETCH_HEAD file can become quite large, especially after fetching updates from multiple remotes.

#### Solution

The gix-fetchhead crate will provide efficient parsing and streaming options to handle large FETCH_HEAD files without loading the entire content into memory.

```rust
use gix_fetchhead::FetchHead;
use std::path::Path;

fn analyze_large_fetch_head(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let fetch_head_path = repo_path.join(".git/FETCH_HEAD");
    
    // Use a streaming parser for large FETCH_HEAD files
    let mut stats = FetchHead::stream_from_file(&fetch_head_path)?
        .fold((0, 0), |(total, for_merge), entry| {
            (
                total + 1,
                for_merge + if entry.for_merge() { 1 } else { 0 }
            )
        });
    
    println!("Analyzed {} entries, {} marked for merge", stats.0, stats.1);
    
    Ok(())
}
```

## Integration with Other Components

The gix-fetchhead crate is designed to integrate with the broader gitoxide ecosystem:

### Integration with Remote Operations

When performing fetch operations with the `gix-transport` and `gix-protocol` crates, gix-fetchhead will provide the functionality to record the fetched references in the FETCH_HEAD file.

```rust
// Pseudocode showing integration with fetch operations
async fn fetch_from_remote(repo: &gix::Repository, remote_name: &str) -> Result<(), Error> {
    // Perform fetch using gix-transport and gix-protocol
    let fetch_result = repo.remote(remote_name)?.fetch()?;
    
    // Use gix-fetchhead to update FETCH_HEAD
    let mut fetch_head = gix_fetchhead::FetchHead::new();
    
    // Add entries for each fetched reference
    for ref_update in fetch_result.updated_refs {
        fetch_head.add_entry(
            gix_fetchhead::Entry::new()
                .with_object_id(ref_update.new_oid)
                .with_ref_name(&ref_update.ref_name)
                .with_remote_name(remote_name)
                .with_remote_url(&fetch_result.remote_url)
                .with_for_merge(ref_update.is_branch())
        );
    }
    
    // Write the updated FETCH_HEAD
    fetch_head.write_to_file(&repo.path().join("FETCH_HEAD"))?;
    
    Ok(())
}
```

### Integration with Merge Operations

When performing merges, the gix-fetchhead crate will help identify appropriate merge candidates from the FETCH_HEAD file.

```rust
// Pseudocode showing integration with merge operations
fn merge_from_fetch_head(repo: &gix::Repository) -> Result<(), Error> {
    // Read FETCH_HEAD
    let fetch_head_path = repo.path().join("FETCH_HEAD");
    let fetch_head = gix_fetchhead::FetchHead::from_file(&fetch_head_path)?;
    
    // Find merge candidates (entries marked for merge)
    let merge_candidates = fetch_head.entries()
        .filter(|entry| entry.for_merge())
        .collect::<Vec<_>>();
    
    if merge_candidates.is_empty() {
        return Err(Error::NoCandidatesForMerge);
    }
    
    // Use the first merge candidate
    let entry = &merge_candidates[0];
    
    // Perform the merge using the object ID from the FETCH_HEAD entry
    repo.merge(&entry.object_id())?;
    
    Ok(())
}
```

### Integration with Reference Updates

When updating references after a fetch, gix-fetchhead will help determine what references need to be updated based on the FETCH_HEAD file.

```rust
// Pseudocode showing integration with reference updates
fn update_refs_from_fetch_head(repo: &gix::Repository) -> Result<(), Error> {
    // Read FETCH_HEAD
    let fetch_head_path = repo.path().join("FETCH_HEAD");
    let fetch_head = gix_fetchhead::FetchHead::from_file(&fetch_head_path)?;
    
    // For each fetched branch reference, update the corresponding local remote-tracking branch
    for entry in fetch_head.entries() {
        // Only process branch references
        if !entry.ref_name().starts_with("refs/heads/") {
            continue;
        }
        
        let branch_name = entry.ref_name().strip_prefix("refs/heads/").unwrap();
        let remote_name = entry.remote_name().unwrap_or("origin");
        let remote_tracking_ref = format!("refs/remotes/{}/{}", remote_name, branch_name);
        
        // Update the remote-tracking reference
        repo.references()?.update(
            &remote_tracking_ref,
            entry.object_id(),
            true, // Force update
            &format!("update by fetch from {}", remote_name)
        )?;
    }
    
    Ok(())
}
```

## Conclusion

The gix-fetchhead crate will provide essential functionality for handling Git's FETCH_HEAD file, supporting a range of use cases from basic parsing to complex fetch and merge operations. By offering a Rust-native interface to this important Git component, it will enhance the gitoxide ecosystem's ability to perform Git operations efficiently and correctly.