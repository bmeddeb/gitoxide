# Gitoxide Documentation Plan

This document outlines the plan for documenting the gitoxide codebase, organized by dependency levels to provide a natural learning path for developers.

## Documentation Approach

We'll document crates in order of their position in the dependency hierarchy, starting with foundational crates that have zero internal dependencies, then working up to higher-level crates that build upon them.

Within each level, crates will be categorized by functionality type (core, network, filesystem, etc.).

## Dependency Hierarchy

### Level 0 (Zero Internal Dependencies)
These crates depend only on external libraries:

**Core Utilities**:
- [x] `gix-trace`: Tracing functionality
- [x] `gix-utils`: Common utility functions
- [x] `gix-validate`: Validation for git names and paths
- [x] `gix-macros`: Procedural macros

### Level 1 (One Internal Dependency)
These crates depend on only one gitoxide crate:

**Core**:
- [x] `gix-hashtable`: Hashtable optimized for ObjectId keys

**Filesystem**:
- [x] `gix-path`: Path manipulation and conversions

**Security/Permissions**:
- [ ] `gix-sec`: Security and trust model

### Level 2 (Two Internal Dependencies)

**Core**:
- [ ] `gix-features`: Feature flag integrations
- [x] `gix-hash`: Git hash digest handling
- [ ] `gix-date`: Git date parsing

### Level 3 (Three+ Internal Dependencies)

**Object Model**:
- [ ] `gix-actor`: Git actor identification
- [ ] `gix-object`: Git object handling

**Protocol/Network**:
- [ ] `gix-negotiate`: Negotiation algorithms
- [ ] `gix-packetline`: Packetline protocol implementation
- [ ] `gix-packetline-blocking`: Blocking version of packetline

### Level 4+

**Git Data Model**:
- [ ] `gix-ref`: Reference handling
- [ ] `gix-index`: Index file handling
- [ ] `gix-config`: Config file handling
- [ ] `gix-config-value`: Config value parsing

**Git Operations**:
- [ ] `gix-odb`: Object database
- [ ] `gix-pack`: Pack file handling
- [ ] `gix-diff`: Diff implementation
- [ ] `gix-status`: Status implementation

**Network**:
- [ ] `gix-transport`: Transport protocol
- [ ] `gix-protocol`: Git protocol 
- [ ] `gix-url`: URL parsing and handling

**Filesystem Operations**:
- [ ] `gix-fs`: Filesystem operations
- [ ] `gix-worktree`: Worktree handling
- [ ] `gix-worktree-stream`: Worktree streaming
- [ ] `gix-dir`: Directory walking

### Top Level
- [x] `gix`: Main library
- [x] `gitoxide-core`: Core CLI implementation 
- [ ] `gitoxide`: Main binary crate

## Progress

- Total crates: 62
- Documented: 9
- Remaining: 53

## Next Steps

1. ✅ Complete documentation for Level 0 crates
2. Proceed with documentation for Level 1 crates
3. Continue up the dependency hierarchy

This approach will create coherent documentation that follows the natural structure of the codebase, making it easier for new developers to understand how components fit together.