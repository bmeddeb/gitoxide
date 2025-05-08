# gix-diff Use Cases

This document outlines common use cases for the `gix-diff` crate, describing problems, solutions, and example code.

## Intended Audience

The `gix-diff` crate is intended for:

1. **Git Client Developers**: Those building Git client applications or tools that need to display changes between commits, working directory, or index
2. **Code Analysis Tool Developers**: Developers building tools that analyze code changes, such as code review systems or change metrics
3. **CI/CD Pipeline Implementers**: For building automated systems that need to analyze changes for specific patterns
4. **Repository Browsers**: Developers creating web or GUI interfaces for browsing Git repositories and visualizing changes

## Use Case 1: Comparing Two Git Trees

### Problem

You need to list all changes (added, removed, modified files) between two Git trees (such as two commits).

### Solution

Use the `tree` function to traverse and compare two trees, collecting all differences.

### Example

```rust
use gix_diff::tree::{self, Recorder};
use gix_object::find::existing_iter::Find;
use gix_hash::ObjectId;

fn show_changes_between_commits(
    repo: &impl Find,
    old_commit_id: &ObjectId,
    new_commit_id: &ObjectId,
) -> Result<(), Box<dyn std::error::Error>> {
    // Get tree IDs from commits
    let old_commit = repo.find_object(old_commit_id)?.into_commit();
    let new_commit = repo.find_object(new_commit_id)?.into_commit();
    
    let old_tree_id = old_commit.tree_id();
    let new_tree_id = new_commit.tree_id();
    
    // Create diff state and recorder
    let mut state = tree::State::default();
    let mut recorder = Recorder::default();
    
    // Perform the diff
    tree::diff(repo, Some(old_tree_id), Some(new_tree_id), &mut state, &mut recorder)?;
    
    // Print changes
    for change in recorder.records {
        match change.change {
            tree::visit::Change::Addition { entry, .. } => {
                println!("A {}", change.location.path_str());
            }
            tree::visit::Change::Deletion { entry, .. } => {
                println!("D {}", change.location.path_str());
            }
            tree::visit::Change::Modification { previous_entry, current_entry, .. } => {
                println!("M {}", change.location.path_str());
            }
        }
    }
    
    Ok(())
}
```

## Use Case 2: Generating Unified Diffs

### Problem

You need to show the exact text changes between two versions of a file in a unified diff format (the standard format used by `git diff`).

### Solution

Use the `blob::UnifiedDiff` struct to generate a unified diff between two file versions.

### Example

```rust
use std::path::Path;
use gix_diff::blob::{Platform, pipeline, ResourceKind};
use bstr::BString;

fn generate_unified_diff(
    repo_root: &Path,
    old_file_path: &Path,
    new_file_path: &Path,
) -> Result<String, Box<dyn std::error::Error>> {
    // Create a diff platform with worktree roots
    let roots = pipeline::WorktreeRoots::pairs(
        repo_root.into(), // old root
        repo_root.into(), // new root
    );
    
    let worktree_filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    let options = pipeline::Options::default();
    
    // Initialize the platform
    let mut platform = Platform::new(
        pipeline::Pipeline::new(roots, worktree_filter, options)?,
        &Default::default(), // attribute stack
        Default::default(),  // options
        pipeline::Mode::WorktreeToWorkingdir,
    );
    
    // Prepare the paths
    let old_path = BString::from(old_file_path.to_string_lossy().as_bytes());
    let new_path = BString::from(new_file_path.to_string_lossy().as_bytes());
    
    // Ensure we have diffable content for both files
    platform.prepare_for_diff(ResourceKind::OldOrSource, &old_path, None)?;
    platform.prepare_for_diff(ResourceKind::NewOrDestination, &new_path, None)?;
    
    // Generate unified diff
    let unified_diff = platform.unified_diff(
        &old_path,
        &new_path,
        old_file_path.to_string_lossy().as_ref(),
        new_file_path.to_string_lossy().as_ref(),
        3, // context lines
    )?;
    
    Ok(unified_diff.to_string())
}
```

## Use Case 3: Detecting Renamed Files

### Problem

When comparing two trees, you need to detect files that were renamed rather than treating them as separate deletion and addition operations.

### Solution

Use the `tree_with_rewrites` function with a configured `Rewrites` struct to enable rename detection with appropriate similarity thresholds.

### Example

