# gix-bitmap Use Cases

This document outlines the primary use cases for the `gix-bitmap` crate, including target audiences, problems solved, and example code demonstrating solutions.

## Intended Audience

- Git implementation developers
- Developers working on space-efficient data structures
- Contributors to the gitoxide ecosystem
- Developers needing bitmap compression in Rust

## Use Cases

### 1. Efficient Storage of Git Index Information

**Problem**: Git needs to store information about file states in its index, but storing individual flags for each file would be inefficient, especially for repositories with many files.

**Solution**: Use EWAH bitmaps to efficiently encode sets of flags or properties.

```rust
use gix_bitmap::ewah;

// Example: Decoding directory flags from Git index untracked cache extension
fn decode_directory_flags(data: &[u8]) -> Result<Vec<DirectoryEntry>, Box<dyn std::error::Error>> {
    // Parse basic directory information first...
    let mut directories = Vec::with_capacity(100);
    
    // ...directory parsing code here...
    
    // Now parse the bitmaps that define various properties
    let (valid_bitmap, data) = ewah::decode(data)?;
    let (check_only_bitmap, data) = ewah::decode(data)?;
    let (hash_valid_bitmap, mut data) = ewah::decode(data)?;
    
    // Apply the valid flag to directories
    valid_bitmap.for_each_set_bit(|index| {
        if index < directories.len() {
            // Parse additional data for valid directories
            // For example, stat information
            let (stat, rest) = parse_stat_info(data)?;
            directories[index].stat = Some(stat);
            data = rest;
        }
        Some(())
    });
    
    // Apply the check_only flag
    check_only_bitmap.for_each_set_bit(|index| {
        if index < directories.len() {
            directories[index].check_only = true;
        }
        Some(())
    });
    
    // Process directories with valid hashes
    hash_valid_bitmap.for_each_set_bit(|index| {
        if index < directories.len() {
            // Parse hash data
            let (hash, rest) = extract_hash(data)?;
            directories[index].hash = Some(hash);
            data = rest;
        }
        Some(())
    });
    
    Ok(directories)
}

// Helper functions for the example
fn parse_stat_info(data: &[u8]) -> Result<(StatInfo, &[u8]), Box<dyn std::error::Error>> {
    // Implementation would parse file stat information
    // Simplified for example
    Ok((StatInfo {}, data))
}

fn extract_hash(data: &[u8]) -> Result<(Hash, &[u8]), Box<dyn std::error::Error>> {
    // Implementation would extract hash data
    // Simplified for example
    Ok((Hash {}, data))
}

struct DirectoryEntry {
    path: String,
    stat: Option<StatInfo>,
    check_only: bool,
    hash: Option<Hash>,
}

struct StatInfo {}
struct Hash {}
```

### 2. Tracking Object Reachability in Pack Files

**Problem**: Git needs to track which objects are reachable from specific commits to optimize operations like fetching and cloning.

**Solution**: Use bitmaps to efficiently represent sets of reachable objects.

```rust
use gix_bitmap::ewah;
use gix_hash::ObjectId;

struct CommitReachability {
    commit_id: ObjectId,
    reachable_objects: ReachabilityBitmap,
}

struct ReachabilityBitmap {
    bitmap: ewah::Vec,
    object_position_map: Vec<ObjectId>, // Maps bit positions to object IDs
}

impl ReachabilityBitmap {
    fn decode_from(data: &[u8]) -> Result<(Self, &[u8]), Box<dyn std::error::Error>> {
        // Decode the bitmap
        let (bitmap, remaining) = ewah::decode(data)?;
        
        // In a real implementation, we would also decode the object position map
        // from the remaining data. Simplified for this example.
        let object_position_map = Vec::new();
        
        Ok((
            Self {
                bitmap,
                object_position_map,
            },
            remaining
        ))
    }
    
    // Check if a specific object is reachable
    fn contains(&self, object_id: &ObjectId) -> bool {
        // Find the position of this object ID in the position map
        if let Some(position) = self.find_position(object_id) {
            // Create a wrapper to check the bit
            let mut result = false;
            self.bitmap.for_each_set_bit(|bit_index| {
                if bit_index == position {
                    result = true;
                    None  // Stop iteration once found
                } else {
                    Some(()) // Continue looking
                }
            });
            result
        } else {
            false
        }
    }
    
    // Get all reachable objects
    fn get_all_reachable(&self) -> Vec<ObjectId> {
        let mut result = Vec::new();
        
        self.bitmap.for_each_set_bit(|bit_index| {
            if bit_index < self.object_position_map.len() {
                result.push(self.object_position_map[bit_index].clone());
            }
            Some(())
        });
        
        result
    }
    
    // Helper to find an object's position
    fn find_position(&self, object_id: &ObjectId) -> Option<usize> {
        self.object_position_map.iter().position(|id| id == object_id)
    }
}
```

