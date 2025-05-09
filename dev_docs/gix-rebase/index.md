# gix-rebase

## Overview

The `gix-rebase` crate is intended to provide Git rebase functionality within the gitoxide ecosystem. Git rebase is a powerful operation that allows for the rewriting of commit history by changing the base of a sequence of commits, enabling cleaner repository history and more flexible branch management.

**Current Status**: This crate is currently a placeholder. It reserves the name within the gitoxide project but contains no implementation yet. The crate is at version 0.0.0, indicating it's in the early planning stages.

## Architecture

While the crate doesn't have an implementation yet, we can outline the expected architecture based on how Git rebase works:

1. **Rebase Modes**: Support for different rebase modes:
   - Standard rebase (changing the base of a branch)
   - Interactive rebase (allowing manipulation of commits during rebase)
   - Rebase onto (rebasing a range of commits onto a specific base)

2. **Backend Implementation**:
   - Apply backend (patch-based approach)
   - Merge backend (commit-by-commit approach with more control)

3. **State Management**: Handling of rebase state throughout the operation, including:
   - Todo list tracking
   - Progress tracking
   - Conflict resolution state

4. **Operation Flow**: Implementation of the rebase process:
   - Preparation (calculating common ancestor, preparing new base)
   - Commit processing (generating patches or todo list)
   - Commit application (applying changes to new base)
   - Conflict resolution (handling merge conflicts)
   - Branch updating (updating references to point to new history)

## Core Components

When implemented, the crate is expected to contain the following components:

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Rebase` | Main rebase controller | Orchestrates the rebase operation |
| `InteractiveRebase` | Interactive rebase implementation | Handles interactive rebase operations |
| `RebaseState` | State of an ongoing rebase | Tracks progress and manages rebase state |
| `TodoList` | List of rebase operations to perform | Tracks commits and actions during interactive rebase |
| `RebaseOptions` | Configuration for rebase operations | Controls rebase behavior and options |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `RebaseMode` | Type of rebase operation | `Standard`, `Interactive`, `Onto` |
| `RebaseAction` | Action to perform on a commit | `Pick`, `Reword`, `Edit`, `Squash`, `Fixup`, `Drop`, `Exec` |
| `RebaseStatus` | Current status of rebase operation | `InProgress`, `Paused`, `Conflict`, `Complete` |
| `RebaseError` | Errors that can occur during rebase | Various error types for different failure scenarios |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `start` | Start a new rebase operation | `fn start(repo: &Repository, onto: &Commit, upstream: &Commit, options: RebaseOptions) -> Result<Rebase>` |
| `continue_rebase` | Continue a paused rebase | `fn continue_rebase(repo: &Repository) -> Result<Rebase>` |
| `abort` | Abort an in-progress rebase | `fn abort(repo: &Repository) -> Result<()>` |
| `interactive` | Start an interactive rebase | `fn interactive(repo: &Repository, commit: &Commit, options: InteractiveOptions) -> Result<InteractiveRebase>` |

## Dependencies

The crate is expected to have the following dependencies when implemented:

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For object ID representation and manipulation |
| `gix-object` | For accessing and manipulating Git objects |
| `gix-commit` | For working with commit objects |
| `gix-index` | For staging changes and handling conflicts |
| `gix-diff` | For generating patches and handling diffs |
| `gix-ref` | For reference manipulation |
| `gix-repository` | For repository access and operations |
| `gix-lockfile` | For safely updating references |
| `gix-tempfile` | For handling temporary files during rebase |

### External Dependencies

When implemented, the crate might have these external dependencies:

| Crate | Usage |
|-------|-------|
| `thiserror` | For error handling |
| `log` | For logging rebase operations |
| `tempfile` | For temporary file management |
| `chrono` | For timestamp manipulation |

## Feature Flags

No feature flags are currently defined as the crate is not yet implemented, but potential ones could include:

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `interactive` | Enable interactive rebase functionality | Additional UI-related dependencies |
| `merge-backend` | Use merge-based backend for rebase | Additional merge-related dependencies |
| `apply-backend` | Use apply-based backend for rebase | Additional patch-related dependencies |

## Examples

While there is no implementation yet, here's an example of how the API might look based on Git rebase functionality:

```rust
use gix_rebase::{Rebase, RebaseOptions, RebaseMode};
use std::path::Path;

