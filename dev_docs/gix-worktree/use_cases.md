# gix-worktree Use Cases

This document outlines the primary use cases for the `gix-worktree` crate, describing the problems it solves and providing example code for common scenarios.

## Intended Audience

The `gix-worktree` crate is designed for:

- **Git Implementation Developers**: Building Git commands that interact with the working directory
- **Repository Management Tools**: Applications that need to apply Git-compatible rules for ignoring files or applying attributes
- **Build Systems**: Tools that need to efficiently traverse directory structures while respecting Git's ignore and attribute rules

## Use Cases

### 1. Efficiently Creating Directories During Checkout

**Problem**: When checking out files from a Git repository, you need to create directories efficiently while adhering to Git's rules about symbolic links and path validation.

**Solution**: The `Stack` with `CreateDirectoryAndAttributesStack` state provides an efficient way to create directories while traversing paths in sorted order.

```rust
use gix_worktree::{Stack, stack::State};
use gix_validate::path::component::Options as ValidateOptions;
use std::path::Path;

fn checkout_files(
    worktree_root: &Path, 
    files: &[(String, gix_index::entry::Mode, gix_hash::ObjectId)],
    index: &gix_index::State,
    objects: &dyn gix_object::Find
) -> std::io::Result<()> {
    // Create attributes state
    let attributes = gix_worktree::stack::state::Attributes::default();
    
    // Configure validation options for path components
    let validate_opts = ValidateOptions::default();
    
    // Create stack state for checkout
    let state = State::for_checkout(
        true, // unlink files/symlinks on collision
        validate_opts,
        attributes,
    );
    
    // Create the stack
    let fs_caps = gix_fs::Capabilities::probe(worktree_root);
    let path_backing = index.path_backing();
    let mut stack = Stack::from_state_and_ignore_case(
        worktree_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    );
    
    // Process files in path order (should be pre-sorted for best performance)
    for (path, mode, object_id) in files {
        // Navigate to the file's path, creating directories as needed
        let platform = stack.at_entry(path, Some(*mode), objects)?;
        
        // Now we can write the file at platform.path()
        let dest_path = platform.path();
        
        // Read the object content
        let mut content = Vec::new();
        let data = objects.try_find(&object_id, &mut content)?.unwrap();
        
        // Write the file content
        if !mode.is_dir() && !mode.is_submodule() {
            std::fs::write(dest_path, data.data)?;
            
            // Set executable bit if needed
            #[cfg(unix)]
            if mode.is_executable() {
                use std::os::unix::fs::PermissionsExt;
                let mut perms = std::fs::metadata(dest_path)?.permissions();
                perms.set_mode(perms.mode() | 0o100); // Add executable bit
                std::fs::set_permissions(dest_path, perms)?;
            }
        }
    }
    
    Ok(())
}
```

### 2. Determining if Files Are Ignored

**Problem**: When performing Git operations like status or add, you need to determine which files are ignored based on rules in various `.gitignore` files.

**Solution**: The `Stack` with `IgnoreStack` state efficiently evaluates ignore patterns as you traverse directories.

```rust
use gix_worktree::{Stack, stack::State};
use gix_ignore::Search as IgnoreSearch;
use std::path::{Path, PathBuf};
use bstr::ByteSlice;

fn find_untracked_files(
    worktree_root: &Path,
    index: &gix_index::State,
    objects: &dyn gix_object::Find
) -> std::io::Result<Vec<PathBuf>> {
    // Create ignore state
    let git_dir = worktree_root.join(".git");
    let mut buf = Vec::with_capacity(512);
    
    // Setup ignore stack with:
    // 1. Command-line overrides (empty in this example)
    // 2. Repository ignore patterns from git directory
    // 3. Default exclude file name (.gitignore)
    let ignore = gix_worktree::stack::state::Ignore::new(
        IgnoreSearch::default(),
        IgnoreSearch::from_git_dir(&git_dir, None, &mut buf)?,
        None,
        gix_worktree::stack::state::ignore::Source::WorktreeThenIdMappingIfNotSkipped,
    );
    
    // Create state for status operations
    let state = State::IgnoreStack(ignore);
    
    // Create the stack
    let fs_caps = gix_fs::Capabilities::probe(worktree_root);
    let path_backing = index.path_backing();
    let mut stack = Stack::from_state_and_ignore_case(
        worktree_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    );
    
    let mut untracked_files = Vec::new();
    
    // Walk the directory recursively
    walkdir::WalkDir::new(worktree_root)
        .sort_by_file_name() // Important for efficiency
        .into_iter()
        .filter_map(Result::ok)
        .filter(|entry| entry.file_type().is_file())
        .for_each(|entry| {
            // Convert the absolute path to a path relative to the worktree
            let rel_path = entry.path().strip_prefix(worktree_root).unwrap();
            let rel_str = rel_path.to_string_lossy();
            
            // Check if the path is in the index
            let in_index = index.entries()
                .iter()
                .any(|e| e.path_in(&path_backing).as_bytes() == rel_str.as_bytes());
                
            if !in_index {
                // Check if the file is ignored
                if let Ok(platform) = stack.at_path(
                    rel_str.as_ref(), 
                    Some(gix_index::entry::Mode::FILE),
                    objects
                ) {
                    if !platform.is_excluded() {
                        untracked_files.push(entry.path().to_path_buf());
                    }
                }
            }
        });
    
    Ok(untracked_files)
}
```

