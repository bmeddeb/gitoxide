# gix-revision

## Overview

The `gix-revision` crate provides functionality for parsing Git revision specifications (revspecs) and describing commits in terms of reference names. It serves as a core component in Git's revision resolution system, allowing users to identify commits using various syntax forms including commit hashes, reference names, ancestry specifications, and range operators.

## Architecture

The crate is organized around two primary concepts:

1. **Parsing and Interpretation**: The ability to parse Git's revision syntax into structured specifications that can be used to identify specific commits or commit ranges.

2. **Description Generation**: Functionality to generate human-readable descriptions of commits, similar to `git describe`, which creates reference-relative names for commits.

The architecture follows Git's approach to revision specifications, with a clean separation between parsing and execution. The parsing is language-driven, tokenizing input into operations that can later be executed against a repository to locate commits.

Key design principles include:
- Flexible delegate-based parsing system
- Repository-agnostic specifications
- Clear separation between parsing and application of revspecs

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `MatchGroup` | Represents a successful match of a pattern against a reference name | Used for extracting matched portions of patterns for substitution |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `Delegate` | Interface for handling revision parsing events | Repository implementations that want to interpret revspecs |
| `delegate::Revision` | Interface for finding revisions by name or prefix | Part of the `Delegate` trait family |
| `delegate::Navigate` | Interface for traversing commit ancestry | Part of the `Delegate` trait family |
| `delegate::Kind` | Interface for handling revision specification kinds | Part of the `Delegate` trait family |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `spec::parse` | Parses a revision specification string | `fn parse(input: &BStr, delegate: &mut impl Delegate) -> Result<(), Error>` |
| `describe` | Creates a human-readable name for a commit | `fn describe(oid: ObjectId, graph: &impl Graph, ...) -> Result<Description, Error>` |
| `merge_base` | Finds common ancestors for multiple commits | `fn merge_base(objects: &[ObjectId], graph: &impl Graph, ...) -> Result<Vec<ObjectId>, Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Spec` | Represents a parsed revision specification | `Include`, `Exclude`, `Range`, `Merge`, `IncludeOnlyParents`, `ExcludeParents` |
| `spec::Kind` | How to interpret a revision specification | `IncludeReachable`, `ExcludeReachable`, `RangeBetween`, `ReachableToMergeBase`, `IncludeReachableFromParents`, `ExcludeReachableFromParents` |
| `spec::parse::Error` | Error returned by revision parsing | Various error variants for invalid revspecs |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For object ID handling and prefix disambiguation |
| `gix-object` | For object type definitions |
| `gix-date` | For parsing dates in reflog specifications |
| `gix-revwalk` | For traversing commit history |
| `gix-commitgraph` | For efficient commit graph traversals |
| `gix-hashtable` | For efficient hashing operations (optional) |
| `gix-trace` | For tracing and logging (optional) |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | For efficient byte string handling |
| `thiserror` | For error type definitions |
| `bitflags` | For flag combinations in merge-base functionality (optional) |
| `serde` | For serialization support (optional) |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `default` | Enables both `describe` and `merge_base` features | `describe`, `merge_base` |
| `describe` | Git describe functionality | `gix-trace`, `gix-hashtable` |
| `merge_base` | Git merge-base functionality | `gix-trace`, `bitflags` |
| `serde` | Serialization support | `serde`, `gix-hash/serde`, `gix-object/serde` |

## Examples

