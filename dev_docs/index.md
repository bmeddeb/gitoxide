# Gitoxide Documentation Index

This directory contains comprehensive documentation for all the crates in the gitoxide workspace. The goal is to document each crate's architecture, design, components, and relationships to other crates.

## Documentation Status

The following table tracks the documentation status for each crate in the workspace. As documentation is completed, check boxes will be marked.

### Core Crates

| Status | Crate | Description |
|--------|-------|-------------|
| [ ] | [gitoxide](./gitoxide/) | Main library and binary crates |
| [x] | [gitoxide-core](./gitoxide-core/) | Core implementation of CLI commands |
| [x] | [gix](./gix/) | Top-level crate acting as hub for all functionality |

### Specialized Crates

| Status | Crate | Description |
|--------|-------|-------------|
| [x] | [gix-actor](./gix-actor/) | Git actor (author/committer) handling |
| [x] | [gix-archive](./gix-archive/) | Repository archiving functionality |
| [x] | [gix-attributes](./gix-attributes/) | Git attributes handling |
| [x] | [gix-bitmap](./gix-bitmap/) | Bitmap functionality for pack files |
| [x] | [gix-blame](./gix-blame/) | Git blame implementation |
| [x] | [gix-chunk](./gix-chunk/) | Chunk file handling |
| [x] | [gix-command](./gix-command/) | Git command execution |
| [x] | [gix-commitgraph](./gix-commitgraph/) | Commit graph handling |
| [x] | [gix-config](./gix-config/) | Git configuration handling |
| [x] | [gix-config-value](./gix-config-value/) | Git configuration value parsing |
| [x] | [gix-credentials](./gix-credentials/) | Credential handling |
| [x] | [gix-date](./gix-date/) | Git date parsing and formatting |
| [x] | [gix-diff](./gix-diff/) | Git diff implementation |
| [x] | [gix-dir](./gix-dir/) | Directory walk functionality |
| [x] | [gix-discover](./gix-discover/) | Repository discovery functionality |
| [x] | [gix-features](./gix-features/) | Feature flags and utilities |
| [x] | [gix-fetchhead](./gix-fetchhead/) | FETCH_HEAD handling |
| [x] | [gix-filter](./gix-filter/) | Git filter functionality |
| [x] | [gix-fs](./gix-fs/) | Filesystem operations |
| [x] | [gix-fsck](./gix-fsck/) | Repository integrity checking |
| [x] | [gix-glob](./gix-glob/) | Glob pattern matching |
| [x] | [gix-hash](./gix-hash/) | Git hash types and operations |
| [x] | [gix-hashtable](./gix-hashtable/) | Hash table implementation |
| [x] | [gix-ignore](./gix-ignore/) | Git ignore handling |
| [x] | [gix-index](./gix-index/) | Git index handling |
| [ ] | [gix-lfs](./gix-lfs/) | Git LFS implementation |
| [ ] | [gix-lock](./gix-lock/) | File locking functionality |
| [x] | [gix-macros](./gix-macros/) | Procedural macros |
| [ ] | [gix-mailmap](./gix-mailmap/) | Git mailmap functionality |
| [ ] | [gix-merge](./gix-merge/) | Git merge functionality |
| [x] | [gix-negotiate](./gix-negotiate/) | Network protocol negotiation |
| [ ] | [gix-note](./gix-note/) | Git notes functionality |
| [x] | [gix-object](./gix-object/) | Git object handling |
| [x] | [gix-odb](./gix-odb/) | Object database functionality |
| [x] | [gix-pack](./gix-pack/) | Pack file handling |
| [x] | [gix-packetline](./gix-packetline/) | Async packetline protocol implementation |
| [x] | [gix-packetline-blocking](./gix-packetline-blocking/) | Blocking packetline protocol implementation |
| [x] | [gix-path](./gix-path/) | Path handling utilities |
| [ ] | [gix-pathspec](./gix-pathspec/) | Git pathspec handling |
| [ ] | [gix-prompt](./gix-prompt/) | User prompt functionality |
| [x] | [gix-protocol](./gix-protocol/) | Git protocol implementation |
| [ ] | [gix-quote](./gix-quote/) | String quoting utilities |
| [ ] | [gix-rebase](./gix-rebase/) | Git rebase functionality |
| [x] | [gix-ref](./gix-ref/) | Git reference handling |
| [ ] | [gix-refspec](./gix-refspec/) | Git refspec handling |
| [ ] | [gix-revision](./gix-revision/) | Git revision parsing and handling |
| [ ] | [gix-revwalk](./gix-revwalk/) | Revision walking functionality |
| [x] | [gix-sec](./gix-sec/) | Security-related functionality |
| [ ] | [gix-sequencer](./gix-sequencer/) | Git sequencer operations |
| [ ] | [gix-shallow](./gix-shallow/) | Shallow repository handling |
| [x] | [gix-status](./gix-status/) | Repository status functionality |
| [ ] | [gix-submodule](./gix-submodule/) | Git submodule handling |
| [ ] | [gix-tempfile](./gix-tempfile/) | Temporary file management |
| [ ] | [gix-tix](./gix-tix/) | Terminal UI components |
| [x] | [gix-trace](./gix-trace/) | Tracing and logging functionality |
| [x] | [gix-transport](./gix-transport/) | Transport protocol implementation |
| [ ] | [gix-traverse](./gix-traverse/) | Object graph traversal |
| [ ] | [gix-tui](./gix-tui/) | Terminal UI implementation |
| [x] | [gix-url](./gix-url/) | Git URL parsing and handling |
| [x] | [gix-utils](./gix-utils/) | Utility functions |
| [x] | [gix-validate](./gix-validate/) | Input validation functionality |
| [x] | [gix-worktree](./gix-worktree/) | Git worktree handling |
| [ ] | [gix-worktree-state](./gix-worktree-state/) | Worktree state management |
| [x] | [gix-worktree-stream](./gix-worktree-stream/) | Worktree streaming functionality |

## Documentation Structure

Each crate's documentation follows this structure:

1. **Overview** - Brief description of the crate's purpose
2. **Architecture** - Design principles and high-level architecture
3. **Core Components** - Detailed description of main structs, traits, and functions
4. **Dependencies** - Relationship with other crates and external dependencies
5. **Feature Flags** - Description of available feature flags and their effects
6. **Examples** - Usage examples
7. **Implementation Details** - Notes on implementation approaches and design decisions

## Progress Tracking

- Total crates: 62
- Documented: 46
- Remaining: 16