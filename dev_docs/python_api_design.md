# Python API Design for Gitoxide

This document outlines the Python API design for Gitoxide bindings, focusing on creating a Pythonic, user-friendly interface while leveraging Gitoxide's powerful internals.

## Design Philosophy

1. **Pythonic Interface**: Follow Python conventions and idioms
2. **Task-Oriented API**: Focus on common user tasks rather than internal structures
3. **Simple by Default, Powerful When Needed**: Provide sensible defaults with options for advanced usage
4. **Consistent Error Handling**: Use Python exception hierarchy
5. **Strong Type Hints**: Provide complete type annotations for IDE support

## Package Structure

```
gitoxide/
├── sync/           # Synchronous API
│   ├── __init__.py
│   ├── repository.py
│   ├── objects.py
│   ├── refs.py
│   └── ...
├── asyncio/        # Asynchronous API
│   ├── __init__.py
│   ├── repository.py
│   ├── objects.py
│   ├── refs.py
│   └── ...
└── common/         # Shared types and utilities
    ├── __init__.py
    ├── errors.py
    └── ...
```

## API Examples

### Core Repository Operations

#### Synchronous API

```python
from gitoxide.sync import Repository, Signature

# Open an existing repository
repo = Repository.open("/path/to/repo")

# Initialize a new repository
repo = Repository.init("/path/to/new/repo")
repo = Repository.init("/path/to/new/repo", bare=True)  # Create a bare repository

# Clone a repository
repo = Repository.clone("https://github.com/user/repo", "/path/to/destination")
# With options
repo = Repository.clone(
    "https://github.com/user/repo",
    "/path/to/destination",
    depth=1,                # Shallow clone
    branch="develop",       # Clone specific branch
    progress=True           # Show progress
)

# Repository information
print(repo.path)            # Path to .git directory
print(repo.workdir)         # Path to working directory (None for bare repos)
print(repo.is_bare)         # Is this a bare repository?
print(repo.is_empty)        # Is this repository empty?
print(repo.is_shallow)      # Is this a shallow clone?

# Remote operations
repo.fetch("origin")
repo.pull("origin", "main")
repo.push("origin", "main")

# Working with remotes
remote = repo.remote("origin")
print(remote.name)
print(remote.url)
remotes = list(repo.remotes())  # List all remotes

# Create a new remote
repo.remote_create("upstream", "https://github.com/upstream/repo")
```

#### Asynchronous API

```python
import asyncio
from gitoxide.asyncio import Repository

async def main():
    # Open an existing repository
    repo = await Repository.open("/path/to/repo")
    
    # Clone a repository with progress reporting
    repo = await Repository.clone(
        "https://github.com/user/repo",
        "/path/to/destination",
        progress=True
    )
    
    # Remote operations
    await repo.fetch("origin")
    await repo.pull("origin", "main")
    
    # Working with remotes
    remote = await repo.remote("origin")
    print(remote.name)
    print(remote.url)
    
    # List all remotes
    remotes = [remote async for remote in repo.remotes()]

asyncio.run(main())
```

### Object Manipulation

#### Synchronous API

```python
from gitoxide.sync import Repository, Commit, Tree, Blob, Tag

# Get a commit
repo = Repository.open("/path/to/repo")
commit = repo.commit("abc123")  # Get by SHA
commit = repo.head().peel_to_commit()  # Get HEAD commit

# Commit properties
print(commit.id)           # Full SHA
print(commit.short_id)     # Short SHA
print(commit.message)      # Full commit message
print(commit.summary)      # First line of message
print(commit.author.name)  # Author name
print(commit.author.email) # Author email
print(commit.author.time)  # Author time (as datetime)
print(commit.committer.name)  # Committer name

# Commit relationships
parent = commit.parent(0)  # First parent
parents = list(commit.parents())  # All parents
tree = commit.tree()      # Root tree

# Working with trees
for entry in tree:
    print(f"{entry.name}: {entry.type}")
    
    # Get the object
    obj = entry.to_object()
    if obj.type == "blob":
        print(obj.content)  # Get blob content
    elif obj.type == "tree":
        # Recurse into subtree
        for subentry in obj:
            print(f"  {subentry.name}")

# Direct blob access
blob = repo.blob("abc123")
print(blob.content)        # Raw content
print(blob.size)           # Size in bytes
print(blob.is_binary)      # Is this binary data?

# Tag handling
tag = repo.tag("v1.0")
print(tag.name)            # Tag name
print(tag.target)          # Target SHA
print(tag.message)         # Tag message
```

#### Asynchronous API

```python
import asyncio
from gitoxide.asyncio import Repository

async def main():
    repo = await Repository.open("/path/to/repo")
    
    # Get HEAD commit
    head_ref = await repo.head()
    commit = await head_ref.peel_to_commit()
    
    # Get commit properties
    print(commit.id)
    print(commit.message)
    
    # Get tree and iterate entries
    tree = await commit.tree()
    async for entry in tree:
        print(f"{entry.name}: {entry.type}")
        
        # Get the object
        obj = await entry.to_object()
        if obj.type == "blob":
            content = await obj.content()
            print(f"Content size: {len(content)}")

asyncio.run(main())
```

