# gix-prompt Use Cases

This document describes the primary use cases for the gix-prompt crate, who its intended audience is, what problems it solves, and how it solves them.

## Intended Audience

The gix-prompt crate is primarily intended for:

1. **Git Client Developers**: Developers building Git clients or Git-compatible tools that need to prompt for credentials
2. **CLI Tool Developers**: Developers creating command-line tools that need secure password input
3. **Gitoxide Component Developers**: Internal users developing components in the gitoxide ecosystem that need user input
4. **Authentication System Developers**: Developers implementing authentication systems that need to collect user credentials securely

## Core Use Cases

### 1. Implementing Git Credential Helper

#### Problem

Git needs to collect usernames and passwords for authentication with remote repositories. This requires a secure way to prompt users for sensitive information while respecting their configuration preferences regarding how prompts should be handled.

#### Solution

The gix-prompt crate provides functionality to implement credential helper programs that can securely prompt for authentication information:

```rust
use std::io::{self, BufRead, Write};
use gix_prompt::{Options, Mode, openly, securely};

/// A basic git credential helper that prompts for username and password
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Read stdin line by line to process Git's credential protocol
    let stdin = io::stdin();
    let mut stdout = io::stdout();
    let mut command = None;
    let mut protocol = None;
    let mut host = None;
    let mut username = None;
    
    // Process the input from Git
    for line in stdin.lock().lines() {
        let line = line?;
        if line.is_empty() {
            break;
        }
        
        if let Some(cmd) = line.strip_prefix("command=") {
            command = Some(cmd.to_string());
            continue;
        }
        if let Some(proto) = line.strip_prefix("protocol=") {
            protocol = Some(proto.to_string());
            continue;
        }
        if let Some(h) = line.strip_prefix("host=") {
            host = Some(h.to_string());
            continue;
        }
        if let Some(user) = line.strip_prefix("username=") {
            username = Some(user.to_string());
            continue;
        }
    }
    
    // Handle the "get" command
    if command == Some("get".to_string()) {
        // If we have protocol and host information, prompt for credentials
        if let (Some(protocol), Some(host)) = (protocol.as_ref(), host.as_ref()) {
            // We might already have a username from Git
            let username = match username {
                Some(username) => username,
                None => {
                    // Create a prompt message based on the repository information
                    let prompt = format!("Username for {protocol}://{host}: ");
                    openly(prompt)?
                }
            };
            
            // Always prompt for password
            let password_prompt = format!("Password for {protocol}://{username}@{host}: ");
            let password = securely(password_prompt)?;
            
            // Output the credentials in Git's expected format
            writeln!(stdout, "username={username}")?;
            writeln!(stdout, "password={password}")?;
            stdout.flush()?;
        }
    }
    
    Ok(())
}
```

### 2. Implementing SSH Passphrase Prompt

#### Problem

SSH keys used for Git authentication may be encrypted and require a passphrase. Git needs a way to prompt for this passphrase, possibly using a GUI program if available, or falling back to a terminal prompt.

#### Solution

The gix-prompt crate can be used to implement SSH passphrase prompting that respects Git's configuration for askpass programs:

