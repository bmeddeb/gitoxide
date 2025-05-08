# gix-archive Use Cases

This document outlines the primary use cases for the `gix-archive` crate, including target audiences, problems solved, and example code demonstrating solutions.

## Intended Audience

- Git tool developers creating archive functionality
- Application developers who need to export Git repository content
- CI/CD workflow developers who need to package repository content
- Developers of backup or distribution systems that work with Git repositories

## Use Cases

### 1. Creating Distribution Archives from a Repository

**Problem**: A developer needs to create a clean distribution archive from a Git repository without including Git metadata.

**Solution**: Use `gix-archive` to create an archive in a standard format like tar, tar.gz, or zip.

```rust
use gix_archive::{Format, Options, write_stream};
use gix_worktree_stream::Stream;
use std::fs::File;
use std::io::BufWriter;

fn create_repository_archive(repo_path: &str, output_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the tree from HEAD
    let head_tree = repo.head_commit()?.tree()?;
    
    // Create a worktree stream from the tree
    let odb = repo.objects.clone();
    let mut stream = gix_worktree_stream::from_tree(
        head_tree.id,
        odb.clone(),
        gix_filter::Pipeline::default(),
        |_path, _mode, _attrs| Ok(()),
    );
    
    // Set up the output file
    let file = File::create(output_path)?;
    let writer = BufWriter::new(file);
    
    // Configure archive options
    let options = Options {
        format: Format::TarGz { compression_level: Some(6) },
        tree_prefix: None,
        modification_time: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|t| t.as_secs() as i64)
            .unwrap_or_default(),
    };
    
    // Create the archive
    write_stream(
        &mut stream,
        Stream::next_entry,
        writer,
        options,
    )?;
    
    Ok(())
}
```

### 2. Creating an Archive with a Specific Prefix

**Problem**: A developer needs to create an archive where all files are contained within a specific directory prefix.

**Solution**: Use the `tree_prefix` option to add a prefix to all paths in the archive.

```rust
use gix_archive::{Format, Options, write_stream_seek};
use gix_worktree_stream::Stream;
use std::fs::File;
use std::io::BufWriter;
use bstr::BString;

fn create_prefixed_archive(
    repo_path: &str, 
    output_path: &str, 
    prefix: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the tree from HEAD
    let head_tree = repo.head_commit()?.tree()?;
    
    // Create a worktree stream from the tree
    let odb = repo.objects.clone();
    let mut stream = gix_worktree_stream::from_tree(
        head_tree.id,
        odb.clone(),
        gix_filter::Pipeline::default(),
        |_path, _mode, _attrs| Ok(()),
    );
    
    // Set up the output file
    let file = File::create(output_path)?;
    let writer = BufWriter::new(file);
    
    // Configure archive options with a prefix
    // Make sure the prefix ends with a '/'
    let prefix = if prefix.ends_with('/') {
        prefix.to_string()
    } else {
        format!("{}/", prefix)
    };
    
    let options = Options {
        format: Format::Zip { compression_level: Some(6) },
        tree_prefix: Some(prefix.into()),
        modification_time: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|t| t.as_secs() as i64)
            .unwrap_or_default(),
    };
    
    // Create the archive (using write_stream_seek for ZIP format)
    write_stream_seek(
        &mut stream,
        Stream::next_entry,
        writer,
        options,
    )?;
    
    Ok(())
}
```

### 3. Creating an Archive with a Specific Commit Time

**Problem**: A developer needs to create an archive where all files have the same modification time as the commit they were created from.

**Solution**: Extract the commit time and use it as the modification time in the archive options.

```rust
use gix_archive::{Format, Options, write_stream};
use gix_worktree_stream::Stream;
use std::fs::File;
use std::io::BufWriter;

fn create_archive_with_commit_time(
    repo_path: &str, 
    output_path: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the head commit
    let commit = repo.head_commit()?;
    
    // Get the commit time
    let commit_time = commit.time()?.seconds_since_unix_epoch;
    
    // Get the tree from the commit
    let tree_id = commit.tree_id()?;
    
    // Create a worktree stream from the tree
    let odb = repo.objects.clone();
    let mut stream = gix_worktree_stream::from_tree(
        tree_id,
        odb.clone(),
        gix_filter::Pipeline::default(),
        |_path, _mode, _attrs| Ok(()),
    );
    
    // Set up the output file
    let file = File::create(output_path)?;
    let writer = BufWriter::new(file);
    
    // Configure archive options with the commit time
    let options = Options {
        format: Format::Tar,
        tree_prefix: None,
        modification_time: commit_time,
    };
    
    // Create the archive
    write_stream(
        &mut stream,
        Stream::next_entry,
        writer,
        options,
    )?;
    
    Ok(())
}
```

