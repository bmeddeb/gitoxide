# gix-worktree-stream

## Overview

The `gix-worktree-stream` crate provides functionality for generating streams of file entries from Git trees, similar to the `git archive` command but using an internal format. It enables the efficient streaming of content from Git trees, with support for filtering and transformation of content according to Git attributes. This crate is essential for operations that need to process or extract files from a Git repository, such as checkout, archive creation, or content inspection.

## Architecture

`gix-worktree-stream` follows a producer-consumer architecture with the following key components:

1. **Stream Generation**: The crate efficiently traverses a Git tree and converts its contents into a byte stream, exposing each entry with its metadata and content.

2. **Filtering**: The crate supports content filtering through Git's attribute system, allowing transformations like line-ending normalization or text encoding.

3. **Additional Entries**: Beyond the content in the Git tree, the stream can be augmented with additional entries from other sources.

4. **Threaded Operation**: The crate uses a background thread for tree traversal and content generation, synchronizing with the consumer through a pipe to ensure efficient memory usage.

5. **Binary Protocol**: An internal binary protocol efficiently encodes entry metadata and content, supporting both known-size content and streaming.

The overall design prioritizes memory efficiency and streaming performance, allowing large trees to be processed without loading everything into memory at once.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Stream` | Central component that provides access to entries from a Git tree | Used to iterate through entries in a Git tree |
| `Entry<'a>` | Represents a single entry in the stream with file metadata and content | Used to access details and read content of a specific file |
| `AdditionalEntry` | Defines an extra entry to add to the stream beyond the Git tree | Used to inject content from other sources into the stream |
| `Delegate` | Internal component that handles tree traversal and stream generation | Used by the tree traversal system to process entries |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| N/A | The crate primarily uses composition rather than traits for its architecture | N/A |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `from_tree` | Creates a stream from a Git tree | `fn from_tree<Find, E>(tree: ObjectId, objects: Find, pipeline: Pipeline, attributes: impl FnMut(&BStr, EntryMode, &mut Outcome) -> Result<(), E> + Send + 'static) -> Stream` |
| `Stream::new` | Internal function to create a stream with a pipe writer | `fn new() -> (Stream, pipe::Writer, Receiver<AdditionalEntry>)` |
| `Stream::next_entry` | Gets the next entry from the stream | `fn next_entry(&mut self) -> Result<Option<Entry<'_>>, Error>` |
| `Stream::into_read` | Converts the stream into a Read implementation | `fn into_read(self) -> impl std::io::Read` |
| `Stream::from_read` | Creates a stream from a Read implementation | `fn from_read(read: impl std::io::Read + 'static) -> Self` |
| `Stream::add_entry` | Adds a custom entry to the stream | `fn add_entry(&mut self, entry: AdditionalEntry) -> &mut Self` |
| `Stream::add_entry_from_path` | Adds an entry from a file system path | `fn add_entry_from_path(&mut self, root: &Path, path: &Path) -> std::io::Result<&mut Self>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `entry::Error` | Represents errors that can occur during stream operation | `Io`, `Find`, `FindTree`, `Attributes`, `Traverse`, `ConvertToWorktree` |
| `entry::Source` | Defines where additional entry content comes from | `Null`, `Path`, `Memory` |
| `utils::Read` | Internal enum for different read implementations | `Known`, `Unknown` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-features` | Used for IO pipes and progress tracking |
| `gix-hash` | Used for working with Git object IDs |
| `gix-object` | Used for accessing Git tree objects and their content |
| `gix-attributes` | Used for processing Git attributes affecting export |
| `gix-filter` | Used for applying filters to blob content |
| `gix-traverse` | Used for efficient tree traversal |
| `gix-fs` | Used for file system operations |
| `gix-path` | Used for path manipulation and conversion |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `thiserror` | Error type definitions |
| `parking_lot` | Efficient mutex implementation for shared error slot |
| `bstr` | Binary string handling for paths |

## Feature Flags

The crate does not define any specific feature flags. It uses features from its dependencies as needed.

## Examples

Here's an example of using the `Stream` to process files from a Git tree:

```rust
use gix_worktree_stream::from_tree;
use gix_attributes::search::Outcome;
use gix_object::bstr::BStr;
use gix_hash::ObjectId;
use gix_filter::Pipeline;
use std::io::Read;
use std::path::Path;

// Process a Git tree and apply filters to its contents
fn process_tree(
    repo_path: &Path,
    tree_id: ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static
) -> std::io::Result<()> {
    // Create a filter pipeline
    let pipeline = Pipeline::default();
    
    // Create a worktree to check attributes
    let attributes_fn = |path: &BStr, mode, attrs: &mut Outcome| {
        // Typically you'd check attributes from a Stack here
        // For simplicity, we just set default attributes
        attrs.set_export_ignore(false);
        Ok(())
    };
    
    // Create the stream from the tree
    let mut stream = from_tree(
        tree_id, 
        objects.clone(),
        pipeline,
        attributes_fn,
    );
    
    // Process each entry
    while let Some(mut entry) = stream.next_entry()? {
        println!(
            "Path: {}, Mode: {:?}, ID: {}",
            entry.relative_path(), 
            entry.mode.kind(),
            entry.id
        );
        
        // Read and process the entry content
        let mut content = Vec::new();
        entry.read_to_end(&mut content)?;
        
        // Process the content as needed...
        if !content.is_empty() {
            println!("  Content size: {} bytes", content.len());
        }
    }
    
    Ok(())
}
```

