# gix-protocol Use Cases

## Intended Audience

- **Git Client Implementers**: Developers building Git clients that need to interact with Git servers
- **Repository Management Tools**: Applications that need to fetch, list, or manipulate remote repositories
- **CI/CD Systems**: Systems that need Git protocol operations without a full Git implementation
- **Custom Git Workflow Tools**: Specialized tools that need direct access to Git protocol operations

## Use Cases

### 1. Listing Remote References

**Problem**: A Git client or tool needs to discover what references (branches, tags) exist on a remote repository.

**Solution**: Use the `ls_refs` command to query references from a remote Git server.

```rust
use gix_protocol::{transport::client::{git, Transport}, Command};
use gix_features::progress::NoProgress;

// Connect to a remote repository
let url = "https://github.com/example/repo.git";
let mut transport = git::connect(url, &None)?;

// Perform protocol handshake
let outcome = gix_protocol::handshake(
    &mut transport,
    gix_transport::Protocol::V2,  // Request protocol V2
    None,                         // No authentication
    gix_transport::Service::UploadPack,
)?;

// List references from the remote repository
let mut progress = NoProgress;
let remote_refs = gix_protocol::ls_refs(
    transport,
    &outcome.capabilities,
    |_, args, features| {
        // Request only specific reference patterns
        args.push("ref-prefix refs/heads/".into());  // Only branches
        args.push("ref-prefix refs/tags/".into());   // And tags
        
        // Add agent information
        features.push(("agent", Some("my-git-tool/1.0".into())));
        
        Ok(gix_protocol::ls_refs::Action::Continue)
    },
    &mut progress,
    false,  // No trace output
)?;

// Display the retrieved references
for reference in remote_refs {
    match &reference {
        gix_protocol::handshake::Ref::Direct { full_ref_name, object } => {
            println!("{}: {}", full_ref_name, object);
        },
        gix_protocol::handshake::Ref::Peeled { full_ref_name, tag, object } => {
            println!("{} (tag): {} -> {}", full_ref_name, tag, object);
        },
        // Handle other reference types...
        _ => {}
    }
}
```

### 2. Fetching Objects from a Remote Repository

**Problem**: A Git client needs to fetch objects (commits, trees, blobs) from a remote repository based on specified references.

**Solution**: Use the protocol handshake followed by a fetch operation to retrieve a packfile containing the requested objects.

```rust
use gix_protocol::{transport::client::{git, Transport}, fetch::Arguments};
use gix_features::progress::Progress;
use std::io::{self, Write};

// Simple progress reporter
struct SimpleProgress;
impl Progress for SimpleProgress {
    fn enable(&mut self, _enable: bool) {}
    fn set_name(&mut self, name: &str) {
        print!("\r{}: ", name);
        io::stdout().flush().ok();
    }
    fn set_progress(&mut self, progress: Option<f32>) {
        if let Some(p) = progress {
            print!("{:.1}%", p * 100.0);
            io::stdout().flush().ok();
        }
    }
    fn message(&mut self, message: &str) {
        println!("\r{}", message);
    }
    fn step(&mut self) {}
}

// Connect to a remote repository
let url = "https://github.com/example/repo.git";
let mut transport = git::connect(url, &None)?;

// Perform protocol handshake
let outcome = gix_protocol::handshake(
    &mut transport,
    gix_transport::Protocol::V2,
    None,
    gix_transport::Service::UploadPack,
)?;

// Build fetch arguments
let mut arguments = Arguments::default();

// Specify what to fetch - here we want a specific commit
arguments.want_object(gix_hash::ObjectId::from_hex("abcdef1234567890abcdef1234567890abcdef12")?);

// Or fetch by reference name using ref-in-want feature (Protocol V2)
if outcome.server_protocol_version == gix_transport::Protocol::V2 {
    if outcome.capabilities.contains("ref-in-want") {
        arguments.want_ref("refs/heads/main".into());
    }
}

// Specify what we already have to minimize data transfer
arguments.have_object(gix_hash::ObjectId::from_hex("0123456789abcdef0123456789abcdef01234567")?);

// Execute the fetch operation
let mut progress = SimpleProgress;
let response = gix_protocol::fetch(
    transport,
    &outcome.capabilities,
    arguments,
    &mut progress,
    false, // No trace
)?;

// Process the packfile data from the response
match response {
    gix_protocol::fetch::Response::Data(mut reader) => {
        // Read and process the packfile data
        let mut pack_data = Vec::new();
        reader.read_to_end(&mut pack_data)?;
        
        // Write pack to a file or process it directly
        std::fs::write("fetched.pack", pack_data)?;
        println!("Fetched {} bytes of pack data", pack_data.len());
    }
    gix_protocol::fetch::Response::Empty => {
        println!("No new objects to fetch");
    }
}
```

