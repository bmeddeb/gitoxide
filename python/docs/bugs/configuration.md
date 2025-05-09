# Issue: Git Configuration in Gitoxide doesn't behave consistently with Git spec

## Summary
When working with the configuration API in Gitoxide, certain behaviors don't align with the standard Git implementation, making it difficult to build compatible Python bindings. Specifically:

1. Configuration changes made through external Git commands (`git config`) aren't reflected in existing config snapshots
2. Default/cached values for certain settings persist despite filesystem changes
3. Multi-valued keys using indexed format (key.0, key.1) aren't handled according to Git spec

## Detailed Description

### Configuration Snapshot Behavior
The `config_snapshot()` method creates a snapshot of configuration that doesn't update when the underlying config files change. To get updated configuration, a user must reopen the entire repository, which is inconsistent with Git's behavior where configuration updates are detected.

```rust
// Example of the issue
let repo = gitoxide.Repository.open(temp_dir);
let config = repo.config();
// External changes happen
os.system(f"cd {temp_dir} && git config core.compression 42");
// Config still has old value
assert config.integer("core.compression") != 42;  // Still has original/default value
```

### Default Values Override User Configuration
Some configuration values appear to have hardcoded default values that take precedence over what's set in the config file. For example, `core.compression` maintains a value of `9` even when explicitly set to `42` in the config file and the repository is reopened.

```rust
// Even after reopening, values maintain defaults
repo = gitoxide.Repository.open(temp_dir);
config = repo.config();
// Still doesn't have the updated value
assert config.integer("core.compression") != 42;  // Stays at default value (9)
```

### Indexed Multi-Value Keys
Git supports multi-valued keys in the indexed format (e.g., remote.origin.url.0, remote.origin.url.1), but Gitoxide doesn't seem to handle these properly. This makes it impossible to implement a correct `values()` method in the Python bindings.

## Reproduction Steps
1. Create a Git repository (or use an existing one)
2. Open the repository with Gitoxide
3. Get a configuration snapshot
4. Make a configuration change with external Git command
5. Observe that the snapshot doesn't reflect the change
6. Reopen the repository
7. Observe that certain settings still show default values

## Impact
These inconsistencies make it difficult to create Python bindings that behave correctly according to the Git specification. Users of the Gitoxide Python bindings will experience unexpected behavior, especially when:

1. Working with configuration in scripts that also call external Git commands
2. Trying to retrieve multi-valued configuration entries
3. Changing configuration values like `core.compression` that have defaults

## Possible Solutions
1. Implement real-time configuration updates by monitoring the config files
2. Ensure default values don't override explicit user configuration
3. Support indexed multi-value keys according to Git specification
4. Add a `reload_config()` method to refresh configuration without reopening the entire repository

## Conformance to Git Specification
According to the Git documentation:
1. Configuration changes should be immediately reflected in subsequent queries
2. Multi-valued keys should be accessible by index notation
3. Explicitly set values in config files should take precedence over defaults

The current implementation deviates from these expectations, making it difficult for users to work with configuration in a predictable way.

## Workarounds
For Python bindings users, the current workaround is:
1. Reopen the repository every time you need fresh configuration values
2. Be cautious with settings that have defaults in Gitoxide
3. Avoid using indexed multi-value keys for now