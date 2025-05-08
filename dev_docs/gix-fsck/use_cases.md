# gix-fsck Use Cases

This document describes the main use cases for the gix-fsck crate, who its intended audience is, what problems it solves, and how it solves them.

## Intended Audience

The primary audience for the gix-fsck crate includes:

1. **Git Repository Administrators**: People who need to validate the integrity of Git repositories to ensure they can be safely used
2. **Git Tool Developers**: Developers building Git-compatible tools that need to verify repository health
3. **Backup and Recovery Tool Developers**: Developers creating tools for backing up and restoring Git repositories
4. **Repository Migration Tool Developers**: Developers working on tools to move repositories between systems or storage formats
5. **Gitoxide Component Developers**: Internal users developing other components in the gitoxide ecosystem

## Core Use Cases

### 1. Validating Repository Integrity After Transfer

#### Problem

When a Git repository is transferred between systems (cloned, pushed, pulled, or physically moved), there's a risk that some objects might not be transferred completely. Partial transfers can leave a repository in an inconsistent state where operations that depend on the missing objects will fail.

#### Solution

The gix-fsck crate provides functionality to verify that all objects referenced from a given commit are present in the repository, making it ideal for post-transfer validation.

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;
use std::collections::HashMap;

fn validate_after_clone(
    repo_path: &str,
    reference: &str
) -> Result<bool, Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Resolve the reference (e.g., "HEAD", "refs/heads/main") to a commit ID
    let commit_id = repo.rev_parse_single(reference)?.object()?.id();
    
    // Track missing objects
    let mut missing_objects = HashMap::new();
    let on_missing = |oid: &ObjectId, kind: Kind| {
        missing_objects.insert(*oid, kind);
    };
    
    // Run connectivity check
    let mut checker = Connectivity::new(&repo.objects, on_missing);
    checker.check_commit(&commit_id)?;
    
    // If there are no missing objects, the repository is valid
    Ok(missing_objects.is_empty())
}
```

### 2. Detecting Object Corruption in a Repository

#### Problem

Git repositories can become corrupted due to disk errors, filesystem issues, or other problems. Objects might be present but their content might be corrupted, making them invalid.

#### Solution

While gix-fsck primarily checks for missing objects, it will also detect some forms of corruption by attempting to parse objects when traversing the repository structure.

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;
use std::io::{self, Write};

fn check_repository_health(
    repo_path: &str,
    out: &mut impl Write
) -> Result<bool, Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get all local branch heads to check
    let refs = repo.references()?;
    let heads = refs.local_branches()?.map(|r| r.map(|r| r.id())).collect::<Result<Vec<_>, _>>()?;
    
    writeln!(out, "Checking {} branch heads for connectivity", heads.len())?;
    
    // Track issues
    let mut has_issues = false;
    let on_missing = |oid: &ObjectId, kind: Kind| {
        has_issues = true;
        writeln!(out, "Missing {} object: {}", kind, oid).unwrap();
    };
    
    // Create checker
    let mut checker = Connectivity::new(&repo.objects, on_missing);
    
    // Check each branch head
    for head_id in heads {
        match checker.check_commit(&head_id) {
            Ok(()) => {}
            Err(e) => {
                has_issues = true;
                writeln!(out, "Error checking commit {}: {}", head_id, e)?;
            }
        }
    }
    
    Ok(!has_issues)
}
```

### 3. Identifying Missing Objects in Partial or Shallow Clones

#### Problem

Git supports partial clones (`--filter`) and shallow clones (`--depth`) that intentionally omit certain objects. When working with these repositories, it's important to identify which objects are missing to understand potential limitations.

#### Solution

The gix-fsck crate can catalog missing objects in partial or shallow repositories, helping users understand what's not available locally.

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;
use std::collections::HashMap;

