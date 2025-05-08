# gix-packetline-blocking Use Cases

This document provides practical examples of using the `gix-packetline-blocking` crate for various Git protocol operations in blocking IO contexts.

## Git Protocol Communication

**Problem**: You need to implement a Git client that communicates with a Git server using the Git protocol.

**Solution**: Use the `gix-packetline-blocking` crate to handle the low-level packet line format.

```rust
use std::io::{BufReader, BufWriter, Read, Write};
use std::net::TcpStream;
use gix_packetline_blocking::{encode, PacketLineRef, StreamingPeekableIter, Writer};

fn git_clone_request(repo_url: &str, reference: &str) -> std::io::Result<Vec<u8>> {
    // Connect to Git server
    let stream = TcpStream::connect("git.example.com:9418")?;
    let reader = stream.try_clone()?;
    
    // Set up writer for sending commands
    let mut writer = Writer::new(BufWriter::new(stream)).text_mode();
    
    // Send initial request
    writer.write_all(format!("git-upload-pack {}", repo_url).as_bytes())?;
    encode::flush_to_write(writer.inner_mut())?;
    
    // Send want command for specific reference
    writer.write_all(format!("want {}", reference).as_bytes())?;
    encode::flush_to_write(writer.inner_mut())?;
    
    // Set up reader for parsing response
    let mut line_reader = StreamingPeekableIter::new(
        BufReader::new(reader),
        &[PacketLineRef::Flush],
        true
    );
    
    // Process response
    let mut response_data = Vec::new();
    while let Some(line_result) = line_reader.read_line() {
        match line_result? {
            PacketLineRef::Data(data) => {
                response_data.extend_from_slice(data);
            },
            PacketLineRef::Flush => {
                break; // End of response
            },
            _ => {}
        }
    }
    
    Ok(response_data)
}
```

## Custom Git Server Implementation

**Problem**: You need to implement a custom Git server that responds to Git protocol requests.

**Solution**: Use `gix-packetline-blocking` to parse incoming commands and respond with properly formatted packet lines.

```rust
use std::io::{BufReader, BufWriter, Read, Write};
use std::net::{TcpListener, TcpStream};
use gix_packetline_blocking::{encode, PacketLineRef, StreamingPeekableIter, Writer};

fn handle_git_client(mut stream: TcpStream) -> std::io::Result<()> {
    let reader = stream.try_clone()?;
    
    // Set up packet line reader
    let mut line_reader = StreamingPeekableIter::new(
        BufReader::new(reader),
        &[PacketLineRef::Flush],
        true
    );
    
    // Read the command
    let command = if let Some(Ok(Ok(PacketLineRef::Data(cmd)))) = line_reader.read_line() {
        String::from_utf8_lossy(cmd).to_string()
    } else {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "Invalid Git protocol command"
        ));
    };
    
    // Expect a flush
    match line_reader.read_line() {
        Some(Ok(Ok(PacketLineRef::Flush))) => {},
        _ => return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "Expected flush after command"
        )),
    }
    
    // Parse the command (e.g., git-upload-pack /path/to/repo.git)
    let parts: Vec<&str> = command.split_whitespace().collect();
    if parts.len() < 2 || parts[0] != "git-upload-pack" {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "Unsupported command"
        ));
    }
    
    // Repository path
    let repo_path = parts[1];
    
    // Set up response writer
    let mut writer = Writer::new(BufWriter::new(stream));
    
    // Send reference advertisement
    let references = ["refs/heads/main abcdef1234567890", 
                      "refs/heads/develop fedcba0987654321"];
    
    for reference in &references {
        writer.enable_text_mode();
        writer.write_all(reference.as_bytes())?;
    }
    
    // End references with flush
    encode::flush_to_write(writer.inner_mut())?;
    writer.flush()?;
    
    Ok(())
}

fn run_git_server() -> std::io::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:9418")?;
    
    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                std::thread::spawn(move || {
                    if let Err(e) = handle_git_client(stream) {
                        eprintln!("Error handling client: {}", e);
                    }
                });
            },
            Err(e) => {
                eprintln!("Error accepting connection: {}", e);
            }
        }
    }
    
    Ok(())
}
```

## Progress Reporting during Git Operations

