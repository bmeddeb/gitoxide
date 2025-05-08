# gix-filter

## Overview

The `gix-filter` crate provides a comprehensive implementation of Git's content filtering system. It enables the transformation of file content when moving between Git's object database and the working tree, handling operations such as line ending conversions, ident substitution, character encoding transformations, and external filter programs. This crate serves as a crucial component in maintaining file integrity across different platforms and ensuring correct file formatting according to user-defined rules.

## Architecture

The `gix-filter` crate follows a modular design centered around the concept of a filter pipeline where multiple filters can be applied sequentially to transform file content. The architecture consists of several key components:

1. **Pipeline**: The central component that orchestrates the application of filters based on file attributes and configuration.

2. **Filter Types**: Several specialized filter modules, each handling a specific type of transformation:
   - **EOL Filters**: Convert line endings between repository format (LF) and working tree format (platform-specific or configured).
   - **Ident Filters**: Replace `$Id$` patterns with Git object IDs.
   - **Working Tree Encoding Filters**: Convert file encoding based on the `working-tree-encoding` attribute.
   - **Driver Filters**: Interface with external filter programs for custom transformations.

3. **Processing Direction**:
   - **To Git**: Transform content from working tree format to Git repository format.
   - **To Working Tree**: Transform content from Git repository format to working tree format.

4. **Driver System**: Handles interaction with external filter programs, supporting both single-invocation filters and long-running filter processes.

The architecture emphasizes:
- **Performance**: Efficient buffer handling and processing with minimal copying.
- **Flexibility**: Support for various filter types and configurations.
- **Streaming**: Support for both in-memory and streaming operations.
- **Configurability**: Extensive options for controlling filter behavior.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Pipeline` | The main filter pipeline that applies multiple filters based on file attributes | Used to transform file content between Git and working tree formats |
| `Driver` | Represents an external filter program configuration | Defines clean, smudge, and process programs for external filtering |
| `driver::State` | Manages the state of long-running filter processes | Tracks running processes and handles delayed filtering operations |
| `pipeline::Options` | Configuration options for the filter pipeline | Controls behavior of filters and provides driver programs |
| `pipeline::Context` | Additional context for filter operations | Provides information about the repository state for filter processes |
| `eol::Configuration` | Configuration for line ending conversions | Controls behavior of EOL filters |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `eol::Mode` | The type of line ending to use | `Lf`, `CrLf` |
| `eol::AutoCrlf` | Possible states for `core.autocrlf` configuration | `Input`, `Enabled`, `Disabled` |
| `eol::AttributesDigest` | Combination of EOL-related attributes | Multiple variants for different attribute combinations |
| `pipeline::CrlfRoundTripCheck` | How to handle CRLF round-trip checking | `Fail`, `Warn`, `Skip` |
| `driver::Operation` | Type of filter operation | `Clean`, `Smudge` |
| `driver::Process` | Type of external filter process | `SingleFile`, `MultiFile` |
| `ToGitOutcome` | Result of conversion to Git format | `Unchanged`, `Process`, `Buffer` |
| `ToWorktreeOutcome` | Result of conversion to working tree format | `Unchanged`, `Buffer`, `Process` |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `Pipeline::new` | Create a new filter pipeline | `fn new(context: gix_command::Context, options: Options) -> Self` |
| `Pipeline::convert_to_git` | Apply filters to prepare content for Git storage | `fn convert_to_git<R>(&mut self, src: R, rela_path: &Path, attributes: &mut dyn FnMut(&BStr, &mut gix_attributes::search::Outcome), index_object: &mut to_git::IndexObjectFn<'_>) -> Result<ToGitOutcome<'_, R>, to_git::Error>` |
| `Pipeline::convert_to_worktree` | Apply filters to prepare content for the working tree | `fn convert_to_worktree<'input>(&mut self, src: &'input [u8], rela_path: &BStr, attributes: &mut dyn FnMut(&BStr, &mut gix_attributes::search::Outcome), can_delay: driver::apply::Delay) -> Result<ToWorktreeOutcome<'input, '_>, to_worktree::Error>` |
| `eol::convert_to_git` | Convert line endings for Git storage | `fn convert_to_git(src: &[u8], digest: eol::AttributesDigest, dst: &mut Vec<u8>, index_object: &mut impl FnMut(&mut Vec<u8>) -> Result<Option<()>, gix_object::find::Error>, options: eol::convert_to_git::Options) -> Result<bool, eol::convert_to_git::Error>` |
| `eol::convert_to_worktree` | Convert line endings for working tree | `fn convert_to_worktree(src: &[u8], digest: eol::AttributesDigest, dst: &mut Vec<u8>, config: eol::Configuration) -> Result<bool, eol::convert_to_worktree::Error>` |
| `ident::apply` | Apply `$Id$` substitution (Git to working tree) | `fn apply(src: &[u8], object_hash: gix_hash::Kind, dst: &mut Vec<u8>) -> Result<bool, ident::apply::Error>` |
| `ident::undo` | Undo `$Id$` substitution (working tree to Git) | `fn undo(src: &[u8], dst: &mut Vec<u8>) -> Result<bool, ident::apply::Error>` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For handling object IDs and computing hashes |
| `gix-trace` | For logging and tracing filter operations |
| `gix-object` | For accessing Git objects |
| `gix-command` | For executing external filter programs |
| `gix-quote` | For properly quoting filenames in filter commands |
| `gix-utils` | For utility functions and buffer management |
| `gix-path` | For path manipulation and normalization |
| `gix-packetline-blocking` | For communication with long-running filter processes |
| `gix-attributes` | For handling Git attributes that control filtering |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `encoding_rs` | For character encoding conversion |
| `bstr` | For byte string handling |
| `thiserror` | For error type definitions |
| `smallvec` | For efficient small vector allocations |

## Feature Flags

The crate doesn't define its own feature flags but inherits features from its dependencies.

## Examples

### Basic Filter Pipeline Usage

```rust
use std::path::Path;
use bstr::ByteSlice;
use gix_filter::{Pipeline, driver};
use gix_attributes::search::Outcome;

