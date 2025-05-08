# gix-status Use Cases

This document outlines common use cases for the `gix-status` crate, describing problems, solutions, and example code.

## Intended Audience

The `gix-status` crate is intended for:

1. **Git Client Developers**: Those building Git client applications or tools that need to display and manipulate repository status
2. **Text Editors and IDEs**: For integrating Git status information in real-time
3. **DevOps Tool Developers**: Creating deployment tools that need to verify clean states
4. **Repository Management System Developers**: Building systems that need to track working directory changes

## Use Case 1: Checking If a Repository Is Dirty

### Problem

You need to quickly determine if a Git repository has any uncommitted changes without collecting detailed information about each change.

### Solution

Use `index_as_worktree` with the `early_termination_on_first_change` option to stop processing as soon as a change is found.

### Example

```rust
use gix_features::progress::Discard;
use gix_index::State as IndexState;
use gix_object::Find;
use gix_pathspec::Search;
use gix_status::{index_as_worktree, SymlinkCheck};
use std::path::Path;
use std::sync::atomic::AtomicBool;

/// A simple implementation to check if blobs are different
struct SimpleBlobCompare;

impl index_as_worktree::traits::CompareBlobs for SimpleBlobCompare {
    type Output = ();
    
    fn compare_blobs(
        &self,
        _a_id: &gix_hash::ObjectId,
        a_data: &[u8],
        _b_id: &gix_hash::ObjectId,
        b_data: &[u8],
    ) -> Self::Output {
        // We don't care about the details, just if they differ
        // This implementation just returns () in all cases
    }
}

/// A simple implementation that doesn't actually check submodules
struct NoopSubmoduleCheck;

impl index_as_worktree::traits::SubmoduleStatus for NoopSubmoduleCheck {
    type Output = ();
    type Error = std::io::Error;
    
    fn check_submodule(
        &self,
        _worktree_path: &Path,
        _rela_path: &bstr::BStr,
    ) -> Result<Self::Output, Self::Error> {
        Ok(())
    }
}

/// Check if the repository is dirty with early termination
fn is_repository_dirty(
    repo_path: &Path,
    index: &IndexState,
    object_db: &impl Find,
) -> Result<bool, Box<dyn std::error::Error>> {
    // Create a simple recorder to detect changes
    let mut recorder = index_as_worktree::Recorder::default();
    
    // Create attribute stack and filter pipeline
    let stack = gix_worktree::Stack::from_attributes(None);
    let filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    
    // Setup context with empty pathspec (match all files)
    let interrupt = AtomicBool::new(false);
    let context = index_as_worktree::Context {
        pathspec: Search::new(Vec::new()),
        stack,
        filter,
        should_interrupt: &interrupt,
    };
    
    // Configure options for early termination
    let mut options = index_as_worktree::Options::default();
    options.early_termination_on_first_change = true;
    
    // Run the status check
    let outcome = index_as_worktree(
        index,
        repo_path,
        &mut recorder,
        SimpleBlobCompare,
        NoopSubmoduleCheck,
        object_db,
        &mut Discard,
        context,
        options,
    )?;
    
    // If we found any changes, the repository is dirty
    Ok(!recorder.records.is_empty())
}
```

## Use Case 2: Creating a Full Status Report

### Problem

You need to generate a detailed report of all changes in the repository, similar to what `git status` displays.

### Solution

Use `index_as_worktree_with_renames` to collect all types of changes including renames, and process them into a human-readable format.

### Example