fn analyze_partial_clone(
    repo_path: &str
) -> Result<HashMap<Kind, Vec<ObjectId>>, Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get HEAD commit
    let head_id = repo.head_id()?;
    
    // Track missing objects by kind
    let mut missing_by_kind: HashMap<Kind, Vec<ObjectId>> = HashMap::new();
    let on_missing = |oid: &ObjectId, kind: Kind| {
        missing_by_kind.entry(kind).or_default().push(*oid);
    };
    
    // Check connectivity
    let mut checker = Connectivity::new(&repo.objects, on_missing);
    checker.check_commit(&head_id)?;
    
    // Return analysis results
    Ok(missing_by_kind)
}
```

### 4. Pre-push Validation to Prevent Incomplete Pushes

#### Problem

When pushing changes to a remote repository, it's important to ensure that all necessary objects are included to avoid creating an incomplete or broken state on the remote.

#### Solution

By checking the connectivity of commits before pushing, developers can ensure they're sending a complete set of objects.

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;

fn validate_before_push(
    repo_path: &str,
    remote_name: &str,
    branch_name: &str
) -> Result<bool, Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get the local branch commit
    let branch_ref = format!("refs/heads/{}", branch_name);
    let commit_id = repo.find_reference(&branch_ref)?.target().id();
    
    // Check if any objects are missing
    let mut missing_count = 0;
    let on_missing = |_: &ObjectId, _: Kind| { missing_count += 1; };
    
    // Run connectivity check
    let mut checker = Connectivity::new(&repo.objects, on_missing);
    checker.check_commit(&commit_id)?;
    
    if missing_count > 0 {
        println!("Warning: Found {} missing objects - push would be incomplete", missing_count);
        return Ok(false);
    }
    
    Ok(true)
}
```

### 5. Diagnostic Tool for Repository Recovery

#### Problem

When a repository is damaged or inconsistent, users need to understand the extent of the damage to plan recovery actions.

#### Solution

The gix-fsck crate can be used to build diagnostic tools that map the full extent of missing or corrupted objects.

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;
use std::collections::{HashMap, HashSet};
use std::io::Write;

fn diagnose_repository(
    repo_path: &str,
    output: &mut impl Write
) -> Result<(), Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get all refs
    let refs = repo.references()?.all()?
        .collect::<Result<Vec<_>, _>>()?;
    
    writeln!(output, "Analyzing repository with {} references", refs.len())?;
    
    // Track missing objects and which refs they're referenced from
    let mut missing_objects: HashMap<ObjectId, (Kind, HashSet<String>)> = HashMap::new();
    
    // Check each ref
    for reference in refs {
        let ref_name = reference.name().to_string();
        let target = reference.target();
        
        // Only check direct references to objects (not symbolic refs)
        if let gix_ref::Target::Peeled(id) = target {
            writeln!(output, "Checking '{}'...", ref_name)?;
            
            // Define callback for this specific reference
            let on_missing = |oid: &ObjectId, kind: Kind| {
                missing_objects
                    .entry(*oid)
                    .or_insert_with(|| (kind, HashSet::new()))
                    .1
                    .insert(ref_name.clone());
            };
            
            // Create a new checker for each ref to isolate errors
            let mut checker = Connectivity::new(&repo.objects, on_missing);
            
            // Only check if it's a commit
            if let Ok(obj) = repo.find_object(&id) {
                if obj.kind() == Kind::Commit {
                    if let Err(e) = checker.check_commit(&id) {
                        writeln!(output, "  Error checking '{}': {}", ref_name, e)?;
                    }
                }
            }
        }
    }
    
    // Report findings
    if missing_objects.is_empty() {
        writeln!(output, "No missing objects found - repository appears intact")?;
    } else {
        writeln!(output, "Found {} missing objects:", missing_objects.len())?;
        
        // Group by kind for better reporting
        let mut by_kind: HashMap<Kind, Vec<(ObjectId, HashSet<String>)>> = HashMap::new();
        for (oid, (kind, refs)) in missing_objects {
            by_kind.entry(kind).or_default().push((oid, refs));
        }
        
        for (kind, objects) in by_kind {
            writeln!(output, "  {} missing {} objects:", objects.len(), kind)?;
            for (oid, refs) in objects {
                let ref_list = refs.into_iter().collect::<Vec<_>>().join(", ");
                writeln!(output, "    {} - referenced from: {}", oid, ref_list)?;
            }
        }
    }
    
    Ok(())
}
```

### 6. Repository Verification in CI/CD Pipelines

#### Problem

In automated CI/CD environments, Git repositories are often cloned and manipulated programmatically. Ensuring that these operations resulted in valid repositories is crucial for the success of subsequent steps in the pipeline.

#### Solution

Integrating gix-fsck checks into CI/CD pipelines can catch issues early and prevent build failures due to repository problems.

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;
use std::process;

fn verify_repository_in_ci(
    repo_path: &str,
    abort_on_error: bool
) -> Result<(), Box<dyn std::error::Error>> {
    println!("CI step: Verifying repository integrity");
    
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get commit to verify (typically the one being built)
    let commit_id = repo.head_id()?;
    println!("Checking commit: {}", commit_id);
    
    // Flag for any issues found
    let mut issues_found = false;
    
    // Track missing objects
    let on_missing = |oid: &ObjectId, kind: Kind| {
        issues_found = true;
        eprintln!("ERROR: Missing {} object: {}", kind, oid);
    };
    
    // Run connectivity check
    let mut checker = Connectivity::new(&repo.objects, on_missing);
    match checker.check_commit(&commit_id) {
        Ok(()) => {
            if !issues_found {
                println!("Repository verification successful");
            } else if abort_on_error {
                eprintln!("Repository verification failed - missing objects detected");
                process::exit(1);
            }
        }
        Err(e) => {
            if abort_on_error {
                eprintln!("Repository verification failed: {}", e);
                process::exit(1);
            } else {
                eprintln!("Warning: Repository verification issue: {}", e);
            }
        }
    }
    
    Ok(())
}
```

