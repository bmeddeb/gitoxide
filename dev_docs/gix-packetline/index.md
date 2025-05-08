# gix-packetline

## Overview

`gix-packetline` is a foundational crate in the gitoxide ecosystem that implements the Git "packet line" wire protocol format. This protocol is the foundation of Git's network communication, providing a simple framing mechanism for data exchange between Git clients and servers.

The crate offers high-performance implementations for both reading and writing packet lines with support for both synchronous (blocking) and asynchronous IO, while avoiding unnecessary memory allocations and copying where possible.

## Architecture

The crate follows a modular architecture focused on the core packet line protocol operations:

1. **Encoding and Decoding**: Core functionality to parse and generate packet lines
2. **Reading**: Stream-based packet line reading with support for sidebands
3. **Writing**: Efficient packet line writing with support for different modes
4. **Streaming Support**: Incremental parsing capabilities for efficient network operations
5. **Async/Blocking Duality**: Conditional compilation to support both IO paradigms

### Key Components

#### Core Types

- `PacketLineRef<'a>`: A borrowed representation of a packet line that refers to data by reference
- `StreamingPeekableIter<T>`: Core reader that processes packet lines one by one
- `Writer<T>`: Writes data as packet lines to an underlying writer
- `Channel`: Side-band type for multiplexing information over a single connection
- `BandRef<'a>`: A band in a side-band channel
- `ErrorRef<'a>`: Packet line representing an error
- `TextRef<'a>`: Packet line representing text

#### Constants and Limits

The protocol defines several special packet line formats and limits:

```rust
const U16_HEX_BYTES: usize = 4;           // Prefix size in bytes
const MAX_DATA_LEN: usize = 65516;        // Maximum data length
const MAX_LINE_LEN: usize = MAX_DATA_LEN + U16_HEX_BYTES;
const FLUSH_LINE: &[u8] = b"0000";        // Special line indicating flush
const DELIMITER_LINE: &[u8] = b"0001";    // Special line for delimiting
const RESPONSE_END_LINE: &[u8] = b"0002"; // Special line for end of response
const ERR_PREFIX: &[u8] = b"ERR ";        // Prefix for error messages
```

### Reading and Streaming

The `StreamingPeekableIter` provides efficient reading capabilities:

- Minimizes allocations for high performance
- Supports stopping at delimiter lines
- Handles incremental parsing
- Detects and optionally fails on error lines
- Supports sidebands for multiplexed communication
- Works with both blocking and async IO depending on feature flags

### Writing

The `Writer` provides functionality to write packet lines:

- Supports text and binary modes
- Automatically fragments large inputs that exceed maximum line length
- Efficient output with minimal allocations
- Dedicated functions for writing special lines (flush, delimiter, errors)

## Dependencies

The crate has minimal dependencies to maintain efficiency:

- `gix-trace`: Used for tracing/logging packet lines when enabled
- `bstr`: Handling binary strings efficiently
- `thiserror`: Error handling
- `faster-hex`: High-performance hex encoding/decoding
- `futures-io`, `futures-lite`, `pin-project-lite` (Optional): Async IO support
- `serde` (Optional): Serialization support

## Feature Flags

The crate provides several feature flags to customize its capabilities:

- `blocking-io`: Enables blocking IO operations
- `async-io`: Enables asynchronous IO operations with `futures-io`
- `serde`: Adds serialization support for data structures 

The `blocking-io` and `async-io` features are mutually exclusive - attempting to enable both results in a compile error.

## Implementation Details

### Packet Line Format

Git's packet line format consists of:

1. A 4-byte hex prefix specifying the total length (including the prefix itself)
2. The actual data content

Special packet lines are defined:
- `0000`: Flush packet (end of section)
- `0001`: Delimiter packet (separates sections)
- `0002`: Response end packet

### Streaming and Incremental Parsing

The incremental parsing approach enables efficient network operations:

```rust
// Incremental parsing result
pub enum Stream<'a> {
    // A complete packet line was parsed
    Complete {
        line: PacketLineRef<'a>,
        bytes_consumed: usize,
    },
    // Not enough data to parse a complete line
    Incomplete {
        bytes_needed: usize,
    },
}
```

