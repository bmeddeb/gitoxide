# Revision Parsing

This page documents methods for parsing and resolving revision specifications in Git history.

## Understanding Revision Specifications

In Git, revision specifications (or "revspecs") are a powerful way to refer to commits and other objects using a variety of syntaxes. The `rev_parse` method allows you to convert these human-readable specifications into Git object IDs.

Some common revision specification formats include:

- `HEAD`: The current commit pointed to by HEAD
- `master`: The tip of the master branch
- `v1.0`: A tag named v1.0
- `HEAD^`: The first parent of HEAD
- `HEAD~3`: The commit 3 steps back from HEAD
- `main..feature`: All commits in the feature branch that aren't in main
- `HEAD@{2}`: The value of HEAD 2 moves ago (reflog)
- `:/fix bug`: The most recent commit with "fix bug" in its message

## Repository.rev_parse(spec)

Parse a revision specification and return a single commit/object ID.

**Parameters:**
- `spec`: `str` - The revision specification (e.g., "HEAD", "main~3", "v1.0^{}")

**Returns:**
- `str` - The object ID that the revision specification resolves to

**Raises:**
- `RepositoryError` - If the specification is invalid or cannot be resolved

**Example:**
```python
import gitoxide

repo = gitoxide.Repository.open("/path/to/repo")

# Get the current HEAD commit
head_id = repo.rev_parse("HEAD")
print(f"HEAD is at: {head_id}")

# Get the parent of HEAD
parent_id = repo.rev_parse("HEAD^")
print(f"Parent commit: {parent_id}")

# Get a specific tag
tag_commit = repo.rev_parse("v1.0")
print(f"v1.0 tag points to: {tag_commit}")

# Get a commit from 5 commits ago
old_commit = repo.rev_parse("HEAD~5")
print(f"Five commits ago: {old_commit}")
```

## Common Revision Specification Formats

### Direct References

- `HEAD`: The current branch/commit
- `FETCH_HEAD`: The branch you fetched from
- `refs/heads/master`: Full reference name for the master branch
- `master`: Short name for the master branch
- `v1.0`: Tag name

### Suffixes

- `^`: Parent commit (e.g., `HEAD^` means the parent of HEAD)
- `^n`: The nth parent of a merge commit (e.g., `HEAD^2` is the second parent of HEAD)
- `~n`: Go back n generations (e.g., `HEAD~3` means HEAD's parent's parent's parent)
- `^{tree}`: Get the tree object pointed to by a commit
- `v1.0^{}`: Dereference a tag to get the object it points to

### Date and Message Specs

- `HEAD@{yesterday}`: Where HEAD was yesterday
- `HEAD@{2 weeks ago}`: Where HEAD was 2 weeks ago
- `:/fix bug`: Find most recent commit with "fix bug" in its message

### Ranges

Note: The range specifications are not directly usable with the `rev_parse` method as it only returns single objects, but they are an important part of Git's revision syntax:

- `main..feature`: All commits in feature that aren't in main
- `main...feature`: All commits in either branch but not both

## Use Cases

**Getting a Specific Commit:**
```python
import gitoxide

repo = gitoxide.Repository.open("/path/to/repo")

# Get a specific tagged release
release_commit = repo.rev_parse("v1.0.0")

# Get the parent of a branch tip
parent_of_master = repo.rev_parse("master^")

# Get a commit from 10 commits ago
historical_commit = repo.rev_parse("HEAD~10")
```

**Working with Branches and Tags:**
```python
import gitoxide

repo = gitoxide.Repository.open("/path/to/repo")

# Check if two branches point to the same commit
main_commit = repo.rev_parse("main")
master_commit = repo.rev_parse("master")
if main_commit == master_commit:
    print("main and master are at the same commit")

# Find where a tag points to
tag_commit = repo.rev_parse("v1.0")
print(f"Tag v1.0 points to commit: {tag_commit}")
```