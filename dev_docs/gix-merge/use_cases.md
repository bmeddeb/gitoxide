# gix-merge Use Cases

This document outlines the primary use cases for the `gix-merge` crate in the gitoxide ecosystem, along with code examples demonstrating how to address each use case.

## Intended Audience

- Rust developers implementing Git functionality
- Contributors to gitoxide working on merge-related features
- Developers building tools that require Git-compatible merge capabilities
- Users needing fine-grained control over Git merge operations

## Use Cases

### 1. Merging File Content (Blob Merge)

**Problem**: You need to perform a three-way merge of file content, similar to Git's internal merge mechanism.

**Solution**: Use the blob merge functionality with the appropriate driver.

```rust
use bstr::ByteSlice;
use gix_merge::blob::{self, Platform, BuiltinDriver};
use gix_object::Find;
use gix_hash::ObjectId;
use gix_filter::Pipeline;
use gix_worktree::Stack;

// Set up a merge platform for handling blob merges
fn setup_merge_platform<F: Find + 'static>(
    objects: F, 
    attr_stack: Stack
) -> Platform {
    // Create a pipeline for converting objects
    let filter_pipeline = Pipeline::new_with_attributes(attr_stack.clone());
    
    // Set up the worktree roots (not needed for in-memory merges)
    let roots = blob::pipeline::WorktreeRoots::default();
    
    // Create a pipeline for object conversion
    let pipeline = blob::Pipeline {
        roots,
        filter: filter_pipeline,
        options: blob::pipeline::Options::default(),
        path: Default::default(),
    };
    
    // Create the platform with all necessary components
    let mut platform = Platform {
        filter: pipeline,
        attr_stack,
        options: blob::platform::Options::default(),
        filter_mode: blob::pipeline::Mode::BlobToBlob,
        ..Default::default()
    };
    
    // Register the built-in drivers
    platform.register_builtin_driver(BuiltinDriver::Text);
    platform.register_builtin_driver(BuiltinDriver::Binary);
    platform.register_builtin_driver(BuiltinDriver::Union);
    
    platform
}

// Perform a three-way merge of blob content
fn merge_blobs<F: Find + 'static>(
    objects: F,
    attr_stack: Stack,
    base_id: &ObjectId,
    our_id: &ObjectId,
    their_id: &ObjectId,
    path: &[u8],
) -> Result<(Vec<u8>, blob::Resolution), Box<dyn std::error::Error>> {
    let mut platform = setup_merge_platform(objects.clone(), attr_stack);
    
    // Set the resources to merge
    platform.set_resource_from_object(blob::ResourceKind::CommonAncestorOrBase, base_id, objects.clone())?;
    platform.set_resource_from_object(blob::ResourceKind::CurrentOrOurs, our_id, objects.clone())?;
    platform.set_resource_from_object(blob::ResourceKind::OtherOrTheirs, their_id, objects.clone())?;
    
    // Prepare the merge with the given path (for determining merge driver)
    let merge_ref = platform.prepare_merge(path.as_bstr())?;
    
    // Execute the merge
    let merge_result = merge_ref.merge()?;
    
    // Get the merged content and resolution status
    let merged_content = merge_result.output().to_owned();
    let resolution = merge_result.resolution();
    
    Ok((merged_content, resolution))
}

// Usage example
fn handle_merge_result(
    merged_content: Vec<u8>, 
    resolution: blob::Resolution
) {
    match resolution {
        blob::Resolution::Complete => {
            println!("Merge completed successfully without conflicts");
        },
        blob::Resolution::CompleteWithAutoResolvedConflict => {
            println!("Merge completed with auto-resolved conflicts");
        },
        blob::Resolution::Conflict => {
            println!("Merge has conflicts that need manual resolution");
            // The content contains conflict markers
        }
    }
    
    // Do something with the merged content
    println!("Merged content size: {}", merged_content.len());
}
```

### 2. Merging Directory Trees

**Problem**: You need to merge directory trees, handling both structural changes (file additions, deletions, renames) and content changes.