### 4. Creating an Archive with Custom Filtering

**Problem**: A developer needs to create an archive that includes only certain files or excludes specific files.

**Solution**: Filter the worktree stream before creating the archive.

```rust
use gix_archive::{Format, Options, write_stream};
use gix_worktree_stream::{Stream, Entry};
use std::fs::File;
use std::io::BufWriter;
use bstr::ByteSlice;

fn create_filtered_archive(
    repo_path: &str, 
    output_path: &str,
    exclude_pattern: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the tree from HEAD
    let head_tree = repo.head_commit()?.tree()?;
    
    // Create a worktree stream from the tree
    let odb = repo.objects.clone();
    let mut stream = gix_worktree_stream::from_tree(
        head_tree.id,
        odb.clone(),
        gix_filter::Pipeline::default(),
        |_path, _mode, _attrs| Ok(()),
    );
    
    // Set up the output file
    let file = File::create(output_path)?;
    let writer = BufWriter::new(file);
    
    // Configure archive options
    let options = Options {
        format: Format::TarGz { compression_level: None },
        tree_prefix: None,
        modification_time: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|t| t.as_secs() as i64)
            .unwrap_or_default(),
    };
    
    // Create a custom next_entry function that filters entries
    let exclude_pattern = exclude_pattern.to_string();
    let next_entry = move |stream: &mut Stream| -> Result<Option<Entry<'_>>, gix_worktree_stream::entry::Error> {
        loop {
            match stream.next_entry()? {
                Some(entry) if !entry.relative_path().to_str_lossy().contains(&exclude_pattern) => {
                    return Ok(Some(entry));
                }
                Some(_) => {
                    // Skip this entry and continue to the next one
                    continue;
                }
                None => return Ok(None),
            }
        }
    };
    
    // Create the archive
    write_stream(
        &mut stream,
        next_entry,
        writer,
        options,
    )?;
    
    Ok(())
}
```

### 5. In-Memory Archive Creation for Web Services

**Problem**: A web service needs to generate an archive on-demand and serve it directly without writing to disk.

**Solution**: Use in-memory buffers with `Cursor` for seek operations when needed.

```rust
use gix_archive::{Format, Options, write_stream_seek};
use gix_worktree_stream::Stream;
use std::io::Cursor;

async fn serve_repository_archive(
    repo_path: &str,
    format: Format
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the tree from HEAD
    let head_tree = repo.head_commit()?.tree()?;
    
    // Create a worktree stream from the tree
    let odb = repo.objects.clone();
    let mut stream = gix_worktree_stream::from_tree(
        head_tree.id,
        odb.clone(),
        gix_filter::Pipeline::default(),
        |_path, _mode, _attrs| Ok(()),
    );
    
    // Create an in-memory buffer
    let mut buffer = Vec::new();
    
    // Configure archive options
    let options = Options {
        format,
        tree_prefix: None,
        modification_time: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|t| t.as_secs() as i64)
            .unwrap_or_default(),
    };
    
    // Create the archive in memory
    match format {
        Format::Zip { .. } => {
            let cursor = Cursor::new(&mut buffer);
            write_stream_seek(
                &mut stream,
                Stream::next_entry,
                cursor,
                options,
            )?;
        },
        _ => {
            write_stream(
                &mut stream,
                Stream::next_entry,
                &mut buffer,
                options,
            )?;
        }
    }
    
    // Return the buffer to be sent as a response
    Ok(buffer)
}
```

## Advanced Use Cases

### 1. Incremental Archive Updates

**Problem**: A developer needs to create archive updates that only include files that have changed since a specific commit.

