# gix-dir Use Cases

The `gix-dir` crate provides functionality for Git-style directory traversal. This document outlines common use cases for this crate.

## Intended Audience

- **Git-like Tool Developers**: Building tools that need to traverse and classify files in a Git repository
- **File System Utility Developers**: Creating utilities that need Git-aware file traversal
- **Git Operation Implementers**: Implementing Git operations that need file system traversal and classification

## Use Case: Finding Untracked Files

### Problem

You need to identify all untracked files in a Git repository, which requires efficiently walking the directory structure while respecting `.gitignore` rules and the Git index.

### Solution

Use `gix-dir` to walk the repository directory tree and filter for untracked entries.

```rust
use gix_dir::{walk, entry::Status, walk::delegate::Collect};
use std::path::Path;

fn find_untracked_files(repo_path: &Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Set up context and pathspec
    let repo = gix::open(repo_path)?;
    let index = repo.index()?;
    let mut excludes = repo.excludes()?;
    let objects = repo.objects();
    let git_dir = repo.git_dir().to_path_buf();
    let current_dir = std::env::current_dir()?;
    let mut pathspec = gix_pathspec::Search::default();
    
    let mut delegate = Collect::default();
    
    let ctx = gix_dir::walk::Context {
        should_interrupt: None,
        git_dir_realpath: &git_dir,
        current_dir: &current_dir,
        index: index.read()?,
        ignore_case_index_lookup: None,
        pathspec: &mut pathspec,
        pathspec_attributes: &mut |_, _, _, _| false,
        excludes: Some(&mut excludes),
        objects,
        explicit_traversal_root: None,
    };
    
    let options = gix_dir::walk::Options {
        emit_pruned: false,
        emit_ignored: None,
        emit_untracked: gix_dir::walk::EmissionMode::Matching,
        emit_tracked: false,
        emit_empty_directories: false,
        ..Default::default()
    };
    
    walk(repo_path, ctx, options, &mut delegate)?;
    
    // Extract untracked files from collected entries
    let untracked_files = delegate
        .unorded_entries
        .into_iter()
        .filter(|(entry, _)| matches!(entry.status, Status::Untracked))
        .map(|(entry, _)| entry.rela_path.to_string())
        .collect();
    
    Ok(untracked_files)
}
```

## Use Case: Implementing `git clean`

### Problem

You need to implement a function that can identify and remove untracked files, similar to `git clean`, while being careful to respect nested repositories and ignored files.

### Solution

Use `gix-dir` with deletion-specific options to safely identify files that can be removed.

```rust
use gix_dir::{walk, entry::Status, walk::delegate::Collect, walk::ForDeletionMode};
use std::{path::Path, fs};

fn clean_untracked_files(
    repo_path: &Path,
    include_ignored: bool,
    dry_run: bool
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Set up context and pathspec
    let repo = gix::open(repo_path)?;
    let index = repo.index()?;
    let mut excludes = repo.excludes()?;
    let objects = repo.objects();
    let git_dir = repo.git_dir().to_path_buf();
    let current_dir = std::env::current_dir()?;
    let mut pathspec = gix_pathspec::Search::default();
    
    let mut delegate = Collect::default();
    
    let ctx = gix_dir::walk::Context {
        should_interrupt: None,
        git_dir_realpath: &git_dir,
        current_dir: &current_dir,
        index: index.read()?,
        ignore_case_index_lookup: None,
        pathspec: &mut pathspec,
        pathspec_attributes: &mut |_, _, _, _| false,
        excludes: Some(&mut excludes),
        objects,
        explicit_traversal_root: None,
    };
    
    let options = gix_dir::walk::Options {
        emit_pruned: false,
        emit_ignored: if include_ignored {
            Some(gix_dir::walk::EmissionMode::Matching)
        } else {
            None
        },
        emit_untracked: gix_dir::walk::EmissionMode::Matching,
        emit_tracked: false,
        emit_empty_directories: true,
        for_deletion: Some(ForDeletionMode::FindNonBareRepositoriesInIgnoredDirectories),
        ..Default::default()
    };
    
    walk(repo_path, ctx, options, &mut delegate)?;
    
    // Filter entries based on status
    let mut files_to_clean: Vec<String> = Vec::new();
    
    for (entry, _) in delegate.unorded_entries {
        let path = repo_path.join(entry.rela_path.to_string());
        let should_clean = match entry.status {
            Status::Untracked => true,
            Status::Ignored(_) if include_ignored => true,
            _ => false,
        };
        
        // Don't delete repositories
        if entry.disk_kind == Some(gix_dir::entry::Kind::Repository) {
            continue;
        }
        
        if should_clean {
            files_to_clean.push(entry.rela_path.to_string());
            
            if !dry_run {
                if entry.disk_kind == Some(gix_dir::entry::Kind::Directory) {
                    fs::remove_dir_all(path)?;
                } else {
                    fs::remove_file(path)?;
                }
            }
        }
    }
    
    Ok(files_to_clean)
}
```

## Use Case: Finding Files for Status Display

### Problem

You need to implement a Git-like status display that shows both modified tracked files and untracked files, with proper classification.

