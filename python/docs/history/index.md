# History Traversal

The Gitoxide Python bindings provide methods for traversing and analyzing the commit history of a Git repository.

## Pages in this Section

- [Merge Base Operations](merge_base.md) - Finding common ancestor commits

## Overview

Working with Git history allows you to understand the relationships between commits, find common ancestors, and traverse the commit graph. These operations are essential for many Git operations like merging, rebasing, and visualizing repository history.

The history traversal methods are primarily accessed through the `Repository` class and provide insight into how commits relate to each other in the repository history.

## Available History Methods

Currently, the following history-related methods are available:

| Method | Description |
| ------ | ----------- |
| `Repository.merge_bases(one, others)` | Find all merge bases (common ancestors) between two or more commits |

## Example Usage

```python
import gitoxide

# Open a repository
repo = gitoxide.Repository.open('/path/to/repo')

# Find merge bases between two commits
commit1 = "1234567890abcdef1234567890abcdef12345678"
commit2 = "abcdef1234567890abcdef1234567890abcdef12"

merge_bases = repo.merge_bases(commit1, [commit2])
print(f"Found {len(merge_bases)} merge base(s):")
for base in merge_bases:
    print(f"  - {base}")
```