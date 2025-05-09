# Repository

The `Repository` class is the central component of the Gitoxide Python bindings. It represents a Git repository and provides methods for accessing and manipulating repository data.

## Class Overview

```python
class Repository:
    @classmethod
    def open(cls, path): ...
    @classmethod
    def init(cls, path, bare=False): ...

    def git_dir(self): ...
    def work_dir(self): ...
    def is_bare(self): ...
    def head(self): ...
    def is_shallow(self): ...
    def shallow_commits(self): ...
    def shallow_file(self): ...
    def object_hash(self): ...

    # Object methods - see Objects documentation
    def find_object(self, id): ...
    def find_blob(self, id): ...
    def find_commit(self, id): ...
    def find_tree(self, id): ...
    def find_tag(self, id): ...
    def find_header(self, id): ...
    def has_object(self, id): ...

    # Reference methods - see References documentation
    def references(self): ...
    def reference_names(self): ...
    def find_reference(self, name): ...
    def create_reference(self, name, target, is_symbolic, force): ...

    # History methods - see History documentation
    def merge_bases(self, one, others): ...
```

## Basic Usage

```python
import gitoxide

# Open an existing repository
repo = gitoxide.Repository.open("/path/to/repo")

# Create a new repository
new_repo = gitoxide.Repository.init("/path/to/new/repo", bare=False)
```

## Pages in this Section

- [Opening & Creating Repositories](opening.md)
- [Basic Repository Properties](properties.md)
- [Shallow Repository Operations](shallow.md)

## Class Methods

### Repository.open(path)

Open an existing Git repository at the given path.

**Parameters:**
- `path`: `str` or `pathlib.Path` - Path to the repository (can be either the .git directory or the working directory)

**Returns:**
- `Repository` - Repository object

**Raises:**
- `RepositoryError` - If the repository cannot be opened or doesn't exist

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
```

### Repository.init(path, bare=False)

Initialize a new Git repository at the given path.

**Parameters:**
- `path`: `str` or `pathlib.Path` - Path where the repository will be created
- `bare`: `bool` - If True, create a bare repository without a working directory (defaults to False)

**Returns:**
- `Repository` - Repository object

**Raises:**
- `RepositoryError` - If the repository cannot be initialized

**Example:**
```python
# Create a regular repository
regular_repo = gitoxide.Repository.init("/path/to/new/repo")

# Create a bare repository
bare_repo = gitoxide.Repository.init("/path/to/bare/repo.git", bare=True)
```