# gix-commitgraph Use Cases

This document outlines practical applications of the `gix-commitgraph` crate, demonstrating how it can be used to accelerate Git operations that involve commit history traversal.

## Intended Audience

- **Git Client Developers**: Building Git clients that need efficient commit history traversal
- **Git Hosting Platform Engineers**: Implementing scalable repository analysis features
- **Git Extension Authors**: Creating tools that need to analyze commit relationships

## Use Case: Fast Ancestor Checking for Pull Request Analysis

### Problem

When analyzing pull requests, Git clients need to determine if one commit is an ancestor of another. Traditional methods require walking the commit history, which can be slow for large repositories.

### Solution

```rust
use gix_commitgraph::at;
use std::path::Path;

/// Determines if candidate is an ancestor of target
fn is_ancestor(
    repo_path: &Path,
    candidate_oid: &gix_hash::oid,
    target_oid: &gix_hash::oid
) -> Result<bool, Box<dyn std::error::Error>> {
    // Load the commit graph
    let graph = at(repo_path.join(".git/objects/info"))?;
    
    // Get positions of the commits we're checking
    let candidate_pos = match graph.lookup(candidate_oid) {
        Some(pos) => pos,
        None => return Ok(false), // Commit not in graph
    };
    
    let target_pos = match graph.lookup(target_oid) {
        Some(pos) => pos,
        None => return Ok(false), // Commit not in graph
    };
    
    // Fast path: check generation numbers
    let candidate = graph.commit_at(candidate_pos);
    let target = graph.commit_at(target_pos);
    
    // If candidate's generation is greater than target's, it can't be an ancestor
    if candidate.generation() > target.generation() {
        return Ok(false);
    }
    
    // Use a breadth-first search from target, going backward through parents
    let mut queue = std::collections::VecDeque::new();
    let mut visited = std::collections::HashSet::new();
    
    queue.push_back(target_pos);
    visited.insert(target_pos);
    
    while let Some(pos) = queue.pop_front() {
        if pos == candidate_pos {
            return Ok(true);
        }
        
        let commit = graph.commit_at(pos);
        
        // Only explore paths where generation could include our candidate
        if commit.generation() <= candidate.generation() {
            continue;
        }
        
        // Add all parents to the queue
        for parent_result in commit.iter_parents() {
            let parent_pos = parent_result?;
            if visited.insert(parent_pos) {
                queue.push_back(parent_pos);
            }
        }
    }
    
    Ok(false)
}
```

This approach is significantly faster than traditional commit walking because:

1. Generation numbers provide an immediate disqualification check
2. The commit-graph provides direct access to parent relationships without loading commit objects
3. All data is memory-mapped for efficient access

## Use Case: Finding Merge-Base Commits

### Problem

Finding the common ancestor (merge-base) of two commits is a fundamental operation in Git, required for merges, rebases, and various history analysis tools. The traditional approach requires loading and parsing many commit objects.

### Solution

```rust
use gix_commitgraph::at;
use std::{collections::{BinaryHeap, HashSet}, path::Path};

/// Find the merge-base (common ancestor) of two commits
fn find_merge_base(
    repo_path: &Path,
    commit1_oid: &gix_hash::oid,
    commit2_oid: &gix_hash::oid
) -> Result<Option<gix_hash::ObjectId>, Box<dyn std::error::Error>> {
    // Load the commit graph
    let graph = at(repo_path.join(".git/objects/info"))?;
    
    // Get positions of the commits
    let pos1 = match graph.lookup(commit1_oid) {
        Some(pos) => pos,
        None => return Ok(None), // Commit not in graph
    };
    
    let pos2 = match graph.lookup(commit2_oid) {
        Some(pos) => pos,
        None => return Ok(None), // Commit not in graph
    };
    
    // Create a priority queue ordered by generation number (highest first)
    let mut queue = BinaryHeap::new();
    let mut visited1 = HashSet::new();
    let mut visited2 = HashSet::new();
    
    // Data type for our priority queue
    #[derive(Eq, PartialEq)]
    struct QueueEntry {
        generation: u32,
        position: gix_commitgraph::Position,
        from_first: bool,
    }
    
    impl Ord for QueueEntry {
        fn cmp(&self, other: &Self) -> std::cmp::Ordering {
            self.generation.cmp(&other.generation)
        }
    }
    
    impl PartialOrd for QueueEntry {
        fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
            Some(self.cmp(other))
        }
    }
    
    // Add initial commits to their respective visited sets
    visited1.insert(pos1);
    visited2.insert(pos2);
    
    // Enqueue both starting commits
    let commit1 = graph.commit_at(pos1);
    let commit2 = graph.commit_at(pos2);
    
    queue.push(QueueEntry {
        generation: commit1.generation(),
        position: pos1,
        from_first: true,
    });
    
    queue.push(QueueEntry {
        generation: commit2.generation(),
        position: pos2,
        from_first: false,
    });
    
    // Process commits in generation order (highest first)
    while let Some(entry) = queue.pop() {
        let position = entry.position;
        
        // Check if this commit has been seen from the other direction
        if (entry.from_first && visited2.contains(&position)) ||
           (!entry.from_first && visited1.contains(&position)) {
            // We found the merge-base
            return Ok(Some(graph.id_at(position).into()));
        }
        
        // Add all parents to the queue
        let commit = graph.commit_at(position);
        for parent_result in commit.iter_parents() {
            let parent_pos = parent_result?;
            let parent = graph.commit_at(parent_pos);
            
            let visited = if entry.from_first { &mut visited1 } else { &mut visited2 };
            
            if visited.insert(parent_pos) {
                queue.push(QueueEntry {
                    generation: parent.generation(),
                    position: parent_pos,
                    from_first: entry.from_first,
                });
            }
        }
    }
    
    // No common ancestor found
    Ok(None)
}
```

