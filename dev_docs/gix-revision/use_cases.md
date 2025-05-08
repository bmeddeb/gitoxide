# gix-revision Use Cases

This document describes the main use cases for the `gix-revision` crate, which provides functionality for handling Git revision specifications and commit descriptions.

## Intended Audience

- Developers implementing Git clients or tools
- Applications that need to resolve Git revisions
- Tools that traverse or analyze Git commit history
- Systems that need to generate user-friendly references to commits

## Use Case 1: Parsing Git Revision Specifications

### Problem

Git provides a rich syntax for specifying revisions (commits, trees, etc.), and tools need to parse and interpret these specifications to locate the correct objects.

### Solution

Use the `spec::parse()` function with a custom delegate to parse revision specifications.

```rust
use bstr::ByteSlice;
use gix_hash::{ObjectId, oid};
use gix_revision::spec::{self, parse::delegate::{self, Revision, Navigate, Kind}};

// A delegate that tracks parsed specification components
struct RevisionResolver {
    current_oid: Option<ObjectId>,
    traverse_operations: Vec<String>,
    spec_kind: Option<gix_revision::spec::Kind>,
}

impl RevisionResolver {
    fn new() -> Self {
        RevisionResolver {
            current_oid: None,
            traverse_operations: Vec::new(),
            spec_kind: None,
        }
    }
    
    fn resolve(&self) -> Option<ObjectId> {
        self.current_oid
    }
}

// Implement the required delegate traits
impl delegate::Revision for RevisionResolver {
    fn find_ref(&mut self, name: &bstr::BStr) -> Option<()> {
        // In a real implementation, we would look up the reference in the repository
        // For this example, we'll simulate finding some predefined refs
        match name.to_str().ok()? {
            "HEAD" | "main" => {
                self.current_oid = Some(oid::hex("1234567890123456789012345678901234567890").unwrap());
                Some(())
            }
            "feature" => {
                self.current_oid = Some(oid::hex("abcdefabcdefabcdefabcdefabcdefabcdefabcd").unwrap());
                Some(())
            }
            _ => None,
        }
    }
    
    fn disambiguate_prefix(&mut self, prefix: gix_hash::Prefix, _hint: Option<delegate::PrefixHint<'_>>) -> Option<()> {
        // Simulate prefix resolution
        if prefix.hex_len() >= 7 {
            self.current_oid = Some(oid::hex("1234567890123456789012345678901234567890").unwrap());
            Some(())
        } else {
            None
        }
    }
    
    // Other methods would be implemented similarly
    fn reflog(&mut self, _query: delegate::ReflogLookup) -> Option<()> { Some(()) }
    fn nth_checked_out_branch(&mut self, _branch_no: usize) -> Option<()> { Some(()) }
    fn sibling_branch(&mut self, _kind: delegate::SiblingBranch) -> Option<()> { Some(()) }
}

impl delegate::Navigate for RevisionResolver {
    fn traverse(&mut self, kind: delegate::Traversal) -> Option<()> {
        // Record the traversal operation
        match kind {
            delegate::Traversal::NthAncestor(n) => {
                self.traverse_operations.push(format!("~{}", n));
                Some(())
            }
            delegate::Traversal::NthParent(n) => {
                self.traverse_operations.push(format!("^{}", n));
                Some(())
            }
        }
    }
    
    // Other navigation methods
    fn peel_until(&mut self, _kind: delegate::PeelTo<'_>) -> Option<()> { Some(()) }
    fn find(&mut self, _regex: &bstr::BStr, _negated: bool) -> Option<()> { Some(()) }
    fn index_lookup(&mut self, _path: &bstr::BStr, _stage: u8) -> Option<()> { Some(()) }
}

impl delegate::Kind for RevisionResolver {
    fn kind(&mut self, kind: gix_revision::spec::Kind) -> Option<()> {
        self.spec_kind = Some(kind);
        Some(())
    }
}

impl spec::parse::Delegate for RevisionResolver {
    fn done(&mut self) {
        // Nothing special to do when parsing is complete
    }
}

// Example usage
fn resolve_revision(revspec: &str) -> Result<String, Box<dyn std::error::Error>> {
    let mut resolver = RevisionResolver::new();
    
    // Parse the revision spec
    spec::parse(revspec.as_bytes().as_bstr(), &mut resolver)?;
    
    // Describe the resolution
    let resolved = match resolver.resolve() {
        Some(oid) => {
            let mut description = format!("Resolved to: {}", oid);
            
            if !resolver.traverse_operations.is_empty() {
                description.push_str("\nTraversals: ");
                description.push_str(&resolver.traverse_operations.join(", "));
            }
            
            if let Some(kind) = resolver.spec_kind {
                description.push_str(&format!("\nSpecification kind: {:?}", kind));
            }
            
            description
        },
        None => "Failed to resolve revision".to_string(),
    };
    
    Ok(resolved)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let revspecs = ["HEAD", "HEAD~2", "HEAD^1", "main..feature", "123456"];
    
    for revspec in &revspecs {
        println!("\nRevspec: {}", revspec);
        println!("{}", resolve_revision(revspec)?);
    }
    
    Ok(())
}
```

