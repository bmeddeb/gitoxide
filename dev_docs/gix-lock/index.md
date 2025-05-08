# gix-lock

A crate in the gitoxide project that provides Git-style lock files for atomic operations on resources.

## Overview

The `gix-lock` crate implements a locking mechanism similar to how Git manages file locking, focusing on atomicity and automatic cleanup. When modifying resources like index files or references, Git uses lock files to ensure that concurrent operations don't corrupt data. This crate provides that functionality with additional safety features.

The primary goal of `gix-lock` is to ensure resource modifications are atomic while providing automatic cleanup of lock files when operations complete or fail. Lock files are created with a standard naming convention (appending `.lock` to the resource name) and can either be committed to replace the original resource or be released without making changes.

## Architecture & Components

The crate consists of two main types and several supporting modules:

### Core Types

1. **File**: A writable lock file that can eventually atomically replace the resource it locks.
   - Provides methods to acquire, write to, close, and commit the lock file.
   - Implements standard I/O traits (`Read`, `Write`, `Seek`).

2. **Marker**: A read-only lock that holds a resource without the intent to modify it.
   - Can be created directly or by closing a `File`.
   - Used when you need to lock a resource but don't need to write to it.

### Supporting Modules

1. **acquire**: Handles lock acquisition with configurable failure behaviors.
   - `Fail` enum: Controls what happens when a lock can't be acquired.
   - Functions to acquire locks with different strategies.

2. **commit**: Manages committing lock files to atomically replace the resources they lock.
   - Error handling for commit operations.
   - Atomic replacement of locked resources.

3. **file**: Implements file operations on locked resources.
   - Path handling for locked resources.
   - I/O traits implementation for `File`.

## Dependencies

- **gix-tempfile**: Provides the underlying temporary file functionality with automatic cleanup.
- **gix-utils**: Used for backoff strategies when acquiring locks.
- **thiserror**: For error type definitions.
- **std::path**: For path manipulation and resource naming.

## Implementation Details

### Lock Files

Lock files in `gix-lock` follow Git's naming convention:
- For a resource `path/to/file.ext`, the lock file will be `path/to/file.ext.lock`.
- For a resource without an extension, like `path/to/HEAD`, the lock file will be `path/to/HEAD.lock`.

### Lock Acquisition

The crate provides two strategies for acquiring locks:
1. **Immediate Failure**: Fail immediately if the lock cannot be acquired.
2. **Backoff with Timeout**: Retry with quadratic backoff until a specified timeout is reached.

Both strategies are controlled through the `Fail` enum in the `acquire` module.

### Write Operations

Once a lock is acquired via a `File`:
1. The caller can write to the file using standard I/O operations.
2. Changes can be committed, which atomically replaces the original resource.
3. If the `File` is dropped without committing, changes are discarded and the lock is released.

### Atomic Commits

The commit operation:
1. Ensures all data is flushed to disk.
2. Atomically moves the lock file to replace the original resource.
3. Returns the resource path and, optionally, an open file handle for further operations.

### Marker Operations

A `Marker` can be used to:
1. Prevent other processes from modifying a resource without intending to modify it.
2. Hold a former `File` that has been closed but might still be committed.

## Error Handling

The crate has specialized error types:
- `acquire::Error`: For errors during lock acquisition, including timeout errors.
- `commit::Error`: For errors during the commit process, which returns the instance to allow recovery.

## Safety and Resource Management

Safety features include:
- Automatic cleanup of lock files when dropped, even in case of program interruption.
- Optional creation and cleanup of parent directories.
- Permissions control for created lock files (defaults to 0o666 before umask on Unix).

### Limitations

- Relies on the underlying `gix-tempfile` crate, inheriting its limitations.
- If destructors don't run (e.g., due to a crash), lock files might remain, requiring manual cleanup.
- Locking is cooperative rather than enforced by the filesystem, so applications must adhere to the convention.

## Usage Examples

See the [use cases](use_cases.md) document for detailed examples of how to use the locking functionality in various scenarios.