### 3. Authenticated Remote Operations

**Problem**: A Git client needs to perform operations against a private repository that requires authentication.

**Solution**: Use credential authentication during the handshake to establish an authenticated connection.

```rust
use gix_protocol::{transport::client::{http, Transport}, credentials::helper::{self, Outcome, Action}};
use gix_features::progress::NoProgress;

// Define a credential helper function
fn authenticate(action: gix_credentials::helper::Action) -> gix_credentials::protocol::Result {
    // For testing, you might hard-code credentials
    // In production, you'd use credential helpers or UI prompts
    match action {
        Action::Get(url) => {
            Ok(Outcome::Provided(gix_credentials::protocol::Credential {
                username: Some("my-username".into()),
                password: Some("my-password".into()),
                url,
            }))
        }
        _ => Ok(Outcome::Abort)
    }
}

// Create authentication function
let authenticate_fn = Box::new(authenticate);

// Connect to a private repository
let url = "https://github.com/private/repo.git";
let mut transport = http::connect(url)?;

// Perform authenticated handshake
let outcome = gix_protocol::handshake(
    &mut transport,
    gix_transport::Protocol::V2,
    Some(authenticate_fn),
    gix_transport::Service::UploadPack,
)?;

// After successful handshake, proceed with operations...
let mut progress = NoProgress;
let remote_refs = gix_protocol::ls_refs(
    transport,
    &outcome.capabilities,
    |_, args, features| {
        features.push(("agent", Some("my-auth-client/1.0".into())));
        Ok(gix_protocol::ls_refs::Action::Continue)
    },
    &mut progress,
    false,
)?;

println!("Successfully authenticated and fetched {} refs", remote_refs.len());
```

### 4. Protocol Version Negotiation

**Problem**: A Git client needs to communicate with various servers that might support different protocol versions.

**Solution**: Negotiate the protocol version during handshake, adapting operations based on the server's capabilities.

```rust
use gix_protocol::transport::client::{git, Transport};
use gix_features::progress::NoProgress;

// Connect to a repository (unknown protocol version support)
let url = "https://github.com/example/repo.git";
let mut transport = git::connect(url, &None)?;

// Request V2, but be prepared to handle V1
let outcome = gix_protocol::handshake(
    &mut transport,
    gix_transport::Protocol::V2,  // Prefer V2
    None,
    gix_transport::Service::UploadPack,
)?;

// Check which protocol version was negotiated
match outcome.server_protocol_version {
    gix_transport::Protocol::V2 => {
        println!("Using modern protocol V2");
        
        // With V2, we need a separate ls-refs command to get references
        let mut progress = NoProgress;
        let refs = gix_protocol::ls_refs(
            transport.clone(),
            &outcome.capabilities,
            |_, args, features| {
                features.push(("agent", Some("my-client/1.0".into())));
                Ok(gix_protocol::ls_refs::Action::Continue)
            },
            &mut progress,
            false,
        )?;
        
        println!("Found {} references", refs.len());
    },
    gix_transport::Protocol::V1 => {
        println!("Using legacy protocol V1");
        
        // With V1, refs are included in the handshake outcome
        if let Some(refs) = outcome.refs {
            println!("Found {} references", refs.len());
        }
    },
    gix_transport::Protocol::V0 => {
        println!("Using very old protocol V0");
        // Handle accordingly
    }
}
```

### 5. Working with Shallow Repositories

**Problem**: A Git client needs to work with shallow repositories to limit data transfer for large projects.

**Solution**: Use shallow repository features during fetch operations to control repository depth.

```rust
use gix_protocol::{transport::client::{git, Transport}, fetch::Arguments};
use gix_features::progress::NoProgress;

// Connect to a repository
let url = "https://github.com/large/repo.git";
let mut transport = git::connect(url, &None)?;

// Perform handshake
let outcome = gix_protocol::handshake(
    &mut transport,
    gix_transport::Protocol::V2,
    None,
    gix_transport::Service::UploadPack,
)?;

// Check if server supports shallow fetches
let supports_shallow = if outcome.server_protocol_version == gix_transport::Protocol::V2 {
    outcome.capabilities.contains("shallow")
} else {
    outcome.capabilities.contains("shallow")
};

if supports_shallow {
    // Build fetch arguments with shallow options
    let mut arguments = Arguments::default();
    
    // Specify what to fetch
    arguments.want_ref("refs/heads/main".into());
    
    // Limit clone depth to 10 commits
    arguments.deepen(10);
    
    // Or limit by date
    // arguments.deepen_since(gix_date::Time::now() - Duration::days(30));
    
    // Or exclude specific commits and their ancestors
    // arguments.deepen_not("refs/tags/old-release".into());
    
    // Execute the shallow fetch
    let mut progress = NoProgress;
    let response = gix_protocol::fetch(
        transport,
        &outcome.capabilities,
        arguments,
        &mut progress,
        false,
    )?;
    
    // Process response...
    match response {
        gix_protocol::fetch::Response::Data(mut reader) => {
            // Read and process the packfile with shallow info
            let mut pack_data = Vec::new();
            reader.read_to_end(&mut pack_data)?;
            println!("Fetched shallow repository data: {} bytes", pack_data.len());
        }
        gix_protocol::fetch::Response::Empty => {
            println!("No objects to fetch (already up to date)");
        }
    }
} else {
    println!("Server does not support shallow fetches");
}
```