## Use Case 2: Generating Human-Readable Commit References

### Problem

When working with Git repositories, especially in automated systems or UIs, raw commit hashes are not user-friendly. You need a way to generate meaningful names for commits that relate them to known references.

### Solution

Use the `describe` function to generate human-readable commit descriptions based on nearby tags.

```rust
use gix_hash::{ObjectId, oid};
use gix_revision::{describe, Graph};
use std::collections::HashMap;

// A simple graph implementation for the example
struct SimpleGraph {
    commits: HashMap<ObjectId, Vec<ObjectId>>,
    tags: HashMap<ObjectId, Vec<String>>,
}

impl SimpleGraph {
    fn new() -> Self {
        let mut graph = SimpleGraph {
            commits: HashMap::new(),
            tags: HashMap::new(),
        };
        
        // Set up a simple commit graph with some tags
        // A -> B -> C -> D -> E -> F
        //       ^        ^
        //       |        |
        //     v1.0     v2.0
        
        let commits = [
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "ccccccccccccccccccccccccccccccccccccccc",
            "ddddddddddddddddddddddddddddddddddddddd",
            "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            "fffffffffffffffffffffffffffffffffffffff",
        ];
        
        // Create parent-child relationships
        for i in 0..commits.len() - 1 {
            let child = oid::hex(commits[i]).unwrap();
            let parent = oid::hex(commits[i + 1]).unwrap();
            graph.commits.insert(child, vec![parent]);
        }
        
        // Add tags
        graph.tags.insert(oid::hex(commits[1]).unwrap(), vec!["v1.0".to_string()]);
        graph.tags.insert(oid::hex(commits[3]).unwrap(), vec!["v2.0".to_string()]);
        
        graph
    }
}

// Implement the Graph trait required by describe()
impl Graph for SimpleGraph {
    fn parents(&self, id: ObjectId) -> Option<Vec<ObjectId>> {
        self.commits.get(&id).cloned()
    }
    
    fn contains(&self, id: ObjectId) -> bool {
        self.commits.contains_key(&id)
    }
}

fn describe_commit(commit_id: &str, graph: &SimpleGraph) -> Result<String, Box<dyn std::error::Error>> {
    let oid = oid::hex(commit_id)?;
    
    // In a real implementation, reference_names would be a closure that
    // queries the repository for references pointing to the given object
    let reference_names = |id: ObjectId| -> Vec<String> {
        graph.tags.get(&id).cloned().unwrap_or_default()
    };
    
    // Call the describe function
    let description = describe(
        oid,
        graph,
        reference_names,
        gix_revision::describe::Strategy::Default,
        0,
        None,
    )?;
    
    // Format the result based on the kind of description
    Ok(match description {
        gix_revision::describe::Description::Tag { name, distance, id } => {
            if distance == 0 {
                format!("{}", name)
            } else {
                format!("{}-{}-g{}", name, distance, id.to_hex_with_len(7))
            }
        }
        gix_revision::describe::Description::CommitOnly(id) => {
            format!("g{}", id.to_hex_with_len(7))
        }
    })
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let graph = SimpleGraph::new();
    
    // Describe various commits in the graph
    let commits = [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  // 2 commits after v1.0
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",  // exactly at v1.0
        "ddddddddddddddddddddddddddddddddddddddd",  // exactly at v2.0
        "fffffffffffffffffffffffffffffffffffffff",  // 2 commits before v2.0
    ];
    
    for commit in &commits {
        let description = describe_commit(commit, &graph)?;
        println!("Commit {}: {}", &commit[..7], description);
    }
    
    Ok(())
}
```

