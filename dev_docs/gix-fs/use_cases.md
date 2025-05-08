# gix-fs Use Cases

This document outlines the main use cases for the `gix-fs` crate, describing the problems it solves and providing example code for common scenarios.

## Intended Audience

The `gix-fs` crate is designed for:

- **Git Implementation Developers**: Building Git functionality that needs to interact with the file system in a reliable, cross-platform way
- **Repository Management Tools**: Applications that need to manipulate Git repositories at the file system level
- **Filesystem Abstraction Consumers**: Any code that needs reliable file system operations with retry logic and platform-specific handling

## Use Cases

### 1. Adapting to Platform-Specific File System Capabilities

**Problem**: Git needs to work correctly across different file systems (Windows, macOS, Linux, etc.) that have different capabilities regarding case sensitivity, Unicode normalization, and symlink support.

**Solution**: The `Capabilities` struct detects and exposes platform-specific file system behavior, allowing code to adapt accordingly.

```rust
use gix_fs::Capabilities;
use std::path::Path;

fn git_repo_operations(repo_path: &Path) -> std::io::Result<()> {
    // Probe the file system capabilities at the repository location
    let caps = Capabilities::probe(repo_path);
    
    // Adjust behavior based on capabilities
    if caps.ignore_case {
        // Use case-insensitive path comparison
        println!("Using case-insensitive path handling");
    }
    
    if caps.precompose_unicode {
        // Ensure Unicode paths are precomposed for storage
        println!("Using Unicode path normalization");
        
        // Get current directory with proper Unicode normalization
        let cwd = gix_fs::current_dir(caps.precompose_unicode)?;
        println!("Current directory: {}", cwd.display());
    }
    
    if !caps.symlink {
        // Handle symlinks as regular files with special content
        println!("Symlinks not supported, using alternative approach");
    }
    
    Ok(())
}
```

### 2. Creating Directory Hierarchies with Robust Error Handling

**Problem**: When creating directories (e.g., for a new repository or during checkout), operations can fail due to race conditions, missing parent directories, or interruptions.

**Solution**: The `dir::create` module provides robust directory creation with configurable retry logic.

```rust
use gix_fs::dir::create::{all, Retries};
use std::path::Path;

fn create_repository_directories(repo_root: &Path) -> std::io::Result<()> {
    // Define directory paths to create
    let objects_dir = repo_root.join(".git/objects");
    let refs_dir = repo_root.join(".git/refs");
    let hooks_dir = repo_root.join(".git/hooks");
    
    // Custom retry configuration for critical operations
    let critical_retries = Retries {
        to_create_entire_directory: 10,
        on_create_directory_failure: 30,
        on_interrupt: 15,
    };
    
    // Create directories with appropriate retry logic
    all(&objects_dir, critical_retries)?;
    all(&refs_dir, Retries::default())?;
    all(&hooks_dir, Retries::default())?;
    
    println!("Repository directories created successfully");
    Ok(())
}
```

### 3. Efficient Path Traversal with Operation Callbacks

**Problem**: When performing operations on nested directory structures (like a worktree), you often need to track the current path and perform different operations at each level efficiently.

**Solution**: The `Stack` struct provides a powerful path traversal mechanism with callback support.

```rust
use gix_fs::Stack;
use std::path::PathBuf;
use std::io::Result;

struct GitCheckoutDelegate {
    // State for the checkout operation
    index_entries: Vec<(String, Vec<u8>)>, // Simplified for example: (path, content)
}

impl gix_fs::stack::Delegate for GitCheckoutDelegate {
    fn push_directory(&mut self, stack: &Stack) -> Result<()> {
        // Create the directory if it doesn't exist
        if !stack.current().exists() {
            std::fs::create_dir(stack.current())?;
        }
        Ok(())
    }
    
    fn push(&mut self, is_last_component: bool, stack: &Stack) -> Result<()> {
        if is_last_component {
            // This is a file, not a directory
            let path = stack.current().to_string_lossy();
            
            // Find the file content in our index (simplified example)
            if let Some(entry) = self.index_entries.iter().find(|(p, _)| p == &*path) {
                // Write the file content
                std::fs::write(stack.current(), &entry.1)?;
            }
        }
        Ok(())
    }
    
    fn pop_directory(&mut self) {
        // Called when exiting a directory, could be used for cleanup or logging
    }
}

fn checkout_files(repo_root: &Path, index_entries: Vec<(String, Vec<u8>)>) -> Result<()> {
    let mut stack = Stack::new(repo_root.to_path_buf());
    let mut delegate = GitCheckoutDelegate { index_entries };
    
    // Process each path
    for (path, _) in &delegate.index_entries {
        stack.make_relative_path_current(path, &mut delegate)?;
    }
    
    Ok(())
}
```

### 4. Managing File Content Caching with Change Detection

**Problem**: Git needs to read and cache file contents (like config files) but must detect when they've changed on disk to refresh the cache.

**Solution**: The `FileSnapshot` family of types provides a caching mechanism with modification time tracking for automatic refreshing.

