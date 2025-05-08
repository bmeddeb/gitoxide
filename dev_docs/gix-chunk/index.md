# gix-chunk

## Overview

The `gix-chunk` crate provides low-level functionality for reading and writing chunk file formats used in Git. It specifically supports the chunk file format documented in Git's [technical documentation](https://github.com/git/git/blob/seen/Documentation/technical/chunk-format.txt), which is used in Multi-Pack Indexes (MIDX) and commit-graph files. This crate enables efficient access to data stored in these chunked files by managing their table of contents and providing utilities for reading and writing these specialized files.

## Architecture

The crate follows a straightforward architecture focused on the specific requirements of chunk files:

1. **Core Types**: Defines the fundamental types like `Id` (chunk identifier) and `Offset` (position within a file)
2. **Index Management**: Provides structures to represent and navigate a chunk file's table of contents
3. **File Operations**: Implements reading and writing functions for working with chunk files

The design emphasizes safety and correctness first, with extensive validation to ensure chunk files are properly formed, while still providing efficient access to data within the file.

### Key Concepts

- **Chunk Format**: A file format consisting of:
  - A table of contents (TOC) at the beginning listing chunk types and their locations
  - A series of chunks, each with a unique 4-byte identifier
  - A sentinel value marking the end of the table of contents

- **Index**: A representation of the table of contents that allows for efficient lookup of chunks by their identifier

- **Chunk Writing**: A structured approach to writing chunks that validates sizes and ensures proper formatting

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Index` | Represents a chunk file's table of contents | Central structure for accessing chunks within a file |
| `index::Entry` | An entry in the table of contents | Maps a chunk identifier to its location in the file |
| `write::Chunk<W>` | A writer for chunk data | Validates chunk sizes during writing operations |

### Types

| Type | Description | Usage |
|------|-------------|-------|
| `Id` | A 4-byte identifier for a chunk | Used to identify different chunk types (e.g., `RIDX`, `OIDX`) |
| `Offset` | Position in a file as a u64 | Used to represent chunk boundaries |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `Index::from_bytes` | Decode a chunk file's table of contents | `fn from_bytes(data: &[u8], toc_offset: usize, num_chunks: u32) -> Result<Self, Error>` |
| `Index::for_writing` | Create an index for writing chunks | `fn for_writing() -> Self` |
| `Index::plan_chunk` | Add a chunk to be written | `fn plan_chunk(&mut self, chunk: Id, exact_size_on_disk: u64)` |
| `Index::into_write` | Convert the index to a writer | `fn into_write<W: Write>(self, out: W, current_offset: usize) -> io::Result<Chunk<W>>` |
| `Index::offset_by_id` | Find a chunk's offset by its ID | `fn offset_by_id(&self, kind: Id) -> Result<Range<Offset>, offset_by_kind::Error>` |
| `Index::data_by_id` | Get a chunk's data by its ID | `fn data_by_id<'a>(&self, data: &'a [u8], kind: Id) -> Result<&'a [u8], data_by_kind::Error>` |

### Constants

| Constant | Description | Value |
|----------|-------------|-------|
| `SENTINEL` | Marks the end of the chunk file TOC | `[0u8; 4]` |
| `Index::ENTRY_SIZE` | Size of a TOC entry in bytes | Size of ID (4) + size of offset (8) = 12 bytes |
| `Index::EMPTY_SIZE` | Minimum size of a TOC (just sentinel) | 12 bytes |

### Error Types

| Error | Description | Usage |
|-------|-------------|-------|
| `decode::Error` | Errors when decoding a chunk file | Reports issues with file format validation |
| `index::offset_by_kind::Error` | Error when chunk not found | Reports when a requested chunk ID doesn't exist |
| `index::data_by_kind::Error` | Errors accessing chunk data | Reports issues with chunk access |

## Dependencies

### Internal Dependencies

The `gix-chunk` crate is at level 0 in the dependency hierarchy, meaning it doesn't depend on other gitoxide crates.

### External Dependencies