### 3. Implementing Sparse Checkouts

**Problem**: When users want to check out only a subset of files from a large repository, Git needs an efficient way to track which paths are included in the sparse checkout.

**Solution**: Use bitmaps to represent which paths are included in the sparse checkout pattern.

```rust
use gix_bitmap::ewah;
use std::path::Path;

struct SparseCheckout {
    // Bitmap where each bit represents a path in the repository
    included_paths: ewah::Vec,
    // Map of paths to their indices in the bitmap
    path_to_index: std::collections::HashMap<String, usize>,
}

impl SparseCheckout {
    // In a real implementation, this would decode from the sparse-checkout file
    fn decode_from(data: &[u8]) -> Result<Self, Box<dyn std::error::Error>> {
        let (bitmap, _) = ewah::decode(data)?;
        
        // The path mapping would also be decoded from the data
        // Simplified for this example
        let path_to_index = std::collections::HashMap::new();
        
        Ok(Self {
            included_paths: bitmap,
            path_to_index,
        })
    }
    
    // Check if a path is included in the sparse checkout
    fn is_path_included(&self, path: &str) -> bool {
        if let Some(index) = self.path_to_index.get(path) {
            let mut result = false;
            self.included_paths.for_each_set_bit(|bit_index| {
                if bit_index == *index {
                    result = true;
                    None  // Stop iteration
                } else {
                    Some(()) // Continue
                }
            });
            result
        } else {
            false // Path not known
        }
    }
    
    // Get all included paths
    fn get_all_included_paths(&self) -> Vec<String> {
        let mut result = Vec::new();
        let mut index_to_path = vec![String::new(); self.path_to_index.len()];
        
        // Invert the path_to_index map
        for (path, &index) in &self.path_to_index {
            if index < index_to_path.len() {
                index_to_path[index] = path.clone();
            }
        }
        
        // Collect all included paths
        self.included_paths.for_each_set_bit(|bit_index| {
            if bit_index < index_to_path.len() {
                result.push(index_to_path[bit_index].clone());
            }
            Some(())
        });
        
        result
    }
}
```

### 4. Efficiently Tracking Changed Files

**Problem**: Git needs to efficiently track which files have changed between revisions to optimize operations like status, diff, and commit.

**Solution**: Use bitmaps to represent sets of changed files.

```rust
use gix_bitmap::ewah;

struct ChangedFiles {
    // Bitmap where each bit represents a file in the repository
    changed: ewah::Vec,
    // Map of files to their indices in the bitmap
    file_to_index: std::collections::HashMap<String, usize>,
}

impl ChangedFiles {
    fn decode_from(data: &[u8]) -> Result<Self, Box<dyn std::error::Error>> {
        let (bitmap, _) = ewah::decode(data)?;
        
        // The file mapping would also be decoded from the data
        // Simplified for this example
        let file_to_index = std::collections::HashMap::new();
        
        Ok(Self {
            changed: bitmap,
            file_to_index,
        })
    }
    
    // Check if a file has changed
    fn is_file_changed(&self, file_path: &str) -> bool {
        if let Some(index) = self.file_to_index.get(file_path) {
            let mut result = false;
            self.changed.for_each_set_bit(|bit_index| {
                if bit_index == *index {
                    result = true;
                    None  // Stop iteration
                } else {
                    Some(()) // Continue
                }
            });
            result
        } else {
            false // File not known
        }
    }
    
    // Get all changed files
    fn get_all_changed_files(&self) -> Vec<String> {
        let mut result = Vec::new();
        let mut index_to_file = vec![String::new(); self.file_to_index.len()];
        
        // Invert the file_to_index map
        for (file, &index) in &self.file_to_index {
            if index < index_to_file.len() {
                index_to_file[index] = file.clone();
            }
        }
        
        // Collect all changed files
        self.changed.for_each_set_bit(|bit_index| {
            if bit_index < index_to_file.len() {
                result.push(index_to_file[bit_index].clone());
            }
            Some(())
        });
        
        result
    }
}
```

