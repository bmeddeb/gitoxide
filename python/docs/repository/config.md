# Configuration

The Repository class provides access to the Git configuration through the `config()` method, which returns a `ConfigSnapshot` object.

## ConfigSnapshot

The `ConfigSnapshot` class provides read-only access to the repository's configuration values. It represents a snapshot of the configuration at the time it was created and doesn't update if the configuration changes afterward.

## Methods

### Repository.config()

Get a snapshot of the repository's configuration.

**Returns:**
- `ConfigSnapshot` - A snapshot of the repository's configuration

**Raises:**
- `RepositoryError` - If the configuration cannot be accessed

**Example:**
```python
config = repo.config()
```

### ConfigSnapshot.boolean(key)

Get a boolean value from the configuration.

**Parameters:**
- `key`: `str` - The configuration key (e.g., "core.bare")

**Returns:**
- `bool` or `None` - The boolean value if the key exists and is a valid boolean, or None if the key doesn't exist or isn't a valid boolean

**Example:**
```python
# Get whether the repository is bare
is_bare = config.boolean("core.bare")  # True or False, or None if not set
```

### ConfigSnapshot.integer(key)

Get an integer value from the configuration.

**Parameters:**
- `key`: `str` - The configuration key (e.g., "core.compression")

**Returns:**
- `int` or `None` - The integer value if the key exists and is a valid integer, or None if the key doesn't exist or isn't a valid integer

**Example:**
```python
# Get the compression level
compression = config.integer("core.compression")  # 0-9, or None if not set
```

### ConfigSnapshot.string(key)

Get a string value from the configuration.

**Parameters:**
- `key`: `str` - The configuration key (e.g., "user.name")

**Returns:**
- `str` or `None` - The string value if the key exists, or None if the key doesn't exist

**Example:**
```python
# Get the user name
user_name = config.string("user.name")  # "John Doe", or None if not set
```

### ConfigSnapshot.values(key)

Get a list of values from a multi-valued configuration key.

**Parameters:**
- `key`: `str` - The configuration key (e.g., "remote.origin.fetch")

**Returns:**
- `list[str]` - A list of string values associated with the key, or an empty list if the key doesn't exist

**Example:**
```python
# Get fetch refspecs for origin
fetch_refspecs = config.values("remote.origin.fetch")  # ["+refs/heads/*:refs/remotes/origin/*", ...]
```

### ConfigSnapshot.entries()

List common configuration entries. Since Git configuration can have a large number of possible keys,
this method returns a subset focusing on commonly used configuration values.

**Returns:**
- `dict[str, str]` - A dictionary of {key: value} pairs for common configuration entries

**Example:**
```python
# Get all configuration entries
entries = config.entries()
for key, value in entries.items():
    print(f"{key} = {value}")
```

### ConfigSnapshot.has_key(key)

Check if a configuration key exists.

**Parameters:**
- `key`: `str` - The configuration key to check

**Returns:**
- `bool` - True if the key exists, False otherwise

**Example:**
```python
# Check if user.name is set
if config.has_key("user.name"):
    print(f"User name is: {config.string('user.name')}")
else:
    print("User name is not set")
```

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