**Solution**: Use the tree merge functionality with appropriate configuration options.

```rust
use gix_hash::ObjectId;
use gix_object::Find;
use gix_merge::tree::{self, TreatAsUnresolved, ResolveWith};
use gix_diff::Rewrites;
use gix_index::State as IndexState;
use std::collections::HashSet;

// Merge two trees with customized conflict resolution settings
fn merge_trees_with_custom_resolution<F: Find + 'static>(
    objects: F,
    base_id: &ObjectId,
    our_id: &ObjectId,
    their_id: &ObjectId,
) -> Result<(ObjectId, Vec<tree::Conflict>), Box<dyn std::error::Error>> {
    // Configure merge options
    let options = tree::Options {
        // Enable rename detection
        rewrites: Some(Rewrites {
            // Track files with similarity 50% or higher
            track_moves: Some(50),
            // Don't track empty files as renames
            track_empty: false,
        }),
        // Configure blob merge options
        blob_merge: gix_merge::blob::platform::merge::Options {
            // Show conflict markers with 7 characters
            marker_size: 7,
            // Resolve binary conflicts by keeping our version
            binary_conflicts: Some(gix_merge::blob::builtin_driver::binary::ResolveWith::Ours),
            ..Default::default()
        },
        // Resolve tree conflicts by choosing our side
        tree_conflicts: Some(ResolveWith::Ours),
        // Don't stop on first conflict
        fail_on_conflict: None,
        ..Default::default()
    };
    
    // Perform the merge
    let merge_result = tree::tree(objects, base_id, our_id, their_id, options)?;
    
    // Check for unresolved conflicts with default criteria
    let has_conflicts = merge_result.has_unresolved_conflicts(TreatAsUnresolved::default());
    
    if has_conflicts {
        println!("Merge has conflicts that need manual resolution");
    } else {
        println!("Merge completed successfully");
    }
    
    // Create ID for the merged tree
    let merged_tree_id = merge_result.tree.write_to()?;
    
    // Return the merged tree ID and any conflicts
    Ok((merged_tree_id, merge_result.conflicts))
}

// Update a Git index with conflict information
fn update_index_with_conflicts(
    index: &mut IndexState,
    conflicts: &[tree::Conflict],
) -> bool {
    // Determine how to treat conflicts as unresolved
    let unresolved_criteria = TreatAsUnresolved {
        // Consider any conflict with markers as unresolved
        content_merge: tree::treat_as_unresolved::ContentMerge::Markers,
        // Consider any conflict with evasive renames as unresolved
        tree_merge: tree::treat_as_unresolved::TreeMerge::EvasiveRenames,
    };
    
    // Apply conflicts to the index, removing conflicting stages
    tree::apply_index_entries(
        conflicts, 
        unresolved_criteria, 
        index, 
        tree::apply_index_entries::RemovalMode::Prune
    )
}

// Collect statistics about conflicts
fn analyze_conflicts(conflicts: &[tree::Conflict]) -> (usize, usize, usize) {
    let mut content_conflicts = 0;
    let mut rename_conflicts = 0;
    let mut other_conflicts = 0;
    
    for conflict in conflicts {
        match &conflict.resolution {
            Ok(resolution) => match resolution {
                tree::Resolution::OursModifiedTheirsModifiedThenBlobContentMerge { merged_blob }
                    if merged_blob.resolution == gix_merge::blob::Resolution::Conflict => {
                    content_conflicts += 1;
                }
                tree::Resolution::OursModifiedTheirsRenamedAndChangedThenRename { .. } => {
                    rename_conflicts += 1;
                }
                _ => {}
            },
            Err(_) => {
                other_conflicts += 1;
            }
        }
    }
    
    (content_conflicts, rename_conflicts, other_conflicts)
}
```

### 3. Merging Commits

**Problem**: You need to perform a full commit merge, including finding the common ancestor (merge base) and merging the trees.

**Solution**: Use the commit merge functionality, which handles merge base detection and tree merging in one operation.

