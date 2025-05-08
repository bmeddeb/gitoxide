# gix-tempfile

A crate in the gitoxide project that provides Git-style temporary files with built-in signal handling for safe resource cleanup.

## Overview

The `gix-tempfile` crate implements temporary file handling similar to how Git manages its temporary resources. It focuses on ensuring that temporary files are properly cleaned up, even when the process is terminated by signals. This is crucial for Git operations where temporary files are often used as locks or for preparing atomic file updates.

The primary goals of `gix-tempfile` are:
1. Provide temporary files that are automatically removed when no longer needed
2. Handle process termination signals to clean up resources
3. Support atomic file operations via persist functionality
4. Manage parent directory creation and cleanup
5. Provide fork-safe operation

## Architecture & Components

The crate is structured around several key components:

### 1. Handle

The `Handle<T>` struct is the primary interface for working with temporary files:

- `Handle<Writable>`: Represents an open, writable temporary file
- `Handle<Closed>`: Represents a closed temporary file that consumes no system resources but still marks a path

The `Handle` type provides methods for:
- Creating temporary files at specific paths or with auto-generated names
- Writing to and reading from temporary files
- Closing files to save system resources
- Persisting temporary files to replace target resources
- Taking ownership of the underlying temporary file

### 2. Registry

The registry keeps track of all temporary files created within the process:

- Uses a concurrent hash map to track temporary files by ID
- Ensures files are properly cleaned up when handlers are dropped
- Provides signal-safe cleanup functionality
- Handles process forking by tracking the owning process ID

### 3. Signal Handling

The signal handling component:

- Sets up signal handlers to catch termination signals
- Provides different modes for signal handling behavior
- Implements cleanup routines that are signal-safe
- Works across different platforms (with specialized handling for Windows vs Unix)

### 4. ForksafeTempfile

The `ForksafeTempfile` struct:

- Wraps the underlying tempfile implementation
- Tracks the owning process ID to handle forking correctly
- Manages the file state (open or closed)
- Handles persisting operations

## Dependencies

- **tempfile**: The underlying temporary file implementation
- **signal-hook**: For setting up and handling termination signals
- **once_cell**: For lazily initialized static variables
- **parking_lot**: For lightweight, non-blocking mutexes (when not using high-performance hashmaps)
- Optional **dashmap**: For high-performance concurrent hash maps

## Feature Flags

- **signals**: Enables signal handling (enabled by default)
- **hp-hashmap**: Uses DashMap instead of a mutex-protected HashMap for higher performance

## Implementation Details

### Temporary File Creation

When creating a temporary file:
1. A unique file ID is generated and used as a key in the registry
2. The file is created using the `tempfile` crate
3. The file is wrapped with fork-safe tracking information
4. The file is registered for automatic cleanup

### Signal Safety

The crate is designed to be signal-safe:
1. Signal handlers are set up to catch termination signals
2. The registry is accessed in a lock-free manner during signal handling
3. Memory deallocation is avoided using `std::mem::forget` where necessary
4. Process ID tracking ensures only files owned by the current process are cleaned up

### Atomic Persistence

When persisting a temporary file to replace a target resource:
1. The file is fully written and flushed
2. An atomic rename operation replaces the target file
3. If the operation fails, the temporary file is recovered and put back in the registry
4. On success, the file handle may be returned for further operations

### Directory Handling

The crate offers two strategies for managing containing directories:
1. `ContainingDirectory::Exists`: Assumes the directory exists and fails if it doesn't
2. `ContainingDirectory::CreateAllRaceProof`: Creates directories with race-detection and retry logic

Similarly, cleanup strategies are configurable:
1. `AutoRemove::Tempfile`: Just removes the temporary file
2. `AutoRemove::TempfileAndEmptyParentDirectoriesUntil`: Removes the file and any empty parent directories up to a boundary

## Limitations

The crate has several documented limitations:

1. Temporary files might remain on disk if:
   - Uninterruptible signals (like SIGKILL) are received
   - The process is in the middle of a file operation when a signal arrives
   - Signal handlers are not properly set up

2. The concurrent hash map implementation has tradeoffs:
   - The default implementation uses a mutex for protection
   - The high-performance variant (with `hp-hashmap` feature) uses more memory

3. Signal handling is complex and platform-dependent:
   - Different behavior between Unix and Windows platforms
   - Careful consideration is needed when integrating with other signal handlers

## Usage Examples

See the [use cases](use_cases.md) document for detailed examples of how to use the temporary file functionality in various scenarios.