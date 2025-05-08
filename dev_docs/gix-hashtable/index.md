# gix-hashtable

## Overview

`gix-hashtable` is a specialized crate in the gitoxide ecosystem that provides hash table implementations optimized specifically for Git object IDs. It offers customized `HashMap` and `HashSet` types that leverage the properties of Git object identifiers (which are already secure hashes) to achieve better performance with less overhead when compared to standard hash collections.

The crate provides both thread-safe and non-thread-safe variants of its collections, making it suitable for various use cases within the gitoxide ecosystem, from single-threaded object lookups to multi-threaded concurrent operations.

## Architecture

`gix-hashtable` follows a focused design that builds upon existing hash table implementations to optimize for the specific case of Git object IDs:

### Core Design Principles

1. **Optimized for ObjectId Keys** - The hash functions and data structures are specifically optimized for Git object IDs, taking advantage of their properties as already-robust hash values.

2. **Zero Hash Overhead** - Since Git object IDs are already high-quality hashes, the hasher implementation simply uses the first 8 bytes of the ID directly, avoiding the need to compute additional hash values.

3. **Thread Safety When Needed** - Provides both thread-safe and non-thread-safe variants to suit different usage scenarios without imposing unnecessary overhead.

4. **Familiar API** - Mirrors the standard library's collection interfaces for ease of use and familiarity.

### Module Structure

The crate is organized into focused modules:

- **lib.rs** - Main entry point that re-exports the data structures and contains the primary hash table type definitions
- **hash** - Contains the specialized hasher implementation optimized for object IDs
- **sync** - Provides thread-safe variants of the hash collections using sharding for concurrent access

## Core Components

### Type Aliases

| Type Alias | Description | Usage |
|------------|-------------|-------|
| `HashMap<K, V>` | A specialized hash map that uses a custom hasher optimized for object IDs | Used for associating data with Git objects in a high-performance manner |
| `HashSet<T = ObjectId>` | A specialized hash set that uses a custom hasher optimized for object IDs | Used for tracking collections of unique object IDs efficiently |

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `sync::ObjectIdMap<V>` | A thread-safe map for associating data with object IDs | Used in multi-threaded contexts to store and retrieve values by object ID |
| `hash::Hasher` | A custom hasher implementation optimized for object IDs | Used internally by the hash collections to compute hash values |
| `hash::Builder` | A hasher builder that creates instances of the custom hasher | Used by the hash collections to create new hashers when needed |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | Provides the `ObjectId` type that the hash tables are optimized for |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `hashbrown` | Provides the underlying high-performance hash table implementation |
| `parking_lot` | Offers efficient mutex implementations for the thread-safe collections |

## Feature Flags

The `gix-hashtable` crate doesn't define any specific feature flags of its own. It inherits the features from its dependencies, particularly `gix-hash`.

## Examples

```rust
use gix_hash::ObjectId;
use gix_hashtable::HashMap;

// Create a new object ID hash map
let mut objects = HashMap::default();

// Create an object ID
let id = ObjectId::from_hex("7f0b2d3f6a9d1e4c2b5a8c7d6e3f2a1b0c9d8e7f").unwrap();

// Store a value by object ID
objects.insert(id, "commit data");

// Lookup a value
assert_eq!(objects.get(&id), Some(&"commit data"));
```

For thread-safe operations:

```rust
use gix_hash::ObjectId;
use gix_hashtable::sync::ObjectIdMap;

// Create a thread-safe object ID map
let objects = ObjectIdMap::default();

// Create an object ID
let id = ObjectId::from_hex("7f0b2d3f6a9d1e4c2b5a8c7d6e3f2a1b0c9d8e7f").unwrap();

// Store a value
objects.insert(id, "commit data");
```

## Implementation Details

### Optimized Hashing

The core optimization in `gix-hashtable` is its approach to hashing Git object IDs. Since Git object IDs are already high-quality cryptographic hashes, the custom hasher simply uses the first 8 bytes of the object ID directly as the hash value:

```rust
impl std::hash::Hasher for Hasher {
    #[inline(always)]
    fn write(&mut self, bytes: &[u8]) {
        self.0 = u64::from_ne_bytes(bytes[..8].try_into().unwrap());
    }
    
    fn finish(&self) -> u64 {
        self.0
    }
}
```

This avoids the overhead of running the bytes through another hash function and is extremely fast since it's just a memory copy operation. It works well because Git object IDs are already high-quality, well-distributed hash values.

### Sharding for Thread Safety

The thread-safe `ObjectIdMap` uses a simple but effective sharding strategy based on the first byte of the object ID:

```rust
pub struct ObjectIdMap<V> {
    shards: [parking_lot::Mutex<super::HashMap<gix_hash::ObjectId, V>>; 256],
}
```

This creates 256 separate hash maps, each protected by its own mutex. The first byte of the object ID determines which shard to use:

```rust
self.shards[key.as_slice()[0] as usize].lock().insert(key, value)
```

This approach allows up to 256 threads to operate concurrently on different shards, minimizing lock contention since Git object IDs should be well-distributed.

### Safety Considerations

The custom hasher is designed to be used only with specific types that have manually verified hash implementations. Any attempt to use other hash methods will panic:

```rust
macro_rules! panic_other_writers {
    ($func:ident, $type:ty) => {
        #[cold]
        fn $func(&mut self, _i: $type) {
            panic!("This hasher only supports manually verified `Hash` implementations")
        }
    };
}
```

This ensures that the hasher is only used with types that are known to work correctly with it, preventing silent bugs in unexpected contexts.

## Testing Strategy

The crate includes tests that verify the behavior of the custom hasher implementation:

- Verifies that the hasher correctly uses the first 8 bytes of input as the hash value
- Confirms that attempts to use unsupported hasher methods result in panics

This testing approach ensures that the core optimization strategy works as expected and that the safety measures are effective.