```rust
use gix_hash::ObjectId;
use gix_object::Find;
use gix_merge::{commit, tree};
use gix_revision::merge_base;
use std::collections::HashSet;

// Perform a commit merge with detailed output about the merge process
fn merge_commits_with_details<F: Find + 'static>(
    objects: F,
    our_commit_id: &ObjectId,
    their_commit_id: &ObjectId,
) -> Result<CommitMergeResult, Box<dyn std::error::Error>> {
    // Configure merge options
    let options = commit::Options {
        // Allow merge of unrelated histories
        allow_missing_merge_base: true,
        // Use a merged version of multiple merge bases if they exist
        use_first_merge_base: false,
        // Configure tree merge options
        tree_merge: tree::Options {
            // Enable rename detection
            rewrites: Some(gix_diff::Rewrites::default()),
            // Don't stop on first conflict
            fail_on_conflict: None,
            ..Default::default()
        },
    };
    
    // Create a function to find merge bases
    let base_finder = |ours, theirs| {
        merge_base::all(objects.clone(), ours, theirs)
    };
    
    // Perform the merge
    let merge_result = commit::commit(objects.clone(), base_finder, our_commit_id, their_commit_id, options)?;
    
    // Gather information about the merge
    let mut result = CommitMergeResult {
        merged_tree_id: merge_result.tree_merge.tree.write_to()?,
        merge_base_tree_id: merge_result.merge_base_tree_id,
        merge_bases: merge_result.merge_bases.unwrap_or_default(),
        virtual_merge_bases: merge_result.virtual_merge_bases,
        conflicts: merge_result.tree_merge.conflicts,
    };
    
    // Check for conflicts based on different criteria
    result.has_conflicts = merge_result.tree_merge.has_unresolved_conflicts(tree::TreatAsUnresolved::default());
    result.has_forced_resolution_conflicts = merge_result.tree_merge.has_unresolved_conflicts(tree::TreatAsUnresolved::forced_resolution());
    
    Ok(result)
}

// A structure to hold commit merge results
struct CommitMergeResult {
    merged_tree_id: ObjectId,
    merge_base_tree_id: ObjectId,
    merge_bases: Vec<ObjectId>,
    virtual_merge_bases: Vec<ObjectId>,
    conflicts: Vec<tree::Conflict>,
    has_conflicts: bool,
    has_forced_resolution_conflicts: bool,
}

// Create a commit with the merge result
fn create_merge_commit<F: Find + 'static>(
    objects: F,
    result: &CommitMergeResult,
    our_commit_id: &ObjectId,
    their_commit_id: &ObjectId,
    author: &str,
    committer: &str,
    message: &str,
) -> Result<ObjectId, Box<dyn std::error::Error>> {
    // Create a new commit
    let commit = gix_object::Commit {
        tree: result.merged_tree_id,
        parents: vec![our_commit_id.to_owned(), their_commit_id.to_owned()],
        author: gix_actor::Signature::from_bytes(author.as_bytes())?.0,
        committer: gix_actor::Signature::from_bytes(committer.as_bytes())?.0,
        encoding: None,
        message: message.into(),
    };
    
    // Write the commit to the object database
    let id = objects.write(&commit.to_object())?;
    
    Ok(id)
}
```

### 4. Implementing a Custom Merge Driver

**Problem**: You need to implement a custom merge strategy for specific file types that Git's built-in merge drivers don't handle well.

**Solution**: Register a custom merge driver and use it for files matching specific patterns in `.gitattributes`.

