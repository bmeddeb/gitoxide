# gix-packetline Use Cases

This document provides practical examples of using the `gix-packetline` crate for various Git protocol operations.

## Basic Packet Line Reading

**Problem**: You need to read Git protocol data from a stream (such as a network connection) and process it packet by packet.

**Solution**: Use the `StreamingPeekableIter` to read and parse packet lines from the stream.

```rust
use std::io::BufReader;
use gix_packetline::{PacketLineRef, StreamingPeekableIter};

fn process_git_response(stream: impl std::io::Read) -> std::io::Result<()> {
    // Create a reader with Flush as a delimiter
    let mut line_reader = StreamingPeekableIter::new(
        BufReader::new(stream),
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

## Writing Git Protocol Commands

**Problem**: You need to send Git protocol commands to a server, properly formatted as packet lines.

**Solution**: Use the `Writer` to format and send Git commands.

```rust
use std::io::BufWriter;
use gix_packetline::Writer;

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
    crate::encode::flush_to_write(writer.inner_mut())?;
    writer.flush()?;
    
    Ok(())
}

// Example usage:
// send_git_command(socket, "git-upload-pack", &["/path/to/repo.git"])
```

## Working with Side-band Protocol

**Problem**: You need to handle multiplexed communication using Git's side-band protocol, which combines data, progress, and error messages.

**Solution**: Use the side-band functionality to separate different channels.

```rust
use std::io::BufReader;
use gix_packetline::{PacketLineRef, StreamingPeekableIter, BandRef, Channel};
use gix_packetline::read::WithSidebands;

fn process_sideband_data(stream: impl std::io::Read) -> std::io::Result<()> {
    let line_reader = StreamingPeekableIter::new(
        BufReader::new(stream),
        &[PacketLineRef::Flush],
        true
    );
    
    // Create a sideband reader
    let mut sideband_reader = WithSidebands::new(line_reader);
    
    // Process all bands
    while let Some(band) = sideband_reader.read_band()? {
        match band {
            BandRef::Data(data) => {
                println!("Received data: {:?}", data);
                // Process the actual data...
            },
            BandRef::Progress(progress) => {
                println!("Progress: {:?}", progress);
                // Update progress display...
            },
            BandRef::Error(error) => {
                eprintln!("Error: {:?}", error);
                // Handle error...
                return Err(std::io::Error::new(
                    std::io::ErrorKind::Other,
                    format!("Server error: {:?}", error)
                ));
            }
        }
    }
    
    Ok(())
}
```

## Writing Side-band Messages

**Problem**: You need to send data with progress information using the side-band protocol.

**Solution**: Use the encoding functions to write data to different side-band channels.

```rust
use std::io::BufWriter;
use gix_packetline::{Channel, Writer};

fn send_with_progress(
    stream: impl std::io::Write,
    data: &[u8],
    progress_messages: &[&str]
) -> std::io::Result<()> {
    let mut writer = Writer::new(BufWriter::new(stream)).binary_mode();
    
    // Send data in chunks with progress updates
    let chunk_size = 1024;
    let chunks = data.chunks(chunk_size);
    let total_chunks = (data.len() + chunk_size - 1) / chunk_size;
    
    for (i, chunk) in chunks.enumerate() {
        // Send a chunk of actual data on the data channel
        let mut data_packet = Vec::with_capacity(chunk.len() + 1);
        data_packet.push(Channel::Data as u8);
        data_packet.extend_from_slice(chunk);
        writer.write_all(&data_packet)?;
        
        // Send progress update if available
        if i < progress_messages.len() {
            let mut progress_packet = Vec::new();
            progress_packet.push(Channel::Progress as u8);
            progress_packet.extend_from_slice(progress_messages[i].as_bytes());
            writer.write_all(&progress_packet)?;
        } else {
            // Generate default progress message
            let progress = format!("Processing chunk {}/{}", i + 1, total_chunks);
            let mut progress_packet = Vec::new();
            progress_packet.push(Channel::Progress as u8);
            progress_packet.extend_from_slice(progress.as_bytes());
            writer.write_all(&progress_packet)?;
        }
    }
    
    // Send flush to indicate completion
    crate::encode::flush_to_write(writer.inner_mut())?;
    writer.flush()?;
    
    Ok(())
}
```

## Incremental Packet Line Parsing

**Problem**: You're working with limited resources and need to parse packet lines incrementally from a stream without buffering everything.

**Solution**: Use the streaming decoder to parse packet lines as data arrives.

```rust
use gix_packetline::decode::{self, Stream};

