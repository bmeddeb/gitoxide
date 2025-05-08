# Gitoxide Extraction Guide

This guide outlines how to extract specific functionality from the gitoxide library. We focus on the core analysis tools we identified in the `gitoxide-analysis-tools.md` document.

## Required Crates by Feature

### 1. Repository Cloning

**Core crates needed:**
- `gix` (with `blocking-network-client` feature)
- `gix-url`
- `gix-protocol`
- `gix-features` (for progress reporting)

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["blocking-network-client", "comfort"] }
```

### 2. Repository Log

**Core crates needed:**
- `gix` (with `revision` feature)
- `gix-revision`
- `gix-hash`
- `gix-object`
- `gix-traverse`

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["revision"] }
```

### 3. Diff Analysis

**Core crates needed:**
- `gix-diff`
- `gix` (with `blob-diff` feature)
- `gix-hash`
- `gix-object`

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["blob-diff"] }
gix-diff = { version = "0.47.1", features = ["blob", "tree"] }
```

### 4. Blame Analysis

**Core crates needed:**
- `gix-blame`
- `gix-hash`
- `gix-object`

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["blame"] }
gix-blame = { version = "0.47.1" }
```

### 5. Status Analysis

**Core crates needed:**
- `gix-status`
- `gix` (with `status` feature)
- `gix-index`

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["status"] }
gix-status = { version = "0.47.1" }
```

### 6. Branch Handling

**Core crates needed:**
- `gix-ref`
- `gix` (with basic features)
- `gix-object`

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["basic"] }
gix-ref = { version = "0.47.1" }
```

### 7. Remote Operations

**Core crates needed:**
- `gix` (with `blocking-network-client` feature)
- `gix-protocol`
- `gix-url`
- `gix-transport`

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["blocking-network-client"] }
```

### 8. Author Information

**Core crates needed:**
- `gix-actor`
- `gix-date`

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["basic"] }
gix-actor = { version = "0.47.1" }
```

### 9. Async Support

**Core crates needed:**
- `gix` (with `async-network-client` feature)
- `gix-protocol` (with async features)
- `gix-transport` (with async features)
- `futures-lite`
- An async runtime like `async-std` or `tokio`

**Feature flags to enable:**
```toml
[dependencies]
gix = { version = "0.72.1", default-features = false, features = ["async-network-client"] }
futures-lite = "2.1.0"
async-std = { version = "1.12.0", features = ["attributes"] }
```

## Extraction Steps

To extract only the needed functionality from gitoxide, follow these steps:

1. **Create a new Cargo project:**
   ```bash
   cargo new my-git-tools
   cd my-git-tools
   ```

2. **Add dependencies to Cargo.toml:**
   Choose the specific features you need from the lists above. For example, if you need cloning and log functionality:
   ```toml
   [dependencies]
   gix = { version = "0.72.1", default-features = false, features = ["blocking-network-client", "revision", "comfort"] }
   ```

3. **Optimize dependencies:**
   If you need multiple features, consolidate them:
   ```toml
   [dependencies]
   gix = { version = "0.72.1", default-features = false, features = [
     "blocking-network-client",  # For cloning and remote operations
     "revision",                # For log functionality
     "blob-diff",               # For diff functionality
     "blame",                   # For blame analysis
     "status"                   # For status analysis
   ]}
   ```

4. **Create a minimal build:**
   If you only need specific functionality (like just log and diff), you can limit the features to just those components.

## Example: Creating a Minimal Cloning and Log Tool

```rust
use std::path::PathBuf;
use anyhow::Result;

fn main() -> Result<()> {
    // Parse command line args (simplified example)
    let args: Vec<String> = std::env::args().collect();
    
    if args.len() < 2 {
        println!("Usage: {} [clone|log] [args...]", args[0]);
        return Ok(());
    }
    
    match args[1].as_str() {
        "clone" => {
            if args.len() < 4 {
                println!("Usage: {} clone <repo_url> <destination>", args[0]);
                return Ok(());
            }
            clone_repo(&args[2], &args[3])
        }
        "log" => {
            if args.len() < 3 {
                println!("Usage: {} log <repo_path>", args[0]);
                return Ok(());
            }
            show_log(&args[2])
        }
        _ => {
            println!("Unknown command: {}", args[1]);
            Ok(())
        }
    }
}

fn clone_repo(repo_url: &str, destination: &str) -> Result<()> {
    // Parse the URL
    let url = gix::url::parse(repo_url)?;
    
    // Create a progress handler
    let progress = gix::progress::Discard;
    
    // Prepare clone operation
    let mut prepare_clone = gix::prepare_clone(url, destination)?;
    
    // Perform fetch then checkout
    let (mut prepare_checkout, _) = prepare_clone.fetch_then_checkout(
        progress,
        &gix::interrupt::IS_INTERRUPTED
    )?;
    
    // Create the main worktree
    let (_repo, _) = prepare_checkout.main_worktree(
        progress, 
        &gix::interrupt::IS_INTERRUPTED
    )?;
    
    println!("Repository cloned successfully to {}", destination);
    Ok(())
}

fn show_log(repo_path: &str) -> Result<()> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the HEAD commit
    let head = repo.head()?;
    let head_commit = head.peel_to_commit_in_place()?;
    
    // Set up the revision walker
    let log_entries = repo.rev_walk([head_commit.id])
        .sorting(gix::revision::walk::Sorting::ByCommitTime(Default::default()))
        .all()?
        .map_while(Result::ok)
        .take(10);  // Only show 10 most recent commits
    
    // Print the log entries
    for (i, info) in log_entries.enumerate() {
        // Get the commit object
        let commit = info.object()?;
        let commit_obj = commit.decode()?;
        
        // Format and print the commit info
        println!("Commit: {}", info.id);
        println!("Author: {}", commit_obj.author.name);
        println!("Date:   {}", commit_obj.author.time?.format(gix::date::time::format::DEFAULT));
        println!("Message:\n{}\n", commit_obj.message);
    }
    
    Ok(())
}
```

