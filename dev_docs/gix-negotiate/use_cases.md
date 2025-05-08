# gix-negotiate Use Cases

This document provides practical examples of how to use the `gix-negotiate` crate for various Git network operation scenarios.

## Efficient Fetch from Remote Repository

**Problem**: You need to fetch changes from a remote repository while minimizing the amount of data transferred over the network.

**Solution**: Use the Consecutive negotiation algorithm to precisely identify which objects are needed.

```rust
use gix_hash::ObjectId;
use gix_negotiate::{Algorithm, Negotiator, Graph};
use gix_odb::Store;
use gix_ref::transaction::PreviousValue;
use std::collections::HashSet;

fn fetch_efficiently(repo_path: &str, remote_name: &str, refspecs: &[&str]) -> Result<(), Box<dyn std::error::Error>> {
    // Open the object database
    let store = Store::at_path(format!("{}/objects", repo_path))?;
    
    // Create the commit graph for traversal
    let commit_graph_path = format!("{}/info/commit-graph", store.path());
    let commit_graph = gix_commitgraph::at(commit_graph_path).ok();
    let mut graph = Graph::new(&store, commit_graph.as_ref());
    
    // Create negotiator with consecutive algorithm for optimal pack size
    let mut negotiator = Algorithm::Consecutive.into_negotiator();
    
    // Get local refs to add as tips
    let ref_store = gix_ref::file::Store::at(repo_path, gix_ref::store::init::Options::default())?;
    let local_refs: HashSet<_> = ref_store.iter()?.filter_map(Result::ok).collect();
    
    // Add remote tracking refs as known common points
    for r in local_refs.iter().filter(|r| r.name().starts_with(format!("refs/remotes/{}", remote_name).as_bytes())) {
        let id = r.target.id()?;
        negotiator.known_common(id, &mut graph)?;
    }
    
    // Add local branches as tips to start traversal
    for r in local_refs.iter().filter(|r| r.name().starts_with(b"refs/heads/")) {
        let id = r.target.id()?;
        negotiator.add_tip(id, &mut graph)?;
    }
    
    // Perform negotiation loop
    let mut round = 0;
    let mut window_size = None;
    let stateless = true; // Use stateless transport (like HTTP)
    
    // In a real implementation, this would interface with transport layer
    while round < 10 {
        let current_window = gix_negotiate::window_size(stateless, window_size);
        window_size = Some(current_window);
        
        // Collect HAVEs for this round
        let mut haves = Vec::with_capacity(current_window);
        for _ in 0..current_window {
            match negotiator.next_have(&mut graph) {
                Some(Ok(id)) => haves.push(id),
                Some(Err(e)) => return Err(e.into()),
                None => break, // No more commits to send
            }
        }
        
        if haves.is_empty() {
            break; // Negotiation complete
        }
        
        // In real implementation:
        // 1. Send HAVEs to server
        // 2. Receive ACKs from server
        let acks = simulate_server_acks(&haves);
        
        // Process ACKs
        for ack in acks {
            negotiator.in_common_with_remote(ack, &mut graph)?;
        }
        
        round += 1;
    }
    
    // At this point, we would receive the pack with only needed objects
    println!("Fetch completed with {} negotiation rounds", round);
    
    Ok(())
}

// Simulates server response for example purposes
fn simulate_server_acks(haves: &[ObjectId]) -> Vec<ObjectId> {
    // In a real implementation, this would be the server's response
    // Based on what objects it recognizes from our HAVEs
    haves.iter().take(haves.len() / 2).copied().collect()
}
```

## Initial Clone Optimization

**Problem**: You're implementing a Git client and need to handle the initial clone of a repository.

**Solution**: Since there are no local objects during an initial clone, use the Noop algorithm to avoid unnecessary negotiation.

