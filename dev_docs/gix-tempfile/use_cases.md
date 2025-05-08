# gix-tempfile Use Cases

This document describes typical use cases for the `gix-tempfile` crate, which provides temporary file handling with signal-safe cleanup.

## Intended Audience

- Developers implementing Git operations
- Applications that need atomic file updates
- Systems that require temporary files with guaranteed cleanup
- Applications that need to handle signals gracefully
- Developers working with resource locking

## Use Case 1: Atomic File Updates

### Problem

When updating configuration or important data files, you need to ensure that the update is atomic - either the entire update succeeds or the file remains unchanged. Partial updates can lead to corruption.

### Solution

Use `gix-tempfile` to create a temporary file, write the new content, and then atomically replace the original file.

```rust
use std::io::Write;
use std::path::Path;
use gix_tempfile::{AutoRemove, ContainingDirectory, Handle};

fn update_file_atomically(file_path: &Path, new_content: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Set up signal handlers if they haven't been set up already
    #[cfg(feature = "signals")]
    gix_tempfile::signal::setup(Default::default());
    
    // Create a temporary file at the specific path with .new extension
    let mut temp_path = file_path.to_path_buf();
    temp_path.set_extension(format!("{}.new", file_path.extension().unwrap_or_default().to_string_lossy()));
    
    // Create the temporary file
    let mut temp_file = Handle::<gix_tempfile::handle::Writable>::at(
        &temp_path,
        ContainingDirectory::Exists,
        AutoRemove::Tempfile,
    )?;
    
    // Write the new content
    writeln!(temp_file, "{}", new_content)?;
    
    // Persist the temporary file, replacing the original
    match temp_file.persist(file_path) {
        Ok(_) => {
            println!("File updated successfully");
            Ok(())
        }
        Err(err) => {
            // The original temp_file is recovered and returned in the error
            Err(format!("Failed to update file: {}", err.error).into())
        }
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config_path = Path::new("/path/to/config.json");
    let new_config = r#"{"setting": "new_value", "version": 2}"#;
    
    update_file_atomically(config_path, new_config)?;
    
    Ok(())
}
```

## Use Case 2: Resource Locking

### Problem

In multi-process environments, you need to coordinate access to shared resources to prevent conflicts.

### Solution

Use a temporary file as a lock to ensure exclusive access to resources.

```rust
use std::path::Path;
use std::time::Duration;
use gix_tempfile::{AutoRemove, ContainingDirectory, Handle};

struct FileLock {
    lock_file: Handle<gix_tempfile::handle::Closed>,
    resource_path: std::path::PathBuf,
}

impl FileLock {
    // Try to acquire a lock, with configurable timeout
    fn try_acquire(
        resource_path: &Path,
        timeout: Duration,
    ) -> Result<Option<Self>, std::io::Error> {
        // Set up signal handlers for cleanup
        #[cfg(feature = "signals")]
        gix_tempfile::signal::setup(Default::default());
        
        // Create lock path
        let lock_path = resource_path.with_extension("lock");
        
        // Try to create the lock file with retries
        let start = std::time::Instant::now();
        let mut last_error = None;
        
        while start.elapsed() < timeout {
            match Handle::<gix_tempfile::handle::Closed>::at(
                &lock_path,
                ContainingDirectory::Exists,
                AutoRemove::Tempfile,
            ) {
                Ok(lock_file) => {
                    return Ok(Some(FileLock {
                        lock_file,
                        resource_path: resource_path.to_path_buf(),
                    }));
                }
                Err(err) => {
                    if err.kind() == std::io::ErrorKind::AlreadyExists {
                        // Someone else has the lock, wait and retry
                        last_error = Some(err);
                        std::thread::sleep(Duration::from_millis(50));
                        continue;
                    }
                    return Err(err);
                }
            }
        }
        
        // Timeout expired
        Err(last_error.unwrap_or_else(|| {
            std::io::Error::new(
                std::io::ErrorKind::TimedOut,
                "Timed out waiting for lock",
            )
        }))
    }
    
    // Access the locked resource
    fn access_resource<F, T>(&self, operation: F) -> Result<T, std::io::Error>
    where
        F: FnOnce(&Path) -> Result<T, std::io::Error>,
    {
        operation(&self.resource_path)
    }
}

// Lock is automatically released when dropped
impl Drop for FileLock {
    fn drop(&mut self) {
        // The lock_file will be dropped, which removes the lock file
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let resource_path = Path::new("/path/to/shared/resource.dat");
    
    // Try to acquire the lock with a 5 second timeout
    match FileLock::try_acquire(resource_path, Duration::from_secs(5))? {
        Some(lock) => {
            // We have the lock, perform operations on the resource
            lock.access_resource(|path| {
                println!("Accessing resource: {}", path.display());
                // ... do something with the resource ...
                Ok(())
            })?;
            
            // Lock is automatically released when it goes out of scope
        }
        None => {
            println!("Could not acquire lock within timeout period");
        }
    }
    
    Ok(())
}
```

