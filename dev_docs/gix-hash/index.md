# gix-hash

## Overview

The `gix-hash` crate provides types for identifying git objects using hash digests. It's a foundational crate in the gitoxide ecosystem that handles both borrowed and owned hash value representations, with a focus on SHA1 digests (the traditional Git hash function).

## Architecture

The crate is designed around two primary types:
- Borrowed hash references via the `oid` module
- Owned hash values via the `ObjectId` struct

It also provides functionality for hashing data, verifying hashes, and handling partial hash prefixes (used for short-form Git object identifiers). The crate is designed to be extensible to eventually support other hash algorithms like SHA256 (which Git is planning to support).

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `ObjectId` | An owned Git object ID, containing a hash digest | `let id = ObjectId::from_hex("deadbeef...").unwrap();` |
| `Prefix` | A partial, owned hash that can match objects with a specific prefix | Used for matching objects with a hash prefix |
| `Hasher` | A hasher that computes Git object IDs | `let hasher = Hasher::new(Kind::Sha1);` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Kind` | The kind of hash function | `Sha1` (default) |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `oid::from_hex` | Convert a hex string to an object ID | `fn from_hex(hex: &str) -> Result<&oid, Error>` |
| `bytes_of_file` | Compute the hash of a file | `fn bytes_of_file(path: impl AsRef<Path>) -> io::Result<ObjectId>` |
| `bytes` | Compute the hash of bytes | `fn bytes(data: &[u8]) -> ObjectId` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-features` | Provides progress reporting and other shared features |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `faster-hex` | Fast hex encoding/decoding |
| `sha1-checked` | SHA1 implementation |
| `serde` | Optional serialization/deserialization support |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enable serialization/deserialization support | `serde` |

## Examples

```rust
use gix_hash::{oid, ObjectId, Kind};

// Create an ObjectId from a hexadecimal string
let id = ObjectId::from_hex("1234567890abcdef1234567890abcdef12345678").unwrap();

// Create a borrowed object ID reference
let oid_ref = oid::from_hex("1234567890abcdef1234567890abcdef12345678").unwrap();

// Convert from borrowed to owned
let owned_id = oid_ref.to_owned();

// Hash some data
let data = b"hello, world";
let hashed_id = gix_hash::bytes(data);

// Create a hasher and update it with data
let mut hasher = gix_hash::hasher(Kind::Sha1);
hasher.update(b"hello, ");
hasher.update(b"world");
let id = hasher.digest();
```

## Implementation Details

The crate is built around the idea that Git object IDs are essentially hash digests of the content of Git objects. Currently, it primarily supports SHA1 as the hash algorithm, which produces a 20-byte (160-bit) digest.

Key implementation details:
- The `ObjectId` struct is a wrapper around a 20-byte array
- The `oid` module provides borrowed views into those bytes
- The crate is designed to eventually support SHA256 as Git plans to transition to this algorithm
- Hash prefixes are supported for abbreviated object identifiers
- The crate includes utilities for hashing files and byte slices

## Testing Strategy

Testing ensures:
- Correct parsing of hex strings into object IDs
- Proper error handling for invalid inputs
- Correct hashing of content to match Git's behavior
- Correct prefix matching