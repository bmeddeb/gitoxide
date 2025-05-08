# gix-credentials Use Cases

This document outlines practical applications of the `gix-credentials` crate, demonstrating how it can be used to solve various Git credential management challenges.

## Intended Audience

- **Git Client Developers**: Implementing Git clients that need to authenticate with remote repositories
- **Credential Helper Authors**: Creating custom credential storage solutions
- **Git Tools Developers**: Building utilities that interact with Git repositories and need authentication

## Use Case: Seamless Authentication in a Git Client

### Problem

When implementing a Git client application, you need to handle authentication to remote repositories without prompting users for credentials every time they perform an operation.

### Solution

```rust
use gix_credentials::{builtin, helper, protocol::Context};
use gix_url::parse;
use std::error::Error;

/// Authenticate a request to a Git repository URL
fn authenticate_git_request(repo_url: &str) -> Result<gix_sec::identity::Account, Box<dyn Error>> {
    // Parse the URL to get protocol, host, path
    let parsed_url = parse(repo_url)?;
    
    // Create a context with URL components
    let mut context = Context::default();
    context.url = Some(repo_url.into());
    context.protocol = parsed_url.scheme.map(|s| s.to_string());
    context.host = parsed_url.host.map(|h| h.to_string());
    context.path = parsed_url.path;
    
    // Create a Get action with this context
    let action = helper::Action::Get(context);
    
    // Try to get credentials from Git's built-in credential helper
    match builtin(action)? {
        Some(outcome) => {
            // Store the credentials for future use if they work
            // (This would be called after confirming they actually work)
            Ok(outcome.identity)
        },
        None => Err("No credentials found".into()),
    }
}

/// Example of using the authentication function
fn perform_git_operation(repo_url: &str) -> Result<(), Box<dyn Error>> {
    // Get credentials
    let credentials = authenticate_git_request(repo_url)?;
    
    println!(
        "Authenticated as {} with password of length {}",
        credentials.username,
        credentials.password.len()
    );
    
    // Use credentials for Git operations...
    
    Ok(())
}
```

This approach:
1. Seamlessly gets credentials from the user's configured credential helpers
2. Works with any helper the user has configured (store, cache, etc.)
3. Handles credential parsing and formatting
4. Can be integrated into any Git operation that requires authentication

## Use Case: Implementing a Custom Credential Helper

### Problem

You need to implement a custom credential helper that integrates with a specific password manager or authentication system not supported by Git's built-in helpers.

### Solution

