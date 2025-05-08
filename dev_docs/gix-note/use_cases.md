# gix-note Use Cases

This document outlines potential use cases for the `gix-note` crate once it is implemented. Git notes provide a way to add metadata to Git objects without changing their identities, which enables various workflows and integrations.

## Intended Audience

- Rust developers building Git-based tools and integrations
- Contributors to gitoxide who need to implement or use Git notes functionality
- Developers building code review, CI/CD, or project management tools that integrate with Git
- Users who want to attach additional metadata to Git objects

## Use Cases

Since the `gix-note` crate is currently a placeholder with no implementation, the following use cases represent potential applications once the crate is fully implemented:

### 1. Adding CI/CD Status Information to Commits

**Problem**: You want to attach CI/CD build status information to commits without modifying the commits themselves.

**Solution**: Use Git notes to store build status metadata that can be queried later.

```rust
// Example of what the API might look like when implemented
use gix_hash::ObjectId;
use gix_note::{Notes, AddOptions};
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
struct BuildStatus {
    status: Status,
    build_url: String,
    timestamp: u64,
    metrics: BuildMetrics,
}

#[derive(Serialize, Deserialize)]
enum Status {
    Passed,
    Failed,
    Pending,
}

#[derive(Serialize, Deserialize)]
struct BuildMetrics {
    duration_seconds: u32,
    test_count: u32,
    test_failures: u32,
    coverage_percent: f32,
}

fn attach_build_status(
    repo_path: &str,
    commit_id: &str,
    status: BuildStatus
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for CI namespace
    let mut notes = Notes::new(repo, Some("refs/notes/ci"))?;
    
    // Serialize build status to JSON
    let status_json = serde_json::to_string(&status)?;
    
    // Add note to the commit
    let commit_id = ObjectId::from_hex(commit_id)?;
    notes.add(
        &commit_id,
        status_json.as_bytes(),
        AddOptions {
            force: true, // Overwrite existing note
            ..Default::default()
        }
    )?;
    
    println!("Build status attached to commit {}", commit_id);
    Ok(())
}

fn query_build_status(
    repo_path: &str,
    commit_id: &str
) -> Result<Option<BuildStatus>, Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for CI namespace
    let notes = Notes::new(repo, Some("refs/notes/ci"))?;
    
    // Get note for the commit
    let commit_id = ObjectId::from_hex(commit_id)?;
    let note = notes.show(&commit_id, Default::default())?;
    
    // Parse build status from note content
    if let Some(content) = note {
        let status: BuildStatus = serde_json::from_slice(&content)?;
        Ok(Some(status))
    } else {
        Ok(None)
    }
}
```

### 2. Implementing a Code Review System

**Problem**: You want to implement a code review system that attaches review comments to commits without modifying them.

**Solution**: Use Git notes to store review comments in a structured format.

```rust
// Example of what the API might look like when implemented
use gix_hash::ObjectId;
use gix_note::{Notes, AddOptions, ListOptions};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize)]
struct ReviewData {
    reviewer: String,
    status: ReviewStatus,
    comments: Vec<Comment>,
    timestamp: u64,
}

#[derive(Serialize, Deserialize)]
enum ReviewStatus {
    Approved,
    RequestChanges,
    Commented,
}

#[derive(Serialize, Deserialize)]
struct Comment {
    file_path: String,
    line_number: Option<u32>,
    content: String,
    is_resolved: bool,
}

fn add_review(
    repo_path: &str,
    commit_id: &str,
    review: ReviewData
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for review namespace
    let mut notes = Notes::new(repo, Some("refs/notes/reviews"))?;
    
    // Serialize review data to JSON
    let review_json = serde_json::to_string(&review)?;
    
    // Add note to the commit
    let commit_id = ObjectId::from_hex(commit_id)?;
    notes.add(
        &commit_id,
        review_json.as_bytes(),
        AddOptions {
            force: false, // Don't overwrite, append instead
            append: true, // Append to existing note
            ..Default::default()
        }
    )?;
    
    println!("Review added to commit {}", commit_id);
    Ok(())
}

fn list_commits_with_reviews(
    repo_path: &str
) -> Result<Vec<ObjectId>, Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for review namespace
    let notes = Notes::new(repo, Some("refs/notes/reviews"))?;
    
    // List all commits that have reviews
    let commits = notes.list(ListOptions::default())?;
    
    Ok(commits)
}

fn get_reviews_for_commit(
    repo_path: &str,
    commit_id: &str
) -> Result<Vec<ReviewData>, Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for review namespace
    let notes = Notes::new(repo, Some("refs/notes/reviews"))?;
    
    // Get note for the commit
    let commit_id = ObjectId::from_hex(commit_id)?;
    let note = notes.show(&commit_id, Default::default())?;
    
    // Parse reviews from note content
    if let Some(content) = note {
        // Note may contain multiple reviews separated by newlines
        let content_str = String::from_utf8_lossy(&content);
        let mut reviews = Vec::new();
        
        for review_json in content_str.split('\n').filter(|s| !s.trim().is_empty()) {
            let review: ReviewData = serde_json::from_str(review_json)?;
            reviews.push(review);
        }
        
        Ok(reviews)
    } else {
        Ok(Vec::new())
    }
}
```

