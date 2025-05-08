# gix-negotiate

## Overview

`gix-negotiate` is a core component of the gitoxide ecosystem that implements Git's negotiation algorithms. These algorithms determine which objects are needed during network operations like fetching, by efficiently identifying what objects a client already has versus what it needs to request from the server.

The crate provides multiple negotiation strategies with different trade-offs between accuracy and performance, allowing Git clients to minimize network traffic and transfer only the objects they don't already possess.

## Architecture

`gix-negotiate` follows a design centered around the negotiation process between Git clients and servers:

1. **Core Abstraction**: A trait-based design with the `Negotiator` trait defining the contract for all negotiation algorithms
2. **Multiple Algorithms**: Three distinct negotiation strategies with different performance characteristics:
   - `Noop`: Minimal communication, typically resulting in full packs being sent
   - `Consecutive`: Exhaustive traversal of commit history for optimal pack sizes
   - `Skipping`: Time-to-live based approach for faster convergence at the cost of potentially larger packs
3. **Shared Graph**: An underlying graph structure for efficient traversal and tracking of commit metadata
4. **Stateful Tracking**: Detailed tracking of object states during the negotiation process

### Key Components

#### Core Types

- `Negotiator`: Trait defining the contract for negotiation algorithms
- `Algorithm`: Enum representing the available negotiation strategies
- `Metadata`: Additional data stored with each commit to track negotiation state
- `Flags`: Bitflags representing the state of commits during negotiation
- `Graph`: Type alias for the traversal graph with commit metadata

#### Negotiation Algorithms

The implementation provides three primary algorithms:

1. **Noop Algorithm**
   - Simplest approach with no negotiation
   - Sends no "HAVE" statements to the server
   - Results in complete packs being transferred
   - Useful for initial clones or when network bandwidth is not a concern

2. **Consecutive Algorithm**
   - Walks through consecutive commits in the history
   - Ensures optimal pack sizes by communicating exactly what the client has
   - More network roundtrips but minimizes data transfer
   - Prioritizes commits by timestamp using a priority queue

3. **Skipping Algorithm**
   - More efficient traversal that skips some commits
   - Uses a time-to-live (TTL) approach to determine which commits to report
   - Faster convergence at the cost of potentially larger packs
   - Good balance between network roundtrips and data transfer

#### State Tracking with Flags

The crate uses bitflags to track various states of commits during negotiation:

```rust
pub struct Flags: u8 {
    // Object availability
    const COMPLETE = 1 << 0;    // Object available locally
    const ALTERNATE = 1 << 1;    // From alternate object database
    
    // Negotiation state
    const COMMON = 1 << 2;       // Known to be in common with remote
    const SEEN = 1 << 3;         // Entered priority queue
    const POPPED = 1 << 4;       // Popped from priority queue
    const COMMON_REF = 1 << 5;   // Common via remote tracking ref
    const ADVERTISED = 1 << 6;   // Remote has this object
}
```

## Dependencies

The crate depends on several other gitoxide components:

- `gix-hash`: Object ID handling and hash digest functionality
- `gix-object`: Git object model and parsing
- `gix-date`: Date handling for commit timestamps
- `gix-commitgraph`: Commit graph access for traversal optimization
- `gix-revwalk`: Commit graph traversal and priority queues

External dependencies include:
- `smallvec`: Optimization for small collections on the stack
- `bitflags`: Efficient bitflag representation
- `thiserror`: Error handling

## Implementation Details

### Negotiation Protocol Flow

The Git negotiation process follows a specific protocol:

1. The client identifies tips (branches, tags) it wants to fetch from the server
2. Client traverses its commit history, sending "HAVE" statements about objects it already possesses
3. Server responds with "ACK" for objects it recognizes, establishing common ground
4. Process continues until enough common objects are identified or traversal is exhausted
5. Server then sends only the objects the client doesn't have

### Window Size Calculation

The crate implements a window size calculation function that determines how many "HAVE" lines to send in each batch, which grows exponentially or linearly depending on whether the transport is stateless:

```rust
pub fn window_size(transport_is_stateless: bool, window_size: Option<usize>) -> usize {
    // Initial window size is 16
    let current_size = match window_size {
        None => return 16,
        Some(cs) => cs,
    };
    
    if transport_is_stateless {
        // For stateless transports (like HTTP), grow more aggressively
        if current_size < 16384 {
            current_size * 2         // Double until reaching large size
        } else {
            current_size * 11 / 10   // Then grow by 10%
        }
    } else {
        // For stateful transports (like SSH/Git), grow more conservatively
        if current_size < 32 {
            current_size * 2         // Double for small windows
        } else {
            current_size + 32        // Add fixed increment for larger windows
        }
    }
}
```

### Consecutive Algorithm Implementation

The consecutive algorithm takes a thorough approach:

1. Starts with tips and explores commits in order of timestamp
2. Uses a priority queue to traverse commits from newest to oldest
3. Sends "HAVE" for each unprocessed commit
4. Marks parents of known common commits as common
5. Tracks how many non-common revisions remain to efficiently determine when to stop

Core logic for finding the next "HAVE" to send:

```rust
fn next_have(&mut self, graph: &mut crate::Graph<'_, '_>) -> Option<Result<ObjectId, Error>> {
    loop {
        // Get next commit from priority queue, filtering when done
        let id = self.revs.pop_value().filter(|_| self.non_common_revs != 0)?;
        
        // Update state for this commit
        let commit = graph.get_mut(&id).expect("it was added to the graph by now");
        let flags = &mut commit.data.flags;
        *flags |= Flags::POPPED;
        
        // Count non-common revisions
        if !flags.contains(Flags::COMMON) {
            self.non_common_revs -= 1;
        }
        
        // Determine if we should send this as HAVE
        let (res, mark) = if flags.contains(Flags::COMMON) {
            (None, Flags::COMMON | Flags::SEEN)
        } else if flags.contains(Flags::COMMON_REF) {
            (Some(id), Flags::COMMON | Flags::SEEN)
        } else {
            (Some(id), Flags::SEEN)
        };
        
        // Add parents to queue for future processing
        for parent_id in commit.parents.clone() {
            // Process parent...
        }
        
        if let Some(id) = res {
            return Some(Ok(id));
        }
    }
}
```