### 7. Finding Unreferenced or Dangling Objects

#### Problem

Over time, Git repositories can accumulate unreferenced objects that take up space but aren't accessible through any branch or tag. Identifying these objects can help with repository maintenance.

#### Solution

While gix-fsck primarily checks for missing objects, it can be used indirectly to identify unreferenced objects by comparing the set of all objects in the repository with the set of reachable objects.

```rust
use gix_fsck::Connectivity;
use gix_hash::ObjectId;
use gix_object::Kind;
use std::collections::HashSet;

fn find_unreferenced_objects(
    repo_path: &str
) -> Result<HashSet<ObjectId>, Box<dyn std::error::Error>> {
    // Open the repository
    let repo = gix::open(repo_path)?;
    
    // Get all objects in the repository
    let mut all_objects = HashSet::new();
    let odb = &repo.objects;
    odb.traverse_objects(move |id, _| {
        all_objects.insert(id);
        Ok(())
    })?;
    
    // Build set of reachable objects
    let mut reachable_objects = HashSet::new();
    
    // Track seen objects during traversal
    let on_object = |oid: &ObjectId, _: Kind| {
        reachable_objects.insert(*oid);
    };
    
    // Create connectivity checker that records all seen objects
    let mut checker = Connectivity::new(odb, on_object);
    
    // Check all refs
    let refs = repo.references()?.all()?.collect::<Result<Vec<_>, _>>()?;
    for reference in refs {
        if let gix_ref::Target::Peeled(id) = reference.target() {
            // Only process commit objects
            if let Ok(obj) = repo.find_object(&id) {
                if obj.kind() == Kind::Commit {
                    let _ = checker.check_commit(&id); // Ignore errors, we just want to build the set
                }
            }
        }
    }
    
    // Find the difference: all objects minus reachable objects
    let unreferenced = all_objects.difference(&reachable_objects).cloned().collect();
    
    Ok(unreferenced)
}
```

## Integration with Other Components

The gix-fsck crate integrates with several other components in the gitoxide ecosystem:

### Integration with Repository Operations

