# gix-prompt

## Overview

The `gix-prompt` crate provides functionality for securely prompting users for input in a terminal environment, with a focus on Git-style interaction patterns. It offers support for both visible input (like usernames) and hidden input (like passwords), respecting Git's conventions for askpass programs and terminal prompting configurations. The crate is designed to be simple to use while handling the complexities of terminal I/O and environment-specific behavior transparently.

## Architecture

The crate is designed with a modular architecture that separates platform-specific implementations from the common interface. The current implementation primarily targets Unix-like platforms, with a fallback error path for other platforms.

The architecture consists of several key components:

1. **High-Level API**: Simple functions like `openly()` and `securely()` that provide the most common functionality with minimal configuration.

2. **Customizable Prompting**: A more flexible `ask()` function that allows configuration of prompt behavior through options.

3. **Environment Integration**: Support for Git's environment variables like `GIT_ASKPASS`, `SSH_ASKPASS`, and `GIT_TERMINAL_PROMPT` to maintain consistent behavior with Git.

4. **Platform-Specific Terminal Handling**: Unix-specific code that handles terminal attributes for secure password input.

The design prioritizes:

- **Security**: Proper handling of terminal echo for sensitive input
- **Compatibility**: Following Git's conventions for askpass programs and environment variables
- **Simplicity**: Easy-to-use API for common use cases
- **Flexibility**: Options for more complex scenarios

## Core Components

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `ask` | Main function that prompts for input with configurable options | `fn ask(prompt: &str, opts: &Options<'_>) -> Result<String, Error>` |
| `openly` | Convenience function for visible input | `fn openly(prompt: impl AsRef<str>) -> Result<String, Error>` |
| `securely` | Convenience function for hidden/password input | `fn securely(prompt: impl AsRef<str>) -> Result<String, Error>` |

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Options<'a>` | Configuration options for prompting | Allows configuring askpass program and mode |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Mode` | Controls how input is displayed | `Visible`, `Hidden`, `Disable` |
| `Error` | Errors that can occur during prompting | Various error conditions |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-command` | Used to run external askpass programs |
| `gix-config-value` | Used to parse boolean values from environment variables |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `thiserror` | Error handling |
| `rustix` | Unix-specific terminal I/O (termios) |
| `parking_lot` | Thread-safe state management for terminal attributes |

## Feature Flags

This crate does not define any feature flags.

## Examples

### Basic Username and Password Prompt

```rust
use gix_prompt::{openly, securely};

fn main() -> Result<(), gix_prompt::Error> {
    // Prompt for username (visible input)
    let username = openly("Username: ")?;
    
    // Prompt for password (hidden input)
    let password = securely("Password: ")?;
    
    println!("Logged in as {} with password of length {}", username, password.len());
    Ok(())
}
```

### Using the Flexible API with Options

```rust
use std::path::PathBuf;
use std::borrow::Cow;
use gix_prompt::{ask, Options, Mode, Error};

fn main() -> Result<(), Error> {
    // Get the options with environment-based configuration
    let options = Options {
        mode: Mode::Hidden,
        askpass: Some(Cow::Owned(PathBuf::from("/usr/bin/ssh-askpass"))),
    }
    .apply_environment(
        true,   // use GIT_ASKPASS
        true,   // use SSH_ASKPASS as fallback
        true,   // respect GIT_TERMINAL_PROMPT
    );
    
    // Prompt for password
    let password = ask("Password: ", &options)?;
    
    println!("Password length: {}", password.len());
    Ok(())
}
```

### Implementing a Simple Askpass Program

```rust
use gix_prompt::securely;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Get the prompt from the command line arguments
    let prompt = std::env::args()
        .nth(1)
        .ok_or("First argument must be the prompt")?;
    
    // Prompt for password securely (hidden input)
    let password = securely(prompt)?;
    
    // Print the result to stdout (expected behavior for askpass programs)
    println!("{}", password);
    Ok(())
}
```

## Implementation Details

### Terminal Handling on Unix

On Unix platforms, the crate uses the termios API to temporarily modify terminal attributes for secure password input:

1. The current terminal state is saved
2. Echo is disabled to prevent displaying the password
3. The user is prompted and input is read
4. The terminal is restored to its original state

This process ensures passwords aren't displayed while being typed, but still allows proper handling of input and newlines.

### Askpass Program Integration

The crate follows Git's convention for external askpass programs:

1. If an askpass program is specified (via options or environment variables), it is called with the prompt as an argument
2. The program's stdout is captured and returned as the user's input
3. If the program fails, the crate falls back to direct terminal prompting

This allows seamless integration with graphical password prompts and SSH authentication agents.

### Environment Variable Handling

The crate respects several Git environment variables:

- `GIT_ASKPASS`: Path to an askpass program, takes precedence over other options
- `SSH_ASKPASS`: Fallback askpass program if GIT_ASKPASS is not set
- `GIT_TERMINAL_PROMPT`: Controls whether terminal prompting is allowed (if "0" or "false", terminal prompting is disabled)

These environment variables allow consistent behavior with Git and other Git-compatible tools.

### Platform Limitations

Currently, the crate has full functionality only on Unix-like platforms (Linux, macOS, FreeBSD). On other platforms (e.g., Windows), direct terminal prompting will return an error, but askpass program functionality will still work if configured.

On Windows, it's common for Git installations to include their own GUI askpass programs, so this limitation doesn't typically cause practical problems.

## Testing Strategy

The crate is tested using:

1. **Integration Tests**: Tests that verify the behavior of the prompting functions with actual terminal I/O
2. **Example Programs**: Executable examples that demonstrate and verify the functionality
3. **Terminal Emulation**: Using the `expectrl` crate to simulate user input in a controlled environment

These tests ensure that:
- Visible input is correctly displayed and captured
- Hidden input is not displayed but correctly captured
- Askpass programs are properly invoked and their output is correctly processed
- Environment variables are correctly interpreted and applied