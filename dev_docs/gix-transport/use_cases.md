# gix-transport Use Cases

This document outlines common use cases for the `gix-transport` crate, describing problems, solutions, and example code.

## Intended Audience

The `gix-transport` crate is intended for:

1. **Git Client Developers**: Those building Git client applications (like Git GUI clients, IDEs with Git integration)
2. **Code Hosting Platform Developers**: Developers creating Git server or hosting solutions
3. **CI/CD Tool Creators**: Anyone building tools that need to communicate with Git repositories
4. **Advanced Git Users**: Users creating custom Git workflows or automation tools

## Use Case 1: Cloning a Repository

### Problem

You need to implement a Git clone operation by communicating with a remote repository to fetch its objects and refs.

### Solution

Use the `gix-transport` crate to establish a connection to the remote repository, negotiate capabilities, and fetch the necessary data.

### Example

```rust
use gix_transport::{
    client::{self, Capabilities, Transport},
    Protocol, Service,
};
use std::{error::Error, io::Read};

fn clone_repository(
    url: &str,
    local_path: &std::path::Path,
) -> Result<(), Box<dyn Error>> {
    // Parse the URL and connect
    let url = url.parse()?;
    let mut transport = client::connect(
        url,
        client::non_io_types::connect::Options {
            version: Protocol::V2, // Prefer the most recent protocol
            trace: false,
            ..Default::default()
        },
    )?;

    // Perform handshake to get server capabilities
    let response = transport.handshake(Service::UploadPack, &[])?;
    println!("Connected using protocol: {:?}", response.actual_protocol);
    
    // With Protocol V2, we can use the fetch command
    let mut writer = transport.request(
        client::WriteMode::Text,
        client::MessageKind::Flush,
        false,
    )?;
    
    // Request objects and refs
    writer.write_text("command=fetch\n")?;
    writer.write_text("no-progress\n")?;
    writer.write_text("want-ref refs/heads/main\n")?;
    writer.write_text("ofs-delta\n")?;
    
    // Convert writer to reader for response
    let mut reader = writer.into_read()?;
    
    // Handle the packfile response
    // In a real implementation, you'd:
    // 1. Parse the packfile
    // 2. Extract objects
    // 3. Create refs
    // 4. Set up the working directory
    
    // This is simplified to just read the response
    let mut response_data = Vec::new();
    reader.read_to_end(&mut response_data)?;
    
    println!("Received {} bytes of data", response_data.len());
    
    // Further processing would happen here...
    
    Ok(())
}
```

## Use Case 2: Implementing a Custom Git Transport

### Problem

You need to create a custom Git transport that works over a non-standard protocol or medium (e.g., a proprietary network protocol).

### Solution

Implement the `TransportWithoutIO` and `Transport` traits to create a custom transport that can be used with the rest of the Git stack.

### Example

