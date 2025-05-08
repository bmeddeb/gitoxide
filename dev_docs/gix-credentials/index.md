# gix-credentials

## Overview

The `gix-credentials` crate provides functionality for interacting with Git credential helpers, which are programs that store and retrieve authentication credentials for Git operations. This crate allows users to obtain, store, and erase credentials using both Git's built-in credential helpers and custom credential helpers. It implements the Git credential protocol and provides interfaces for both consuming helper programs and implementing new ones.

## Architecture

The architecture of the `gix-credentials` crate is organized around three main components:

1. **Helper Interface**: Provides functionality to interact with credential helpers, both built-in and custom, through a clean API.

2. **Protocol Implementation**: Handles the Git credential protocol's data format, including parsing and formatting credentials.

3. **Program Management**: Manages the lifecycle of credential helper programs, from launching them to interacting with their input/output streams.

The crate follows a modular design where each component has specific responsibilities:

- The protocol module handles the communication format and context structure
- The helper module manages credential helper cascades and invocation logic
- The program module focuses on launching and interacting with credential helpers

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Program` | Represents a Git credential helper program. | Used to launch and interact with credential helper programs. |
| `helper::Cascade` | Manages a sequence of credential helpers to try in order. | Provides a streamlined credential lookup mechanism with fallbacks. |
| `helper::Outcome` | Contains the result of invoking a credential helper. | Stores credentials and handles to subsequent operations. |
| `protocol::Context` | Holds credential context information. | Contains URL components, username, password, and control flags. |
| `protocol::Outcome` | High-level result of credential operations. | Wraps identity information with action handles. |
| `helper::NextAction` | Handle for follow-up actions after a credential lookup. | Used to store or erase credentials after obtaining them. |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `program::Kind` | Specifies the type of credential helper program. | `Builtin`, `ExternalName`, `ExternalPath`, `ExternalShellScript` |
| `helper::Action` | Defines the action to perform with the credential helper. | `Get`, `Store`, `Erase` |
| `helper::Error` | Errors that can occur during helper operations. | Various error types related to credential helper operations. |
| `protocol::Error` | High-level errors from credential operations. | Protocol-related errors, including missing identities. |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `builtin` | Invokes Git's built-in credential helper. | `fn builtin(action: helper::Action) -> protocol::Result` |
| `helper::invoke` | Invokes a credential helper with a specific action. | `fn invoke(program: &mut Program, action: &Action) -> Result` |
| `program::main` | Main function for implementing credential helpers. | `fn main<I, R, W, F>(args: I, stdin: R, stdout: W, handler: F) -> Result<(), main::Error>` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-sec` | Security-related functionality, including identity types. |
| `gix-url` | URL parsing and handling. |
| `gix-path` | Path manipulation and conversion utilities. |
| `gix-command` | Command execution for launching credential helpers. |
| `gix-prompt` | User interaction for obtaining credentials interactively. |
| `gix-trace` | Tracing and logging functionality. |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Binary string handling for non-UTF8 paths and data. |
| `thiserror` | Error handling and formatting. |
| `serde` | Optional serialization/deserialization support. |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization of data structures. | `serde`, and serde features for `gix-sec` and `bstr`. |

## Examples

### Basic Usage for Obtaining Credentials

```rust
use gix_credentials::{builtin, helper};

// Create a Get action for a URL 
let action = helper::Action::get_for_url("https://github.com/user/repo");

// Use Git's built-in credential helper to obtain credentials
match builtin(action) {
    Ok(Some(outcome)) => {
        // We have credentials
        println!("Username: {}", outcome.identity.username);
        println!("Password: {}", outcome.identity.password);
        
        // To approve and store these credentials
        builtin(outcome.next.store())?;
        
        // Or to reject them
        // builtin(outcome.next.erase())?;
    },
    Ok(None) => println!("No credentials available"),
    Err(err) => eprintln!("Error: {}", err),
}
```

### Custom Credential Helper