```rust
use std::path::PathBuf;
use std::env;
use gix_prompt::{ask, Options, Mode, Error};

/// Prompt for an SSH key passphrase
fn prompt_for_ssh_passphrase(key_path: &str) -> Result<String, Error> {
    // Create the prompt message
    let prompt = format!("Enter passphrase for key '{}': ", key_path);
    
    // Set up options according to Git's conventions
    let options = Options {
        mode: Mode::Hidden, // Don't display the passphrase
        askpass: None,      // Will be filled in from environment if available
    }
    .apply_environment(
        true,  // Use GIT_ASKPASS if available
        true,  // Fall back to SSH_ASKPASS if GIT_ASKPASS isn't set
        true,  // Respect GIT_TERMINAL_PROMPT
    );
    
    // Prompt for the passphrase
    ask(&prompt, &options)
}

/// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Get the key path from arguments or use a default
    let key_path = env::args().nth(1).unwrap_or_else(|| "~/.ssh/id_rsa".to_string());
    
    match prompt_for_ssh_passphrase(&key_path) {
        Ok(passphrase) => {
            // In a real implementation, this would be used to decrypt the key
            println!("Successfully obtained passphrase ({} characters)", passphrase.len());
            // Don't print the actual passphrase!
        }
        Err(Error::Disabled) => {
            eprintln!("Terminal prompts are disabled by GIT_TERMINAL_PROMPT");
            eprintln!("Set an askpass program or enable terminal prompts");
        }
        Err(Error::UnsupportedPlatform) => {
            eprintln!("Terminal prompting is not supported on this platform");
            eprintln!("Set GIT_ASKPASS or SSH_ASKPASS to a GUI askpass program");
        }
        Err(e) => {
            eprintln!("Error prompting for passphrase: {}", e);
        }
    }
    
    Ok(())
}
```

### 3. Creating a Custom Askpass Program

#### Problem

Git and other tools rely on external "askpass" programs to prompt for passwords, especially in environments where direct terminal access isn't available (like in GUI applications or when running as a service). These programs need to follow a specific protocol to integrate properly.

#### Solution

The gix-prompt crate can be used to create a custom askpass program that follows Git's conventions:

```rust
use std::env;
use gix_prompt::{securely, Error};

/// A custom askpass program that prompts for input securely
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Get the prompt from command-line arguments
    // askpass programs are called with the prompt as the first argument
    let prompt = match env::args().nth(1) {
        Some(prompt) => prompt,
        None => {
            eprintln!("Error: No prompt provided");
            return Err("No prompt provided".into());
        }
    };
    
    // Determine if this is a password prompt
    let is_password = prompt.contains("password") || 
                     prompt.contains("passphrase") ||
                     prompt.contains("Password") ||
                     prompt.contains("Passphrase");
    
    // Get the input
    let input = if is_password {
        // Use hidden input for passwords/passphrases
        securely(&prompt)?
    } else {
        // Use visible input for usernames and other non-sensitive input
        gix_prompt::openly(&prompt)?
    };
    
    // Print the result to stdout (this is the protocol expected by Git)
    println!("{}", input);
    
    Ok(())
}
```

### 4. Implementing Two-Factor Authentication Flow

#### Problem

Modern authentication systems often require multi-factor authentication, requiring prompting for different types of credentials (passwords, one-time codes, etc.) in sequence, with appropriate UI treatment for each.

#### Solution

The gix-prompt crate provides flexibility to implement more complex authentication flows:

```rust
use gix_prompt::{openly, securely, ask, Options, Mode, Error};
use std::borrow::Cow;
use std::path::PathBuf;

/// A struct representing authentication factors
struct AuthFactors {
    username: String,
    password: String,
    totp_code: Option<String>,
    security_key_used: bool,
}

/// Prompt for all required authentication factors
fn prompt_for_auth_factors(
    service_name: &str,
    username: Option<&str>,
    requires_2fa: bool,
    prefer_gui: bool,
) -> Result<AuthFactors, Error> {
    // Set up the options - use GUI if preferred and available
    let askpass_path = if prefer_gui {
        if let Ok(path) = std::env::var("GUI_ASKPASS") {
            Some(Cow::Owned(PathBuf::from(path)))
        } else {
            None
        }
    } else {
        None
    };
    
    let options = Options {
        askpass: askpass_path,
        mode: Mode::Visible, // Will be overridden for passwords
    };
    
    // Prompt for username if not provided
    let username = match username {
        Some(username) => username.to_string(),
        None => {
            let prompt = format!("Username for {}: ", service_name);
            openly(prompt)?
        }
    };
    
    // Prompt for password (always hidden)
    let password_prompt = format!("Password for {} @ {}: ", username, service_name);
    let password_options = Options {
        mode: Mode::Hidden,
        ..options.clone()
    };
    let password = ask(&password_prompt, &password_options)?;
    
    let mut factors = AuthFactors {
        username,
        password,
        totp_code: None,
        security_key_used: false,
    };
    
    // Handle 2FA if required
    if requires_2fa {
        // Ask user for 2FA method
        let method_prompt = format!("Two-factor authentication required for {}\n1. Time-based one-time password (TOTP)\n2. Security key\nChoose method (1-2): ", service_name);
        let method = openly(method_prompt)?;
        
        match method.trim() {
            "1" => {
                // Prompt for TOTP code
                let totp_prompt = "Authentication code: ";
                factors.totp_code = Some(openly(totp_prompt)?);
            },
            "2" => {
                // Simulate security key prompt (in a real app, this would use a security key API)
                println!("Please insert your security key and press the button when it flashes...");
                // Security key handling would go here
                factors.security_key_used = true;
            },
            _ => {
                return Err(Error::Disabled); // Reuse this error for invalid input
            }
        }
    }
    
    Ok(factors)
}

/// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let service_name = "example.com";
    let requires_2fa = true;
    let prefer_gui = false;
    
    match prompt_for_auth_factors(service_name, None, requires_2fa, prefer_gui) {
        Ok(factors) => {
            println!("Authentication successful for {}", factors.username);
            if let Some(totp) = factors.totp_code {
                println!("TOTP code provided: {}", totp);
            }
            if factors.security_key_used {
                println!("Security key authentication used");
            }
        },
        Err(e) => {
            eprintln!("Authentication failed: {}", e);
        }
    }
    
    Ok(())
}
```

### 5. Secure Configuration Input for CLI Tools

#### Problem

Command-line tools often need to collect sensitive configuration information, like API keys or tokens, during initial setup. This needs to be done securely, while providing a good user experience.

#### Solution

The gix-prompt crate can be used to implement secure configuration input:

```rust
use std::{fs, path::PathBuf};
use gix_prompt::{openly, securely, Error};

/// Configuration data structure
struct Config {
    username: String,
    api_key: String,
    endpoint: String,
    save_credentials: bool,
}

/// Interactive configuration wizard
fn configure() -> Result<Config, Error> {
    println!("=== Configuration Wizard ===");
    println!("Please enter your account information:");
    
    // Ask for non-sensitive information with visible input
    let username = openly("Username: ")?;
    let endpoint = openly("API Endpoint URL: ")?;
    
    // Ask for sensitive information with hidden input
    let api_key = securely("API Key: ")?;
    
    // Ask for a boolean preference
    let save_prompt = "Save credentials to configuration file? (y/n): ";
    let save_response = openly(save_prompt)?;
    let save_credentials = save_response.trim().to_lowercase().starts_with('y');
    
    // Create and return the configuration
    Ok(Config {
        username,
        api_key,
        endpoint,
        save_credentials,
    })
}

/// Save configuration to file
fn save_config(config: &Config, path: &PathBuf) -> Result<(), Box<dyn std::error::Error>> {
    // In a real application, this would use proper serialization
    let content = format!(
        "username={}\nendpoint={}\n",
        config.username, config.endpoint
    );
    
    // Create directory if it doesn't exist
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    
    // Write the non-sensitive parts to the config file
    fs::write(path, content)?;
    
    // Handle sensitive information according to user preference
    if config.save_credentials {
        // In a real app, this would use a secure credential store
        println!("Saving API key to secure storage...");
        // simulate_secure_storage(&config.api_key)?;
    } else {
        println!("API key not saved. You will need to enter it each time.");
    }
    
    println!("Configuration saved to {}", path.display());
    Ok(())
}

/// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config_path = PathBuf::from("./config.ini");
    
    // Run the configuration wizard
    match configure() {
        Ok(config) => {
            save_config(&config, &config_path)?;
        },
        Err(Error::Disabled) => {
            eprintln!("Terminal prompts are disabled");
        },
        Err(Error::UnsupportedPlatform) => {
            eprintln!("This platform doesn't support terminal prompting");
            eprintln!("Please use the --config flag to specify a configuration file");
        },
        Err(e) => {
            eprintln!("Error during configuration: {}", e);
        }
    }
    
    Ok(())
}
```