**Problem**: You need to implement a Git clone operation with progress reporting for end users.

**Solution**: Use the side-band protocol support to separate actual data from progress information.

```rust
use std::io::{BufReader, BufWriter, Read, Write};
use gix_packetline_blocking::{PacketLineRef, StreamingPeekableIter, read::ProgressAction};

fn clone_with_progress(repo_url: &str, dest_path: &str) -> std::io::Result<()> {
    // Connect to Git server and initiate clone (simplified)
    let stream = establish_connection(repo_url)?;
    let reader = BufReader::new(stream);
    
    // Create packet line reader
    let mut line_reader = StreamingPeekableIter::new(
        reader,
        &[PacketLineRef::Flush],
        true
    );
    
    // Set up progress handling
    let mut with_sidebands = line_reader.as_read_with_sidebands(|is_error, text| {
        if is_error {
            eprintln!("Error: {}", String::from_utf8_lossy(text));
            ProgressAction::Interrupt // Stop on error
        } else {
            println!("Progress: {}", String::from_utf8_lossy(text));
            ProgressAction::Continue // Continue on progress messages
        }
    });
    
    // Process pack data
    let mut pack_data = Vec::new();
    with_sidebands.read_to_end(&mut pack_data)?;
    
    // Write pack data to appropriate location in the repository
    std::fs::write(format!("{}/objects/pack/pack-received.pack", dest_path), &pack_data)?;
    
    // In a real implementation, we would then process the pack file
    
    println!("Clone completed successfully");
    Ok(())
}

// Helper function to establish connection (simplified)
fn establish_connection(repo_url: &str) -> std::io::Result<impl Read> {
    // In a real implementation, this would connect to the Git server
    // and send the initial negotiation
    
    // For demonstration purposes, returning a mock stream
    Ok(std::io::Cursor::new(vec![
        // Sample packet lines simulating a Git server response
        // First packet: data with side-band marker (0x01 = data channel)
        0x00, 0x10, 0x01, b'p', b'a', b'c', b'k', b' ', b'd', b'a', b't', b'a', b'\n',
        // Second packet: progress with side-band marker (0x02 = progress channel)
        0x00, 0x19, 0x02, b'R', b'e', b'c', b'e', b'i', b'v', b'i', b'n', b'g', b' ', 
        b'o', b'b', b'j', b'e', b'c', b't', b's', b'\n',
        // Flush packet
        0x00, 0x00
    ]))
}
```

## Error Handling in Git Protocol

**Problem**: You need to handle protocol errors gracefully when interacting with a Git server.

**Solution**: Use the error detection and handling features of `gix-packetline-blocking`.

```rust
use std::io::{BufReader, BufWriter, Read, Write};
use gix_packetline_blocking::{PacketLineRef, StreamingPeekableIter};

fn robust_git_request(server: impl Read + Write, command: &str) -> std::io::Result<Vec<u8>> {
    let writer_stream = server.try_clone()?;
    let mut writer = BufWriter::new(writer_stream);
    
    // Send command as packet line
    let packet = format!("{:04x}{}", command.len() + 4, command);
    writer.write_all(packet.as_bytes())?;
    writer.write_all(b"0000")?; // Flush
    writer.flush()?;
    
    // Set up reader with error detection
    let mut line_reader = StreamingPeekableIter::new(
        BufReader::new(server),
        &[PacketLineRef::Flush],
        true
    );
    
    // Enable ERR packet detection
    line_reader.fail_on_err_lines(true);
    
    // Process response with error handling
    let mut response = Vec::new();
    let result = loop {
        match line_reader.read_line() {
            Some(Ok(Ok(line))) => {
                match line {
                    PacketLineRef::Data(data) => {
                        response.extend_from_slice(data);
                    },
                    PacketLineRef::Flush => {
                        break Ok(response);
                    },
                    _ => {}
                }
            },
            Some(Err(e)) => {
                // IO error
                break Err(e);
            },
            Some(Ok(Err(e))) => {
                // Decode error
                break Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidData,
                    format!("Decode error: {}", e)
                ));
            },
            None => {
                // Check if we stopped due to an error packet
                if let Some(stopped_at) = line_reader.stopped_at() {
                    // For ERR packets, we get None with stopped_at() providing the cause
                    break Err(std::io::Error::new(
                        std::io::ErrorKind::Other,
                        format!("Protocol error: {:?}", stopped_at)
                    ));
                } else {
                    // Normal EOF
                    break Ok(response);
                }
            }
        }
    };
    
    result
}
```