### 5. Implementing Efficient Filters for Content Search

**Problem**: When searching through repository content, Git needs to quickly filter out irrelevant files and focus on potentially matching files.

**Solution**: Use bitmaps as Bloom filters to efficiently pre-filter files that might contain the search terms.

```rust
use gix_bitmap::ewah;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

struct BloomFilter {
    // The bitmap representing the Bloom filter
    bitmap: ewah::Vec,
    // Number of hash functions used
    num_hash_functions: usize,
}

impl BloomFilter {
    // Create a new Bloom filter from a bitmap
    fn new(bitmap: ewah::Vec, num_hash_functions: usize) -> Self {
        Self {
            bitmap,
            num_hash_functions,
        }
    }
    
    // Decode a Bloom filter from binary data
    fn decode_from(data: &[u8], num_hash_functions: usize) -> Result<Self, Box<dyn std::error::Error>> {
        let (bitmap, _) = ewah::decode(data)?;
        Ok(Self::new(bitmap, num_hash_functions))
    }
    
    // Check if an element might be in the set
    // Bloom filters can have false positives but not false negatives
    fn might_contain<T: Hash>(&self, item: &T) -> bool {
        let bitmap_size = self.bitmap.num_bits();
        if bitmap_size == 0 {
            return false;
        }
        
        for i in 0..self.num_hash_functions {
            let bit_index = self.hash_item(item, i) % bitmap_size;
            
            // Check if this bit is set
            let mut is_set = false;
            self.bitmap.for_each_set_bit(|index| {
                if index == bit_index {
                    is_set = true;
                    None  // Stop iteration
                } else {
                    Some(()) // Continue
                }
            });
            
            if !is_set {
                return false; // If any bit is not set, the item is definitely not in the set
            }
        }
        
        true // All bits were set, so the item might be in the set
    }
    
    // Hash an item with a specific seed
    fn hash_item<T: Hash>(&self, item: &T, seed: usize) -> usize {
        let mut hasher = DefaultHasher::new();
        seed.hash(&mut hasher);
        item.hash(&mut hasher);
        hasher.finish() as usize
    }
}

// Example usage for content search
fn filter_files_for_search(
    files: &[String],
    search_term: &str,
    bloom_filter_data: &[u8]
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Decode the Bloom filter
    let bloom_filter = BloomFilter::decode_from(bloom_filter_data, 3)?;
    
    // Filter files that might contain the search term
    let possible_matches: Vec<String> = files
        .iter()
        .filter(|file| bloom_filter.might_contain(file))
        .cloned()
        .collect();
    
    Ok(possible_matches)
}
```

## Integration Examples

### Integrating with Git Index for File Tracking

This example shows how to integrate `gix-bitmap` with the Git index functionality to track file status:

```rust
use gix_bitmap::ewah;

// This is a simplified version of how Git might use bitmaps in its index
struct IndexExtension {
    // Various bitmaps for tracking file status
    untracked_files_bitmap: ewah::Vec,
    modified_files_bitmap: ewah::Vec,
    assume_unchanged_bitmap: ewah::Vec,
    
    // File to index mapping
    file_to_index: std::collections::HashMap<String, usize>,
}

impl IndexExtension {
    fn decode_from(data: &[u8]) -> Result<Self, Box<dyn std::error::Error>> {
        // Decode each bitmap in sequence
        let (untracked_files_bitmap, data) = ewah::decode(data)?;
        let (modified_files_bitmap, data) = ewah::decode(data)?;
        let (assume_unchanged_bitmap, _) = ewah::decode(data)?;
        
        // In a real implementation, we would also decode the file mapping
        let file_to_index = std::collections::HashMap::new();
        
        Ok(Self {
            untracked_files_bitmap,
            modified_files_bitmap,
            assume_unchanged_bitmap,
            file_to_index,
        })
    }
    
    fn is_file_untracked(&self, file_path: &str) -> bool {
        self.check_file_bitmap(file_path, &self.untracked_files_bitmap)
    }
    
    fn is_file_modified(&self, file_path: &str) -> bool {
        self.check_file_bitmap(file_path, &self.modified_files_bitmap)
    }
    
    fn is_assume_unchanged(&self, file_path: &str) -> bool {
        self.check_file_bitmap(file_path, &self.assume_unchanged_bitmap)
    }
    
    fn check_file_bitmap(&self, file_path: &str, bitmap: &ewah::Vec) -> bool {
        if let Some(index) = self.file_to_index.get(file_path) {
            let mut result = false;
            bitmap.for_each_set_bit(|bit_index| {
                if bit_index == *index {
                    result = true;
                    None  // Stop iteration
                } else {
                    Some(()) // Continue
                }
            });
            result
        } else {
            false  // File not in index
        }
    }
    
    // Get all files matching a certain condition
    fn get_files_by_condition(&self, bitmap: &ewah::Vec) -> Vec<String> {
        let mut result = Vec::new();
        let mut index_to_file = vec![String::new(); self.file_to_index.len()];
        
        // Invert the mapping for lookup
        for (file, &index) in &self.file_to_index {
            if index < index_to_file.len() {
                index_to_file[index] = file.clone();
            }
        }
        
        // Collect all matching files
        bitmap.for_each_set_bit(|bit_index| {
            if bit_index < index_to_file.len() {
                result.push(index_to_file[bit_index].clone());
            }
            Some(())
        });
        
        result
    }
    
    // Get all untracked files
    fn get_untracked_files(&self) -> Vec<String> {
        self.get_files_by_condition(&self.untracked_files_bitmap)
    }
    
    // Get all modified files
    fn get_modified_files(&self) -> Vec<String> {
        self.get_files_by_condition(&self.modified_files_bitmap)
    }
}
```