## Integration with Other Components

The gix-prompt crate is integrated with several other components in the gitoxide ecosystem:

### Integration with gix-credentials

The `gix-credentials` crate uses gix-prompt to implement Git credential helpers:

```rust
use gix_prompt::{openly, securely, Options, Mode};
use gix_credentials::protocol::{Request, Response};

/// Fill in missing credential information by prompting the user
fn fill_credentials(request: &Request) -> Result<Response, gix_prompt::Error> {
    // Create a response object to fill in
    let mut response = Response::default();
    
    // Make sure we have protocol and host information for a meaningful prompt
    let protocol = request.protocol.as_deref().unwrap_or("https");
    let host = match &request.host {
        Some(host) => host,
        None => return Ok(response), // Can't prompt without a host
    };
    
    // If username is not provided, prompt for it
    if request.username.is_none() {
        let prompt = format!("Username for {protocol}://{host}: ");
        response.username = Some(openly(prompt)?);
    } else {
        response.username = request.username.clone();
    }
    
    // If we need a password, prompt for it securely
    if request.password.is_none() {
        let username = response.username.as_deref().unwrap_or("anonymous");
        let prompt = format!("Password for {protocol}://{username}@{host}: ");
        
        // Use environment-aware options
        let options = Options {
            mode: Mode::Hidden,
            askpass: None,
        }.apply_environment(true, true, true);
        
        response.password = Some(gix_prompt::ask(&prompt, &options)?);
    } else {
        response.password = request.password.clone();
    }
    
    Ok(response)
}
```

### Integration with Command-Line Tools

The `gix-prompt` crate can be used in command-line tools within the gitoxide ecosystem to handle user input consistently:

```rust
use gix_prompt::{openly, securely, Error};
use std::path::PathBuf;

// A hypothetical CLI command that needs user confirmation and credentials
fn execute_command(
    repo_path: PathBuf,
    force: bool,
    operation: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // If not forcing, ask for confirmation
    if !force {
        let prompt = format!("This will {} the repository at {}. Continue? (y/N): ", 
                           operation, repo_path.display());
        let confirmation = openly(prompt)?;
        if !confirmation.trim().eq_ignore_ascii_case("y") {
            println!("Operation cancelled by user");
            return Ok(());
        }
    }
    
    // For sensitive operations, require password authentication
    if operation == "delete" || operation == "force-push" {
        let prompt = "Enter your admin password to authorize this operation: ";
        let password = securely(prompt)?;
        
        // In a real implementation, this would verify the password
        if password.len() < 8 {
            return Err("Invalid password".into());
        }
    }
    
    // Perform the actual operation
    println!("Executing {} on {}", operation, repo_path.display());
    // Implementation would go here
    
    Ok(())
}
```

## Conclusion

The gix-prompt crate provides essential functionality for secure user interaction in a terminal environment. Its integration with Git's conventions for askpass programs and environment variables makes it particularly well-suited for Git-related tools, but its simple API and focus on security make it useful for any command-line application that needs to prompt for sensitive information.

The key strengths of the crate are:

1. **Security**: Properly handles terminal attributes to ensure sensitive input isn't displayed
2. **Git Integration**: Follows Git's conventions for askpass programs and environment variables
3. **Simplicity**: Provides an easy-to-use API for common use cases
4. **Flexibility**: Offers configuration options for more complex scenarios

While the crate has some platform limitations (full functionality is only available on Unix-like systems), it provides a consistent interface across all platforms and follows Git's approach to handling these limitations.