| Crate | Usage |
|-------|-------|
| `thiserror` | Error handling and formatting |

## Feature Flags

The crate doesn't define any feature flags.

## Examples

### Reading a Chunk File

```rust
use gix_chunk::{Id, file::Index};
use std::fs::File;
use std::io::Read;

// Read the file into memory
let mut file = File::open("multi-pack-index")?;
let mut data = Vec::new();
file.read_to_end(&mut data)?;

// MIDX header is 12 bytes, then comes the TOC
let toc_offset = 12;
let num_chunks = 4; // Example: OIDX, PNAM, IFAN, EOMD chunks

// Parse the table of contents
let index = Index::from_bytes(&data, toc_offset, num_chunks)?;

// Get data from a specific chunk (e.g., OIDX - Object ID Fanout)
let oidx_id = *b"OIDX";
let oidx_data = index.data_by_id(&data, oidx_id)?;

// Work with the chunk data
println!("OIDX chunk size: {} bytes", oidx_data.len());
```

### Writing a Chunk File

```rust
use gix_chunk::{Id, file::Index};
use std::fs::File;
use std::io::{Write, BufWriter};

// Create a new file
let file = File::create("output.midx")?;
let mut writer = BufWriter::new(file);

// Write a header (for MIDX)
let header = b"\xfeMIDX\x01\x00\x00\x00\x04\x00\x00\x00";
writer.write_all(header)?;

// Create an index for writing
let mut index = Index::for_writing();

// Plan chunks with their sizes
index.plan_chunk(*b"OIDX", 1024); // 1KB object ID fanout table
index.plan_chunk(*b"PNAM", 512);  // 512B packfile names 
index.plan_chunk(*b"IFAN", 2048); // 2KB fanout data
index.plan_chunk(*b"EOMD", 128);  // 128B end of MIDX data

// Convert the index to a chunk writer, starting after the header
let mut chunk_writer = index.into_write(writer, 12)?;

// Write each chunk
if let Some(chunk_id) = chunk_writer.next_chunk() {
    // Write OIDX data (1024 bytes)
    let oidx_data = generate_oidx_data();
    chunk_writer.write_all(&oidx_data)?;
}

if let Some(chunk_id) = chunk_writer.next_chunk() {
    // Write PNAM data (512 bytes)
    let pnam_data = generate_pnam_data();
    chunk_writer.write_all(&pnam_data)?;
}

// ... write remaining chunks ...

// Finalize the file
let writer = chunk_writer.into_inner();
writer.flush()?;
```

## Implementation Details

### Binary Format

The chunk file format consists of:

1. A file header (specific to the file type, not handled by this crate)
2. A table of contents containing:
   - One entry per chunk, with:
     - 4-byte chunk identifier (e.g., "OIDX")
     - 8-byte offset to chunk data (big-endian)
   - A sentinel entry (zeros for identifier) marking the end
3. The actual chunk data, stored sequentially

### Safety Validations

The crate performs extensive validation when decoding chunk files:
- Verifies that chunk offsets are within file bounds
- Ensures chunk offsets are in ascending order
- Checks for duplicate chunk identifiers
- Validates the presence of the sentinel marker
- Verifies that all expected chunks are present

### Memory Management

The crate is designed for safe and efficient memory usage:
- Uses memory-mapped files implicitly through byte slices
- Returns references to the original data rather than copying
- Handles conversion between file offsets and memory addresses safely

### Performance Considerations

- The design focuses on minimal allocations and copies
- Index lookups are O(n) in the number of chunks, which is typically small
- Validation is thorough but adds minimal overhead compared to I/O operations

## Testing Strategy

While the crate doesn't contain explicit doctest or test modules based on the Cargo.toml configuration, the implementation has:

- Extensive error checking with detailed error messages
- Assertions to catch misuse during development
- Careful bounds checking to prevent undefined behavior

The crate is also indirectly tested through its use in higher-level crates like `gix-commitgraph` and `gix-pack` for MIDX files.