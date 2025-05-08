# gix-worktree-stream Use Cases

This document outlines the primary use cases for the `gix-worktree-stream` crate, describing the problems it solves and providing example code for common scenarios.

## Intended Audience

The `gix-worktree-stream` crate is designed for:

- **Git Implementation Developers**: Building Git commands that need to extract and process content from Git trees
- **Archive Generation Tools**: Applications that create archives or exports from Git repositories
- **Streaming Processors**: Systems that need to process Git repository content without loading everything into memory

## Use Cases

### 1. Generating Repository Archives

**Problem**: You need to create an archive of a repository (like `git archive`) with content correctly filtered according to Git attributes.

**Solution**: The crate provides a memory-efficient way to stream content from a Git tree with proper attribute handling.

```rust
use gix_worktree_stream::{from_tree, AdditionalEntry, entry};
use gix_filter::Pipeline;
use gix_object::bstr::BStr;
use gix_object::tree::EntryKind;
use gix_attributes::search::Outcome;
use std::path::Path;
use std::io::{Read, Write};
use std::fs::File;

fn create_archive(
    repo_path: &Path,
    tree_id: gix_hash::ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static,
    output_path: &Path
) -> std::io::Result<()> {
    // Setup attribute handling via a worktree stack
    let repo = gix::open(repo_path)?;
    let index = repo.index()?;
    
    // Create a worktree stack for attribute lookup
    let mut worktree_stack = {
        let attributes = gix_worktree::stack::state::Attributes::default();
        let state = gix_worktree::stack::State::AttributesStack(attributes);
        let ignore_case = repo.config()?.snapshot()?
            .boolean("core.ignorecase")?.unwrap_or(false);
        
        gix_worktree::Stack::from_state_and_ignore_case(
            repo_path,
            ignore_case,
            state,
            &index,
            &index.path_backing(),
        )
    };
    
    // Define attribute lookup function
    let attribute_fn = move |path: &BStr, mode, attrs: &mut Outcome| {
        if let Ok(platform) = worktree_stack.at_entry(path, Some(mode), &repo.objects) {
            platform.matching_attributes(attrs);
        }
        Ok(())
    };
    
    // Create filter pipeline
    let pipeline = Pipeline::default();
    
    // Create the stream
    let mut stream = from_tree(
        tree_id, 
        objects,
        pipeline,
        attribute_fn,
    );
    
    // Add an informational README
    let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    let readme = format!(
        "# Repository Archive\n\nCreated: {}\nTree: {}\n", 
        timestamp, 
        tree_id
    );
    
    stream.add_entry(AdditionalEntry {
        id: gix_hash::ObjectId::null(gix_hash::Kind::Sha1),
        mode: EntryKind::Blob.into(),
        relative_path: "README.txt".into(),
        source: entry::Source::Memory(readme.into_bytes()),
    });
    
    // Create a TAR file from the stream
    let mut archive = tar::Builder::new(File::create(output_path)?);
    
    while let Some(mut entry) = stream.next_entry()? {
        let path = entry.relative_path().to_str_lossy().to_string();
        let mut header = tar::Header::new_gnu();
        
        match entry.mode.kind() {
            EntryKind::Blob | EntryKind::BlobExecutable => {
                // Read content
                let mut content = Vec::new();
                entry.read_to_end(&mut content)?;
                
                // Set header fields
                header.set_size(content.len() as u64);
                header.set_mtime(std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs());
                
                if entry.mode.kind() == EntryKind::BlobExecutable {
                    header.set_mode(0o755);
                } else {
                    header.set_mode(0o644);
                }
                
                // Add to archive
                archive.append_data(&mut header, &path, &content[..])?;
            }
            EntryKind::Link => {
                // Read symlink target
                let mut target = Vec::new();
                entry.read_to_end(&mut target)?;
                
                // Add symlink to archive
                let target_str = String::from_utf8_lossy(&target).to_string();
                header.set_entry_type(tar::EntryType::Symlink);
                header.set_size(0);
                header.set_mode(0o777);
                archive.append_link(&mut header, &path, &target_str)?;
            }
            _ => { /* Skip other entry types */ }
        }
    }
    
    archive.finish()?;
    Ok(())
}
```

### 2. Efficiently Streaming Repository Content

**Problem**: You need to process a large number of files from a Git tree without loading all content into memory at once.

**Solution**: The crate provides incremental access to entries, allowing efficient streaming of content.

