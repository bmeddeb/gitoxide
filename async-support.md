# Async Support in Gitoxide

Gitoxide provides support for asynchronous operations, particularly for network operations like cloning, fetching, and pushing. This document explains how to enable and use the async features of gitoxide.

## Async Feature Flags

Gitoxide supports both blocking and async networking models, but they are mutually exclusive. The primary async feature flags include:

### Main Async Features

- **`async-network-client`**: Basic async client support for protocols like git://
- **`async-network-client-async-std`**: Integration with async-std runtime for async operations

### Blocking Features (for comparison)

- **`blocking-network-client`**: Blocking client for file://, git://, and ssh:// transports
- **`blocking-http-transport-curl`**: HTTP/S support using curl
- **`blocking-http-transport-reqwest`**: HTTP/S support using reqwest

## Required Crates for Async Support

When using async features, you will need:

1. **Core async requirements:**
   - `futures-lite`: For Future-related functionality
   - A runtime like `async-std` or `tokio`

2. **Protocol and transport support:**
   - `gix-protocol` with async features
   - `gix-transport` with appropriate async features

## Example: Enabling Async Support in Your Project

```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["async-network-client", "comfort"] }
async-std = { version = "1.12.0", features = ["attributes"] }
futures-lite = "2.1.0"
```

## Async Clone Example

```rust
use std::path::Path;
use async_std::task;
use futures_lite::future::FutureExt;

async fn clone_repo_async(url: &str, path: impl AsRef<Path>) -> Result<(), Box<dyn std::error::Error>> {
    // Parse the URL
    let url = gix::url::parse(url)?;
    
    // Create a progress handler
    let progress = gix::progress::Discard;
    
    // Prepare clone operation
    let mut prepare_clone = gix::prepare_clone(url, path)?;
    
    // You would need the async variant of fetch operation
    // Note that the API is marked with `maybe_async`, meaning it works in both sync and async contexts
    let (repo, _) = prepare_clone.fetch_only(progress, &gix::interrupt::IS_INTERRUPTED).await?;
    
    println!("Repository cloned successfully");
    Ok(())
}

// Usage in async context:
// task::block_on(clone_repo_async("https://github.com/example/repo.git", "./my-repo"));
```

## Important Notes on Async Support

1. **Limited Transport Support**: The async implementation currently has more limited transport support than the blocking version. It primarily supports:
   - `git://` protocol
   - Limited HTTP support

2. **Mutual Exclusivity**: You cannot enable both `async-network-client` and `blocking-network-client` features at the same time.

3. **`maybe_async` API Design**: Many APIs are marked with `maybe_async`, allowing them to work in both blocking and async contexts based on the feature flags enabled.

4. **Performance Considerations**: The async implementation may still perform blocking operations under the hood for certain tasks, so it should be run in a runtime that can handle blocking futures.

5. **Runtime Selection**: You must choose which async runtime to use (typically async-std or tokio) and enable the appropriate feature flags.

## Using Direct Source Copy with Async Features

If you're using the direct source copy approach mentioned in the extraction guide, you'll need to modify the `Cargo.toml` files of the copied crates to enable the async features:

```toml
# Example for gix-protocol/Cargo.toml
[features]
async-client = ["dep:futures-io", "dep:futures-lite"]
```

You'll also need to ensure that all interdependent crates have their async features properly configured.

## Recommended Approach for Async Usage

For most users who need async clone functionality, the recommended approach is:

1. Use feature flags through Cargo's dependency system rather than direct source copy
2. Enable only the specific async features you need
3. Choose an async runtime and ensure it's properly configured

Example minimal Cargo.toml for async clone functionality:

```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = [
    "async-network-client",
    "comfort"
]}
async-std = { version = "1.12.0", features = ["attributes"] }
futures-lite = "2.1.0"
```

This will give you a functional async git client with the ability to clone repositories using the git:// protocol.