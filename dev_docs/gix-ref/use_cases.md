# gix-ref Use Cases

This document provides practical examples of using the `gix-ref` crate for various Git reference management scenarios.

## Managing Branches

**Problem**: You need to create, list, update, and delete branches in a Git repository.

**Solution**: Use the reference store to manage branches with proper transactions.

```rust
use gix_hash::ObjectId;
use gix_ref::{
    file::Store,
    transaction::{Change, LogChange, PreviousValue, RefEdit, RefLog},
    FullName, Target,
};
use std::path::Path;

/// Create a new branch pointing to a specific commit
fn create_branch(
    repo_path: &Path,
    branch_name: &str,
    commit_id: &str,
    message: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse commit ID
    let target = ObjectId::from_hex(commit_id.as_bytes())?;
    
    // Create branch reference name
    let branch_ref: FullName = format!("refs/heads/{}", branch_name).try_into()?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare the branch creation
    transaction.prepare_edit(RefEdit {
        name: branch_ref,
        change: Change::Update {
            expected: PreviousValue::MustNotExist, // Ensure branch doesn't exist
            log: LogChange {
                mode: RefLog::AndReference,
                force_create_reflog: true, // Always create reflog for branches
                message: message.into(),
            },
            new: Target::Object(target),
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}

/// List all branches in the repository
fn list_branches(repo_path: &Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Create namespace for branches
    let branch_prefix = gix_ref::Namespace::try_from("refs/heads/")?;
    
    // Collect branch names
    let branches = store
        .iter()?
        .prefixed(branch_prefix.as_ref())?
        .filter_map(|result| {
            result.ok().map(|reference| {
                // Extract branch name without refs/heads/ prefix
                reference
                    .name_without_namespace(&branch_prefix)
                    .map(|name| name.as_bstr().to_string())
                    .unwrap_or_default()
            })
        })
        .collect();
    
    Ok(branches)
}

/// Delete a branch
fn delete_branch(
    repo_path: &Path,
    branch_name: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Create branch reference name
    let branch_ref: FullName = format!("refs/heads/{}", branch_name).try_into()?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare the branch deletion
    transaction.prepare_edit(RefEdit {
        name: branch_ref,
        change: Change::Delete {
            expected: PreviousValue::MustExist, // Ensure branch exists
            log: RefLog::AndReference,
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}

/// Rename a branch
fn rename_branch(
    repo_path: &Path,
    old_name: &str,
    new_name: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Create branch reference names
    let old_ref: FullName = format!("refs/heads/{}", old_name).try_into()?;
    let new_ref: FullName = format!("refs/heads/{}", new_name).try_into()?;
    
    // Find the current branch target
    let reference = store.find_one(&old_ref)?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare the branch creation with existing target
    transaction.prepare_edit(RefEdit {
        name: new_ref.clone(),
        change: Change::Update {
            expected: PreviousValue::MustNotExist, // Ensure new branch doesn't exist
            log: LogChange {
                mode: RefLog::AndReference,
                force_create_reflog: true,
                message: format!("Branch: renamed {} to {}", old_name, new_name).into(),
            },
            new: reference.target.clone(),
        },
        deref: false,
    })?;
    
    // Prepare the old branch deletion
    transaction.prepare_edit(RefEdit {
        name: old_ref,
        change: Change::Delete {
            expected: PreviousValue::MustExist, // Ensure old branch exists
            log: RefLog::AndReference,
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}
```

## Working with HEAD

**Problem**: You need to manage the HEAD reference, which represents the current checkout state.

**Solution**: Use symbolic references and transactions to update HEAD.