## Use Case 3: Creating Temporary Files with Cleanup

### Problem

You need to create temporary files for intermediate processing, ensuring they're cleaned up even if the process is terminated abnormally.

### Solution

Use `gix-tempfile` to create and manage temporary files with automatic cleanup.

```rust
use std::io::{Read, Write};
use std::path::Path;
use gix_tempfile::{AutoRemove, ContainingDirectory};

fn process_large_file(input_path: &Path) -> Result<String, Box<dyn std::error::Error>> {
    // Set up signal handlers
    #[cfg(feature = "signals")]
    gix_tempfile::signal::setup(Default::default());
    
    // Create a temporary directory for our processing
    let temp_dir = tempfile::tempdir()?;
    
    // Create a temporary file in that directory
    let mut temp_file = gix_tempfile::new(
        temp_dir.path(),
        ContainingDirectory::Exists,
        AutoRemove::Tempfile,
    )?;
    
    // Read input file
    let mut input_data = Vec::new();
    std::fs::File::open(input_path)?.read_to_end(&mut input_data)?;
    
    // Process the data and write to temp file
    let processed_data = process_data(&input_data)?;
    temp_file.write_all(&processed_data)?;
    
    // Create a second temporary file for the results
    let result_path = temp_dir.path().join("result.txt");
    let mut result_file = gix_tempfile::writable_at(
        &result_path,
        ContainingDirectory::Exists,
        AutoRemove::Tempfile,
    )?;
    
    // Further processing with the temporary file
    temp_file.with_mut(|file| {
        file.seek(std::io::SeekFrom::Start(0))?;
        let mut content = Vec::new();
        file.read_to_end(&mut content)?;
        
        // Process content further
        let final_result = generate_final_result(&content)?;
        
        // Write result to the result file
        result_file.write_all(final_result.as_bytes())?;
        
        Ok::<_, std::io::Error>(())
    })??;
    
    // Read the result
    let mut result = String::new();
    result_file.with_mut(|file| {
        file.seek(std::io::SeekFrom::Start(0))?;
        file.read_to_string(&mut result)
    })??;
    
    // All temporary files will be automatically removed when they go out of scope
    // or if the process is terminated by a signal
    
    Ok(result)
}

// Example data processing functions
fn process_data(data: &[u8]) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Process the data somehow
    Ok(data.to_vec())
}

fn generate_final_result(processed_data: &[u8]) -> Result<String, Box<dyn std::error::Error>> {
    // Generate a final result from the processed data
    Ok(String::from_utf8_lossy(processed_data).to_string())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let input_path = Path::new("/path/to/input.dat");
    let result = process_large_file(input_path)?;
    println!("Processing result: {}", result);
    Ok(())
}
```

## Use Case 4: Managing Nested Directory Creation and Cleanup

### Problem

You need to create temporary files in nested directories and ensure all empty directories are cleaned up when done.

### Solution

Use `gix-tempfile` with directory creation and cleanup features.