### Implementing a Commit Graph with Reachability Information

This example shows how bitmaps could be used to implement an efficient commit graph with reachability information:

```rust
use gix_bitmap::ewah;
use gix_hash::ObjectId;
use std::collections::HashMap;

struct CommitGraph {
    // Map from commit ID to its position in the graph
    commit_to_position: HashMap<ObjectId, usize>,
    // Array of commit metadata (parent information, etc.)
    commits: Vec<CommitMetadata>,
    // Reachability bitmaps for selected commits
    reachability: HashMap<ObjectId, ewah::Vec>,
}

struct CommitMetadata {
    id: ObjectId,
    parents: Vec<usize>, // Positions of parent commits in the graph
    // Other metadata...
}

impl CommitGraph {
    fn decode_from(data: &[u8]) -> Result<Self, Box<dyn std::error::Error>> {
        // In a real implementation, we would decode the commit graph structure
        // For simplicity, we'll create an empty graph
        let commit_to_position = HashMap::new();
        let commits = Vec::new();
        let reachability = HashMap::new();
        
        Ok(Self {
            commit_to_position,
            commits,
            reachability,
        })
    }
    
    // Check if commit B is reachable from commit A
    fn is_reachable(&self, from_commit: &ObjectId, to_commit: &ObjectId) -> bool {
        // If we have a reachability bitmap for the "from" commit, use it
        if let Some(bitmap) = self.reachability.get(from_commit) {
            if let Some(position) = self.commit_to_position.get(to_commit) {
                let mut result = false;
                bitmap.for_each_set_bit(|bit_index| {
                    if bit_index == *position {
                        result = true;
                        None  // Stop iteration
                    } else {
                        Some(()) // Continue
                    }
                });
                return result;
            }
        }
        
        // Fallback to graph traversal if we don't have a bitmap
        self.is_reachable_by_traversal(from_commit, to_commit)
    }
    
    // Fallback method using graph traversal
    fn is_reachable_by_traversal(&self, from_commit: &ObjectId, to_commit: &ObjectId) -> bool {
        // This would implement a graph traversal algorithm
        // Simplified for this example
        false
    }
    
    // Get all commits reachable from a given commit
    fn get_reachable_commits(&self, from_commit: &ObjectId) -> Vec<ObjectId> {
        if let Some(bitmap) = self.reachability.get(from_commit) {
            let mut result = Vec::new();
            
            bitmap.for_each_set_bit(|bit_index| {
                if bit_index < self.commits.len() {
                    result.push(self.commits[bit_index].id.clone());
                }
                Some(())
            });
            
            result
        } else {
            // Fallback if no bitmap exists
            self.get_reachable_commits_by_traversal(from_commit)
        }
    }
    
    // Fallback method using graph traversal
    fn get_reachable_commits_by_traversal(&self, from_commit: &ObjectId) -> Vec<ObjectId> {
        // This would implement a graph traversal algorithm
        // Simplified for this example
        Vec::new()
    }
}
```