# gix-lfs Use Cases

This document outlines potential use cases for the `gix-lfs` crate once it is implemented. Git LFS (Large File Storage) solves specific challenges related to managing large binary files in Git repositories, and these use cases reflect common patterns and applications.

## Intended Audience

- Rust developers building Git-based tools and applications
- Contributors to gitoxide who need to implement or use Git LFS functionality
- Developers working with repositories containing large binary assets
- Teams managing game development, media production, or data science projects

## Use Cases

Since the `gix-lfs` crate is currently a placeholder with no implementation, the following use cases represent potential applications once the crate is fully implemented:

### 1. Managing Game Development Assets

**Problem**: Game developers need to version control large binary assets like textures, models, and sound files, which can quickly bloat a Git repository.

**Solution**: Use Git LFS to store large game assets outside the main repository while maintaining version control.

```rust
// Example of what the API might look like when implemented
use gix_lfs::{self, track, LfsConfig};
use std::path::Path;

fn setup_game_dev_repository(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Open or initialize repository
    let repo = if repo_path.exists() {
        gix::open(repo_path)?
    } else {
        gix::init(repo_path)?
    };
    
    // Configure LFS with higher limits for game assets
    let config = LfsConfig {
        batch_size: 100, // Process more files at once
        transfer_config: gix_lfs::TransferConfig {
            max_concurrent_transfers: 8,
            transfer_retry_count: 3,
            ..Default::default()
        },
        ..Default::default()
    };
    
    // Install LFS for the repository
    gix_lfs::install(&repo, config)?;
    
    // Track game asset file types
    track(
        &[
            "*.png", "*.jpg", "*.psd",     // Textures and images
            "*.fbx", "*.obj", "*.blend",   // 3D models
            "*.wav", "*.mp3", "*.ogg",     // Audio files
            "*.mp4", "*.mov",              // Video files
            "Assets/**/*.unity",           // Unity scene files
            "Assets/**/*.asset",           // Unity asset files
        ],
        repo_path.join(".gitattributes")
    )?;
    
    println!("Game development repository setup complete");
    println!("Large assets will be managed by Git LFS");
    
    Ok(())
}

// Process for artists and designers adding assets
fn add_asset_to_repository(
    repo_path: &Path,
    asset_path: &Path,
    commit_message: &str
) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    
    // Verify LFS is properly set up
    if !gix_lfs::is_installed(&repo)? {
        return Err("LFS is not installed for this repository".into());
    }
    
    // Add the asset file
    // (Behind the scenes, gix-filter with LFS will convert to pointer)
    let mut index = repo.index()?;
    index.add_path(asset_path)?;
    
    // Create a commit with the new asset
    let signature = repo.signature()?;
    let tree_id = index.write_tree()?;
    let tree = repo.find_tree(tree_id)?;
    
    let head = repo.head()?;
    let parent_commit = head.peel_to_commit()?;
    
    repo.commit(
        Some("HEAD"),
        &signature,
        &signature,
        commit_message,
        &tree,
        &[&parent_commit]
    )?;
    
    // Push both Git data and LFS objects
    let lfs_client = gix_lfs::LfsClient::new(&repo)?;
    lfs_client.push(
        &["HEAD"],
        "origin",
        gix_lfs::PushOptions::default()
    )?;
    
    println!("Asset {} added and LFS objects pushed", asset_path.display());
    Ok(())
}
```

### 2. Optimizing Data Science Workflows

**Problem**: Data scientists need to track large datasets and model files while keeping repositories efficient.

**Solution**: Use Git LFS to store datasets and trained models outside the main repository.