### Solution

Use `gix-dir` to traverse the repository and classify files according to their status.

```rust
use gix_dir::{walk, entry::Status, walk::delegate::Collect};
use std::{path::Path, collections::HashMap};

// A simplified status representation
enum FileStatus {
    Modified,
    Added,
    Deleted,
    Untracked,
    Ignored,
}

fn get_status_info(repo_path: &Path) -> Result<HashMap<String, FileStatus>, Box<dyn std::error::Error>> {
    // Set up context and pathspec
    let repo = gix::open(repo_path)?;
    let index = repo.index()?;
    let mut excludes = repo.excludes()?;
    let objects = repo.objects();
    let git_dir = repo.git_dir().to_path_buf();
    let current_dir = std::env::current_dir()?;
    let mut pathspec = gix_pathspec::Search::default();
    
    let mut delegate = Collect::default();
    
    let ctx = gix_dir::walk::Context {
        should_interrupt: None,
        git_dir_realpath: &git_dir,
        current_dir: &current_dir,
        index: index.read()?,
        ignore_case_index_lookup: None,
        pathspec: &mut pathspec,
        pathspec_attributes: &mut |_, _, _, _| false,
        excludes: Some(&mut excludes),
        objects,
        explicit_traversal_root: None,
    };
    
    let options = gix_dir::walk::Options {
        emit_pruned: false,
        emit_ignored: Some(gix_dir::walk::EmissionMode::Matching),
        emit_untracked: gix_dir::walk::EmissionMode::Matching,
        emit_tracked: true,  // Include tracked files
        emit_empty_directories: false,
        ..Default::default()
    };
    
    walk(repo_path, ctx, options, &mut delegate)?;
    
    // Map entries to status
    let mut status_map = HashMap::new();
    for (entry, _) in delegate.unorded_entries {
        let path = entry.rela_path.to_string();
        let status = match entry.status {
            Status::Tracked => {
                // In a real implementation, you would compare index and working tree
                // states to determine if the file is modified, added, or deleted
                FileStatus::Modified
            },
            Status::Untracked => FileStatus::Untracked,
            Status::Ignored(_) => FileStatus::Ignored,
            Status::Pruned => continue, // Skip pruned entries
        };
        
        status_map.insert(path, status);
    }
    
    Ok(status_map)
}
```

## Use Case: Efficient Directory Traversal with Collapsing

### Problem

You need to traverse a large repository efficiently, collapsing directories where appropriate to minimize the number of entries processed.

### Solution

Use `gix-dir` with directory collapsing options to optimize traversal.

```rust
use gix_dir::{walk, entry::Status, walk::delegate::Collect};
use std::path::Path;

fn traverse_with_collapsing(repo_path: &Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Set up context and pathspec
    let repo = gix::open(repo_path)?;
    let index = repo.index()?;
    let mut excludes = repo.excludes()?;
    let objects = repo.objects();
    let git_dir = repo.git_dir().to_path_buf();
    let current_dir = std::env::current_dir()?;
    let mut pathspec = gix_pathspec::Search::default();
    
    let mut delegate = Collect::default();
    
    let ctx = gix_dir::walk::Context {
        should_interrupt: None,
        git_dir_realpath: &git_dir,
        current_dir: &current_dir,
        index: index.read()?,
        ignore_case_index_lookup: None,
        pathspec: &mut pathspec,
        pathspec_attributes: &mut |_, _, _, _| false,
        excludes: Some(&mut excludes),
        objects,
        explicit_traversal_root: None,
    };
    
    let options = gix_dir::walk::Options {
        emit_pruned: false,
        emit_ignored: Some(gix_dir::walk::EmissionMode::CollapseDirectory),
        emit_untracked: gix_dir::walk::EmissionMode::CollapseDirectory,
        emit_tracked: true,
        emit_empty_directories: true,
        emit_collapsed: Some(gix_dir::walk::CollapsedEntriesEmissionMode::OnStatusMismatch),
        ..Default::default()
    };
    
    let (outcome, _) = walk(repo_path, ctx, options, &mut delegate)?;
    
    println!(
        "Traversal statistics: {} read_dir calls, {} seen entries, {} returned entries",
        outcome.read_dir_calls, outcome.seen_entries, outcome.returned_entries
    );
    
    // Get sorted entries by path
    let sorted_entries = delegate.into_entries_by_path();
    
    // Extract paths
    let paths = sorted_entries
        .into_iter()
        .map(|(entry, _)| {
            let status_str = match entry.status {
                Status::Tracked => "tracked",
                Status::Untracked => "untracked",
                Status::Ignored(_) => "ignored",
                Status::Pruned => "pruned",
            };
            
            let kind_str = if let Some(kind) = entry.disk_kind {
                match kind {
                    gix_dir::entry::Kind::Directory => "dir",
                    gix_dir::entry::Kind::File => "file",
                    gix_dir::entry::Kind::Symlink => "symlink",
                    gix_dir::entry::Kind::Repository => "repo",
                    gix_dir::entry::Kind::Untrackable => "untrackable",
                }
            } else {
                "unknown"
            };
            
            format!("{} ({} {})", entry.rela_path, status_str, kind_str)
        })
        .collect();
    
    Ok(paths)
}
```

