# gix-odb

## Overview

The `gix-odb` crate implements Git's object database (ODB), which is the storage layer for all Git objects. It provides abstractions for reading, writing, and iterating over objects in various storage formats, including loose objects, packfiles, and alternates.

This crate is a fundamental component of any Git implementation, as Git's data model relies on content-addressable storage where all objects (commits, trees, blobs, and tags) are identified by their content hash and stored in an object database.

## Architecture

The crate is structured around a central `Store` type that represents a complete Git object database. It's designed with the following principles:

1. **Zero-copy Reads**: Minimizes memory allocations when reading objects
2. **Lazy Loading**: Only loads indices and packs when needed
3. **Thread-safety**: Lock-free reading for perfect scaling across all cores
4. **Caching**: Per-thread caching of objects and pack information
5. **Auto-updates**: Ability to rescan for new objects when objects are not found

The architecture provides multiple abstraction layers:

- **High-level API**: `Store` and `Handle` for complete object database functionality
- **Mid-level API**: Specialized implementations for different storage types (loose, packed)
- **Low-level API**: Traits and interfaces for custom object database implementations

A key design feature is the use of thread-local handles and caches to maximize performance in multi-threaded environments without lock contention.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Store` | The main object database implementation | Central storage for all Git objects |
| `Handle` | Thread-local handle to access objects | Provides efficient access to the store with caching |
| `Cache` | Object and pack cache implementation | Caches Git objects and pack entries to improve performance |
| `Sink` | An object database that discards objects | Used when objects need to be processed but not stored |
| `memory::Proxy` | In-memory object database | Used for temporary storage or testing |
| `loose::Store` | Store for loose objects | Manages loose objects (one file per object) |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `find::Header` | Represents an object header | `Loose`, `Packed` |
| `store::RefreshMode` | Controls store refresh behavior | `AfterAllIndicesLoaded`, `Never` |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `Header` | Object header access | `Store`, `Handle`, `memory::Proxy` |
| `HeaderExt` | Extensions for `Header` | Automatically implemented for all `Header` implementors |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | Object ID computation and verification |
| `gix-object` | Git object parsing and representation |
| `gix-pack` | Pack file handling and manipulation |
| `gix-hashtable` | Efficient hash tables for object lookups |
| `gix-features` | Feature flags and utilities |
| `gix-date` | Date handling for pack index information |
| `gix-path` | Path handling for object storage locations |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `parking_lot` | Efficient mutex implementation |
| `arc-swap` | Lock-free atomic pointer swap |
| `tempfile` | Temporary file handling |
| `thiserror` | Error handling |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Adds serialization/deserialization support | `serde`, `gix-hash/serde`, `gix-object/serde`, `gix-pack/serde` |

## Git Object Storage Types

The `gix-odb` crate supports multiple storage types for Git objects:

### Loose Objects

Loose objects are individual files stored in the `.git/objects` directory, with filenames derived from their hash. For example, an object with the hash `abcd1234...` would be stored in `.git/objects/ab/cd1234...`.

The `loose::Store` component provides functionality to:
- Create and write loose objects
- Read loose objects
- Iterate over loose objects
- Verify loose object integrity

### Packfiles

Packfiles are compressed collections of multiple Git objects stored in a single file, with an accompanying index file for efficient lookups. They're stored in `.git/objects/pack/`.

The `store::Handle` component provides functionality to:
- Access objects within packfiles
- Load packfiles and indices on demand
- Cache frequently accessed objects
- Handle delta-compressed objects

### Alternates

The `alternate` module provides support for Git's alternates mechanism, which allows repositories to share objects by referencing object databases from other repositories. This is used in features like Git worktrees and submodules.

## Implementation Details

### Multi-threaded Access

The crate is designed for efficient access in multi-threaded environments:

- `Store` is thread-safe and allows concurrent access through multiple handles
- Each `Handle` maintains its own set of caches to prevent cache thrashing
- Pack indices and objects are loaded lazily to minimize memory usage
- A lock-free design ensures operations don't block each other

### Object Caching

Objects and pack entries are cached at multiple levels:

1. Thread-local object cache for fully decoded objects
2. Thread-local pack cache for base objects within packs
3. Pack index cache for object lookup acceleration

These caches significantly improve performance for operations that repeatedly access the same objects, such as walking a commit history.

### Store Updates

The `Store` can update itself when objects aren't found, to handle cases where another process has added objects to the database. This behavior is controlled by the `RefreshMode` enum:

- `AfterAllIndicesLoaded`: Refresh the store after all existing indices are loaded (default)
- `Never`: Never refresh the store, assuming all objects should be found in the current state

### Memory Management

The crate is designed to be memory-efficient:

- Objects are only loaded when needed
- Indices are loaded lazily
- The `memory::Proxy` provides an in-memory object database for temporary storage

## Examples

### Creating and Using an Object Database

```rust
use gix_odb::{self, Handle};
use std::path::Path;