```rust
use bstr::{BString, ByteSlice};
use gix_merge::blob::{Driver, Platform};
use std::path::Path;

// Register a custom merge driver for specific file types
fn register_custom_driver(platform: &mut Platform) {
    // Create a custom driver for merging XML files
    let xml_driver = Driver {
        // Name used in .gitattributes (merge=xml-merge)
        name: BString::from("xml-merge"),
        // Display name for user interfaces
        display_name: BString::from("XML Structure-Aware Merge"),
        // Command to execute (with placeholders)
        command: BString::from("xml-merge-tool %O %A %B %P"),
        // Use the text driver for recursive merges
        recursive: Some(BString::from("text")),
    };
    
    // Register the driver
    platform.register_driver(xml_driver);
    
    // Create a custom driver for merging JSON files
    let json_driver = Driver {
        name: BString::from("json-merge"),
        display_name: BString::from("JSON Structure-Aware Merge"),
        command: BString::from("json-merge-tool %O %A %B --output=%A"),
        recursive: None,
    };
    
    // Register the driver
    platform.register_driver(json_driver);
}

// Simulate the lookup of a merge driver based on path (like Git would do with attributes)
fn get_driver_for_path(path: &Path) -> Option<String> {
    let extension = path.extension()?.to_str()?;
    
    match extension {
        "xml" => Some("xml-merge".to_string()),
        "json" => Some("json-merge".to_string()),
        _ => None,
    }
}

// Use a custom driver for merging a specific file
fn merge_with_custom_driver(
    platform: &mut Platform,
    base_content: &[u8],
    our_content: &[u8],
    their_content: &[u8],
    path: &Path,
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Set resources manually with content
    platform.set_resource_content(gix_merge::blob::ResourceKind::CommonAncestorOrBase, base_content)?;
    platform.set_resource_content(gix_merge::blob::ResourceKind::CurrentOrOurs, our_content)?;
    platform.set_resource_content(gix_merge::blob::ResourceKind::OtherOrTheirs, their_content)?;
    
    // Look up the driver to use based on path
    let driver_name = get_driver_for_path(path);
    
    // Prepare merge with the path
    let path_str = path.to_str().unwrap_or_default();
    let merge_ref = platform.prepare_merge_with_driver(
        path_str.as_bytes().as_bstr(),
        driver_name.as_deref()
    )?;
    
    // Perform the merge
    let merge_result = merge_ref.merge()?;
    
    // Get the merged content
    let merged_content = merge_result.output().to_owned();
    
    Ok(merged_content)
}
```

### 5. Detecting and Handling Specific Conflict Types

**Problem**: You need to detect and handle specific types of merge conflicts in a custom way.

**Solution**: Analyze the conflicts returned by the merge operation and implement custom resolution strategies.

