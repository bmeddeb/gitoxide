# gix-sequencer Use Cases

This document describes common use cases for the `gix-sequencer` crate, focusing on how it can be used to manage sequential operations in Git repositories.

## Intended Audience

- Git client developers integrating with the gitoxide ecosystem
- Library consumers implementing Git functionality
- Advanced users building custom Git workflows
- Developers working on repository management tools

## Use Case 1: Cherry-picking Multiple Commits

### Problem

A developer needs to cherry-pick a sequence of commits from one branch to another, possibly encountering conflicts along the way.

### Solution

The `gix-sequencer` crate provides infrastructure for cherry-picking multiple commits in sequence, handling conflicts, and allowing the process to be paused and resumed.

```rust
// Create a new sequencer for a repository
let repo = gix::open("/path/to/repo")?;
let mut sequencer = gix_sequencer::Sequencer::new(&repo)?;

// Add a sequence of cherry-pick operations for specific commits
sequencer.add_cherry_pick("abc123")?;
sequencer.add_cherry_pick("def456")?;
sequencer.add_cherry_pick("ghi789")?;

// Configure sequencer options
let options = gix_sequencer::Options::new()
    .auto_stash(true)
    .allow_empty(false)
    .mainline(1);

// Execute the sequence with options
let result = sequencer.execute(options)?;

// Check if there are any conflicts
if result.status() == gix_sequencer::Status::Paused {
    println!("Please resolve conflicts and continue");
    
    // After conflicts are resolved manually
    sequencer.continue_operation()?;
}

println!("Cherry-pick sequence completed successfully!");
```

## Use Case 2: Reverting Multiple Commits

### Problem

A series of problematic commits have been pushed to the main branch, and they need to be reverted systematically.

### Solution

The sequencer can be used to revert multiple commits in sequence, creating new commits that undo the changes.

```rust
// Create a new sequencer for a repository
let repo = gix::open("/path/to/repo")?;
let mut sequencer = gix_sequencer::Sequencer::new(&repo)?;

// Add a sequence of revert operations in reverse chronological order
sequencer.add_revert("latest123")?;
sequencer.add_revert("middle456")?;
sequencer.add_revert("earliest789")?;

// Configure sequencer options
let options = gix_sequencer::Options::new()
    .edit_commit_messages(true)
    .gpg_sign(true);

// Execute the sequence
match sequencer.execute(options) {
    Ok(_) => println!("All commits reverted successfully!"),
    Err(gix_sequencer::Error::Conflict) => {
        println!("Conflicts detected. Please resolve them.");
        
        // To skip the current conflicting revert and move to the next
        sequencer.skip_current()?;
        
        // Or to abort the entire sequence
        // sequencer.abort()?;
    },
    Err(e) => return Err(e.into()),
}
```

## Use Case 3: Interactive Rebase with Complex Operations

### Problem

A developer needs to clean up a feature branch history before merging, involving multiple operations like editing, squashing, and reordering commits.

### Solution

The sequencer provides infrastructure for complex interactive rebase operations, supporting a variety of commit manipulations.

```rust
// Create a new sequencer for a repository
let repo = gix::open("/path/to/repo")?;
let mut sequencer = gix_sequencer::Sequencer::new(&repo)?;

// Define a series of rebase operations
let operations = vec![
    gix_sequencer::RebaseOperation::pick("abc123"),
    gix_sequencer::RebaseOperation::squash("def456"),
    gix_sequencer::RebaseOperation::edit("ghi789"),
    gix_sequencer::RebaseOperation::reword("jkl012"),
    gix_sequencer::RebaseOperation::fixup("mno345"),
];

// Setup the rebase sequence
sequencer.setup_rebase("HEAD~5", "HEAD", operations)?;

// Execute the sequence
let result = sequencer.execute_rebase()?;

// If an edit operation is encountered, the sequence pauses
if result.status() == gix_sequencer::Status::EditRequested {
    println!("Paused for editing commit {}", result.current_commit());
    
    // Make changes to files...
    
    // Amend the current commit and continue
    let repo = sequencer.repository();
    repo.amend_commit()?;
    sequencer.continue_operation()?;
}

println!("Interactive rebase completed!");
```

## Use Case 4: Automated Conflict Resolution