```rust
use gix_credentials::{program, protocol};
use std::{fs, io, path::Path};
use serde::{Serialize, Deserialize};

// A simple credential store in a JSON file
#[derive(Serialize, Deserialize, Default)]
struct CredentialStore {
    credentials: Vec<StoredCredential>,
}

#[derive(Serialize, Deserialize)]
struct StoredCredential {
    protocol: Option<String>,
    host: Option<String>,
    path: Option<String>,
    username: String,
    password: String,
}

impl CredentialStore {
    fn load(path: &Path) -> Self {
        fs::read_to_string(path)
            .map(|data| serde_json::from_str(&data).unwrap_or_default())
            .unwrap_or_default()
    }
    
    fn save(&self, path: &Path) -> io::Result<()> {
        let json = serde_json::to_string_pretty(self)?;
        fs::write(path, json)
    }
    
    fn find(&self, ctx: &protocol::Context) -> Option<(&str, &str)> {
        for cred in &self.credentials {
            if matches_context(cred, ctx) {
                return Some((&cred.username, &cred.password));
            }
        }
        None
    }
    
    fn add(&mut self, ctx: &protocol::Context) -> bool {
        if let (Some(username), Some(password)) = (&ctx.username, &ctx.password) {
            self.credentials.push(StoredCredential {
                protocol: ctx.protocol.clone(),
                host: ctx.host.clone(),
                path: ctx.path.as_ref().map(|p| String::from_utf8_lossy(p).to_string()),
                username: username.clone(),
                password: password.clone(),
            });
            true
        } else {
            false
        }
    }
    
    fn remove(&mut self, ctx: &protocol::Context) -> bool {
        let len = self.credentials.len();
        self.credentials.retain(|cred| !matches_context(cred, ctx));
        self.credentials.len() < len
    }
}

fn matches_context(cred: &StoredCredential, ctx: &protocol::Context) -> bool {
    // Protocol must match if specified
    if let Some(ref proto) = ctx.protocol {
        if cred.protocol.as_deref() != Some(proto) {
            return false;
        }
    }
    
    // Host must match if specified
    if let Some(ref host) = ctx.host {
        if cred.host.as_deref() != Some(host) {
            return false;
        }
    }
    
    // Path must match if specified
    if let Some(ref path) = ctx.path {
        let path_str = String::from_utf8_lossy(path);
        if cred.path.as_deref() != Some(&path_str) {
            return false;
        }
    }
    
    true
}

fn main() -> Result<(), program::main::Error> {
    // Path to credentials storage
    let store_path = dirs::home_dir()
        .unwrap_or_default()
        .join(".git-credentials-json");
    
    // Run the credential helper
    program::main(
        std::env::args_os().skip(1),
        io::stdin(),
        io::stdout(),
        move |action, context| {
            let mut store = CredentialStore::load(&store_path);
            
            match action {
                program::main::Action::Get => {
                    if let Some((username, password)) = store.find(&context) {
                        // Return credentials if found
                        Ok(Some(protocol::Context {
                            username: Some(username.to_string()),
                            password: Some(password.to_string()),
                            ..context
                        }))
                    } else {
                        // No credentials found
                        Ok(None)
                    }
                },
                program::main::Action::Store => {
                    // Store credentials
                    if store.add(&context) {
                        store.save(&store_path)?;
                    }
                    Ok(None)
                },
                program::main::Action::Erase => {
                    // Erase credentials
                    if store.remove(&context) {
                        store.save(&store_path)?;
                    }
                    Ok(None)
                },
            }
        },
    )
}
```

This implementation:
1. Creates a file-based credential storage system
2. Handles the full Git credential protocol
3. Properly matches credential contexts
4. Can be installed as `git-credential-json` for Git to use

## Use Case: Interactive Authentication with Fallbacks

### Problem

Your application needs to authenticate with Git repositories, but you want to try multiple methods and fall back to interactive prompting if needed.

### Solution

```rust
use gix_credentials::{helper, Program, protocol::Context};
use gix_prompt::Options;
use std::error::Error;

/// Try multiple authentication methods in sequence
fn authenticate_with_fallbacks(
    repo_url: &str
) -> Result<gix_sec::identity::Account, Box<dyn Error>> {
    // Create a cascade of authentication methods
    let mut cascade = helper::Cascade::default();
    
    // 1. Try environment variables if available
    if std::env::var("GIT_USERNAME").is_ok() && std::env::var("GIT_PASSWORD").is_ok() {
        cascade.programs.push(
            Program::from_custom_definition("!f() { echo username=$GIT_USERNAME; echo password=$GIT_PASSWORD; }; f")
        );
    }
    
    // 2. Try a custom credential store
    cascade.programs.push(
        Program::from_custom_definition("custom-store")
    );
    
    // 3. Fall back to built-in Git credential helper
    cascade.programs.push(
        Program::from_kind(gix_credentials::program::Kind::Builtin)
    );
    
    // Create prompt options for interactive fallback
    let prompt_options = Options::default()
        .apply_environment(true, true, true)
        .allow_terminal(true);
    
    // Create the action with the URL
    let action = helper::Action::get_for_url(repo_url);
    
    // Try the cascade
    match cascade.invoke(action, prompt_options)? {
        Some(mut outcome) => {
            // Extract the identity if we got one
            if let Some(identity) = outcome.consume_identity() {
                return Ok(identity);
            }
            
            // If we got here, we might have gotten a partial result
            // (like only username), or the helper might have indicated to quit
            if outcome.quit {
                return Err("Authentication cancelled".into());
            }
            
            Err("Couldn't get complete credentials".into())
        },
        None => Err("No credentials available".into()),
    }
}
```

This approach:
1. Tries multiple credential sources in order
2. Includes environment variables as a credential source
3. Falls back to Git's configured helpers
4. Handles interactive prompting if needed
5. Properly processes "quit" signals from helpers

## Use Case: Smart SSH Key Selection