```rust
use std::io::Write;
use std::path::Path;
use gix_tempfile::{AutoRemove, ContainingDirectory};

fn create_nested_temp_file(
    base_dir: &Path,
    nested_path: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Set up signal handlers
    #[cfg(feature = "signals")]
    gix_tempfile::signal::setup(Default::default());
    
    // Full path to the nested temp file
    let file_path = base_dir.join(nested_path);
    
    // Create the temp file, automatically creating all parent directories
    let mut temp_file = gix_tempfile::writable_at(
        &file_path,
        ContainingDirectory::CreateAllRaceProof(Default::default()),
        AutoRemove::TempfileAndEmptyParentDirectoriesUntil {
            boundary_directory: base_dir.to_path_buf(),
        },
    )?;
    
    // Write some content
    writeln!(temp_file, "Temporary content")?;
    
    println!("Created temp file at: {}", file_path.display());
    
    // Option 1: Let it be removed automatically when it goes out of scope
    // along with any empty parent directories up to base_dir
    drop(temp_file);
    
    // Option 2: Persist it to a final location
    let mut another_temp_file = gix_tempfile::writable_at(
        &file_path,
        ContainingDirectory::CreateAllRaceProof(Default::default()),
        AutoRemove::TempfileAndEmptyParentDirectoriesUntil {
            boundary_directory: base_dir.to_path_buf(),
        },
    )?;
    
    writeln!(another_temp_file, "Content to persist")?;
    
    // Persist to a different location
    let final_path = base_dir.join("final_output.txt");
    another_temp_file.persist(&final_path)?;
    
    // The parent directories of the temporary file will still be cleaned up
    // if they're empty (but not the final_path itself)
    
    Ok(())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let base_dir = Path::new("/tmp/my_app");
    std::fs::create_dir_all(base_dir)?;
    
    // Create a temp file in a deeply nested structure
    create_nested_temp_file(base_dir, "level1/level2/level3/temp_file.txt")?;
    
    // After the function returns, all empty directories under base_dir will be removed
    
    Ok(())
}
```

## Use Case 5: Two-Phase File Operations

### Problem

You need to perform a "prepare and commit" operation where files are first prepared in a temporary location, then applied only if all preparations succeed.

### Solution

Use `gix-tempfile` to manage multiple temporary files and atomically commit them when ready.

```rust
use std::io::Write;
use std::path::Path;
use gix_tempfile::{AutoRemove, ContainingDirectory, Handle};

struct Transaction {
    temp_files: Vec<Handle<gix_tempfile::handle::Writable>>,
    target_paths: Vec<std::path::PathBuf>,
}

impl Transaction {
    fn new() -> Self {
        // Set up signal handlers
        #[cfg(feature = "signals")]
        gix_tempfile::signal::setup(Default::default());
        
        Transaction {
            temp_files: Vec::new(),
            target_paths: Vec::new(),
        }
    }
    
    fn prepare_file(
        &mut self,
        target_path: &Path,
        content: &str,
    ) -> Result<(), std::io::Error> {
        // Create a temporary file that will eventually replace target_path
        let temp_file = Handle::<gix_tempfile::handle::Writable>::at(
            &target_path.with_extension("new"),
            ContainingDirectory::CreateAllRaceProof(Default::default()),
            AutoRemove::Tempfile,
        )?;
        
        // Write the content to the temporary file
        let mut temp_file = temp_file;
        temp_file.write_all(content.as_bytes())?;
        
        // Store the temporary file and its target path
        self.target_paths.push(target_path.to_path_buf());
        self.temp_files.push(temp_file);
        
        Ok(())
    }
    
    fn commit(mut self) -> Result<(), std::io::Error> {
        // Verify that all target paths are ready to be overwritten
        for path in &self.target_paths {
            if let Some(parent) = path.parent() {
                if !parent.exists() {
                    return Err(std::io::Error::new(
                        std::io::ErrorKind::NotFound,
                        format!("Parent directory does not exist: {}", parent.display()),
                    ));
                }
            }
        }
        
        // Commit all temporary files to their target paths
        for (i, temp_file) in self.temp_files.drain(..).enumerate() {
            let target_path = &self.target_paths[i];
            temp_file.persist(target_path)?;
        }
        
        Ok(())
    }
    
    fn rollback(self) {
        // Explicitly drop the transaction, which will remove all temporary files
        drop(self);
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut transaction = Transaction::new();
    
    // Prepare multiple files
    transaction.prepare_file(
        Path::new("/path/to/config.json"),
        r#"{"setting": "value"}"#,
    )?;
    
    transaction.prepare_file(
        Path::new("/path/to/users.json"),
        r#"[{"name": "user1"}, {"name": "user2"}]"#,
    )?;
    
    // Try to perform some operation that might fail
    let success = perform_critical_operation()?;
    
    if success {
        // If successful, commit all changes
        transaction.commit()?;
        println!("All files updated successfully");
    } else {
        // If failed, roll back (remove all temporary files)
        transaction.rollback();
        println!("Operation failed, all changes rolled back");
    }
    
    Ok(())
}

fn perform_critical_operation() -> Result<bool, Box<dyn std::error::Error>> {
    // Simulate some operation that might succeed or fail
    Ok(true)
}
```

These use cases demonstrate how `gix-tempfile` can be used to implement atomic file operations, resource locking, temporary file management, nested directory handling, and transactional file updates with robust cleanup even when the process is terminated abnormally.