This implementation:
1. Uses generation numbers to process commits in optimal order
2. Avoids loading actual commit objects
3. Stops as soon as the earliest common ancestor is found

## Use Case: Generating Repository Statistics

### Problem

Software analytics tools need to generate statistics about repository activity and commit patterns, but analyzing a large Git repository can be prohibitively slow.

### Solution

```rust
use gix_commitgraph::at;
use std::collections::HashMap;
use std::path::Path;

/// Repository statistics generated from commit-graph data
struct RepoStats {
    /// Total number of commits
    commit_count: u32,
    /// Number of merge commits (with multiple parents)
    merge_count: u32,
    /// Max number of parents for any commit (octopus merges)
    max_parents: u32,
    /// Distribution of commits by generation (depth in history)
    commits_by_generation: HashMap<u32, u32>,
    /// Longest linear chain length
    longest_chain: Option<u32>,
}

/// Generate repository statistics using the commit-graph
fn analyze_repository(repo_path: &Path) -> Result<RepoStats, Box<dyn std::error::Error>> {
    // Load the commit graph
    let graph = at(repo_path.join(".git/objects/info"))?;
    
    // Verify integrity and get basic stats
    let verification = graph.verify_integrity(|_| Ok(()))?;
    
    let mut stats = RepoStats {
        commit_count: verification.num_commits,
        merge_count: 0,
        max_parents: 0,
        commits_by_generation: HashMap::new(),
        longest_chain: verification.longest_path_length,
    };
    
    // Process parent counts from verification
    for (parent_count, commit_count) in verification.parent_counts {
        if parent_count > 1 {
            stats.merge_count += commit_count;
        }
        
        if parent_count > stats.max_parents {
            stats.max_parents = parent_count;
        }
    }
    
    // Build generation distribution
    for commit in graph.iter_commits() {
        let gen = commit.generation();
        *stats.commits_by_generation.entry(gen).or_insert(0) += 1;
    }
    
    Ok(stats)
}
```

This approach:
1. Uses the verification process to get bulk statistics efficiently
2. Avoids parsing or loading full commit objects
3. Creates a comprehensive statistical profile of the repository

## Use Case: Commit History Visualization

### Problem

Git visualization tools need to efficiently build graph data structures representing commit history relationships. Traditional approaches that load every commit object are too slow for repositories with thousands of commits.

### Solution

```rust
use gix_commitgraph::at;
use std::{collections::{HashMap, VecDeque}, path::Path};

/// Node in the commit graph visualization
struct CommitNode {
    id: gix_hash::ObjectId,
    timestamp: u64,
    generation: u32,
    parent_ids: Vec<gix_hash::ObjectId>,
}

/// Build a visualization-ready commit graph starting from a specific commit
fn build_commit_graph(
    repo_path: &Path, 
    start_commit: &gix_hash::oid,
    max_commits: usize
) -> Result<Vec<CommitNode>, Box<dyn std::error::Error>> {
    // Load the commit graph
    let graph = at(repo_path.join(".git/objects/info"))?;
    
    let mut result = Vec::new();
    let mut queue = VecDeque::new();
    let mut visited = HashMap::new();
    
    // Start from the given commit
    if let Some(start_pos) = graph.lookup(start_commit) {
        queue.push_back(start_pos);
        visited.insert(start_pos, result.len());
        
        let commit = graph.commit_at(start_pos);
        result.push(CommitNode {
            id: commit.id().into(),
            timestamp: commit.committer_timestamp(),
            generation: commit.generation(),
            parent_ids: Vec::new(), // Fill later
        });
    } else {
        return Ok(Vec::new()); // Start commit not found
    }
    
    // BFS traversal to build the graph
    while let Some(pos) = queue.pop_front() {
        if result.len() >= max_commits {
            break;
        }
        
        let commit = graph.commit_at(pos);
        let node_idx = visited[&pos];
        
        // Collect parent IDs and add them to the queue
        for parent_result in commit.iter_parents() {
            let parent_pos = parent_result?;
            let parent = graph.commit_at(parent_pos);
            let parent_id = parent.id().into();
            
            // Add parent ID to the current node
            result[node_idx].parent_ids.push(parent_id);
            
            // Process parent if not visited yet
            if !visited.contains_key(&parent_pos) {
                visited.insert(parent_pos, result.len());
                queue.push_back(parent_pos);
                
                // Create node for the parent
                result.push(CommitNode {
                    id: parent_id,
                    timestamp: parent.committer_timestamp(),
                    generation: parent.generation(),
                    parent_ids: Vec::new(), // Fill later
                });
            }
        }
    }
    
    Ok(result)
}
```