```rust
use gix_fs::{FileSnapshot, SharedFileSnapshotMut};
use std::path::Path;
use std::fs;
use std::io::Result;

// Simple config file representation
struct ConfigFile {
    entries: Vec<String>,
}

impl ConfigFile {
    fn parse(content: &str) -> Self {
        // Simple parsing for example
        ConfigFile {
            entries: content.lines().map(String::from).collect(),
        }
    }
}

struct GitRepository {
    config_file_path: PathBuf,
    config: SharedFileSnapshotMut<ConfigFile>,
}

impl GitRepository {
    fn new(path: &Path) -> Self {
        GitRepository {
            config_file_path: path.join("config"),
            config: SharedFileSnapshotMut::new(),
        }
    }
    
    fn get_config(&self) -> Result<Option<impl std::ops::Deref<Target = ConfigFile>>> {
        // Function to get modification time
        let get_mtime = || -> Option<std::time::SystemTime> {
            fs::metadata(&self.config_file_path).ok()?.modified().ok()
        };
        
        // Function to load the file when needed
        let load_config = || -> Result<Option<ConfigFile>> {
            if !self.config_file_path.exists() {
                return Ok(None);
            }
            
            let content = fs::read_to_string(&self.config_file_path)?;
            Ok(Some(ConfigFile::parse(&content)))
        };
        
        // Get the recent snapshot, which will refresh if the file has changed
        self.config.recent_snapshot(get_mtime, load_config)
    }
}
```

### 5. Reliable File System Operations on Windows and Unix

**Problem**: Git needs to work consistently across Windows and Unix-like systems, despite differences in path handling, symlinks, and permissions.

**Solution**: `gix-fs` abstracts these differences with platform-specific implementations.

```rust
use gix_fs::symlink;
use std::path::Path;
use std::io::Result;

fn create_git_symlinks(repo_path: &Path) -> Result<()> {
    let caps = gix_fs::Capabilities::probe(repo_path);
    
    // Create common Git symlinks if the file system supports them
    if caps.symlink {
        // Create HEAD -> refs/heads/main symlink
        let head_path = repo_path.join(".git/HEAD");
        let target_path = Path::new("refs/heads/main");
        symlink::create(target_path, &head_path)?;
        
        println!("Created symlink: {} -> {}", head_path.display(), target_path.display());
    } else {
        // On file systems without symlink support, create a file with the symlink content
        let head_path = repo_path.join(".git/HEAD");
        std::fs::write(&head_path, b"ref: refs/heads/main\n")?;
        
        println!("Created symlink file: {}", head_path.display());
    }
    
    Ok(())
}

fn check_file_permissions(file_path: &Path) -> Result<()> {
    let metadata = std::fs::metadata(file_path)?;
    
    // Check if the file is executable (platform-dependent implementation)
    if gix_fs::is_executable(&metadata) {
        println!("File is executable: {}", file_path.display());
    } else {
        println!("File is not executable: {}", file_path.display());
    }
    
    Ok(())
}
```

## Common Patterns

### Progressive Directory Creation

When dealing with complex directory structures like Git repositories, creating directories gradually with proper error handling is crucial:

```rust
use gix_fs::dir::create::Iter;
use std::path::Path;

fn create_directory_with_feedback(dir: &Path) -> std::io::Result<()> {
    let iter = Iter::new(dir);
    
    for result in iter {
        match result {
            Ok(created_dir) => {
                println!("Created directory: {}", created_dir.display());
            }
            Err(err) => {
                match err {
                    gix_fs::dir::create::Error::Intermediate { dir, kind } => {
                        println!("Intermediate failure for {}: {:?}, retrying...", dir.display(), kind);
                    }
                    gix_fs::dir::create::Error::Permanent { dir, err, .. } => {
                        return Err(std::io::Error::new(
                            err.kind(),
                            format!("Failed to create directory {}: {}", dir.display(), err)
                        ));
                    }
                }
            }
        }
    }
    
    Ok(())
}
```

### Platform-Aware Path Handling

When working with paths across platforms, normalizing path components helps ensure consistent behavior:

```rust
use gix_fs::stack::ToNormalPathComponents;
use std::path::Path;

fn normalize_git_paths(paths: &[&str]) -> Vec<String> {
    paths
        .iter()
        .filter_map(|&path| {
            let components: Result<Vec<_>, _> = path.to_normal_path_components().collect();
            
            match components {
                Ok(comps) => {
                    // Join components back into a path
                    let normalized = comps
                        .iter()
                        .map(|c| c.to_string_lossy().to_string())
                        .collect::<Vec<_>>()
                        .join("/");
                    
                    Some(normalized)
                }
                Err(_) => None, // Skip paths with non-normal components
            }
        })
        .collect()
}
```

### Thread-Safe File Caching

For multi-threaded Git implementations, safely sharing cached file content is important:

```rust
use gix_fs::{FileSnapshot, SharedFileSnapshot};
use gix_features::threading::OwnShared;
use std::sync::Arc;
use std::collections::HashMap;
use std::path::PathBuf;

struct ThreadSafeCache {
    cache: Arc<std::sync::Mutex<HashMap<PathBuf, SharedFileSnapshot<Vec<u8>>>>>,
}

impl ThreadSafeCache {
    fn new() -> Self {
        ThreadSafeCache {
            cache: Arc::new(std::sync::Mutex::new(HashMap::new())),
        }
    }
    
    fn get_or_load(&self, path: &Path) -> std::io::Result<SharedFileSnapshot<Vec<u8>>> {
        // Check if we have a cached version
        let existing = {
            let cache = self.cache.lock().unwrap();
            cache.get(path).cloned()
        };
        
        if let Some(snapshot) = existing {
            return Ok(snapshot);
        }
        
        // Load the file
        let modified = std::fs::metadata(path)?.modified()?;
        let content = std::fs::read(path)?;
        
        // Create a new snapshot
        let snapshot = OwnShared::new(FileSnapshot {
            value: content,
            modified,
        });
        
        // Cache it
        {
            let mut cache = self.cache.lock().unwrap();
            cache.insert(path.to_path_buf(), snapshot.clone());
        }
        
        Ok(snapshot)
    }
}
```