## Building a Custom Git Transport

**Problem**: You need to implement a custom Git transport protocol (e.g., over a non-TCP channel).

**Solution**: Use `gix-packetline-blocking` as the foundation for your custom transport.

```rust
use std::io::{self, Read, Write};
use gix_packetline_blocking::{encode, PacketLineRef, StreamingPeekableIter, Writer};

// Custom transport example - could be over shared memory, unix socket, etc.
struct CustomTransport {
    reader: Box<dyn Read>,
    writer: Box<dyn Write>,
}

impl CustomTransport {
    fn new(reader: impl Read + 'static, writer: impl Write + 'static) -> Self {
        Self {
            reader: Box::new(reader),
            writer: Box::new(writer),
        }
    }
    
    // Send a Git command
    fn send_command(&mut self, command: &str, args: &[&str]) -> io::Result<()> {
        let mut writer = Writer::new(&mut self.writer).text_mode();
        
        // Write command
        writer.write_all(command.as_bytes())?;
        
        // Write args
        for arg in args {
            writer.write_all(arg.as_bytes())?;
        }
        
        // Send flush
        encode::flush_to_write(writer.inner_mut())?;
        writer.flush()?;
        
        Ok(())
    }
    
    // Receive all packet lines until a flush
    fn receive_response(&mut self) -> io::Result<Vec<Vec<u8>>> {
        let mut line_reader = StreamingPeekableIter::new(
            &mut self.reader,
            &[PacketLineRef::Flush],
            true
        );
        
        let mut response = Vec::new();
        while let Some(line_result) = line_reader.read_line() {
            match line_result? {
                PacketLineRef::Data(data) => {
                    response.push(data.to_vec());
                },
                PacketLineRef::Flush => {
                    break;
                },
                _ => {}
            }
        }
        
        Ok(response)
    }
}

// Example usage
fn git_over_custom_transport() -> io::Result<()> {
    // In a real implementation, these would be custom channels
    let (reader_pipe, mut writer_pipe) = os_pipe::pipe()?;
    let (reader_pipe2, mut writer_pipe2) = os_pipe::pipe()?;
    
    // Simulate server in a thread
    std::thread::spawn(move || {
        // Read the command (simplified server)
        let mut buffer = [0u8; 1024];
        let n = reader_pipe.read(&mut buffer).unwrap();
        
        // Send a response
        let response = b"001fref: refs/heads/main deadbeef";
        writer_pipe2.write_all(response).unwrap();
        writer_pipe2.write_all(b"0000").unwrap(); // Flush
    });
    
    // Client uses the custom transport
    let mut transport = CustomTransport::new(reader_pipe2, writer_pipe);
    
    // Send a command
    transport.send_command("git-upload-pack", &[" /repo.git"])?;
    
    // Receive the response
    let response = transport.receive_response()?;
    
    for packet in response {
        println!("Received: {}", String::from_utf8_lossy(&packet));
    }
    
    Ok(())
}
```

## Implementing a Smart Git HTTP Server

**Problem**: You need to implement a Smart HTTP server for Git that handles both the request and response in the Git protocol format.

**Solution**: Use `gix-packetline-blocking` to parse and generate Git protocol messages in your HTTP handler.