```rust
use gix_negotiate::{Algorithm, Negotiator, Graph};
use gix_odb::Store;
use std::path::Path;

fn optimize_initial_clone(
    url: &str, 
    target_path: &Path,
    shallow: bool
) -> Result<(), Box<dyn std::error::Error>> {
    // Create target directory and initialize empty repo
    std::fs::create_dir_all(target_path)?;
    let git_dir = target_path.join(".git");
    std::fs::create_dir_all(&git_dir)?;
    std::fs::create_dir_all(git_dir.join("objects"))?;
    std::fs::create_dir_all(git_dir.join("refs/heads"))?;
    
    // For initial clone, use Noop negotiator since we have no objects yet
    let mut negotiator = Algorithm::Noop.into_negotiator();
    
    // Setup empty object store
    let store = Store::at_path(git_dir.join("objects"))?;
    let mut graph = Graph::new(&store, None);
    
    // Since we use Noop, there are no HAVE lines to send
    assert!(negotiator.next_have(&mut graph).is_none());
    
    // Connect to remote and directly request objects
    // In a real implementation, this would:
    // 1. Connect to the repository URL
    // 2. Request refs advertisement
    // 3. Request a packfile containing all objects (or with depth limit if shallow)
    // 4. Process and store the received objects
    
    println!("Initial clone completed using Noop negotiation");
    
    Ok(())
}
```

## Conditional Algorithm Selection

**Problem**: You need to choose the best negotiation algorithm based on the specific fetch scenario.

**Solution**: Implement logic to select the optimal algorithm based on factors like connection type, repo size, and previous fetch performance.

```rust
use gix_negotiate::{Algorithm, Negotiator, Graph};
use gix_odb::Store;
use std::time::{Duration, Instant};

enum ConnectionType {
    LowBandwidth,
    HighLatency,
    HighPerformance,
}

enum RepoState {
    Initial,       // No objects yet
    SlightlyBehind, // Few commits behind remote
    FarBehind,     // Many commits behind remote
}

fn select_optimal_algorithm(
    connection: ConnectionType,
    repo_state: RepoState,
    repo_path: &str
) -> Result<Box<dyn Negotiator>, Box<dyn std::error::Error>> {
    // Open store and create graph
    let store = Store::at_path(format!("{}/objects", repo_path))?;
    let commit_graph = gix_commitgraph::at(store.path().join("info")).ok();
    let graph = Graph::new(&store, commit_graph.as_ref());
    
    // Select algorithm based on conditions
    let algorithm = match (connection, repo_state) {
        // For initial clone, always use Noop
        (_, RepoState::Initial) => Algorithm::Noop,
        
        // For low bandwidth, optimize for minimal data transfer
        (ConnectionType::LowBandwidth, _) => Algorithm::Consecutive,
        
        // For high latency, minimize roundtrips
        (ConnectionType::HighLatency, _) => Algorithm::Skipping,
        
        // For high performance connection slightly behind
        (ConnectionType::HighPerformance, RepoState::SlightlyBehind) => Algorithm::Consecutive,
        
        // For high performance connection far behind
        (ConnectionType::HighPerformance, RepoState::FarBehind) => Algorithm::Skipping,
    };
    
    println!("Selected {} algorithm for negotiation", algorithm);
    
    // Create and return the negotiator
    Ok(algorithm.into_negotiator())
}

// Usage example
fn fetch_with_optimal_algorithm(
    repo_path: &str,
    connection: ConnectionType
) -> Result<(), Box<dyn std::error::Error>> {
    // Determine repo state
    let repo_state = analyze_repo_state(repo_path)?;
    
    // Select and create negotiator
    let negotiator = select_optimal_algorithm(connection, repo_state, repo_path)?;
    
    // Proceed with fetch using selected negotiator
    // ...
    
    Ok(())
}

fn analyze_repo_state(repo_path: &str) -> Result<RepoState, Box<dyn std::error::Error>> {
    // In a real implementation, this would:
    // 1. Check if this is an initial clone (no objects)
    // 2. Compare local and remote HEADs to estimate how far behind we are
    // 3. Consider other factors like repo size, history complexity, etc.
    
    // Simplified for example
    if !std::path::Path::new(&format!("{}/objects", repo_path)).exists() {
        Ok(RepoState::Initial)
    } else {
        // Check number of incoming commits...
        let incoming_commits = 100; // Placeholder
        
        if incoming_commits < 50 {
            Ok(RepoState::SlightlyBehind)
        } else {
            Ok(RepoState::FarBehind)
        }
    }
}
```

## Adapting to Server Feedback

**Problem**: You need to adapt your negotiation strategy based on server responses to optimize performance.

**Solution**: Monitor negotiation effectiveness and adjust parameters like window size based on server feedback.