### Skipping Algorithm Implementation

The skipping algorithm uses time-to-live (TTL) values to skip some commits:

1. Each commit gets a TTL value and original TTL value
2. TTL decreases as traversal progresses through parents
3. When TTL reaches zero, the commit is sent as "HAVE"
4. When common commits are found, their ancestors are also marked as common
5. Original TTL can increase for distant commits, creating an adaptive mechanism

This approach reduces the number of roundtrips at the cost of potentially fetching some objects that are already present locally.

## Usage Examples

### Basic Negotiation with Consecutive Algorithm

```rust
use gix_hash::ObjectId;
use gix_negotiate::{Algorithm, Negotiator, Graph};
use gix_odb::Store;

// Setup object database and commit graph
let store = Store::at_path("/path/to/repo/.git/objects")?;
let graph = Graph::new(&store, None);

// Create negotiator with consecutive algorithm
let mut negotiator = Algorithm::Consecutive.into_negotiator();

// Add local tips to start traversal from
let main_tip = ObjectId::from_hex("1234567890abcdef1234567890abcdef12345678")?;
negotiator.add_tip(main_tip, &mut graph)?;

// Add known common commits (e.g., from remote tracking branches)
let remote_main = ObjectId::from_hex("abcdef1234567890abcdef1234567890abcdef12")?;
negotiator.known_common(remote_main, &mut graph)?;

// Iterate through commits to send as HAVE
let mut have_ids = Vec::new();
while let Some(have_id) = negotiator.next_have(&mut graph) {
    let id = have_id?;
    have_ids.push(id);
    
    // In a real implementation, we would send these to the server
    // and process ACKs from the server
}

// Process ACKs from server
for acked_id in server_acks {
    negotiator.in_common_with_remote(acked_id, &mut graph)?;
}
```

### Using the Skipping Algorithm for Faster Convergence

```rust
use gix_hash::ObjectId;
use gix_negotiate::{Algorithm, Negotiator, Graph};
use gix_odb::Store;

// Setup object database and commit graph
let store = Store::at_path("/path/to/repo/.git/objects")?;

// Use commit graph for faster traversal if available
let commit_graph = gix_commitgraph::at(store.path().join("info")).ok();
let mut graph = Graph::new(&store, commit_graph.as_ref());

// Create negotiator with skipping algorithm for faster convergence
let mut negotiator = Algorithm::Skipping.into_negotiator();

// Add local branch tips
let branch_tips = get_branch_tips(); // Function to get all local branch tips
for tip in branch_tips {
    negotiator.add_tip(tip, &mut graph)?;
}

// Perform negotiation in multiple rounds
let mut round = 0;
let mut window_size = None;
while round < 10 { // Limit rounds to avoid infinite loops
    // Calculate window size for this round
    let current_window = gix_negotiate::window_size(true, window_size);
    window_size = Some(current_window);
    
    // Send HACEs in batches
    let mut haves = Vec::with_capacity(current_window);
    for _ in 0..current_window {
        match negotiator.next_have(&mut graph) {
            Some(Ok(id)) => haves.push(id),
            Some(Err(e)) => return Err(e),
            None => break, // No more commits to send
        }
    }
    
    if haves.is_empty() {
        break; // Negotiation complete
    }
    
    // Send HAVE batch to server and process ACKs
    let acks = send_haves_to_server(&haves)?;
    for ack in acks {
        negotiator.in_common_with_remote(ack, &mut graph)?;
    }
    
    round += 1;
}
```

### Using the Noop Algorithm for Initial Clone

```rust
use gix_negotiate::{Algorithm, Negotiator};

// For initial clones, using Noop is often the best choice since
// the client has no objects yet
let mut negotiator = Algorithm::Noop.into_negotiator();

// Since we use Noop, there are no HAVE lines to send
assert!(negotiator.next_have(&mut graph).is_none());

// We directly request the full pack from the server
// without any negotiation
```

## Internal Design Considerations

1. **Memory Efficiency**: The implementation carefully manages memory with techniques like:
   - Using `smallvec` for collections that are expected to be small
   - Reusing the traversal graph between operations
   - Efficient bitflags to pack multiple boolean states into a single byte

2. **Balancing Accuracy and Speed**: The multiple algorithm options allow users to choose the right balance for their use case:
   - `Noop`: Fast but inefficient for bandwidth
   - `Consecutive`: Most efficient for bandwidth but slower convergence
   - `Skipping`: Best balance between speed and bandwidth

3. **Stateful Negotiation**: The algorithms maintain state across multiple negotiation rounds, allowing for incremental refinement of the common object set.

4. **Commit Graph Integration**: The implementation can utilize the commit graph for faster traversal when available.

## Related Components

The `gix-negotiate` crate integrates with several other gitoxide components:

- `gix-protocol`: Uses negotiation results for Git protocol communication
- `gix-transport`: Handles the transport layer for sending negotiation messages
- `gix-odb`: Provides access to the object database 
- `gix-revwalk`: Powers the underlying graph traversal

## Conclusion

The `gix-negotiate` crate provides a crucial part of Git's networking functionality by implementing various negotiation strategies that determine which objects need to be transferred during fetch operations. The implementation is efficient, memory-conscious, and offers multiple algorithms with different trade-offs between transfer size and negotiation speed.