```rust
use gix_features::progress::{Discard, Progress};
use gix_index::State as IndexState;
use gix_object::{Find, FindHeader};
use gix_status::{index_as_worktree, index_as_worktree_with_renames, SymlinkCheck};
use std::path::Path;
use std::sync::atomic::AtomicBool;

/// Implementation to collect detailed content changes
struct ContentChangeCollector;

impl index_as_worktree::traits::CompareBlobs for ContentChangeCollector {
    type Output = (usize, usize); // (insertions, deletions)
    
    fn compare_blobs(
        &self,
        _a_id: &gix_hash::ObjectId,
        a_data: &[u8],
        _b_id: &gix_hash::ObjectId,
        b_data: &[u8],
    ) -> Self::Output {
        // This is simplified - in reality you'd use a diff algorithm
        // to compute actual insertions and deletions
        let a_lines = a_data.split(|&b| b == b'\n').count();
        let b_lines = b_data.split(|&b| b == b'\n').count();
        
        if a_lines > b_lines {
            (0, a_lines - b_lines)
        } else {
            (b_lines - a_lines, 0)
        }
    }
}

/// Implementation to check submodule status
struct SubmoduleStatusCheck;

impl index_as_worktree::traits::SubmoduleStatus for SubmoduleStatusCheck {
    type Output = bool; // true if submodule is modified
    type Error = std::io::Error;
    
    fn check_submodule(
        &self,
        worktree_path: &Path,
        rela_path: &bstr::BStr,
    ) -> Result<Self::Output, Self::Error> {
        let submodule_path = worktree_path.join(gix_path::from_bstr(rela_path));
        
        // In a real implementation, you would:
        // 1. Check if HEAD matches the recorded commit
        // 2. Check if the worktree is dirty
        // 3. Check for untracked files
        
        // Simplified implementation that always returns false
        Ok(false)
    }
}

/// Generate a full status report with rename detection
fn generate_status_report(
    repo_path: &Path,
    index: &IndexState,
    object_db: &impl Find + FindHeader + Clone,
) -> Result<String, Box<dyn std::error::Error>> {
    // Create a recorder to collect status information
    let mut recorder = index_as_worktree_with_renames::Recorder::default();
    
    // Create attribute stack and filter pipeline
    let stack = gix_worktree::Stack::from_attributes(None);
    let filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    
    // Setup context
    let interrupt = AtomicBool::new(false);
    let base_context = index_as_worktree::Context {
        pathspec: gix_pathspec::Search::new(Vec::new()),
        stack: stack.clone(),
        filter: filter.clone(),
        should_interrupt: &interrupt,
    };
    
    // Setup enhanced context with resource cache
    let resource_cache = gix_diff::rewrites::ResourceCache {
        attr_stack: stack,
        filter: gix_diff::blob::pipeline::FilterWithDriver {
            worktree_filter: filter,
            drivers: Vec::new(),
        },
    };
    
    let context = index_as_worktree_with_renames::Context {
        pathspec: gix_pathspec::Search::new(Vec::new()),
        should_interrupt: &interrupt,
        resource_cache,
        dirwalk: index_as_worktree_with_renames::DirwalkContext::default(),
    };
    
    // Configure options with rename detection
    let options = index_as_worktree_with_renames::Options {
        tracked_file_modifications: index_as_worktree::Options::default(),
        dirwalk: Some(gix_dir::walk::Options::default()),
        rewrites: Some(gix_diff::Rewrites {
            copies: None, // Only detect renames, not copies
            percentage: Some(0.5), // 50% similarity threshold
            limit: 1000,
            track_empty: false,
        }),
        object_hash: gix_hash::Kind::Sha1, // Use appropriate hash algorithm
        sorting: Some(index_as_worktree_with_renames::Sorting::ByPath),
    };
    
    // Run the status check
    let outcome = index_as_worktree_with_renames(
        index,
        repo_path,
        &mut recorder,
        ContentChangeCollector,
        SubmoduleStatusCheck,
        object_db.clone(),
        &mut Discard,
        context,
        options,
    )?;
    
    // Generate the report from the recorded entries
    let mut report = String::new();
    
    // Changes to be committed (staged changes)
    // This would require a separate check between HEAD and index
    
    // Changes not staged for commit
    report.push_str("Changes not staged for commit:\n");
    for entry in &recorder.entries {
        use index_as_worktree_with_renames::Entry;
        match entry {
            Entry::Modification { rela_path, status, .. } => {
                use index_as_worktree::EntryStatus;
                match status {
                    EntryStatus::Change(change) => {
                        use index_as_worktree::Change;
                        match change {
                            Change::Removed => {
                                report.push_str(&format!("    deleted:    {}\n", 
                                    String::from_utf8_lossy(rela_path)));
                            }
                            Change::Type { .. } => {
                                report.push_str(&format!("    typechange: {}\n", 
                                    String::from_utf8_lossy(rela_path)));
                            }
                            Change::Modification { .. } => {
                                report.push_str(&format!("    modified:   {}\n", 
                                    String::from_utf8_lossy(rela_path)));
                            }
                            Change::SubmoduleModification(_) => {
                                report.push_str(&format!("    modified:   {} (submodule)\n", 
                                    String::from_utf8_lossy(rela_path)));
                            }
                        }
                    }
                    EntryStatus::Conflict(_) => {
                        report.push_str(&format!("    conflict:   {}\n", 
                            String::from_utf8_lossy(rela_path)));
                    }
                    _ => {}
                }
            }
            Entry::Rewrite { dirwalk_entry, copy, .. } => {
                let action = if *copy { "copied:" } else { "renamed:" };
                report.push_str(&format!("    {}    {}\n", 
                    action, String::from_utf8_lossy(&dirwalk_entry.rela_path)));
            }
            Entry::DirectoryContents { entry, .. } => {
                if entry.status.is_untracked() {
                    if !report.contains("Untracked files:") {
                        report.push_str("\nUntracked files:\n");
                    }
                    report.push_str(&format!("    {}\n", 
                        String::from_utf8_lossy(&entry.rela_path)));
                }
            }
        }
    }
    
    Ok(report)
}
```

