# gix-revwalk Use Cases

This document outlines common use cases for the `gix-revwalk` crate and provides code examples demonstrating how to use it effectively.

## Intended Audience

- Rust developers working with Git internals
- Contributors to gitoxide who need to traverse commit history
- Developers building Git tools that need efficient commit graph traversal
- Users of the gitoxide library who need to analyze repository history

## Use Cases

### 1. Traversing Commit History Chronologically

**Problem**: You need to process commits in chronological order, from newest to oldest.

**Solution**: Use `Graph` to build a representation of the commit graph, then use `PriorityQueue` to extract commits ordered by timestamp.

```rust
use gix_hash::ObjectId;
use gix_revwalk::{Graph, PriorityQueue};
use std::cmp::Reverse;

// Create a commit graph
let repo = gix::open("/path/to/repo").unwrap();
let mut graph = Graph::<()>::new(repo.objects.clone(), repo.object_cache.commit_graph());

// Start with HEAD
let head_id = repo.head()?.id().to_owned();

// Insert the starting commit
let _ = graph.try_lookup_or_insert(head_id, |_| {});

// Recursive function to process commit and its parents
fn process_commit_and_parents(
    graph: &mut Graph<()>,
    id: &gix_hash::oid,
    depth: usize,
    max_depth: usize,
) -> Result<(), Box<dyn std::error::Error>> {
    // Stop at max depth
    if depth >= max_depth {
        return Ok(());
    }
    
    // Process parents recursively
    graph.insert_parents(
        id,
        &mut |_, _| (), // No special data needed for new parents
        &mut |_, _| {}, // No updates needed for existing parent data
        false,          // Process all parents, not just the first
    )?;
    
    // Continue with parents
    let commit = graph.lookup(id)?;
    for parent_result in commit.iter_parents() {
        let parent_id = parent_result?;
        process_commit_and_parents(graph, &parent_id, depth + 1, max_depth)?;
    }
    
    Ok(())
}

// Build the graph
process_commit_and_parents(&mut graph, &head_id, 0, 100).unwrap();

// Create a priority queue ordered by commit time (newest first)
let mut queue = PriorityQueue::new();
for (id, commit) in graph.detach().into_iter() {
    let commit_time = graph.lookup(&id).unwrap().committer_timestamp().unwrap();
    queue.insert(Reverse(commit_time), id);
}

// Process commits in timestamp order
while let Some((_, id)) = queue.pop() {
    // Do something with each commit
    println!("Processing commit: {}", id);
}
```

### 2. First-Parent History Traversal

**Problem**: You want to follow only the first parent of each commit to traverse the "main line" of development.

**Solution**: Use the `insert_parents` method with the `first_parent` parameter set to `true`.

```rust
use gix_hash::ObjectId;
use gix_revwalk::Graph;

// Create a commit graph
let repo = gix::open("/path/to/repo").unwrap();
let mut graph = Graph::<()>::new(repo.objects.clone(), repo.object_cache.commit_graph());

// Start with HEAD
let head_id = repo.head()?.id().to_owned();

// Initialize the starting commit
let _ = graph.try_lookup_or_insert(head_id, |_| {});

// Get first-parent history
let mut current_id = head_id;
loop {
    // Insert only the first parent
    graph.insert_parents(
        &current_id,
        &mut |_, _| (), // No special data needed
        &mut |_, _| {}, // No updates needed
        true,           // Only follow first parent
    )?;
    
    // Get the commit to access its parents
    let commit = graph.lookup(&current_id)?;
    let parents: Vec<_> = commit.iter_parents().collect();
    
    if parents.is_empty() {
        // Reached root commit
        break;
    }
    
    // Move to first parent
    current_id = parents[0].unwrap();
    
    // Process the commit
    println!("Processing commit in first-parent line: {}", current_id);
}
```

### 3. Tracking Custom Data During Traversal

**Problem**: During traversal, you need to track custom data for each commit, such as branch membership or commit reachability.

**Solution**: Use the type parameter of `Graph` to store custom data with each commit.

