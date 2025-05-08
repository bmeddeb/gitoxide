# gix-lock Use Cases

This document describes typical use cases for the `gix-lock` crate, which provides Git-style lock files for atomic operations on resources.

## Intended Audience

- Developers implementing Git functionality or Git-compatible tools
- Application developers needing atomic file operations with cleanup guarantees
- Systems that need to safely coordinate access to shared resources
- Developers working on multi-process applications where file locking is necessary

## Use Case 1: Safely Updating a Configuration File

### Problem

When multiple processes need to read and update a shared configuration file, there's a risk of corruption if two processes attempt to write simultaneously.

### Solution

Use `gix-lock` to ensure atomic updates to the configuration file.

```rust
use gix_lock::{acquire::Fail, File};
use std::io::Write;
use std::path::Path;
use std::time::Duration;

fn update_config_file(config_path: &Path, new_content: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Try to acquire a lock with a timeout of 5 seconds, using backoff strategy
    let mut file = File::acquire_to_update_resource(
        config_path,
        Fail::AfterDurationWithBackoff(Duration::from_secs(5)),
        None,
    )?;
    
    // Write the new content
    file.with_mut(|f| f.write_all(new_content.as_bytes()))?;
    
    // Commit the changes, atomically replacing the original file
    let (resource_path, _) = file.commit()?;
    println!("Successfully updated {}", resource_path.display());
    
    Ok(())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config_path = Path::new("/path/to/config.json");
    let new_content = r#"{"setting": "new_value", "enabled": true}"#;
    
    update_config_file(config_path, new_content)?;
    
    Ok(())
}
```

## Use Case 2: Coordinating Access to Git Repository Components

### Problem

In a Git implementation, multiple operations might need to update repository structures like the index or reference files concurrently.

### Solution

Use `gix-lock` to coordinate access and ensure atomic updates to repository components.

```rust
use gix_lock::{acquire::Fail, File, Marker};
use std::io::{Read, Write};
use std::path::Path;

fn update_git_reference(repo_path: &Path, ref_name: &str, new_value: &str) -> Result<(), Box<dyn std::error::Error>> {
    let ref_path = repo_path.join("refs").join(ref_name);
    
    // Ensure the parent directory exists
    if let Some(parent) = ref_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    
    // Acquire a lock on the reference file
    let mut file = File::acquire_to_update_resource(
        &ref_path,
        Fail::Immediately, // Fail immediately if locked
        Some(repo_path.to_path_buf()), // Use repo_path as boundary for directory cleanup
    )?;
    
    // Write the new reference value with a newline
    file.with_mut(|f| writeln!(f, "{}", new_value))?;
    
    // Commit the change
    file.commit()?;
    
    println!("Reference {} updated to {}", ref_name, new_value);
    Ok(())
}

fn read_git_reference(repo_path: &Path, ref_name: &str) -> Result<String, Box<dyn std::error::Error>> {
    let ref_path = repo_path.join("refs").join(ref_name);
    
    // Use a Marker to hold the resource while reading it
    // This prevents other processes from modifying it while we read
    let marker = Marker::acquire_to_hold_resource(
        &ref_path,
        Fail::Immediately,
        None,
    )?;
    
    // Read the file content
    let content = std::fs::read_to_string(marker.resource_path())?;
    
    // The marker is automatically dropped when it goes out of scope, 
    // releasing the lock
    
    Ok(content.trim().to_string())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let repo_path = Path::new("/path/to/git/repo");
    
    // Update a reference
    update_git_reference(repo_path, "heads/main", "abcdef1234567890")?;
    
    // Read a reference
    let value = read_git_reference(repo_path, "heads/main")?;
    println!("Current value: {}", value);
    
    Ok(())
}
```

## Use Case 3: Creating Temporary Resources with Directory Cleanup

### Problem

When creating resources in a directory structure that might not exist yet, you need to ensure both the creation of the directories and their cleanup if the operation fails.

### Solution

Use `gix-lock` with boundary directory cleanup to manage temporary resources.

```rust
use gix_lock::{acquire::Fail, File};
use std::io::Write;
use std::path::Path;

fn create_nested_resource(
    base_dir: &Path,
    relative_path: &str,
    content: &[u8],
) -> Result<(), Box<dyn std::error::Error>> {
    let resource_path = base_dir.join(relative_path);
    
    // Acquire a lock with automatic directory creation and cleanup
    // The boundary_directory parameter ensures any created directories
    // up to the base_dir will be cleaned up if the operation fails
    let mut file = File::acquire_to_update_resource(
        &resource_path,
        Fail::Immediately,
        Some(base_dir.to_path_buf()),
    )?;
    
    // Write content
    file.with_mut(|f| f.write_all(content))?;
    
    // Commit changes
    file.commit()?;
    
    println!("Resource created at {}", resource_path.display());
    Ok(())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let base_dir = Path::new("/tmp/app_data");
    let relative_path = "cache/user_123/profile.json";
    let content = b"{\"name\": \"Example User\", \"settings\": {}}";
    
    create_nested_resource(base_dir, relative_path, content)?;
    
    Ok(())
}
```

