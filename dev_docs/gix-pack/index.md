# gix-pack

## Overview

The `gix-pack` crate implements Git's pack file format, which is used for efficient storage and transfer of Git objects. Pack files store multiple Git objects (commits, trees, blobs, and tags) in a single compressed file, often with delta compression to reduce size. This format is critical for Git's performance, especially when working with large repositories or when transferring objects over a network.

The crate provides functionality for:
- Reading and parsing pack files and indices
- Creating new pack files from Git objects
- Finding objects within pack files
- Verifying pack file integrity
- Working with multi-pack indices for improved performance

## Architecture

The crate is organized around several key components:

1. **Pack Data Files** (`data::File`): Storage of the actual Git objects, potentially delta-compressed
2. **Pack Indices** (`index::File`): Lookup tables that map object IDs to their locations in the data file
3. **Bundles** (`Bundle`): Combined pack data and index for convenient access
4. **Multi-Pack Indices** (`multi_index::File`): Indices that span multiple pack files
5. **Caching** (`cache`): Caching mechanisms for improved performance

The architecture follows a layered approach:
- Low-level components handle raw byte-level operations
- Mid-level components provide structured access to pack elements
- High-level components offer convenient APIs for common operations

A core design principle is minimizing memory usage while maximizing performance through techniques like memory mapping, delta resolution caching, and lazy loading of data.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `data::File` | Represents a pack data file | Reading and accessing packed objects |
| `index::File` | Represents a pack index file | Finding objects in a pack by their hash |
| `Bundle` | Combines a pack data file and its index | Convenient access to both data and index |
| `multi_index::File` | Represents a multi-pack index | Efficient lookup across multiple packs |
| `data::Entry` | Represents an entry in a pack file | Access to object metadata in a pack |
| `find::Entry` | Entry with source location information | Used when generating new packs |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `data::Version` | Pack data file version | `V2`, `V3` |
| `index::Version` | Pack index file version | `V1`, `V2` |
| `multi_index::Version` | Multi-pack index file version | `V1` |
| `data::entry::Kind` | Types of entries in a pack | `Base`, `OfsDelta`, `RefDelta` |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `Find` | Object lookup functionality | `Bundle`, custom object databases |
| `FindExt` | Convenience extensions for `Find` | Automatically implemented for all `Find` implementors |
| `cache::DecodeEntry` | Pack entry caching interface | Cache implementations |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-object` | Git object representation and parsing |
| `gix-hash` | Hash handling for object identification |
| `gix-features` | Feature flags and utilities |
| `gix-chunk` | Chunked file handling |
| `gix-path` | Path handling for pack files |
| `gix-traverse` | Object graph traversal (with "generate" feature) |
| `gix-diff` | Diff implementation for delta generation (with "generate" feature) |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `memmap2` | Memory-mapped file access |
| `smallvec` | Small vector optimization |
| `parking_lot` | Efficient mutex implementation (with "generate" or "streaming-input" features) |
| `uluru` | Fixed-size allocation-free LRU cache (with "pack-cache-lru-static" feature) |
| `clru` | Memory-cap-based LRU cache (with "pack-cache-lru-dynamic" or "object-cache-dynamic" features) |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `generate` | Support for generating new pack files | `gix-traverse`, `gix-diff`, `parking_lot`, `gix-hashtable` |
| `streaming-input` | Support for receiving pack data as a stream | `parking_lot`, `gix-tempfile` |
| `pack-cache-lru-static` | Fixed-size allocation-free LRU cache for packs | `uluru` |
| `pack-cache-lru-dynamic` | Memory-cap-based LRU cache for packs | `clru` |
| `object-cache-dynamic` | Object caching for improved performance | `clru`, `gix-hashtable` |
| `serde` | Serialization/deserialization support | `serde`, `gix-object/serde` |
| `wasm` | WebAssembly target support | `gix-diff?/wasm` |

## Pack File Structure

### Data Pack Files

Pack data files (`.pack`) contain the actual Git objects in a compressed format:

1. **Header**: 12 bytes containing a signature ("PACK"), version, and object count
2. **Objects**: Sequence of Git objects, potentially delta-compressed
3. **Trailer**: Hash of all preceding content

Objects in the pack can be stored in three ways:
- **Base objects**: Complete objects stored with zlib compression
- **Offset deltas**: Objects stored as a delta against another object in the same pack
- **Reference deltas**: Objects stored as a delta against an object referenced by its hash

### Pack Indices

Pack index files (`.idx`) provide efficient lookup from object IDs to their locations in the pack:

1. **Header**: 8 bytes containing a signature and version
2. **Fan-out table**: 256 × 4-byte entries for efficient lookup based on first byte of hash
3. **Object IDs**: Sorted list of object IDs in the pack
4. **CRC-32 checksums**: CRC-32 values for each object in the pack
5. **Offsets**: Offsets into the pack file for each object
6. **Large offsets**: Additional space for offsets larger than 32 bits (version 2 only)
7. **Trailer**: Hash of the entire index

### Multi-Pack Indices

Multi-pack index files provide a unified index across multiple pack files:

1. **Header**: Signature ("MIDX"), version, and hash algorithm information
2. **Chunk offsets**: Offsets to different chunks within the file
3. **Pack file names**: Names of pack files included in the index
4. **Fan-out table**: Similar to pack indices
5. **Object IDs**: Sorted list of all object IDs
6. **Pack index mapping**: Maps each object to its pack file
7. **Offsets**: Offsets within each pack file
8. **Trailer**: Hash of the entire index

## Implementation Details

### Memory Mapping

The crate uses memory mapping (`memmap2`) to efficiently access pack files without loading them entirely into memory. This approach provides:
- Better performance by leveraging the operating system's virtual memory system
- Lower memory usage, as only accessed pages are loaded into memory
- Simplified file access through pointer-like operations

### Delta Compression

Pack files use delta compression to reduce size:

1. **Delta encoding**: Only the differences between objects are stored
2. **Delta chains**: Multiple deltas can form a chain (object A → delta B → delta C)
3. **Delta resolution**: Process of reconstructing the full object by applying deltas

The crate provides optimized delta resolution with caching to improve performance, particularly when working with large repositories.

### Cache Implementation

Several caching mechanisms are available:

1. **Static LRU cache**: Fixed-size cache for pack entries
2. **Dynamic LRU cache**: Memory-limited cache for pack entries
3. **Object cache**: Cache for fully resolved objects

These caches significantly improve performance for operations that repeatedly access the same objects, such as walking a commit history.

### Pack Generation

When the `generate` feature is enabled, the crate can create new pack files:

1. **Object collection**: Gathering objects to be packed
2. **Delta selection**: Determining which objects should be stored as deltas
3. **Sorting**: Arranging objects for optimal compression
4. **Encoding**: Writing objects to the pack file
5. **Index creation**: Building an index for the new pack

This process is optimized for both speed and the resulting pack size.

## Examples

### Reading Objects from a Pack File

```rust
use gix_pack::{bundle, data, index};
use gix_hash::ObjectId;
use std::path::Path;