Benefits of this approach:
1. Generation numbers help build a properly layered visualization
2. Timestamps are directly available for time-based layouts
3. Parent relationships are efficiently extracted
4. BFS traversal with bounded depth prevents processing too many commits

## Use Case: Finding Branch Divergence Points

### Problem

Git clients need to efficiently find where two branches diverged to calculate ahead/behind commit counts or to show branch comparison views. Traditional approaches require examining multiple merge-bases and performing full history traversals.

### Solution

```rust
use gix_commitgraph::at;
use std::{collections::HashSet, path::Path};

/// Information about branch divergence
struct BranchDivergence {
    /// Common ancestor where branches diverged
    common_ancestor: gix_hash::ObjectId,
    /// Commits in branch1 not in branch2
    branch1_ahead: Vec<gix_hash::ObjectId>,
    /// Commits in branch2 not in branch1
    branch2_ahead: Vec<gix_hash::ObjectId>,
}

/// Find the divergence point between two branches
fn find_branch_divergence(
    repo_path: &Path,
    branch1_tip: &gix_hash::oid,
    branch2_tip: &gix_hash::oid
) -> Result<Option<BranchDivergence>, Box<dyn std::error::Error>> {
    // Load the commit graph
    let graph = at(repo_path.join(".git/objects/info"))?;
    
    // Find positions for branch tips
    let pos1 = match graph.lookup(branch1_tip) {
        Some(pos) => pos,
        None => return Ok(None), // Commit not in graph
    };
    
    let pos2 = match graph.lookup(branch2_tip) {
        Some(pos) => pos,
        None => return Ok(None), // Commit not in graph
    };
    
    // Find merge-base (common ancestor)
    let mut common_ancestor = None;
    let mut branch1_commits = HashSet::new();
    let mut branch2_commits = HashSet::new();
    
    // Collect all commits in branch1
    let mut stack = vec![pos1];
    while let Some(pos) = stack.pop() {
        if !branch1_commits.insert(pos) {
            continue; // Already visited
        }
        
        let commit = graph.commit_at(pos);
        for parent_result in commit.iter_parents() {
            if let Ok(parent_pos) = parent_result {
                stack.push(parent_pos);
            }
        }
    }
    
    // Find divergence by walking branch2
    stack = vec![pos2];
    while let Some(pos) = stack.pop() {
        if !branch2_commits.insert(pos) {
            continue; // Already visited
        }
        
        // Check if this commit is in branch1
        if branch1_commits.contains(&pos) {
            // This is a common commit - might be the merge-base
            if common_ancestor.is_none() {
                common_ancestor = Some(pos);
            } else {
                let current = graph.commit_at(pos);
                let previous = graph.commit_at(common_ancestor.unwrap());
                
                // Keep the one with higher generation number (closer to tips)
                if current.generation() > previous.generation() {
                    common_ancestor = Some(pos);
                }
            }
            
            continue; // Don't process parents
        }
        
        // Add parents to the stack
        let commit = graph.commit_at(pos);
        for parent_result in commit.iter_parents() {
            if let Ok(parent_pos) = parent_result {
                stack.push(parent_pos);
            }
        }
    }
    
    // No common ancestor found
    let merge_base = match common_ancestor {
        Some(pos) => pos,
        None => return Ok(None),
    };
    
    // Collect unique commits in each branch
    let branch1_ahead = branch1_commits
        .iter()
        .filter(|&pos| !branch2_commits.contains(pos))
        .map(|&pos| graph.id_at(pos).into())
        .collect();
    
    let branch2_ahead = branch2_commits
        .iter()
        .filter(|&pos| !branch1_commits.contains(pos))
        .map(|&pos| graph.id_at(pos).into())
        .collect();
    
    Ok(Some(BranchDivergence {
        common_ancestor: graph.id_at(merge_base).into(),
        branch1_ahead,
        branch2_ahead,
    }))
}
```

