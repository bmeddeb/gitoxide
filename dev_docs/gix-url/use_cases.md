# gix-url Use Cases

## Intended Audience

- **Git Client Implementers**: Developers building Git clients that need to parse and manipulate Git URLs
- **Repository Management Tools**: Applications that need to work with Git repositories at different locations
- **Repository URI Handlers**: Software that registers to handle Git URLs in various formats
- **Git Workflow Tools**: Applications that need to parse and validate Git URLs from user input

## Use Cases

### 1. Parsing and Validating Git URLs from User Input

**Problem**: Applications need to safely parse and validate Git URLs entered by users, which can come in various formats.

**Solution**: Use the `parse` function to handle all Git URL formats while validating their correctness.

```rust
use bstr::ByteSlice;
use gix_url::{parse, Scheme};
use std::io::{self, Write};

// Function to parse and validate a Git URL from user input
fn parse_and_validate_git_url(input: &str) -> Result<String, String> {
    let input_bytes = input.trim().as_bytes();
    
    match parse(input_bytes.as_bstr()) {
        Ok(url) => {
            // Validate that the URL has necessary components
            match url.scheme {
                Scheme::Http | Scheme::Https | Scheme::Git => {
                    if url.host().is_none() {
                        return Err(format!("Missing host in {} URL", url.scheme));
                    }
                }
                Scheme::Ssh => {
                    if url.host().is_none() {
                        return Err("Missing host in SSH URL".to_string());
                    }
                }
                Scheme::File => {
                    // File URLs don't necessarily need a host
                }
                Scheme::Ext(ref proto) => {
                    return Err(format!("Unsupported protocol: {}", proto));
                }
            }
            
            // Check if the path component is not empty (except for root)
            if url.path.len() <= 1 && !url.path_is_root() {
                return Err("Missing repository path in URL".to_string());
            }
            
            Ok(format!("Valid Git URL: {} (Scheme: {})", url, url.scheme))
        }
        Err(err) => Err(format!("Invalid Git URL: {}", err)),
    }
}

// Example usage:
fn main() -> io::Result<()> {
    println!("Enter a Git URL:");
    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    
    match parse_and_validate_git_url(&input) {
        Ok(message) => println!("{}", message),
        Err(error) => println!("Error: {}", error),
    }
    
    Ok(())
}
```

### 2. Secure Command-Line Argument Construction

**Problem**: When working with Git URLs, components like hostnames and paths need to be passed to command-line tools (like SSH), but could contain malicious characters.

**Solution**: Use the `ArgumentSafety` features to ensure URL components can be safely used as command-line arguments.

```rust
use bstr::ByteSlice;
use gix_url::{parse, ArgumentSafety};
use std::process::Command;

// Function to safely clone a repository using system commands
fn clone_repository(url_str: &str, destination: &str) -> Result<(), String> {
    let url = parse(url_str.as_bytes().as_bstr())
        .map_err(|e| format!("Failed to parse URL: {}", e))?;
    
    // Check if the URL components are safe to use in command-line arguments
    match url.host_as_argument() {
        ArgumentSafety::Usable(_) => { /* Host is safe to use */ },
        ArgumentSafety::Dangerous(host) => {
            return Err(format!("Potentially dangerous hostname detected: {}", host));
        },
        ArgumentSafety::Absent => {
            if url.scheme != gix_url::Scheme::File {
                return Err("Host is required for non-file URLs".to_string());
            }
        }
    }
    
    // For SSH URLs, also check if the username is safe
    if url.scheme == gix_url::Scheme::Ssh {
        if let Some(user) = url.user() {
            if user.starts_with('-') {
                return Err(format!("Potentially dangerous username detected: {}", user));
            }
        }
    }
    
    // Check if the path is safe (doesn't start with - after the leading /)
    if url.path_argument_safe().is_none() && !url.path_is_root() {
        return Err("Potentially dangerous path detected".to_string());
    }
    
    // Now we can safely construct the git clone command
    let url_string = url.to_bstring();
    let status = Command::new("git")
        .arg("clone")
        .arg(url_string.to_str().unwrap())
        .arg(destination)
        .status()
        .map_err(|e| format!("Failed to execute git clone: {}", e))?;
    
    if status.success() {
        Ok(())
    } else {
        Err(format!("git clone exited with status: {}", status))
    }
}

// Example usage:
fn main() {
    let safe_url = "https://github.com/GitoxideLabs/gitoxide.git";
    let dangerous_url = "ssh://-malicious-host/repo.git";
    
    match clone_repository(safe_url, "gitoxide") {
        Ok(()) => println!("Successfully cloned repository"),
        Err(e) => println!("Error: {}", e),
    }
    
    match clone_repository(dangerous_url, "malicious-repo") {
        Ok(()) => println!("Successfully cloned repository"),
        Err(e) => println!("Error: {}", e),  // Should print the security error
    }
}
```