// Open a pack file and its index
let pack_path = Path::new("objects/pack/pack-1234.pack");
let idx_path = Path::new("objects/pack/pack-1234.idx");

// Create a bundle for easier access
let bundle = bundle::init::from_path(pack_path, idx_path, 0, Default::default()).unwrap();

// Look up an object by its ID
let object_id = ObjectId::from_hex("abcdef1234567890abcdef1234567890abcdef12").unwrap();
let mut buffer = Vec::new();

// Try to find the object in the pack
if let Some((object, _)) = bundle.try_find(&object_id, &mut buffer).unwrap() {
    println!("Found object: kind={:?}, size={}", object.kind, object.data.len());
    // Use the object data...
}
```

### Verifying Pack Integrity

```rust
use gix_pack::{bundle, verify};
use std::path::Path;

// Open a pack file and its index
let pack_path = Path::new("objects/pack/pack-1234.pack");
let idx_path = Path::new("objects/pack/pack-1234.idx");
let bundle = bundle::init::from_path(pack_path, idx_path, 0, Default::default()).unwrap();

// Verify the pack integrity
let progress = gix_features::progress::DoOrDiscard::from(None);
match verify::pack_with_index(&bundle.pack, &bundle.index, progress) {
    Ok(_) => println!("Pack is valid!"),
    Err(err) => println!("Pack verification failed: {:?}", err),
}
```

### Working with Multi-Pack Indices

```rust
use gix_pack::multi_index;
use std::path::Path;

// Open a multi-pack index
let midx_path = Path::new("objects/pack/multi-pack-index");
let midx = multi_index::init::from_path(midx_path, Default::default()).unwrap();

// Get information about the index
println!("Multi-pack index contains {} objects across {} packs", 
    midx.num_objects(), midx.num_indices());

// List pack files included in the index
for pack_name in midx.index_names() {
    println!("Included pack: {}", pack_name.display());
}

// Verify the multi-pack index
let progress = gix_features::progress::DoOrDiscard::from(None);
match midx.verify(progress) {
    Ok(_) => println!("Multi-pack index is valid!"),
    Err(err) => println!("Multi-pack index verification failed: {:?}", err),
}
```

### Creating a New Pack (with "generate" feature)

```rust
use gix_pack::data::output;
use gix_object::Kind;
use std::fs::File;
use std::io::{BufWriter, Cursor};
use std::path::Path;

// Create a new pack file
let pack_path = Path::new("new-pack.pack");
let mut pack_file = BufWriter::new(File::create(pack_path).unwrap());

// Prepare objects to pack
let objects = vec![
    // (object_id, kind, data)
    (object_id1, Kind::Blob, data1),
    (object_id2, Kind::Commit, data2),
    // ...
];

// Generate object entries
let entries = output::entries_from_objects(&objects).unwrap();

// Write the pack file
let object_hash = gix_hash::Kind::Sha1;
output::write_pack(&mut pack_file, &entries, object_hash).unwrap();

// Generate and write the index file
let idx_path = Path::new("new-pack.idx");
let mut idx_file = BufWriter::new(File::create(idx_path).unwrap());
gix_pack::index::write::to_write(&mut idx_file, &entries, object_hash).unwrap();
```

## Testing Strategy

The crate is tested through a combination of:

1. **Unit tests**: Testing individual components in isolation
2. **Integration tests**: Testing the interaction between components
3. **Property tests**: Testing invariants that should hold for all valid inputs
4. **Compatibility tests**: Testing compatibility with Git's own pack files

A common testing approach is creating test fixtures that match real-world scenarios and comparing results with Git's behavior to ensure compatibility.