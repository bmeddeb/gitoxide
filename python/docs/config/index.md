# Configuration

The `config()` method provides access to a repository's configuration settings, allowing you to read Git configuration values.

## Classes

- `Config` - A snapshot of a repository's configuration

## Overview

Git configurations come from several sources, in order of increasing precedence:

1. System-wide configuration file (`/etc/gitconfig`)
2. User-level configuration file (`~/.gitconfig` or `~/.config/git/config`)
3. Repository-level configuration file (`.git/config`)
4. Environment variables
5. Command-line options

The `Config` class provides access to the merged configuration from all these sources, as of the time it was created.

## Basic Usage

```python
import gitoxide

# Open a repository
repo = gitoxide.Repository.open("/path/to/repo")

# Get the configuration
config = repo.config()

# Read configuration values
user_name = config.string("user.name")
user_email = config.string("user.email")
is_bare = config.boolean("core.bare")
compression = config.integer("core.compression")

# Check if a key exists
if config.has_key("core.ignorecase"):
    print(f"ignorecase = {config.boolean('core.ignorecase')}")

# Get all configuration entries
all_entries = config.entries()
for key, value in all_entries.items():
    print(f"{key} = {value}")

# Get multi-valued configuration (like remote.origin.fetch)
fetch_specs = config.values("remote.origin.fetch")
for spec in fetch_specs:
    print(f"Fetch spec: {spec}")
```

## Methods

### Config.boolean(key)

Get a boolean value from the configuration.

**Parameters:**
- `key`: `str` - The configuration key (e.g., "core.bare")

**Returns:**
- `bool` or `None` - The boolean value if the key exists and is a valid boolean, or None if the key doesn't exist or isn't a valid boolean

### Config.integer(key)

Get an integer value from the configuration.

**Parameters:**
- `key`: `str` - The configuration key (e.g., "core.compression")

**Returns:**
- `int` or `None` - The integer value if the key exists and is a valid integer, or None if the key doesn't exist or isn't a valid integer

### Config.string(key)

Get a string value from the configuration.

**Parameters:**
- `key`: `str` - The configuration key (e.g., "user.name")

**Returns:**
- `str` or `None` - The string value if the key exists, or None if the key doesn't exist

### Config.values(key)

Get a list of values from a multi-valued configuration key.

**Parameters:**
- `key`: `str` - The configuration key (e.g., "remote.origin.fetch")

**Returns:**
- `list[str]` - A list of string values associated with the key, or an empty list if the key doesn't exist

### Config.entries()

List common configuration entries.

**Returns:**
- `dict[str, str]` - A dictionary of {key: value} pairs for common configuration entries

### Config.has_key(key)

Check if a configuration key exists.

**Parameters:**
- `key`: `str` - The configuration key to check

**Returns:**
- `bool` - True if the key exists, False otherwise

## Common Configuration Keys

### Core Settings
- `core.bare` - Whether the repository is bare
- `core.compression` - Compression level
- `core.filemode` - Whether to consider file modes for status
- `core.ignorecase` - Whether to ignore case in filenames

### User Settings
- `user.name` - User name
- `user.email` - User email

### Remote Settings
- `remote.<name>.url` - URL of the remote
- `remote.<name>.fetch` - Fetch refspec
- `remote.<name>.push` - Push refspec

### Branch Settings
- `branch.<name>.remote` - Remote for the branch
- `branch.<name>.merge` - Merge configuration for the branch