```rust
// Example of what the API might look like when implemented
use gix_lfs::{self, track, LfsConfig};
use std::path::Path;

fn setup_data_science_repository(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Open or initialize repository
    let repo = gix::init(repo_path)?;
    
    // Configure LFS for data science needs
    let config = LfsConfig {
        // Configure for very large files
        local_storage_path: repo_path.join(".git/lfs/objects"),
        transfer_config: gix_lfs::TransferConfig {
            allow_download_resume: true,
            ..Default::default()
        },
        ..Default::default()
    };
    
    // Install LFS
    gix_lfs::install(&repo, config)?;
    
    // Track data science file types
    track(
        &[
            "data/**/*.csv", "data/**/*.parquet", "data/**/*.json",  // Datasets
            "models/**/*.pkl", "models/**/*.h5", "models/**/*.onnx", // Model files
            "notebooks/**/*.ipynb",                                  // Notebooks
            "*.npy", "*.npz",                                        // NumPy arrays
        ],
        repo_path.join(".gitattributes")
    )?;
    
    // Create directory structure
    std::fs::create_dir_all(repo_path.join("data/raw"))?;
    std::fs::create_dir_all(repo_path.join("data/processed"))?;
    std::fs::create_dir_all(repo_path.join("models"))?;
    std::fs::create_dir_all(repo_path.join("notebooks"))?;
    std::fs::create_dir_all(repo_path.join("src"))?;
    
    println!("Data science repository setup complete");
    Ok(())
}

// Add a trained model to the repository
fn add_trained_model(
    repo_path: &Path, 
    model_path: &Path,
    model_metrics: &str
) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    
    // Add the model file (handled by LFS)
    let mut index = repo.index()?;
    index.add_path(model_path)?;
    
    // Create a metrics file (not handled by LFS)
    let metrics_path = model_path.with_extension("metrics.json");
    std::fs::write(&metrics_path, model_metrics)?;
    index.add_path(&metrics_path)?;
    
    // Commit the changes
    let signature = repo.signature()?;
    let tree_id = index.write_tree()?;
    let tree = repo.find_tree(tree_id)?;
    
    let head = repo.head()?;
    let parent_commit = head.peel_to_commit()?;
    
    repo.commit(
        Some("HEAD"),
        &signature,
        &signature,
        &format!("Add trained model: {}", model_path.file_name().unwrap().to_string_lossy()),
        &tree,
        &[&parent_commit]
    )?;
    
    // Push both Git data and LFS objects
    let lfs_client = gix_lfs::LfsClient::new(&repo)?;
    lfs_client.push(
        &["HEAD"],
        "origin",
        gix_lfs::PushOptions::default()
    )?;
    
    println!("Model {} added with metrics and pushed", model_path.display());
    Ok(())
}

// Selective LFS fetching for efficient dataset access
fn fetch_specific_dataset(
    repo_path: &Path,
    dataset_path: &Path
) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    let lfs_client = gix_lfs::LfsClient::new(&repo)?;
    
    // Fetch only the specific dataset
    lfs_client.fetch_paths(
        &[dataset_path.to_str().unwrap()],
        gix_lfs::FetchOptions {
            include_referenced: false,
            ..Default::default()
        }
    )?;
    
    println!("Dataset {} fetched", dataset_path.display());
    Ok(())
}
```

### 3. Media Production and Digital Asset Management

**Problem**: Media production teams need to track large video, audio, and design files with proper versioning.

**Solution**: Use Git LFS with file locking to prevent concurrent editing of binary assets.