```rust
use gix_credentials::{program, protocol};
use std::io;

fn main() -> Result<(), program::main::Error> {
    program::main(
        std::env::args_os().skip(1),
        io::stdin(),
        io::stdout(),
        |action, context| {
            match action {
                program::main::Action::Get => {
                    // Return credentials for the given context
                    Ok(Some(protocol::Context {
                        username: Some("user".into()),
                        password: Some("password".into()),
                        ..context
                    }))
                },
                program::main::Action::Store => {
                    // Store the credentials
                    println!("Storing credentials for {}", 
                        context.url.as_deref().unwrap_or_default());
                    Ok(None)
                },
                program::main::Action::Erase => {
                    // Delete the credentials
                    println!("Erasing credentials for {}", 
                        context.url.as_deref().unwrap_or_default());
                    Ok(None)
                },
            }
        },
    )
}
```

### Using a Cascade of Credential Helpers

```rust
use gix_credentials::{helper, Program, protocol};

// Create a cascade of credential helpers
let mut cascade = helper::Cascade::default();

// Add a custom helper script
cascade.programs.push(Program::from_custom_definition("!/path/to/helper.sh"));

// Add the built-in Git credential helper
cascade.programs.push(Program::from_kind(gix_credentials::program::Kind::Builtin));

// Try to obtain credentials
let url = "https://example.com/repo.git";
let action = helper::Action::get_for_url(url);
let result = cascade.invoke(action, Default::default())?;

if let Some(outcome) = result {
    if let Some(identity) = outcome.consume_identity() {
        println!("Got credentials: {}:{}", identity.username, identity.password);
    }
}
```

## Implementation Details

### Git Credential Protocol

The Git credential protocol is a line-based, key-value protocol used for communication between Git and credential helpers. The crate implements this protocol with the following characteristics:

1. **Line Format**: Each line contains a key-value pair separated by "=".
2. **Request**: Git sends credential information (protocol, host, path, etc.).
3. **Response**: Helper returns username/password or control information.
4. **Control Flow**: Special keys like "quit" control the credentials lookup process.

### Credential Context

The `protocol::Context` struct mirrors Git's credential context and includes:

- URL components (protocol, host, path)
- Authentication details (username, password)
- Control flags (quit)
- The full URL as a shorthand

### Credential Helper Types

The crate supports four types of credential helpers:

1. **Builtin**: Git's built-in credential helper (`git credential`)
2. **ExternalName**: Custom helpers identified by name (`git-credential-name`)
3. **ExternalPath**: Custom helpers identified by path (`/path/to/helper`)
4. **ExternalShellScript**: Shell scripts to execute (`!script-content`)

### Helper Cascades

The `helper::Cascade` struct implements the sequence of credential helpers that Git typically tries in order:

1. Each helper is tried in turn until credentials are found
2. Helpers can signal to stop the process with the "quit" flag
3. Special handling is available for HTTP paths and username-only queries

### Credential Storage

When credentials are obtained, they can be:

1. **Stored**: Using the `Store` action, typically called after successful authentication
2. **Erased**: Using the `Erase` action, typically after failed authentication
3. **Left Alone**: If no action is taken after retrieval

### Error Handling

The crate provides detailed error types for different failure scenarios:

- Protocol errors (missing URL, parse errors)
- Helper invocation errors (I/O errors, helper failures)
- Identity errors (missing or incomplete credentials)

### Security Considerations

The crate implements several security measures:

1. Password redaction in error messages
2. Using `gix-sec` types for identity information
3. Proper handling of shell escape sequences
4. Support for secure input prompting

## Testing Strategy

The crate is extensively tested with:

1. **Unit Tests**: Test individual components like protocol parsing.
2. **Integration Tests**: Test interaction with mock credential helpers.
3. **Fixture-Based Tests**: Use script fixtures to simulate different helper behaviors.
4. **Example Programs**: Provide working examples that double as functional tests.

Test fixtures include mock credential helpers that:
- Return valid credentials
- Return partial credentials
- Return control signals
- Simulate failure conditions