This approach allows for:
- Processing packet lines as soon as they arrive
- Avoiding blocking while waiting for complete data
- Minimizing memory usage for large streams

### Side-band Protocol

The side-band protocol multiplexes three channels over a single connection:

1. `Data` (Channel 1): The actual content being transferred
2. `Progress` (Channel 2): User-readable progress information
3. `Error` (Channel 3): User-readable error messages

This allows Git to send multiple streams of information simultaneously, such as transmitting object data while providing progress updates.

### Zero-Copy Parsing

The crate emphasizes efficient, zero-copy parsing where possible:

- Uses borrowed reference types (`PacketLineRef<'a>`, `BandRef<'a>`) to avoid unnecessary allocations
- Implements streaming interfaces to avoid buffering large packets
- Employs incremental parsing for network efficiency

## Usage Examples

### Reading Packet Lines

```rust
use std::io::BufReader;
use gix_packetline::{decode, PacketLineRef, StreamingPeekableIter};

// Create a reader for incoming packet lines
let reader = BufReader::new(socket);
let mut line_reader = StreamingPeekableIter::new(reader, &[PacketLineRef::Flush], true);

// Read packet lines until a delimiter is encountered
while let Some(line) = line_reader.read_line()? {
    match line {
        PacketLineRef::Data(data) => {
            // Process data
            println!("Received data: {:?}", data);
        },
        PacketLineRef::Flush => {
            println!("Received flush packet");
            break;
        },
        PacketLineRef::Delimiter => {
            println!("Received delimiter packet");
            // Reset to continue reading after delimiter
            line_reader.reset();
        },
        PacketLineRef::ResponseEnd => {
            println!("Response ended");
            break;
        }
    }
}
```

### Writing Packet Lines

```rust
use std::io::BufWriter;
use gix_packetline::Writer;

// Create a writer for outgoing packet lines
let writer = BufWriter::new(socket);
let mut line_writer = Writer::new(writer).text_mode();

// Write data as packet lines
line_writer.write_all(b"Hello, Git!")?;

// Send special packet lines
line_writer.inner_mut().flush_to_write()?;  // Send flush packet
line_writer.inner_mut().delim_to_write()?;  // Send delimiter packet

// Switch to binary mode if needed
line_writer.enable_binary_mode();
line_writer.write_all(&binary_data)?;
```

### Incremental Parsing

```rust
use gix_packetline::decode;

// Partial data received from network
let mut buffer = [0u8; 1024];
let bytes_read = socket.read(&mut buffer)?;
let data = &buffer[..bytes_read];

// Try to parse a packet line
match decode::streaming(data)? {
    decode::Stream::Complete { line, bytes_consumed } => {
        // Process the complete line
        println!("Parsed complete line: {:?}", line);
        
        // Remove consumed bytes from buffer
        // ...
    },
    decode::Stream::Incomplete { bytes_needed } => {
        // Not enough data yet, read more from socket
        println!("Need {} more bytes", bytes_needed);
        // ...
    }
}
```

## Internal Design Considerations

1. **Allocation Efficiency**: The implementation is designed to minimize allocations, which is crucial for handling large repositories with many objects.

2. **Dual IO Support**: The crate supports both blocking and async IO through conditional compilation, avoiding code duplication while providing both interfaces.

3. **Error Handling**: Comprehensive error types provide detailed information about failures, with special handling for ERR packet lines.

4. **Protocol Awareness**: The implementation is aware of Git protocol specifics like side-bands and special packet lines.

## Related Components

The `gix-packetline` crate is a foundational component used by higher-level network and transport crates:

- `gix-protocol`: Builds on packet lines to implement Git protocol commands
- `gix-transport`: Uses packet lines for transport layer communications
- `gix-packetline-blocking`: A blocking-only variant of this crate

## Conclusion

The `gix-packetline` crate provides the foundation for Git's network communication in the gitoxide ecosystem. Its efficient, allocation-conscious implementation of the packet line protocol enables reliable and performant Git operations across both synchronous and asynchronous IO paradigms.