```rust
// Example of what the API might look like when implemented
use gix_lfs::{self, LfsClient, LockOptions, track};
use std::path::Path;

fn setup_media_repository(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    // Open or initialize repository
    let repo = gix::init(repo_path)?;
    
    // Install LFS with file locking enabled
    let config = gix_lfs::LfsConfig {
        file_locking_enabled: true,
        ..Default::default()
    };
    
    gix_lfs::install(&repo, config)?;
    
    // Track media file types
    track(
        &[
            "*.psd", "*.ai", "*.indd",           // Adobe design files
            "*.mp4", "*.mov", "*.avi", "*.mxf",  // Video files
            "*.wav", "*.mp3", "*.aiff",          // Audio files
            "*.blend", "*.c4d", "*.ma",          // 3D files
        ],
        repo_path.join(".gitattributes")
    )?;
    
    // Set up lockable files
    let lockable_patterns = &[
        "**/*.psd", "**/*.ai", "**/*.indd",  // Design files can't be merged
        "**/*.mp4", "**/*.mov",             // Video files can't be merged
        "**/*.blend", "**/*.c4d",           // 3D files can't be merged
    ];
    
    gix_lfs::set_lockable(lockable_patterns, repo_path.join(".gitattributes"))?;
    
    println!("Media production repository setup complete");
    Ok(())
}

// Lock a media file for exclusive editing
fn lock_media_file(
    repo_path: &Path,
    file_path: &Path
) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    let lfs_client = LfsClient::new(&repo)?;
    
    // Verify file is an LFS file
    if !gix_lfs::is_pointer_file(file_path)? {
        return Err(format!("{} is not an LFS file", file_path.display()).into());
    }
    
    // Attempt to lock the file
    let lock = lfs_client.lock(
        file_path,
        LockOptions {
            remote: Some("origin"),
            ..Default::default()
        }
    )?;
    
    println!("File locked successfully: {}", file_path.display());
    println!("Lock ID: {}", lock.id);
    println!("Locked by: {}", lock.owner.name);
    
    Ok(())
}

// List all locks in the repository
fn list_locked_files(repo_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    let lfs_client = LfsClient::new(&repo)?;
    
    // Get all locks
    let locks = lfs_client.list_locks(None)?;
    
    if locks.is_empty() {
        println!("No locked files found");
    } else {
        println!("Locked files:");
        for lock in locks {
            println!("{}: locked by {} at {}", 
                lock.path, 
                lock.owner.name,
                lock.locked_at.format("%Y-%m-%d %H:%M:%S")
            );
        }
    }
    
    Ok(())
}

// Unlock a file when editing is complete
fn unlock_media_file(
    repo_path: &Path,
    file_path: &Path
) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    let lfs_client = LfsClient::new(&repo)?;
    
    // Unlock the file
    lfs_client.unlock(
        file_path,
        gix_lfs::UnlockOptions {
            force: false,  // Only the owner can unlock
            remote: Some("origin"),
            ..Default::default()
        }
    )?;
    
    println!("File unlocked successfully: {}", file_path.display());
    Ok(())
}
```

### 4. Automated CI/CD for Repositories with LFS Content

**Problem**: CI/CD pipelines need to efficiently handle repositories containing LFS content without downloading all LFS objects.

**Solution**: Use selective LFS fetching to optimize CI/CD workflows.

```rust
// Example of what the API might look like when implemented
use gix_lfs::{LfsClient, FetchOptions};
use std::path::Path;

fn setup_ci_clone(
    repo_url: &str,
    target_dir: &Path
) -> Result<(), Box<dyn std::error::Error>> {
    // Clone the repository without LFS content
    let repo = gix::clone(repo_url, target_dir)?;
    
    println!("Repository cloned without LFS content");
    
    // Only fetch LFS objects that are relevant for the build
    let lfs_client = LfsClient::new(&repo)?;
    
    // Fetch only what's needed based on changed files
    let diff = repo.diff_workdir(None)?;
    let changed_paths: Vec<String> = diff.deltas()
        .filter_map(|delta| {
            let path = delta.new_file().path().map(|p| p.to_string_lossy().to_string());
            // Only include paths that match our build-required patterns
            path.filter(|p| {
                p.starts_with("src/") || p.starts_with("assets/") || p.ends_with(".lock")
            })
        })
        .collect();
    
    // Fetch LFS objects only for the required files
    if !changed_paths.is_empty() {
        println!("Fetching LFS objects for {} changed files relevant to the build", changed_paths.len());
        
        lfs_client.fetch_paths(
            &changed_paths.iter().map(|s| s.as_str()).collect::<Vec<_>>(),
            FetchOptions {
                include_referenced: false,
                ..Default::default()
            }
        )?;
    }
    
    println!("CI clone and selective LFS fetch completed successfully");
    Ok(())
}

fn build_artifact_with_lfs(
    repo_path: &Path,
    build_script: &Path
) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    
    // Check which LFS files we need for this build
    let build_script_content = std::fs::read_to_string(build_script)?;
    
    // Parse script to determine required asset paths
    let required_assets = extract_required_assets(&build_script_content);
    
    // Fetch only those assets
    let lfs_client = LfsClient::new(&repo)?;
    lfs_client.fetch_paths(
        &required_assets,
        FetchOptions {
            include_referenced: true,
            ..Default::default()
        }
    )?;
    
    // Now run the build with all required assets
    println!("Running build with LFS assets");
    let status = std::process::Command::new(build_script)
        .current_dir(repo_path)
        .status()?;
    
    if !status.success() {
        return Err("Build process failed".into());
    }
    
    println!("Build completed successfully");
    Ok(())
}

// Helper function to parse build script and extract required assets
fn extract_required_assets(script_content: &str) -> Vec<&str> {
    // This would be a more complex parser in reality
    script_content.lines()
        .filter(|line| line.contains("REQUIRED_ASSET:"))
        .map(|line| {
            let parts: Vec<&str> = line.split("REQUIRED_ASSET:").collect();
            parts[1].trim()
        })
        .collect()
}
```