### 3. Tracking Documentation Status

**Problem**: You want to track which parts of your code are well-documented without modifying the code itself.

**Solution**: Use Git notes to store documentation status metadata for various files and commits.

```rust
// Example of what the API might look like when implemented
use gix_hash::ObjectId;
use gix_note::{Notes, AddOptions};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize)]
struct DocStatus {
    files: HashMap<String, FileDocStatus>,
    overall_score: f32,
    last_reviewed: u64,
    reviewer: String,
}

#[derive(Serialize, Deserialize)]
struct FileDocStatus {
    coverage_percent: f32,
    missing_docs: Vec<String>,
    examples_count: u32,
    quality_score: f32,
}

fn update_doc_status(
    repo_path: &str,
    commit_id: &str,
    doc_status: DocStatus
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for documentation namespace
    let mut notes = Notes::new(repo, Some("refs/notes/documentation"))?;
    
    // Serialize documentation status to JSON
    let status_json = serde_json::to_string(&doc_status)?;
    
    // Add note to the commit
    let commit_id = ObjectId::from_hex(commit_id)?;
    notes.add(
        &commit_id,
        status_json.as_bytes(),
        AddOptions {
            force: true, // Overwrite existing note
            ..Default::default()
        }
    )?;
    
    println!("Documentation status updated for commit {}", commit_id);
    Ok(())
}

fn get_doc_status_history(
    repo_path: &str,
    file_path: &str
) -> Result<HashMap<String, FileDocStatus>, Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for documentation namespace
    let notes = Notes::new(repo, Some("refs/notes/documentation"))?;
    
    // List all commits that have documentation notes
    let commits = notes.list(Default::default())?;
    
    // Collect documentation status for the specified file across all commits
    let mut history = HashMap::new();
    
    for commit_id in commits {
        let note = notes.show(&commit_id, Default::default())?;
        
        if let Some(content) = note {
            let doc_status: DocStatus = serde_json::from_slice(&content)?;
            
            if let Some(file_status) = doc_status.files.get(file_path) {
                history.insert(commit_id.to_string(), file_status.clone());
            }
        }
    }
    
    Ok(history)
}
```

### 4. Implementing Collaborative TODOs

**Problem**: You want to maintain a list of TODOs for your project that are associated with specific commits but don't clutter the commit messages.

**Solution**: Use Git notes to store TODO items linked to relevant commits.