### 3. URL Canonicalization and Path Expansion

**Problem**: Repository URLs and paths can be specified in various formats, including relative paths and home directory references.

**Solution**: Use the path expansion and canonicalization features to standardize URLs for consistent handling.

```rust
use bstr::{BString, ByteSlice};
use gix_url::{parse, expand_path, Scheme};
use std::path::Path;

// Function to canonicalize various repo specifiers to absolute URLs
fn canonicalize_repo_specifier(repo_spec: &str) -> Result<String, String> {
    let bytes = repo_spec.as_bytes();
    
    // Check if it's a path with home directory references
    if repo_spec.starts_with('~') {
        // Parse the home directory reference
        let (user, adjusted_path) = gix_url::expand_path::parse(bytes.as_bstr())
            .map_err(|e| format!("Failed to parse path: {}", e))?;
        
        // Expand the path
        let expanded_path = expand_path(user.as_ref(), &adjusted_path)
            .map_err(|e| format!("Failed to expand path: {}", e))?;
        
        // Convert to a file URL
        let file_url = format!("file://{}", expanded_path.display());
        return Ok(file_url);
    }
    
    // Try to parse as a URL
    match parse(bytes.as_bstr()) {
        Ok(mut url) => {
            // For file URLs, make sure the path is absolute
            if url.scheme == Scheme::File {
                let current_dir = std::env::current_dir()
                    .map_err(|e| format!("Failed to get current directory: {}", e))?;
                
                url.canonicalize(&current_dir)
                    .map_err(|e| format!("Failed to canonicalize path: {}", e))?;
            }
            
            Ok(url.to_bstring().to_str().unwrap_or_default().to_string())
        }
        Err(_) => {
            // If it's not a valid URL, treat it as a local path
            let path = Path::new(repo_spec);
            
            // Convert relative paths to absolute
            let absolute_path = if path.is_relative() {
                std::env::current_dir()
                    .map_err(|e| format!("Failed to get current directory: {}", e))?
                    .join(path)
            } else {
                path.to_path_buf()
            };
            
            // Canonicalize the path (resolves symlinks, etc.)
            let canonical_path = absolute_path.canonicalize()
                .map_err(|e| format!("Failed to canonicalize path: {}", e))?;
            
            Ok(format!("file://{}", canonical_path.display()))
        }
    }
}

// Example usage:
fn main() {
    let examples = vec![
        "~/repos/gitoxide",
        "https://github.com/GitoxideLabs/gitoxide.git",
        "../relative/path/to/repo",
        "file:///absolute/path/to/repo",
        "user@host.com:path/to/repo.git",
    ];
    
    for example in examples {
        match canonicalize_repo_specifier(example) {
            Ok(canonical) => println!("{} -> {}", example, canonical),
            Err(e) => println!("{} -> Error: {}", example, e),
        }
    }
}
```

### 4. Building and Modifying Repository URLs

**Problem**: Applications need to programmatically construct or modify Git URLs, for instance when generating URLs for different protocols.

**Solution**: Use the URL modification methods to build and alter repository URLs dynamically.

```rust
use bstr::{BString, ByteSlice};
use gix_url::{parse, Scheme, Url};

// Function to convert a repository URL to different protocols
fn convert_repo_url(original_url_str: &str, target_scheme: Scheme) -> Result<String, String> {
    // Parse the original URL
    let original_url = parse(original_url_str.as_bytes().as_bstr())
        .map_err(|e| format!("Failed to parse URL: {}", e))?;
    
    // Extract components from the original URL
    let host = original_url.host().unwrap_or_default().to_string();
    let path = original_url.path.to_str().unwrap_or_default().to_string();
    let user = original_url.user().map(ToString::to_string);
    
    // Build a new URL with the target scheme
    let new_url = match target_scheme {
        Scheme::Http => {
            // HTTP URLs don't typically use authentication in the URL
            Url::from_parts(
                Scheme::Http,
                None,
                None,
                Some(host),
                None,
                path.into(),
                false,
            )
        }
        Scheme::Https => {
            // HTTPS URLs don't typically use authentication in the URL
            Url::from_parts(
                Scheme::Https,
                None,
                None,
                Some(host),
                None,
                path.into(),
                false,
            )
        }
        Scheme::Ssh => {
            // SSH URLs often use a username
            let ssh_user = user.or_else(|| Some("git".to_string()));
            Url::from_parts(
                Scheme::Ssh,
                ssh_user,
                None,
                Some(host),
                None,
                path.into(),
                true,  // Use SCP-like syntax
            )
        }
        Scheme::Git => {
            Url::from_parts(
                Scheme::Git,
                None,
                None,
                Some(host),
                None,
                path.into(),
                false,
            )
        }
        Scheme::File => {
            // File URLs don't need a host
            Url::from_parts(
                Scheme::File,
                None,
                None,
                None,
                None,
                path.into(),
                false,
            )
        }
        Scheme::Ext(proto) => {
            return Err(format!("Unsupported protocol: {}", proto));
        }
    }.map_err(|e| format!("Failed to create URL: {}", e))?;
    
    Ok(new_url.to_bstring().to_str().unwrap_or_default().to_string())
}

// Example usage:
fn main() {
    let original_url = "https://github.com/GitoxideLabs/gitoxide.git";
    
    // Convert to different protocols
    let protocols = vec![
        Scheme::Https,
        Scheme::Http,
        Scheme::Git,
        Scheme::Ssh,
    ];
    
    for protocol in protocols {
        match convert_repo_url(original_url, protocol.clone()) {
            Ok(new_url) => println!("{} -> {}", protocol, new_url),
            Err(e) => println!("{} -> Error: {}", protocol, e),
        }
    }
}
```