```rust
use std::io::{Cursor, Read};
use gix_packetline_blocking::{encode, PacketLineRef, StreamingPeekableIter, Writer};

// Simplified HTTP handler function for a Git smart HTTP server
fn handle_git_http_request(request_body: Vec<u8>, repo_path: &str) -> Vec<u8> {
    // Parse the incoming Git protocol request from HTTP body
    let mut reader = StreamingPeekableIter::new(
        Cursor::new(request_body),
        &[PacketLineRef::Flush],
        true
    );
    
    // Read the command (e.g., git-upload-pack)
    let command = match reader.read_line() {
        Some(Ok(Ok(PacketLineRef::Data(cmd)))) => {
            String::from_utf8_lossy(cmd).to_string()
        },
        _ => {
            // Invalid request
            return build_error_response("Invalid Git protocol request");
        }
    };
    
    // Process command based on Git service
    let mut response = Vec::new();
    let mut writer = Writer::new(Cursor::new(&mut response));
    
    match command.as_str() {
        "git-upload-pack" => {
            // Server would open the repository and list refs
            writer.enable_text_mode();
            writer.write_all(b"refs/heads/main abcdef1234567890").unwrap();
            writer.write_all(b"refs/heads/develop 0987654321abcdef").unwrap();
            encode::flush_to_write(writer.inner_mut()).unwrap();
        },
        "git-receive-pack" => {
            // Handle push operation
            writer.enable_text_mode();
            writer.write_all(b"unpack ok").unwrap();
            encode::flush_to_write(writer.inner_mut()).unwrap();
        },
        _ => {
            return build_error_response(&format!("Unsupported Git service: {}", command));
        }
    }
    
    response
}

// Helper function to build an error response in Git protocol format
fn build_error_response(error_message: &str) -> Vec<u8> {
    let mut response = Vec::new();
    let mut writer = Writer::new(Cursor::new(&mut response));
    
    // Write error as ERR packet
    encode::error_to_write(error_message.as_bytes(), writer.inner_mut()).unwrap();
    encode::flush_to_write(writer.inner_mut()).unwrap();
    
    response
}
```

## Incremental Packet Line Processing

**Problem**: You need to handle large Git protocol responses without loading everything into memory at once.

**Solution**: Process packet lines incrementally, handling each one as it arrives.

```rust
use std::io::{BufReader, Read};
use gix_packetline_blocking::{PacketLineRef, StreamingPeekableIter};

fn process_large_packfile(stream: impl Read, process_chunk: impl FnMut(&[u8])) -> std::io::Result<()> {
    let mut line_reader = StreamingPeekableIter::new(
        BufReader::new(stream),
        &[PacketLineRef::Flush],
        true
    );
    
    // Set up progressive data handling
    let mut processor = process_chunk;
    let mut packet_count = 0;
    
    // Process each packet as it arrives
    while let Some(line_result) = line_reader.read_line() {
        match line_result? {
            PacketLineRef::Data(data) => {
                // Process this chunk without storing the whole data
                processor(data);
                packet_count += 1;
                
                // Periodically report progress
                if packet_count % 100 == 0 {
                    println!("Processed {} packets", packet_count);
                }
            },
            PacketLineRef::Flush => {
                println!("End of data (flush packet)");
                break;
            },
            PacketLineRef::Delimiter => {
                println!("Section delimiter");
                // Reset to continue with next section
                line_reader.reset();
            },
            PacketLineRef::ResponseEnd => {
                println!("Response complete");
                break;
            }
        }
    }
    
    println!("Total packets processed: {}", packet_count);
    Ok(())
}

// Example usage:
fn incremental_clone() -> std::io::Result<()> {
    // In a real implementation, this would be a connection to a Git server
    let mock_stream = Cursor::new(vec![
        // Pack data packets (simplified)
        0x00, 0x10, b'P', b'A', b'C', b'K', b' ', b'D', b'A', b'T', b'A', b' ', b'1',
        0x00, 0x10, b'P', b'A', b'C', b'K', b' ', b'D', b'A', b'T', b'A', b' ', b'2',
        0x00, 0x10, b'P', b'A', b'C', b'K', b' ', b'D', b'A', b'T', b'A', b' ', b'3',
        // Flush packet
        0x00, 0x00
    ]);
    
    // Process the stream incrementally
    let mut pack_file = std::fs::File::create("incremental-pack.pack")?;
    process_large_packfile(mock_stream, |chunk| {
        // In a real implementation, we'd write to the packfile
        println!("Processing chunk: {:?}", chunk);
        // pack_file.write_all(chunk).unwrap();
    })?;
    
    Ok(())
}
```

These use cases demonstrate how `gix-packetline-blocking` can be utilized for various Git protocol operations in a synchronous context. The crate provides the foundation for implementing Git clients, servers, and custom transport mechanisms with efficient packet line processing.