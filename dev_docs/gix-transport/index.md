# gix-transport

## Overview

The `gix-transport` crate implements the Git transport layer, providing abstractions for communicating with remote Git repositories over various protocols. It supports all standard Git transport protocols (git, http, https, ssh, file) and handles protocol negotiation, connection establishment, and data transfer.

This crate is a key component in the networking stack of gitoxide, enabling operations like clone, fetch, and push by providing the underlying transport mechanisms needed to communicate with remote repositories. It implements all versions of the Git protocol (v0, v1, v2) and takes care of the complexity of protocol negotiation, authentication, and request/response handling.

## Architecture

The `gix-transport` crate follows a modular architecture with a clear separation between:

1. **Protocols**: Supports different Git protocols through specific implementations
   - `file`: Direct access to local repositories
   - `git`: TCP-based Git protocol
   - `ssh`: SSH-based Git protocol
   - `http`/`https`: HTTP-based Git protocol

2. **Transport Modes**:
   - Blocking transport: Synchronous implementation for typical usage
   - Async transport: Asynchronous implementation for non-blocking operations

3. **Protocol Versions**:
   - V0: Legacy protocol without capabilities
   - V1: The original stateful protocol
   - V2: The modern command-based stateless protocol

The crate is designed with a focus on:
- **Abstractions**: Common interfaces for all transports through traits
- **Configurability**: Extensive options for customizing transport behavior
- **Error Handling**: Comprehensive error types that indicate whether retries are viable
- **Feature Flags**: Granular control over included functionality

The architecture uses a trait-based approach where the `Transport` trait provides a common interface for all transport implementations, allowing higher-level code to work with any transport protocol transparently.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `client::Transport` | Main transport trait implementation | Provides a uniform interface for all transport types |
| `client::http::Transport<H>` | HTTP transport implementation | Handles HTTP/HTTPS protocol communication |
| `client::file::Transport` | File transport implementation | Access to local repositories |
| `client::ssh::Transport` | SSH transport implementation | Access to remote repositories via SSH |
| `client::git::Transport` | Git daemon transport implementation | Access to Git daemon via TCP |
| `client::RequestWriter` | Writer for sending data | Creates requests to the remote server |
| `client::Capabilities` | Repository capabilities | Tracks what the server can do |
| `client::http::Options` | HTTP-specific options | Configure HTTP transport settings |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `client::TransportWithoutIO` | Base transport functionality without I/O | `Transport` and other concrete transport implementations |
| `client::Transport` | Full transport interface | Concrete transport implementations |
| `client::http::Http` | HTTP client interface | `curl::Curl`, `reqwest::Remote` |
| `IsSpuriousError` | Error classification for retries | Various error types |
| `client::ExtendedBufRead` | Enhanced buffer reading | Buffer readers in both async and blocking modes |
| `client::HandleProgress` | Progress reporting | Used for reporting transfer progress |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `client::connect` | Connect to a repository URL | `fn connect<Url, E>(url: Url, options: Options) -> Result<Box<dyn Transport + Send>, Error>` |
| `client::http::connect` | Connect via HTTP/HTTPS | `fn connect(url: Url, desired_version: Protocol, trace: bool) -> Transport<Impl>` |
| `client::file::connect` | Connect to local repository | `fn connect<P>(path: P, desired_version: Protocol, trace: bool) -> Result<Transport, Error>` |
| `client::ssh::connect` | Connect via SSH | `fn connect(url: Url, desired_version: Protocol, options: Options, trace: bool) -> Result<Transport, Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Protocol` | Git protocol version | `V0`, `V1`, `V2` |
| `Service` | Git service to invoke | `UploadPack`, `ReceivePack` |
| `client::WriteMode` | How to interpret writes | `Binary`, `Text`, `OneLFTerminatedLinePerWriteCall` |
| `client::MessageKind` | Message type for transport | `Flush`, `Text`, `Delimiter` |
| `client::Error` | Transport error types | Various error variants |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-command` | Execute Git commands for local repositories |
| `gix-features` | Feature flags and utilities |
| `gix-url` | Parse and manipulate Git URLs |
| `gix-sec` | Security and authentication |
| `gix-packetline` | Git protocol packet line handling |
| `gix-credentials` | Credential handling (optional) |
| `gix-quote` | Command line argument quoting |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Binary string handling |
| `thiserror` | Error definition |
| `async-trait` | Async trait support (with `async-client` feature) |
| `futures-io` | Async I/O traits (with `async-client` feature) |
| `futures-lite` | Async utilities (with `async-client` feature) |
| `pin-project-lite` | Pinning utilities (with `async-client` feature) |
| `base64` | Base64 encoding (with `http-client` feature) |
| `curl` | HTTP client (with `http-client-curl` feature) |
| `reqwest` | HTTP client (with `http-client-reqwest` feature) |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `blocking-client` | Enables blocking implementations of Git transports | `gix-packetline/blocking-io` |
| `http-client` | Adds support for HTTP/HTTPS transports | `base64`, `gix-features/io-pipe`, `blocking-client`, `gix-credentials` |
| `http-client-curl` | Uses libcurl for HTTP transport | `curl`, `http-client` |
| `http-client-curl-rust-tls` | Uses rustls with curl for HTTPS | `http-client-curl`, `curl/rustls` |
| `http-client-reqwest` | Uses reqwest for HTTP transport | `reqwest`, `http-client` |
| `http-client-reqwest-rust-tls` | Uses rustls with reqwest for HTTPS | `http-client-reqwest`, `reqwest/rustls-tls` |
| `http-client-reqwest-native-tls` | Uses native-tls with reqwest for HTTPS | `http-client-reqwest`, `reqwest/default-tls` |
| `async-client` | Enables async implementations of Git transports | `gix-packetline/async-io`, `async-trait`, `futures-lite`, `futures-io`, `pin-project-lite` |
| `serde` | Enables serialization/deserialization | `serde` |

## Examples

```rust
// Connect to a git repository via HTTPS
use std::error::Error;
use gix_transport::{Protocol, client::{self, Transport}};
use gix_url::Url;