## Use Case 3: Real-time Status Monitoring in an Editor

### Problem

You are building a text editor with Git integration and need to provide real-time status information about files being edited.

### Solution

Use `index_as_worktree` with pathspec filtering to check only the status of specific files currently open in the editor.

### Example

```rust
use bstr::BString;
use gix_features::progress::Discard;
use gix_index::State as IndexState;
use gix_object::Find;
use gix_pathspec::{Pattern, Search};
use gix_status::{index_as_worktree, SymlinkCheck};
use std::path::{Path, PathBuf};
use std::sync::atomic::AtomicBool;

/// Status information for a file in the editor
struct FileStatus {
    path: PathBuf,
    is_modified: bool,
    is_staged: bool,
    is_untracked: bool,
    is_conflicted: bool,
}

/// Check status of specific files in the repository
fn check_file_statuses(
    repo_path: &Path,
    index: &IndexState,
    object_db: &impl Find,
    files: &[PathBuf],
) -> Result<Vec<FileStatus>, Box<dyn std::error::Error>> {
    // Convert file paths to repository-relative paths and create pathspec
    let mut patterns = Vec::new();
    for file in files {
        let rel_path = file.strip_prefix(repo_path)?.to_path_buf();
        let pattern_str = BString::from(rel_path.to_string_lossy().as_bytes());
        patterns.push(Pattern::new(pattern_str, Pattern::Attributes::default()));
    }
    let pathspec = Search::new(patterns);
    
    // Setup status checking
    let mut recorder = index_as_worktree::Recorder::default();
    let stack = gix_worktree::Stack::from_attributes(None);
    let filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    
    let interrupt = AtomicBool::new(false);
    let context = index_as_worktree::Context {
        pathspec,
        stack,
        filter,
        should_interrupt: &interrupt,
    };
    
    // Run status check for specified files
    let outcome = index_as_worktree(
        index,
        repo_path,
        &mut recorder,
        SimpleBlobCompare, // Define this as in the first example
        NoopSubmoduleCheck, // Define this as in the first example
        object_db,
        &mut Discard,
        context,
        index_as_worktree::Options::default(),
    )?;
    
    // Convert results to FileStatus objects
    let mut results = Vec::new();
    
    // Process the status records
    for record in recorder.records {
        let path = repo_path.join(gix_path::from_bstr(record.relative_path));
        
        let mut status = FileStatus {
            path,
            is_modified: false,
            is_staged: false, // Would need index vs HEAD comparison
            is_untracked: false,
            is_conflicted: false,
        };
        
        match &record.status {
            index_as_worktree::EntryStatus::Conflict(_) => {
                status.is_conflicted = true;
            }
            index_as_worktree::EntryStatus::Change(change) => {
                match change {
                    index_as_worktree::Change::Removed 
                    | index_as_worktree::Change::Type { .. }
                    | index_as_worktree::Change::Modification { .. }
                    | index_as_worktree::Change::SubmoduleModification(_) => {
                        status.is_modified = true;
                    }
                }
            }
            index_as_worktree::EntryStatus::IntentToAdd => {
                status.is_untracked = true;
                status.is_staged = true;
            }
            _ => {}
        }
        
        results.push(status);
    }
    
    // Add untracked files not found in index
    // This would require additional directory scanning
    
    Ok(results)
}
```

## Use Case 4: Security-Conscious Repository Validation

### Problem

You're developing a deployment tool that needs to verify repository status while ensuring protection against potential symlink attacks.

### Solution