// Open an object database at a specific location
let odb = gix_odb::at(Path::new(".git/objects")).unwrap();

// Read an object
let object_id = gix_hash::ObjectId::from_hex("1234567890123456789012345678901234567890").unwrap();
let mut buffer = Vec::new();
if let Some(object) = odb.try_find(&object_id, &mut buffer).unwrap() {
    println!("Found object: kind={:?}, size={}", object.kind, object.data.len());
}

// Check if an object exists
if odb.exists(&object_id) {
    println!("Object exists in the database");
}

// Get object header information
if let Some(header) = odb.try_header(&object_id).unwrap() {
    println!("Object kind: {:?}, size: {}", header.kind(), header.size());
}
```

### Writing Objects

```rust
use gix_odb::{self, Handle};
use gix_object::Kind;
use std::path::Path;
use std::io::Cursor;

// Open an object database
let odb = gix_odb::at(Path::new(".git/objects")).unwrap();

// Write a blob object
let data = b"Hello, world!";
let cursor = Cursor::new(data);
let object_id = odb.write_stream(Kind::Blob, data.len() as u64, &mut cursor.clone()).unwrap();

// Now we can read it back
let mut buffer = Vec::new();
let obj = odb.find(&object_id, &mut buffer).unwrap();
assert_eq!(obj.data, data);
```

### Using an In-Memory Object Database

```rust
use gix_odb::{self, memory::Proxy};
use gix_object::Kind;
use std::path::Path;
use std::io::Cursor;

// Open a real object database
let odb = gix_odb::at(Path::new(".git/objects")).unwrap();

// Create an in-memory proxy on top of it
let mut proxy_odb = Proxy::from(odb);

// Write an object (it will only exist in memory)
let data = b"Temporary data";
let cursor = Cursor::new(data);
let object_id = proxy_odb.write_stream(Kind::Blob, data.len() as u64, &mut cursor.clone()).unwrap();

// Access the object from memory
let mut buffer = Vec::new();
let obj = proxy_odb.find(&object_id, &mut buffer).unwrap();
assert_eq!(obj.data, data);

// The object doesn't exist in the underlying database
assert!(!proxy_odb.inner.exists(&object_id));

// We can retrieve and manage the in-memory objects
let storage = proxy_odb.take_object_memory().unwrap();
println!("Number of in-memory objects: {}", storage.len());
```

### Advanced Handle Configuration

```rust
use gix_odb::{self, store};
use std::path::Path;

// Create a handle with custom options
let odb = gix_odb::at_opts(
    Path::new(".git/objects"),
    vec![], // No replacements
    store::init::Options {
        object_hash: gix_hash::Kind::Sha1,
        slots: store::init::Slots::Given {
            multi_pack_index: store::init::Slot::Load,
            packs: store::init::Slot::Load,
            indices: store::init::Slot::Load,
        },
        use_multi_pack_index: true,
        ..Default::default()
    }
).unwrap();

// Configure the handle to never refresh
odb.refresh = store::RefreshMode::Never;

// Set a maximum recursion depth for delta resolution
odb.max_recursion_depth = 50;
```

## Testing Strategy

The crate is tested through a combination of:

1. **Unit tests**: Testing individual components in isolation
2. **Integration tests**: Testing the interaction between components
3. **Property tests**: Testing invariants that should hold for all valid inputs
4. **Compatibility tests**: Testing compatibility with Git's own object database

A common testing approach is using the `memory::Proxy` to create isolated test environments that don't depend on the filesystem.