// Create a default filter pipeline
let mut pipeline = Pipeline::default();

// Convert content to working tree format
let content = b"hello\nworld\n";  // Git format (LF line endings)
let result = pipeline.convert_to_worktree(
    content,
    "example.txt".as_ref(),
    &mut |_, _| {},  // No attributes for this example
    driver::apply::Delay::Allow,
)?;

// Use the result
match result {
    gix_filter::ToWorktreeOutcome::Unchanged(bytes) => {
        // Content wasn't changed
        println!("Unchanged: {}", bytes.as_bstr());
    },
    gix_filter::ToWorktreeOutcome::Buffer(bytes) => {
        // Content was transformed
        println!("Transformed: {}", bytes.as_bstr());
    },
    gix_filter::ToWorktreeOutcome::Process(stream) => {
        // Content is being processed by an external filter
        // Read from the stream
    }
}
```

### Configuring a Filter Pipeline with Attributes

```rust
use std::path::Path;
use gix_filter::{Pipeline, pipeline, eol, driver, Driver};
use gix_attributes::search::Outcome;

// Create a pipeline with specific options
let mut pipeline = Pipeline::new(
    Default::default(),
    pipeline::Options {
        // Add external filter drivers
        drivers: vec![
            Driver {
                name: "lfs".into(),
                clean: Some("git-lfs clean -- %f".into()),
                smudge: Some("git-lfs smudge -- %f".into()),
                process: Some("git-lfs filter-process".into()),
                required: true,
            }
        ],
        // Configure EOL handling
        eol_config: eol::Configuration {
            auto_crlf: eol::AutoCrlf::Input,
            eol: Some(eol::Mode::Lf),
        },
        // Configure round-trip checks
        crlf_roundtrip_check: pipeline::CrlfRoundTripCheck::Warn,
        // Configure encodings requiring round-trip checks
        encodings_with_roundtrip_check: vec![encoding_rs::UTF_16LE],
        // Set object hash for ident filter
        object_hash: gix_hash::Kind::Sha1,
    },
);