```rust
use bstr::{BStr, BString};
use gix_transport::{
    client::{
        self, Error, ExtendedBufRead, HandleProgress, MessageKind, ReadlineBufRead, 
        RequestWriter, TransportWithoutIO, WriteMode, Transport as TransportTrait
    },
    packetline::{self, PacketLineRef},
    Protocol, Service,
};
use std::{
    any::Any, borrow::Cow, io::{BufRead, Read}, sync::Arc,
};

// A custom transport implementation for demonstration
struct CustomTransport {
    url: String,
    buffer: Vec<u8>,
    protocol_version: Protocol,
    // Add fields for your custom connection
}

impl CustomTransport {
    fn new(url: &str) -> Self {
        Self {
            url: url.to_string(),
            buffer: Vec::new(),
            protocol_version: Protocol::V2,
            // Initialize your custom connection
        }
    }
    
    // Helper method to simulate sending data over your custom transport
    fn send_data(&mut self, data: &[u8]) -> std::io::Result<()> {
        // In a real implementation, send data through your custom channel
        println!("Sending {} bytes", data.len());
        Ok(())
    }
    
    // Helper method to simulate receiving data
    fn receive_data(&mut self) -> std::io::Result<Vec<u8>> {
        // In a real implementation, receive data from your custom channel
        // Here we'll just return some simulated data for demonstration
        Ok(b"0008done\n".to_vec())
    }
}

// Implement the base transport functionality
impl TransportWithoutIO for CustomTransport {
    fn request(
        &mut self,
        write_mode: WriteMode,
        on_into_read: MessageKind,
        trace: bool,
    ) -> Result<RequestWriter<'_>, Error> {
        // Create a custom writer that will handle the data according to write_mode
        // and eventually send it through your transport
        
        // This is a simplified implementation
        struct CustomWriter<'a> {
            transport: &'a mut CustomTransport,
            data: Vec<u8>,
            write_mode: WriteMode,
            on_into_read: MessageKind,
        }
        
        impl<'a> RequestWriter<'a> for CustomWriter<'a> {
            fn write(&mut self, data: &[u8]) -> Result<(), Error> {
                self.data.extend_from_slice(data);
                Ok(())
            }
            
            fn into_read(mut self: Box<Self>) -> Result<Box<dyn ExtendedBufRead<'a> + 'a>, Error> {
                // Send the accumulated data
                self.transport.send_data(&self.data)?;
                
                // Add final message based on on_into_read
                match self.on_into_read {
                    MessageKind::Flush => self.transport.send_data(b"0000")?,
                    MessageKind::Delimiter => self.transport.send_data(b"0001")?,
                    MessageKind::Text(text) => {
                        let data = packetline::encode(text);
                        self.transport.send_data(&data)?;
                    }
                }
                
                // Receive response data
                let response = self.transport.receive_data()?;
                self.transport.buffer = response;
                
                // Create a reader for the response
                Ok(Box::new(CustomReader {
                    transport: self.transport,
                    position: 0,
                }))
            }
        }
        
        // Create a reader for the response
        struct CustomReader<'a> {
            transport: &'a mut CustomTransport,
            position: usize,
        }
        
        impl<'a> Read for CustomReader<'a> {
            fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
                if self.position >= self.transport.buffer.len() {
                    return Ok(0); // EOF
                }
                
                let available = self.transport.buffer.len() - self.position;
                let count = buf.len().min(available);
                
                buf[..count].copy_from_slice(
                    &self.transport.buffer[self.position..self.position + count]
                );
                self.position += count;
                
                Ok(count)
            }
        }
        
        impl<'a> BufRead for CustomReader<'a> {
            fn fill_buf(&mut self) -> std::io::Result<&[u8]> {
                if self.position >= self.transport.buffer.len() {
                    return Ok(&[]);
                }
                Ok(&self.transport.buffer[self.position..])
            }
            
            fn consume(&mut self, amt: usize) {
                self.position = (self.position + amt).min(self.transport.buffer.len());
            }
        }
        
        // Implement necessary traits for the custom reader
        impl<'a> ReadlineBufRead for CustomReader<'a> {
            fn readline(&mut self) -> Option<std::io::Result<Result<PacketLineRef<'_>, packetline::decode::Error>>> {
                // Implementation of readline for packet line parsing
                // This is simplified for the example
                Some(Ok(Ok(PacketLineRef::Flush)))
            }
            
            fn readline_str(&mut self, line: &mut String) -> std::io::Result<usize> {
                // Implementation for reading text lines
                // Simplified for the example
                Ok(0)
            }
        }
        
        impl<'a, 'b> ExtendedBufRead<'b> for CustomReader<'a> {
            fn set_progress_handler(&mut self, _handle_progress: Option<HandleProgress<'b>>) {
                // Handle progress reporting
            }
            
            fn peek_data_line(&mut self) -> Option<std::io::Result<Result<&[u8], Error>>> {
                // Implementation for peeking at the next data line
                None
            }
            
            fn reset(&mut self, _version: Protocol) {
                // Reset the reader state
                self.position = 0;
            }
            
            fn stopped_at(&self) -> Option<MessageKind> {
                // Return the message kind that caused the reader to stop
                None
            }
        }
        
        // Return the custom writer
        Ok(Box::new(CustomWriter {
            transport: self,
            data: Vec::new(),
            write_mode,
            on_into_read,
        }))
    }
    
    fn to_url(&self) -> Cow<'_, BStr> {
        Cow::Borrowed(self.url.as_str().into())
    }
    
    fn connection_persists_across_multiple_requests(&self) -> bool {
        // Indicate whether your transport maintains a persistent connection
        true
    }
    
    fn configure(&mut self, _config: &dyn Any) -> Result<(), Box<dyn std::error::Error + Send + Sync + 'static>> {
        // Handle any custom configuration
        Ok(())
    }
}

// Implement the full transport trait
impl TransportTrait for CustomTransport {
    fn handshake<'a>(
        &mut self,
        service: Service,
        extra_parameters: &'a [(&'a str, Option<&'a str>)],
    ) -> Result<client::SetServiceResponse<'_>, Error> {
        // Perform the initial handshake to establish the connection
        // and negotiate capabilities
        
        // This would involve:
        // 1. Sending a request to the remote for the specified service
        // 2. Receiving and parsing capabilities
        // 3. Setting up the protocol version
        
        // For demonstration, we'll return a minimal response
        Ok(client::SetServiceResponse {
            actual_protocol: self.protocol_version,
            capabilities: Capabilities::empty(),
            refs: Vec::new(),
        })
    }
}

// Using the custom transport
fn use_custom_transport() -> Result<(), Box<dyn std::error::Error>> {
    let mut transport = CustomTransport::new("custom://my-repo.git");
    
    // Use the transport for Git operations
    let response = transport.handshake(Service::UploadPack, &[])?;
    println!("Connected using protocol: {:?}", response.actual_protocol);
    
    // Further operations...
    
    Ok(())
}
```

