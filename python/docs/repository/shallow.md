# Shallow Repository Operations

This page documents methods for working with shallow repositories in Gitoxide.

A shallow clone is a repository that has truncated history. It contains only a portion of the history, up to a specified commit depth. Shallow repositories are smaller in size because they don't contain the entire commit history.

## Checking for Shallow Repository

### is_shallow()

Check if the repository is a shallow clone.

**Returns:**
- `bool` - True if the repository is a shallow clone, False otherwise

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
if repo.is_shallow():
    print("Repository is a shallow clone")
else:
    print("Repository is a full clone")
```

## Getting Shallow Commits

### shallow_commits()

Get a list of commit IDs that are shallow in this repository. These commits form the boundary between the included and excluded history.

**Returns:**
- `List[str]` or `None` - List of commit IDs that form the shallow boundary, or None if the repository is not shallow

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
commits = repo.shallow_commits()
if commits:
    print(f"Repository is shallow with {len(commits)} boundary commits:")
    for commit in commits:
        print(f"  - {commit}")
else:
    print("Repository is not shallow")
```

## Getting Shallow File Path

### shallow_file()

Get the path to the repository's `shallow` file, which contains the list of shallow commit IDs.

**Returns:**
- `str` - Path to the shallow file

**Note:**
This method returns the path even if the repository is not shallow. In that case, the file might not exist on disk.

**Example:**
```python
repo = gitoxide.Repository.open("/path/to/repo")
shallow_path = repo.shallow_file()
print(f"Shallow file path: {shallow_path}")
```

## Understanding Shallow Repositories

Shallow repositories are created using Git's `--depth` option when cloning:

```bash
git clone --depth=1 https://github.com/example/repo.git
```

Shallow repositories:
- Have smaller disk size
- Contain limited history
- May not work with all Git operations
- Can be "unshallowed" later by fetching the missing history

When working with a shallow repository in gitoxide, you can use the methods above to identify if a repository is shallow and which commits form the shallow boundary.