```rust
use gix_worktree_stream::from_tree;
use gix_filter::Pipeline;
use gix_object::bstr::BStr;
use std::io::Read;
use std::path::Path;

fn process_large_repository(
    repo_path: &Path,
    tree_id: gix_hash::ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static
) -> std::io::Result<()> {
    // Create a simple attributes handler that doesn't ignore anything
    let attributes_fn = |_: &BStr, _, attrs: &mut gix_attributes::search::Outcome| {
        attrs.set_export_ignore(false);
        Ok(())
    };
    
    // Create stream with default pipeline
    let mut stream = from_tree(
        tree_id,
        objects,
        Pipeline::default(),
        attributes_fn,
    );
    
    // Process entries one at a time
    let mut total_size = 0;
    let mut total_files = 0;
    
    while let Some(mut entry) = stream.next_entry()? {
        // Process content incrementally with a buffer
        let mut buf = [0; 8192]; // 8KB buffer
        let mut file_size = 0;
        
        loop {
            match entry.read(&mut buf)? {
                0 => break, // End of file
                n => {
                    // Process chunk of data (in this example, just count bytes)
                    file_size += n;
                    
                    // In a real application, you'd do something with buf[0..n]
                    // For example, compute a hash, search for patterns, etc.
                }
            }
        }
        
        println!(
            "Processed: {}, size: {} bytes", 
            entry.relative_path(),
            file_size
        );
        
        total_size += file_size;
        total_files += 1;
    }
    
    println!("Total files: {}, Total size: {} bytes", total_files, total_size);
    Ok(())
}
```

### 3. Filtering Content Based on Git Attributes

**Problem**: You need to apply Git's content filters (like line ending normalization) when extracting content from a repository.

**Solution**: The crate integrates with `gix-filter` to apply the appropriate filters based on Git attributes.

```rust
use gix_worktree_stream::from_tree;
use gix_filter::{Pipeline, driver};
use gix_attributes::search::Outcome;
use gix_object::bstr::BStr;
use std::io::Read;
use std::path::Path;

fn extract_with_filters(
    repo_path: &Path,
    tree_id: gix_hash::ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static
) -> std::io::Result<()> {
    // Create a repository to access config
    let repo = gix::open(repo_path)?;
    
    // Setup pipeline with EOL conversion
    let mut pipeline = Pipeline::from_config(
        &repo.config()?.snapshot()?,
        driver::Context::default()
    )?;
    
    // Set working directory for filters
    pipeline.driver_context_mut().working_directory = Some(repo_path.to_path_buf());
    
    // Setup attributes lookup via worktree stack
    let index = repo.index()?;
    let mut worktree_stack = {
        let attributes = gix_worktree::stack::state::Attributes::default();
        let state = gix_worktree::stack::State::AttributesStack(attributes);
        
        gix_worktree::Stack::from_state_and_ignore_case(
            repo_path,
            false, // Use case-sensitive matching
            state,
            &index,
            &index.path_backing(),
        )
    };
    
    // Create attribute lookup function
    let attribute_fn = move |path: &BStr, mode, attrs: &mut Outcome| {
        if let Ok(platform) = worktree_stack.at_entry(path, Some(mode), &repo.objects) {
            platform.matching_attributes(attrs);
        }
        Ok(())
    };
    
    // Create the stream
    let mut stream = from_tree(
        tree_id,
        objects,
        pipeline,
        attribute_fn,
    );
    
    // Extract files with content filtering
    let output_dir = Path::new("/tmp/filtered-output");
    std::fs::create_dir_all(output_dir)?;
    
    while let Some(mut entry) = stream.next_entry()? {
        // Skip directories
        if entry.mode.is_dir() || entry.mode.is_submodule() {
            continue;
        }
        
        // Create output path
        let rel_path = entry.relative_path().to_str_lossy();
        let output_path = output_dir.join(rel_path.as_ref());
        
        // Create parent directories
        if let Some(parent) = output_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        // Write filtered content to file
        let mut content = Vec::new();
        entry.read_to_end(&mut content)?;
        
        std::fs::write(&output_path, content)?;
        
        // Set executable bit if needed
        #[cfg(unix)]
        if entry.mode.is_executable() {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = std::fs::metadata(&output_path)?.permissions();
            perms.set_mode(perms.mode() | 0o100);
            std::fs::set_permissions(&output_path, perms)?;
        }
        
        println!("Extracted: {}", rel_path);
    }
    
    Ok(())
}
```

### 4. Combining Git Content with Generated Files

**Problem**: You need to create a directory structure that contains both files from a Git tree and additional generated or external files.

**Solution**: The crate allows adding custom entries from various sources to the stream.