Here's an example of adding custom entries to the stream:

```rust
use gix_worktree_stream::{from_tree, AdditionalEntry, entry};
use gix_hash::ObjectId;
use gix_object::tree::EntryKind;
use gix_object::bstr::ByteVec;
use std::path::Path;

fn create_archive_with_custom_entries(
    repo_path: &Path,
    tree_id: ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static,
    output_path: &Path
) -> std::io::Result<()> {
    // Create the basic stream
    let mut stream = from_tree(
        tree_id,
        objects.clone(),
        gix_filter::Pipeline::default(),
        |_, _, attrs| {
            attrs.set_export_ignore(false);
            Ok(())
        },
    );
    
    // Add a readme file that doesn't exist in the repository
    let readme_content = b"# Project Archive\n\nThis archive was created with gix-worktree-stream.".to_vec();
    stream.add_entry(AdditionalEntry {
        id: ObjectId::null(gix_hash::Kind::Sha1), // ID doesn't matter for additional entries
        mode: EntryKind::Blob.into(),
        relative_path: "README.md".into(),
        source: entry::Source::Memory(readme_content),
    });
    
    // Add existing files from the file system
    let license_path = repo_path.join("LICENSE");
    if license_path.exists() {
        stream.add_entry_from_path(repo_path, &license_path)?;
    }
    
    // Convert stream to a reader and write to file
    let reader = stream.into_read();
    let mut file = std::fs::File::create(output_path)?;
    std::io::copy(&mut std::io::BufReader::new(reader), &mut file)?;
    
    Ok(())
}
```

## Implementation Details

### Streaming Protocol

The crate uses a custom binary protocol to efficiently encode entry information:

1. **Entry Header**: Contains information about the path length, stream length, entry mode, and hash kind.
2. **Object ID**: The Git object ID identifying the content.
3. **Path**: The relative path of the entry.
4. **Content**: The actual file content, potentially chunked for streaming entries.

This format allows for efficient transmission with minimal overhead, supporting both known-size content and streamed content of unknown size.

### Threaded Operation

The crate uses a background thread for tree traversal and content generation:

1. The `from_tree` function spawns a thread that traverses the tree.
2. The thread communicates with the main thread via a pipe.
3. Content is produced lazily as entries are consumed.
4. If an error occurs during traversal, it's stored in a shared error slot.

This design ensures that memory usage is kept to a minimum, as only one entry's content is in memory at a time, and tree traversal doesn't get ahead of consumption.

### Tree Traversal Strategy

The crate uses breadth-first traversal to process the tree:

1. It starts at the root tree and visits all entries.
2. When encountering a tree entry, it applies the export-ignore attribute check.
3. If the tree isn't ignored, it's queued for later traversal.
4. For blob entries, they're converted to worktree format and written to the stream.

This approach ensures that directory structure is maintained in the output stream.

### Content Filtering

The crate integrates with Git's attribute and filter systems:

1. For each entry, it checks the `export-ignore` attribute to determine if it should be included.
2. For included entries, it applies content filters (like line-ending conversion) via the filter pipeline.
3. Filtered content is then written to the stream.

This allows for transformations like line-ending normalization during stream generation.

### Additional Entries

Beyond the content in the Git tree, the stream can be augmented with additional entries:

1. Additional entries can come from memory, filesystem paths, or be empty (null).
2. They're processed after the Git tree entries.
3. Each additional entry follows the same protocol format.

This is particularly useful for adding files that aren't tracked in Git or for injecting generated content.

## Testing Strategy

The crate is tested through:

1. **Unit Tests**: Testing individual components like the protocol encoding/decoding.

2. **Integration Tests**: Testing the full stream generation and consumption with real repositories.

3. **Edge Cases**: Tests cover scenarios like empty trees, attribute errors, object retrieval failures, etc.

4. **Content Transformation**: Tests verify that content filters are correctly applied based on attributes.

5. **Additional Entries**: Tests confirm that entries can be added from various sources and are correctly streamed.

The tests ensure that the generated stream is valid, can be consumed incrementally, and correctly applies all transformations according to Git attributes.