fn incremental_parse(mut socket: impl std::io::Read) -> std::io::Result<Vec<Vec<u8>>> {
    let mut buffer = Vec::new();
    let mut collected_lines = Vec::new();
    let mut unparsed_data = Vec::new();
    
    loop {
        // Read some data from the socket
        buffer.resize(1024, 0);
        let bytes_read = socket.read(&mut buffer)?;
        if bytes_read == 0 {
            break; // End of stream
        }
        
        // Append new data to unparsed buffer
        unparsed_data.extend_from_slice(&buffer[..bytes_read]);
        
        // Try to parse as many complete packet lines as possible
        let mut start = 0;
        while start < unparsed_data.len() {
            match decode::streaming(&unparsed_data[start..]) {
                Ok(Stream::Complete { line, bytes_consumed }) => {
                    // Process the complete line
                    if let gix_packetline::PacketLineRef::Data(data) = line {
                        collected_lines.push(data.to_vec());
                    }
                    
                    // Move past this packet line
                    start += bytes_consumed;
                },
                Ok(Stream::Incomplete { bytes_needed }) => {
                    // Not enough data yet, need to read more
                    break;
                },
                Err(e) => {
                    return Err(std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        format!("Failed to parse packet line: {}", e)
                    ));
                }
            }
        }
        
        // Remove consumed data from the unparsed buffer
        if start > 0 {
            unparsed_data.drain(0..start);
        }
    }
    
    Ok(collected_lines)
}
```

## Handling Interleaved Binary and Text Data

**Problem**: You need to handle a Git protocol that mixes both binary and text data in the same stream.

**Solution**: Use the Writer's ability to switch between binary and text modes.

```rust
use std::io::BufWriter;
use gix_packetline::Writer;

fn send_mixed_data(
    stream: impl std::io::Write,
    text_data: &[&str],
    binary_data: &[&[u8]]
) -> std::io::Result<()> {
    let mut writer = Writer::new(BufWriter::new(stream));
    
    // Interleave text and binary data
    for (i, (text, binary)) in text_data.iter().zip(binary_data.iter()).enumerate() {
        // Send text with automatic newline handling
        writer.enable_text_mode();
        writer.write_all(text.as_bytes())?;
        
        // Send binary data as-is
        writer.enable_binary_mode();
        writer.write_all(binary)?;
        
        // Add a delimiter between sets
        if i < text_data.len() - 1 {
            crate::encode::delim_to_write(writer.inner_mut())?;
        }
    }
    
    // End with a flush
    crate::encode::flush_to_write(writer.inner_mut())?;
    writer.flush()?;
    
    Ok(())
}
```

## Error Handling and Recovery

**Problem**: You need to handle packet line protocol errors gracefully with proper recovery.

**Solution**: Use the error handling mechanisms and the ability to reset the reader state.

```rust
use std::io::BufReader;
use gix_packetline::{PacketLineRef, StreamingPeekableIter};
use gix_packetline::read::Error as PacketLineError;

fn robust_protocol_handler(stream: impl std::io::Read) -> std::io::Result<()> {
    let mut line_reader = StreamingPeekableIter::new(
        BufReader::new(stream),
        &[PacketLineRef::Flush, PacketLineRef::ResponseEnd],
        true
    );
    
    // Enable failing on ERR lines
    line_reader.fail_on_err_lines(true);
    
    // Process data with error handling
    loop {
        match line_reader.read_line() {
            Ok(Some(line)) => {
                match line {
                    PacketLineRef::Data(data) => {
                        println!("Received data: {:?}", data);
                    },
                    PacketLineRef::Flush => {
                        println!("End of section");
                        
                        // Check if we stopped due to an error
                        if let Some(stop_reason) = line_reader.stopped_at() {
                            println!("Stopped due to: {:?}", stop_reason);
                        }
                        
                        // Reset to continue with the next section
                        line_reader.reset();
                    },
                    PacketLineRef::ResponseEnd => {
                        println!("Response complete");
                        break;
                    },
                    _ => {}
                }
            },
            Ok(None) => {
                // End of stream or stopped due to error
                if let Some(stop_reason) = line_reader.stopped_at() {
                    println!("Stopped due to: {:?}", stop_reason);
                    
                    // We can choose to reset and continue
                    line_reader.reset();
                } else {
                    // Normal end of stream
                    break;
                }
            },
            Err(e) => {
                if let Some(err) = e.downcast_ref::<PacketLineError>() {
                    eprintln!("Protocol error: {}", err);
                    
                    // We can reset and try to continue
                    line_reader.reset();
                } else {
                    // IO error or other issue, can't continue
                    return Err(e);
                }
            }
        }
    }
    
    Ok(())
}
```

These use cases demonstrate the flexibility and efficiency of the `gix-packetline` crate in handling the Git wire protocol for various client and server operations. The crate's design allows for both high-level, convenient API usage as well as fine-grained control over packet line parsing and generation.