```rust
use gix_hash::ObjectId;
use gix_negotiate::{Algorithm, Negotiator, Graph, Flags};
use gix_odb::Store;
use std::time::{Duration, Instant};

struct NegotiationMetrics {
    rounds: usize,
    haves_sent: usize,
    acks_received: usize,
    last_round_effectiveness: f32, // Ratio of acks to haves
    duration: Duration,
}

fn adaptive_fetch(
    repo_path: &str,
    remote_name: &str
) -> Result<NegotiationMetrics, Box<dyn std::error::Error>> {
    // Setup
    let store = Store::at_path(format!("{}/objects", repo_path))?;
    let commit_graph = gix_commitgraph::at(store.path().join("info")).ok();
    let mut graph = Graph::new(&store, commit_graph.as_ref());
    
    // Start with skipping algorithm for good initial performance
    let mut negotiator = Algorithm::Skipping.into_negotiator();
    
    // Add remote tracking refs as known common and local branches as tips
    // (implementation omitted for brevity)
    
    // Metrics tracking
    let start = Instant::now();
    let mut metrics = NegotiationMetrics {
        rounds: 0,
        haves_sent: 0,
        acks_received: 0,
        last_round_effectiveness: 1.0,
        duration: Duration::default(),
    };
    
    // Initial window size calculation
    let stateless = true; // e.g., HTTP connection
    let mut window_size = None;
    
    // Negotiation loop
    while metrics.rounds < 10 {
        // Adjust window size based on previous round effectiveness
        let adaptive_factor = if metrics.last_round_effectiveness < 0.1 {
            // Very few ACKs - increase window size more aggressively
            2.0
        } else if metrics.last_round_effectiveness < 0.5 {
            // Moderate ACKs - normal growth
            1.0
        } else {
            // Many ACKs - slow down growth to avoid sending too many unneeded HAVEs
            0.5
        };
        
        let calculated_window = gix_negotiate::window_size(stateless, window_size);
        let current_window = (calculated_window as f32 * adaptive_factor) as usize;
        window_size = Some(current_window);
        
        // Collect HAVEs for this round
        let mut round_haves = Vec::with_capacity(current_window);
        for _ in 0..current_window {
            match negotiator.next_have(&mut graph) {
                Some(Ok(id)) => round_haves.push(id),
                Some(Err(e)) => return Err(e.into()),
                None => break, // No more commits to send
            }
        }
        
        if round_haves.is_empty() {
            break; // Negotiation complete
        }
        
        metrics.haves_sent += round_haves.len();
        
        // In real implementation: send HAVEs to server
        let round_acks = simulate_server_acks(&round_haves);
        metrics.acks_received += round_acks.len();
        
        // Calculate round effectiveness
        metrics.last_round_effectiveness = if !round_haves.is_empty() {
            round_acks.len() as f32 / round_haves.len() as f32
        } else {
            0.0
        };
        
        // Process ACKs
        for ack in round_acks {
            negotiator.in_common_with_remote(ack, &mut graph)?;
        }
        
        metrics.rounds += 1;
        
        // Switch algorithms if needed
        if metrics.rounds == 3 && metrics.last_round_effectiveness < 0.2 {
            // Poor performance with skipping, switch to consecutive
            println!("Switching to consecutive algorithm after poor performance");
            let mut new_negotiator = Algorithm::Consecutive.into_negotiator();
            
            // Transfer already known common commits to new negotiator
            // (In practice, this would require accessing the internal state)
            
            negotiator = new_negotiator;
        }
    }
    
    metrics.duration = start.elapsed();
    Ok(metrics)
}

// Simulates server response for example purposes
fn simulate_server_acks(haves: &[ObjectId]) -> Vec<ObjectId> {
    // In a real implementation, this would be the server's response
    haves.iter().take(haves.len() / 3).copied().collect()
}
```

## Integrating with Commit Graph for Performance

**Problem**: You want to optimize negotiation performance by utilizing the commit graph when available.

**Solution**: Integrate with the commit-graph file to speed up traversal and reduce overhead.