### 3. Checking Git Attributes for Files

**Problem**: When performing operations like checkout, diff, or merge, you need to determine the Git attributes that apply to files.

**Solution**: The `Stack` with `AttributesStack` or a combined state efficiently evaluates attribute patterns.

```rust
use gix_worktree::{Stack, stack::State};
use gix_attributes::search::Outcome as AttributeOutcome;
use std::path::Path;

fn should_apply_filter(
    worktree_root: &Path,
    file_path: &str,
    index: &gix_index::State,
    objects: &dyn gix_object::Find
) -> std::io::Result<bool> {
    // Setup attributes state
    let attributes = gix_worktree::stack::state::Attributes::default();
    
    // Create state for attributes
    let state = State::AttributesStack(attributes);
    
    // Create the stack
    let fs_caps = gix_fs::Capabilities::probe(worktree_root);
    let path_backing = index.path_backing();
    let mut stack = Stack::from_state_and_ignore_case(
        worktree_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    );
    
    // Get the file mode from the index
    let file_mode = index.entries()
        .iter()
        .find(|e| e.path_in(&path_backing).as_bytes() == file_path.as_bytes())
        .map(|e| e.mode);
    
    // Navigate to the file path
    let platform = stack.at_entry(file_path, file_mode, objects)?;
    
    // Check the attributes
    let mut outcome = AttributeOutcome::default();
    platform.matching_attributes(&mut outcome);
    
    // Check if the filter attribute is set
    let filter_set = outcome
        .iter()
        .any(|attr| attr.name.as_bytes() == b"filter" && attr.is_set());
    
    Ok(filter_set)
}
```

### 4. Determining File Types for Status Operations

**Problem**: When calculating the status of a repository, you need to efficiently determine which files are ignored, tracked, or untracked.

**Solution**: The `Stack` with combined `AttributesAndIgnoreStack` state provides a comprehensive solution for this scenario.

```rust
use gix_worktree::{Stack, stack::State};
use std::path::Path;
use bstr::ByteSlice;

enum FileStatus {
    Tracked,
    Ignored,
    Untracked,
}

fn get_file_status(
    worktree_root: &Path,
    file_path: &str,
    index: &gix_index::State,
    objects: &dyn gix_object::Find
) -> std::io::Result<FileStatus> {
    // Setup the combined state for both attributes and ignore handling
    let git_dir = worktree_root.join(".git");
    let mut buf = Vec::with_capacity(512);
    
    // Create attributes state
    let attributes = gix_worktree::stack::state::Attributes::default();
    
    // Create ignore state
    let ignore = gix_worktree::stack::state::Ignore::new(
        gix_ignore::Search::default(),
        gix_ignore::Search::from_git_dir(&git_dir, None, &mut buf)?,
        None,
        gix_worktree::stack::state::ignore::Source::WorktreeThenIdMappingIfNotSkipped,
    );
    
    // Create the combined state
    let state = State::for_add(attributes, ignore);
    
    // Create the stack
    let fs_caps = gix_fs::Capabilities::probe(worktree_root);
    let path_backing = index.path_backing();
    let mut stack = Stack::from_state_and_ignore_case(
        worktree_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    );
    
    // Check if the file is in the index
    let in_index = index.entries()
        .iter()
        .any(|e| e.path_in(&path_backing).as_bytes() == file_path.as_bytes());
        
    if in_index {
        return Ok(FileStatus::Tracked);
    }
    
    // Navigate to the file path
    let platform = stack.at_entry(file_path, Some(gix_index::entry::Mode::FILE), objects)?;
    
    // Check if the file is ignored
    if platform.is_excluded() {
        Ok(FileStatus::Ignored)
    } else {
        Ok(FileStatus::Untracked)
    }
}
```

### 5. Optimizing Performance with Statistics

**Problem**: You want to optimize the performance of operations that traverse the worktree by understanding how the cache is used.

**Solution**: The `Stack` provides statistics that can help identify performance bottlenecks.

