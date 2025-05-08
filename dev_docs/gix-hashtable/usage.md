# gix-hashtable Usage Guide

This document provides detailed examples and use cases for the `gix-hashtable` crate, demonstrating how its specialized hash collections can be used effectively in Git-related applications.

## Common Use Cases

### 1. Object Deduplication

**Use Case**: Efficiently tracking which Git objects have already been processed to avoid duplicate work.

**Users**:
- Object database implementations
- Pack file generators
- Object traversal algorithms

**Example**:
```rust
use gix_hash::ObjectId;
use gix_hashtable::HashSet;

struct ObjectProcessor {
    // Track objects we've already seen
    processed_objects: HashSet,
}

impl ObjectProcessor {
    fn new() -> Self {
        Self {
            processed_objects: HashSet::default(),
        }
    }
    
    fn process_object(&mut self, id: ObjectId, data: &[u8]) -> bool {
        // If we've already processed this object, don't do it again
        if self.processed_objects.contains(&id) {
            return false;
        }
        
        // Process the object...
        // ...
        
        // Mark as processed
        self.processed_objects.insert(id);
        true
    }
    
    fn stats(&self) -> usize {
        self.processed_objects.len()
    }
}
```

### 2. Object Caching

**Use Case**: Maintaining a high-performance cache of recently accessed Git objects.

**Users**:
- Repository implementations
- Object databases
- Git operations that repeatedly access the same objects

**Example**:
```rust
use gix_hash::ObjectId;
use gix_hashtable::HashMap;

struct ObjectCache {
    // Store object data by ID
    objects: HashMap<ObjectId, Vec<u8>>,
    // Track cache size
    current_size: usize,
    max_size: usize,
}

impl ObjectCache {
    fn new(max_size_bytes: usize) -> Self {
        Self {
            objects: HashMap::default(),
            current_size: 0,
            max_size: max_size_bytes,
        }
    }
    
    fn get(&self, id: &ObjectId) -> Option<&[u8]> {
        self.objects.get(id).map(|v| v.as_slice())
    }
    
    fn insert(&mut self, id: ObjectId, data: Vec<u8>) {
        let data_size = data.len();
        
        // Ensure we have space
        if self.current_size + data_size > self.max_size {
            // Simple strategy: clear cache if we would exceed limit
            self.objects.clear();
            self.current_size = 0;
        }
        
        self.objects.insert(id, data);
        self.current_size += data_size;
    }
}
```

### 3. Concurrent Object Processing

**Use Case**: Processing Git objects in parallel while maintaining shared state.

**Users**:
- Multi-threaded Git operations
- Parallel repository scanners
- Background object compression/decompression

**Example**:
```rust
use std::sync::Arc;
use std::thread;
use gix_hash::ObjectId;
use gix_hashtable::sync::ObjectIdMap;

struct ParallelProcessor {
    // Thread-safe map to track processing status
    object_status: Arc<ObjectIdMap<ProcessingStatus>>,
}

enum ProcessingStatus {
    Queued,
    Processing,
    Completed,
    Failed,
}

impl ParallelProcessor {
    fn new() -> Self {
        Self {
            object_status: Arc::new(ObjectIdMap::default()),
        }
    }
    
    fn process_batch(&self, object_ids: Vec<ObjectId>) {
        // Queue all objects
        for id in &object_ids {
            self.object_status.insert(*id, ProcessingStatus::Queued);
        }
        
        // Process in parallel
        let mut handles = Vec::new();
        for chunk in object_ids.chunks(10) {
            let ids = chunk.to_vec();
            let status_map = Arc::clone(&self.object_status);
            
            let handle = thread::spawn(move || {
                for id in ids {
                    // Update status to processing
                    status_map.insert(id, ProcessingStatus::Processing);
                    
                    // Perform actual processing
                    match process_single_object(id) {
                        Ok(_) => {
                            status_map.insert(id, ProcessingStatus::Completed);
                        }
                        Err(_) => {
                            status_map.insert(id, ProcessingStatus::Failed);
                        }
                    }
                }
            });
            
            handles.push(handle);
        }
        
        // Wait for all threads to complete
        for handle in handles {
            handle.join().unwrap();
        }
    }
}

fn process_single_object(id: ObjectId) -> Result<(), ()> {
    // Simulated processing
    Ok(())
}
```