Use the `SymlinkCheck` functionality along with `index_as_worktree` to safely validate repository status before deployment.

### Example

```rust
use bstr::BString;
use gix_features::progress::Discard;
use gix_index::State as IndexState;
use gix_object::Find;
use gix_status::{index_as_worktree, SymlinkCheck};
use std::path::{Path, PathBuf};
use std::sync::atomic::AtomicBool;

/// Error type for deployment validation
#[derive(Debug, thiserror::Error)]
enum DeploymentError {
    #[error("Repository contains uncommitted changes")]
    DirtyRepository,
    #[error("Potential security risk: symlink traversal detected at {0}")]
    SymlinkTraversal(PathBuf),
    #[error("Status check failed: {0}")]
    StatusCheck(#[from] Box<dyn std::error::Error + Send + Sync>),
}

/// Safely validate repository status before deployment
fn validate_repository_for_deployment(
    repo_path: &Path,
    index: &IndexState,
    object_db: &impl Find,
) -> Result<(), DeploymentError> {
    // Create a symlink checker
    let mut symlink_check = SymlinkCheck::new(repo_path.to_path_buf());
    
    // Check if the repository is clean
    let interrupt = AtomicBool::new(false);
    let stack = gix_worktree::Stack::from_attributes(None);
    let filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    
    let mut recorder = index_as_worktree::Recorder::default();
    let context = index_as_worktree::Context {
        pathspec: gix_pathspec::Search::new(Vec::new()),
        stack,
        filter,
        should_interrupt: &interrupt,
    };
    
    // Configure options for early termination
    let mut options = index_as_worktree::Options::default();
    options.early_termination_on_first_change = true;
    
    // Run the status check
    let outcome = index_as_worktree(
        index,
        repo_path,
        &mut recorder,
        SimpleBlobCompare, // Define this as in the first example
        NoopSubmoduleCheck, // Define this as in the first example
        object_db,
        &mut Discard,
        context,
        options,
    ).map_err(|e| DeploymentError::StatusCheck(Box::new(e)))?;
    
    // Check for uncommitted changes
    if !recorder.records.is_empty() {
        return Err(DeploymentError::DirtyRepository);
    }
    
    // Verify critical deployment paths for symlink traversal
    let critical_paths = [
        "config",
        "scripts/deploy.sh",
        "credentials",
    ];
    
    for path in critical_paths {
        let bstr_path = BString::from(path.as_bytes());
        
        // Check if path would traverse a symlink
        match symlink_check.verified_path_allow_nonexisting(&bstr_path) {
            Ok(_) => {
                // Path is safe
            }
            Err(e) if e.kind() == std::io::ErrorKind::Other && 
                      e.to_string().contains("Cannot step through symlink") => {
                // Symlink traversal detected
                return Err(DeploymentError::SymlinkTraversal(PathBuf::from(path)));
            }
            Err(e) => {
                // Other error
                return Err(DeploymentError::StatusCheck(Box::new(e)));
            }
        }
    }
    
    // All checks passed, repository is valid for deployment
    Ok(())
}
```

## Use Case 5: Optimizing Status for Large Repositories

### Problem

You need to check the status of a large repository efficiently, focusing on specific areas and minimizing resource usage.

### Solution

Use a combination of pathspec filtering, parallel processing control, and early termination to optimize status checks for large repositories.

### Example