```rust
use gix_worktree_stream::{from_tree, AdditionalEntry, entry};
use gix_object::tree::EntryKind;
use gix_filter::Pipeline;
use std::io::Read;
use std::path::Path;

fn create_hybrid_content(
    repo_path: &Path,
    tree_id: gix_hash::ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static,
    output_dir: &Path
) -> std::io::Result<()> {
    // Create a basic stream with default attributes
    let mut stream = from_tree(
        tree_id,
        objects,
        Pipeline::default(),
        |_, _, attrs| {
            attrs.set_export_ignore(false);
            Ok(())
        },
    );
    
    // Add a generated VERSION file
    let version = "1.2.3"; // This would come from your build system
    stream.add_entry(AdditionalEntry {
        id: gix_hash::ObjectId::null(gix_hash::Kind::Sha1),
        mode: EntryKind::Blob.into(),
        relative_path: "VERSION".into(),
        source: entry::Source::Memory(version.as_bytes().to_vec()),
    });
    
    // Add a build timestamp file
    let timestamp = chrono::Local::now().to_rfc3339();
    stream.add_entry(AdditionalEntry {
        id: gix_hash::ObjectId::null(gix_hash::Kind::Sha1),
        mode: EntryKind::Blob.into(),
        relative_path: "build_info/timestamp.txt".into(),
        source: entry::Source::Memory(timestamp.as_bytes().to_vec()),
    });
    
    // Add external license files
    let external_dir = Path::new("/path/to/external/licenses");
    for entry in std::fs::read_dir(external_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_file() && path.extension().map_or(false, |ext| ext == "txt") {
            let rel_path = format!("licenses/{}", path.file_name().unwrap().to_string_lossy());
            stream.add_entry(AdditionalEntry {
                id: gix_hash::ObjectId::null(gix_hash::Kind::Sha1),
                mode: EntryKind::Blob.into(),
                relative_path: rel_path.into(),
                source: entry::Source::Path(path),
            });
        }
    }
    
    // Extract all content to the output directory
    std::fs::create_dir_all(output_dir)?;
    
    while let Some(mut entry) = stream.next_entry()? {
        let rel_path = entry.relative_path().to_str_lossy();
        let output_path = output_dir.join(rel_path.as_ref());
        
        // Create parent directories
        if let Some(parent) = output_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        // Handle different entry types
        match entry.mode.kind() {
            EntryKind::Blob | EntryKind::BlobExecutable => {
                let mut content = Vec::new();
                entry.read_to_end(&mut content)?;
                std::fs::write(&output_path, content)?;
                
                #[cfg(unix)]
                if entry.mode.kind() == EntryKind::BlobExecutable {
                    use std::os::unix::fs::PermissionsExt;
                    let mut perms = std::fs::metadata(&output_path)?.permissions();
                    perms.set_mode(perms.mode() | 0o100);
                    std::fs::set_permissions(&output_path, perms)?;
                }
            }
            EntryKind::Link => {
                let mut target = Vec::new();
                entry.read_to_end(&mut target)?;
                let target_str = String::from_utf8_lossy(&target);
                
                #[cfg(unix)]
                std::os::unix::fs::symlink(target_str.as_ref(), &output_path)?;
                
                #[cfg(windows)]
                {
                    // On Windows, create a text file with the link target
                    let content = format!("SYMLINK -> {}", target_str);
                    std::fs::write(&output_path, content)?;
                }
            }
            EntryKind::Tree => {
                std::fs::create_dir_all(&output_path)?;
            }
            _ => { /* Skip other types */ }
        }
        
        println!("Created: {}", rel_path);
    }
    
    Ok(())
}
```

### 5. Creating Custom Stream Processors

**Problem**: You need to implement a custom processor for Git tree content that applies specialized transformations or filtering.

**Solution**: The crate provides a streaming interface that can be easily wrapped and extended.