### Reference Management

#### Synchronous API

```python
from gitoxide.sync import Repository

repo = Repository.open("/path/to/repo")

# Get HEAD
head = repo.head()
print(head.name)           # Reference name
print(head.shorthand())    # Short name (e.g., 'main')
print(head.target)         # Target SHA

# Get a specific branch
main = repo.branch("main")
print(main.name)
print(main.is_head())      # Is this the current HEAD?

# List all branches
for branch in repo.branches():
    print(branch.name)
    
# List remote branches
for branch in repo.branches(remote=True):
    print(branch.name)

# Create a new branch
branch = repo.branch_create("new-feature", commit_id="abc123")
branch = repo.branch_create("hotfix", from_branch="main")  # Branch from another branch

# Tags
tag = repo.tag("v1.0")
print(tag.name)

# List all tags
for tag in repo.tags():
    print(tag.name)
    
# Create a new tag
tag = repo.tag_create(
    "v1.1", 
    commit_id="abc123", 
    message="Version 1.1"
)

# Checkout a branch or commit
repo.checkout("main")                        # By name
repo.checkout("abc123")                      # By commit SHA
repo.checkout("feature", create=True)        # Create and checkout

# Check if reference exists
exists = repo.reference_exists("refs/heads/main")
```

#### Asynchronous API

```python
import asyncio
from gitoxide.asyncio import Repository

async def main():
    repo = await Repository.open("/path/to/repo")
    
    # Get HEAD
    head = await repo.head()
    print(head.name)
    print(await head.shorthand())
    
    # List all branches
    branches = [branch async for branch in repo.branches()]
    for branch in branches:
        print(branch.name)
    
    # Create a new branch
    branch = await repo.branch_create("new-feature", commit_id="abc123")
    
    # Checkout a branch
    await repo.checkout("main")

asyncio.run(main())
```

### Working Directory and Status

#### Synchronous API

```python
from gitoxide.sync import Repository, StatusEntry

repo = Repository.open("/path/to/repo")

# Get status of working directory
status = repo.status()

# Iterate through status entries
for entry in status:
    print(f"{entry.path}: {entry.status}")
    
# Filter status entries
untracked = status.untracked()
modified = status.modified()
staged = status.staged()

# Diff between index and working directory
diff = repo.diff()
print(diff.stats.files_changed)
print(diff.stats.insertions)
print(diff.stats.deletions)

# Iterate through diff hunks
for file_diff in diff:
    print(f"File: {file_diff.new_file.path}")
    for hunk in file_diff.hunks:
        print(f"@@ {hunk.header} @@")
        for line in hunk.lines:
            print(line.content)

# Index operations
repo.add("file.txt")                      # Add a file to index
repo.add("directory", recursive=True)     # Add a directory recursively
repo.remove("file.txt")                   # Remove a file
repo.reset("file.txt")                    # Unstage a file

# Commit changes
author = repo.signature("Author Name", "author@example.com")
committer = repo.signature("Committer Name", "committer@example.com")
commit_id = repo.commit("Commit message", author=author, committer=committer)

# Amend last commit
commit_id = repo.commit_amend("New commit message")
```

#### Asynchronous API

```python
import asyncio
from gitoxide.asyncio import Repository

async def main():
    repo = await Repository.open("/path/to/repo")
    
    # Get status
    status = await repo.status()
    
    # Iterate through status entries
    async for entry in status:
        print(f"{entry.path}: {entry.status}")
    
    # Get diff
    diff = await repo.diff()
    print(diff.stats.files_changed)
    
    # Add and commit
    await repo.add("file.txt")
    author = await repo.signature("Author Name", "author@example.com")
    commit_id = await repo.commit("Commit message", author=author)

asyncio.run(main())
```

### Configuration

#### Synchronous API

```python
from gitoxide.sync import Repository

repo = Repository.open("/path/to/repo")

# Get config values
user_name = repo.config.get("user.name")
user_email = repo.config.get("user.email")
remote_url = repo.config.get("remote.origin.url")

# Get config with default value
value = repo.config.get("core.ignorecase", default=True)

# Set config values
repo.config.set("user.name", "New Name")
repo.config.set("core.ignorecase", True)

# Check if config exists
exists = repo.config.exists("user.name")

# Delete config entry
repo.config.delete("user.name")

# Iterate through config
for entry in repo.config:
    print(f"{entry.name}: {entry.value}")

# Get multivar (multiple values for a key)
values = repo.config.get_multivar("remote.*.url")
for value in values:
    print(value)
```

#### Asynchronous API