```rust
use gix_hash::ObjectId;
use gix_ref::{
    file::Store,
    transaction::{Change, LogChange, PreviousValue, RefEdit, RefLog},
    FullName, Target,
};
use std::path::Path;

/// Get the current HEAD reference
fn get_head(repo_path: &Path) -> Result<String, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Find HEAD reference
    let head_ref: FullName = "HEAD".try_into()?;
    let head = store.find_one(&head_ref)?;
    
    // Resolve HEAD to its target
    match head.target {
        Target::Symbolic(ref_name) => {
            // Return branch name
            Ok(ref_name.0.to_string())
        }
        Target::Object(id) => {
            // Detached HEAD state - return commit ID
            Ok(format!("Detached HEAD at {}", id))
        }
    }
}

/// Switch HEAD to a different branch (checkout)
fn checkout_branch(
    repo_path: &Path,
    branch_name: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Get current HEAD to create appropriate log message
    let head_ref: FullName = "HEAD".try_into()?;
    let head = store.find_one(&head_ref)?;
    let current_branch = match head.target {
        Target::Symbolic(ref_name) => ref_name.0.to_string(),
        Target::Object(_) => "detached HEAD".to_string(),
    };
    
    // Create branch reference name
    let branch_ref: FullName = format!("refs/heads/{}", branch_name).try_into()?;
    
    // Verify branch exists
    store.find_one(&branch_ref)?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare HEAD update
    transaction.prepare_edit(RefEdit {
        name: head_ref,
        change: Change::Update {
            expected: PreviousValue::Any,
            log: LogChange {
                mode: RefLog::AndReference,
                force_create_reflog: false,
                message: format!("checkout: moving from {} to {}", current_branch, branch_name).into(),
            },
            new: Target::Symbolic(branch_ref),
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}

/// Detach HEAD to a specific commit
fn detach_head(
    repo_path: &Path,
    commit_id: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse commit ID
    let target = ObjectId::from_hex(commit_id.as_bytes())?;
    
    // Get current HEAD to create appropriate log message
    let head_ref: FullName = "HEAD".try_into()?;
    let head = store.find_one(&head_ref)?;
    let current_branch = match head.target {
        Target::Symbolic(ref_name) => ref_name.0.to_string(),
        Target::Object(_) => "detached HEAD".to_string(),
    };
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare HEAD update to point directly to commit
    transaction.prepare_edit(RefEdit {
        name: head_ref,
        change: Change::Update {
            expected: PreviousValue::Any,
            log: LogChange {
                mode: RefLog::AndReference,
                force_create_reflog: false,
                message: format!("checkout: moving from {} to {}", current_branch, commit_id).into(),
            },
            new: Target::Object(target),
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}
```

## Tag Management

**Problem**: You need to create, list, and delete tags in a Git repository.

**Solution**: Use the reference system to manage tags with proper transactions.

```rust
use gix_hash::ObjectId;
use gix_ref::{
    file::Store,
    transaction::{Change, LogChange, PreviousValue, RefEdit, RefLog},
    FullName, Target,
};
use std::path::Path;

/// Create a new lightweight tag
fn create_tag(
    repo_path: &Path,
    tag_name: &str,
    commit_id: &str,
    message: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse commit ID
    let target = ObjectId::from_hex(commit_id.as_bytes())?;
    
    // Create tag reference name
    let tag_ref: FullName = format!("refs/tags/{}", tag_name).try_into()?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare the tag creation
    transaction.prepare_edit(RefEdit {
        name: tag_ref,
        change: Change::Update {
            expected: PreviousValue::MustNotExist, // Ensure tag doesn't exist
            log: LogChange {
                mode: RefLog::AndReference,
                force_create_reflog: false, // Tags typically don't have reflogs
                message: message.into(),
            },
            new: Target::Object(target),
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}

/// List all tags in the repository
fn list_tags(repo_path: &Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Create namespace for tags
    let tag_prefix = gix_ref::Namespace::try_from("refs/tags/")?;
    
    // Collect tag names
    let tags = store
        .iter()?
        .prefixed(tag_prefix.as_ref())?
        .filter_map(|result| {
            result.ok().map(|reference| {
                // Extract tag name without refs/tags/ prefix
                reference
                    .name_without_namespace(&tag_prefix)
                    .map(|name| name.as_bstr().to_string())
                    .unwrap_or_default()
            })
        })
        .collect();
    
    Ok(tags)
}

/// Delete a tag
fn delete_tag(
    repo_path: &Path,
    tag_name: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Create tag reference name
    let tag_ref: FullName = format!("refs/tags/{}", tag_name).try_into()?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare the tag deletion
    transaction.prepare_edit(RefEdit {
        name: tag_ref,
        change: Change::Delete {
            expected: PreviousValue::MustExist, // Ensure tag exists
            log: RefLog::AndReference,
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}
```