### 4. Delta Compression Analysis

**Use Case**: Identifying similar objects for delta compression by tracking objects by their prefix.

**Users**:
- Pack file generators
- Repository optimizers
- Git garbage collection tools

**Example**:
```rust
use gix_hash::ObjectId;
use gix_hashtable::HashMap;

struct DeltaCompressor {
    // Group objects by their first 2 bytes to find potential delta candidates
    prefix_groups: HashMap<[u8; 2], Vec<ObjectId>>,
}

impl DeltaCompressor {
    fn new() -> Self {
        Self {
            prefix_groups: HashMap::default(),
        }
    }
    
    fn add_object(&mut self, id: ObjectId) {
        // Extract first 2 bytes as prefix
        let prefix = [id.as_slice()[0], id.as_slice()[1]];
        
        // Add to the appropriate group
        self.prefix_groups.entry(prefix)
            .or_insert_with(Vec::new)
            .push(id);
    }
    
    fn find_delta_candidates(&self, id: &ObjectId) -> Vec<ObjectId> {
        // Get first 2 bytes
        let prefix = [id.as_slice()[0], id.as_slice()[1]];
        
        // Return other objects with same prefix
        self.prefix_groups.get(&prefix)
            .map(|group| {
                group.iter()
                     .filter(|candidate_id| *candidate_id != id)
                     .copied()
                     .collect()
            })
            .unwrap_or_default()
    }
}
```

## Advanced Usage Patterns

### Hybrid Caching Strategy

This example demonstrates a more sophisticated caching strategy that uses both non-thread-safe and thread-safe collections for different phases of operation:

```rust
use std::sync::Arc;
use gix_hash::ObjectId;
use gix_hashtable::{HashMap, HashSet};
use gix_hashtable::sync::ObjectIdMap;

struct HybridObjectCache {
    // Fast, single-threaded cache for the preparation phase
    preparation_cache: HashMap<ObjectId, Vec<u8>>,
    
    // Thread-safe cache for the parallel processing phase
    shared_cache: Arc<ObjectIdMap<Vec<u8>>>,
    
    // Single-threaded set of objects that were fully processed
    completed_objects: HashSet,
}

impl HybridObjectCache {
    fn new() -> Self {
        Self {
            preparation_cache: HashMap::default(),
            shared_cache: Arc::new(ObjectIdMap::default()),
            completed_objects: HashSet::default(),
        }
    }
    
    // Single-threaded preparation phase
    fn prepare_object(&mut self, id: ObjectId, data: Vec<u8>) {
        self.preparation_cache.insert(id, data);
    }
    
    // Transition to multi-threaded processing
    fn prepare_for_parallel_processing(&mut self) {
        // Move all prepared objects to the shared cache
        for (id, data) in self.preparation_cache.drain() {
            self.shared_cache.insert(id, data);
        }
    }
    
    // Mark as fully processed (back in single-threaded mode)
    fn mark_completed(&mut self, id: ObjectId) {
        self.completed_objects.insert(id);
    }
    
    // Check completion status (single-threaded)
    fn is_completed(&self, id: &ObjectId) -> bool {
        self.completed_objects.contains(id)
    }
}
```

### Custom Key Type with ObjectId

This example shows how to implement a custom key type that contains an ObjectId and works efficiently with the specialized hasher:

```rust
use std::hash::{Hash, Hasher};
use gix_hash::ObjectId;
use gix_hashtable::HashMap;

// A custom key type that includes an ObjectId and a path
#[derive(Eq, PartialEq, Clone)]
struct ObjectWithPath {
    id: ObjectId,
    path: String,
}

// Custom Hash implementation that delegates to the ObjectId,
// which is compatible with gix-hashtable's optimized hasher
impl Hash for ObjectWithPath {
    fn hash<H: Hasher>(&self, state: &mut H) {
        // Just use the ObjectId for hashing
        self.id.hash(state);
    }
}

fn main() {
    // Create a map using our custom key type
    let mut object_map = HashMap::default();
    
    // Create a key with an ObjectId and a path
    let id = ObjectId::from_hex("7f0b2d3f6a9d1e4c2b5a8c7d6e3f2a1b0c9d8e7f").unwrap();
    let key = ObjectWithPath {
        id,
        path: "src/main.rs".to_string(),
    };
    
    // Insert into the map
    object_map.insert(key.clone(), "file content");
    
    // Retrieve from the map
    assert_eq!(object_map.get(&key), Some(&"file content"));
}
```

### Temporary Object Tracking

This pattern is useful for tracking temporary objects during complex Git operations:

```rust
use gix_hash::ObjectId;
use gix_hashtable::{HashMap, HashSet};

struct TemporaryObjectTracker {
    // Track object dependencies
    dependencies: HashMap<ObjectId, HashSet>,
    
    // Track temporary objects we can delete when no longer needed
    temporary_objects: HashSet,
}

impl TemporaryObjectTracker {
    fn new() -> Self {
        Self {
            dependencies: HashMap::default(),
            temporary_objects: HashSet::default(),
        }
    }
    
    fn add_temporary_object(&mut self, id: ObjectId) {
        self.temporary_objects.insert(id);
    }
    
    fn add_dependency(&mut self, object: ObjectId, depends_on: ObjectId) {
        self.dependencies
            .entry(depends_on)
            .or_insert_with(HashSet::default)
            .insert(object);
    }
    
    fn remove_object(&mut self, id: &ObjectId) {
        // Remove the object itself
        self.temporary_objects.remove(id);
        
        // Get objects that depended on this one
        if let Some(dependents) = self.dependencies.remove(id) {
            // Recursively remove those objects too
            for dependent in dependents {
                self.remove_object(&dependent);
            }
        }
    }
    
    fn cleanup(&mut self) {
        // Clear all temporary objects
        self.temporary_objects.clear();
        self.dependencies.clear();
    }
}
```

## Performance Considerations

### When to Use Thread-safe vs. Non-thread-safe Collections

- **Use non-thread-safe collections (`HashMap`, `HashSet`):**
  - For single-threaded code paths
  - When the collection is only accessed by one thread at a time
  - When maximum performance is needed

- **Use thread-safe collections (`sync::ObjectIdMap`):**
  - When multiple threads need concurrent access to the same collection
  - When the collection is shared across thread boundaries
  - When you need to avoid the overhead of mutex locking around an entire collection

### Memory vs. Performance Tradeoffs

The shard-based approach in `ObjectIdMap` requires 256 separate hash maps and mutexes, which can use more memory than a single map with a global lock. Consider these tradeoffs:

- If memory usage is a concern, but you still need thread safety, consider using a standard `HashMap` protected by a single mutex
- If you have many concurrent threads and performance is critical, the sharded approach in `ObjectIdMap` will provide better scalability
- For very small maps (less than a few dozen entries), the overhead of 256 shards might not be worth it

### Custom Hasher Limitations

Remember that the specialized hasher in `gix-hashtable` is designed specifically for object IDs and similar types. It will panic if used with types that hash using methods other than `write()`.

When using custom key types:
- Ensure they implement `Hash` by delegating to an `ObjectId` field
- Avoid complex custom hash implementations
- Consider deriving `Eq` and `PartialEq` based on the same field(s) used for hashing

## Integration with Other Gitoxide Components

`gix-hashtable` is designed to work seamlessly with other parts of the gitoxide ecosystem:

- **With `gix-hash`**: The primary use case, providing optimized collections for `ObjectId` keys
- **With `gix-object`**: For caching and deduplicating Git objects
- **With `gix-pack`**: For efficiently tracking objects during pack file operations
- **With `gix-odb`**: For implementing high-performance object databases

When building Git tools with gitoxide, consider using `gix-hashtable` whenever you need to store or look up data by `ObjectId`.