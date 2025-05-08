# gix-archive

## Overview

`gix-archive` is a crate dedicated to creating archives from Git repositories, similar to the `git archive` command. It takes a stream of worktree entries and packages them into various archive formats. This crate serves as the implementation for creating Git repository archives in gitoxide.

## Architecture

The architecture of `gix-archive` is designed around a simple, flexible streaming model:

1. **Stream-Based Processing**: The crate operates on a stream of worktree entries (`gix_worktree_stream::Stream`), converting them into the specified archive format on-the-fly.

2. **Multiple Format Support**: The core functionality supports various archive formats (tar, tar.gz, zip) through feature flags, allowing for customization based on requirements.

3. **Configurable Output**: The archive creation can be configured with options for tree prefixes and modification times.

4. **Streaming Interface**: The crate provides functions for both standard stream writing and seek-enabled stream writing (required for some formats like zip).

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Options` | Configures archive creation, including format, tree prefix, and modification time | Used as a parameter to `write_stream` and `write_stream_seek` to control archive creation |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Format` | Specifies the archive format | `InternalTransientNonPersistable`, `Tar`, `TarGz`, `Zip` |
| `Error` | Error types for archive operations | Various error types related to I/O, format support, etc. |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `write_stream` | Writes a worktree stream to a regular Write implementation | `fn write_stream<NextFn>(stream: &mut Stream, next_entry: NextFn, out: impl std::io::Write, opts: Options) -> Result<(), Error>` |
| `write_stream_seek` | Writes a worktree stream to a Seek-enabled Write implementation | `fn write_stream_seek<NextFn>(stream: &mut Stream, next_entry: NextFn, out: impl std::io::Write + std::io::Seek, opts: Options) -> Result<(), Error>` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-worktree-stream` | Provides the stream of worktree entries to archive |
| `gix-object` | Used for object-related functionality, especially tree entry modes and kinds |
| `gix-path` | Used for path handling when optional `tar` feature is enabled |
| `gix-date` | Used for handling date/time functionality for archive entries |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `tar` | Implements the tar archive format (optional) |
| `flate2` | Provides compression for tar.gz format (optional) |
| `zip` | Implements the zip archive format (optional) |
| `jiff` | Date/time handling for zip archives |
| `bstr` | Binary string handling |
| `thiserror` | Error handling |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `tar` | Enables support for the tar archive format | `tar`, `gix-path` |
| `tar_gz` | Enables support for the compressed tar.gz archive format | Depends on `tar`, adds `flate2` |
| `zip` | Enables support for the zip archive format | `flate2`, `zip` |
| `default` | Default features | Enables `tar`, `tar_gz`, and `zip` |

## Examples

### Creating a tar archive from a worktree stream

```rust
use gix_archive::{Format, Options, write_stream};
use gix_worktree_stream::Stream;
use std::io::BufWriter;
use std::fs::File;

// Set up a worktree stream (simplified)
let mut stream = /* some gix_worktree_stream::Stream */;

// Configure archive options
let options = Options {
    format: Format::Tar,
    tree_prefix: Some("prefix/".into()),  // Add a prefix to all paths
    modification_time: 1620000000,        // Set modification time for all entries
};

// Create a file to write the archive to
let file = File::create("output.tar")?;
let buffered_writer = BufWriter::new(file);

// Write the archive
write_stream(
    &mut stream,
    Stream::next_entry,  // Function to get the next entry
    buffered_writer,
    options,
)?;
```

### Creating a zip archive (requires seek capability)

```rust
use gix_archive::{Format, Options, write_stream_seek};
use gix_worktree_stream::Stream;
use std::io::{BufWriter, Cursor};

// Set up a worktree stream (simplified)
let mut stream = /* some gix_worktree_stream::Stream */;

// Configure archive options with zip format and compression level
let options = Options {
    format: Format::Zip { compression_level: Some(6) },
    tree_prefix: None,  // No prefix
    modification_time: std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|t| t.as_secs() as i64)
        .unwrap_or_default(),
};

// Create a memory buffer that supports seeking
let mut buffer = Vec::new();
let cursor = Cursor::new(&mut buffer);

// Write the archive
write_stream_seek(
    &mut stream,
    Stream::next_entry,
    cursor,
    options,
)?;

// Use the resulting buffer (e.g., write to file, serve over HTTP, etc.)
```

## Implementation Details

1. **Format-Specific Implementation**:
   - The crate uses conditional compilation to include only the code needed for the enabled formats.
   - Tar and tar.gz formats use the `tar` crate for archive creation.
   - Zip format uses the `zip` crate and requires `std::io::Seek` capability.

2. **Streaming Approach**:
   - The crate processes one entry at a time from the worktree stream, minimizing memory usage.
   - For tar format, this has a limitation with large files since the header needs to know the file size upfront.

3. **Prefixing**:
   - The crate allows adding a prefix to all paths in the archive, similar to the `--prefix` option in `git archive`.

4. **Entry Type Mapping**:
   - Git object types are mapped to corresponding archive entry types (regular files, directories, symlinks).

5. **Performance Considerations**:
   - The caller is responsible for using a fast enough writer (e.g., `BufWriter`).
   - Zip format can stream large files efficiently, unlike the tar implementation.

## Testing Strategy

The crate is tested through integration tests that:

1. Create archives in different formats from a test repository
2. Verify the content and structure of the resulting archives
3. Test with various options (compression levels, prefixes, etc.)
4. Ensure proper handling of different entry types (files, directories, symlinks)

The tests also include specific assertions for each format to verify proper implementation of the format-specific details.