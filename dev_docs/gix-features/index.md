# gix-features

## Overview

`gix-features` is a foundational crate in the gitoxide ecosystem that provides configurable capabilities through compile-time feature toggles. It serves as a central configuration hub that allows the application-level crate to control feature toggles, which then affect all other `gix-*` crates that use this crate. This approach enables flexible trade-offs between compile time, binary size, and performance.

## Architecture

The crate is organized around the principle of providing multiple implementations of common functionality with different performance and size characteristics. Each module typically offers:

1. A base implementation that is always available and has minimal dependencies
2. Enhanced implementations that are activated via feature flags, providing better performance at the cost of additional dependencies or larger binary size

Key architectural components include:

1. **Parallel Processing**: Optional threading and parallelism utilities that can be enabled via feature flags
2. **Feature-gated Modules**: Modules that are only available when specific features are enabled (like `zlib` compression)
3. **Conditional Implementations**: Different implementations of the same interface based on enabled features
4. **Tracing Support**: Integration with the tracing system through the `gix-trace` crate

This architecture allows applications to precisely control their dependency footprint while maintaining a consistent API whether using high-performance or minimalistic implementations.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `parallel::Iter<'a, I>` | Iterator wrapper that checks for interruption on each iteration | Used to make iterators interruptible |
| `parallel::IterWithErr<'a, I, EFN>` | Iterator wrapper that produces `Result<T, E>` and can be interrupted | Used to make iterators interruptible with error reporting |
| `parallel::EagerIter` | An iterator with eagerly evaluated items | Used to avoid recomputation in iterator chains |
| `interrupt::Read<'a, R>` | Wrapper for `Read` implementations with interrupt support | Used to make I/O operations interruptible |
| `interrupt::Write<'a, W>` | Wrapper for `Write` implementations with interrupt support | Used to make I/O operations interruptible |
| `iter::Chunks<I>` | Iterator over chunks of input | Used to process data in fixed-size chunks |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `parallel::Reduce` | Interface for collecting and aggregating results | Used by parallel processing utilities to combine results |
| `threading::Syncable` | Abstracts sync/non-sync implementations based on feature flags | Types that need to work in both single-threaded and multi-threaded contexts |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `parallel::in_parallel` | Processes items in parallel using multiple threads | `fn in_parallel<I, S, O, R>(input: impl Iterator<Item = I>, thread_limit: Option<usize>, new_thread_state: impl FnOnce(usize) -> S, consume: impl FnMut(I, &mut S) -> O, reducer: R) -> Result<R::Output, R::Error>` |
| `hash::crc32` | Computes CRC32 hash of bytes | `fn crc32(bytes: &[u8]) -> u32` |
| `hash::crc32_update` | Updates a CRC32 hash with more bytes | `fn crc32_update(previous_value: u32, bytes: &[u8]) -> u32` |
| `parallel::optimize_chunk_size_and_thread_limit` | Calculates optimal chunk size and thread count | `fn optimize_chunk_size_and_thread_limit(desired_chunk_size: usize, num_items: Option<usize>, thread_limit: Option<usize>, available_threads: Option<usize>) -> (usize, Option<usize>, usize)` |

### Modules

| Module | Description | Key Components |
|--------|-------------|----------------|
| `parallel` | Utilities for parallel processing | `in_parallel`, `reduce::Stepwise`, `InOrderIter` |
| `interrupt` | Utilities for interruptible operations | `Iter`, `Read`, `Write` |
| `cache` | Cache implementations with optional efficiency debugging | Various cache implementations |
| `decode` | Decoders for binary data | Decode implementations |
| `fs` | Filesystem operations | Directory walking, file reading |
| `hash` | Hashing utilities | `crc32`, `crc32_update` |
| `zlib` | Compression/decompression utilities (feature-gated) | Inflate/deflate streams |
| `threading` | Thread-safe or thread-unsafe primitives | Depends on `parallel` feature |
| `progress` | Progress reporting (feature-gated) | Interfaces to `prodash` crate |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-trace` | For tracing and instrumentation |
| `gix-path` | Used for path handling with the `walkdir` feature |
| `gix-utils` | Used for filesystem utilities with the `fs-read-dir` feature |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `crossbeam-channel` | For efficient multi-threading with the `parallel` feature |
| `parking_lot` | More efficient mutexes with the `parallel` feature |
| `walkdir` | Directory traversal with the `walkdir` feature |
| `crc32fast` | Fast CRC32 implementation with the `crc32` feature |
| `prodash` | Progress reporting with the `progress` feature |
| `bytesize` | Human-readable byte sizes with `progress-unit-bytes` feature |
| `bytes` | Efficient byte buffer manipulation with `io-pipe` feature |
| `flate2` | Compression/decompression with the `zlib` feature |
| `thiserror` | Error handling with the `zlib` feature |
| `once_cell` | Thread-safe lazy initialization with `once_cell` feature |
| `libc` | Platform-specific functionality on Unix systems |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `progress` | Enables progress reporting | `prodash` |
| `progress-unit-human-numbers` | Human-readable numbers in progress reporting | `prodash?/unit-human` |
| `progress-unit-bytes` | Human-readable byte units in progress reporting | `bytesize`, `prodash?/unit-bytes` |
| `fs-read-dir` | Utilities for working with directory entries | `gix-utils` |
| `tracing` | Performance instrumentation | `gix-trace/tracing` |
| `tracing-detail` | Detailed performance traces | `gix-trace/tracing-detail` |
| `parallel` | Multi-threaded parallelism | `crossbeam-channel`, `parking_lot` |
| `once_cell` | Thread-safe lazy initialization | `once_cell` |
| `walkdir` | Directory traversal utilities | `walkdir`, `gix-path`, `gix-utils` |
| `io-pipe` | In-memory unidirectional pipe | `bytes` |
| `crc32` | CRC32 hashing | `crc32fast` |
| `zlib` | Compression/decompression | `flate2`, `thiserror` |
| `cache-efficiency-debug` | Debugging for cache hits/misses | None |

## Examples

### Parallel Processing

```rust
use gix_features::parallel::{self, Reduce};