```rust
use gix_diff::{Rewrites, tree_with_rewrites, rewrites::Copies};
use gix_object::find::existing_iter::Find;
use gix_hash::ObjectId;

fn detect_renamed_files(
    repo: &impl Find,
    old_tree_id: &ObjectId,
    new_tree_id: &ObjectId,
) -> Result<(), Box<dyn std::error::Error>> {
    // Configure rewrite detection
    let rewrites = Rewrites {
        // Don't detect copies, only renames
        copies: None,
        // 50% similarity threshold for rename detection
        percentage: Some(0.5),
        // Limit comparisons to prevent performance issues
        limit: 1000,
        // Don't track empty files
        track_empty: false,
    };
    
    // Perform the diff with rewrite detection
    let changes = tree_with_rewrites(
        repo,
        Some(old_tree_id),
        Some(new_tree_id),
        &rewrites,
        Default::default(), // tree state
        Default::default(), // platform options
    )?;
    
    // Process and display changes
    for change in changes {
        match change {
            gix_diff::tree_with_rewrites::Change::Addition { .. } => {
                // Handle additions
            }
            gix_diff::tree_with_rewrites::Change::Deletion { .. } => {
                // Handle deletions
            }
            gix_diff::tree_with_rewrites::Change::Modification { .. } => {
                // Handle modifications
            }
            gix_diff::tree_with_rewrites::Change::Rename { from_path, to_path, .. } => {
                println!("Renamed: {} -> {}", from_path, to_path);
            }
            gix_diff::tree_with_rewrites::Change::Copy { from_path, to_path, .. } => {
                // This won't occur with our settings, but would handle copies
            }
        }
    }
    
    Ok(())
}
```

## Use Case 4: Comparing Working Directory with Index

### Problem

You need to identify changes between the Git index (staging area) and the working directory, respecting git attributes.

### Solution

Use the `index` function to compare the index contents with the actual files in the working directory.

### Example

```rust
use gix_diff::index;
use gix_index::File as IndexFile;
use std::path::Path;

fn compare_index_with_working_dir(
    repo_path: &Path,
    index_file: &IndexFile,
) -> Result<(), Box<dyn std::error::Error>> {
    // Configure diff options
    let options = index::Options {
        include_untracked: true,
        ..Default::default()
    };
    
    // Perform the diff
    let changes = index::diff(
        index_file,
        repo_path,
        &index::Algorithm::PlatformDefault,
        options,
    )?;
    
    // Process changes
    for change in changes {
        match change {
            index::Change::Addition { path, .. } => {
                println!("Added in working dir: {}", path);
            }
            index::Change::Deletion { path, .. } => {
                println!("Deleted from working dir: {}", path);
            }
            index::Change::Modification { path, .. } => {
                println!("Modified in working dir: {}", path);
            }
        }
    }
    
    Ok(())
}
```

## Use Case 5: Custom Filtering of Diff Results

### Problem

You need to perform a diff operation, but want to customize how the diff is traversed and which results are recorded.

### Solution

Implement the `tree::Visit` trait to create a custom visitor that can control traversal and selectively record changes.

### Example

```rust
use gix_diff::tree::{self, Visit, visit::{Action, Change}};
use gix_object::bstr::BStr;
use bstr::BString;

// A custom visitor that only records changes to Rust source files
struct RustFilesVisitor {
    path: BString,
    changes: Vec<String>,
}

impl RustFilesVisitor {
    fn new() -> Self {
        Self {
            path: BString::default(),
            changes: Vec::new(),
        }
    }
}

impl Visit for RustFilesVisitor {
    fn pop_front_tracked_path_and_set_current(&mut self) {
        // Not used in this implementation
    }
    
    fn push_back_tracked_path_component(&mut self, component: &BStr) {
        // Not used in this implementation
    }
    
    fn push_path_component(&mut self, component: &BStr) {
        if !self.path.is_empty() {
            self.path.push(b'/');
        }
        self.path.extend_from_slice(component);
    }
    
    fn pop_path_component(&mut self) {
        if let Some(pos) = self.path.rfind(b'/') {
            self.path.truncate(pos);
        } else {
            self.path.clear();
        }
    }
    
    fn visit(&mut self, change: Change) -> Action {
        // Only record changes to .rs files
        if self.path.ends_with(b".rs") {
            match change {
                Change::Addition { .. } => {
                    self.changes.push(format!("A {}", String::from_utf8_lossy(&self.path)));
                }
                Change::Deletion { .. } => {
                    self.changes.push(format!("D {}", String::from_utf8_lossy(&self.path)));
                }
                Change::Modification { .. } => {
                    self.changes.push(format!("M {}", String::from_utf8_lossy(&self.path)));
                }
            }
        }
        
        // Continue traversal
        Action::Continue
    }
}

// Usage example
fn diff_rust_files(
    repo: &impl gix_object::find::existing_iter::Find,
    old_tree_id: Option<&gix_hash::ObjectId>,
    new_tree_id: Option<&gix_hash::ObjectId>,
) -> Result<Vec<String>, tree::Error> {
    let mut state = tree::State::default();
    let mut visitor = RustFilesVisitor::new();
    
    tree::diff(repo, old_tree_id, new_tree_id, &mut state, &mut visitor)?;
    
    Ok(visitor.changes)
}
```

