# gix-object

## Overview

`gix-object` is a core crate in the gitoxide ecosystem that provides types for Git's object model. It handles the parsing, representation, manipulation, and serialization of Git objects: commits, trees, blobs, and tags. The crate offers both immutable (read-only) variants backed by byte buffers and fully-owned mutable variants, making it suitable for both high-performance reading and flexible writing operations.

## Architecture

The crate's architecture is built around the four fundamental Git object types, with a clean separation between immutable and mutable variants:

1. **Immutable Object References**: Represented by the `*Ref` types (`CommitRef`, `TreeRef`, `BlobRef`, `TagRef`), these are read-only views into existing Git object data. They reference their data from a backing byte slice, minimizing memory allocations during parsing.

2. **Mutable Objects**: Represented by the bare type names (`Commit`, `Tree`, `Blob`, `Tag`), these are fully owned objects that can be modified and serialized. They are typically created by either constructing them from scratch or converting from their immutable counterparts.

3. **Iterator Variants**: For performance-critical applications, there are also iterator-based variants (`CommitRefIter`, `TreeRefIter`, `TagRefIter`) that allow for allocation-free traversal of object data.

4. **Generic Types**: The `ObjectRef` and `Object` enums serve as generic containers for the four object types in their immutable and mutable forms, respectively.

This architecture provides flexibility for different use cases:
- When parsing existing Git data, the immutable types minimize allocations
- When creating or modifying Git objects, the mutable types provide a convenient interface
- When memory efficiency is critical, the iterator variants allow for allocation-free processing

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `CommitRef<'a>` | Immutable view of a Git commit | Parsing existing commit data with minimal allocations |
| `Commit` | Mutable Git commit | Creating or modifying commits |
| `TreeRef<'a>` | Immutable view of a Git tree | Parsing existing tree data with minimal allocations |
| `Tree` | Mutable Git tree | Creating or modifying directory trees |
| `BlobRef<'a>` | Immutable view of a Git blob | Referencing file content |
| `Blob` | Mutable Git blob | Creating or modifying file content |
| `TagRef<'a>` | Immutable view of a Git tag | Parsing existing tag data with minimal allocations |
| `Tag` | Mutable Git tag | Creating or modifying tags |
| `Data<'a>` | Borrowed object with kind and data | Low-level representation of any Git object |
| `Header` | Information about an object | Contains kind and size metadata |
| `tree::EntryRef<'a>` | Immutable entry in a tree | Representing files, directories, or submodules in a tree |
| `tree::Entry` | Mutable entry in a tree | Creating or modifying tree entries |
| `tree::EntryMode` | File mode of a tree entry | Representing mode bits (permissions) of files |
| `tree::Editor` | Helper for efficient tree editing | Making changes to trees with minimal object database access |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `Find` | Lookup Git objects by ID | Object databases |
| `FindExt` | Extended object lookup functionality | Object databases |
| `FindObjectOrHeader` | Low-level object or header lookup | Object databases |
| `Write` | Write object data to a sink | For storing Git objects |
| `WriteTo` | Write object to a specific destination | Implementors convert objects to bytes |
| `Exists` | Check if an object exists | Object databases |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `compute_hash` | Calculate object hash | `fn compute_hash(hash_kind: gix_hash::Kind, object_kind: Kind, data: &[u8]) -> Result<gix_hash::ObjectId, gix_hash::hasher::Error>` |
| `compute_stream_hash` | Calculate hash from stream | `fn compute_stream_hash(hash_kind: gix_hash::Kind, object_kind: Kind, stream: &mut dyn std::io::Read, stream_len: u64, progress: &mut dyn gix_features::progress::Progress, should_interrupt: &std::sync::atomic::AtomicBool) -> Result<gix_hash::ObjectId, gix_hash::io::Error>` |
| `decode::loose_header` | Parse a Git object header | `fn loose_header(input: &[u8]) -> Result<(Kind, u64, usize), decode::LooseHeaderDecodeError>` |
| `encode::loose_header` | Create a Git object header | `fn loose_header(kind: Kind, size: u64) -> Vec<u8>` |
| `CommitRef::from_bytes` | Parse a commit | `fn from_bytes(data: &'a [u8]) -> Result<CommitRef<'a>, decode::Error>` |
| `TreeRef::from_bytes` | Parse a tree | `fn from_bytes(data: &'a [u8]) -> Result<TreeRef<'a>, decode::Error>` |
| `TagRef::from_bytes` | Parse a tag | `fn from_bytes(data: &'a [u8]) -> Result<TagRef<'a>, decode::Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Kind` | The four types of Git objects | `Tree`, `Blob`, `Commit`, `Tag` |
| `ObjectRef<'a>` | Immutable git object | `Tree(TreeRef<'a>)`, `Blob(BlobRef<'a>)`, `Commit(CommitRef<'a>)`, `Tag(TagRef<'a>)` |
| `Object` | Mutable git object | `Tree(Tree)`, `Blob(Blob)`, `Commit(Commit)`, `Tag(Tag)` |
| `tree::EntryKind` | Type of tree entry | `Tree`, `Blob`, `BlobExecutable`, `Link`, `Commit` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-features` | For progress reporting functionality |
| `gix-hash` | For object ID and hash computation |
| `gix-hashtable` | For efficient hash table implementations |
| `gix-validate` | For validation functions |
| `gix-actor` | For author/committer information |
| `gix-date` | For time handling |
| `gix-path` | For path operations |
| `gix-utils` | For utility functions |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | For binary string handling |
| `winnow` | For parsing Git objects |
| `smallvec` | For small vector optimizations |
| `itoa` | For efficient integer to string conversion |
| `thiserror` | For error type definitions |
| `serde` (optional) | For serialization/deserialization |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization | `serde`, `bstr/serde`, `smallvec/serde`, `gix-hash/serde`, `gix-actor/serde` |
| `verbose-object-parsing-errors` | Enables detailed error reporting | `winnow/std` |

## Examples

### Parsing a Git Commit

```rust
use gix_object::CommitRef;