```rust
// Example of what the API might look like when implemented
use gix_hash::ObjectId;
use gix_note::{Notes, AddOptions, EditOptions};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize)]
struct TodoList {
    items: Vec<TodoItem>,
    last_updated: u64,
}

#[derive(Serialize, Deserialize)]
struct TodoItem {
    id: String,
    description: String,
    assigned_to: Option<String>,
    status: TodoStatus,
    created_at: u64,
    updated_at: u64,
}

#[derive(Serialize, Deserialize)]
enum TodoStatus {
    Pending,
    InProgress,
    Completed,
    Cancelled,
}

fn add_todo(
    repo_path: &str,
    commit_id: &str,
    todo_item: TodoItem
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for todos namespace
    let mut notes = Notes::new(repo, Some("refs/notes/todos"))?;
    
    // Get existing todos or create new list
    let commit_id = ObjectId::from_hex(commit_id)?;
    let mut todo_list = if let Some(content) = notes.show(&commit_id, Default::default())? {
        serde_json::from_slice(&content)?
    } else {
        TodoList {
            items: Vec::new(),
            last_updated: chrono::Utc::now().timestamp() as u64,
        }
    };
    
    // Add new todo item
    todo_list.items.push(todo_item);
    todo_list.last_updated = chrono::Utc::now().timestamp() as u64;
    
    // Save updated todo list
    let todo_json = serde_json::to_string(&todo_list)?;
    
    notes.add(
        &commit_id,
        todo_json.as_bytes(),
        AddOptions {
            force: true, // Overwrite existing note
            ..Default::default()
        }
    )?;
    
    println!("TODO item added to commit {}", commit_id);
    Ok(())
}

fn update_todo_status(
    repo_path: &str,
    commit_id: &str,
    todo_id: &str,
    new_status: TodoStatus
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for todos namespace
    let mut notes = Notes::new(repo, Some("refs/notes/todos"))?;
    
    // Get existing todos
    let commit_id = ObjectId::from_hex(commit_id)?;
    let note = notes.show(&commit_id, Default::default())?;
    
    if let Some(content) = note {
        let mut todo_list: TodoList = serde_json::from_slice(&content)?;
        
        // Find and update the specified TODO item
        for item in &mut todo_list.items {
            if item.id == todo_id {
                item.status = new_status;
                item.updated_at = chrono::Utc::now().timestamp() as u64;
                todo_list.last_updated = item.updated_at;
                break;
            }
        }
        
        // Save updated todo list
        let todo_json = serde_json::to_string(&todo_list)?;
        
        notes.add(
            &commit_id,
            todo_json.as_bytes(),
            AddOptions {
                force: true, // Overwrite existing note
                ..Default::default()
            }
        )?;
        
        println!("TODO status updated for item {} in commit {}", todo_id, commit_id);
        Ok(())
    } else {
        Err(format!("No TODOs found for commit {}", commit_id).into())
    }
}
```

### 5. Implementing Distributed Annotations

**Problem**: You want to implement a system for distributed annotations that can be shared across team members without modifying the repository.

**Solution**: Use Git notes with custom merge strategies to combine annotations from different team members.

```rust
// Example of what the API might look like when implemented
use gix_hash::ObjectId;
use gix_note::{Notes, MergeOptions, MergeStrategy};
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
struct AnnotationSet {
    annotations: Vec<Annotation>,
    author: String,
    version: u32,
}

#[derive(Serialize, Deserialize)]
struct Annotation {
    id: String,
    file_path: String,
    line_range: Option<(u32, u32)>,
    content: String,
    tags: Vec<String>,
    created_at: u64,
}

fn add_annotation(
    repo_path: &str,
    commit_id: &str,
    annotation: Annotation,
    author: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for annotations namespace
    let mut notes = Notes::new(repo, Some("refs/notes/annotations"))?;
    
    // Get existing annotations or create new set
    let commit_id = ObjectId::from_hex(commit_id)?;
    let mut annotation_set = if let Some(content) = notes.show(&commit_id, Default::default())? {
        serde_json::from_slice(&content)?
    } else {
        AnnotationSet {
            annotations: Vec::new(),
            author: author.to_string(),
            version: 1,
        }
    };
    
    // Add new annotation
    annotation_set.annotations.push(annotation);
    annotation_set.version += 1;
    
    // Save updated annotation set
    let anno_json = serde_json::to_string(&annotation_set)?;
    
    notes.add(
        &commit_id,
        anno_json.as_bytes(),
        AddOptions {
            force: true, // Overwrite existing note
            ..Default::default()
        }
    )?;
    
    println!("Annotation added to commit {}", commit_id);
    Ok(())
}

fn merge_team_annotations(
    repo_path: &str,
    remote_name: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository
    let repo = gix::open(repo_path)?;
    
    // Initialize notes manager for annotations namespace
    let mut notes = Notes::new(repo, Some("refs/notes/annotations"))?;
    
    // Define custom merge strategy for annotations
    let merge_options = MergeOptions {
        strategy: MergeStrategy::Custom("annotation-merger"),
        command: Some(format!("annotation-merger-tool %O %A %B %L")),
        verify_signatures: false,
    };
    
    // Fetch remote notes
    println!("Fetching remote notes from {}", remote_name);
    // (This would be a call to git fetch using gix-transport)
    
    // Merge remote notes into local notes
    let remote_ref = format!("refs/notes/annotations/{}", remote_name);
    notes.merge(&remote_ref, merge_options)?;
    
    println!("Team annotations merged successfully");
    Ok(())
}
```

