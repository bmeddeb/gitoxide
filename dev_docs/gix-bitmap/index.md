# gix-bitmap

## Overview

`gix-bitmap` is a crate in the gitoxide ecosystem that provides an implementation of bitmap data structures used in Git. It specifically implements the Enhanced Word-Aligned Hybrid (EWAH) bitmap compression algorithm, which is used by Git for efficiently encoding sets of bits. This crate serves as a foundation for other components like `gix-pack`, `gix-index`, and `gix-worktree` that need to work with bitmap data.

## Architecture

The architecture of `gix-bitmap` is designed to be simple and focused on a single task: handling EWAH bitmap encoding and decoding. The crate consists of:

1. **Core Bitmap Implementation**: A `Vec` structure that represents an EWAH bitmap, with operations for decoding and accessing bits.

2. **Decoding Utilities**: Helper functions for parsing binary data into bitmap structures.

3. **Bit Access Interface**: Functionality to efficiently operate on individual bits in the bitmap.

The implementation is designed to be memory-efficient and performant, following Git's approach to bitmap handling while providing a safe Rust interface.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `ewah::Vec` | Represents an EWAH-compressed bitmap | Main bitmap data structure that holds bit data and provides access methods |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `ewah::decode` | Decodes EWAH-compressed binary data into a bitmap | `fn decode(data: &[u8]) -> Result<(Vec, &[u8]), decode::Error>` |
| `Vec::for_each_set_bit` | Iterates over each set bit in the bitmap | `fn for_each_set_bit(&self, f: impl FnMut(usize) -> Option<()>) -> Option<()>` |
| `Vec::num_bits` | Returns the total number of bits in the bitmap | `fn num_bits(&self) -> usize` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `ewah::decode::Error` | Error returned when decoding fails | `Corrupt` |

## Dependencies

### Internal Dependencies

`gix-bitmap` is a foundational crate with no internal dependencies on other gitoxide crates.

### External Dependencies

| Crate | Usage |
|-------|-------|
| `thiserror` | Error handling |

## Feature Flags

The crate doesn't define any feature flags of its own, keeping its interface simple and focused.

## Examples

### Decoding and Processing an EWAH Bitmap

```rust
use gix_bitmap::ewah;

fn process_bitmap_data(data: &[u8]) -> Result<(), Box<dyn std::error::Error>> {
    // Decode the EWAH bitmap
    let (bitmap, remaining_data) = ewah::decode(data)?;
    
    // Process each set bit
    bitmap.for_each_set_bit(|bit_index| {
        println!("Bit set at position: {}", bit_index);
        Some(()) // Continue iteration
    });
    
    // Get the total number of bits
    let total_bits = bitmap.num_bits();
    println!("Total bits in bitmap: {}", total_bits);
    
    Ok(())
}
```

### Using EWAH Bitmaps with Git Index

This example shows how `gix-bitmap` might be used in the context of the Git index for tracking untracked files:

```rust
use gix_bitmap::ewah;
use gix_hash::ObjectId;

struct DirectoryEntry {
    name: String,
    is_valid: bool,
    check_only: bool,
    has_hash: bool,
    // Other fields...
}

fn parse_directory_entries(data: &[u8]) -> Result<Vec<DirectoryEntry>, Box<dyn std::error::Error>> {
    // First part: parse basic directory data
    let (num_entries, data) = decode_var_int(data)?;
    let mut entries = Vec::with_capacity(num_entries);
    
    // Parse basic entry data...
    
    // Now decode bitmaps for flags
    let (valid_bitmap, data) = ewah::decode(data)?;
    let (check_only_bitmap, data) = ewah::decode(data)?;
    let (hash_valid_bitmap, mut data) = ewah::decode(data)?;
    
    // Apply valid flags
    valid_bitmap.for_each_set_bit(|index| {
        if index < entries.len() {
            entries[index].is_valid = true;
        }
        Some(())
    });
    
    // Apply check_only flags
    check_only_bitmap.for_each_set_bit(|index| {
        if index < entries.len() {
            entries[index].check_only = true;
        }
        Some(())
    });
    
    // Apply hash flags and extract hash data
    hash_valid_bitmap.for_each_set_bit(|index| {
        if index < entries.len() {
            entries[index].has_hash = true;
            // In a real implementation, we would extract the hash from data
            // and advance the data pointer
        }
        Some(())
    });
    
    Ok(entries)
}

// Helper function for the example
fn decode_var_int(data: &[u8]) -> Result<(usize, &[u8]), Box<dyn std::error::Error>> {
    // Simplified implementation
    Ok((0, data))
}
```

## Implementation Details

### EWAH Bitmap Compression

The Enhanced Word-Aligned Hybrid (EWAH) compression is a variation of the Word-Aligned Hybrid (WAH) bitmap compression algorithm. It efficiently encodes sparse bitmaps by:

1. Compressing runs of identical bits
2. Storing literals for areas with mixed bits
3. Using run-length encoding (RLE) to encode repeated patterns

The EWAH format used in Git consists of:
- A header with the number of bits and chunk length
- A bit data section containing the actual compressed bits
- A run length width (RLW) that controls how the bits are interpreted

### Bitmap Decoding Process

The decoding process in `gix-bitmap` follows these steps:

1. Read the number of bits and chunk length from the header
2. Read the bit data, converting from big-endian byte order
3. Read the run length width parameter
4. Return a `Vec` structure with the decoded data

### Efficient Bit Access

The `for_each_set_bit` method provides an efficient way to iterate over only the bits that are set to 1, without having to check every bit in the bitmap. This is particularly valuable for sparse bitmaps where most bits are 0.

The implementation handles two cases:
1. Runs of identical bits (all 0s or all 1s)
2. Literal words where each bit needs to be checked individually

### Memory Safety Considerations

The crate uses safe Rust code throughout, avoiding any `unsafe` blocks. The original Git implementation uses memcpy for efficiency when loading bits, but this implementation relies on Rust's safe abstractions and compiler optimizations.

## Testing Strategy

The crate includes minimal direct tests as most of its functionality is tested indirectly through the consuming crates (`gix-pack`, `gix-index`, and `gix-worktree`). This approach ensures that the bitmap implementation is tested in the context of its actual use cases.

Tests typically cover:
1. Decoding various bitmap patterns
2. Handling edge cases in bitmap data
3. Integration with higher-level Git data structures