### Problem

Your application needs to select the appropriate SSH key for different Git repositories, perhaps using different keys for different organizations or projects.

### Solution

```rust
use gix_credentials::{helper, Program, protocol};
use std::{fs, path::PathBuf};

/// Create a custom credential helper that selects SSH keys based on host patterns
fn main() -> Result<(), gix_credentials::program::main::Error> {
    let ssh_config = load_ssh_key_config();
    
    gix_credentials::program::main(
        std::env::args_os().skip(1),
        std::io::stdin(),
        std::io::stdout(),
        move |action, context| {
            match action {
                gix_credentials::program::main::Action::Get => {
                    // Only handle SSH protocol
                    if context.protocol.as_deref() != Some("ssh") {
                        return Ok(None);
                    }
                    
                    // Find SSH key for this host
                    if let Some(host) = &context.host {
                        if let Some(key_path) = find_ssh_key_for_host(&ssh_config, host) {
                            // Git expects the private key path in the password field
                            // for SSH authentication
                            return Ok(Some(protocol::Context {
                                username: context.username,
                                password: Some(key_path.to_string_lossy().to_string()),
                                ..context
                            }));
                        }
                    }
                    
                    // No matching key found
                    Ok(None)
                },
                // We don't handle storing or erasing SSH keys
                _ => Ok(None),
            }
        },
    )
}

// Types for SSH key configuration
struct SshKeyConfig {
    patterns: Vec<SshKeyPattern>,
}

struct SshKeyPattern {
    host_pattern: String,
    key_path: PathBuf,
}

fn load_ssh_key_config() -> SshKeyConfig {
    // In a real application, this would load from a config file
    // Here we're just creating a sample configuration
    SshKeyConfig {
        patterns: vec![
            SshKeyPattern {
                host_pattern: "github.com".to_string(),
                key_path: PathBuf::from("~/.ssh/github_key"),
            },
            SshKeyPattern {
                host_pattern: "gitlab.com".to_string(),
                key_path: PathBuf::from("~/.ssh/gitlab_key"),
            },
            // You could add patterns with wildcards
            SshKeyPattern {
                host_pattern: "*.work.com".to_string(),
                key_path: PathBuf::from("~/.ssh/work_key"),
            },
        ],
    }
}

fn find_ssh_key_for_host(config: &SshKeyConfig, host: &str) -> Option<PathBuf> {
    for pattern in &config.patterns {
        if host_matches_pattern(host, &pattern.host_pattern) {
            // Expand ~ in the path
            let path_str = pattern.key_path.to_string_lossy();
            if path_str.starts_with("~/") {
                if let Some(home) = dirs::home_dir() {
                    let expanded = home.join(&path_str[2..]);
                    return Some(expanded);
                }
            }
            return Some(pattern.key_path.clone());
        }
    }
    None
}

fn host_matches_pattern(host: &str, pattern: &str) -> bool {
    if pattern.starts_with("*.") {
        // Wildcard pattern like "*.example.com"
        let suffix = &pattern[1..]; // Remove the *
        host.ends_with(suffix)
    } else {
        // Exact match
        host == pattern
    }
}
```

This credential helper:
1. Only handles SSH protocol URLs
2. Selects different SSH keys based on hostname patterns
3. Returns the key path in the password field, as Git expects
4. Supports organization-specific keys

## Use Case: Secure Cloud-based Credential Storage

### Problem

You want to store Git credentials securely in the cloud, synchronized across devices, but with local caching for offline use.

### Solution