```rust
use gix_hash::ObjectId;
use gix_object::Find;
use gix_merge::tree::{self, Conflict, Resolution, ResolutionFailure};
use std::collections::HashSet;

// Categorize conflicts by type for custom handling
fn categorize_conflicts(conflicts: &[Conflict]) -> ConflictCategories {
    let mut categories = ConflictCategories::default();
    
    for conflict in conflicts {
        match &conflict.resolution {
            Ok(resolution) => match resolution {
                Resolution::OursModifiedTheirsModifiedThenBlobContentMerge { merged_blob } => {
                    match merged_blob.resolution {
                        gix_merge::blob::Resolution::Conflict => {
                            categories.content_conflicts.push(conflict.clone());
                        }
                        _ => {
                            categories.auto_resolved.push(conflict.clone());
                        }
                    }
                }
                Resolution::OursModifiedTheirsRenamedAndChangedThenRename { .. } => {
                    categories.rename_conflicts.push(conflict.clone());
                }
                Resolution::SourceLocationAffectedByRename { .. } => {
                    categories.directory_renamed_conflicts.push(conflict.clone());
                }
                Resolution::Forced(_) => {
                    categories.forced_resolutions.push(conflict.clone());
                }
            },
            Err(failure) => match failure {
                ResolutionFailure::OursRenamedTheirsRenamedDifferently { .. } => {
                    categories.divergent_renames.push(conflict.clone());
                }
                ResolutionFailure::OursModifiedTheirsDeleted => {
                    categories.modify_delete_conflicts.push(conflict.clone());
                }
                ResolutionFailure::OursAddedTheirsAddedTypeMismatch { .. } => {
                    categories.type_conflicts.push(conflict.clone());
                }
                _ => {
                    categories.other_conflicts.push(conflict.clone());
                }
            },
        }
    }
    
    categories
}

// A structure to categorize different types of conflicts
#[derive(Default)]
struct ConflictCategories {
    content_conflicts: Vec<Conflict>,
    rename_conflicts: Vec<Conflict>,
    directory_renamed_conflicts: Vec<Conflict>,
    divergent_renames: Vec<Conflict>,
    modify_delete_conflicts: Vec<Conflict>,
    type_conflicts: Vec<Conflict>,
    forced_resolutions: Vec<Conflict>,
    auto_resolved: Vec<Conflict>,
    other_conflicts: Vec<Conflict>,
}

// Generate a human-readable report about merge conflicts
fn generate_conflict_report(categories: &ConflictCategories) -> String {
    let mut report = String::new();
    
    report.push_str(&format!("Merge Conflict Report\n"));
    report.push_str(&format!("====================\n\n"));
    
    report.push_str(&format!("Content conflicts: {}\n", categories.content_conflicts.len()));
    report.push_str(&format!("Rename conflicts: {}\n", categories.rename_conflicts.len()));
    report.push_str(&format!("Directory renamed conflicts: {}\n", categories.directory_renamed_conflicts.len()));
    report.push_str(&format!("Divergent renames: {}\n", categories.divergent_renames.len()));
    report.push_str(&format!("Modify/delete conflicts: {}\n", categories.modify_delete_conflicts.len()));
    report.push_str(&format!("Type conflicts: {}\n", categories.type_conflicts.len()));
    report.push_str(&format!("Forced resolutions: {}\n", categories.forced_resolutions.len()));
    report.push_str(&format!("Auto-resolved conflicts: {}\n", categories.auto_resolved.len()));
    report.push_str(&format!("Other conflicts: {}\n\n", categories.other_conflicts.len()));
    
    // Detail each content conflict
    if !categories.content_conflicts.isEmpty() {
        report.push_str("Content Conflicts:\n");
        report.push_str("-----------------\n");
        for (i, conflict) in categories.content_conflicts.iter().enumerate() {
            let (ours, theirs) = conflict.changes_in_resolution();
            report.push_str(&format!("{}. Path: {}\n", i+1, ours.location().to_str_lossy()));
            report.push_str(&format!("   Our change: {}\n", describe_change(ours)));
            report.push_str(&format!("   Their change: {}\n", describe_change(theirs)));
            report.push_str("\n");
        }
    }
    
    // Similar sections for other conflict types...
    
    report
}

// Helper to describe a change in human-readable form
fn describe_change(change: &gix_diff::tree_with_rewrites::Change) -> String {
    use gix_diff::tree_with_rewrites::Change;
    
    match change {
        Change::Addition { mode, id, .. } => {
            format!("Added as {} with ID {}", mode, id)
        }
        Change::Deletion { mode, id, .. } => {
            format!("Deleted (was {} with ID {})", mode, id)
        }
        Change::Modification { mode, id, old_id, old_mode, .. } => {
            format!("Modified from {} ({}) to {} ({})", 
                old_mode, old_id, 
                mode.unwrap_or(*old_mode), id.unwrap_or(*old_id))
        }
        Change::Type { mode, id, old_id, old_mode, .. } => {
            format!("Changed type from {} ({}) to {} ({})", 
                old_mode, old_id, 
                mode, id)
        }
        _ => "Complex change".to_string(),
    }
}
```

## Best Practices

### 1. Configuring Merge Sensitivity

When setting up merge operations, consider the sensitivity level for conflicts:

```rust
// Default Git settings
let git_standard = tree::TreatAsUnresolved::git();

// Most lenient: only completely undecidable merges are conflicts
let lenient = tree::TreatAsUnresolved::undecidable();

// Most strict: any forced resolution is considered a conflict
let strict = tree::TreatAsUnresolved::forced_resolution();

// Custom configuration
let custom = tree::TreatAsUnresolved {
    // Treat content merges with conflict markers as unresolved
    content_merge: tree::treat_as_unresolved::ContentMerge::Markers,
    // Treat tree merges with evasive renames as unresolved
    tree_merge: tree::treat_as_unresolved::TreeMerge::EvasiveRenames,
};
```