```rust
use gix_features::progress::{Progress, Count};
use gix_index::State as IndexState;
use gix_object::Find;
use gix_pathspec::{Pattern, Search};
use gix_status::{index_as_worktree, SymlinkCheck};
use std::path::Path;
use std::sync::atomic::AtomicBool;

/// Configuration for optimized status checking
struct OptimizedStatusConfig {
    /// Only check paths within these directories
    focus_paths: Vec<String>,
    /// Maximum number of threads to use
    thread_limit: Option<usize>,
    /// Stop after finding this many changes (0 = no limit)
    max_changes: usize,
    /// Show progress information
    show_progress: bool,
}

/// Run an optimized status check on a large repository
fn optimized_status_check(
    repo_path: &Path,
    index: &IndexState,
    object_db: &impl Find,
    config: OptimizedStatusConfig,
) -> Result<Vec<index_as_worktree::Record>, Box<dyn std::error::Error>> {
    // Create pathspec from focus paths
    let mut patterns = Vec::new();
    for path in &config.focus_paths {
        patterns.push(Pattern::new(
            bstr::BString::from(path.as_bytes()), 
            Pattern::Attributes::default()
        ));
    }
    let pathspec = Search::new(patterns);
    
    // Setup context
    let interrupt = AtomicBool::new(false);
    let stack = gix_worktree::Stack::from_attributes(None);
    let filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    
    let context = index_as_worktree::Context {
        pathspec,
        stack,
        filter,
        should_interrupt: &interrupt,
    };
    
    // Configure options
    let mut options = index_as_worktree::Options::default();
    options.thread_limit = config.thread_limit;
    
    // Create recorder with optional limit
    let mut recorder = if config.max_changes > 0 {
        let mut recorder = index_as_worktree::Recorder::default();
        recorder.set_limit(config.max_changes, &interrupt);
        recorder
    } else {
        index_as_worktree::Recorder::default()
    };
    
    // Setup progress reporting
    let mut progress: Box<dyn Progress> = if config.show_progress {
        Box::new(Count::new("files checked", None))
    } else {
        Box::new(Discard)
    };
    
    // Run the status check
    let outcome = index_as_worktree(
        index,
        repo_path,
        &mut recorder,
        ContentChangeCollector, // Define this as in the second example
        SubmoduleStatusCheck, // Define this as in the second example
        object_db,
        progress.as_mut(),
        context,
        options,
    )?;
    
    // Print some stats about the operation
    if config.show_progress {
        println!("Status check stats:");
        println!("  Entries processed: {}/{}", 
            outcome.entries_processed, outcome.entries_to_process);
        println!("  Entries skipped by pathspec: {}", 
            outcome.entries_skipped_by_pathspec);
        println!("  Files read: {} ({}bytes)", 
            outcome.worktree_files_read, outcome.worktree_bytes);
        println!("  Objects read: {} ({}bytes)", 
            outcome.odb_objects_read, outcome.odb_bytes);
    }
    
    Ok(recorder.records)
}
```

## Use Case 6: Conflict Detection and Resolution

### Problem

You need to detect and handle conflicts in a Git repository, such as during a merge or rebase operation.

### Solution

Use `index_as_worktree` to detect conflicts and provide information to help users resolve them.

### Example

```rust
use bstr::BStr;
use gix_features::progress::Discard;
use gix_index::{Entry, State as IndexState};
use gix_object::Find;
use gix_status::{index_as_worktree, SymlinkCheck};
use std::path::Path;
use std::sync::atomic::AtomicBool;

/// Information about a conflict
struct ConflictInfo {
    path: String,
    conflict_type: String,
    our_id: Option<String>,
    their_id: Option<String>,
    resolution_hint: String,
}

/// Conflict-specific visitor implementation
struct ConflictVisitor {
    conflicts: Vec<ConflictInfo>,
}

impl ConflictVisitor {
    fn new() -> Self {
        Self { conflicts: Vec::new() }
    }
}

impl<'index> index_as_worktree::VisitEntry<'index> for ConflictVisitor {
    type ContentChange = ();
    type SubmoduleStatus = ();
    
    fn visit_entry(
        &mut self,
        entries: &'index [Entry],
        entry: &'index Entry,
        entry_index: usize,
        rela_path: &'index BStr,
        status: index_as_worktree::EntryStatus<Self::ContentChange, Self::SubmoduleStatus>,
    ) {
        if let index_as_worktree::EntryStatus::Conflict(conflict) = status {
            let path = String::from_utf8_lossy(rela_path).to_string();
            
            let (conflict_type, resolution_hint) = match conflict {
                index_as_worktree::Conflict::BothDeleted => (
                    "both deleted".to_string(),
                    "Remove the file from the index".to_string()
                ),
                index_as_worktree::Conflict::AddedByUs => (
                    "added by us".to_string(),
                    "Keep our version or merge manually".to_string()
                ),
                index_as_worktree::Conflict::DeletedByThem => (
                    "deleted by them".to_string(),
                    "Either keep our version or delete it".to_string()
                ),
                index_as_worktree::Conflict::AddedByThem => (
                    "added by them".to_string(),
                    "Keep their version or merge manually".to_string()
                ),
                index_as_worktree::Conflict::DeletedByUs => (
                    "deleted by us".to_string(),
                    "Either restore their version or confirm deletion".to_string()
                ),
                index_as_worktree::Conflict::BothAdded => (
                    "both added".to_string(),
                    "Merge the contents manually".to_string()
                ),
                index_as_worktree::Conflict::BothModified => (
                    "both modified".to_string(),
                    "Merge the contents manually".to_string()
                ),
            };
            
            // Find stage 2 (our version) and stage 3 (their version) entries
            let mut our_id = None;
            let mut their_id = None;
            
            for i in 0..3 {
                if entry_index + i >= entries.len() {
                    break;
                }
                
                let e = &entries[entry_index + i];
                if e.path() != entry.path() {
                    break;
                }
                
                match e.stage() {
                    2 => our_id = Some(e.id.to_hex().to_string()),
                    3 => their_id = Some(e.id.to_hex().to_string()),
                    _ => {}
                }
            }
            
            self.conflicts.push(ConflictInfo {
                path,
                conflict_type,
                our_id,
                their_id,
                resolution_hint,
            });
        }
    }
}

/// Detect and provide information about conflicts
fn detect_conflicts(
    repo_path: &Path,
    index: &IndexState,
    object_db: &impl Find,
) -> Result<Vec<ConflictInfo>, Box<dyn std::error::Error>> {
    // Create conflict visitor
    let mut visitor = ConflictVisitor::new();
    
    // Setup context
    let interrupt = AtomicBool::new(false);
    let stack = gix_worktree::Stack::from_attributes(None);
    let filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    
    let context = index_as_worktree::Context {
        pathspec: gix_pathspec::Search::new(Vec::new()),
        stack,
        filter,
        should_interrupt: &interrupt,
    };
    
    // Run the status check
    index_as_worktree(
        index,
        repo_path,
        &mut visitor,
        SimpleBlobCompare, // Define this as in the first example
        NoopSubmoduleCheck, // Define this as in the first example
        object_db,
        &mut Discard,
        context,
        index_as_worktree::Options::default(),
    )?;
    
    Ok(visitor.conflicts)
}
```

