# gix-filter Use Cases

This document describes the main use cases for the gix-filter crate, who its intended audience is, what problems it solves, and how it solves them.

## Intended Audience

The primary audience for the gix-filter crate includes:

1. **Git Tool Developers**: Developers building Git-compatible tools that need to process files with Git's filtering system
2. **Repository Management Systems**: Systems that need to apply Git's filter transformations for correct file handling
3. **Gitoxide Component Developers**: Internal users developing other components in the gitoxide ecosystem
4. **Custom Filter Implementers**: Developers creating custom filter programs that need to follow Git's filter protocol

## Core Use Cases

### 1. Converting Working Tree Files to Git Storage Format

#### Problem

When files are added to Git from the working tree, they may need transformation before storage in the object database. For example:
- Converting line endings from platform-specific (CRLF on Windows) to Git-standard (LF)
- Removing developer-specific ident tags
- Converting character encodings
- Running content through external filters like Git LFS

These transformations need to happen consistently and efficiently based on Git attributes.

#### Solution

The `convert_to_git` method in the Pipeline struct handles these transformations:

```rust
use std::{io, path::Path};
use gix_filter::{Pipeline, to_git};
use gix_attributes::search::Outcome;

fn prepare_file_for_git_storage(
    filepath: &Path,
    file_content: &[u8],
    attributes: &mut dyn FnMut(&bstr::BStr, &mut Outcome),
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut pipeline = Pipeline::default();
    
    // Get the relative path for attribute lookup
    let relative_path = filepath.strip_prefix("/repo/root/").unwrap_or(filepath);
    
    // Determine if we have an index version for potential CRLF checks
    let mut index_version_fn = |_: &mut Vec<u8>| -> Result<Option<()>, _> { Ok(None) };
    
    // Apply filters to convert to Git format
    let result = pipeline.convert_to_git(
        io::Cursor::new(file_content),
        relative_path,
        attributes,
        &mut index_version_fn,
    )?;
    
    // Get the resulting bytes
    let mut output = Vec::new();
    io::copy(&mut result, &mut output)?;
    
    Ok(output)
}
```

### 2. Converting Git Storage Files to Working Tree Format

#### Problem

When files are checked out from Git's object database to the working tree, they may need transformation. For example:
- Converting line endings from Git-standard (LF) to platform-specific (CRLF on Windows)
- Expanding ident tags with current object ID
- Converting character encodings for editor compatibility
- Running content through external filters like Git LFS

#### Solution

The `convert_to_worktree` method handles these transformations:

```rust
use gix_filter::{Pipeline, driver};
use gix_attributes::search::Outcome;

fn prepare_file_for_working_tree(
    blob_content: &[u8],
    relative_path: &str,
    attributes: &mut dyn FnMut(&bstr::BStr, &mut Outcome),
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut pipeline = Pipeline::default();
    
    // Apply filters to convert to working tree format
    let result = pipeline.convert_to_worktree(
        blob_content,
        relative_path.as_ref(),
        attributes,
        driver::apply::Delay::Forbid, // Don't allow delayed processing
    )?;
    
    // Get the resulting bytes
    if let Some(bytes) = result.as_bytes() {
        Ok(bytes.to_vec())
    } else if result.is_delayed() {
        Err("Delayed processing not supported in this context".into())
    } else {
        // Otherwise stream the result
        let mut output = Vec::new();
        std::io::copy(&mut result, &mut output)?;
        Ok(output)
    }
}
```

### 3. Handling Git LFS and Large Files

#### Problem

Git LFS stores large files outside of the repository, using placeholder files with pointers in the repository itself. When checking out files, these placeholders need to be replaced with the actual content, potentially fetched from a server. Similarly, when adding large files, they need to be uploaded to the LFS server and replaced with placeholders.

#### Solution

The driver filter system in gix-filter can handle Git LFS:

```rust
use gix_filter::{Pipeline, Driver, pipeline};
use gix_attributes::search::Outcome;

fn setup_lfs_filter_pipeline() -> Pipeline {
    // Create a pipeline with Git LFS filter
    let lfs_driver = Driver {
        name: "lfs".into(),
        clean: Some("git-lfs clean -- %f".into()),
        smudge: Some("git-lfs smudge -- %f".into()),
        process: Some("git-lfs filter-process".into()),
        required: true,
    };
    
    Pipeline::new(
        Default::default(),
        pipeline::Options {
            drivers: vec![lfs_driver],
            ..Default::default()
        },
    )
}

fn process_lfs_checkout(
    blob_content: &[u8],
    relative_path: &str,
    attributes: &mut dyn FnMut(&bstr::BStr, &mut Outcome),
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut pipeline = setup_lfs_filter_pipeline();
    
    // Apply filters with LFS smudge support
    let mut result = pipeline.convert_to_worktree(
        blob_content,
        relative_path.as_ref(),
        attributes,
        driver::apply::Delay::Forbid,
    )?;
    
    // Stream the result from LFS
    if let Some(reader) = result.as_read() {
        let mut output = Vec::new();
        std::io::copy(reader, &mut output)?;
        Ok(output)
    } else {
        // Just return the buffer if no streaming was needed
        Ok(result.as_bytes().unwrap_or_default().to_vec())
    }
}
```

### 4. Cross-Platform Line Ending Handling

#### Problem

Git repositories often contain files that need to be used on multiple platforms with different line ending conventions (LF on Unix-like systems, CRLF on Windows). Proper line ending conversion is critical for text files to be usable on all platforms while maintaining compatibility with tools.

#### Solution

The EOL filters handle line ending conversions based on Git attributes and configuration:

```rust
use gix_filter::{Pipeline, pipeline, eol};
use gix_attributes::search::Outcome;

fn configure_line_ending_aware_pipeline() -> Pipeline {
    Pipeline::new(
        Default::default(),
        pipeline::Options {
            // Configure EOL handling based on core.autocrlf setting
            eol_config: eol::Configuration {
                // Equivalent to core.autocrlf=input
                auto_crlf: eol::AutoCrlf::Input,
                // Use platform-native EOL in working tree
                eol: None,
            },
            // Configure how to handle round-trip safety checks
            crlf_roundtrip_check: pipeline::CrlfRoundTripCheck::Warn,
            ..Default::default()
        },
    )
}

fn normalize_line_endings_for_commit(
    file_content: &[u8],
    relative_path: &str,
    attributes: &mut dyn FnMut(&bstr::BStr, &mut Outcome),
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut pipeline = configure_line_ending_aware_pipeline();
    
    // Convert to Git format (normalizing to LF)
    let mut result = pipeline.convert_to_git(
        std::io::Cursor::new(file_content),
        std::path::Path::new(relative_path),
        attributes,
        &mut |_| Ok(None),
    )?;
    
    // Return the normalized content
    let mut output = Vec::new();
    std::io::copy(&mut result, &mut output)?;
    Ok(output)
}
```

### 5. Character Encoding Transformation

#### Problem

Some files need to be stored in Git with one encoding but displayed in the working tree with another encoding. For example, files might be edited in UTF-16 but stored in UTF-8 for better compatibility and space efficiency.

#### Solution

The working-tree-encoding filter handles encoding transformations:

```rust
use gix_filter::Pipeline;
use gix_attributes::search::Outcome;

fn setup_encoding_attributes(
    path: &bstr::BStr,
    outcome: &mut Outcome,
) {
    // Set up attributes to specify working-tree-encoding for specific file types
    if path.ends_with(b".txt") {
        outcome.insert("working-tree-encoding", Some("UTF-16LE".into()));
    }
}

fn convert_encoding_for_checkout(
    blob_content: &[u8],
    relative_path: &str,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut pipeline = Pipeline::default();
    let mut attributes = Outcome::default();
    
    // Apply encoding conversion
    let result = pipeline.convert_to_worktree(
        blob_content,
        relative_path.as_ref(),
        &mut setup_encoding_attributes,
        gix_filter::driver::apply::Delay::Forbid,
    )?;
    
    // Return the content with converted encoding
    Ok(result.as_bytes().unwrap_or_default().to_vec())
}
```

### 6. Ident Substitution

#### Problem

Source files often include expandable keywords like `$Id$` that should be replaced with the Git object ID when checking out files, allowing developers to see which version of the file they're looking at.

#### Solution

The ident filter handles substitution of ident patterns:

```rust
use gix_filter::{Pipeline, pipeline};
use gix_attributes::search::Outcome;

fn setup_ident_attributes(
    path: &bstr::BStr,
    outcome: &mut Outcome,
) {
    // Set up ident attribute for specific file types
    if path.ends_with(b".c") || path.ends_with(b".h") {
        outcome.insert("ident", None);
    }
}

fn expand_idents_for_checkout(
    blob_content: &[u8],
    relative_path: &str,
    object_hash: gix_hash::Kind,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut pipeline = Pipeline::new(
        Default::default(),
        pipeline::Options {
            object_hash,
            ..Default::default()
        },
    );
    
    // Apply ident expansion
    let result = pipeline.convert_to_worktree(
        blob_content,
        relative_path.as_ref(),
        &mut setup_ident_attributes,
        gix_filter::driver::apply::Delay::Forbid,
    )?;
    
    // Return the content with expanded idents
    Ok(result.as_bytes().unwrap_or_default().to_vec())
}
```

### 7. Implementing a Long-Running Filter Process

#### Problem

Custom filter programs can be more efficient when implemented as long-running processes that handle multiple files, especially on platforms like Windows where process creation is expensive.

#### Solution

The driver module provides server and client implementations for the Git filter protocol:

```rust
use std::io::{self, Read, Write};
use gix_filter::driver::process;

fn run_custom_filter_server() -> Result<(), Box<dyn std::error::Error>> {
    // Set up the server using stdin/stdout
    let stdin = io::stdin();
    let stdout = io::stdout();
    
    // Perform protocol handshake
    let mut server = process::Server::handshake(
        stdin,
        stdout,
        "custom-filter",
        &mut |versions| versions.contains(&2).then_some(2),
        &["clean", "smudge"],
    )?;
    
    // Process filter requests
    while let Some(mut request) = server.next_request()? {
        match request.command.as_str() {
            "clean" => {
                // Read input content
                let mut content = Vec::new();
                request.as_read().read_to_end(&mut content)?;
                
                // Signal success and that we'll be writing output
                request.write_status(process::Status::success())?;
                
                // Implement custom transformation for storing in Git
                // ...transform content...
                
                // Write transformed content
                request.as_write().write_all(&content)?;
                
                // Signal the end of our response
                request.write_status(process::Status::Previous)?;
            },
            "smudge" => {
                // Similar logic for the inverse transformation
                // ...
            },
            _ => {
                // Reject unknown commands
                request.write_status(process::Status::abort())?;
            }
        }
    }
    
    Ok(())
}
```

### 8. Delayed Processing for Large Files

#### Problem

Some filter operations on large files can be time-consuming, and it's more efficient to process them asynchronously while letting the main checkout operation continue with other files.

#### Solution

The driver system supports delayed processing:

```rust
use gix_filter::{Pipeline, driver};
use gix_attributes::search::Outcome;

fn process_files_with_delayed_filtering(
    files: &[(String, Vec<u8>)],
    attributes: &mut dyn FnMut(&bstr::BStr, &mut Outcome),
) -> Result<(), Box<dyn std::error::Error>> {
    let mut pipeline = Pipeline::default();
    let mut delayed_files = Vec::new();
    
    // Process all files, allowing delayed processing
    for (path, content) in files {
        let result = pipeline.convert_to_worktree(
            &content,
            path.as_ref(),
            attributes,
            driver::apply::Delay::Allow,
        )?;
        
        if result.is_delayed() {
            // Keep track of files that need delayed processing
            delayed_files.push(path.clone());
        } else {
            // Handle immediate results
            // ...
        }
    }
    
    // Wait for and process delayed results
    if !delayed_files.is_empty() {
        println!("Waiting for {} files to complete processing...", delayed_files.len());
        
        // Get all delayed results by checking the driver state
        let driver_state = pipeline.driver_state_mut();
        for path in &delayed_files {
            if let Some(result) = driver_state.get_delayed_result(path)? {
                // Process the delayed result
                // ...
            }
        }
    }
    
    // Clean up filter processes
    pipeline.into_driver_state().shutdown(driver::shutdown::Deadline::None)?;
    
    Ok(())
}
```

### 9. Stream Processing for Memory Efficiency

#### Problem

When handling large files, loading the entire file into memory can be inefficient. Streaming filters allow processing files piece by piece without excessive memory usage.

#### Solution

The filter system supports streaming operations:

```rust
use std::{io, fs::File};
use gix_filter::{Pipeline, driver};
use gix_attributes::search::Outcome;

fn stream_large_file_checkout(
    file_path: &str,
    output_path: &str,
    attributes: &mut dyn FnMut(&bstr::BStr, &mut Outcome),
) -> Result<(), Box<dyn std::error::Error>> {
    let mut pipeline = Pipeline::default();
    
    // Open the Git blob source
    let blob_source = File::open(file_path)?;
    
    // Apply filters
    let mut result = pipeline.convert_to_git(
        blob_source,
        std::path::Path::new(file_path),
        attributes,
        &mut |_| Ok(None),
    )?;
    
    // Stream directly to output file
    let mut output_file = File::create(output_path)?;
    io::copy(&mut result, &mut output_file)?;
    
    Ok(())
}
```

## Integration with Other Components

The gix-filter crate integrates with several other components in the gitoxide ecosystem:

### Integration with Checkout Operations

```rust
// Integration with worktree checkout
fn checkout_files(
    repo: &gix::Repository,
    tree: &gix::object::Tree<'_>,
    target_dir: &std::path::Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut pipeline = gix_filter::Pipeline::default();
    
    // Get attribute stack from the repository
    let mut attr_stack = repo.attributes()?;
    
    // Process each entry in the tree
    for entry in tree.iter() {
        let entry_path = entry.filename.to_str()?;
        let object = entry.object()?;
        
        if let gix::object::Kind::Blob = object.kind() {
            let blob = object.into_blob();
            let content = blob.data;
            
            // Apply filters based on attributes
            let filtered = pipeline.convert_to_worktree(
                content,
                entry_path.as_ref(),
                &mut |path, outcome| {
                    attr_stack.fill(path, outcome);
                },
                gix_filter::driver::apply::Delay::Forbid,
            )?;
            
            // Write the filtered content to the target file
            let target_file = target_dir.join(entry_path);
            if let Some(parent) = target_file.parent() {
                std::fs::create_dir_all(parent)?;
            }
            
            let mut file = std::fs::File::create(target_file)?;
            std::io::copy(&mut filtered, &mut file)?;
        }
    }
    
    // Clean up filter processes
    pipeline.into_driver_state().shutdown(gix_filter::driver::shutdown::Deadline::None)?;
    
    Ok(())
}
```

### Integration with Add/Stage Operations

```rust
// Integration with staging files to index
fn stage_file(
    repo: &gix::Repository,
    file_path: &std::path::Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut pipeline = gix_filter::Pipeline::default();
    
    // Get attribute stack from the repository
    let mut attr_stack = repo.attributes()?;
    
    // Read the file content
    let content = std::fs::read(file_path)?;
    
    // Get relative path for attribute lookup
    let repo_relative_path = file_path.strip_prefix(repo.workdir()?)?;
    
    // Apply filters to prepare for Git storage
    let filtered = pipeline.convert_to_git(
        std::io::Cursor::new(content),
        repo_relative_path,
        &mut |path, outcome| {
            attr_stack.fill(path, outcome);
        },
        &mut |_| Ok(None),
    )?;
    
    // Read the filtered content into a buffer
    let mut buffer = Vec::new();
    std::io::copy(&mut filtered, &mut buffer)?;
    
    // Create a blob with the filtered content
    let id = repo.objects()?.write(&buffer, gix::object::Kind::Blob)?;
    
    // Update the index entry
    let mut index = repo.index()?;
    index.add_entry(repo_relative_path, id, false)?;
    index.write()?;
    
    Ok(())
}
```

### Integration with Git Attributes

```rust
// Integration with Git attributes system
fn setup_attribute_provider(
    repo: &gix::Repository,
) -> Result<impl Fn(&bstr::BStr, &mut gix_attributes::search::Outcome), Box<dyn std::error::Error>> {
    // Create an attribute stack
    let attr_stack = repo.attributes()?;
    
    // Return a closure that looks up attributes
    Ok(move |path: &bstr::BStr, outcome: &mut gix_attributes::search::Outcome| {
        attr_stack.fill(path, outcome);
    })
}
```

## Conclusion

The gix-filter crate provides a comprehensive implementation of Git's content filtering system, enabling correct handling of files as they move between Git's object database and the working tree. It supports all standard Git filters (EOL, ident, working-tree-encoding) as well as external filters through a flexible driver system.

By offering both high-level interfaces for common operations and low-level components for custom implementations, the crate serves a wide range of use cases from basic line ending conversion to complex custom filtering with streaming and delayed processing support.