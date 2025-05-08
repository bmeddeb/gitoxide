# gix-packetline-blocking

## Overview

`gix-packetline-blocking` is a specialized crate in the gitoxide ecosystem that provides blocking IO functionality for Git's packet line protocol. This crate is effectively a subset of the `gix-packetline` crate with the `blocking-io` feature pre-selected, making it easier to use in contexts where only synchronous IO is needed.

The packet line protocol is the foundation of Git's network communication, providing a simple framing mechanism for data exchange between Git clients and servers. This crate offers a high-performance implementation for reading and writing packet lines with a focus on minimal allocations and efficient IO operations.

## Architecture

`gix-packetline-blocking` is a direct copy of `gix-packetline` with the `blocking-io` feature enabled by default. It maintains the same architecture and design principles:

1. **Core Types**: Defines the core packet line types and structures
2. **Reading**: Provides synchronous stream-based packet line reading
3. **Writing**: Implements efficient packet line writing with binary and text modes
4. **Encoding/Decoding**: Contains utilities for packet line format encoding and decoding

The crate is automatically kept in sync with `gix-packetline` through a build script (`etc/copy-packetline.sh`) that copies the files and adds a header indicating they should not be edited directly.

### Key Components

#### Core Types

- `PacketLineRef<'a>`: A borrowed representation of a packet line
- `StreamingPeekableIter<T>`: Core reader for processing packet lines sequentially
- `Writer<T>`: Writer that formats data as packet lines
- `Channel`: Side-band type for multiplexing information
- `BandRef<'a>`: Representation of a side-band channel packet
- `ErrorRef<'a>` and `TextRef<'a>`: Specialized packet line types

#### Constants and Protocol Details

The implementation defines several protocol-specific constants:

```rust
const U16_HEX_BYTES: usize = 4;           // Prefix size in bytes
const MAX_DATA_LEN: usize = 65516;        // Maximum data length
const MAX_LINE_LEN: usize = MAX_DATA_LEN + U16_HEX_BYTES;
const FLUSH_LINE: &[u8] = b"0000";        // Special line indicating flush
const DELIMITER_LINE: &[u8] = b"0001";    // Special line for delimiting
const RESPONSE_END_LINE: &[u8] = b"0002"; // Special line for end of response
const ERR_PREFIX: &[u8] = b"ERR ";        // Prefix for error messages
```

### Reading Implementation

The `StreamingPeekableIter` type provides efficient reading with synchronous IO:

- `read_line()`: Reads a single packet line from the stream
- `peek_line()`: Examines the next packet line without consuming it
- `read_line_inner()`: Internal method for actual packet parsing
- `as_read_with_sidebands()`: Adapts the reader for side-band protocol support
- `reset()` and `reset_with()`: Allow reusing the reader after encountering a delimiter

The implementation is designed to minimize allocations and efficiently handle packet lines of various types.

### Writing Implementation

The `Writer` type implements `std::io::Write` for packet line formatting:

- `write()`: Writes data as packet lines, handling fragmentation for large inputs
- `enable_binary_mode()` and `enable_text_mode()`: Control the output format
- `flush()`: Passes through to the inner writer

### Encoding Utilities

The `encode` module provides functions for writing specific packet line types:

- `data_to_write()`: Writes raw data as a packet line
- `text_to_write()`: Writes text with automatic newline handling
- `flush_to_write()`, `delim_to_write()`, `response_end_to_write()`: Write special packet lines
- `error_to_write()`: Writes error messages
- `band_to_write()`: Writes side-band data for multiplexed connections

## Dependencies

The crate has minimal dependencies to maintain efficiency:

- `gix-trace`: Used for tracing/logging packet lines
- `bstr`: Handling binary strings efficiently
- `thiserror`: Error handling
- `faster-hex`: High-performance hex encoding/decoding
- `serde` (Optional): Serialization support for data structures

## Feature Flags

While the crate is designed specifically for blocking IO, it provides a few feature flags:

- `blocking-io`: Enabled by default, provides blocking IO operations
- `async-io`: Disabled and not intended for use (the crate's documentation explicitly advises against using this feature)
- `serde`: Adds serialization support for data structures

## Implementation Details

### Packet Line Format

The Git packet line format consists of:

1. A 4-byte hex prefix specifying the total length (including the prefix)
2. The actual content

Special packet lines include:
- `0000`: Flush packet (end of section)
- `0001`: Delimiter packet (separates sections)
- `0002`: Response end packet

### Side-band Protocol Support

The crate supports Git's side-band protocol, which multiplexes three channels over a single connection:

1. `Data` (Channel 1): The primary content
2. `Progress` (Channel 2): User-readable progress information
3. `Error` (Channel 3): User-readable error messages

The `WithSidebands` adapter processes side-band encoded packet lines and routes data to the appropriate handlers.

### Error Handling

The implementation provides detailed error types:

- `decode::Error`: Parsing and validation errors
- `encode::Error`: Content formatting errors
- `read::Error`: Specialized error for ERR packet lines

### Relationship to gix-packetline

This crate is a convenience wrapper around `gix-packetline` with the blocking feature enabled by default. The code is kept in sync through an automated process:

1. The `etc/copy-packetline.sh` script copies files from `gix-packetline`
2. Each file is prefixed with a header warning against direct edits
3. The script is run via the `just copy-packetline` command

This approach ensures that improvements to the main implementation are automatically available in the blocking variant.

## Usage Examples

### Reading Packet Lines

```rust
use std::io::BufReader;
use gix_packetline_blocking::{PacketLineRef, StreamingPeekableIter};

fn process_git_response(reader: impl std::io::Read) -> std::io::Result<()> {
    // Create a reader with Flush as a delimiter
    let mut line_reader = StreamingPeekableIter::new(
        BufReader::new(reader),
        &[PacketLineRef::Flush],
        true // Enable tracing
    );
    
    // Read packet lines until we're done
    while let Some(line) = line_reader.read_line()? {
        match line {
            PacketLineRef::Data(data) => {
                println!("Received data: {:?}", data);
                // Process the data...
            },
            PacketLineRef::Flush => {
                println!("End of data section");
                break;
            },
            PacketLineRef::Delimiter => {
                println!("Section delimiter");
                // Handle the section transition...
                line_reader.reset(); // Continue after delimiter
            },
            PacketLineRef::ResponseEnd => {
                println!("Response complete");
                break;
            }
        }
    }
    
    Ok(())
}
```

### Writing Packet Lines

```rust
use std::io::BufWriter;
use gix_packetline_blocking::Writer;

fn send_git_command(
    stream: impl std::io::Write,
    command: &str,
    args: &[&str]
) -> std::io::Result<()> {
    let mut writer = Writer::new(BufWriter::new(stream)).text_mode();
    
    // Write the command
    writer.write_all(command.as_bytes())?;
    
    // Write the arguments
    for arg in args {
        writer.write_all(arg.as_bytes())?;
    }
    
    // Send a flush packet to indicate the end of the command
    gix_packetline_blocking::encode::flush_to_write(writer.inner_mut())?;
    writer.flush()?;
    
    Ok(())
}
```

### Working with Side-band Protocol

```rust
use std::io::BufReader;
use gix_packetline_blocking::{PacketLineRef, StreamingPeekableIter};
use gix_packetline_blocking::read::ProgressAction;

fn process_with_sidebands(stream: impl std::io::Read) -> std::io::Result<Vec<u8>> {
    let mut line_reader = StreamingPeekableIter::new(
        BufReader::new(stream),
        &[PacketLineRef::Flush],
        true
    );
    
    // Set up progress handling
    let mut data = Vec::new();
    let mut with_sidebands = line_reader.as_read_with_sidebands(|is_error, text| {
        if is_error {
            eprintln!("Error: {:?}", text);
            ProgressAction::Interrupt
        } else {
            println!("Progress: {:?}", text);
            ProgressAction::Continue
        }
    });
    
    // Read all data from the main channel
    with_sidebands.read_to_end(&mut data)?;
    
    Ok(data)
}
```

### Peeking at Packet Lines

```rust
use gix_packetline_blocking::{PacketLineRef, StreamingPeekableIter};

fn inspect_git_stream(reader: impl std::io::Read) -> std::io::Result<()> {
    let mut line_reader = StreamingPeekableIter::new(
        reader,
        &[PacketLineRef::Flush],
        true
    );
    
    // Peek at the next packet without consuming it
    if let Some(Ok(Ok(next_packet))) = line_reader.peek_line() {
        println!("Next packet is: {:?}", next_packet);
        
        // Now consume it if it's what we want
        if let PacketLineRef::Data(data) = next_packet {
            if data.starts_with(b"wanted-prefix") {
                line_reader.read_line();  // Actually consume it
                // Process the data...
            }
        }
    }
    
    Ok(())
}
```

## Design Considerations

1. **Efficiency**: The implementation is designed to minimize allocations and memory copies, making it suitable for handling large repositories.

2. **Zero-Copy Approach**: Uses borrowed references like `PacketLineRef<'a>` to avoid unnecessary allocations.

3. **Feature Isolation**: By having a separate crate with blocking IO pre-selected, it simplifies dependency management for projects that only need synchronous operations.

4. **Maintenance Strategy**: The automated copy process ensures that improvements to the main implementation are reliably propagated to the blocking variant.

## Related Components

`gix-packetline-blocking` is part of the network communication stack:

- `gix-packetline`: The parent crate that supports both blocking and async IO
- `gix-protocol`: Higher-level Git protocol implementation
- `gix-transport`: Transport layer that uses packet lines for communication

## Conclusion

`gix-packetline-blocking` provides efficient, allocation-conscious implementation of Git's packet line protocol with a focus on synchronous IO operations. It offers the same functionality as the core `gix-packetline` crate but with a simplified feature set optimized for blocking IO contexts. This specialization helps reduce dependencies and compilation complexity for projects that don't require async support.