## Example: Async Clone Implementation

If you need to use async features for clone operations:

```rust
use std::path::Path;
use async_std::task;
use futures_lite::future::FutureExt;
use anyhow::Result;

async fn clone_repo_async(url: &str, path: impl AsRef<Path>) -> Result<()> {
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

fn main() -> Result<()> {
    // Block on the async operation to run it from a sync context
    task::block_on(clone_repo_async("https://github.com/example/repo.git", "./my-repo"))
}
```

## Important Notes on Async Support

1. **Limited Transport Support**: The async implementation currently has more limited transport support than the blocking version. It primarily supports:
   - `git://` protocol
   - Limited HTTP support

2. **Mutual Exclusivity**: You cannot enable both `async-network-client` and `blocking-network-client` features at the same time.

3. **`maybe_async` API Design**: Many APIs are marked with `maybe_async`, allowing them to work in both blocking and async contexts based on the feature flags enabled.

4. **Performance Considerations**: The async implementation may still perform blocking operations under the hood for certain tasks, so it should be run in a runtime that can handle blocking futures.

## Minimizing Library Size

To create the smallest possible extraction of the needed functionality:

1. **Use specific crates directly:**
   Instead of depending on the high-level `gix` crate, you can depend on specific subcrates. For example, for log functionality, you might use:
   ```toml
   [dependencies]
   gix-hash = "0.47.1"
   gix-object = "0.47.1"
   gix-traverse = "0.47.1"
   ```

2. **Disable default features:**
   Always use `default-features = false` to avoid pulling in unnecessary functionality.

3. **Use feature flags selectively:**
   Only enable the specific features you need.

4. **Consider compile-time optimization:**
   Add the following to your Cargo.toml to improve compile times:
   ```toml
   [profile.dev.package]
   gix-object = { opt-level = 3 }
   gix-hash = { opt-level = 3 }
   ```

## Dependencies Graph

The dependencies between the various components can be visualized as follows:

```
gix (high-level API)
├── gix-hash (core object identifiers)
├── gix-object (git objects)
├── gix-ref (git references)
├── gix-diff (diff implementation)
├── gix-blame (blame implementation)
├── gix-status (status implementation)
├── gix-index (git index)
├── gix-protocol (git protocol)
├── gix-transport (transport layers)
└── gix-url (git URL handling)
```

By understanding this dependency graph, you can selectively include only the pieces you need for your specific application.

## Direct Source Code Extraction and Modification

If you need to modify the library's source code directly rather than using Cargo's dependency system, follow these steps:

### Command Line Instructions for Copying and Modifying Source Code

1. **Create a directory structure for your project:**
   ```bash
   mkdir -p my-git-project/src
   cd my-git-project
   ```

2. **Copy specific crates you need:**
   For example, to copy the log functionality:
   ```bash
   # Copy core crates
   cp -r /path/to/gitoxide/gix-hash .
   cp -r /path/to/gitoxide/gix-object .
   cp -r /path/to/gitoxide/gix-traverse .
   cp -r /path/to/gitoxide/gix-revision .
   ```

3. **Create a Cargo workspace:**
   Create a `Cargo.toml` file in your project root:
   ```toml
   [workspace]
   members = [
       "gix-hash",
       "gix-object",
       "gix-traverse",
       "gix-revision",
       "src",
   ]
   ```

