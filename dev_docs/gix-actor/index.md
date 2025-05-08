# gix-actor

## Overview

`gix-actor` is a specialized crate in the gitoxide ecosystem that provides types for identifying and representing Git actors (authors and committers). It handles parsing, creating, and serializing Git actor identities and signatures in both immutable (reference-based) and mutable variants. The crate is essential for working with Git commits and tags, where author and committer information is a fundamental part of the metadata.

## Architecture

The crate's architecture is built around two main concepts:

1. **Identity**: Represents a Git actor's basic information (name and email) without timestamp data. This is used when only the actor's identity is needed, not their action timestamp.

2. **Signature**: Extends Identity to include timestamp information. This is used to represent both authorship (who created content originally) and committer information (who committed it to the repository).

Both concepts are implemented with two variants:

- **Immutable References**: `IdentityRef` and `SignatureRef` types that reference their data from a backing byte slice, minimizing allocations.

- **Owned Variants**: `Identity` and `Signature` types that own their data and can be modified.

This dual approach allows for efficient parsing of existing Git objects while also providing mutable versions for creating and modifying actor information.

The crate is designed to handle the parsing and serialization of Git actor information according to Git's format specifications, with careful attention to proper handling of edge cases, whitespace, and validation.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Identity` | Mutable Git actor identity with name and email | Creating or modifying actor identities |
| `IdentityRef<'a>` | Immutable reference to a Git actor's identity | Parsing existing actor identities with minimal allocations |
| `Signature` | Mutable Git actor signature with name, email, and timestamp | Creating or modifying signatures for commits and tags |
| `SignatureRef<'a>` | Immutable reference to a Git actor's signature | Parsing existing signatures with minimal allocations |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `IdentityRef::from_bytes` | Parse an identity from bytes | `fn from_bytes<E>(data: &'a [u8]) -> Result<Self, winnow::error::ErrMode<E>>` |
| `SignatureRef::from_bytes` | Parse a signature from bytes | `fn from_bytes<E>(data: &'a [u8]) -> Result<Self, winnow::error::ErrMode<E>>` |
| `Identity::write_to` | Serialize an identity to a writer | `fn write_to(&self, out: &mut dyn std::io::Write) -> std::io::Result<()>` |
| `Signature::write_to` | Serialize a signature to a writer | `fn write_to(&self, out: &mut dyn std::io::Write) -> std::io::Result<()>` |
| `IdentityRef::trim` | Create a new identity with whitespace trimmed | `fn trim(&self) -> IdentityRef<'a>` |
| `SignatureRef::trim` | Create a new signature with whitespace trimmed | `fn trim(&self) -> SignatureRef<'a>` |
| `SignatureRef::time` | Parse the time string into a Time object | `fn time(&self) -> Result<gix_date::Time, gix_date::parse::Error>` |
| `SignatureRef::seconds` | Extract just the seconds timestamp from the time | `fn seconds(&self) -> gix_date::SecondsSinceUnixEpoch` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-date` | For handling timestamps in signatures |
| `gix-utils` | For common utility functions |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | For binary string handling |
| `winnow` | For parsing actor signatures |
| `thiserror` | For error type definitions |
| `itoa` | For efficient integer to string conversion |
| `serde` (optional) | For serialization/deserialization |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization | `serde`, `bstr/serde`, `gix-date/serde` |

## Examples

### Parsing a Git Actor Identity

```rust
use gix_actor::IdentityRef;
use bstr::ByteSlice;

fn parse_identity(data: &[u8]) -> Result<(), Box<dyn std::error::Error>> {
    // Parse an identity from bytes (e.g., "John Doe <john@example.com>")
    let identity = IdentityRef::from_bytes::<()>(data)?;
    
    // Access identity information
    println!("Name: {}", identity.name.to_str()?);
    println!("Email: {}", identity.email.to_str()?);
    
    // Trim whitespace (Git often has whitespace in names and emails)
    let trimmed = identity.trim();
    println!("Trimmed name: {}", trimmed.name.to_str()?);
    println!("Trimmed email: {}", trimmed.email.to_str()?);
    
    // Convert to owned version if needed
    let owned_identity = identity.to_owned();
    
    Ok(())
}
```

### Parsing a Git Signature

```rust
use gix_actor::SignatureRef;
use bstr::ByteSlice;

fn parse_signature(data: &[u8]) -> Result<(), Box<dyn std::error::Error>> {
    // Parse a signature from bytes (e.g., "John Doe <john@example.com> 1528473343 +0230")
    let signature = SignatureRef::from_bytes::<()>(data)?;
    
    // Access signature information
    println!("Name: {}", signature.name.to_str()?);
    println!("Email: {}", signature.email.to_str()?);
    println!("Timestamp string: {}", signature.time);
    
    // Parse the timestamp
    if let Ok(time) = signature.time() {
        println!("Seconds since epoch: {}", time.seconds);
        println!("Timezone offset (seconds): {}", time.offset);
    }
    
    // Extract just the seconds (useful for quick timestamp comparison)
    let seconds = signature.seconds();
    println!("Seconds since epoch: {}", seconds);
    
    // Get just the identity part (name and email)
    let identity = signature.actor();
    
    Ok(())
}
```

### Creating a New Actor Signature

```rust
use gix_actor::Signature;
use gix_date::Time;

fn create_signature() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Create a new signature
    let signature = Signature {
        name: "John Doe".into(),
        email: "john@example.com".into(),
        time: Time::new(1660797906, 7200), // Timestamp with +0200 timezone
    };
    
    // Serialize the signature
    let mut buffer = Vec::new();
    signature.write_to(&mut buffer)?;
    
    // The buffer now contains "John Doe <john@example.com> 1660797906 +0200"
    Ok(buffer)
}
```

### Validating Actor Information

```rust
use gix_actor::Signature;