```rust
use gix_credentials::{program, protocol, helper};
use std::{fs, io, path::PathBuf, time::{Duration, SystemTime}};
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Default)]
struct CloudCredentialCache {
    credentials: Vec<CachedCredential>,
}

#[derive(Serialize, Deserialize)]
struct CachedCredential {
    protocol: Option<String>,
    host: Option<String>,
    path: Option<String>,
    username: String,
    password: String,
    // When this cache entry expires
    expires_at: SystemTime,
}

impl CloudCredentialCache {
    fn load(path: &PathBuf) -> Self {
        fs::read_to_string(path)
            .map(|data| serde_json::from_str(&data).unwrap_or_default())
            .unwrap_or_default()
    }
    
    fn save(&self, path: &PathBuf) -> io::Result<()> {
        let json = serde_json::to_string_pretty(self)?;
        fs::write(path, json)
    }
    
    fn find(&mut self, ctx: &protocol::Context) -> Option<(&str, &str)> {
        // Remove expired entries
        let now = SystemTime::now();
        self.credentials.retain(|cred| cred.expires_at > now);
        
        // Find matching credential
        for cred in &self.credentials {
            if matches_context(cred, ctx) {
                return Some((&cred.username, &cred.password));
            }
        }
        None
    }
    
    fn add(&mut self, ctx: &protocol::Context, ttl: Duration) {
        if let (Some(username), Some(password)) = (&ctx.username, &ctx.password) {
            let expires_at = SystemTime::now() + ttl;
            
            // Remove any existing entry
            self.credentials.retain(|cred| !matches_context(cred, ctx));
            
            // Add new entry
            self.credentials.push(CachedCredential {
                protocol: ctx.protocol.clone(),
                host: ctx.host.clone(),
                path: ctx.path.as_ref().map(|p| String::from_utf8_lossy(p).to_string()),
                username: username.clone(),
                password: password.clone(),
                expires_at,
            });
        }
    }
    
    fn remove(&mut self, ctx: &protocol::Context) -> bool {
        let len = self.credentials.len();
        self.credentials.retain(|cred| !matches_context(cred, ctx));
        self.credentials.len() < len
    }
}

fn matches_context(cred: &CachedCredential, ctx: &protocol::Context) -> bool {
    // Protocol must match if specified
    if let Some(ref proto) = ctx.protocol {
        if cred.protocol.as_deref() != Some(proto) {
            return false;
        }
    }
    
    // Host must match if specified
    if let Some(ref host) = ctx.host {
        if cred.host.as_deref() != Some(host) {
            return false;
        }
    }
    
    // Path must match if specified
    if let Some(ref path) = ctx.path {
        let path_str = String::from_utf8_lossy(path);
        if cred.path.as_deref() != Some(&path_str) {
            return false;
        }
    }
    
    true
}

// In a real implementation, this would communicate with a cloud service
fn fetch_from_cloud(ctx: &protocol::Context) -> Option<(String, String)> {
    // Simulate cloud API call...
    None
}

fn store_in_cloud(ctx: &protocol::Context) -> bool {
    // Simulate cloud API call...
    true
}

fn main() -> Result<(), program::main::Error> {
    // Path to local cache
    let cache_path = dirs::cache_dir()
        .unwrap_or_default()
        .join("git-cloud-credentials.json");
    
    // Cache TTL (24 hours)
    let cache_ttl = Duration::from_secs(24 * 60 * 60);
    
    program::main(
        std::env::args_os().skip(1),
        io::stdin(),
        io::stdout(),
        move |action, context| {
            let mut cache = CloudCredentialCache::load(&cache_path);
            
            match action {
                program::main::Action::Get => {
                    // First try the local cache
                    if let Some((username, password)) = cache.find(&context) {
                        return Ok(Some(protocol::Context {
                            username: Some(username.to_string()),
                            password: Some(password.to_string()),
                            ..context
                        }));
                    }
                    
                    // If not in cache, try to fetch from cloud
                    if let Some((username, password)) = fetch_from_cloud(&context) {
                        // Add to local cache
                        let mut ctx_with_creds = context.clone();
                        ctx_with_creds.username = Some(username.clone());
                        ctx_with_creds.password = Some(password.clone());
                        cache.add(&ctx_with_creds, cache_ttl);
                        cache.save(&cache_path)?;
                        
                        return Ok(Some(protocol::Context {
                            username: Some(username),
                            password: Some(password),
                            ..context
                        }));
                    }
                    
                    // No credentials found
                    Ok(None)
                },
                program::main::Action::Store => {
                    // Store in both cloud and local cache
                    if store_in_cloud(&context) {
                        cache.add(&context, cache_ttl);
                        cache.save(&cache_path)?;
                    }
                    Ok(None)
                },
                program::main::Action::Erase => {
                    // Remove from cloud and local cache
                    store_in_cloud(&context); // This would be a deletion API call
                    cache.remove(&context);
                    cache.save(&cache_path)?;
                    Ok(None)
                },
            }
        },
    )
}
```

