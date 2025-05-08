# gix-fsck

## Overview

The `gix-fsck` crate provides functionality for verifying the integrity and connectivity of objects in a Git repository. Named after Git's `fsck` command (which stands for "file system check"), this crate focuses on ensuring that all referenced objects in a repository exist and are accessible. It's a crucial component for detecting corruption, missing objects, or incomplete repository transfers.

## Architecture

The `gix-fsck` crate follows a straightforward design focused on the core task of validating repository connectivity. It primarily consists of a single main struct that performs a depth-first traversal of Git objects starting from a commit, ensuring that all referenced trees and blobs exist.

The architecture is built around these key concepts:

1. **Connectivity Checking**: The primary function of verifying that all objects referenced by a commit (including its tree and all nested objects) exist in the object database.

2. **Object Traversal**: A depth-first traversal algorithm that walks through the entire object graph from a starting commit.

3. **Missing Object Handling**: A flexible callback-based approach for reporting missing objects.

This design emphasizes:
- **Efficiency**: Objects are only checked once, even if referenced multiple times
- **Flexibility**: Missing object handling can be customized via callbacks
- **Simplicity**: Focus on a single, well-defined task without unnecessary complexity

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Connectivity<T, F>` | The primary struct for performing connectivity checks | Used to verify object connectivity starting from a commit |

### Traits / Bounds

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `T: FindExt + Exists` | Bounds for the object database type | Any object database that can find objects by ID and check if they exist |
| `F: FnMut(&ObjectId, Kind)` | Bound for the missing object callback | Any function or closure that receives missing object information |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `Connectivity::new` | Creates a new connectivity checker | `fn new(db: T, missing_cb: F) -> Connectivity<T, F>` |
| `Connectivity::check_commit` | Runs the connectivity check starting from a commit | `fn check_commit(&mut self, oid: &ObjectId) -> Result<(), gix_object::find::existing_object::Error>` |
| `check_blob` (private) | Checks if a blob exists | `fn check_blob<F>(db: impl Exists, oid: &ObjectId, mut missing_cb: F) where F: FnMut(&ObjectId, Kind)` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For handling object IDs |
| `gix-hashtable` | For efficient object ID caching using HashSet |
| `gix-object` | For finding objects, accessing their content, and determining their type |

### External Dependencies

The crate has no direct external dependencies beyond those inherited from its internal dependencies.

## Feature Flags

The crate doesn't define its own feature flags but inherits features from its dependencies.

## Examples

### Basic Connectivity Check

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;
use std::collections::HashMap;

// Assume we have an object database that implements FindExt + Exists
let odb = get_object_database();

// Track missing objects
let mut missing_objects = HashMap::new();
let record_missing = |oid: &ObjectId, kind: Kind| {
    missing_objects.insert(*oid, kind);
    println!("Missing object: {} ({})", oid, kind);
};

// Create a connectivity checker
let mut checker = Connectivity::new(odb, record_missing);

// Check a specific commit
let commit_id = ObjectId::from_hex(b"abcdef1234567890abcdef1234567890abcdef12").unwrap();
match checker.check_commit(&commit_id) {
    Ok(()) => {
        if missing_objects.is_empty() {
            println!("All objects are present and connected!");
        } else {
            println!("Found {} missing objects", missing_objects.len());
            // Handle missing objects
        }
    },
    Err(e) => {
        println!("Error checking commit: {}", e);
        // Handle error (e.g., commit itself is missing)
    }
}
```

### Checking Multiple Commits

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;

// Assume we have an object database and multiple commits to check
let odb = get_object_database();
let commits = vec![
    ObjectId::from_hex(b"commit1_hash_here...").unwrap(),
    ObjectId::from_hex(b"commit2_hash_here...").unwrap(),
    ObjectId::from_hex(b"commit3_hash_here...").unwrap(),
];

// Create a connectivity checker that logs missing objects
let mut checker = Connectivity::new(odb, |oid, kind| {
    println!("Missing object detected: {} ({})", oid, kind);
});

// Check all commits
for commit_id in &commits {
    match checker.check_commit(commit_id) {
        Ok(()) => println!("Checked commit: {}", commit_id),
        Err(e) => println!("Error checking commit {}: {}", commit_id, e),
    }
}
```

### Integration with Repository Handling

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;
use std::io::Write;

// Function to check a repository given a reference like "HEAD" or "main"
fn check_repository_integrity(
    repo_path: &str, 
    reference: &str,
    output: &mut impl Write
) -> Result<bool, Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Resolve the reference to a commit ID
    let commit_id = repo.rev_parse_single(reference)?.object()?.id();
    
    // Count missing objects
    let mut missing_count = 0;
    let on_missing = |oid: &ObjectId, kind: Kind| {
        writeln!(output, "Missing: {} ({})", oid, kind).unwrap();
        missing_count += 1;
    };
    
    // Create a connectivity checker and run it
    let mut checker = Connectivity::new(&repo.objects, on_missing);
    checker.check_commit(&commit_id)?;
    
    // Return whether all objects are present
    Ok(missing_count == 0)
}
```

## Implementation Details

### Algorithm

The connectivity check algorithm works as follows:

1. Start with a commit object ID.
2. Check if the commit has already been seen (using the `seen` HashSet). If so, return.
3. Mark the commit as seen.
4. Find the commit object in the database, extracting its tree ID.
5. Initialize a queue with the tree ID.
6. While the queue isn't empty:
   a. Pop a tree ID from the queue.
   b. Mark the tree as seen.
   c. Find the tree object in the database, reporting it as missing if not found.
   d. For each entry in the tree:
      i. If it's a tree, add it to the queue (unless already seen).
      ii. If it's a blob, check if it exists in the database (unless already seen).
      iii. If it's a commit (submodule), skip it as it belongs to another repository.

The algorithm efficiently handles cycles in the object graph by tracking seen objects and avoids redundant checks for objects referenced multiple times.

### Object References and Handling

Git objects reference each other in specific ways:

1. **Commit -> Tree**: Each commit points to a tree representing the repository's state.
2. **Tree -> Blob/Tree/Commit**: Trees can reference blobs (files), other trees (directories), or commits (submodules).

The `gix-fsck` crate handles these references appropriately:

- **Blobs**: Checked for existence using the `Exists` trait.
- **Trees**: Checked for existence and then traversed for more references.
- **Commits (as submodules)**: Ignored, as they belong to a different repository.

### Missing Object Reporting

When a missing object is detected, it's reported through the callback function provided to the `Connectivity` struct. This allows for flexible handling of missing objects, such as:

- Recording them in a data structure
- Logging them to a file or console
- Taking corrective action (e.g., attempting to fetch them)
- Aborting the check early for critical objects

### Performance Considerations

The crate is designed with performance in mind:

1. **Object Caching**: The `seen` HashSet ensures that objects are only checked once.
2. **Buffer Reuse**: A single buffer is reused for all object reads to reduce allocations.
3. **Depth-first Traversal**: This approach is memory-efficient and works well with Git's object model.
4. **Early Return**: The algorithm stops checking branches that have already been explored.

## Testing Strategy

The crate is tested using:

1. **Unit Tests**: Testing the connectivity checker with different repository scenarios.
2. **Fixture Repositories**: Using specially crafted repositories with known missing objects.
3. **Integration Tests**: Testing the crate's interaction with higher-level components.

Test fixtures include:
- A complete repository with all objects present
- A repository missing some blobs (simulating `--filter=blob:none` clone)
- A repository missing some trees (simulating `--filter=tree:0` clone)

These tests verify that the connectivity checker correctly identifies missing objects of different types and handles various edge cases appropriately.