This implementation:
1. Uses the commit-graph to avoid loading commit objects
2. Efficiently collects all commits in both branches
3. Finds the optimal common ancestor (merge-base)
4. Calculates ahead/behind counts for each branch

## Use Case: Commit Date Range Analysis

### Problem

Git analysis tools need to find all commits within a specific date range, which can be slow using traditional Git commands that load each commit.

### Solution

```rust
use gix_commitgraph::at;
use std::path::Path;

/// Find all commits within a specific date range
fn find_commits_in_date_range(
    repo_path: &Path,
    start_timestamp: u64,
    end_timestamp: u64
) -> Result<Vec<gix_hash::ObjectId>, Box<dyn std::error::Error>> {
    // Load the commit graph
    let graph = at(repo_path.join(".git/objects/info"))?;
    
    // Collect all commits within the date range
    let mut commits_in_range = Vec::new();
    
    for commit in graph.iter_commits() {
        let timestamp = commit.committer_timestamp();
        
        if timestamp >= start_timestamp && timestamp <= end_timestamp {
            commits_in_range.push(commit.id().into());
        }
    }
    
    // Sort by timestamp (newest first)
    commits_in_range.sort_by(|a, b| {
        let pos_a = graph.lookup(a).unwrap();
        let pos_b = graph.lookup(b).unwrap();
        
        let commit_a = graph.commit_at(pos_a);
        let commit_b = graph.commit_at(pos_b);
        
        commit_b.committer_timestamp().cmp(&commit_a.committer_timestamp())
    });
    
    Ok(commits_in_range)
}
```

This approach:
1. Directly accesses commit timestamps from the commit-graph without loading objects
2. Efficiently filters by date range
3. Uses the commit-graph for all operations, making it much faster than traditional Git commands

## Use Case: Repository Integrity Verification

### Problem

Git hosting platforms and repository management tools need to verify the integrity of repositories, including detecting corrupt or inconsistent commit-graph files.

### Solution

```rust
use gix_commitgraph::at;
use std::path::Path;

/// Verify commit-graph integrity with detailed reporting
fn verify_repository_commit_graph(
    repo_path: &Path
) -> Result<String, Box<dyn std::error::Error>> {
    // Load the commit graph
    let graph_result = at(repo_path.join(".git/objects/info"));
    
    // Check if commit graph exists
    let graph = match graph_result {
        Ok(g) => g,
        Err(e) => return Ok(format!("No valid commit-graph found: {e}")),
    };
    
    // Build a report with statistics
    let mut report = String::new();
    
    // Verify integrity of the commit-graph
    match graph.verify_integrity(|_| Ok(())) {
        Ok(stats) => {
            report.push_str(&format!("Commit-graph is valid.\n"));
            report.push_str(&format!("Total commits: {}\n", stats.num_commits));
            
            if let Some(length) = stats.longest_path_length {
                report.push_str(&format!("Longest path length: {}\n", length));
            } else {
                report.push_str("Longest path length is too large to represent.\n");
            }
            
            report.push_str("Parent counts:\n");
            let mut counts: Vec<_> = stats.parent_counts.into_iter().collect();
            counts.sort_by_key(|&(count, _)| count);
            
            for (parent_count, commit_count) in counts {
                report.push_str(&format!("  {} parents: {} commits\n", parent_count, commit_count));
            }
        },
        Err(e) => {
            report.push_str(&format!("Commit-graph verification failed: {}\n", e));
            
            // Add suggestions for fixing the issue
            match e {
                gix_commitgraph::verify::Error::BaseGraphCount { .. } | 
                gix_commitgraph::verify::Error::BaseGraphId { .. } => {
                    report.push_str("The commit-graph chain appears to be corrupted. Try running:\n");
                    report.push_str("  git commit-graph write --reachable --split\n");
                },
                gix_commitgraph::verify::Error::Generation { .. } => {
                    report.push_str("Invalid generation numbers detected. Try running:\n");
                    report.push_str("  git commit-graph write --reachable\n");
                },
                _ => {
                    report.push_str("The commit-graph appears to be corrupted. Try running:\n");
                    report.push_str("  git commit-graph verify\n");
                    report.push_str("If issues are found, recreate the commit-graph with:\n");
                    report.push_str("  git commit-graph write --reachable\n");
                }
            }
        }
    }
    
    Ok(report)
}
```

This verification approach:
1. Detects invalid or corrupt commit-graph files
2. Provides detailed statistics about the repository
3. Gives specific recommendations for fixing issues
4. Handles both single-file and split commit graphs

These use cases demonstrate the power and flexibility of the `gix-commitgraph` crate for accelerating Git operations that involve commit history traversal and analysis.