```rust
// Integration with repository operations like fetch or clone
fn verify_after_operation(
    repo: &gix::Repository,
    reference: &str,
    operation_name: &str
) -> Result<(), Box<dyn std::error::Error>> {
    println!("Verifying repository after {}", operation_name);
    
    // Get the reference to check
    let target = repo.rev_parse_single(reference)?.object()?.id();
    
    // Set up error reporting
    let mut issues_found = false;
    let on_missing = |oid: &ObjectId, kind: Kind| {
        issues_found = true;
        eprintln!("Missing {} object: {}", kind, oid);
    };
    
    // Run check
    let mut checker = gix_fsck::Connectivity::new(&repo.objects, on_missing);
    checker.check_commit(&target)?;
    
    if issues_found {
        eprintln!("Warning: {} operation may have been incomplete", operation_name);
    } else {
        println!("{} operation completed successfully", operation_name);
    }
    
    Ok(())
}
```

### Integration with CLI Tools

The gix-fsck crate is integrated with the gitoxide-core crate to provide the `gix fsck` command-line functionality:

```rust
// From gitoxide-core/src/repository/fsck.rs
pub fn function(mut repo: gix::Repository, spec: Option<String>, mut out: impl std::io::Write) -> anyhow::Result<()> {
    let spec = spec.unwrap_or("HEAD".into());

    repo.object_cache_size_if_unset(4 * 1024 * 1024);
    // We expect to be finding a bunch of non-existent objects here - never refresh the ODB
    repo.objects.refresh_never();

    let id = repo
        .rev_parse_single(spec.as_str())
        .context("Only single revisions are supported")?;
    let commits: gix::revision::Walk<'_> = id
        .object()?
        .peel_to_kind(gix::object::Kind::Commit)
        .context("Need committish as starting point")?
        .id()
        .ancestors()
        .all()?;

    let on_missing = |oid: &ObjectId, kind: Kind| {
        writeln!(out, "{oid}: {kind}").expect("failed to write output");
    };

    let mut check = gix_fsck::Connectivity::new(&repo.objects, on_missing);
    // Walk all commits, checking each one for connectivity
    for commit in commits {
        let commit = commit?;
        check.check_commit(&commit.id)?;
        // Note that we leave parent-iteration to the commits iterator, as it will
        // correctly handle shallow repositories which are expected to have the commits
        // along the shallow boundary missing.
    }
    Ok(())
}
```

### Integration with Backup and Recovery Systems

```rust
// Integration with backup validation
fn validate_backed_up_repository(
    backup_path: &str,
    important_refs: &[&str]
) -> Result<bool, Box<dyn std::error::Error>> {
    // Open the backed up repository
    let repo = gix::open(backup_path)?;
    
    // Check each important reference
    let mut valid = true;
    for ref_name in important_refs {
        println!("Validating backup of reference: {}", ref_name);
        
        // Resolve the reference to a commit
        let commit_id = match repo.rev_parse_single(ref_name) {
            Ok(rev) => match rev.object() {
                Ok(obj) => obj.id(),
                Err(e) => {
                    println!("Error resolving object for '{}': {}", ref_name, e);
                    valid = false;
                    continue;
                }
            },
            Err(e) => {
                println!("Error resolving reference '{}': {}", ref_name, e);
                valid = false;
                continue;
            }
        };
        
        // Check connectivity
        let mut issues_found = false;
        let on_missing = |_: &ObjectId, _: Kind| {
            issues_found = true;
        };
        
        let mut checker = gix_fsck::Connectivity::new(&repo.objects, on_missing);
        if let Err(e) = checker.check_commit(&commit_id) {
            println!("Error checking commit for '{}': {}", ref_name, e);
            valid = false;
            continue;
        }
        
        if issues_found {
            println!("Backup of '{}' is incomplete - missing objects detected", ref_name);
            valid = false;
        } else {
            println!("Backup of '{}' is valid", ref_name);
        }
    }
    
    Ok(valid)
}
```

## Conclusion

The gix-fsck crate provides an essential component for validating Git repository integrity. By focusing specifically on object connectivity checks, it offers a foundational building block for more complex repository validation, maintenance, and recovery operations.

The use cases presented here demonstrate the versatility of this relatively simple crate - from basic integrity checks to complex diagnostic tools. When integrated with other gitoxide components, it enables comprehensive repository health monitoring and maintenance capabilities.