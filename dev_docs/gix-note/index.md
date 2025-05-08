# gix-note

## Overview

The `gix-note` crate is intended to provide functionality for working with Git notes within the gitoxide ecosystem. Git notes allow attaching additional metadata to Git objects (primarily commits) without modifying the objects themselves. This is useful for adding supplementary information like code review comments, CI build statuses, or additional context that doesn't belong in the commit message.

**Current Status**: This crate is currently a placeholder. It reserves the name within the gitoxide project but contains no implementation yet. The crate is at version 0.0.0, indicating it's in the early planning stages.

## Architecture

While the crate doesn't have implementation yet, we can outline the expected architecture based on Git's notes functionality:

1. **Note Storage**: Git notes are stored in the `refs/notes/` namespace, with `refs/notes/commits` being the default reference.

2. **Object Mapping**: Each note is associated with a specific Git object (typically a commit) by using the object's hash as the path in a tree.

3. **Note Content**: Notes are stored as blob objects in the Git object database, containing arbitrary text content.

4. **Operations**: The crate will likely provide operations for adding, editing, removing, and merging notes, similar to the `git notes` command.

## Core Components

When implemented, the crate is expected to contain the following components:

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Note` | Representation of a Git note | Core data structure for note manipulation |
| `NotesRef` | Reference to a notes namespace | Used to specify which notes collection to work with |
| `NotesManager` | Interface for managing notes | High-level API for note operations |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `add` | Add a note to an object | `fn add(target: &ObjectId, content: &[u8], options: AddOptions) -> Result<ObjectId>` |
| `remove` | Remove a note from an object | `fn remove(target: &ObjectId, options: RemoveOptions) -> Result<bool>` |
| `show` | Show the note for an object | `fn show(target: &ObjectId, options: ShowOptions) -> Result<Option<Vec<u8>>>` |
| `list` | List objects that have notes | `fn list(options: ListOptions) -> Result<Vec<ObjectId>>` |
| `merge` | Merge notes from another notes ref | `fn merge(source_ref: &NotesRef, options: MergeOptions) -> Result<MergeSummary>` |

## Dependencies

The crate is expected to have the following dependencies when implemented:

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For object ID representation and manipulation |
| `gix-object` | For accessing and manipulating Git objects |
| `gix-ref` | For handling Git references, where notes are stored |
| `gix-odb` | For accessing the object database |

### External Dependencies

No external dependencies are currently defined as the crate is not yet implemented.

## Feature Flags

No feature flags are currently defined as the crate is not yet implemented.

## Examples

While there is no implementation yet, here's an example of how the API might look based on Git's notes functionality:

```rust
// Example of what the API might look like when implemented
use gix_hash::ObjectId;
use gix_note::{Notes, AddOptions};

fn add_note_to_commit() -> Result<(), Box<dyn std::error::Error>> {
    // Open a repository
    let repo = gix::open("/path/to/repo")?;
    
    // Create a notes manager for the default notes reference
    let mut notes = Notes::new(repo.clone(), None)?;
    
    // Add a note to a commit
    let commit_id = ObjectId::from_hex("abcdef1234567890abcdef1234567890abcdef12")?;
    let note_content = b"This commit passed all CI tests";
    
    notes.add(
        &commit_id, 
        note_content, 
        AddOptions {
            force: false,
            ..Default::default()
        }
    )?;
    
    println!("Note added successfully");
    
    // Show the note
    let note = notes.show(&commit_id, Default::default())?;
    if let Some(content) = note {
        println!("Note content: {}", String::from_utf8_lossy(&content));
    }
    
    Ok(())
}
```

## Implementation Details

When implemented, the `gix-note` crate will need to address several aspects of Git's notes functionality:

1. **Notes References**: Support for different notes references (beyond the default `refs/notes/commits`).

2. **Formatting**: Handling the formatting of notes content, which are typically plain text but can be any format.

3. **Merge Strategies**: Support for different merge strategies when combining notes from different sources:
   - `manual`: Manual resolution of conflicts
   - `ours`: Keep the local notes version
   - `theirs`: Use the remote notes version
   - `union`: Concatenate notes (default)
   - `cat_sort_uniq`: Concatenate and sort notes, removing duplicates

4. **Performance Considerations**: Efficient access and manipulation of notes, especially for repositories with a large number of notes.

## Testing Strategy

When the crate is implemented, the testing strategy will likely include:

1. **Unit Tests**: Tests for individual components and functions.

2. **Integration Tests**: Tests that verify the correct interaction with other components of the gitoxide ecosystem.

3. **Compatibility Tests**: Tests that verify compatibility with Git's notes implementation.

4. **Edge Cases**: Tests for handling edge cases like empty notes, large notes, and notes for non-existent objects.

## Future Development

The `gix-note` crate is reserved for future development within the gitoxide project. When implemented, it will provide a Rust-native interface for working with Git notes, enabling applications to add metadata to Git objects without modifying them.