### 5. Migration from Standard Git to Git LFS

**Problem**: A repository has grown too large due to binary files and needs to be converted to use Git LFS.

**Solution**: Use tools to identify large files and convert them to LFS pointers.

```rust
// Example of what the API might look like when implemented
use gix_lfs::{self, track, MigrationOptions};
use std::path::Path;

fn analyze_repository_for_lfs_migration(
    repo_path: &Path
) -> Result<Vec<gix_lfs::FileSizeSummary>, Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    
    // Analyze repository to find large files
    let file_sizes = gix_lfs::analyze_repo_object_sizes(
        &repo,
        gix_lfs::AnalysisOptions {
            min_size: 1024 * 1024, // 1MB minimum
            scan_all_history: true,
            ..Default::default()
        }
    )?;
    
    // Sort files by total size impact on the repository
    let mut file_summaries = file_sizes;
    file_summaries.sort_by(|a, b| b.total_size_all_versions.cmp(&a.total_size_all_versions));
    
    // Print analysis results
    println!("Repository analysis complete");
    println!("Found {} files larger than 1MB", file_summaries.len());
    
    if !file_summaries.is_empty() {
        println!("Top 5 largest files by total size:");
        for (i, summary) in file_summaries.iter().take(5).enumerate() {
            println!("{}. {}: {} MB across {} versions", 
                i + 1,
                summary.path,
                summary.total_size_all_versions / (1024 * 1024),
                summary.version_count
            );
        }
    }
    
    Ok(file_summaries)
}

fn migrate_repository_to_lfs(
    repo_path: &Path,
    file_patterns: &[&str],
    include_history: bool
) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    
    // Install LFS
    gix_lfs::install(&repo, gix_lfs::LfsConfig::default())?;
    
    // Track the specified patterns
    track(file_patterns, repo_path.join(".gitattributes"))?;
    
    // Perform the migration
    let migration_result = gix_lfs::migrate(
        &repo,
        MigrationOptions {
            include_history,
            file_patterns: file_patterns.to_vec(),
            prune_after_migration: true,
            verbose: true,
            dry_run: false,
        }
    )?;
    
    println!("Migration complete:");
    println!("Files migrated: {}", migration_result.migrated_file_count);
    println!("Objects processed: {}", migration_result.objects_processed);
    println!("Size before migration: {} MB", migration_result.size_before / (1024 * 1024));
    println!("Size after migration: {} MB", migration_result.size_after / (1024 * 1024));
    println!("Size reduction: {:.1}%", 
        (1.0 - (migration_result.size_after as f64 / migration_result.size_before as f64)) * 100.0
    );
    
    println!("\nNext steps:");
    println!("1. Verify the repository state");
    println!("2. Push the changes to the remote repository");
    println!("3. Make sure all collaborators update their git-lfs installation");
    
    Ok(())
}

// Clean up old history after migration
fn cleanup_after_migration(
    repo_path: &Path
) -> Result<(), Box<dyn std::error::Error>> {
    let repo = gix::open(repo_path)?;
    
    // Force garbage collection to clean up unreferenced objects
    println!("Running garbage collection to clean up old objects...");
    gix_lfs::run_garbage_collection(&repo, true)?;
    
    // Prune old objects
    println!("Pruning old objects...");
    gix_lfs::prune_objects(
        &repo,
        gix_lfs::PruneOptions {
            days_to_keep: 14,
            verify_remote: true,
            ..Default::default()
        }
    )?;
    
    println!("Repository cleanup complete");
    Ok(())
}
```

## Best Practices

Once the `gix-lfs` crate is implemented, consider these best practices for working with Git LFS:

### 1. Selective LFS Tracking