```python
import asyncio
from gitoxide.asyncio import Repository

async def main():
    repo = await Repository.open("/path/to/repo")
    
    # Get config values
    user_name = await repo.config.get("user.name")
    
    # Set config values
    await repo.config.set("user.name", "New Name")
    
    # Iterate through config
    async for entry in repo.config:
        print(f"{entry.name}: {entry.value}")

asyncio.run(main())
```

### Log and History

#### Synchronous API

```python
from gitoxide.sync import Repository

repo = Repository.open("/path/to/repo")

# Get commit log
log = repo.log()
for commit in log:
    print(f"{commit.id}: {commit.summary}")
    
# Limit log
for commit in repo.log(limit=10):
    print(commit.summary)
    
# Log with path filter
for commit in repo.log(paths=["src/main.py"]):
    print(commit.summary)
    
# Log between commits
for commit in repo.log(from_commit="abc123", to_commit="def456"):
    print(commit.summary)
    
# Blame
blame = repo.blame("src/main.py")
for hunk in blame:
    commit = hunk.commit
    print(f"Lines {hunk.start_line}-{hunk.end_line}: {commit.id} {commit.summary}")
    print(hunk.content)
```

#### Asynchronous API

```python
import asyncio
from gitoxide.asyncio import Repository

async def main():
    repo = await Repository.open("/path/to/repo")
    
    # Get commit log
    log = await repo.log()
    async for commit in log:
        print(f"{commit.id}: {commit.summary}")
    
    # Blame
    blame = await repo.blame("src/main.py")
    async for hunk in blame:
        commit = hunk.commit
        print(f"Lines {hunk.start_line}-{hunk.end_line}: {commit.id}")

asyncio.run(main())
```

## Error Handling

```python
from gitoxide.common.errors import (
    GitoxideError,
    RepositoryError,
    ObjectError,
    ReferenceError,
    CheckoutError,
    ConfigError
)

try:
    repo = Repository.open("/not/a/repo")
except RepositoryError as e:
    print(f"Repository error: {e}")
    
try:
    commit = repo.commit("not-a-commit")
except ObjectError as e:
    print(f"Object error: {e}")
```

## Progress and Callbacks

```python
from gitoxide.sync import Repository

# Simple progress display
repo = Repository.clone(
    "https://github.com/user/repo",
    "/path/to/destination",
    progress=True  # Shows default progress output
)

# Custom progress callback
def progress_callback(operation, current, total):
    percent = 100 * current / total if total > 0 else 0
    print(f"{operation}: {percent:.1f}% ({current}/{total})")

repo = Repository.clone(
    "https://github.com/user/repo",
    "/path/to/destination",
    progress=progress_callback
)
```

## Context Managers

```python
from gitoxide.sync import Repository

# Automatic cleanup for repositories
with Repository.open("/path/to/repo") as repo:
    commit = repo.commit("abc123")
    # Repository is automatically closed when exiting the block

# Transaction support for operations that might need to be rolled back
with repo.transaction() as tx:
    repo.add("file1.txt")
    repo.add("file2.txt")
    # If an exception occurs, changes are rolled back
```

## Type Hints

```python
from typing import List, Optional, Union, Iterator
from datetime import datetime

class Repository:
    @classmethod
    def open(cls, path: str) -> "Repository": ...
    
    @classmethod
    def init(cls, path: str, bare: bool = False) -> "Repository": ...
    
    @classmethod
    def clone(
        cls,
        url: str,
        path: str,
        depth: Optional[int] = None,
        branch: Optional[str] = None,
        progress: Union[bool, callable] = False
    ) -> "Repository": ...
    
    def commit(
        self,
        message: str,
        author: Optional["Signature"] = None,
        committer: Optional["Signature"] = None
    ) -> str: ...
    
    def branches(self, remote: bool = False) -> Iterator["Branch"]: ...
```

## Configuration and Environment

```python
import gitoxide

# Library-wide configuration
gitoxide.set_global_config("http.sslVerify", False)

# Get library version
print(gitoxide.__version__)

# Set thread count for parallel operations
gitoxide.set_threads(4)

# Enable or disable features
gitoxide.enable_feature("aggressive-cache")
```

## Class Hierarchy Overview

```
Repository
├── Object
│   ├── Commit
│   ├── Tree
│   ├── Blob
│   └── Tag
├── Reference
│   ├── Branch
│   └── Tag
├── Remote
├── Index
├── Diff
│   ├── FileDiff
│   │   └── Hunk
├── Status
│   └── StatusEntry
├── Config
│   └── ConfigEntry
└── Signature
```

## Implementation Notes

1. **Repository**: Central class for all operations
2. **Objects**: Use Pythonic iteration protocols
3. **References**: Simple interface for manipulating refs
4. **Configuration**: Dict-like interface for config
5. **Diff/Status**: Focus on common operations
6. **Error Handling**: Clear, specific exceptions
7. **Progress**: Support for callbacks and simple displays
8. **Async**: Mirror sync API with awaitables