fn validate_signature(name: &str, email: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Create a test signature
    let signature = Signature {
        name: name.into(),
        email: email.into(),
        time: gix_date::Time::default(),
    };
    
    // Try to serialize it - this will validate the name and email
    // Git doesn't allow '<', '>', or newlines in names and emails
    let mut buffer = Vec::new();
    match signature.write_to(&mut buffer) {
        Ok(_) => {
            println!("Signature is valid");
            Ok(())
        },
        Err(e) => {
            println!("Invalid signature: {}", e);
            Err(e.into())
        }
    }
}
```

## Implementation Details

### Parsing

The crate uses the `winnow` parser combinator library to parse Git actor identities and signatures:

1. **Identity Parsing**: Parses the `name <email>` format, handling whitespace and edge cases.

2. **Signature Parsing**: Extends identity parsing to include the timestamp in the format `name <email> timestamp timezone`.

3. **Lenient Parsing**: The parser is deliberately lenient, accepting various formats as seen in real-world Git repositories.

4. **Validation**: While parsing is lenient, serialization is strict to ensure valid Git objects.

### Whitespace Handling

Git objects often contain whitespace around names and emails. The crate handles this in several ways:

1. **Preservation**: The original whitespace is preserved for round-trip consistency when parsing.

2. **Trimming**: The `trim()` methods provide convenient access to trimmed versions.

3. **Specification Compliance**: The serialization format matches Git's requirements.

### Time Representation

The crate leverages `gix-date` for timestamp handling:

1. **Storage**: In `SignatureRef`, the time is stored as a raw string for maximum fidelity.

2. **Parsing**: Methods like `time()` and `seconds()` parse the time string as needed.

3. **Owned Version**: In the owned `Signature` struct, time is stored as a parsed `Time` object.

## Testing Strategy

The crate employs several testing strategies:

1. **Round-Trip Testing**: Ensures that parsed and then re-serialized identities and signatures match the original.

2. **Edge Cases**: Tests various edge cases in Git actor formats, including whitespace, Unicode characters, and invalid formats.

3. **Validation**: Ensures that invalid characters in names and emails are properly rejected during serialization.

4. **Lenient Parsing**: Tests that the parser can handle various formats seen in real-world Git repositories.

This comprehensive testing ensures compatibility with Git's handling of actor information.