## Use Case 3: Fetching Specific Objects from a Repository

### Problem

You need to fetch only specific objects from a remote repository based on certain criteria, such as retrieving only the latest commit and its associated tree.

### Solution

Use the Git transport with a targeted fetch command to retrieve only the objects you need.

### Example

```rust
use gix_transport::{
    client::{self, MessageKind, WriteMode},
    Protocol, Service,
};
use std::io::Read;

// Fetch just the objects for the main branch tip
fn fetch_main_branch_tip(url: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Parse URL and establish connection
    let url = url.parse()?;
    let mut transport = client::connect(
        url,
        client::non_io_types::connect::Options {
            version: Protocol::V2,
            trace: false,
            ..Default::default()
        },
    )?;
    
    // Perform handshake
    let response = transport.handshake(Service::UploadPack, &[])?;
    println!("Using protocol version: {:?}", response.actual_protocol);
    
    // Find the main branch ref if available
    let main_ref = response.refs.iter()
        .find(|r| r.name.as_bstr() == b"refs/heads/main")
        .ok_or("main branch not found")?;
    
    println!("Main branch OID: {}", main_ref.id);
    
    // Set up the fetch command
    let mut writer = transport.request(
        WriteMode::Text,
        MessageKind::Flush,
        false,
    )?;
    
    // For V2 protocol
    if response.actual_protocol == Protocol::V2 {
        writer.write_text("command=fetch\n")?;
        writer.write_text("no-progress\n")?;
        writer.write_text(&format!("want {}\n", main_ref.id))?;
        writer.write_text("done\n")?;
    } else {
        // For V0/V1 protocol
        writer.write_text(&format!("want {}\n", main_ref.id))?;
        writer.write_text("done\n")?;
    }
    
    // Get the response reader
    let mut reader = writer.into_read()?;
    
    // Read the packfile data
    let mut pack_data = Vec::new();
    reader.read_to_end(&mut pack_data)?;
    
    Ok(pack_data)
}
```

## Use Case 4: Pushing Changes to a Remote Repository

### Problem

You need to push local changes (commits, tags, etc.) to a remote repository, which requires using the `git-receive-pack` service.

### Solution

Use the transport to connect with the `ReceivePack` service and send a packfile containing the objects to push.

### Example

```rust
use gix_transport::{
    client::{self, MessageKind, WriteMode},
    Protocol, Service,
};
use std::io::{Read, Write};

fn push_changes(
    url: &str,
    local_ref: &str, 
    remote_ref: &str,
    old_id: &str,
    new_id: &str,
    packfile_data: &[u8],
) -> Result<String, Box<dyn std::error::Error>> {
    // Parse URL and connect
    let url = url.parse()?;
    let mut transport = client::connect(
        url,
        client::non_io_types::connect::Options {
            version: Protocol::V2,
            trace: false,
            ..Default::default()
        },
    )?;
    
    // Perform handshake with ReceivePack service
    let response = transport.handshake(Service::ReceivePack, &[])?;
    println!("Connected using protocol: {:?}", response.actual_protocol);
    
    // Create a writer for the push
    let mut writer = transport.request(
        WriteMode::Binary,
        MessageKind::Flush,
        false,
    )?;
    
    if response.actual_protocol == Protocol::V2 {
        // Protocol V2 push
        writer.write_text("command=push\n")?;
        writer.write_text("no-progress\n")?;
        
        // Send the ref update command
        writer.write_text(&format!("{} {} {}\0 report-status\n", 
            old_id, new_id, remote_ref))?;
            
        // Send the packfile
        writer.write_all(packfile_data)?;
    } else {
        // Protocol V0/V1 push
        // Send the ref update command
        writer.write_text(&format!("{} {} {}\0 report-status\n", 
            old_id, new_id, remote_ref))?;
            
        // Send the packfile
        writer.write_all(packfile_data)?;
    }
    
    // Get the response to check if the push was successful
    let mut reader = writer.into_read()?;
    let mut response = String::new();
    reader.read_to_string(&mut response)?;
    
    Ok(response)
}
```