4. **Set up your main crate:**
   Create a `src/Cargo.toml` file:
   ```toml
   [package]
   name = "my-git-tools"
   version = "0.1.0"
   edition = "2021"

   [dependencies]
   gix-hash = { path = "../gix-hash" }
   gix-object = { path = "../gix-object" }
   gix-traverse = { path = "../gix-traverse" }
   gix-revision = { path = "../gix-revision" }
   ```

5. **Modify the source code as needed:**
   Now you can edit any of the copied crates to modify or extend their functionality.
   ```bash
   # Example of editing a file
   nano gix-revision/src/lib.rs
   ```

6. **Update dependencies between crates:**
   Make sure to update the path references in each crate's `Cargo.toml` file:
   ```toml
   # Example for gix-revision/Cargo.toml
   [dependencies]
   gix-hash = { path = "../gix-hash" }
   gix-object = { path = "../gix-object" }
   ```

### Direct Source Extraction with Async Support

If you're extracting the source code directly and need async support:

1. **Copy additional async-related crates:**
   ```bash
   cp -r /path/to/gitoxide/gix-protocol .
   cp -r /path/to/gitoxide/gix-transport .
   ```

2. **Enable async features in the copied crates:**
   Edit the `Cargo.toml` files of the crates to enable async features:
   ```toml
   # Example for gix-protocol/Cargo.toml
   [features]
   async-client = ["dep:futures-io", "dep:futures-lite"]
   ```

3. **Add async runtime dependencies to your main project:**
   ```toml
   # In src/Cargo.toml
   [dependencies]
   futures-lite = "2.1.0"
   async-std = { version = "1.12.0", features = ["attributes"] }
   ```

### Advanced: Automated Extraction Script

Here's a shell script that automates the extraction of specific gitoxide components:

```bash
#!/bin/bash
# extract-gitoxide.sh

# Parameters
SOURCE_DIR="/path/to/gitoxide"
TARGET_DIR="./my-git-project"
COMPONENTS=("gix-hash" "gix-object" "gix-traverse" "gix-revision")
# Add async components if needed
# COMPONENTS+=("gix-protocol" "gix-transport")
USE_ASYNC=false  # Set to true to enable async features

# Create target directory
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# Create workspace file
echo "[workspace]" > Cargo.toml
echo "members = [" >> Cargo.toml
echo "    \"src\"," >> Cargo.toml

# Copy each component
for component in "${COMPONENTS[@]}"; do
    echo "Copying $component..."
    cp -r "$SOURCE_DIR/$component" .
    echo "    \"$component\"," >> Cargo.toml
    
    # Update the version to avoid conflicts
    sed -i 's/version = ".*"/version = "0.1.0-custom"/' "$component/Cargo.toml"
    
    # Fix path dependencies
    for dep in "${COMPONENTS[@]}"; do
        if grep -q "$dep.*version" "$component/Cargo.toml"; then
            sed -i "s/$dep.*version.*/$dep = { path = \"..\\/$dep\" }/" "$component/Cargo.toml"
        fi
    done
    
    # Enable async features if needed
    if [ "$USE_ASYNC" = true ] && [ "$component" = "gix-protocol" ]; then
        if ! grep -q "\[features\]" "$component/Cargo.toml"; then
            echo -e "\n[features]" >> "$component/Cargo.toml"
        fi
        if ! grep -q "async-client" "$component/Cargo.toml"; then
            echo "async-client = [\"dep:futures-io\", \"dep:futures-lite\"]" >> "$component/Cargo.toml"
        fi
    fi
done

echo "]" >> Cargo.toml

# Create main crate
mkdir -p src/src
cat > src/Cargo.toml << EOF
[package]
name = "my-git-tools"
version = "0.1.0"
edition = "2021"

[dependencies]
EOF

# Add dependencies to main crate
for component in "${COMPONENTS[@]}"; do
    echo "$component = { path = \"../$component\" }" >> src/Cargo.toml
done

# Add async runtime dependencies if needed
if [ "$USE_ASYNC" = true ]; then
    echo "futures-lite = \"2.1.0\"" >> src/Cargo.toml
    echo "async-std = { version = \"1.12.0\", features = [\"attributes\"] }" >> src/Cargo.toml
fi

# Create a simple main file
cat > src/src/main.rs << EOF
fn main() {
    println!("Custom gitoxide tool");
}
EOF

echo "Extraction complete! Your custom gitoxide project is ready at $TARGET_DIR"
```

Save this as `extract-gitoxide.sh`, make it executable with `chmod +x extract-gitoxide.sh`, and run it to automatically extract the components you need.

### Notes on Direct Source Extraction

- **License Compliance**: Make sure to include the original license files when copying the source code
- **Version Compatibility**: Components might have interdependencies with specific versions, so it's best to extract all components from the same gitoxide version
- **Maintenance**: You will need to maintain your fork separately from upstream changes
- **Build System**: You might need to adapt build scripts or configurations to your specific needs