```rust
use gix_worktree_stream::from_tree;
use gix_filter::Pipeline;
use gix_object::bstr::{BStr, ByteSlice};
use std::io::{Read, Write};
use std::path::Path;

struct SourceCodeProcessor<R> {
    inner: R,
    transforms: Vec<Box<dyn Fn(&[u8]) -> Vec<u8> + Send>>,
    total_files: usize,
    total_size: usize,
}

impl<R: Read> SourceCodeProcessor<R> {
    fn new(inner: R) -> Self {
        let mut transforms: Vec<Box<dyn Fn(&[u8]) -> Vec<u8> + Send>> = Vec::new();
        
        // Add some code transformations
        transforms.push(Box::new(|content: &[u8]| {
            // Replace tabs with spaces
            content.replace(b"\t", b"    ").to_vec()
        }));
        
        transforms.push(Box::new(|content: &[u8]| {
            // Add copyright header to source files
            if content.starts_with(b"#include") || content.starts_with(b"package ") 
                || content.starts_with(b"import ") || content.starts_with(b"use ")
            {
                let header = b"/* Copyright (c) 2023 My Company */\n\n";
                let mut result = Vec::with_capacity(header.len() + content.len());
                result.extend_from_slice(header);
                result.extend_from_slice(content);
                result
            } else {
                content.to_vec()
            }
        }));
        
        Self {
            inner,
            transforms,
            total_files: 0,
            total_size: 0,
        }
    }
    
    fn process_repository(
        repo_path: &Path,
        tree_id: gix_hash::ObjectId,
        objects: impl gix_object::Find + Clone + Send + 'static,
        output_dir: &Path
    ) -> std::io::Result<()> {
        // Create stream
        let stream = from_tree(
            tree_id,
            objects,
            Pipeline::default(),
            |_, _, attrs| {
                attrs.set_export_ignore(false);
                Ok(())
            },
        );
        
        // Create processor
        let mut processor = Self::new(stream.into_read());
        
        // Process all entries
        let mut buffer = Vec::new();
        processor.read_to_end(&mut buffer)?;
        
        // Create a new stream from the processed content
        let mut stream = gix_worktree_stream::Stream::from_read(&buffer[..]);
        
        // Extract processed files
        std::fs::create_dir_all(output_dir)?;
        
        while let Some(mut entry) = stream.next_entry()? {
            // Skip non-file entries
            if !entry.mode.is_blob() {
                continue;
            }
            
            let rel_path = entry.relative_path().to_str_lossy();
            let output_path = output_dir.join(rel_path.as_ref());
            
            // Create parent directories
            if let Some(parent) = output_path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            
            // Read and write content
            let mut content = Vec::new();
            entry.read_to_end(&mut content)?;
            std::fs::write(&output_path, content)?;
        }
        
        println!(
            "Processed {} files, {} bytes total", 
            processor.total_files, 
            processor.total_size
        );
        
        Ok(())
    }
}

impl<R: Read> Read for SourceCodeProcessor<R> {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        // First, read from the inner stream
        let bytes_read = self.inner.read(buf)?;
        
        if bytes_read > 0 {
            // Apply transformations if this appears to be a source file
            // Note: In a real implementation, you'd need to track entry boundaries
            let mut content = Vec::from(&buf[..bytes_read]);
            
            // Apply transformations
            for transform in &self.transforms {
                content = transform(&content);
            }
            
            // Copy back to buffer, up to buffer length
            let to_copy = std::cmp::min(content.len(), buf.len());
            buf[..to_copy].copy_from_slice(&content[..to_copy]);
            
            // Update statistics
            self.total_size += bytes_read;
            if bytes_read > 0 && buf[0] == b'/' { // Heuristic to count files
                self.total_files += 1;
            }
            
            Ok(to_copy)
        } else {
            Ok(0)
        }
    }
}
```

## Common Patterns

### Serializing and Deserializing Streams

The stream can be converted to a byte stream and back, allowing for serialization and transmission:

```rust
use gix_worktree_stream::{Stream, from_tree};
use gix_filter::Pipeline;
use std::io::{Read, Write};
use std::path::Path;

fn save_and_load_stream(
    repo_path: &Path,
    tree_id: gix_hash::ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static,
    cache_path: &Path
) -> std::io::Result<()> {
    // Create the stream
    let stream = from_tree(
        tree_id,
        objects.clone(),
        Pipeline::default(),
        |_, _, attrs| {
            attrs.set_export_ignore(false);
            Ok(())
        },
    );
    
    // Serialize the stream to a file
    {
        let mut file = std::fs::File::create(cache_path)?;
        let mut reader = stream.into_read();
        std::io::copy(&mut reader, &mut file)?;
    }
    
    // Later, deserialize the stream
    {
        let file = std::fs::File::open(cache_path)?;
        let mut stream = Stream::from_read(file);
        
        // Process entries
        while let Some(mut entry) = stream.next_entry()? {
            println!(
                "Read cached entry: {}, mode: {:?}", 
                entry.relative_path(), 
                entry.mode
            );
            
            // Read content to confirm it's valid
            let mut content = Vec::new();
            entry.read_to_end(&mut content)?;
        }
    }
    
    Ok(())
}
```

### Efficient Directory Creation

When extracting files, it's efficient to create directories as needed:

```rust
use gix_worktree_stream::from_tree;
use gix_filter::Pipeline;
use std::io::Read;
use std::collections::HashSet;
use std::path::Path;

fn extract_files_efficiently(
    repo_path: &Path,
    tree_id: gix_hash::ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static,
    output_dir: &Path
) -> std::io::Result<()> {
    // Create a set to track created directories
    let mut created_dirs = HashSet::new();
    
    // Create the root output directory
    std::fs::create_dir_all(output_dir)?;
    created_dirs.insert(output_dir.to_path_buf());
    
    // Create the stream
    let mut stream = from_tree(
        tree_id,
        objects,
        Pipeline::default(),
        |_, _, attrs| {
            attrs.set_export_ignore(false);
            Ok(())
        },
    );
    
    // Extract files
    while let Some(mut entry) = stream.next_entry()? {
        let rel_path = entry.relative_path().to_str_lossy();
        let output_path = output_dir.join(rel_path.as_ref());
        
        // Ensure parent directory exists
        if let Some(parent) = output_path.parent() {
            if !created_dirs.contains(parent) {
                std::fs::create_dir_all(parent)?;
                created_dirs.insert(parent.to_path_buf());
            }
        }
        
        // Create the file
        if entry.mode.is_blob() || entry.mode.is_blob_executable() {
            let mut file = std::fs::File::create(&output_path)?;
            std::io::copy(&mut entry, &mut file)?;
            
            // Set executable bit if needed
            #[cfg(unix)]
            if entry.mode.is_executable() {
                use std::os::unix::fs::PermissionsExt;
                let mut perms = file.metadata()?.permissions();
                perms.set_mode(perms.mode() | 0o100);
                std::fs::set_permissions(&output_path, perms)?;
            }
        }
    }
    
    Ok(())
}
```

### Parallel Processing

For CPU-intensive transformations, entries can be processed in parallel:

```rust
use gix_worktree_stream::from_tree;
use gix_filter::Pipeline;
use std::io::Read;
use std::path::Path;
use std::thread;
use std::sync::mpsc;

struct ProcessingJob {
    path: String,
    content: Vec<u8>,
    mode: gix_object::tree::EntryMode,
}

struct ProcessedJob {
    path: String,
    content: Vec<u8>,
    mode: gix_object::tree::EntryMode,
}

fn process_in_parallel(
    repo_path: &Path,
    tree_id: gix_hash::ObjectId,
    objects: impl gix_object::Find + Clone + Send + 'static,
    num_threads: usize
) -> std::io::Result<Vec<ProcessedJob>> {
    // Create the stream
    let mut stream = from_tree(
        tree_id,
        objects,
        Pipeline::default(),
        |_, _, attrs| {
            attrs.set_export_ignore(false);
            Ok(())
        },
    );
    
    // Create channels for job distribution
    let (job_sender, job_receiver) = mpsc::channel();
    let (result_sender, result_receiver) = mpsc::channel();
    
    // Spawn worker threads
    let worker_handles: Vec<_> = (0..num_threads)
        .map(|_| {
            let job_rx = job_receiver.clone();
            let result_tx = result_sender.clone();
            
            thread::spawn(move || {
                while let Ok(job) = job_rx.recv() {
                    // Process the content (example: uppercase all text files)
                    let processed = process_content(job);
                    result_tx.send(processed).unwrap();
                }
            })
        })
        .collect();
    
    // Read entries and send jobs
    let mut job_count = 0;
    while let Some(mut entry) = stream.next_entry()? {
        // Skip non-file entries
        if !entry.mode.is_blob() {
            continue;
        }
        
        // Read content
        let mut content = Vec::new();
        entry.read_to_end(&mut content)?;
        
        // Create job
        let job = ProcessingJob {
            path: entry.relative_path().to_str_lossy().to_string(),
            content,
            mode: entry.mode,
        };
        
        // Send job to workers
        job_sender.send(job).unwrap();
        job_count += 1;
    }
    
    // Close the job channel to signal workers to exit
    drop(job_sender);
    
    // Collect results
    let mut results = Vec::with_capacity(job_count);
    for _ in 0..job_count {
        results.push(result_receiver.recv().unwrap());
    }
    
    // Wait for workers to finish
    for handle in worker_handles {
        handle.join().unwrap();
    }
    
    Ok(results)
}

fn process_content(job: ProcessingJob) -> ProcessedJob {
    // Example processing: uppercase text files
    let content = if job.path.ends_with(".txt") || job.path.ends_with(".md") {
        job.content
            .iter()
            .map(|&b| if b >= b'a' && b <= b'z' { b - 32 } else { b })
            .collect()
    } else {
        job.content
    };
    
    ProcessedJob {
        path: job.path,
        content,
        mode: job.mode,
    }
}
```