### 2. Handling Rename Detection

Rename detection is crucial for high-quality merges but has performance implications. Configure it appropriately:

```rust
// Basic rename detection (50% similarity threshold)
let basic_rename_detection = Some(gix_diff::Rewrites {
    track_moves: Some(50),
    track_empty: false,
});

// Aggressive rename detection (lower threshold catches more renames)
let aggressive_rename_detection = Some(gix_diff::Rewrites {
    track_moves: Some(30),
    track_empty: false,
});

// Disable rename detection for performance in large merges
let no_rename_detection = None;

// Choose based on repository and merge needs
let rewrites = if repo_is_very_large {
    no_rename_detection
} else if contains_many_renames {
    aggressive_rename_detection
} else {
    basic_rename_detection
};
```

### 3. Selecting Resolution Strategies

Choose appropriate resolution strategies based on merge context:

```rust
// In a fast-forward merge context (should never have conflicts)
let ff_merge_options = tree::Options {
    // No need for failure handling as there shouldn't be conflicts
    fail_on_conflict: Some(tree::TreatAsUnresolved::default()),
    ..Default::default()
};

// In an automated merge context (e.g., CI)
let automated_merge_options = tree::Options {
    // Choose our side for anything that can't be auto-merged
    tree_conflicts: Some(tree::ResolveWith::Ours),
    blob_merge: blob::platform::merge::Options {
        // Choose our side for binary conflicts
        binary_conflicts: Some(blob::builtin_driver::binary::ResolveWith::Ours),
        ..Default::default()
    },
    ..Default::default()
};

// In an interactive merge context
let interactive_merge_options = tree::Options {
    // Don't force-resolve anything, let the user handle conflicts
    tree_conflicts: None,
    blob_merge: blob::platform::merge::Options {
        // Don't auto-resolve binary conflicts
        binary_conflicts: None,
        ..Default::default()
    },
    ..Default::default()
};
```

### 4. Efficient Index Handling

When updating the Git index with conflict information:

```rust
// For interactive use, just mark entries for removal
// This preserves the original index structure for inspection
let interactive_mode = tree::apply_index_entries::RemovalMode::Mark;

// For automated processing, fully prune conflicting entries
// This ensures a clean index state
let automated_mode = tree::apply_index_entries::RemovalMode::Prune;

// Apply conflicts to index
let index_changed = tree::apply_index_entries(
    &merge_result.conflicts,
    tree::TreatAsUnresolved::default(),
    &mut index,
    automated_mode
);
```

### 5. Virtual Merge Base Handling

When dealing with multiple merge bases:

```rust
// Check for multiple merge bases
fn handle_merge_bases<F: Find + 'static>(
    objects: F,
    ours: &ObjectId,
    theirs: &ObjectId,
) -> Result<ObjectId, Box<dyn std::error::Error>> {
    // Find all merge bases
    let merge_bases = gix_revision::merge_base::all(objects.clone(), ours, theirs)?;
    
    match merge_bases.len() {
        0 => {
            // No merge base - unrelated histories
            // Return empty tree ID for merge
            Ok(gix_object::empty_tree_id())
        }
        1 => {
            // Single merge base - use directly
            Ok(merge_bases[0])
        }
        _ => {
            // Multiple merge bases - create virtual merge base
            let virtual_base = gix_merge::commit::virtual_merge_base(
                objects,
                &merge_bases,
                gix_merge::tree::Options::default(),
            )?;
            
            Ok(virtual_base)
        }
    }
}
```

## Conclusion

The `gix-merge` crate provides a comprehensive and flexible implementation of Git merge algorithms, allowing for fine-grained control over the merge process. By understanding the different levels of merge functionality (blob, tree, commit) and their respective configuration options, you can implement complex merge operations with custom conflict resolution strategies tailored to your specific needs.