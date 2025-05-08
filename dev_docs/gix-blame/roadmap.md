# gix-blame Roadmap

This document outlines the roadmap for improving the `gix-blame` crate to achieve feature parity with Git's blame command and potentially surpass it in performance and usability.

## Current Status

According to `crate-status.md`, the current implementation has several limitations that need to be addressed:

- [x] Basic commit annotations for a single file
- [ ] Progress reporting
- [ ] Interruptibility
- [ ] Streaming support
- [ ] Support for worktree changes (virtual commits on top of HEAD)
- [ ] Shallow-history support
- [ ] Rename tracking
- [ ] Support for commits to ignore
- [ ] Passing all blame corner cases from Git
- [ ] Performance improvements

## Priority Improvements

### 1. Performance Enhancements

The current implementation isn't competitive with Git's blame performance. Without these improvements, the crate will remain significantly slower than Git's implementation.

1. **Custom Graph Walk (High Priority)**
   - Implement specialized graph traversal that avoids walking down parents that don't have the file in question
   - Skip entire branches that can't contribute to the blame
   - Status: Not implemented

2. **Commit Graph Integration (High Priority)**
   - Use commit-graph data to speed up traversal
   - Fill traversal information into blame data structures
   - Store tree information in the commit-graph for faster lookups
   - Status: Not implemented

3. **Bloom Filter Integration (High Priority)**
   - Use commit-graph bloom filters to quickly check if a commit has a path
   - Allow skipping commits that can't modify the file being blamed
   - Status: Not implemented

### 2. Core Features for Parity with Git

1. **Progress Reporting (Medium Priority)**
   - Add support for showing progress during blame operation
   - Include statistics about processed commits and remaining work
   - Status: Not implemented

2. **Interruptibility (Medium Priority)**
   - Allow blame operations to be safely interrupted
   - Implement graceful cancellation
   - Status: Not implemented

3. **Streaming Output (Medium Priority)**
   - Support for incremental blame output
   - Return results as they're computed rather than all at once
   - Status: Not implemented

4. **Rename and Copy Detection (High Priority)**
   - Track content across file renames
   - Detect code copied from other files
   - Support different similarity thresholds for moves vs. copies
   - Support configurable scoring mechanisms
   - Status: Not implemented

5. **Ignored Commits (Medium Priority)**
   - Support for ignoring specific commits
   - Read ignore list from a file (like Git's `--ignore-revs-file`)
   - Status: Not implemented

6. **Worktree Changes Support (Medium Priority)**
   - Create virtual commits from uncommitted changes
   - Show blame with current work in progress
   - Status: Not implemented

7. **Line Filtering (Low Priority)**
   - Filtering by author
   - Filtering by date range
   - Status: Partial (date filtering exists but needs improvement)

8. **Output Formats (Medium Priority)**
   - Porcelain format (machine-readable)
   - Incremental format
   - Status: Not implemented

### 3. Extended Features

1. **Better Heuristics (Low Priority)**
   - Improve detection of code movement between files
   - Handle code refactoring better
   - Status: Not implemented

2. **Integration with Diff Engines (Medium Priority)**
   - Support for various diff algorithms
   - Whitespace handling options
   - Status: Partial (basic diff algorithm selection exists)

3. **Enhanced API (Low Priority)**
   - Better error reporting
   - More configuration options
   - Status: Not implemented

## Implementation Plan

### Phase 1: Performance Foundation

1. Implement custom graph walk that avoids unnecessary parent commits
2. Add commit-graph integration for faster traversal
3. Implement bloom filter support for path-based filtering
4. Optimize memory usage and reduce allocations

### Phase 2: Core Features

1. Add rename tracking
2. Implement progress reporting and interruptibility
3. Support for ignoring specific commits
4. Add support for uncommitted changes

### Phase 3: Polish and Enhanced Features

1. Improve output formats
2. Add additional filtering options
3. Enhance heuristics for code movement
4. Implement streaming output

## Architectural Changes Needed

1. **Traversal Architecture**
   - Redesign commit graph traversal to be more efficient
   - Make better use of cached commit data

2. **Memory Management**
   - More efficient data structures for tracking blame entries
   - Better caching of intermediate results

3. **Progress and Interruption**
   - Add progress callback interfaces
   - Add cancellation token pattern for interruption

4. **Rename Detection**
   - Add detection of similar content across different file paths
   - Implement file rename detection similar to git's implementation

5. **Streaming Output Design**
   - Restructure to emit results incrementally
   - Allow for progressive refinement of blame information

## Benchmarking Plan

To ensure we're making progress towards our performance goals:

1. Create a benchmark suite that compares with Git's blame
2. Test on repositories of different sizes:
   - Small (~100 commits)
   - Medium (~1,000 commits)
   - Large (~10,000+ commits)
3. Test on files with varying history complexity:
   - Files with few contributors and changes
   - Files with many contributors and frequent changes
   - Files that have been renamed or moved
   - Files with content that has been moved between files

## Comparison with Git

Git's blame implementation has several decades of refinement and optimization. Key aspects to match or exceed:

1. **Performance**: Git's blame is highly optimized but still can be slow on large repositories
2. **Memory usage**: Git can use significant memory for blame operations
3. **Usability**: Git's output formats are well-established, but could be improved upon
4. **Accuracy**: Git uses heuristics that work well in many cases but aren't perfect for all scenarios

Our aim should be to match Git's functionality while exceeding it in:
- Performance for large repositories
- Memory efficiency
- API flexibility
- Integration with the Rust ecosystem