## Best Practices

Once the `gix-note` crate is implemented, consider the following best practices for working with Git notes:

### 1. Use Separate Namespaces

Keep different types of notes in separate namespaces to avoid conflicts and make management easier:

```rust
// Example of working with multiple note namespaces
let ci_notes = Notes::new(repo.clone(), Some("refs/notes/ci"))?;
let review_notes = Notes::new(repo.clone(), Some("refs/notes/reviews"))?;
let doc_notes = Notes::new(repo.clone(), Some("refs/notes/documentation"))?;
```

### 2. Define Structured Data Formats

Use structured data formats like JSON for note content to make it easier to process programmatically:

```rust
// Example of structured note content
fn add_structured_note<T: Serialize>(
    notes: &mut Notes,
    object_id: &ObjectId,
    data: &T
) -> Result<(), Box<dyn std::error::Error>> {
    let json = serde_json::to_string(data)?;
    notes.add(
        object_id,
        json.as_bytes(),
        AddOptions::default()
    )?;
    Ok(())
}
```

### 3. Configure Appropriate Merge Strategies

Choose appropriate merge strategies based on the kind of notes you're working with:

```rust
// Example of configuring merge strategies
fn configure_notes_merge(repo_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Run git commands to configure merge strategies
    let repo = gix::open(repo_path)?;
    
    // For CI notes, use "ours" strategy (latest CI result wins)
    repo.config()?.set("notes.mergeStrategy.ci", "ours")?;
    
    // For review notes, use "union" strategy (combine all reviews)
    repo.config()?.set("notes.mergeStrategy.reviews", "union")?;
    
    // For documentation notes, use custom merger
    repo.config()?.set("notes.mergeStrategy.documentation", "cat_sort_uniq")?;
    
    Ok(())
}
```

### 4. Handle Notes During Synchronization

Remember to handle notes during push and fetch operations:

```rust
// Example of pushing notes to remote
fn push_notes_to_remote(
    repo_path: &str,
    remote_name: &str,
    notes_ref: &str
) -> Result<(), Box<dyn std::error::Error>> {
    // This would use gix-transport functions once implemented
    println!("Pushing notes from {} to {}", notes_ref, remote_name);
    // Equivalent to: git push origin refs/notes/reviews
    Ok(())
}
```

### 5. Consider Performance with Large Repositories

Be mindful of performance when working with notes in large repositories:

```rust
// Example of efficient note operations
fn batch_process_notes(
    repo_path: &str,
    note_refs: &[&str]
) -> Result<(), Box<dyn std::error::Error>> {
    // Open repository once
    let repo = gix::open(repo_path)?;
    
    // Process each notes ref
    for &note_ref in note_refs {
        let notes = Notes::new(repo.clone(), Some(note_ref))?;
        
        // Use an efficient algorithm to process notes
        let commits = notes.list(ListOptions {
            limit: Some(100),  // Process in batches
            ..Default::default()
        })?;
        
        // Process batch
        println!("Processing {} notes in {}", commits.len(), note_ref);
    }
    
    Ok(())
}
```

## Conclusion

Once implemented, the `gix-note` crate will enable powerful workflows for attaching metadata to Git objects without modifying them. This will support a wide range of use cases from CI/CD integration to code review systems, documentation tracking, and collaborative annotations.

The examples in this document illustrate potential APIs and usage patterns, but the actual implementation may differ. The core functionality will revolve around creating, reading, updating, and merging notes across different namespaces, with support for structured data formats and custom merge strategies.