### 6. Implementing Custom Transport Mechanisms

**Problem**: A Git application needs to use a custom transport method (e.g., in-memory, database-backed, p2p protocol).

**Solution**: Implement the `Transport` trait and use it with the protocol operations.

```rust
use gix_protocol::transport::client::{Capabilities, Transport, TransportV2Ext};
use gix_protocol::handshake::Ref;
use gix_features::progress::NoProgress;
use bstr::BString;
use std::borrow::Cow;
use std::io::{Read, Write};
use maybe_async::maybe_async;

// Custom transport implementation example (simplified)
struct CustomTransport {
    // Implementation-specific state
    capabilities: Capabilities,
    // Other fields...
}

#[maybe_async]
impl Transport for CustomTransport {
    type Read = std::io::Cursor<Vec<u8>>;
    
    async fn handshake(
        &mut self, 
        service: gix_transport::Service, 
        _version: gix_transport::Protocol,
    ) -> Result<(gix_transport::Protocol, Capabilities), gix_transport::client::Error> {
        // Custom handshake implementation
        // This would connect to your storage backend and perform protocol negotiation
        
        // For demonstration, returning dummy values
        Ok((gix_transport::Protocol::V2, self.capabilities.clone()))
    }
    
    async fn request(
        &mut self,
        write_mode: gix_transport::client::WriteMode,
        on_into_read: Option<&mut dyn FnMut()>,
    ) -> Result<Self::Read, gix_transport::client::Error> {
        // Custom implementation to create a request channel
        // For demonstration, returning a dummy reader
        if let Some(callback) = on_into_read {
            callback();
        }
        
        match write_mode {
            gix_transport::client::WriteMode::Binary(mut writer) => {
                // For demonstration, just acknowledge the write
                writer.flush()?;
            }
            gix_transport::client::WriteMode::OneLine(line) => {
                // Process the one-line command
                println!("Received command: {:?}", line);
            }
        }
        
        // Return a dummy reader
        Ok(std::io::Cursor::new(Vec::new()))
    }
    
    fn to_url(&self) -> &gix_url::Url {
        // Return the URL representing this transport
        todo!("Implement URL representation")
    }
    
    async fn close(&mut self) -> Result<(), gix_transport::client::Error> {
        // Close connections, clean up resources
        Ok(())
    }
}

#[maybe_async]
impl TransportV2Ext for CustomTransport {
    async fn invoke<'a, F, A>(
        &mut self, 
        command: &str, 
        features: F, 
        arguments: Option<A>,
        _trace: bool,
    ) -> Result<std::io::Cursor<Vec<u8>>, gix_transport::client::Error> 
    where
        F: Iterator<Item = (&'a str, Option<Cow<'a, str>>)>,
        A: Iterator<Item = BString>,
    {
        // Implement V2 command invocation for custom transport
        println!("Invoking command: {}", command);
        
        // Return dummy response
        Ok(std::io::Cursor::new(Vec::new()))
    }
}

// Usage example (conceptual)
fn use_custom_transport() -> std::io::Result<()> {
    // Create custom transport
    let custom_transport = CustomTransport {
        capabilities: Capabilities::default(),
        // Initialize other fields...
    };
    
    // Use the custom transport with the protocol
    // Note: This won't actually run since our implementation is incomplete
    /*
    let outcome = gix_protocol::handshake(
        &mut custom_transport,
        gix_transport::Protocol::V2,
        None,
        gix_transport::Service::UploadPack,
    )?;
    
    let mut progress = NoProgress;
    let refs = gix_protocol::ls_refs(
        custom_transport,
        &outcome.capabilities,
        |_, args, features| {
            Ok(gix_protocol::ls_refs::Action::Continue)
        },
        &mut progress,
        false,
    )?;
    */
    
    Ok(())
}
```

These use cases demonstrate how `gix-protocol` can be used to implement various Git client operations by directly interacting with Git's wire protocol, providing fine-grained control over Git operations without requiring a full Git implementation.