## Use Case: Implementing Pathspec-Based File Finding

### Problem

You need to implement a function that finds files matching a specific pathspec, similar to `git ls-files`.

### Solution

Use `gix-dir` with a custom pathspec to filter matching entries.

```rust
use gix_dir::{walk, entry::Status, walk::delegate::Collect};
use std::path::Path;

fn find_files_matching_pathspec(
    repo_path: &Path,
    patterns: &[&str]
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Set up context and pathspec
    let repo = gix::open(repo_path)?;
    let index = repo.index()?;
    let mut excludes = repo.excludes()?;
    let objects = repo.objects();
    let git_dir = repo.git_dir().to_path_buf();
    let current_dir = std::env::current_dir()?;
    
    // Create pathspec from patterns
    let mut pathspec = gix_pathspec::Search::from_paths(patterns.iter().map(|s| *s))?;
    
    let mut delegate = Collect::default();
    
    let ctx = gix_dir::walk::Context {
        should_interrupt: None,
        git_dir_realpath: &git_dir,
        current_dir: &current_dir,
        index: index.read()?,
        ignore_case_index_lookup: None,
        pathspec: &mut pathspec,
        pathspec_attributes: &mut |_, _, _, _| false,
        excludes: Some(&mut excludes),
        objects,
        explicit_traversal_root: None,
    };
    
    let options = gix_dir::walk::Options {
        emit_pruned: false,
        emit_ignored: Some(gix_dir::walk::EmissionMode::Matching),
        emit_untracked: gix_dir::walk::EmissionMode::Matching,
        emit_tracked: true,
        emit_empty_directories: false,
        ..Default::default()
    };
    
    walk(repo_path, ctx, options, &mut delegate)?;
    
    // Filter entries based on pathspec match
    let matching_files = delegate
        .unorded_entries
        .into_iter()
        .filter(|(entry, _)| {
            entry.pathspec_match.is_some_and(|m| {
                matches!(
                    m,
                    gix_dir::entry::PathspecMatch::Verbatim
                    | gix_dir::entry::PathspecMatch::WildcardMatch
                    | gix_dir::entry::PathspecMatch::Prefix
                )
            })
        })
        .map(|(entry, _)| entry.rela_path.to_string())
        .collect();
    
    Ok(matching_files)
}
```

## Use Case: Safe Directory Operations with Interrupt Handling

### Problem

You need to perform directory operations that can be safely interrupted by the user (e.g., with Ctrl+C).

### Solution

Use `gix-dir` with interrupt handling to safely traverse directories with the ability to cancel the operation.

```rust
use gix_dir::{walk, entry::Status, walk::delegate::Collect};
use std::{path::Path, sync::atomic::{AtomicBool, Ordering}, sync::Arc};
use std::time::Duration;

fn interruptible_directory_walk(repo_path: &Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Create atomic flag for interrupt handling
    let should_interrupt = Arc::new(AtomicBool::new(false));
    let should_interrupt_clone = should_interrupt.clone();
    
    // Set up interrupt handler (e.g., for Ctrl+C)
    // In a real application, you would use a proper signal handler
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_secs(5)); // Simulate interrupt after 5 seconds
        should_interrupt_clone.store(true, Ordering::SeqCst);
        println!("Interrupt signal received!");
    });
    
    // Set up context and pathspec
    let repo = gix::open(repo_path)?;
    let index = repo.index()?;
    let mut excludes = repo.excludes()?;
    let objects = repo.objects();
    let git_dir = repo.git_dir().to_path_buf();
    let current_dir = std::env::current_dir()?;
    let mut pathspec = gix_pathspec::Search::default();
    
    let mut delegate = Collect::default();
    
    let ctx = gix_dir::walk::Context {
        should_interrupt: Some(&should_interrupt),
        git_dir_realpath: &git_dir,
        current_dir: &current_dir,
        index: index.read()?,
        ignore_case_index_lookup: None,
        pathspec: &mut pathspec,
        pathspec_attributes: &mut |_, _, _, _| false,
        excludes: Some(&mut excludes),
        objects,
        explicit_traversal_root: None,
    };
    
    let options = gix_dir::walk::Options {
        emit_untracked: gix_dir::walk::EmissionMode::Matching,
        emit_tracked: true,
        ..Default::default()
    };
    
    let result = walk(repo_path, ctx, options, &mut delegate);
    
    match result {
        Ok((outcome, _)) => {
            println!(
                "Walk completed: {} read_dir calls, {} entries seen, {} entries returned",
                outcome.read_dir_calls, outcome.seen_entries, outcome.returned_entries
            );
            
            let files = delegate
                .unorded_entries
                .into_iter()
                .map(|(entry, _)| entry.rela_path.to_string())
                .collect();
                
            Ok(files)
        },
        Err(gix_dir::walk::Error::Interrupted) => {
            println!("Walk was interrupted as requested");
            Ok(Vec::new()) // Return empty list when interrupted
        },
        Err(e) => Err(e.into()),
    }
}
```