// Standard rebase example
fn rebase_branch(
    repo_path: &Path,
    branch: &str,
    onto: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Resolve references
    let branch_ref = repo.find_reference(branch)?;
    let branch_commit = branch_ref.peel_to_commit()?;
    
    let onto_ref = repo.find_reference(onto)?;
    let onto_commit = onto_ref.peel_to_commit()?;
    
    // Set up rebase options
    let options = RebaseOptions {
        mode: RebaseMode::Standard,
        strategy: gix_rebase::MergeStrategy::Recursive,
        allow_conflicts: true,
        ..Default::default()
    };
    
    // Start rebase operation
    let mut rebase = Rebase::start(&repo, &onto_commit, &branch_commit, options)?;
    
    // Process each operation
    while let Some(operation) = rebase.next()? {
        match operation.apply() {
            Ok(_) => {
                println!("Applied commit: {}", operation.id());
            },
            Err(err) => {
                if err.is_conflict() {
                    println!("Conflict detected in file: {}", err.path().display());
                    // Resolve conflict manually or abort
                    // ...
                    
                    // After resolving:
                    rebase.continue_operation()?;
                } else {
                    return Err(err.into());
                }
            }
        }
    }
    
    // Finish rebase
    let result = rebase.finish()?;
    println!("Rebase complete. New HEAD: {}", result.new_head);
    
    Ok(())
}

// Interactive rebase example
fn interactive_rebase(
    repo_path: &Path,
    commit: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Resolve commit
    let commit_obj = repo.rev_parse_single(commit)?.peel_to_commit()?;
    
    // Start interactive rebase
    let mut rebase = gix_rebase::interactive(&repo, &commit_obj, Default::default())?;
    
    // Get the todo list
    let mut todo = rebase.todo_list()?;
    
    // Edit the todo list (e.g., squash, drop, reorder commits)
    todo.squash(1, 2)?; // Squash second commit into first
    todo.drop(3)?;      // Drop the fourth commit
    
    // Apply the modified todo list
    rebase.set_todo_list(todo)?;
    
    // Process the operations
    while let Some(operation) = rebase.next()? {
        match operation.action() {
            gix_rebase::RebaseAction::Pick => {
                // Apply the commit
                operation.apply()?;
            },
            gix_rebase::RebaseAction::Edit => {
                // Apply the commit and pause for manual editing
                operation.apply()?;
                println!("Paused at commit {}. Make your changes and continue.", operation.id());
                return Ok(());  // Exit to allow user to make changes
            },
            // Handle other actions...
            _ => operation.apply()?,
        }
    }
    
    // Finish rebase
    let result = rebase.finish()?;
    println!("Interactive rebase complete. New HEAD: {}", result.new_head);
    
    Ok(())
}
```

## Implementation Details

When implemented, the `gix-rebase` crate will need to address several aspects of Git rebase functionality:

1. **State Management**: Handling of rebase state to enable operations like continue, abort, and skip. This will involve:
   - Tracking in-progress rebases
   - Saving and restoring state after conflicts
   - Managing temporary files

2. **Backends**: Implementation of both rebase backends:
   - **Apply Backend**: A patch-based approach that generates patches and applies them
   - **Merge Backend**: A commit-by-commit approach that's more flexible for interactive rebases

3. **Interactive Rebase**: Support for interactive rebase functionality:
   - Todo list parsing and editing
   - Action execution (pick, reword, edit, squash, etc.)
   - Handling of exec commands

4. **Conflict Resolution**: Mechanisms for detecting and handling conflicts:
   - Conflict detection
   - Conflict state tracking
   - Resolution validation

5. **Branch Management**: Safe handling of references during rebase:
   - Detaching HEAD for rebase operations
   - Updating branch references
   - Handling special refs (ORIG_HEAD, etc.)

6. **Edge Cases**: Handling of special scenarios:
   - Empty commits
   - Merge commits
   - Root commits
   - Non-linear history

## Testing Strategy

When the crate is implemented, the testing strategy will likely include:

1. **Unit Tests**: Tests for individual components:
   - State management
   - Todo list parsing and manipulation
   - Patch generation and application

2. **Integration Tests**: Tests for complete rebase operations:
   - Standard rebase
   - Interactive rebase
   - Rebase onto

3. **Edge Case Tests**: Tests for handling special cases:
   - Conflict scenarios
   - Interrupted rebases
   - Complex repository structures

4. **Comparison Tests**: Tests comparing results with Git's implementation:
   - Verifying that the same input produces the same output
   - Ensuring compatibility with Git's rebase implementation

## Future Development

The `gix-rebase` crate is reserved for future development within the gitoxide project. When implemented, it will provide a Rust-native interface for performing Git rebase operations, enabling applications to manipulate commit history in a flexible and efficient manner. The implementation is expected to follow Git's rebase functionality closely, providing a familiar and reliable experience for users while leveraging the benefits of Rust's safety and performance.