fn parse_commit(data: &[u8]) -> Result<(), Box<dyn std::error::Error>> {
    // Parse a commit from bytes
    let commit = CommitRef::from_bytes(data)?;
    
    // Access commit information
    println!("Tree: {}", commit.tree());
    println!("Parents: {}", commit.parents().count());
    println!("Author: {} <{}>", commit.author().name, commit.author().email);
    println!("Committer: {} <{}>", commit.committer().name, commit.committer().email);
    println!("Message: {}", commit.message());
    
    // Check for GPG signature
    if let Some(sig) = commit.extra_headers().pgp_signature() {
        println!("Commit is signed");
    }
    
    Ok(())
}
```

### Creating a New Commit

```rust
use gix_object::{Commit, Kind};
use gix_hash::ObjectId;
use bstr::BString;
use smallvec::smallvec;

fn create_commit() -> Commit {
    let tree_id = ObjectId::from_hex(b"4b825dc642cb6eb9a060e54bf8d69288fbee4904").unwrap();
    let author = gix_actor::Signature {
        name: "John Doe".into(),
        email: "john@example.com".into(),
        time: "1580461376 +0000".into(),
    };
    
    Commit {
        tree: tree_id,
        parents: smallvec![],  // No parents (root commit)
        author,
        committer: author.clone(),  // Same person is committing
        encoding: None,  // Default to UTF-8
        message: "Initial commit".into(),
        extra_headers: Vec::new(),
    }
}

// Compute the hash for the commit
fn hash_commit(commit: &Commit) -> Result<ObjectId, Box<dyn std::error::Error>> {
    let mut buf = Vec::new();
    commit.write_to(&mut buf)?;
    
    Ok(gix_object::compute_hash(
        gix_hash::Kind::Sha1,
        Kind::Commit,
        &buf,
    )?)
}
```

### Working with Trees

```rust
use gix_object::{tree, Tree};
use gix_hash::ObjectId;
use bstr::BString;