Track only file types that are truly large binary files:

```rust
// Good - only track truly large binary files
gix_lfs::track(
    &[
        "*.psd", "*.ai",        // Design files
        "*.mp4", "*.mov",       // Video files 
        "*.iso", "*.dmg",       // Disk images
        "*.zip", "*.tar.gz",    // Archives
    ],
    repo_path.join(".gitattributes")
)?;

// Bad - tracking small text files provides no benefit
gix_lfs::track(
    &[
        "*.md", "*.txt",       // Text files don't benefit from LFS
        "*.json", "*.xml",     // Config files don't benefit from LFS
        "*.py", "*.rs",        // Source code doesn't benefit from LFS
    ],
    repo_path.join(".gitattributes")
)?;
```

### 2. Configure Appropriate Transfer Settings

Optimize transfer settings based on your file sizes and network conditions:

```rust
// For large files on reliable networks
let config = gix_lfs::LfsConfig {
    transfer_config: gix_lfs::TransferConfig {
        max_concurrent_transfers: 4,      // More concurrent transfers
        chunk_size: 10 * 1024 * 1024,     // Larger chunk size (10MB)
        allow_download_resume: true,      // Allow resuming downloads
        ..Default::default()
    },
    ..Default::default()
};

// For unstable networks
let config = gix_lfs::LfsConfig {
    transfer_config: gix_lfs::TransferConfig {
        max_concurrent_transfers: 2,      // Fewer concurrent transfers
        chunk_size: 1 * 1024 * 1024,      // Smaller chunk size (1MB)
        transfer_retry_count: 5,          // More retries
        transfer_retry_delay: 3,          // Longer delay between retries
        allow_download_resume: true,      // Allow resuming downloads
        ..Default::default()
    },
    ..Default::default()
};
```

### 3. Use File Locking for Binary Assets

Implement file locking to prevent merge conflicts with binary files:

```rust
// Mark files as lockable in .gitattributes
gix_lfs::set_lockable(
    &["**/*.psd", "**/*.ai", "**/*.mp4"],
    repo_path.join(".gitattributes")
)?;

// Always lock before editing
let client = gix_lfs::LfsClient::new(&repo)?;
client.lock(
    Path::new("assets/logo.psd"),
    gix_lfs::LockOptions::default()
)?;

// Remember to unlock when done
client.unlock(
    Path::new("assets/logo.psd"),
    gix_lfs::UnlockOptions::default()
)?;
```

### 4. Implement CI-Friendly Clone Operations

Optimize CI operations to avoid unnecessary downloads:

```rust
// Clone without LFS content
let repo = gix::clone(
    repo_url,
    target_dir,
    &gix::clone::Options {
        lfs: gix_lfs::CloneOptions {
            skip_smudge: true,  // Don't download LFS content during clone
            ..Default::default()
        },
        ..Default::default()
    }
)?;

// Then download only what's needed
let lfs_client = gix_lfs::LfsClient::new(&repo)?;
lfs_client.fetch_paths(
    &["path/to/needed/asset.psd"],
    gix_lfs::FetchOptions {
        include_referenced: false,  // Only fetch exactly what we request
        ..Default::default()
    }
)?;
```

### 5. Regular Maintenance

Perform regular maintenance on LFS repositories:

```rust
// Verify all LFS pointers match what's in the LFS storage
gix_lfs::verify_objects(
    &repo,
    gix_lfs::VerifyOptions {
        include_work_tree: true,
        ..Default::default()
    }
)?;

// Prune old or unreferenced LFS objects
gix_lfs::prune_objects(
    &repo,
    gix_lfs::PruneOptions {
        days_to_keep: 30,
        verify_remote: true,
        ..Default::default()
    }
)?;
```

## Conclusion

Once implemented, the `gix-lfs` crate will enable efficient management of large files in Git repositories, addressing common challenges in game development, data science, media production, and CI/CD workflows. By providing a Rust-native interface to Git LFS functionality, it will allow developers to build tools and applications that can handle large binary assets without compromising repository performance.

The examples in this document illustrate potential APIs and usage patterns, but the actual implementation may differ. The core functionality will revolve around tracking, storing, and transferring large files efficiently, with additional features for file locking and repository migration.