// Create a system for attribute lookup
let mut attributes = Outcome::default();
let mut attribute_provider = |path: &bstr::BStr, outcome: &mut Outcome| {
    // Populate outcome with attributes for path
    if path.ends_with(b".txt") {
        outcome.insert("text", Some("auto".into()));
        outcome.insert("eol", Some("lf".into()));
    } else if path.ends_with(b".bin") {
        outcome.insert("binary", None);
    } else if path.ends_with(b".lfs") {
        outcome.insert("filter", Some("lfs".into()));
    }
};

// Convert content from Git to working tree
let content = b"Some content with $Id$\n";
let result = pipeline.convert_to_worktree(
    content,
    "example.txt".as_ref(),
    &mut attribute_provider,
    driver::apply::Delay::Forbid,
)?;
```

### Implementing a Custom Filter Process

```rust
use std::io::{Read, Write};
use gix_filter::driver::process;

// Server side (the filter program)
fn run_filter_server() -> Result<(), Box<dyn std::error::Error>> {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    
    // Perform handshake and create server
    let mut server = process::Server::handshake(
        stdin,
        stdout,
        "my-filter",
        &mut |versions| versions.contains(&2).then_some(2),
        &["clean", "smudge"],
    )?;
    
    // Process requests
    while let Some(mut request) = server.next_request()? {
        match request.command.as_str() {
            "clean" => {
                // Read input content
                let mut content = Vec::new();
                request.as_read().read_to_end(&mut content)?;
                
                // Signal success
                request.write_status(process::Status::success())?;
                
                // Write transformed content
                request.as_write().write_all(&content)?;
                request.write_status(process::Status::Previous)?;
            },
            "smudge" => {
                // Similar logic for smudge operation
                // ...
            },
            _ => {
                request.write_status(process::Status::abort())?;
            }
        }
    }
    Ok(())
}
```

## Implementation Details

### Filter Pipeline Operation

The filter pipeline performs the following operations:

1. **Attribute Resolution**: Determines which filters should be applied based on Git attributes at the file's path.

2. **Filter Application**:
   - **To Git**: Applies filters in the order: working-tree-encoding → EOL conversion → ident substitution.
   - **To Working Tree**: Applies filters in the order: ident substitution → EOL conversion → working-tree-encoding.

3. **External Filter Integration**:
   - Detects when an external filter should be applied based on the `filter` attribute.
   - Chooses the most efficient filter method available (process > clean/smudge).
   - Supports delayed processing for better performance with large files.

4. **Buffer Management**:
   - Uses a double-buffer approach to efficiently chain filter operations.
   - Avoids unnecessary memory allocations and copies.
   - Supports streaming when possible for large files.

### EOL Conversion Details

The EOL conversion applies complex rules based on:
- The `text` attribute (possibly with `auto` value)
- The `eol` attribute
- The `core.autocrlf` configuration
- The `core.eol` configuration

The conversion includes:
- **Round-trip safety checks**: Ensures conversions don't cause data loss
- **Binary detection**: Avoids performing conversions on binary files
- **Normalization**: Standardizes line endings in Git's object database to LF

### External Filter Process Protocol

The crate implements Git's filter process protocol (version 2), which allows:
- **Bidirectional communication**: Sending commands and receiving responses
- **Delayed processing**: Allowing efficient handling of large files
- **Multiple files per process**: Using a single long-running process for multiple files
- **Process lifecycle management**: Properly starting and terminating filter processes

## Testing Strategy

The crate is tested through:

1. **Unit Tests**: Testing individual filter components in isolation.
2. **Integration Tests**: Testing filter pipelines with various attribute combinations.
3. **Repository Tests**: Using test repositories with pre-configured attributes.
4. **External Filter Tests**: Testing interaction with mock filter programs.
5. **Edge Cases**: Testing binary files, invalid encodings, and other special cases.

The tests verify:
- Correct application of filters based on attributes
- Proper buffer management and memory usage
- Correct handling of external filter processes
- Compatibility with Git's filter behavior