## Use Case 6: Handling Binary Files in Diffs

### Problem

You need to properly handle binary files in diff operations, possibly with custom processing.

### Solution

Use the `blob::Platform` with appropriate configuration to detect and process binary files according to Git attributes.

### Example

```rust
use gix_diff::blob::{self, Platform, pipeline, ResourceKind, Driver};
use bstr::BString;
use std::path::Path;

fn process_binary_file_diff(
    repo_root: &Path,
    old_binary_path: &Path,
    new_binary_path: &Path,
) -> Result<String, Box<dyn std::error::Error>> {
    // Create roots for the diff
    let roots = pipeline::WorktreeRoots::pairs(
        repo_root.into(),
        repo_root.into(),
    );
    
    // Configure filter pipeline with binary file handling
    let filter_options = gix_filter::Options::default();
    let worktree_filter = gix_filter::Pipeline::from_attributes(None, &filter_options);
    
    // Configure platform options
    let mut options = blob::platform::Options::default();
    
    // Create custom binary file driver
    let binary_driver = Driver {
        name: BString::from("binary"),
        command: None,
        algorithm: None,
        // Specify a command to convert binary to text if needed
        binary_to_text_command: Some(BString::from("hexdump -C")),
        // Explicitly mark as binary
        is_binary: Some(true),
    };
    
    // Create and configure the platform
    let mut platform = Platform::with_drivers(
        pipeline::Pipeline::new(
            roots,
            worktree_filter,
            pipeline::Options::default(),
        )?,
        &Default::default(), // attribute stack
        options,
        pipeline::Mode::WorktreeToWorkingdir,
        vec![binary_driver],
    );
    
    // Prepare paths for diff
    let old_path = BString::from(old_binary_path.to_string_lossy().as_bytes());
    let new_path = BString::from(new_binary_path.to_string_lossy().as_bytes());
    
    // Prepare content for diffing
    platform.prepare_for_diff(ResourceKind::OldOrSource, &old_path, None)?;
    platform.prepare_for_diff(ResourceKind::NewOrDestination, &new_path, None)?;
    
    // Get binary file stats even if we can't diff the content
    let stats = platform.diff(&old_path, &new_path)?;
    
    // Return description of binary diff
    Ok(format!(
        "Binary files differ: {} vs {}\nSize change: {} -> {} bytes",
        old_binary_path.display(),
        new_binary_path.display(),
        stats.before,
        stats.after
    ))
}
```

## Use Case 7: Integrating with Custom Object Storage

### Problem

You need to perform diffs against objects stored in a custom object database or non-standard storage.

### Solution

Implement the `gix_object::find::existing_iter::Find` trait for your custom storage and use it with `gix-diff` functions.

### Example

```rust
use gix_diff::tree;
use gix_object::find::existing_iter::{Find, Result as FindResult};
use gix_hash::ObjectId;
use std::collections::HashMap;

// A simple in-memory object store for demonstration
struct InMemoryObjectStore {
    objects: HashMap<ObjectId, Vec<u8>>,
}

impl InMemoryObjectStore {
    fn new() -> Self {
        Self {
            objects: HashMap::new(),
        }
    }
    
    fn add_object(&mut self, id: ObjectId, data: Vec<u8>) {
        self.objects.insert(id, data);
    }
}

// Implement Find trait for custom store
impl Find for InMemoryObjectStore {
    fn find_object(&self, id: &ObjectId) -> FindResult<gix_object::Object> {
        match self.objects.get(id) {
            Some(data) => {
                // Parse the raw data into a Git object
                let obj = gix_object::parse(data, Some(*id))?;
                Ok(obj)
            }
            None => Err(gix_object::find::existing_iter::Error::NotFound(*id)),
        }
    }
}

// Using the custom store with gix-diff
fn diff_with_custom_store() -> Result<(), Box<dyn std::error::Error>> {
    let mut store = InMemoryObjectStore::new();
    
    // Populate store with objects (in a real scenario, these would come from your storage)
    // ...
    
    // Create tree objects for diffing
    let tree1_id = ObjectId::from_hex("4b825dc642cb6eb9a060e54bf8d69288fbee4904")?;
    let tree2_id = ObjectId::from_hex("8b9af3b4d1535ff9f061c8b94df57d4b66b3a17a")?;
    
    // Perform diff using custom store
    let mut state = tree::State::default();
    let mut recorder = tree::Recorder::default();
    
    tree::diff(&store, Some(&tree1_id), Some(&tree2_id), &mut state, &mut recorder)?;
    
    // Process results
    for change in recorder.records {
        println!("{:?}: {}", change.change, change.location.path_str());
    }
    
    Ok(())
}
```