fn create_tree() -> Tree {
    let mut tree = Tree::empty();
    
    // Add a blob entry (file)
    tree.entries.push(tree::Entry {
        mode: tree::EntryKind::Blob.into(),
        filename: "README.md".into(),
        oid: ObjectId::from_hex(b"5dd01c177f5e08a7b6838e7a1d9e32c1f3fd5a56").unwrap(),
    });
    
    // Add a tree entry (directory)
    tree.entries.push(tree::Entry {
        mode: tree::EntryKind::Tree.into(),
        filename: "src".into(),
        oid: ObjectId::from_hex(b"9638c3d07997b0060c3ea468989bfbc2e8bbd35e").unwrap(),
    });
    
    // Add an executable file
    tree.entries.push(tree::Entry {
        mode: tree::EntryKind::BlobExecutable.into(),
        filename: "build.sh".into(),
        oid: ObjectId::from_hex(b"621e7daf7344a9a887c6f589c945057c4e309980").unwrap(),
    });
    
    // Important: Entries must be sorted!
    tree.entries.sort();
    
    tree
}
```

### Handling Object References

```rust
use gix_object::{ObjectRef, Kind};

fn process_object(object_ref: ObjectRef<'_>) {
    match object_ref {
        ObjectRef::Commit(commit) => {
            println!("Found commit with message: {}", commit.message());
        },
        ObjectRef::Tree(tree) => {
            println!("Found tree with {} entries", tree.entries.len());
        },
        ObjectRef::Tag(tag) => {
            println!("Found tag '{}' pointing to {}", tag.name, tag.target_kind);
        },
        ObjectRef::Blob(blob) => {
            println!("Found blob with {} bytes", blob.data.len());
        },
    }
}

// Convert immutable object to mutable
fn make_mutable(object_ref: ObjectRef<'_>) -> gix_object::Object {
    object_ref.into_owned()
}
```

## Implementation Details

### Memory Efficiency

The crate is designed with memory efficiency in mind, particularly for reading operations:

1. **Immutable Types**: The `*Ref` types don't own their data but reference it from a backing byte slice, minimizing allocations.

2. **Iterator Variants**: The `*RefIter` types offer allocation-free processing by parsing the data incrementally.

3. **SmallVec**: Used for parent references in commits, optimized for the common case of 1-2 parents.

4. **Lazy Parsing**: Some fields are only parsed when accessed, reducing upfront work.

### Object Parsing

Object parsing is handled using the `winnow` parser combinator library, which provides both efficiency and flexibility:

1. **Compact Error Reporting**: By default, errors are compact, but with the `verbose-object-parsing-errors` feature, detailed error context is provided.

2. **Zero-Copy Parsing**: The parsers are designed to reference the input buffer directly where possible.

3. **Validation**: Parsed data is validated during parsing to ensure it meets Git's requirements.

### Tree Handling

Tree handling includes special considerations:

1. **Sorting**: Git requires tree entries to be sorted in a special way (not quite lexicographically), which the crate handles properly.

2. **File Modes**: Git's file modes are preserved with their Unix-style permission bits.

3. **Editor**: The `tree::Editor` provides efficient tree manipulation by caching trees and avoiding duplicate lookups.

### Object Hashing

The crate provides utilities to compute Git object hashes:

1. **Header Prefixing**: All Git objects are hashed with a header that includes the type and size.

2. **Streaming Support**: Large objects can be hashed incrementally from a stream.

3. **Progress Reporting**: Hash computation can report progress and be interrupted.

## Testing Strategy

The crate employs several testing strategies:

1. **Unit Tests**: Extensive tests for parsing, encoding, and manipulating Git objects.

2. **Fixtures**: Uses real-world Git objects as test fixtures to ensure compatibility.

3. **Round-Trip Testing**: Ensures that parsed and then re-encoded objects match the original.

4. **Edge Cases**: Tests for handling malformed inputs, unusual formats, and corner cases.

5. **Benchmarks**: Performance benchmarks to ensure efficient implementation, particularly for parsing.