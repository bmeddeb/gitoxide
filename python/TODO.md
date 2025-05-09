# Python Bindings TODO List

This document tracks the current progress and future work for the gitoxide Python bindings.

## Completed

1. Basic Repository Operations
   - [x] `open()` - Open existing repository
   - [x] `init()` - Initialize new repository
   - [x] `git_dir()` - Get .git directory path
   - [x] `work_dir()` - Get working directory path
   - [x] `is_bare()` - Check if repository is bare
   - [x] `head()` - Get HEAD reference/commit
   - [x] `is_shallow()` - Check if repo is a shallow clone
   - [x] `shallow_commits()` - Get list of shallow commits
   - [x] `shallow_file()` - Get path to shallow file
   - [x] `object_hash()` - Get object hash algorithm used

2. Object Manipulation
   - [x] `find_object()` - Find any Git object by ID
   - [x] `find_blob()` - Find blob by ID
   - [x] `find_commit()` - Find commit by ID
   - [x] `find_tree()` - Find tree by ID
   - [x] `find_tag()` - Find tag by ID
   - [x] `find_header()` - Get object header info
   - [x] `has_object()` - Check if object exists

3. Reference Management
   - [x] `references()` - List all references
   - [x] `find_reference()` - Find reference by name
   - [x] `create_reference()` - Create new reference
   - [x] `reference_names()` - Get all reference names

4. Testing
   - [x] Tests for basic repository operations
   - [x] Tests for object manipulation methods
   - [x] Tests for reference management methods

5. Example Code
   - [x] Basic usage example
   - [x] Repository objects and references example

## In Progress

1. Async API ### Skip for now.
   - [x] Basic repository operations (open, init, head, shallow_commits)
   - [ ] Object manipulation (find_object, etc.)
   - [ ] Reference management (references, etc.)

## Upcoming Work

1. Revision/History Features
   - [x] `merge_bases()` - Find merge bases between commits
   - [x] `merge_base_octopus()` - Find best merge base among multiple commits
   - [x] `revparse()` - Parse revision specifiers

2. Configuration
   - [x] `config()` - Access repository configuration
   - [ ] `command_context()` - Get command execution context
   - [x] Improve `Config.values()` method to properly handle multi-valued keys (currently using hardcoded values)
   - [x] Enhance `Config.integer()` method to handle all numeric formatting cases
   - [x] Add proper config scan for `Config.entries()` to list all configuration entries

3. Network Operations
   - [ ] `clone()` - Clone repository
   - [ ] `fetch()` - Fetch from remote
   - [ ] `push()` - Push to remote
   - [ ] `remote_add()` - Add remote
   - [ ] `remote_list()` - List remotes
   - [ ] `remote_delete()` - Delete remote

4. Index/Working Directory
   - [ ] `status()` - Get working directory status
   - [ ] `diff()` - Generate diff
   - [ ] `index()` - Access index
   - [ ] `checkout()` - Checkout files/refs
   - [ ] `add()` - Add files to index
   - [ ] `commit()` - Create new commit

5. Special Features
   - [ ] `submodule_*` methods - Submodule operations
   - [ ] `blame()` - Line-by-line history tracking
   - [ ] `archive()` - Create archive from repo content
   - [ ] `log()` - Commit history log

## Known Issues

1. Async Implementation
   - Current pyo3-async-runtimes (0.24.0) has API differences that prevent a straightforward implementation
   - Need to update the async implementation to work with the latest version
   - The async module is not being correctly exposed by PyO3 when building with maturin
   - Possible solutions include:
     1. Using a separate package for async functionality
     2. Implementing a Python-side wrapper that initializes the async features
     3. Updating to a newer PyO3 version that better supports submodules
     4. Using a different build approach that allows for more control over the module structure

2. Future Tasks
   - Add type stubs to improve IDE autocompletion
   - Improve error messages and exception handling
   - Add more examples for specific use cases
   - Create comprehensive documentation