## Working with Reference Logs

**Problem**: You need to access and analyze the history of reference changes.

**Solution**: Use the reflog functionality to read and process reference history.

```rust
use gix_ref::{file::Store, FullName};
use std::path::Path;

/// Get the reflog for a specific reference
fn get_reflog(
    repo_path: &Path,
    ref_name: &str,
    limit: Option<usize>,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse reference name
    let full_name: FullName = ref_name.try_into()?;
    
    // Get reflog
    let log_iter = store.reflog_iter(&full_name)?;
    
    // Collect entries with optional limit
    let entries = log_iter
        .take(limit.unwrap_or(usize::MAX))
        .map(|entry_result| {
            entry_result.map(|entry| {
                format!(
                    "{} -> {} by {} at {}: {}",
                    entry.previous_oid,
                    entry.new_oid,
                    entry.committer.name,
                    entry.committer.time,
                    entry.message.to_string()
                )
            })
        })
        .collect::<Result<Vec<_>, _>>()?;
    
    Ok(entries)
}

/// Find the commit ID for a reference at a specific point in history
/// (e.g., HEAD@{2} for two operations ago)
fn get_reference_at_position(
    repo_path: &Path,
    ref_name: &str,
    position: usize,
) -> Result<String, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse reference name
    let full_name: FullName = ref_name.try_into()?;
    
    // Get reflog
    let log_iter = store.reflog_iter(&full_name)?;
    
    // Find the entry at the specified position
    let entry = log_iter
        .enumerate()
        .find(|(idx, _)| *idx == position)
        .map(|(_, entry_result)| entry_result)
        .ok_or_else(|| format!("No reflog entry at position {}", position))??;
    
    // Return the commit ID
    Ok(entry.new_oid.to_string())
}

/// Check if a reference was modified in the last n days
fn was_reference_modified_recently(
    repo_path: &Path,
    ref_name: &str,
    days: u64,
) -> Result<bool, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse reference name
    let full_name: FullName = ref_name.try_into()?;
    
    // Get reflog
    let mut log_iter = store.reflog_iter(&full_name)?;
    
    // Get current time
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    // Calculate cutoff time (n days ago)
    let cutoff = now - (days * 24 * 60 * 60);
    
    // Check if there's a recent entry
    if let Some(entry_result) = log_iter.next() {
        let entry = entry_result?;
        // Check if the timestamp is more recent than cutoff
        Ok(entry.committer.time.seconds() >= cutoff)
    } else {
        // No reflog entries
        Ok(false)
    }
}
```

## Namespace Management

**Problem**: You need to handle references within namespaces for isolated environments.

**Solution**: Use namespaces to isolate references in different contexts.