// Define a reducer that sums values
#[derive(Default)]
struct Adder {
    count: usize,
}

impl Reduce for Adder {
    type Input = usize;
    type FeedProduce = usize;
    type Output = usize;
    type Error = ();

    fn feed(&mut self, item: Self::Input) -> Result<Self::FeedProduce, Self::Error> {
        self.count += item;
        Ok(item)
    }

    fn finalize(self) -> Result<Self::Output, Self::Error> {
        Ok(self.count)
    }
}

// Process items in parallel or serially (depending on feature flags)
fn sum_in_parallel(items: Vec<usize>) -> Result<usize, ()> {
    parallel::in_parallel(
        items.into_iter(),
        None,                // Use default thread limit
        |_thread_id| (),     // No thread-local state needed
        |input, _state| input, // Process each item (identity function)
        Adder::default(),     // Combine results with our reducer
    )
}
```

### Interruptible Operations

```rust
use gix_features::interrupt;
use std::io::Read;
use std::sync::atomic::{AtomicBool, Ordering};

fn read_with_interrupt(mut reader: impl Read, should_interrupt: &AtomicBool) -> std::io::Result<Vec<u8>> {
    let mut interruptible = interrupt::Read {
        inner: reader,
        should_interrupt,
    };
    
    let mut buffer = Vec::new();
    match interruptible.read_to_end(&mut buffer) {
        Ok(_) => Ok(buffer),
        Err(e) if e.kind() == std::io::ErrorKind::Other && e.to_string() == "Interrupted" => {
            // Handle interruption gracefully
            println!("Read operation was interrupted");
            Ok(buffer) // Return partial data
        }
        Err(e) => Err(e),
    }
}

// Usage
fn example() {
    let data = b"example data";
    let interrupt_flag = AtomicBool::new(false);
    
    // Spawn a thread to set the interrupt flag after some time
    let flag_ref = &interrupt_flag;
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_millis(10));
        flag_ref.store(true, Ordering::Relaxed);
    });
    
    // Read will be interrupted
    let result = read_with_interrupt(&data[..], &interrupt_flag);
}
```

### Using CRC32 Hashing

```rust
use gix_features::hash;

fn compute_checksum(data: &[u8]) -> u32 {
    hash::crc32(data)
}

fn update_checksum(prev: u32, new_data: &[u8]) -> u32 {
    hash::crc32_update(prev, new_data)
}

// Computing checksum in chunks
fn compute_in_chunks(chunks: &[&[u8]]) -> u32 {
    let mut checksum = 0;
    for chunk in chunks {
        checksum = hash::crc32_update(checksum, chunk);
    }
    checksum
}
```

## Implementation Details

### Parallel Processing

The parallel processing system is designed to be conditionally compiled based on the `parallel` feature. When enabled, it uses actual multi-threading with `crossbeam-channel` for communication. When disabled, it provides the same API but runs everything in the current thread.

This approach provides:
1. Consistent API regardless of feature flags
2. Zero-cost abstraction when parallelism is disabled
3. Optimal performance when parallelism is enabled

The implementation carefully manages thread-local state to avoid data races and provides reducers to aggregate results in a thread-safe manner.

### Interruptible Operations

Interruptible operations are implemented as wrappers around standard library traits like `Read`, `Write`, and `Iterator`. These wrappers check an `AtomicBool` flag before each operation and abort if the flag is set.

This design ensures:
1. Non-invasive interruption (doesn't require cooperation from the wrapped implementation)
2. Low overhead (a simple atomic load operation)
3. Clean error propagation through the standard error handling mechanisms

### Feature-based Conditional Compilation

Much of the crate uses conditional compilation with `#[cfg(feature = "...")]` directives to include or exclude code based on enabled features. This approach ensures that:

1. Disabled features contribute zero code to the final binary
2. The API remains consistent regardless of enabled features
3. Applications can choose the appropriate trade-offs at compile time

### Zlib Integration

The zlib module provides compression and decompression utilities based on the `flate2` crate. It always uses the high-performance `zlib-rs` backend, having deprecated support for other backends to simplify the architecture.

## Testing Strategy

The crate employs several testing strategies:

1. **Feature-specific tests**: Tests that only run when specific features are enabled (like parallel testing)
2. **Conditional behavior tests**: Tests that verify the same API works correctly with different implementations
3. **Separate test binaries**: Multiple test binaries configured with different feature combinations

These strategies ensure that both the minimal and fully-featured configurations work correctly and maintain API compatibility.