## Use Case 3: Finding Common Ancestors (Merge Base)

### Problem

When merging branches or comparing commits, you need to identify the common ancestor(s) of multiple commits.

### Solution

Use the `merge_base` function to find common ancestors between multiple commits.

```rust
use gix_hash::{ObjectId, oid};
use gix_revision::{merge_base, Graph};
use std::collections::{HashMap, HashSet};

// A simple graph implementation for the example
struct SimpleGraph {
    commits: HashMap<ObjectId, Vec<ObjectId>>,
}

impl SimpleGraph {
    fn new() -> Self {
        let mut graph = SimpleGraph {
            commits: HashMap::new(),
        };
        
        // Set up a commit graph with branches
        //     A
        //    / \
        //   B   C
        //  / \ / \
        // D   E   F
        //  \ /
        //   G
        
        let commits = [
            ("a", vec!["b", "c"]),
            ("b", vec!["d", "e"]),
            ("c", vec!["e", "f"]),
            ("d", vec!["g"]),
            ("e", vec!["g"]),
            ("f", vec![]),
            ("g", vec![]),
        ];
        
        for (commit, parents) in &commits {
            let oid = oid::hex(&format!("{:>40}", commit)).unwrap();
            let parent_oids = parents
                .iter()
                .map(|p| oid::hex(&format!("{:>40}", p)).unwrap())
                .collect();
            
            graph.commits.insert(oid, parent_oids);
        }
        
        graph
    }
}

// Implement the Graph trait required by merge_base
impl Graph for SimpleGraph {
    fn parents(&self, id: ObjectId) -> Option<Vec<ObjectId>> {
        self.commits.get(&id).cloned()
    }
    
    fn contains(&self, id: ObjectId) -> bool {
        self.commits.contains_key(&id)
    }
}

fn find_common_ancestors(
    commit1: &str,
    commit2: &str,
    graph: &SimpleGraph
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let oid1 = oid::hex(&format!("{:>40}", commit1))?;
    let oid2 = oid::hex(&format!("{:>40}", commit2))?;
    
    // Call the merge_base function
    let common_ancestors = merge_base(
        &[oid1, oid2],
        graph,
        merge_base::Mode::All,
        None,
    )?;
    
    // Format the results
    let ancestors: Vec<String> = common_ancestors
        .into_iter()
        .map(|id| format!("{}", id.to_hex()[0..1].to_string()))
        .collect();
    
    Ok(ancestors)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let graph = SimpleGraph::new();
    
    // Find common ancestors for different pairs of commits
    let pairs = [
        ("a", "a"),  // Same commit
        ("b", "c"),  // Branches from a common point
        ("d", "e"),  // Different branches with common ancestor
        ("d", "f"),  // Different branches with multiple common ancestors
    ];
    
    for (commit1, commit2) in &pairs {
        let ancestors = find_common_ancestors(commit1, commit2, &graph)?;
        println!("Common ancestors of {} and {}: {}", 
                 commit1, commit2, ancestors.join(", "));
    }
    
    Ok(())
}
```

These use cases demonstrate the key functionality provided by the `gix-revision` crate for parsing revision specifications, generating human-readable commit descriptions, and finding common ancestors in a commit graph.