```rust
use gix_hash::ObjectId;
use gix_negotiate::{Algorithm, Negotiator, Graph};
use gix_odb::Store;
use std::time::{Duration, Instant};

fn optimized_fetch_with_commit_graph(
    repo_path: &str
) -> Result<Duration, Box<dyn std::error::Error>> {
    // Setup object store
    let store = Store::at_path(format!("{}/objects", repo_path))?;
    
    // Check for and use commit-graph if available
    let commit_graph_path = format!("{}/info/commit-graph", store.path());
    let start = Instant::now();
    
    // Try to load commit-graph
    let commit_graph = match gix_commitgraph::at(&commit_graph_path) {
        Ok(graph) => {
            println!("Using commit-graph for optimized traversal");
            Some(graph)
        },
        Err(_) => {
            println!("Commit-graph not available, using standard traversal");
            None
        }
    };
    
    // Create graph with optional commit-graph
    let mut graph = Graph::new(&store, commit_graph.as_ref());
    
    // Create negotiator and run fetch
    let mut negotiator = Algorithm::Consecutive.into_negotiator();
    
    // Add tips and perform negotiation
    // (implementation omitted for brevity)
    
    let duration = start.elapsed();
    
    // If fetch took a long time and commit-graph wasn't available, suggest creating one
    if duration > Duration::from_secs(5) && commit_graph.is_none() {
        println!("Fetch took {:?}. Consider generating a commit-graph for better performance: git commit-graph write", duration);
    }
    
    Ok(duration)
}
```

## Managing Negotiation for Shallow Clones

**Problem**: You need to negotiate a shallow clone that only fetches recent history.

**Solution**: Adapt the negotiation process to work with depth-limited history.

```rust
use gix_hash::ObjectId;
use gix_negotiate::{Algorithm, Negotiator, Graph, Flags};
use gix_odb::Store;

fn negotiate_shallow_fetch(
    repo_path: &str,
    depth: usize,
) -> Result<(), Box<dyn std::error::Error>> {
    // Setup object store and graph
    let store = Store::at_path(format!("{}/objects", repo_path))?;
    let mut graph = Graph::new(&store, None);
    
    // For shallow fetches, we use the consecutive algorithm for precise control
    let mut negotiator = Algorithm::Consecutive.into_negotiator();
    
    // Get refs from remote (simplified for example)
    let remote_refs = get_remote_refs()?;
    
    // Add remote HEAD/branches as tips
    for (ref_name, id) in remote_refs {
        negotiator.add_tip(id, &mut graph)?;
    }
    
    // In a real implementation, we would:
    // 1. Track depth during traversal 
    // 2. Use deepen requests instead of negotiation for initial shallow clone
    // 3. For subsequent fetches, use negotiation but respect the shallow boundaries
    
    // Perform depth-limited negotiation
    let mut haves_to_send = Vec::new();
    let mut traversed_depth = 0;
    let mut previous_generation = Vec::new();
    let mut current_generation = Vec::new();
    
    // Get initial commits (generation 0)
    while let Some(Ok(id)) = negotiator.next_have(&mut graph) {
        current_generation.push(id);
        haves_to_send.push(id);
        
        // In a real implementation, we'd send these HAVEs to the server
    }
    
    // Process each generation up to requested depth
    while traversed_depth < depth {
        previous_generation = std::mem::take(&mut current_generation);
        
        // Get the next generation of commits
        for parent_id in get_parents_of_commits(&previous_generation, &store)? {
            // In a real implementation, we'd need to check if we've seen this commit before
            negotiator.add_tip(parent_id, &mut graph)?;
            
            while let Some(Ok(id)) = negotiator.next_have(&mut graph) {
                current_generation.push(id);
                haves_to_send.push(id);
                
                // In a real implementation, we'd send these HAVEs to the server
            }
        }
        
        if current_generation.is_empty() {
            // Reached the end of history before hitting depth limit
            break;
        }
        
        traversed_depth += 1;
    }
    
    // Mark boundary commits as shallow points
    for id in &current_generation {
        // In a real implementation, we'd record these as shallow points
        println!("Shallow boundary: {}", id);
    }
    
    Ok(())
}

// Helper functions for the example
fn get_remote_refs() -> Result<Vec<(String, ObjectId)>, Box<dyn std::error::Error>> {
    // In a real implementation, this would query the remote repository
    Ok(vec![
        ("refs/heads/main".to_string(), 
         ObjectId::from_hex("1234567890abcdef1234567890abcdef12345678").unwrap())
    ])
}

fn get_parents_of_commits(
    commits: &[ObjectId], 
    store: &Store
) -> Result<Vec<ObjectId>, Box<dyn std::error::Error>> {
    // In a real implementation, this would look up the parents of each commit
    let mut parents = Vec::new();
    for commit_id in commits {
        // Placeholder - in reality would parse commit objects
        let parent = ObjectId::from_hex("abcdef1234567890abcdef1234567890abcdef12").unwrap();
        parents.push(parent);
    }
    Ok(parents)
}
```