**Solution**: Use a diff between two commits to identify changed files, then include only those in the archive.

```rust
// Note: This is a conceptual example and would require additional implementation
// to fully capture the changed files between commits

use gix_archive::{Format, Options, write_stream};
use gix_worktree_stream::{Stream, Entry};
use std::collections::HashSet;
use std::fs::File;
use std::io::BufWriter;

fn create_incremental_archive(
    repo_path: &str,
    output_path: &str,
    base_commit: &str,
    target_commit: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the base and target commits
    let base = repo.find_commit(base_commit)?;
    let target = repo.find_commit(target_commit)?;
    
    // Use diff to find changed files
    let mut changed_paths = HashSet::new();
    let diff = repo.diff_tree_to_tree(Some(&base.tree()?), Some(&target.tree()?), None)?;
    
    for delta in diff.deltas() {
        if let Some(path) = delta.new_file().path() {
            changed_paths.insert(path.to_owned());
        }
    }
    
    // Create a worktree stream from the target tree
    let odb = repo.objects.clone();
    let mut stream = gix_worktree_stream::from_tree(
        target.tree_id()?,
        odb.clone(),
        gix_filter::Pipeline::default(),
        |_path, _mode, _attrs| Ok(()),
    );
    
    // Set up the output file
    let file = File::create(output_path)?;
    let writer = BufWriter::new(file);
    
    // Configure archive options
    let options = Options {
        format: Format::TarGz { compression_level: Some(6) },
        tree_prefix: None,
        modification_time: target.time()?.seconds_since_unix_epoch,
    };
    
    // Create a custom next_entry function that only includes changed files
    let next_entry = move |stream: &mut Stream| -> Result<Option<Entry<'_>>, gix_worktree_stream::entry::Error> {
        loop {
            match stream.next_entry()? {
                Some(entry) if changed_paths.contains(entry.relative_path().as_bstr()) => {
                    return Ok(Some(entry));
                }
                Some(_) => {
                    // Skip this entry and continue to the next one
                    continue;
                }
                None => return Ok(None),
            }
        }
    };
    
    // Create the archive
    write_stream(
        &mut stream,
        next_entry,
        writer,
        options,
    )?;
    
    Ok(())
}
```

### 2. Multi-Format Archive Generation

**Problem**: A developer needs to generate multiple archive formats from the same repository in one operation.

**Solution**: Reuse the worktree stream for multiple archive creation operations.

```rust
use gix_archive::{Format, Options, write_stream, write_stream_seek};
use gix_worktree_stream::Stream;
use std::fs::File;
use std::io::{BufWriter, Cursor};

fn create_multi_format_archives(
    repo_path: &str,
    tar_path: &str,
    tar_gz_path: &str,
    zip_path: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the tree from HEAD
    let head_tree = repo.head_commit()?.tree()?;
    let commit_time = repo.head_commit()?.time()?.seconds_since_unix_epoch;
    
    // Common options base
    let base_options = Options {
        format: Format::Tar, // Will be overridden for each format
        tree_prefix: None,
        modification_time: commit_time,
    };
    
    // Create tar archive
    {
        // Create a worktree stream from the tree
        let odb = repo.objects.clone();
        let mut stream = gix_worktree_stream::from_tree(
            head_tree.id,
            odb.clone(),
            gix_filter::Pipeline::default(),
            |_path, _mode, _attrs| Ok(()),
        );
        
        let file = File::create(tar_path)?;
        let writer = BufWriter::new(file);
        
        let mut options = base_options.clone();
        options.format = Format::Tar;
        
        write_stream(
            &mut stream,
            Stream::next_entry,
            writer,
            options,
        )?;
    }
    
    // Create tar.gz archive
    {
        // Create a new worktree stream
        let odb = repo.objects.clone();
        let mut stream = gix_worktree_stream::from_tree(
            head_tree.id,
            odb.clone(),
            gix_filter::Pipeline::default(),
            |_path, _mode, _attrs| Ok(()),
        );
        
        let file = File::create(tar_gz_path)?;
        let writer = BufWriter::new(file);
        
        let mut options = base_options.clone();
        options.format = Format::TarGz { compression_level: Some(6) };
        
        write_stream(
            &mut stream,
            Stream::next_entry,
            writer,
            options,
        )?;
    }
    
    // Create zip archive
    {
        // Create a new worktree stream
        let odb = repo.objects.clone();
        let mut stream = gix_worktree_stream::from_tree(
            head_tree.id,
            odb.clone(),
            gix_filter::Pipeline::default(),
            |_path, _mode, _attrs| Ok(()),
        );
        
        let file = File::create(zip_path)?;
        let writer = BufWriter::new(file);
        
        let mut options = base_options.clone();
        options.format = Format::Zip { compression_level: Some(6) };
        
        write_stream_seek(
            &mut stream,
            Stream::next_entry,
            writer,
            options,
        )?;
    }
    
    Ok(())
}
```