fn main() -> Result<(), Box<dyn Error>> {
    // Parse a Git URL
    let url = "https://github.com/GitoxideLabs/gitoxide.git".parse::<Url>()?;
    
    // Create a connection with default options
    let options = client::non_io_types::connect::Options {
        version: Protocol::V2,  // Use Git protocol v2
        trace: false,           // Don't trace protocol messages
        ..Default::default()
    };
    
    // Connect to the repository
    let mut transport = client::connect(url, options)?;
    
    // Perform the handshake to initialize the connection 
    // and get capabilities
    let response = transport.handshake(
        gix_transport::Service::UploadPack,
        &[]
    )?;
    
    println!("Connected using protocol version: {:?}", response.actual_protocol);
    println!("Server capabilities: {:#?}", response.capabilities);
    
    // We could now use the transport for fetch/clone operations
    // ...
    
    Ok(())
}
```

```rust
// Example: Using the transport to list references in a repository
use gix_transport::{client::{self, MessageKind, Transport, WriteMode}, Protocol, Service};
use std::io::Read;

fn list_refs(url: &str) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Parse URL and connect
    let url = url.parse()?;
    let mut transport = client::connect(
        url, 
        client::non_io_types::connect::Options {
            version: Protocol::V2,
            ..Default::default()
        }
    )?;
    
    // Initialize connection
    transport.handshake(Service::UploadPack, &[])?;
    
    // With protocol V2, we can use the ls-refs command
    let mut writer = transport.request(
        WriteMode::Text,
        MessageKind::Flush,
        false,
    )?;
    
    // Write the command
    writer.write_text("command=ls-refs\n")?;
    writer.write_text("peel\n")?;
    writer.write_text("symrefs\n")?;
    
    // Finalize request and get the response
    let mut reader = writer.into_read()?;
    
    // Read the response
    let mut response = String::new();
    reader.read_to_string(&mut response)?;
    
    // Parse references from the response
    // In a real implementation, you would parse the response into a structured format
    Ok(response.lines().map(String::from).collect())
}
```

## Implementation Details

### Protocol Version Negotiation

The transport layer automatically handles Git protocol version negotiation:

1. **Initial Request**: The client requests the highest supported protocol version.
2. **Server Response**: The server indicates its supported version.
3. **Version Selection**: The transport adjusts to use the highest mutually supported version.

This process allows seamless communication with servers of varying protocol support, from old Git servers supporting only v0 to modern servers with v2 support.

### Authentication

The transport layer supports various authentication methods depending on the protocol:

1. **HTTP/HTTPS**:
   - Basic authentication using username/password
   - OAuth tokens
   - Custom authentication headers

2. **SSH**:
   - SSH keys (via system SSH agent)
   - Password authentication

3. **Git Protocol**:
   - Usually unauthenticated

Authentication failures are handled with informative errors, allowing for credential updates or retry logic.

### HTTP Transport Options

The HTTP transport implementation provides extensive configuration options:

- **SSL/TLS Settings**: Version ranges, certificate verification, CA certificates
- **Redirect Handling**: Control how redirects are followed
- **Proxy Support**: Custom proxies with authentication
- **Performance Settings**: Timeouts, low-speed limits
- **Custom Headers**: Add custom headers to requests

These options allow fine-tuning the HTTP transport for different environments and security requirements.

### Packet Line Handling

Git protocol communication is based on packet lines - length-prefixed data chunks. The transport layer abstracts this complexity by:

1. Using the `gix-packetline` crate for encoding/decoding
2. Handling different line termination styles
3. Supporting both binary and text data
4. Providing progress information during long transfers

### Error Classification

The `IsSpuriousError` trait allows determining if an error is transient and can be retried:

```rust
impl IsSpuriousError for std::io::Error {
    fn is_spurious(&self) -> bool {
        use std::io::ErrorKind::*;
        match self.kind() {
            // Errors that might be resolved with a retry
            Interrupted | UnexpectedEof | OutOfMemory | TimedOut |
            BrokenPipe | AddrInUse | ConnectionAborted |
            ConnectionReset | ConnectionRefused => true,
            
            // Errors that won't be fixed by retrying
            _ => false,
        }
    }
}
```

This enables consumers of the transport to implement intelligent retry logic for network operations.

## Testing Strategy

The crate's testing approach includes:

1. **Unit Tests**: Testing individual components in isolation
2. **Integration Tests**: Verifying proper communication between components
3. **Mock Servers**: Using pre-recorded responses to test protocol handling
4. **Feature Flag Testing**: Ensuring functionality works with different feature combinations

The test fixtures include pre-recorded HTTP responses for various Git operations, allowing testing without network access.

Key test areas include:
- Protocol negotiation
- Authentication handling
- Error recovery
- Transport-specific behavior (HTTP, SSH, file, git)