```rust
use gix_hash::ObjectId;
use gix_revwalk::Graph;
use std::collections::HashSet;

// Custom data to track for each commit
struct CommitData {
    branches: HashSet<String>,
    distance_from_head: usize,
}

// Create a commit graph with custom data
let repo = gix::open("/path/to/repo").unwrap();
let mut graph = Graph::<CommitData>::new(repo.objects.clone(), repo.object_cache.commit_graph());

// Start with HEAD and track branch information
let head_id = repo.head()?.id().to_owned();
let head_branch = repo.head()?.name().shorten().to_string();

// Initialize HEAD with custom data
let _ = graph.try_lookup_or_insert_default(
    head_id,
    || CommitData {
        branches: {
            let mut set = HashSet::new();
            set.insert(head_branch.clone());
            set
        },
        distance_from_head: 0,
    },
    |_| {},
);

// Process additional branches
for branch in repo.references()?.prefixed("refs/heads/")? {
    let branch = branch?;
    let branch_name = branch.name().shorten().to_string();
    if branch_name == head_branch {
        continue; // Already processed
    }
    
    let branch_id = branch.id().to_owned();
    
    // Add branch information to commit
    let _ = graph.try_lookup_or_insert_default(
        branch_id,
        || CommitData {
            branches: {
                let mut set = HashSet::new();
                set.insert(branch_name);
                set
            },
            distance_from_head: usize::MAX, // Unknown yet
        },
        |data| {
            data.branches.insert(branch_name.clone());
        },
    );
}

// Propagate information to parents
let mut processed = HashSet::new();
let mut to_process = vec![head_id];

while let Some(id) = to_process.pop() {
    if !processed.insert(id.to_owned()) {
        continue; // Already processed
    }
    
    // Get the current commit's data
    let data = graph.get(&id).unwrap().clone();
    let branches = data.branches.clone();
    let distance = data.distance_from_head;
    
    // Process parents
    graph.insert_parents_with_lookup(
        &id,
        &mut |parent_id, _parent_commit, maybe_existing_data| -> Result<CommitData, Box<dyn std::error::Error>> {
            let mut parent_data = if let Some(existing) = maybe_existing_data {
                // Update existing data
                for branch in &branches {
                    existing.branches.insert(branch.clone());
                }
                if distance + 1 < existing.distance_from_head {
                    existing.distance_from_head = distance + 1;
                }
                existing.clone()
            } else {
                // Create new data
                let mut parent_branches = HashSet::new();
                for branch in &branches {
                    parent_branches.insert(branch.clone());
                }
                CommitData {
                    branches: parent_branches,
                    distance_from_head: distance + 1,
                }
            };
            
            // Add parent to processing queue
            to_process.push(parent_id);
            
            Ok(parent_data)
        },
    )?;
}

// Now the graph contains each commit with branch and distance information
// We can query this information
for (id, data) in graph.detach() {
    println!(
        "Commit {} is on branches {:?} and is {} commits away from HEAD",
        id, data.branches, data.distance_from_head
    );
}
```

### 4. Building a Topological Commit Sorting Algorithm

**Problem**: You need to sort commits in topological order (children before parents).

**Solution**: Combine `Graph` with `PriorityQueue` to implement a topological sorting algorithm.

```rust
use gix_hash::ObjectId;
use gix_revwalk::{Graph, PriorityQueue};
use std::collections::HashMap;

// Create a commit graph
let repo = gix::open("/path/to/repo").unwrap();
let mut graph = Graph::<usize>::new(repo.objects.clone(), repo.object_cache.commit_graph());

// Start with HEAD
let head_id = repo.head()?.id().to_owned();

// First pass: count children for each commit
let mut to_process = vec![head_id.clone()];
let mut processed = std::collections::HashSet::new();

// Start by setting HEAD's child count to 0
let _ = graph.try_lookup_or_insert(head_id, |_| {});

while let Some(id) = to_process.pop() {
    if !processed.insert(id.to_owned()) {
        continue; // Already processed
    }
    
    // Process parents
    graph.insert_parents(
        &id, 
        &mut |_, _| 0, // Initialize parent child count to 0
        &mut |_, data| *data += 1, // Increment parent's child count
        false, // Process all parents
    )?;
    
    // Get the commit to access its parents
    let commit = graph.lookup(&id)?;
    
    // Add all parents to processing queue
    for parent_result in commit.iter_parents() {
        let parent_id = parent_result?;
        to_process.push(parent_id);
    }
}

// Second pass: process commits in topological order
let mut topo_queue = PriorityQueue::new();
let mut topo_sorted = Vec::new();

// Add all commits with no remaining children to the queue
for (id, count) in graph.detach() {
    if count == 0 {
        topo_queue.insert(0, id);
    }
}

// Child count tracking
let mut children_left = HashMap::new();
for (id, count) in graph.detach() {
    if count > 0 {
        children_left.insert(id, count);
    }
}

// Process commits in topological order
while let Some((_, id)) = topo_queue.pop() {
    // Add this commit to the sorted list
    topo_sorted.push(id.to_owned());
    
    // Reduce child count for all parents
    let commit = graph.lookup(&id)?;
    for parent_result in commit.iter_parents() {
        let parent_id = parent_result?;
        
        if let Some(count) = children_left.get_mut(&parent_id) {
            *count -= 1;
            if *count == 0 {
                // All children processed, parent is ready
                children_left.remove(&parent_id);
                topo_queue.insert(0, parent_id);
            }
        }
    }
}

// topo_sorted now contains commits in topological order (children before parents)
for id in topo_sorted {
    println!("Topologically sorted commit: {}", id);
}
```

