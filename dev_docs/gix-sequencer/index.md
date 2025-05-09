# gix-sequencer

## Overview

`gix-sequencer` is a dedicated crate in the gitoxide ecosystem that handles sequences of human-aided operations in Git repositories. It provides the infrastructure for managing operations like cherry-pick and revert, especially in scenarios where these operations need to be applied in sequence and may encounter conflicts requiring human intervention.

## Architecture

The `gix-sequencer` crate is designed to replicate and improve upon Git's native sequencer functionality. It manages the state of sequential operations, allowing them to be paused, resumed, skipped, aborted, or quit at any point during execution.

This crate is currently in an early stage of development (version 0.0.0), serving as a placeholder for future implementation of Git's sequencer functionality. When fully implemented, it will provide a robust infrastructure for operations like cherry-pick, revert, and potentially interactive rebase, which require managing a sequence of commits and potentially handling conflicts between them.

## Core Components

The following components are expected in the future implementation:

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Sequencer` | The main struct managing the state of sequential operations | Central control point for sequence operations |
| `SequencerState` | Represents the current state of an ongoing sequence | Stored between operations to maintain continuity |
| `SequencerCommand` | Represents a command to be executed in a sequence | Used for operations like cherry-pick, revert |
| `SequencerOptions` | Configuration options for sequencer operations | Controls behavior like auto-stashing, conflict handling |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `SequencerOperation` | Defines operations that can be executed in sequence | `CherryPick`, `Revert` would implement this |
| `ConflictHandler` | Defines how conflicts are handled during sequence execution | Various conflict resolution strategies |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `continue_operation` | Continues a paused sequence operation | `fn continue_operation(state: &SequencerState) -> Result<(), Error>` |
| `skip_current` | Skips the current operation in the sequence | `fn skip_current(state: &mut SequencerState) -> Result<(), Error>` |
| `abort_sequence` | Aborts the entire sequence, restoring original state | `fn abort_sequence(state: &SequencerState) -> Result<(), Error>` |
| `quit_sequence` | Quits the sequence but keeps changes applied so far | `fn quit_sequence(state: &SequencerState) -> Result<(), Error>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `SequencerCommandType` | The type of command in the sequence | `CherryPick`, `Revert`, `Merge` |
| `SequencerStatus` | Current status of the sequencer | `InProgress`, `Paused`, `Completed`, `Failed` |
| `ConflictResolutionStrategy` | How to handle conflicts | `Manual`, `Automatic`, `ThreeWay` |

## Dependencies

Since the crate is in a very early stage, the following dependencies are projected for future implementation:

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | For object hash handling |
| `gix-object` | For Git object manipulation |
| `gix-repository` | For repository access |
| `gix-index` | For index file handling during conflict resolution |
| `gix-worktree` | For worktree interaction during operations |
| `gix-diff` | For calculating differences during operations |
| `gix-tempfile` | For handling temporary files during operations |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `thiserror` | For error handling |
| `serde` | For serialization/deserialization of sequencer state |
| `bstr` | For efficient byte string handling |

## Feature Flags

Potential future feature flags:

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `interactive` | Enables interactive mode for sequencer operations | UI components |
| `async` | Enables async API for sequencer operations | Async runtime |
| `thread-safe` | Enables thread-safe implementation | Synchronization primitives |

## Examples

Future implementation might support operations like:

```rust
// Example: Cherry-pick a range of commits
let repo = gix::open("/path/to/repo")?;
let mut sequencer = gix_sequencer::Sequencer::new(&repo)?;

// Add operations to the sequence
sequencer.add_cherry_pick("abc123")?;
sequencer.add_cherry_pick("def456")?;
sequencer.add_cherry_pick("ghi789")?;

// Execute the sequence
let result = sequencer.execute()?;

// If conflicts occurred and were resolved
if result.has_conflicts() {
    sequencer.continue_operation()?;
}
```

## Implementation Details

The Git sequencer manages sequential operations like cherry-pick and revert, handling the state of these operations and allowing them to be paused and resumed when conflicts occur. The sequencer ensures that operations can be:

1. **Continued**: After resolving conflicts, the operation can be continued from where it left off
2. **Skipped**: The current operation can be skipped, and the sequence can continue with the next operation
3. **Aborted**: The entire sequence can be aborted, and the repository state restored
4. **Quit**: The sequence can be abandoned without undoing changes already applied

The sequencer maintains a state file that tracks:
- The type of operation being performed
- The commits involved in the operation
- The current position in the sequence
- Any options specified for the operation

For cherry-pick operations, the sequencer applies each commit in sequence, potentially creating a new commit for each successful cherry-pick. If conflicts occur, the sequencer pauses, allowing the user to resolve the conflicts before continuing the sequence.

For revert operations, the sequencer works similarly but creates commits that undo the changes of the specified commits.

## Testing Strategy

While the crate is in early development, a comprehensive testing strategy would include:

1. **Unit Tests**: For individual components and functions
2. **Integration Tests**: Testing the sequencer with various repository states
3. **Conflict Tests**: Ensuring the sequencer handles conflicts correctly
4. **Stress Tests**: Testing the sequencer with large sequences of operations
5. **Comparison Tests**: Ensuring behavior matches Git's native sequencer

The test suite would verify that the sequencer:
- Correctly maintains state between operations
- Handles conflicts appropriately
- Can be continued, skipped, aborted, or quit at any point
- Correctly applies operations in sequence
- Maintains repository integrity throughout the process