## Integration Examples

### Integration with Web Frameworks

This example shows how to integrate `gix-archive` with a web framework like Axum to provide repository archives on-demand:

```rust
use axum::{
    extract::{Path, State},
    response::IntoResponse,
    routing::get,
    Router,
};
use bytes::Bytes;
use gix_archive::{Format, Options, write_stream_seek};
use gix_worktree_stream::Stream;
use std::io::Cursor;
use std::sync::Arc;

struct AppState {
    repos_dir: String,
}

async fn get_archive(
    State(state): State<Arc<AppState>>,
    Path((repo_name, format)): Path<(String, String)>,
) -> impl IntoResponse {
    let repo_path = format!("{}/{}", state.repos_dir, repo_name);
    
    // Determine format from request
    let archive_format = match format.as_str() {
        "tar" => Format::Tar,
        "tar.gz" => Format::TarGz { compression_level: Some(6) },
        "zip" => Format::Zip { compression_level: Some(6) },
        _ => Format::Tar, // Default
    };
    
    // Generate content type based on format
    let content_type = match format.as_str() {
        "tar" => "application/x-tar",
        "tar.gz" => "application/gzip",
        "zip" => "application/zip",
        _ => "application/octet-stream",
    };
    
    // Generate filename
    let filename = format!("{}.{}", repo_name, format);
    
    // Create the archive
    let buffer = match create_archive(&repo_path, archive_format) {
        Ok(buffer) => buffer,
        Err(_) => return (
            [(axum::http::header::CONTENT_TYPE, "text/plain")],
            "Failed to create archive"
        ).into_response(),
    };
    
    // Return the archive with appropriate headers
    (
        [
            (axum::http::header::CONTENT_TYPE, content_type),
            (axum::http::header::CONTENT_DISPOSITION, &format!("attachment; filename=\"{}\"", filename)),
        ],
        buffer
    ).into_response()
}

fn create_archive(repo_path: &str, format: Format) -> Result<Bytes, Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the tree from HEAD
    let head_tree = repo.head_commit()?.tree()?;
    
    // Create a worktree stream from the tree
    let odb = repo.objects.clone();
    let mut stream = gix_worktree_stream::from_tree(
        head_tree.id,
        odb.clone(),
        gix_filter::Pipeline::default(),
        |_path, _mode, _attrs| Ok(()),
    );
    
    // Create an in-memory buffer
    let mut buffer = Vec::new();
    
    // Configure archive options
    let options = Options {
        format,
        tree_prefix: None,
        modification_time: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|t| t.as_secs() as i64)
            .unwrap_or_default(),
    };
    
    // Create the archive in memory
    match format {
        Format::Zip { .. } => {
            let cursor = Cursor::new(&mut buffer);
            write_stream_seek(
                &mut stream,
                Stream::next_entry,
                cursor,
                options,
            )?;
        },
        _ => {
            gix_archive::write_stream(
                &mut stream,
                Stream::next_entry,
                &mut buffer,
                options,
            )?;
        }
    }
    
    Ok(Bytes::from(buffer))
}

#[tokio::main]
async fn main() {
    let state = Arc::new(AppState {
        repos_dir: "/path/to/repositories".to_string(),
    });
    
    let app = Router::new()
        .route("/repo/:repo_name/archive/:format", get(get_archive))
        .with_state(state);
    
    axum::Server::bind(&"0.0.0.0:3000".parse().unwrap())
        .serve(app.into_make_service())
        .await
        .unwrap();
}
```