## Use Case 7: Intent-to-Add File Detection

### Problem

You need to identify files that have been marked with `git add --intent-to-add` but haven't been fully staged yet.

### Solution

Use `index_as_worktree` to detect files with the intent-to-add status.

### Example

```rust
use bstr::BStr;
use gix_features::progress::Discard;
use gix_index::{Entry, State as IndexState};
use gix_object::Find;
use gix_status::{index_as_worktree, SymlinkCheck};
use std::path::Path;
use std::sync::atomic::AtomicBool;

/// Intent-to-add visitor implementation
struct IntentToAddVisitor {
    intent_to_add_files: Vec<String>,
}

impl IntentToAddVisitor {
    fn new() -> Self {
        Self { intent_to_add_files: Vec::new() }
    }
}

impl<'index> index_as_worktree::VisitEntry<'index> for IntentToAddVisitor {
    type ContentChange = ();
    type SubmoduleStatus = ();
    
    fn visit_entry(
        &mut self,
        _entries: &'index [Entry],
        _entry: &'index Entry,
        _entry_index: usize,
        rela_path: &'index BStr,
        status: index_as_worktree::EntryStatus<Self::ContentChange, Self::SubmoduleStatus>,
    ) {
        if let index_as_worktree::EntryStatus::IntentToAdd = status {
            let path = String::from_utf8_lossy(rela_path).to_string();
            self.intent_to_add_files.push(path);
        }
    }
}

/// Find files marked with 'git add --intent-to-add'
fn find_intent_to_add_files(
    repo_path: &Path,
    index: &IndexState,
    object_db: &impl Find,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Create intent-to-add visitor
    let mut visitor = IntentToAddVisitor::new();
    
    // Setup context
    let interrupt = AtomicBool::new(false);
    let stack = gix_worktree::Stack::from_attributes(None);
    let filter = gix_filter::Pipeline::from_attributes(None, &Default::default());
    
    let context = index_as_worktree::Context {
        pathspec: gix_pathspec::Search::new(Vec::new()),
        stack,
        filter,
        should_interrupt: &interrupt,
    };
    
    // Run the status check
    index_as_worktree(
        index,
        repo_path,
        &mut visitor,
        SimpleBlobCompare, // Define this as in the first example
        NoopSubmoduleCheck, // Define this as in the first example
        object_db,
        &mut Discard,
        context,
        index_as_worktree::Options::default(),
    )?;
    
    Ok(visitor.intent_to_add_files)
}
```