```rust
use bstr::ByteSlice;
use gix_revision::spec::{self, parse::delegate::{self, Revision, Navigate, Kind}};

// A simple delegate implementation that prints actions
struct PrintDelegate;

impl delegate::Revision for PrintDelegate {
    fn find_ref(&mut self, name: &bstr::BStr) -> Option<()> {
        println!("Looking up reference: {}", name);
        Some(())
    }
    
    fn disambiguate_prefix(&mut self, prefix: gix_hash::Prefix, _hint: Option<delegate::PrefixHint<'_>>) -> Option<()> {
        println!("Disambiguating prefix: {}", prefix);
        Some(())
    }
    
    fn reflog(&mut self, query: delegate::ReflogLookup) -> Option<()> {
        println!("Reflog lookup: {:?}", query);
        Some(())
    }
    
    fn nth_checked_out_branch(&mut self, branch_no: usize) -> Option<()> {
        println!("Looking up branch no: {}", branch_no);
        Some(())
    }
    
    fn sibling_branch(&mut self, kind: delegate::SiblingBranch) -> Option<()> {
        println!("Looking up sibling branch: {:?}", kind);
        Some(())
    }
}

impl delegate::Navigate for PrintDelegate {
    fn traverse(&mut self, kind: delegate::Traversal) -> Option<()> {
        println!("Traversing: {:?}", kind);
        Some(())
    }
    
    fn peel_until(&mut self, kind: delegate::PeelTo<'_>) -> Option<()> {
        println!("Peeling until: {:?}", kind);
        Some(())
    }
    
    fn find(&mut self, regex: &bstr::BStr, negated: bool) -> Option<()> {
        println!("Finding by regex: {} (negated: {})", regex, negated);
        Some(())
    }
    
    fn index_lookup(&mut self, path: &bstr::BStr, stage: u8) -> Option<()> {
        println!("Index lookup: {} (stage: {})", path, stage);
        Some(())
    }
}

impl delegate::Kind for PrintDelegate {
    fn kind(&mut self, kind: gix_revision::spec::Kind) -> Option<()> {
        println!("Setting kind: {:?}", kind);
        Some(())
    }
}

impl spec::parse::Delegate for PrintDelegate {
    fn done(&mut self) {
        println!("Parsing completed");
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut delegate = PrintDelegate;
    
    // Parse some revision specifications
    let revspecs = [
        "HEAD",
        "HEAD~1",
        "HEAD^1",
        "master..feature",
        "main...topic",
        "@{1}",
        ":/fix bug"
    ];
    
    for revspec in &revspecs {
        println!("\nParsing: {}", revspec);
        spec::parse(revspec.as_bytes().as_bstr(), &mut delegate)?;
    }
    
    Ok(())
}
```

## Implementation Details

### Revision Specification Syntax

The crate supports Git's rich revision specification syntax, including:

- **Simple Names**: `HEAD`, `master`, `v1.0`
- **Ancestry References**: `HEAD~2`, `HEAD^1`
- **Ranges**: `master..feature`, `main...topic`
- **Reflog References**: `@{1}`, `master@{yesterday}`
- **Commit Message Search**: `:/fix bug`
- **Exclude Specs**: `^refs/tags/v1.0`
- **Tree Entries**: `HEAD:path/to/file`

### Parsing Approach

The parsing system uses a delegate-based approach where the parser analyzes the input string, breaks it down into tokens, and calls appropriate methods on the delegate to determine what the tokens refer to. This allows repository-specific logic to be isolated from the parsing process.

Key steps in the parsing process:

1. **Tokenization**: Breaking the input into meaningful parts
2. **Delegate Callbacks**: Calling appropriate delegate methods for each token
3. **Spec Construction**: Building a complete specification from the parsed components

### Describe Implementation

The `describe` function finds the closest tag to a commit, similar to Git's `git describe` command. It:

1. Identifies candidate tags by walking backwards from the target commit
2. Selects the closest tag based on commit distance
3. Formats the result as `<tag>-<distance>-g<commit-id>`

### Merge-Base Implementation

The `merge_base` function finds common ancestors between commits, essential for various Git operations. It uses:

1. Commit graph traversal to identify potential ancestors
2. Different algorithms depending on the requested mode (all, octopus, independent)
3. Efficient filtering to find the most appropriate common ancestors

## Testing Strategy

The crate uses a comprehensive testing approach:

1. **Unit Tests**: Testing individual components in isolation
2. **Parser Tests**: Verifying correct parsing of various revision specification formats
3. **Integration Tests**: Testing with real repository data
4. **Property-Based Tests**: For merge-base and describe implementations
5. **Error Case Coverage**: Ensuring proper error handling for invalid inputs

Tests are designed to verify compatibility with Git's behavior, ensuring the crate correctly implements Git's revision specification semantics.