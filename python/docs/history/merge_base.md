# Merge Base Operations

This page documents methods for finding common ancestors (merge bases) between commits in Git history.

## Understanding Merge Bases

In Git, a merge base is the common ancestor of two commits. It serves as the base for a three-way merge when integrating changes from different branches. Finding the merge base is a critical operation in Git for:

- Determining what changes to include in a merge
- Handling conflicts properly
- Supporting rebase operations
- Calculating the difference between branches

Technically, a merge base is the best common ancestor for commits in Git's direct acyclic graph (DAG). If multiple common ancestors exist, Git chooses the "best" one, which is typically the most recent.

## Repository.merge_bases(one, others)

Find all merge bases (common ancestors) between one commit and multiple other commits.

**Parameters:**
- `one`: `str` - The object ID (SHA) of the first commit
- `others`: `List[str]` - A list of object IDs (SHAs) to find merge bases with

**Returns:**
- `List[str]` - A list of commit object IDs that are merge bases between the first commit and the others

**Raises:**
- `RepositoryError` - If any of the commit IDs is invalid

**Example:**
```python
import gitoxide

repo = gitoxide.Repository.open("/path/to/repo")

# Find merge bases between two branches (using their commit IDs)
master_id = "1234567890abcdef1234567890abcdef12345678"
feature_id = "abcdef1234567890abcdef1234567890abcdef12"

# Find all merge bases
merge_bases = repo.merge_bases(master_id, [feature_id])

# Print the results
if merge_bases:
    print(f"Found {len(merge_bases)} merge base(s):")
    for base in merge_bases:
        print(f"  - {base}")
else:
    print("No common ancestor found")
```

## Repository.merge_base(one, two)

Find the best merge base (common ancestor) between two commits.

**Parameters:**
- `one`: `str` - The object ID (SHA) of the first commit
- `two`: `str` - The object ID (SHA) of the second commit

**Returns:**
- `str` - The commit object ID of the best merge base between the two commits

**Raises:**
- `RepositoryError` - If any commit ID is invalid or no merge base exists

**Example:**
```python
import gitoxide

repo = gitoxide.Repository.open("/path/to/repo")

# Find merge base between two branches (using their commit IDs)
master_id = "1234567890abcdef1234567890abcdef12345678"
feature_id = "abcdef1234567890abcdef1234567890abcdef12"

try:
    # Find the best merge base
    merge_base = repo.merge_base(master_id, feature_id)
    print(f"Merge base: {merge_base}")
except Exception as e:
    print(f"Error: {e}")
```

This method is similar to `merge_bases`, but it specifically returns the single "best" merge base rather than all merge bases. In simple cases, there will only be one merge base, but in complex histories with multiple merge bases, Git chooses the most appropriate one.

## Multiple Merge Bases

In complex repository histories, especially those with merge commits, there can be multiple merge bases between branches. The method returns all of them, allowing you to process them according to your application's needs.

**Example with multiple merge bases:**
```python
import gitoxide

repo = gitoxide.Repository.open("/path/to/repo")

# Get merge bases between current branch and another branch
current_head = "1234567890abcdef1234567890abcdef12345678"
another_branch = "abcdef1234567890abcdef1234567890abcdef12"
third_branch = "fedcba9876543210fedcba9876543210fedcba98"

# Find all merge bases for these branches
merge_bases = repo.merge_bases(current_head, [another_branch, third_branch])

# The result could contain multiple commits in complex histories
```

## Use Cases

**Checking if One Branch Contains Another:**
```python
import gitoxide

repo = gitoxide.Repository.open("/path/to/repo")

branch1_id = "1234567890abcdef1234567890abcdef12345678"
branch2_id = "abcdef1234567890abcdef1234567890abcdef12"

# Find merge bases
merge_bases = repo.merge_bases(branch1_id, [branch2_id])

# If one of the merge bases is equal to branch2_id, then branch1 contains branch2
if branch2_id in merge_bases:
    print("branch1 contains branch2")
```

**Finding Base for a Rebase Operation:**
```python
import gitoxide

repo = gitoxide.Repository.open("/path/to/repo")

feature_id = "1234567890abcdef1234567890abcdef12345678"
target_id = "abcdef1234567890abcdef1234567890abcdef12"

# Find the merge base to determine the starting point for rebase
merge_bases = repo.merge_bases(feature_id, [target_id])
if merge_bases:
    rebase_start = merge_bases[0]  # Using the first merge base for simplicity
    print(f"Rebase would start from commit {rebase_start}")
```