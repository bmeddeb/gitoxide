# gix-protocol

## Overview

The `gix-protocol` crate implements Git protocol operations, serving as a layer between high-level Git commands and the low-level transport mechanisms in `gix-transport`. It provides abstractions for executing Git protocol commands such as `fetch`, `ls-refs`, and performing protocol handshakes.

This crate handles the command flow in Git client-server communication: establishing a transport connection, performing a handshake to negotiate capabilities, and executing protocol-specific commands with proper argument validation. It supports both the stateful protocol version 1 and the stateless command-based protocol version 2.

## Architecture

The crate is architecturally organized around Git's protocol operations:

1. **Command Model**: Defines Git protocol commands (like `ls-refs` and `fetch`) with their arguments, features, and validation rules
2. **Protocol Variants**: Supports both V1 (stateful) and V2 (stateless) Git protocols with appropriate protocol flows
3. **Handshake Mechanism**: Handles capability negotiation and initial server connections
4. **Command Implementations**: Provides specific implementations for each protocol command
5. **Dual I/O Models**: Offers both blocking and async implementations through feature flags

The design emphasizes a separation between protocol commands and transport layers, allowing for flexible client implementations. It also provides validation of commands and features against server capabilities to prevent protocol errors.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `handshake::Outcome` | Contains results of a protocol handshake with a Git server | Stores protocol version, server capabilities, and references |
| `RemoteProgress` | Represents progress information from remote Git operations | Used for tracking progress of fetch operations |
| `fetch::Arguments` | Represents arguments for a Git fetch command | Configures what and how to fetch from a remote |
| `fetch::RefMap` | Maps between local refspecs and remote references | Used to determine which refs to fetch based on refspecs |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `gix_transport::client::Transport` | Interface for transport implementations | Used by protocol functions to communicate with Git servers |
| `gix_transport::client::TransportV2Ext` | Extension for V2 protocol transport | Implemented by transports supporting V2 protocol commands |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `handshake()` | Performs initial protocol handshake with a Git server | `fn handshake(transport, desired_version, authenticate, service) -> Result<Outcome, Error>` |
| `ls_refs()` | Lists references from the remote repository | `fn ls_refs(transport, capabilities, prepare_ls_refs, progress, trace) -> Result<Vec<Ref>, Error>` |
| `fetch()` | Fetches Git objects from a remote repository | `fn fetch(transport, capabilities, arguments, progress, trace) -> Result<Response, Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Command` | Git protocol commands supported by the implementation | `LsRefs`, `Fetch` |
| `handshake::Ref` | Represents a Git reference returned by the server | `Peeled`, `Direct`, `Symbolic`, `Unborn` |
| `ls_refs::Action` | Controls behavior after preparing ls-refs command | `Continue`, `Skip` |
| `fetch::ShallowUpdate` | Represents changes to shallow repository status | Various variants for shallow operations |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-transport` | Provides transport layer implementations for different protocols (Git, HTTP, SSH) |
| `gix-hash` | Used for object hash identifiers and manipulation |
| `gix-features` | Provides progress tracking, tracing, and other shared features |
| `gix-negotiate` | Implements negotiation algorithms for fetch operations |
| `gix-shallow` | Handles shallow repository operations |
| `gix-credentials` | Manages authentication for remote operations |
| `gix-ref` | Provides reference manipulation utilities |
| `gix-object` | Used for Git object operations |
| `gix-revwalk` | Implements graph traversal for fetch negotiation |
| `gix-refspec` | Handles refspec parsing and matching |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Used for binary string handling (Git uses non-UTF8 strings) |
| `thiserror` | For error type definitions |
| `maybe-async` | Provides unified sync/async API for both blocking and async implementations |
| `futures-lite` | Async utilities (when async-client feature is enabled) |
| `async-trait` | Async trait support (when async-client feature is enabled) |
| `serde` | Optional serialization/deserialization support |
| `winnow` | Parsing utilities for protocol messages |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `blocking-client` | Enables blocking implementation of protocol commands | `gix-transport/blocking-client`, `maybe-async/is_sync`, `handshake`, `fetch` |
| `async-client` | Enables async implementation of protocol commands | `gix-transport/async-client`, `async-trait`, `futures-io`, `futures-lite`, `handshake`, `fetch` |
| `handshake` | Adds protocol handshake implementation | `gix-credentials` |
| `fetch` | Adds fetch command implementation | `gix-negotiate`, `gix-object`, `gix-revwalk`, `gix-lock`, `gix-refspec`, `gix-trace` |
| `serde` | Adds serialization support | `serde`, `bstr/serde`, `gix-transport/serde`, `gix-hash/serde`, `gix-shallow/serde` |

## Examples

```rust
// Example: List references from a remote repository
use gix_protocol::transport::client::{git, Transport};
use gix_features::progress::NoProgress;

// Create a transport to connect to a remote repository
let url = "https://github.com/gitoxide/gitoxide.git";
let mut transport = git::connect(url, &None)?;

// Perform protocol handshake
let outcome = gix_protocol::handshake(
    &mut transport,
    gix_transport::Protocol::V2,
    None,
    gix_transport::Service::UploadPack,
)?;

// List references from the remote repository
let mut progress = NoProgress;
let remote_refs = gix_protocol::ls_refs(
    transport,
    &outcome.capabilities,
    |_, args, features| {
        // Add ref-prefix to limit results to specific refs
        args.push("ref-prefix refs/heads/".into());
        // Add agent information
        features.push(("agent", Some("gix/0.1.0".into())));
        Ok(gix_protocol::ls_refs::Action::Continue)
    },
    &mut progress,
    false, // no trace
)?;

// Process the retrieved references
for reference in remote_refs {
    println!("{:?}", reference);
}
```

## Implementation Details

### Protocol Version Handling

The crate supports both Git protocol versions:

1. **Protocol V1** (stateful):
   - Traditional Git protocol with a single connection for the entire session
   - References and capabilities are advertised during the initial handshake
   - Commands like fetch have a specific sequence that must be followed

2. **Protocol V2** (stateless, command-based):
   - Introduced in Git 2.18
   - Separate, independent commands that can be executed in any order
   - More explicit capability negotiation
   - Supports more efficient operations with features like `ref-in-want`

The protocol version is determined during the handshake phase, where the client can request a specific version, but the server may downgrade to an older version if it doesn't support the requested one.

### Capability and Argument Validation

The crate implements strict validation of command arguments and capabilities:
- Commands can only use arguments and features that are known to be valid
- Server capabilities are checked to ensure the command will be accepted
- This validation happens before sending commands to prevent protocol errors

### Handling Credentials

When authentication is required, the crate uses `gix-credentials` to:
1. Request credentials from a credential helper
2. Apply them to the transport
3. Handle credential rejection with proper error reporting

### Shallow Repository Support

The protocol implementation includes support for shallow repositories with features like:
- Deepen operations (by commit depth, date, or revision)
- Unshallowing operations
- Shallow update tracking

## Testing Strategy

The crate employs several testing approaches:

1. **Protocol Fixtures**: Tests use recorded protocol interactions as fixtures to verify correct behavior without needing a real Git server
2. **Version-specific Tests**: Separate test cases for V1 and V2 protocol versions
3. **Integration Tests**: End-to-end tests validating command flows against real repositories
4. **Async/Blocking Tests**: Separate test suites for both I/O models
5. **Error Handling Tests**: Tests for proper error recovery and reporting

These tests verify both low-level protocol behavior and higher-level command operations, ensuring compatibility with Git servers.