### 5. Finding Common Ancestors Between Commits

**Problem**: You need to find the nearest common ancestor(s) of two commits, e.g., for merge-base calculation.

**Solution**: Use the Graph to traverse both commit histories until finding common commits.

```rust
use gix_hash::ObjectId;
use gix_revwalk::Graph;
use std::collections::{HashMap, HashSet};

// Create a commit graph
let repo = gix::open("/path/to/repo").unwrap();
let mut graph = Graph::<HashSet<usize>>::new(repo.objects.clone(), repo.object_cache.commit_graph());

// The two commits to find common ancestors for
let commit1_id = ObjectId::from_hex("commit1_hash").unwrap();
let commit2_id = ObjectId::from_hex("commit2_hash").unwrap();

// Mark commits with their source (1 or 2) as we traverse
let _ = graph.try_lookup_or_insert_default(
    commit1_id,
    || {
        let mut set = HashSet::new();
        set.insert(1);
        set
    },
    |_| {},
);

let _ = graph.try_lookup_or_insert_default(
    commit2_id,
    || {
        let mut set = HashSet::new();
        set.insert(2);
        set
    },
    |data| {
        data.insert(2);
    },
);

// Process both commit histories
let mut to_process = vec![commit1_id, commit2_id];
let mut common_ancestors = Vec::new();
let mut processed = HashSet::new();

while let Some(id) = to_process.pop() {
    if !processed.insert(id.to_owned()) {
        continue; // Already processed
    }
    
    // Get the current flags
    let sources = graph.get(&id).unwrap().clone();
    
    // If this commit is reachable from both sides, it's a common ancestor
    if sources.contains(&1) && sources.contains(&2) {
        common_ancestors.push(id.to_owned());
    }
    
    // Process parents
    graph.insert_parents_with_lookup(
        &id,
        &mut |parent_id, _parent_commit, maybe_existing_data| -> Result<HashSet<usize>, Box<dyn std::error::Error>> {
            let parent_data = if let Some(existing) = maybe_existing_data {
                // Update existing data with our sources
                let mut updated = existing.clone();
                for &source in &sources {
                    updated.insert(source);
                }
                updated
            } else {
                // Create new data with our sources
                sources.clone()
            };
            
            // Add parent to processing queue
            to_process.push(parent_id);
            
            Ok(parent_data)
        },
    )?;
}

// Find the most recent common ancestors (those with no descendants that are also common ancestors)
let mut merge_bases = HashSet::new();
for id in common_ancestors {
    // Check if any descendant is also a common ancestor
    let is_descendant_of_another = false;
    
    // (In a real implementation, we would check if this commit is a descendant of any other common ancestor)
    
    if !is_descendant_of_another {
        merge_bases.insert(id);
    }
}

// merge_bases now contains the nearest common ancestors
for base in merge_bases {
    println!("Merge base: {}", base);
}
```

## Best Practices

1. **Use the Commit Graph when Available**: Always provide the commit-graph if available to accelerate operations.

2. **Minimize Object Database Lookups**: Try to extract all needed information in a single pass rather than making multiple passes over the commit history.

3. **Choose Appropriate Data Types**: For the Graph's type parameter, choose data structures that match your traversal needs:
   - Use simple types like `()` when you only need the graph structure
   - Use collections when tracking complex metadata
   - Consider performance implications of your chosen data type

4. **Handle Shallow Repositories**: Be aware that some repositories may be shallow clones, where some commits may be missing. Always handle the case where commits might not exist.

5. **Optimize Queue Operations**: When using `PriorityQueue`, choose appropriate keys for ordering based on your specific algorithm's needs.