### 5. Working with Repository URIs in Configuration Files

**Problem**: Git configuration files often contain repository URLs that might be specified in different formats.

**Solution**: Parse and normalize repository URLs from configuration files for consistent handling.

```rust
use bstr::ByteSlice;
use gix_url::{parse, Scheme, Url};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, BufRead, BufReader};
use std::path::Path;

// Simplified representation of a remote configuration
struct RemoteConfig {
    name: String,
    urls: Vec<Url>,
    fetch_refspecs: Vec<String>,
    push_refspecs: Vec<String>,
}

// Parse Git config file for remote definitions
fn parse_git_config_remotes(config_path: &Path) -> Result<Vec<RemoteConfig>, io::Error> {
    let file = File::open(config_path)?;
    let reader = BufReader::new(file);
    
    let mut remotes = HashMap::new();
    let mut current_section = String::new();
    let mut current_remote = String::new();
    
    for line in reader.lines() {
        let line = line?;
        let trimmed = line.trim();
        
        // Parse section headers: [remote "origin"]
        if trimmed.starts_with('[') && trimmed.ends_with(']') {
            let section = &trimmed[1..trimmed.len() - 1];
            current_section = section.to_string();
            
            if section.starts_with("remote \"") && section.ends_with("\"") {
                current_remote = section[8..section.len() - 1].to_string();
                if !remotes.contains_key(&current_remote) {
                    remotes.insert(
                        current_remote.clone(),
                        RemoteConfig {
                            name: current_remote.clone(),
                            urls: Vec::new(),
                            fetch_refspecs: Vec::new(),
                            push_refspecs: Vec::new(),
                        },
                    );
                }
            }
        } 
        // Parse key-value pairs
        else if current_section.starts_with("remote \"") && trimmed.contains('=') {
            let parts: Vec<&str> = trimmed.splitn(2, '=').collect();
            if parts.len() == 2 {
                let key = parts[0].trim();
                let value = parts[1].trim();
                
                if let Some(remote) = remotes.get_mut(&current_remote) {
                    match key {
                        "url" => {
                            // Parse the URL
                            match parse(value.as_bytes().as_bstr()) {
                                Ok(url) => {
                                    remote.urls.push(url);
                                }
                                Err(e) => {
                                    eprintln!("Warning: Failed to parse URL '{}': {}", value, e);
                                }
                            }
                        }
                        "fetch" => {
                            remote.fetch_refspecs.push(value.to_string());
                        }
                        "pushurl" => {
                            // Parse the push URL
                            match parse(value.as_bytes().as_bstr()) {
                                Ok(url) => {
                                    remote.urls.push(url);
                                }
                                Err(e) => {
                                    eprintln!("Warning: Failed to parse pushURL '{}': {}", value, e);
                                }
                            }
                        }
                        "push" => {
                            remote.push_refspecs.push(value.to_string());
                        }
                        _ => {}
                    }
                }
            }
        }
    }
    
    Ok(remotes.into_values().collect())
}

// Format remote configurations for display
fn format_remote_config(remote: &RemoteConfig) -> String {
    let mut result = format!("Remote '{}':\n", remote.name);
    
    for (i, url) in remote.urls.iter().enumerate() {
        result.push_str(&format!("  URL {}: {}\n", i + 1, url));
        
        // Add details about the URL
        result.push_str(&format!("    Scheme: {}\n", url.scheme));
        if let Some(host) = url.host() {
            result.push_str(&format!("    Host: {}\n", host));
        }
        if let Some(user) = url.user() {
            result.push_str(&format!("    User: {}\n", user));
        }
        result.push_str(&format!("    Path: {}\n", url.path.to_str().unwrap_or("[non-UTF8]")));
    }
    
    if !remote.fetch_refspecs.is_empty() {
        result.push_str("  Fetch RefSpecs:\n");
        for refspec in &remote.fetch_refspecs {
            result.push_str(&format!("    {}\n", refspec));
        }
    }
    
    if !remote.push_refspecs.is_empty() {
        result.push_str("  Push RefSpecs:\n");
        for refspec in &remote.push_refspecs {
            result.push_str(&format!("    {}\n", refspec));
        }
    }
    
    result
}

// Example usage (with a mock config file)
fn main() -> io::Result<()> {
    // In a real application, you would use:
    // let config_path = Path::new(".git/config");
    
    // For demonstration, let's create a simple mock config
    let config_path = Path::new("mock_git_config");
    std::fs::write(config_path, r#"[remote "origin"]
    url = https://github.com/GitoxideLabs/gitoxide.git
    fetch = +refs/heads/*:refs/remotes/origin/*
[remote "upstream"]
    url = git@github.com:rust-lang/rust.git
    fetch = +refs/heads/*:refs/remotes/upstream/*
    push = refs/heads/main:refs/heads/main
[remote "local"]
    url = file:///path/to/local/repo
    fetch = +refs/heads/*:refs/remotes/local/*
"#)?;
    
    // Parse the config file
    let remotes = parse_git_config_remotes(config_path)?;
    
    // Display the parsed remotes
    for remote in remotes {
        println!("{}", format_remote_config(&remote));
    }
    
    // Clean up the mock file
    std::fs::remove_file(config_path)?;
    
    Ok(())
}
```