## Parallel Negotiation for Multiple Remotes

**Problem**: You need to optimize fetching from multiple remotes simultaneously.

**Solution**: Run multiple negotiation processes in parallel, each with its own state.

```rust
use gix_hash::ObjectId;
use gix_negotiate::{Algorithm, Negotiator, Graph};
use gix_odb::Store;
use std::thread;
use std::sync::{Arc, Mutex};
use std::collections::HashMap;

struct RemoteNegotiationResult {
    remote_name: String,
    haves_sent: usize,
    acks_received: usize,
    objects_received: usize,
}

fn parallel_negotiate_multiple_remotes(
    repo_path: &str,
    remote_names: &[&str]
) -> Result<Vec<RemoteNegotiationResult>, Box<dyn std::error::Error>> {
    // Share the object store across threads
    let store = Arc::new(Store::at_path(format!("{}/objects", repo_path))?);
    let commit_graph = gix_commitgraph::at(store.path().join("info")).ok();
    
    // Results will be collected here
    let results = Arc::new(Mutex::new(Vec::new()));
    
    // Launch a thread for each remote
    let mut handles = Vec::new();
    
    for &remote_name in remote_names {
        let store_clone = Arc::clone(&store);
        let commit_graph_clone = commit_graph.clone();
        let results_clone = Arc::clone(&results);
        let remote_name = remote_name.to_string();
        
        let handle = thread::spawn(move || {
            // Create a new graph for this thread
            let mut graph = Graph::new(&store_clone, commit_graph_clone.as_ref());
            
            // Use skipping algorithm for faster convergence when dealing with multiple remotes
            let mut negotiator = Algorithm::Skipping.into_negotiator();
            
            // In a real implementation:
            // 1. Add remote tracking refs as known common
            // 2. Add local branches as tips
            // 3. Perform negotiation with the remote
            
            // Simulate the negotiation
            let mut haves_sent = 0;
            let mut acks_received = 0;
            
            // Batch HAVEs by window size
            let mut window_size = None;
            for round in 0..5 {
                let current_window = gix_negotiate::window_size(true, window_size);
                window_size = Some(current_window);
                
                // Collect HAVEs for this round
                let mut round_haves = Vec::with_capacity(current_window);
                for _ in 0..current_window {
                    if let Some(Ok(id)) = negotiator.next_have(&mut graph) {
                        round_haves.push(id);
                    } else {
                        break;
                    }
                }
                
                if round_haves.is_empty() {
                    break;
                }
                
                haves_sent += round_haves.len();
                
                // Simulate server response
                let round_acks = round_haves.iter().take(round_haves.len() / 3).copied().collect::<Vec<_>>();
                acks_received += round_acks.len();
                
                // Process ACKs
                for ack in round_acks {
                    // This would fail in a real implementation as we can't handle errors in threads easily
                    let _ = negotiator.in_common_with_remote(ack, &mut graph);
                }
            }
            
            // Record results
            let mut results = results_clone.lock().unwrap();
            results.push(RemoteNegotiationResult {
                remote_name,
                haves_sent,
                acks_received,
                objects_received: 100, // Placeholder
            });
        });
        
        handles.push(handle);
    }
    
    // Wait for all threads to complete
    for handle in handles {
        handle.join().map_err(|_| "Thread panicked")?;
    }
    
    // Return the collected results
    let results = Arc::try_unwrap(results)
        .map_err(|_| "Failed to unwrap results")?
        .into_inner()
        .map_err(|_| "Failed to unlock results")?;
    
    Ok(results)
}
```

These use cases demonstrate the flexibility and power of the `gix-negotiate` crate for handling different Git negotiation scenarios. The implementations showcase how to select and configure the appropriate algorithm based on specific requirements, optimize performance with commit-graph integration, and adapt to various fetch scenarios like shallow clones and multiple remotes.