# gix-fetchhead

## Overview

The `gix-fetchhead` crate is designed to handle operations related to Git's FETCH_HEAD file. This crate provides functionality to parse, manipulate, and write FETCH_HEAD files, which are used to track information about references fetched from remote repositories. Although currently in early development (version 0.0.0), this crate will serve as an important component in the gitoxide ecosystem for handling fetch operations.

## Architecture

When fully implemented, `gix-fetchhead` will follow a modular design with clear separation between parsing, manipulation, and serialization of FETCH_HEAD data:

1. **Parsing Layer**: Responsible for reading and parsing the FETCH_HEAD file, extracting information about fetched references.
2. **Data Model**: Represents the structured data contained in a FETCH_HEAD file.
3. **Serialization Layer**: Handles the generation of properly formatted FETCH_HEAD entries and writing them to the file.

This design will prioritize:
- **Performance**: Efficient parsing and generation of FETCH_HEAD entries
- **Correctness**: Adherence to Git's format and semantic rules for FETCH_HEAD
- **Flexibility**: Supporting various use cases like merge determination, reference updates, etc.

## Core Components

When implemented, the crate is expected to provide the following components:

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `FetchHead` | Represents a complete FETCH_HEAD file with multiple entries | Used to read from and write to the FETCH_HEAD file |
| `Entry` | Represents a single entry in the FETCH_HEAD file | Used to store and manipulate individual fetched reference information |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `parse` | Parse a FETCH_HEAD file into a structured representation | `fn parse(content: &[u8]) -> Result<FetchHead, Error>` |
| `write` | Write a FetchHead structure to a file | `fn write(fetch_head: &FetchHead, path: &Path) -> Result<(), Error>` |

## Dependencies

### Internal Dependencies

When implemented, the crate is expected to have the following dependencies:

| Crate | Usage |
|-------|-------|
| `gix-hash` | For handling object IDs referenced in the FETCH_HEAD file |
| `gix-ref` | For working with reference names |
| `gix-url` | For handling remote repository URLs |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | For efficient handling of byte strings in the FETCH_HEAD file |

## Feature Flags

No feature flags are currently defined as the crate is in early development.

## Examples

When implemented, the crate is expected to provide APIs similar to these examples:

### Reading a FETCH_HEAD File

```rust
use gix_fetchhead::FetchHead;
use std::path::Path;

fn read_fetch_head() -> Result<(), Box<dyn std::error::Error>> {
    let repo_path = Path::new("/path/to/repo");
    let fetch_head_path = repo_path.join(".git").join("FETCH_HEAD");
    
    // Read and parse the FETCH_HEAD file
    let fetch_head = FetchHead::from_file(&fetch_head_path)?;
    
    // Iterate through entries
    for entry in fetch_head.entries() {
        println!("Ref: {}", entry.ref_name());
        println!("Remote: {}", entry.remote_name().unwrap_or("(none)"));
        println!("URL: {}", entry.remote_url());
        println!("Object ID: {}", entry.object_id());
        println!("For merge: {}", entry.for_merge());
        println!("---");
    }
    
    Ok(())
}
```

### Writing to a FETCH_HEAD File

```rust
use gix_fetchhead::{FetchHead, Entry};
use gix_hash::ObjectId;
use std::path::Path;

fn update_fetch_head() -> Result<(), Box<dyn std::error::Error>> {
    let repo_path = Path::new("/path/to/repo");
    let fetch_head_path = repo_path.join(".git").join("FETCH_HEAD");
    
    // Create a new FETCH_HEAD structure
    let mut fetch_head = FetchHead::new();
    
    // Add entries for fetched references
    fetch_head.add_entry(Entry::new()
        .with_object_id(ObjectId::from_hex(b"abcdef0123456789abcdef0123456789abcdef01")?)
        .with_ref_name("refs/heads/main")
        .with_remote_name("origin")
        .with_remote_url("https://github.com/example/repo.git")
        .with_for_merge(true));
    
    // Add more entries as needed
    
    // Write to the FETCH_HEAD file
    fetch_head.write_to_file(&fetch_head_path)?;
    
    Ok(())
}
```

## Implementation Details

### FETCH_HEAD File Format

The FETCH_HEAD file uses a specific format for each entry:

```
<object-id>\t<for-merge-marker>\t<reference>\t<remote-description>
```

For example:
```
abcdef0123456789abcdef0123456789abcdef01	branch 'main' of https://github.com/example/repo.git
abcdef0123456789abcdef0123456789abcdef02	not-for-merge	branch 'feature' of https://github.com/example/repo.git
```

When implemented, the crate will need to handle:

1. **Parsing Complexity**: The format has nuances requiring careful parsing, especially with remote descriptions that may contain spaces and special characters.

2. **For-Merge Determination**: The presence or absence of the "not-for-merge" marker determines whether a reference should be considered for merge operations.

3. **Multiple Entries with Same Reference**: FETCH_HEAD may contain multiple entries for the same reference from different remotes, which needs proper handling.

4. **File Locking**: When writing to FETCH_HEAD, proper file locking will be necessary to handle concurrent operations.

### Role in Git Operations

The FETCH_HEAD file serves several important roles in Git operations:

1. **Merge Source Identification**: When executing `git merge FETCH_HEAD`, Git uses this file to identify what to merge.

2. **Remote Reference Tracking**: It keeps track of the latest fetched state of remote references.

3. **Fetch History**: It provides a history of the most recent fetch operation.

4. **Default Pull Target**: When pulling without specifying a remote or branch, Git may use FETCH_HEAD to determine what to merge.

### Performance Considerations

When fully implemented, the crate will need to consider:

1. **Memory Efficiency**: Avoiding unnecessary allocations during parsing and handling potentially large FETCH_HEAD files efficiently.

2. **Parse Speed**: Ensuring fast parsing for large repositories with many remotes and references.

3. **Concurrent Access**: Handling concurrent read/write operations safely.

## Testing Strategy

When implemented, the crate will be tested using:

1. **Unit Tests**: Testing individual components like parsers and serializers.

2. **Integration Tests**: Testing the crate against actual FETCH_HEAD files in repositories.

3. **Property-Based Tests**: Ensuring that serialized and then parsed FETCH_HEAD data remains identical.

4. **Compatibility Tests**: Verifying compatibility with FETCH_HEAD files generated by Git itself.

5. **Edge Cases**: Testing handling of malformed FETCH_HEAD files, concurrent access, and other edge cases.