```rust
use gix_worktree::{Stack, stack::State};
use std::path::Path;

fn analyze_performance(
    worktree_root: &Path,
    index: &gix_index::State,
    objects: &dyn gix_object::Find,
    file_paths: &[String]
) -> std::io::Result<()> {
    // Setup a suitable state for the operation
    let ignore = gix_worktree::stack::state::Ignore::default();
    let state = State::IgnoreStack(ignore);
    
    // Create the stack
    let fs_caps = gix_fs::Capabilities::probe(worktree_root);
    let path_backing = index.path_backing();
    let mut stack = Stack::from_state_and_ignore_case(
        worktree_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    );
    
    // Process the files
    for path in file_paths {
        let _ = stack.at_entry(path, None, objects)?;
    }
    
    // Get and analyze statistics
    let stats = stack.take_statistics();
    
    println!("Performance Statistics:");
    println!("  Platforms created: {}", stats.platforms);
    println!("  Directory operations:");
    println!("    mkdir calls: {}", stats.delegate.num_mkdir_calls);
    println!("    push_element calls: {}", stats.delegate.push_element);
    println!("    push_directory calls: {}", stats.delegate.push_directory);
    println!("    pop_directory calls: {}", stats.delegate.pop_directory);
    
    // Ignore statistics
    println!("  Ignore operations:");
    println!("    Files loaded: {}", stats.ignore.files_loaded);
    println!("    Lines parsed: {}", stats.ignore.lines_parsed);
    
    // Attribute statistics (when enabled)
    #[cfg(feature = "attributes")]
    {
        println!("  Attribute operations:");
        println!("    Files loaded: {}", stats.attributes.files_loaded);
        println!("    Lines parsed: {}", stats.attributes.lines_parsed);
    }
    
    Ok(())
}
```

## Common Patterns

### Ordered Directory Traversal

For best performance, the `Stack` should be used with paths in sorted order:

```rust
use gix_worktree::{Stack, stack::State};
use std::path::Path;

fn process_files_efficiently(
    worktree_root: &Path,
    index: &gix_index::State,
    objects: &dyn gix_object::Find,
    mut file_paths: Vec<String>
) -> std::io::Result<()> {
    // Sort the paths for optimal performance
    file_paths.sort();
    
    // Setup a suitable state
    let state = State::IgnoreStack(gix_worktree::stack::state::Ignore::default());
    
    // Create the stack
    let fs_caps = gix_fs::Capabilities::probe(worktree_root);
    let path_backing = index.path_backing();
    let mut stack = Stack::from_state_and_ignore_case(
        worktree_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    );
    
    // Process the files in sorted order
    for path in file_paths {
        let platform = stack.at_entry(&path, None, objects)?;
        
        // Perform operations with the platform...
        println!("Processing: {}", platform.path().display());
    }
    
    Ok(())
}
```

### Handling Skip-Worktree Files

The `Stack` can access attribute and ignore files directly from the object database when they're not in the worktree:

```rust
use gix_worktree::{Stack, stack::State};
use std::path::Path;

fn setup_with_id_mappings(
    worktree_root: &Path,
    index: &gix_index::State,
) -> Stack {
    // Create a basic state
    let state = State::IgnoreStack(gix_worktree::stack::state::Ignore::default());
    
    // Determine case sensitivity
    let fs_caps = gix_fs::Capabilities::probe(worktree_root);
    let case = if fs_caps.ignore_case {
        gix_glob::pattern::Case::Fold
    } else {
        gix_glob::pattern::Case::Sensitive
    };
    
    // Extract ID mappings from the index
    let path_backing = index.path_backing();
    let id_mappings = state.id_mappings_from_index(index, &path_backing, case);
    
    // Create the stack with the mappings
    Stack::new(
        worktree_root,
        state,
        case,
        Vec::with_capacity(512),
        id_mappings,
    )
}
```

### Customizing Ignore Behavior

You can customize the ignore behavior with different sources and overrides:

```rust
use gix_worktree::{Stack, stack::State};
use gix_ignore::Search as IgnoreSearch;
use std::path::Path;

fn setup_with_custom_ignores(
    worktree_root: &Path,
    index: &gix_index::State,
    exclude_patterns: &[&str]
) -> std::io::Result<Stack> {
    let git_dir = worktree_root.join(".git");
    let mut buf = Vec::with_capacity(512);
    
    // Create ignore state with custom overrides
    let ignore = gix_worktree::stack::state::Ignore::new(
        // Command-line overrides (highest priority)
        IgnoreSearch::from_overrides(exclude_patterns.iter().copied()),
        
        // Repository and global patterns
        IgnoreSearch::from_git_dir(&git_dir, None, &mut buf)?,
        
        // Custom exclude file name (instead of .gitignore)
        Some(".customignore".into()),
        
        // Source policy
        gix_worktree::stack::state::ignore::Source::WorktreeThenIdMappingIfNotSkipped,
    );
    
    // Create state for status operations
    let state = State::IgnoreStack(ignore);
    
    // Create the stack
    let fs_caps = gix_fs::Capabilities::probe(worktree_root);
    let path_backing = index.path_backing();
    
    Ok(Stack::from_state_and_ignore_case(
        worktree_root,
        fs_caps.ignore_case,
        state,
        index,
        &path_backing,
    ))
}
```