## Use Case 4: Two-Phase Commit Pattern

### Problem

Sometimes you need to prepare a change, validate it, and then either commit or discard it - a pattern known as a two-phase commit.

### Solution

Use `gix-lock` with the `close` and `commit` operations to implement a two-phase commit pattern.

```rust
use gix_lock::{acquire::Fail, File};
use std::io::Write;
use std::path::Path;

fn two_phase_commit(
    resource_path: &Path,
    prepare_fn: impl FnOnce(&mut std::fs::File) -> Result<(), Box<dyn std::error::Error>>,
    validate_fn: impl FnOnce(&Path) -> Result<bool, Box<dyn std::error::Error>>,
) -> Result<bool, Box<dyn std::error::Error>> {
    // Phase 1: Prepare the change
    let mut file = File::acquire_to_update_resource(
        resource_path,
        Fail::Immediately,
        None,
    )?;
    
    // Apply changes
    file.with_mut(|f| prepare_fn(f))?;
    
    // Close the file to finalize the content but keep the lock
    let marker = file.close()?;
    
    // Phase 2: Validate and decide whether to commit
    let is_valid = validate_fn(marker.lock_path())?;
    
    if is_valid {
        // Commit if valid
        marker.commit()?;
        println!("Changes committed to {}", resource_path.display());
        Ok(true)
    } else {
        // The marker will be dropped without committing, discarding changes
        println!("Changes discarded");
        Ok(false)
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let resource_path = Path::new("/path/to/important/data.json");
    
    // Define preparation function
    let prepare = |file: &mut std::fs::File| -> Result<(), Box<dyn std::error::Error>> {
        writeln!(file, "{{\"updated\": true, \"timestamp\": {}}}", chrono::Utc::now().timestamp())?;
        Ok(())
    };
    
    // Define validation function
    let validate = |lock_path: &Path| -> Result<bool, Box<dyn std::error::Error>> {
        // Read the content from the lock file
        let content = std::fs::read_to_string(lock_path)?;
        
        // Check if the content meets some criteria
        // For example, validate JSON structure
        let is_valid = content.contains("\"updated\": true");
        
        Ok(is_valid)
    };
    
    // Perform the two-phase commit
    let committed = two_phase_commit(resource_path, prepare, validate)?;
    
    println!("Operation result: {}", if committed { "committed" } else { "rolled back" });
    
    Ok(())
}
```

## Use Case 5: Implementing a Simple Transaction Log

### Problem

Maintaining a transaction log that can't be corrupted by concurrent writes.

### Solution

Use `gix-lock` to implement an append-only transaction log with atomic writes.

```rust
use gix_lock::{acquire::Fail, File};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::Path;
use std::time::Duration;

struct TransactionLog {
    log_path: std::path::PathBuf,
}

impl TransactionLog {
    fn new(log_path: impl Into<std::path::PathBuf>) -> Self {
        Self {
            log_path: log_path.into(),
        }
    }
    
    fn append_entry(&self, entry: &str) -> Result<(), Box<dyn std::error::Error>> {
        // Try to acquire the lock with backoff
        let mut file = File::acquire_to_update_resource(
            &self.log_path,
            Fail::AfterDurationWithBackoff(Duration::from_secs(3)),
            None,
        )?;
        
        // If the file doesn't exist yet, we'll create it
        // Otherwise, we need to read its content first
        let existing_content = if self.log_path.exists() {
            let mut content = String::new();
            std::fs::File::open(&self.log_path)?.read_to_string(&mut content)?;
            content
        } else {
            String::new()
        };
        
        // Write existing content plus new entry
        file.with_mut(|f| {
            f.write_all(existing_content.as_bytes())?;
            writeln!(f, "{}", entry)?;
            Ok(())
        })?;
        
        // Commit changes
        file.commit()?;
        
        Ok(())
    }
    
    fn read_entries(&self) -> Result<Vec<String>, Box<dyn std::error::Error>> {
        if !self.log_path.exists() {
            return Ok(Vec::new());
        }
        
        // Use a marker to hold the log while reading
        let marker = gix_lock::Marker::acquire_to_hold_resource(
            &self.log_path,
            Fail::Immediately,
            None,
        )?;
        
        let content = std::fs::read_to_string(marker.resource_path())?;
        let entries = content.lines().map(String::from).collect();
        
        Ok(entries)
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let log = TransactionLog::new("/path/to/transactions.log");
    
    // Append entries
    log.append_entry("TXID:1001 - User created - 2023-01-15T14:30:00Z")?;
    log.append_entry("TXID:1002 - Payment processed - 2023-01-15T14:32:15Z")?;
    
    // Read all entries
    let entries = log.read_entries()?;
    for entry in entries {
        println!("{}", entry);
    }
    
    Ok(())
}
```

These use cases demonstrate how `gix-lock` can be used to implement atomic file operations, coordinate access to shared resources, and ensure data integrity across various scenarios.