### Problem

When cherry-picking or reverting multiple commits, conflicts may arise that need to be resolved automatically according to certain rules.

### Solution

The sequencer can be configured with conflict resolution strategies to handle conflicts automatically when possible.

```rust
// Create a new sequencer for a repository
let repo = gix::open("/path/to/repo")?;
let mut sequencer = gix_sequencer::Sequencer::new(&repo)?;

// Add cherry-pick operations
sequencer.add_cherry_pick("abc123")?;
sequencer.add_cherry_pick("def456")?;

// Configure with automatic conflict resolution strategy
let strategy = gix_sequencer::ConflictStrategy::new()
    .on_conflict(gix_sequencer::ConflictAction::TakeOurs)
    .for_path("src/specific_file.rs", gix_sequencer::ConflictAction::TakeTheirs)
    .for_path("README.md", gix_sequencer::ConflictAction::Merge);

let options = gix_sequencer::Options::new()
    .conflict_strategy(strategy);

// Execute with automatic conflict resolution
match sequencer.execute(options) {
    Ok(_) => println!("Sequence completed with automatic conflict resolution!"),
    Err(gix_sequencer::Error::ManualResolutionRequired) => {
        println!("Some conflicts could not be resolved automatically.");
        // Handle manual resolution
    },
    Err(e) => return Err(e.into()),
}
```

## Use Case 5: Recovery from Interrupted Operations

### Problem

A cherry-pick or revert sequence may be interrupted by system shutdown, and the state needs to be recovered.

### Solution

The sequencer persists its state, allowing operations to be recovered and continued after interruptions.

```rust
// Try to load an existing sequencer state
let repo = gix::open("/path/to/repo")?;
match gix_sequencer::Sequencer::load_state(&repo) {
    Ok(mut sequencer) => {
        println!("Recovered sequencer state: {:?}", sequencer.status());
        
        // Continue, skip, or abort based on user choice
        match user_choice() {
            Choice::Continue => sequencer.continue_operation()?,
            Choice::Skip => sequencer.skip_current()?,
            Choice::Abort => sequencer.abort()?,
            Choice::Quit => sequencer.quit()?,
        }
    },
    Err(_) => {
        println!("No sequencer state found, starting fresh.");
        let sequencer = gix_sequencer::Sequencer::new(&repo)?;
        // Setup new sequence...
    }
}
```

## Use Case 6: Custom Sequencing Operations

### Problem

A developer needs to implement a custom sequence of operations that isn't covered by standard Git commands.

### Solution

The sequencer architecture can be extended with custom operations that implement the `SequencerOperation` trait.

```rust
// Define a custom sequencer operation
struct CustomOperation {
    target_commit: String,
    // other fields...
}

impl gix_sequencer::SequencerOperation for CustomOperation {
    fn apply(&self, repo: &gix::Repository) -> Result<(), Error> {
        // Implementation of the custom operation
        // ...
        Ok(())
    }
    
    fn describe(&self) -> String {
        format!("Custom operation on commit {}", self.target_commit)
    }
}

// Use the custom operation with the sequencer
let repo = gix::open("/path/to/repo")?;
let mut sequencer = gix_sequencer::Sequencer::new(&repo)?;

// Add standard and custom operations to the sequence
sequencer.add_cherry_pick("abc123")?;
sequencer.add_operation(CustomOperation {
    target_commit: "def456".to_string(),
    // other fields...
})?;
sequencer.add_revert("ghi789")?;

// Execute the mixed sequence
sequencer.execute(gix_sequencer::Options::default())?;
```

## Summary

The `gix-sequencer` crate provides a flexible framework for managing sequences of operations in Git repositories, particularly focusing on operations like cherry-pick, revert, and potentially interactive rebase. It offers:

1. **Sequential Execution**: Apply multiple operations in sequence
2. **State Management**: Pause, resume, skip, abort, or quit sequences
3. **Conflict Handling**: Strategies for resolving conflicts automatically or manually
4. **Persistence**: Recovery from interrupted operations
5. **Extensibility**: Support for custom sequencing operations

These capabilities make the crate valuable for implementing Git clients, repository management tools, and custom Git workflows that involve sequences of potentially conflicting operations.