```rust
use gix_ref::{
    file::Store,
    transaction::{Change, LogChange, PreviousValue, RefEdit, RefLog},
    FullName, Namespace, Target,
};
use gix_hash::ObjectId;
use std::path::Path;

/// Create a reference in a specific namespace
fn create_namespaced_reference(
    repo_path: &Path,
    namespace: &str,
    ref_name: &str,
    target_id: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let mut store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Set namespace
    store.namespace = Some(Namespace::try_from(namespace)?);
    
    // Parse target ID
    let target = ObjectId::from_hex(target_id.as_bytes())?;
    
    // Parse reference name
    let full_name: FullName = ref_name.try_into()?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare reference creation
    transaction.prepare_edit(RefEdit {
        name: full_name,
        change: Change::Update {
            expected: PreviousValue::Any,
            log: LogChange {
                mode: RefLog::AndReference,
                force_create_reflog: false,
                message: format!("create: {}", ref_name).into(),
            },
            new: Target::Object(target),
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}

/// List references in a specific namespace
fn list_namespaced_references(
    repo_path: &Path,
    namespace: &str,
) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    // Open reference store
    let mut store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Set namespace
    let ns = Namespace::try_from(namespace)?;
    store.namespace = Some(ns.clone());
    
    // Collect references in namespace
    let refs = store
        .iter()?
        .map(|result| {
            result.map(|reference| {
                // Remove namespace from display
                let name = reference.name_without_namespace(&ns)
                    .map(|n| n.as_bstr().to_string())
                    .unwrap_or_else(|| reference.name.0.to_string());
                name
            })
        })
        .collect::<Result<Vec<_>, _>>()?;
    
    Ok(refs)
}

/// Copy references between namespaces
fn copy_between_namespaces(
    repo_path: &Path,
    from_namespace: &str,
    to_namespace: &str,
    ref_pattern: Option<&str>,
) -> Result<usize, Box<dyn std::error::Error>> {
    // Open reference store for source namespace
    let mut source_store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    source_store.namespace = Some(Namespace::try_from(from_namespace)?);
    
    // Open reference store for destination namespace
    let mut dest_store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    dest_store.namespace = Some(Namespace::try_from(to_namespace)?);
    
    // Collect references to copy
    let refs_to_copy = source_store
        .iter()?
        .filter_map(|result| {
            result.ok().and_then(|reference| {
                if let Some(pattern) = ref_pattern {
                    // Filter by pattern if provided
                    if reference.name.0.to_string().contains(pattern) {
                        Some(reference)
                    } else {
                        None
                    }
                } else {
                    Some(reference)
                }
            })
        })
        .collect::<Vec<_>>();
    
    // Create transaction for destination
    let mut transaction = dest_store.transaction();
    
    // Prepare all reference copies
    for reference in &refs_to_copy {
        transaction.prepare_edit(RefEdit {
            name: reference.name.clone(),
            change: Change::Update {
                expected: PreviousValue::Any,
                log: LogChange {
                    mode: RefLog::AndReference,
                    force_create_reflog: false,
                    message: format!("copy from namespace: {}", from_namespace).into(),
                },
                new: reference.target.clone(),
            },
            deref: false,
        })?;
    }
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(refs_to_copy.len())
}
```

## Working with Packed References

**Problem**: You need to optimize repository performance by managing packed references.

**Solution**: Use the packed references functionality for better performance.

```rust
use gix_ref::file::Store;
use std::path::Path;

/// Pack all loose references to improve performance
fn pack_references(
    repo_path: &Path,
    include_tags: bool,
) -> Result<usize, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Count loose references before packing
    let refs_before = store
        .iter()?
        .filter(|r| r.is_ok())
        .count();
    
    // Create transaction for packing
    let mut transaction = store.transaction();
    
    // Pack all references or only non-tags
    if include_tags {
        transaction.prepare_pack_all_loose_refs()?;
    } else {
        // Pack all but tags - useful to keep tags loose for better performance on tag operations
        transaction.prepare_pack_refs_excluding_tags()?;
    }
    
    // Commit the transaction
    transaction.commit()?;
    
    // Count loose references after packing
    let refs_after = store
        .iter()?
        .filter(|r| r.is_ok())
        .count();
    
    // Return the number of packed references
    Ok(refs_before - refs_after)
}

/// Optimize packed references by repacking
fn repack_references(
    repo_path: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare repack operation
    transaction.prepare_repack()?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}

/// Check if a reference is packed or loose
fn is_reference_packed(
    repo_path: &Path,
    ref_name: &str,
) -> Result<bool, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse reference name
    let full_name = ref_name.try_into()?;
    
    // Check in packed references first
    if let Ok(Some(_)) = store.packed_find_one(&full_name) {
        return Ok(true);
    }
    
    // Check if loose reference exists
    if let Ok(Some(_)) = store.loose_find_one(&full_name) {
        return Ok(false);
    }
    
    // Reference doesn't exist
    Err(format!("Reference '{}' not found", ref_name).into())
}
```

## Handling Reference Creation Atomically

**Problem**: You need to ensure that reference operations are atomic, especially when multiple references need to be updated together.

**Solution**: Use transactions to ensure atomicity across multiple reference changes.

