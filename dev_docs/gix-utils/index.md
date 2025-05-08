# gix-utils

## Overview

The `gix-utils` crate provides utility functions and structures that don't require feature toggles. It serves as a collection of foundational utilities used throughout the gitoxide ecosystem. This crate is intentionally kept simple, with no internal dependencies on other gitoxide crates.

## Architecture

The crate is organized into several modules, each providing specific utility functions:

1. **Buffers**: Utilities for buffer swapping and handling
2. **Backoff**: Implementation of backoff strategies for retrying operations
3. **String Utilities**: Functions for Unicode normalization and string handling
4. **Binary to Integer**: Efficient parsers for converting byte slices to integers

The design philosophy behind this crate is to provide simple, focused utilities that have minimal dependencies and don't require feature toggles. More complex utilities that need feature toggles are placed in the `gix-features` crate instead.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Buffers` | Utility for buffer swapping | Used for reading from one buffer and writing to another, then swapping them |
| `WithForeignSource` | Buffer swapping with support for read-only source | Similar to `Buffers` but with support for an initial read-only buffer |
| `Quadratic` | Quadratic backoff implementation | Used for implementing retry logic with increasing delays |
| `ParseIntegerError` | Error type for integer parsing | Used in the `btoi` module for error handling |

### Functions

#### String Utilities

| Function | Description | Signature |
|----------|-------------|-----------|
| `precompose` | Convert decomposed Unicode to precomposed form | `fn precompose(s: Cow<'_, str>) -> Cow<'_, str>` |
| `decompose` | Convert precomposed Unicode to decomposed form | `fn decompose(s: Cow<'_, str>) -> Cow<'_, str>` |
| `precompose_path` | Precompose a path | `fn precompose_path(path: Cow<'_, Path>) -> Cow<'_, Path>` |
| `precompose_os_string` | Precompose an OS string | `fn precompose_os_string(name: Cow<'_, OsStr>) -> Cow<'_, OsStr>` |

#### Binary to Integer (btoi)

| Function | Description | Signature |
|----------|-------------|-----------|
| `to_unsigned` | Convert byte slice to unsigned integer | `fn to_unsigned<I: MinNumTraits>(bytes: &[u8]) -> Result<I, ParseIntegerError>` |
| `to_signed` | Convert byte slice to signed integer | `fn to_signed<I: MinNumTraits>(bytes: &[u8]) -> Result<I, ParseIntegerError>` |
| `to_unsigned_with_radix` | Convert byte slice to unsigned integer with radix | `fn to_unsigned_with_radix<I: MinNumTraits>(bytes: &[u8], radix: u32) -> Result<I, ParseIntegerError>` |
| `to_signed_with_radix` | Convert byte slice to signed integer with radix | `fn to_signed_with_radix<I: MinNumTraits>(bytes: &[u8], radix: u32) -> Result<I, ParseIntegerError>` |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `MinNumTraits` | Minimal trait set for numeric operations | Implemented for `i32`, `i64`, `u64`, `u8`, `usize` |

## Dependencies

### External Dependencies

| Crate | Usage |
|-------|-------|
| `fastrand` | Used for randomized backoff calculations |
| `unicode-normalization` | Used for Unicode normalization functions |
| `bstr` | Optional dependency for byte string handling |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `bstr` | Enables byte string handling functions | `bstr` crate |

## Examples

### Using Buffers

```rust
use gix_utils::Buffers;

// Create buffers for processing
let mut buffers = Buffers::default();

// First operation - read from src, write to dest
buffers.src.extend_from_slice(b"initial data");
process_data(&buffers.src, &mut buffers.dest);
buffers.swap(); // Now dest is empty, src contains processed data

// Second operation - read from src (processed data), write to dest
process_data_again(&buffers.src, &mut buffers.dest);
buffers.swap(); // Swap again

// After processing is done
buffers.clear();
```

### Using Backoff

```rust
use gix_utils::backoff::Quadratic;
use std::time::Duration;

// Create a quadratic backoff iterator with randomization
let mut backoff = Quadratic::default_with_random();

// Use it for retrying an operation
for wait in backoff.take(5) {
    match try_operation() {
        Ok(result) => break,
        Err(_) => {
            // Wait before retrying
            std::thread::sleep(wait);
        }
    }
}
```

### String Normalization

```rust
use gix_utils::str::{precompose, decompose};
use std::borrow::Cow;

// Precompose a string (e.g., normalize "a" + "̈" to "ä")
let normalized = precompose(Cow::Borrowed("a\u{0308}"));
assert_eq!(normalized, "ä");

// Decompose a string (e.g., normalize "ä" to "a" + "̈")
let decomposed = decompose(Cow::Borrowed("ä"));
assert_eq!(decomposed, "a\u{0308}");
```

### Integer Parsing

```rust
use gix_utils::btoi::{to_unsigned, to_signed};

// Parse unsigned integer
let num = to_unsigned::<u32>(b"12345").unwrap();
assert_eq!(num, 12345);

// Parse signed integer
let num = to_signed::<i32>(b"-12345").unwrap();
assert_eq!(num, -12345);

// Parse with different radix
let num = to_signed_with_radix::<i32>(b"ff", 16).unwrap();
assert_eq!(num, 255);
```

## Implementation Details

### Buffers Module

The buffers module provides utilities for efficient buffer swapping, which is useful in operations that iteratively read from one buffer and write to another. The `Buffers` struct owns both a source and destination buffer, while `WithForeignSource` allows working with an external read-only buffer.

### Backoff Module

The backoff module implements a quadratic backoff strategy similar to what's used in Git. It calculates increasingly longer delays between retry attempts, optionally with randomization to prevent thundering herd problems in distributed systems.

### String Utilities

The string utilities focus on Unicode normalization, particularly handling the conversion between precomposed and decomposed forms. This is important for case-insensitive path handling across different operating systems and file systems.

### BTOI Module

The "Binary TO Integer" (btoi) module provides efficient functions for parsing integers from byte slices without using the `std::str` intermediate conversion. It was ported from the `rust-btoi` crate to avoid dependencies on `num-traits`, improving compile times.

## Testing Strategy

The crate uses unit tests to verify the correctness of each utility:

- Tests for buffer operations ensure proper swapping and clearing
- Backoff tests verify the correct sequence of delay durations
- String utility tests check correct Unicode normalization
- BTOI tests verify correct parsing of various integer formats and proper error handling