### 6. Implementing URI Transformation for Specialized Protocols

**Problem**: Custom transport protocols need to be registered and handled in a Git client.

**Solution**: Use the `Scheme::Ext` variant to support custom protocol schemes.

```rust
use bstr::ByteSlice;
use gix_url::{parse, Scheme, Url};
use std::collections::HashMap;
use std::io;

// A registry for custom protocol handlers
struct ProtocolRegistry {
    handlers: HashMap<String, Box<dyn Fn(&Url) -> io::Result<()>>>,
}

impl ProtocolRegistry {
    fn new() -> Self {
        Self {
            handlers: HashMap::new(),
        }
    }
    
    // Register a handler for a custom protocol
    fn register<F>(&mut self, protocol: &str, handler: F)
    where
        F: Fn(&Url) -> io::Result<()> + 'static,
    {
        self.handlers.insert(protocol.to_string(), Box::new(handler));
    }
    
    // Handle a URL based on its scheme
    fn handle_url(&self, url_str: &str) -> io::Result<()> {
        let url = parse(url_str.as_bytes().as_bstr())
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidInput, format!("Invalid URL: {}", e)))?;
        
        match &url.scheme {
            Scheme::Ext(protocol) => {
                if let Some(handler) = self.handlers.get(protocol) {
                    handler(&url)
                } else {
                    Err(io::Error::new(
                        io::ErrorKind::Unsupported,
                        format!("Unsupported protocol: {}", protocol),
                    ))
                }
            }
            _ => {
                Err(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    format!("Expected a custom protocol, got: {}", url.scheme),
                ))
            }
        }
    }
}

// Example implementation for custom protocols
fn main() -> io::Result<()> {
    // Create and configure the protocol registry
    let mut registry = ProtocolRegistry::new();
    
    // Register a handler for a custom "s3" protocol
    registry.register("s3", |url| {
        println!("Handling S3 URL: {}", url.to_bstring().to_str().unwrap_or("[non-UTF8]"));
        println!("  Bucket: {}", url.host().unwrap_or("unknown"));
        println!("  Key: {}", url.path.to_str().unwrap_or("[non-UTF8]"));
        Ok(())
    });
    
    // Register a handler for a custom "database" protocol
    registry.register("database", |url| {
        println!("Handling Database URL: {}", url.to_bstring().to_str().unwrap_or("[non-UTF8]"));
        println!("  Host: {}", url.host().unwrap_or("localhost"));
        println!("  Path: {}", url.path.to_str().unwrap_or("[non-UTF8]"));
        if let Some(user) = url.user() {
            println!("  User: {}", user);
        }
        Ok(())
    });
    
    // Test with some custom URLs
    let test_urls = vec![
        "s3://my-bucket/path/to/repo.git",
        "database://db.example.com/gitoxide/repos",
        "database://user:password@db.example.com/secured/repos",
        "unsupported://example.com/repo.git",
    ];
    
    for url_str in test_urls {
        println!("\nTrying URL: {}", url_str);
        match registry.handle_url(url_str) {
            Ok(()) => println!("Successfully handled URL"),
            Err(e) => println!("Error: {}", e),
        }
    }
    
    Ok(())
}
```

These use cases demonstrate how `gix-url` can be employed for various Git-related tasks, from parsing and validating URLs to handling custom protocols and ensuring secure command-line usage of URL components.