```rust
use gix_hash::ObjectId;
use gix_ref::{
    file::Store,
    transaction::{Change, LogChange, PreviousValue, RefEdit, RefLog},
    FullName, Target,
};
use std::path::Path;

/// Atomically update multiple references
fn atomic_multi_ref_update(
    repo_path: &Path,
    updates: &[(&str, &str)],
    message: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare all reference updates
    for (ref_name, target_id) in updates {
        // Parse reference name
        let full_name: FullName = (*ref_name).try_into()?;
        
        // Parse target ID
        let target = ObjectId::from_hex(target_id.as_bytes())?;
        
        // Prepare reference update
        transaction.prepare_edit(RefEdit {
            name: full_name,
            change: Change::Update {
                expected: PreviousValue::Any, // Allow update even if ref doesn't exist
                log: LogChange {
                    mode: RefLog::AndReference,
                    force_create_reflog: false,
                    message: message.into(),
                },
                new: Target::Object(target),
            },
            deref: false,
        })?;
    }
    
    // Commit the transaction - either all updates succeed or none do
    transaction.commit()?;
    
    Ok(())
}

/// Create a new branch only if the target commit matches expectations
fn safe_branch_update(
    repo_path: &Path,
    branch_name: &str,
    expected_current_id: Option<&str>,
    new_target_id: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse branch name
    let branch_ref: FullName = format!("refs/heads/{}", branch_name).try_into()?;
    
    // Parse new target ID
    let new_target = ObjectId::from_hex(new_target_id.as_bytes())?;
    
    // Determine expected value
    let expected = if let Some(current_id) = expected_current_id {
        let current_target = ObjectId::from_hex(current_id.as_bytes())?;
        PreviousValue::MustExistAndMatch(Target::Object(current_target))
    } else {
        PreviousValue::Any
    };
    
    // Create transaction
    let mut transaction = store.transaction();
    
    // Prepare branch update with condition
    transaction.prepare_edit(RefEdit {
        name: branch_ref,
        change: Change::Update {
            expected,
            log: LogChange {
                mode: RefLog::AndReference,
                force_create_reflog: true,
                message: format!("update: {}", branch_name).into(),
            },
            new: Target::Object(new_target),
        },
        deref: false,
    })?;
    
    // Commit the transaction
    transaction.commit()?;
    
    Ok(())
}
```

## Resolving Symbolic References

**Problem**: You need to resolve symbolic references to get their ultimate target object IDs.

**Solution**: Use the reference peeling functionality to follow symbolic references to their targets.

```rust
use gix_ref::{file::Store, file::ReferenceExt, FullName};
use std::path::Path;

/// Resolve a reference to its ultimate object ID target
fn resolve_reference(
    repo_path: &Path,
    ref_name: &str,
) -> Result<String, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse reference name
    let full_name: FullName = ref_name.try_into()?;
    
    // Find the reference
    let mut reference = store.find_one(&full_name)?;
    
    // Peel the reference to its target object ID
    reference.peel_to_id_in_place(&store)?;
    
    // Get the peeled object ID
    if let Some(peeled) = reference.peeled {
        Ok(peeled.to_string())
    } else {
        // This should not happen after peeling
        Err("Failed to peel reference".into())
    }
}

/// List all symbolic references in the repository
fn list_symbolic_references(
    repo_path: &Path,
) -> Result<Vec<(String, String)>, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Collect all symbolic references with their targets
    let symbolic_refs = store
        .iter()?
        .filter_map(|result| {
            result.ok().and_then(|reference| {
                match &reference.target {
                    gix_ref::Target::Symbolic(target) => {
                        Some((reference.name.0.to_string(), target.0.to_string()))
                    },
                    _ => None,
                }
            })
        })
        .collect();
    
    Ok(symbolic_refs)
}

/// Check if a reference points to a specific commit, following symbolic refs
fn does_ref_point_to_commit(
    repo_path: &Path,
    ref_name: &str,
    commit_id: &str,
) -> Result<bool, Box<dyn std::error::Error>> {
    // Open reference store
    let store = Store::at(repo_path, gix_ref::store::init::Options::default())?;
    
    // Parse reference name and commit ID
    let full_name: FullName = ref_name.try_into()?;
    let target_id = gix_hash::ObjectId::from_hex(commit_id.as_bytes())?;
    
    // Find and peel the reference
    let mut reference = store.find_one(&full_name)?;
    let id = reference.peel_to_id_in_place(&store)?;
    
    // Compare with target
    Ok(*id == target_id)
}
```

These use cases demonstrate the versatility and power of the `gix-ref` crate for managing Git references. The examples cover common operations like branch and tag management, working with HEAD, reflogs, namespaces, and atomic transactions, showing how the crate provides a robust and type-safe API for Git reference manipulation.