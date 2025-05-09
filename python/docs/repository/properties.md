# Repository Properties

This page documents methods for accessing basic properties of a Git repository.

## Repository Path Methods

### git_dir()

Get the path to the repository's `.git` directory.

**Returns:**
- `str` - Absolute path to the .git directory

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
git_dir = repo.git_dir()
print(f"Git directory: {git_dir}")  # e.g., "/path/to/repo/.git"
```

### work_dir()

Get the path to the repository's working directory, if it has one.
For bare repositories, this method returns `None`.

**Returns:**
- `str` or `None` - Absolute path to the working directory, or None for bare repositories

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
work_dir = repo.work_dir()
if work_dir:
    print(f"Working directory: {work_dir}")  # e.g., "/path/to/repo"
else:
    print("Repository has no working directory (bare)")
```

## Repository State Methods

### is_bare()

Check if the repository is bare (has no working directory).

**Returns:**
- `bool` - True if the repository is bare, False otherwise

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
if repo.is_bare():
    print("Repository is bare")
else:
    print("Repository has a working directory")
```

### head()

Get the name of the current HEAD reference (e.g., "refs/heads/main") or the commit ID if HEAD is detached.

**Returns:**
- `str` - String with the reference name (e.g., "refs/heads/main") or commit ID

**Raises:**
- `RepositoryError` - If HEAD is not set or cannot be read

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
try:
    head = repo.head()
    if head.startswith("refs/heads/"):
        branch = head[len("refs/heads/"):]
        print(f"On branch {branch}")
    else:
        print(f"HEAD is detached at {head}")
except gitoxide.RepositoryError as e:
    print(f"Error getting HEAD: {e}")
```

## Object Hash Method

### object_hash()

Get the object hash algorithm used by the repository.

**Returns:**
- `str` - String representation of the hash algorithm (e.g., "Sha1")

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
hash_algo = repo.object_hash()
print(f"Repository uses {hash_algo} for object hashing")
```