This credential helper:
1. Maintains a local cache with TTL for offline use
2. Syncs credentials with a cloud service
3. Follows Git credential helper protocols
4. Handles credential expiration
5. Supports both storing and erasing credentials

## Use Case: Multi-Factor Authentication Support

### Problem

Some Git hosting services require multi-factor authentication (MFA) in addition to username/password credentials, but Git credential helpers don't natively support this.

### Solution

```rust
use gix_credentials::{program, protocol};
use gix_prompt::Options;
use std::{collections::HashMap, fs, io, path::PathBuf, time::{Duration, SystemTime}};
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Default)]
struct TokenStore {
    tokens: HashMap<String, TokenEntry>,
}

#[derive(Serialize, Deserialize)]
struct TokenEntry {
    token: String,
    expires_at: SystemTime,
}

impl TokenStore {
    fn load(path: &PathBuf) -> Self {
        fs::read_to_string(path)
            .map(|data| serde_json::from_str(&data).unwrap_or_default())
            .unwrap_or_default()
    }
    
    fn save(&self, path: &PathBuf) -> io::Result<()> {
        let json = serde_json::to_string_pretty(self)?;
        fs::write(path, json)
    }
    
    fn get_key(ctx: &protocol::Context) -> Option<String> {
        let mut key = String::new();
        
        if let Some(ref proto) = ctx.protocol {
            key.push_str(proto);
            key.push(':');
        }
        
        if let Some(ref host) = ctx.host {
            key.push_str(host);
            key.push(':');
        }
        
        if let Some(ref username) = ctx.username {
            key.push_str(username);
            return Some(key);
        }
        
        None
    }
    
    fn get_token(&mut self, ctx: &protocol::Context) -> Option<String> {
        let key = Self::get_key(ctx)?;
        
        // Remove expired tokens
        let now = SystemTime::now();
        self.tokens.retain(|_, entry| entry.expires_at > now);
        
        // Return token if exists
        self.tokens.get(&key).map(|entry| entry.token.clone())
    }
    
    fn store_token(&mut self, ctx: &protocol::Context, token: String, ttl: Duration) -> bool {
        if let Some(key) = Self::get_key(ctx) {
            let expires_at = SystemTime::now() + ttl;
            self.tokens.insert(key, TokenEntry { token, expires_at });
            true
        } else {
            false
        }
    }
    
    fn remove_token(&mut self, ctx: &protocol::Context) -> bool {
        if let Some(key) = Self::get_key(ctx) {
            self.tokens.remove(&key).is_some()
        } else {
            false
        }
    }
}

fn main() -> Result<(), program::main::Error> {
    // Path to token store
    let token_path = dirs::cache_dir()
        .unwrap_or_default()
        .join("git-mfa-tokens.json");
    
    // Token TTL (8 hours)
    let token_ttl = Duration::from_secs(8 * 60 * 60);
    
    // Prompt options
    let prompt_options = Options::default()
        .apply_environment(true, true, true)
        .allow_terminal(true);
    
    program::main(
        std::env::args_os().skip(1),
        io::stdin(),
        io::stdout(),
        move |action, mut context| {
            let mut store = TokenStore::load(&token_path);
            
            match action {
                program::main::Action::Get => {
                    // If we already have a username but no password, check for a token
                    if context.username.is_some() && context.password.is_none() {
                        if let Some(token) = store.get_token(&context) {
                            return Ok(Some(protocol::Context {
                                password: Some(token),
                                ..context
                            }));
                        }
                    }
                    
                    // Try to delegate to the built-in helpers first
                    let builtin_ctx = helper_cascade_get(&context)?;
                    
                    if let Some(mut ctx) = builtin_ctx {
                        // We got credentials from the builtin helper
                        if let (Some(username), Some(password)) = (&ctx.username, &ctx.password) {
                            // Check if these credentials need MFA
                            let needs_mfa = check_if_needs_mfa(username, password, &context);
                            
                            if needs_mfa {
                                // Prompt for MFA code
                                let mfa_code = gix_prompt::password(
                                    "Enter MFA code: ",
                                    prompt_options.clone(),
                                )?;
                                
                                // Generate a token using the username, password and MFA code
                                if let Some(token) = generate_token(username, password, &mfa_code, &context) {
                                    // Store the token
                                    store.store_token(&ctx, token.clone(), token_ttl);
                                    store.save(&token_path)?;
                                    
                                    // Return the token as password
                                    ctx.password = Some(token);
                                    return Ok(Some(ctx));
                                }
                            } else {
                                // No MFA needed, just return the credentials
                                return Ok(Some(ctx));
                            }
                        }
                    }
                    
                    // Failed to get credentials or MFA token
                    Ok(None)
                },
                program::main::Action::Store => {
                    // If this is a token, store it
                    if let (Some(username), Some(token)) = (&context.username, &context.password) {
                        if is_token(token) {
                            store.store_token(&context, token.clone(), token_ttl);
                            store.save(&token_path)?;
                            return Ok(None);
                        }
                    }
                    
                    // Otherwise delegate to the builtin helper
                    helper_cascade_store(&context)
                },
                program::main::Action::Erase => {
                    // Remove any token
                    store.remove_token(&context);
                    store.save(&token_path)?;
                    
                    // Also delegate to the builtin helper
                    helper_cascade_erase(&context)
                },
            }
        },
    )
}

// Helper functions (simplified for this example)

fn helper_cascade_get(context: &protocol::Context) -> io::Result<Option<protocol::Context>> {
    // Create a cascade with builtin helper
    let mut cascade = gix_credentials::helper::Cascade::default();
    cascade.programs.push(
        gix_credentials::Program::from_kind(gix_credentials::program::Kind::Builtin)
    );
    
    // Create a Get action
    let mut action = context.clone();
    let result = cascade.invoke(
        gix_credentials::helper::Action::Get(action),
        gix_prompt::Options::default().apply_environment(true, true, true)
    )?;
    
    if let Some(outcome) = result {
        let next = outcome.next;
        (&next).try_into().map_err(|e| io::Error::new(io::ErrorKind::Other, e)).map(Some)
    } else {
        Ok(None)
    }
}

fn helper_cascade_store(context: &protocol::Context) -> io::Result<Option<protocol::Context>> {
    let mut cascade = gix_credentials::helper::Cascade::default();
    cascade.programs.push(
        gix_credentials::Program::from_kind(gix_credentials::program::Kind::Builtin)
    );
    
    let mut buf = Vec::<u8>::new();
    context.write_to(&mut buf)?;
    cascade.invoke(
        gix_credentials::helper::Action::Store(buf.into()),
        Default::default(),
    )?;
    
    Ok(None)
}

fn helper_cascade_erase(context: &protocol::Context) -> io::Result<Option<protocol::Context>> {
    let mut cascade = gix_credentials::helper::Cascade::default();
    cascade.programs.push(
        gix_credentials::Program::from_kind(gix_credentials::program::Kind::Builtin)
    );
    
    let mut buf = Vec::<u8>::new();
    context.write_to(&mut buf)?;
    cascade.invoke(
        gix_credentials::helper::Action::Erase(buf.into()),
        Default::default(),
    )?;
    
    Ok(None)
}

fn check_if_needs_mfa(username: &str, password: &str, context: &protocol::Context) -> bool {
    // In a real implementation, this might make an API call to check if MFA is required
    // Here we just assume GitHub always needs MFA
    context.host.as_deref() == Some("github.com")
}

fn generate_token(username: &str, password: &str, mfa_code: &str, context: &protocol::Context) -> Option<String> {
    // In a real implementation, this would make an API call to generate a token
    // using the username, password, and MFA code
    Some(format!("generated-token-{}-{}", username, mfa_code))
}

fn is_token(password: &str) -> bool {
    // In a real implementation, this would check if the password is a token
    // based on its format
    password.starts_with("generated-token-")
}
```

This approach:
1. Handles MFA requirements for Git hosting services
2. Caches authentication tokens with TTL
3. Delegates to built-in helpers for initial authentication
4. Prompts for MFA codes when needed
5. Integrates with the Git credential helper system

These use cases demonstrate the flexibility of the `gix-credentials` crate for handling a wide range of Git authentication scenarios.