# Repository Methods Implementation Checklist

This document tracks the implementation status of repository methods from the Rust gitoxide library in the Python bindings.

## Basic Repository Operations

| Method | Sync Implementation | Async Implementation | Notes |
|--------|:------------------:|:-------------------:|-------|
| `open()` | ✅ | ✅ | Open existing repository |
| `init()` | ✅ | ✅ | Initialize new repository |
| `git_dir()` | ✅ | ✅ | Get .git directory path |
| `work_dir()` | ✅ | ✅ | Get working directory path |
| `is_bare()` | ✅ | ✅ | Check if repository is bare |
| `head()` | ✅ | ✅ | Get HEAD reference/commit |
| `is_shallow()` | ✅ | ✅ | Check if repo is a shallow clone |
| `shallow_commits()` | ✅ | ✅ | Get list of shallow commits |
| `shallow_file()` | ✅ | ✅ | Get path to shallow file |
| `object_hash()` | ✅ | ✅ | Get object hash algorithm used |

## Object Manipulation

| Method | Sync Implementation | Async Implementation | Notes |
|--------|:------------------:|:-------------------:|-------|
| `find_object()` | ✅ | ❌ | Find any Git object by ID |
| `find_blob()` | ✅ | ❌ | Find blob by ID |
| `find_commit()` | ✅ | ❌ | Find commit by ID |
| `find_tree()` | ✅ | ❌ | Find tree by ID |
| `find_tag()` | ✅ | ❌ | Find tag by ID |
| `find_header()` | ✅ | ❌ | Get object header info |
| `has_object()` | ✅ | ❌ | Check if object exists |

## Reference Management

| Method | Sync Implementation | Async Implementation | Notes |
|--------|:------------------:|:-------------------:|-------|
| `references()` | ✅ | ❌ | List all references |
| `find_reference()` | ✅ | ❌ | Find reference by name |
| `create_reference()` | ✅ | ❌ | Create new reference |
| `reference_names()` | ✅ | ❌ | Get all reference names |

## Revision/History

| Method | Sync Implementation | Async Implementation | Notes |
|--------|:------------------:|:-------------------:|-------|
| `merge_bases()` | ❌ | ❌ | Find merge bases between commits |
| `merge_base_octopus()` | ❌ | ❌ | Find best merge base among multiple commits |
| `revparse()` | ❌ | ❌ | Parse revision specifiers |

## Configuration

| Method | Sync Implementation | Async Implementation | Notes |
|--------|:------------------:|:-------------------:|-------|
| `config()` | ❌ | ❌ | Access repository configuration |
| `command_context()` | ❌ | ❌ | Get command execution context |

## Network Operations

| Method | Sync Implementation | Async Implementation | Notes |
|--------|:------------------:|:-------------------:|-------|
| `clone()` | ❌ | ❌ | Clone repository |
| `fetch()` | ❌ | ❌ | Fetch from remote |
| `push()` | ❌ | ❌ | Push to remote |
| `remote_add()` | ❌ | ❌ | Add remote |
| `remote_list()` | ❌ | ❌ | List remotes |
| `remote_delete()` | ❌ | ❌ | Delete remote |

## Index/Working Directory

| Method | Sync Implementation | Async Implementation | Notes |
|--------|:------------------:|:-------------------:|-------|
| `status()` | ❌ | ❌ | Get working directory status |
| `diff()` | ❌ | ❌ | Generate diff |
| `index()` | ❌ | ❌ | Access index |
| `checkout()` | ❌ | ❌ | Checkout files/refs |
| `add()` | ❌ | ❌ | Add files to index |
| `commit()` | ❌ | ❌ | Create new commit |

## Special Features

| Method | Sync Implementation | Async Implementation | Notes |
|--------|:------------------:|:-------------------:|-------|
| `submodule_*` methods | ❌ | ❌ | Submodule operations |
| `blame()` | ❌ | ❌ | Line-by-line history tracking |
| `archive()` | ❌ | ❌ | Create archive from repo content |
| `log()` | ❌ | ❌ | Commit history log |

## Implementation Plan

Implementation priority should follow this order:

1. Complete basic repository operations
2. Object manipulation
3. Reference management
4. Revision/history features
5. Configuration access
6. Network operations
7. Index/working directory operations
8. Special features

For each method, implement the synchronous version first, followed by the asynchronous version.

## Implementation Notes

### Async Implementation Status
The asynchronous implementation (marked with ✅ in this checklist) has technically been implemented in the Rust code, but there are issues with exposing it properly to Python due to challenges with PyO3's module system and how it interacts with maturin. The async code has been tested and compiles correctly in Rust, but additional work is needed to make it accessible from Python.

Some approaches to consider:
1. Using a separate Python package for async functionality
2. Implementing a Python-side wrapper that initializes the async features
3. Updating to a newer PyO3 version that better supports submodules
4. Using a different build approach that allows for more control over the module structure

For now, prioritize completing the synchronous API and come back to the async exposure issues later.