# gix-refspec

## Overview

The `gix-refspec` crate provides functionality for parsing, validating, and working with Git reference specifications (refspecs). Refspecs are used in Git to map references from one repository to another, primarily during fetch and push operations. They define the source reference(s) in one repository and the corresponding destination reference(s) in another repository.

## Architecture

The crate is designed around a few key abstractions:

1. **Representation Types**: `RefSpecRef<'a>` and `RefSpec` types that represent borrowed and owned refspec data, respectively.
2. **Parsing System**: Functions to interpret string representations of refspecs and validate their correctness.
3. **Instruction Conversion**: Mechanisms to turn parsed refspecs into concrete instructions for Git operations.
4. **Pattern Matching**: Support for handling glob patterns in refspecs and matching references against them.

The architecture follows Git's approach to refspecs, with strong validation and precise semantics for different refspec forms. The parsing is designed to be strict and enforce Git's rules regarding refspec syntax and semantics.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `RefSpecRef<'a>` | A borrowed refspec representation that references the memory it was parsed from | Used for parsing and analyzing refspecs without taking ownership |
| `RefSpec` | An owned refspec representation containing owned string data | Used for storing refspecs or converting from borrowed to owned representation |
| `MatchGroup` | Represents a successful match of a pattern against a reference name | Used for extracting matched portions of patterns for substitution |

### Traits

The crate doesn't expose public traits as part of its API.

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `parse` | Parses a refspec string with a specified operation | `fn parse(spec: &BStr, operation: Operation) -> Result<RefSpecRef<'_>, Error>` |
| `match_group::from_pattern_and_candidate` | Attempts to match a reference name against a pattern | `fn from_pattern_and_candidate(pattern: &BStr, candidate: &BStr) -> Option<MatchGroup<'_>>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Instruction<'a>` | Concrete operation derived from a refspec | `Push(Push<'a>)`, `Fetch(Fetch<'a>)` |
| `Push<'a>` | Push operation type | `AllMatchingBranches`, `Delete`, `Matching` |
| `Fetch<'a>` | Fetch operation type | `Only`, `Exclude`, `AndUpdate` |
| `parse::Operation` | Defines how the parsed refspec should be used | `Push`, `Fetch` |
| `parse::Error` | Error type for refspec parsing | Various error variants for invalid refspecs |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-validate` | Used for validating reference names in refspecs |
| `gix-revision` | Used for parsing revision specifications in refspecs |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Used for efficient byte string handling |
| `thiserror` | Used for error type definitions |
| `smallvec` | Used for efficient small vector allocations in pattern matching |

## Feature Flags

The crate doesn't expose feature flags in its current version.

## Examples

```rust
use bstr::{BStr, ByteSlice};
use gix_refspec::{parse, parse::Operation, Instruction, instruction::{Push, Fetch}};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Parse a refspec for fetch operation
    let fetch_spec = "+refs/heads/*:refs/remotes/origin/*";
    let parsed = parse(fetch_spec.as_bytes().as_bstr(), Operation::Fetch)?;
    
    // Extract source and destination
    println!("Source: {:?}", parsed.source());      // Some("refs/heads/*")
    println!("Destination: {:?}", parsed.destination()); // Some("refs/remotes/origin/*")
    
    // Get the concrete instruction
    match parsed.instruction() {
        Instruction::Fetch(Fetch::AndUpdate { src, dst, allow_non_fast_forward }) => {
            println!("Fetch and update: {} -> {}", src, dst);
            println!("Force update: {}", allow_non_fast_forward);
        }
        _ => println!("Not a fetch-and-update instruction"),
    }
    
    // Parse a refspec for push operation
    let push_spec = ":refs/heads/old-branch";  // Delete a branch
    let parsed = parse(push_spec.as_bytes().as_bstr(), Operation::Push)?;
    
    match parsed.instruction() {
        Instruction::Push(Push::Delete { ref_or_pattern }) => {
            println!("Delete: {}", ref_or_pattern);
        }
        _ => println!("Not a delete instruction"),
    }
    
    Ok(())
}
```

## Implementation Details

### Refspec Format and Parsing

Git refspecs follow specific formats:
- Basic format: `[+]source:destination`
- Source only: `[+]source`
- Destination only: `:destination` (for deletion in push operations)
- No components: `:` (for pushing all matching branches)
- Negative format: `^source` (for excluding references in fetch operations)

The `+` prefix indicates a force operation, allowing non-fast-forward updates.

The parsing logic in `parse()` handles these formats by:
1. Checking for force (`+`) or negative (`^`) prefixes
2. Splitting the refspec at the colon (`:`) if present
3. Validating source and destination components using `gix-validate`
4. Checking for pattern consistency (e.g., if one side has a glob pattern, the other must as well)
5. Applying special rules for negative refspecs

### Pattern Matching

For refspecs with glob patterns, the crate handles matching and substitution:
- Limited to a single `*` character in patterns
- When a reference matches a pattern, the matched portion can be substituted in the destination pattern
- The `MatchGroup` struct captures the matched portion and provides methods to apply it

### Instruction Generation

The `instruction()` method converts a parsed refspec into a concrete instruction that precisely defines what operation should be performed:
- For `Push` operations: `AllMatchingBranches`, `Delete`, or `Matching`
- For `Fetch` operations: `Only`, `Exclude`, or `AndUpdate`

These instructions can be used by Git clients to perform the appropriate actions during push or fetch operations.

## Testing Strategy

The crate uses Rust's standard testing approach with:
- Unit tests for parsing various refspec formats
- Tests for pattern matching functionality
- Tests for instruction generation
- Validation of error cases

The test suite ensures that the crate correctly implements Git's refspec semantics, including edge cases and invalid inputs. Tests are grouped by functionality and cover the main API entry points as well as internal components.