## Use Case 5: Working with HTTP Authentication

### Problem

You need to connect to a private repository that requires authentication, and you need to handle authentication challenges, credential persistence, and retries.

### Solution

Use the HTTP transport with authentication support, leveraging the identity and credentials functionality.

### Example

```rust
use gix_sec::identity::Account;
use gix_transport::{
    client::{self, http, Transport},
    Protocol, Service,
};

fn connect_with_auth(
    url: &str,
    username: &str,
    password: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Parse the repository URL
    let mut url = url.parse()?;
    
    // Create HTTP options with authentication settings
    let mut http_options = http::Options::default();
    http_options.ssl_verify = true; // Ensure proper SSL verification
    
    // Connect to the repository
    let mut transport = client::connect(
        url,
        client::non_io_types::connect::Options {
            version: Protocol::V2,
            trace: false,
            ..Default::default()
        },
    )?;
    
    // Set identity for authentication
    transport.set_identity(Account {
        username: username.to_string(),
        password: password.to_string(),
    })?;
    
    // Configure HTTP-specific options
    transport.configure(&http_options)?;
    
    // Attempt to connect and handle authentication
    match transport.handshake(Service::UploadPack, &[]) {
        Ok(response) => {
            println!("Successfully authenticated");
            println!("Connected using protocol: {:?}", response.actual_protocol);
            println!("Repository has {} refs", response.refs.len());
        }
        Err(client::Error::AuthenticationRefused(reason)) => {
            println!("Authentication failed: {}", reason);
            // Here you could prompt for new credentials and retry
        }
        Err(err) => return Err(err.into()),
    }
    
    Ok(())
}
```

## Use Case 6: Protocol Feature Detection and Negotiation

### Problem

You need to work with Git servers of varying capabilities and protocol support, requiring feature detection and graceful fallbacks.

### Solution

Use the transport's capability negotiation to detect and adapt to the server's supported features.

### Example

```rust
use gix_transport::{
    client::{self, Capabilities, Transport},
    Protocol, Service,
};

fn negotiate_features(url: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Parse URL and connect
    let url = url.parse()?;
    let mut transport = client::connect(
        url,
        client::non_io_types::connect::Options {
            version: Protocol::V2, // Request newest protocol
            trace: false,
            ..Default::default()
        },
    )?;
    
    // Perform handshake to detect capabilities
    let response = transport.handshake(Service::UploadPack, &[])?;
    println!("Negotiated protocol version: {:?}", response.actual_protocol);
    
    // Check for specific capabilities
    let caps = &response.capabilities;
    
    // For Protocol V2
    if response.actual_protocol == Protocol::V2 {
        if caps.supports_v2_command("fetch") {
            println!("Server supports V2 fetch command");
        }
        
        if caps.supports_v2_command("ls-refs") {
            println!("Server supports V2 ls-refs command");
        }
        
        // Check for object format capability
        if let Some(formats) = caps.supports_v2("object-format") {
            println!("Server supports object formats: {}", formats);
        }
    } 
    // For Protocol V0/V1
    else {
        if caps.supports_v1("multi_ack_detailed") {
            println!("Server supports detailed multi-ack");
        }
        
        if caps.supports_v1("thin-pack") {
            println!("Server supports thin packs");
        }
        
        if caps.supports_v1("ofs-delta") {
            println!("Server supports offset deltas");
        }
    }
    
    // Adapt your strategy based on capabilities
    // For example, using different fetch strategies based on available features
    
    Ok(())
}
```

## Use Case 7: Working with Local Repositories via File Protocol

### Problem

You need to interact with a local Git repository directly, without using a networked transport.

### Solution

Use the file transport to access local repositories efficiently.

### Example

```rust
use gix_transport::{
    client::{self, file, Transport},
    Protocol, Service,
};
use std::path::Path;

fn access_local_repo(
    repo_path: &Path,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Connect to the local repository
    let mut transport = file::connect(
        repo_path,
        Protocol::V2,
        false, // Don't trace
    )?;
    
    // Handshake with the repository
    let response = transport.handshake(Service::UploadPack, &[])?;
    println!("Connected using protocol: {:?}", response.actual_protocol);
    
    // Collect reference names
    let ref_names = response.refs
        .iter()
        .map(|r| String::from_utf8_lossy(&r.name).to_string())
        .collect::<Vec<_>>();
    
    // We could now use the transport for further operations
    // such as fetching objects
    
    Ok(ref_names)
}
```