# gix-blame Use Cases

This document outlines the primary use cases for the `gix-blame` crate, detailing the intended audience, common problems, and solutions provided by the crate.

## Intended Audience

- **Git Application Developers**: Developers building Git clients, IDE extensions, or code analysis tools that need to track file history at the line level
- **Code Analysis Tool Creators**: Developers building tools that need to analyze code attribution and history
- **Code Review Systems**: Platforms that want to show line-by-line authorship information
- **Git Library Implementers**: Developers extending or working with the gitoxide ecosystem

## Use Cases

### 1. Line-by-Line File History Attribution

**Problem**: 
Determining who wrote or last modified each line in a file and when these changes occurred.

**Solution**:
`gix-blame` analyzes a file's history through the commit graph to attribute each line to the commit and author that introduced it.

**Example Code**:
```rust
use gix_blame::{file, Options};
use gix_diff::blob::Algorithm;

// Open a repository
let repo = gix::open("/path/to/repo")?;

// Set up the blame options
let mut options = Options::default();
options.diff_algorithm = Algorithm::Patience; // Choose diff algorithm

// Run blame on a file
let file_path = "src/main.rs";
let resource_cache = &mut gix_diff::blob::Platform::default();
let outcome = file(
    repo.objects(), 
    repo.head_commit()?.id, 
    repo.cache.commit_graph(),
    resource_cache,
    file_path.as_bytes().into(),
    options
)?;

// Process and display results
for (entry, lines) in outcome.entries_with_lines() {
    // Get commit information
    let commit = repo.find_commit(entry.commit_id)?;
    let author = commit.author()?;
    
    println!("Lines {}-{} were introduced by {} <{}> in {}",
        entry.start_in_blamed_file + 1, // Convert to 1-based for display
        entry.start_in_blamed_file + entry.len.get(),
        String::from_utf8_lossy(author.name),
        String::from_utf8_lossy(author.email),
        commit.id()
    );
    
    // Print the actual lines
    for line in lines {
        println!("  {}", String::from_utf8_lossy(&line));
    }
}
```

### 2. Analyzing Code for Targeted Review or Refactoring

**Problem**:
Identifying which parts of a codebase were written by a specific author or during a specific time period to focus code review or refactoring efforts.

**Solution**:
`gix-blame` provides filtering options to focus blame analysis on specific timeframes, and the output can be filtered by commit author.

**Example Code**:
```rust
use gix_blame::{file, Options};
use gix_date::Time;
use std::time::{Duration, SystemTime};

// Open a repository
let repo = gix::open("/path/to/repo")?;

// Set up the blame options with time filtering
let mut options = Options::default();

// Only consider commits from the last 30 days
let thirty_days_ago = SystemTime::now() - Duration::from_secs(30 * 24 * 60 * 60);
let unix_time = thirty_days_ago.duration_since(SystemTime::UNIX_EPOCH)?.as_secs() as i64;
options.since = Some(Time { seconds: unix_time });

// Perform blame
let file_path = "src/main.rs";
let resource_cache = &mut gix_diff::blob::Platform::default();
let outcome = file(
    repo.objects(), 
    repo.head_commit()?.id, 
    repo.cache.commit_graph(),
    resource_cache,
    file_path.as_bytes().into(),
    options
)?;

// Find lines authored by a specific person
let target_author = "jane.doe@example.com";
for (entry, lines) in outcome.entries_with_lines() {
    let commit = repo.find_commit(entry.commit_id)?;
    let author = commit.author()?;
    let author_email = String::from_utf8_lossy(author.email);
    
    if author_email == target_author {
        println!("Lines by {}: {}-{}", 
            target_author,
            entry.start_in_blamed_file + 1,
            entry.start_in_blamed_file + entry.len.get()
        );
        
        // Print the code
        for line in lines {
            println!("  {}", String::from_utf8_lossy(&line));
        }
    }
}
```

### 3. Blaming Specific Line Ranges

**Problem**:
When analyzing large files, users often only need to understand the history of specific sections of code.

**Solution**:
`gix-blame` supports blaming specific line ranges instead of entire files, improving performance when analyzing large files.

**Example Code**:
```rust
use gix_blame::{file, Options, BlameRanges};
use gix_diff::blob::Algorithm;

// Open a repository
let repo = gix::open("/path/to/repo")?;

// Set up options to blame only lines 50-100
let mut options = Options::default();
options.diff_algorithm = Algorithm::Patience;
options.range = BlameRanges::from_range(50..=100); // 1-based inclusive range

// Perform blame
let file_path = "src/large_file.rs";
let resource_cache = &mut gix_diff::blob::Platform::default();
let outcome = file(
    repo.objects(), 
    repo.head_commit()?.id, 
    repo.cache.commit_graph(),
    resource_cache,
    file_path.as_bytes().into(),
    options
)?;

// Process results for the specific range
println!("Blame results for lines 50-100:");
for (entry, lines) in outcome.entries_with_lines() {
    let commit = repo.find_commit(entry.commit_id)?;
    println!("Lines {}-{} from commit {} ({}):",
        entry.start_in_blamed_file + 1,
        entry.start_in_blamed_file + entry.len.get(),
        commit.id().to_string(),
        commit.message_subject()?
    );
    
    for line in lines {
        println!("  {}", String::from_utf8_lossy(&line));
    }
}
```

### 4. Integration with Code Editors and IDEs

**Problem**:
Code editors and IDEs need to provide inline blame annotations to help developers understand code history while browsing source files.

**Solution**:
`gix-blame` provides fast, line-by-line attribution that can be used to annotate code in editors, with a focus on performance for real-time responses.

**Example Integration Pseudocode**:
```rust
// This is simplified pseudocode for an editor integration

// When a file is opened in the editor
fn provide_blame_annotations(file_path: &str, editor_view: &mut EditorView) -> Result<()> {
    // Get repository for the file
    let repo = gix::discover(file_path)?;
    
    // Set up blame options
    let mut options = Options::default();
    options.diff_algorithm = Algorithm::Histogram; // Often a good balance for editor integrations
    
    // Create blame
    let resource_cache = &mut gix_diff::blob::Platform::default();
    let outcome = file(
        repo.objects(), 
        repo.head_commit()?.id, 
        repo.cache.commit_graph(),
        resource_cache,
        file_path.as_bytes().into(),
        options
    )?;
    
    // Convert blame entries to editor annotations
    for (entry, _) in outcome.entries_with_lines() {
        let commit = repo.find_commit(entry.commit_id)?;
        let author = commit.author()?;
        let date = commit.author_time()?.format_rfc2822()?;
        
        // Create annotation for the editor
        let annotation = BlameAnnotation {
            start_line: entry.start_in_blamed_file as usize + 1,
            end_line: (entry.start_in_blamed_file + entry.len.get()) as usize,
            author: String::from_utf8_lossy(author.name).to_string(),
            commit_id: commit.id().to_string(),
            date: date,
        };
        
        // Add to editor's UI
        editor_view.add_blame_annotation(annotation);
    }
    
    Ok(())
}
```

### 5. Git Archaeology and Code Auditing

**Problem**:
Finding when specific code patterns or bugs were introduced to understand their origin and context.

**Solution**:
`gix-blame` helps developers trace the evolution of specific code patterns or bugs through the repository's history.

**Example Code**:
```rust
use gix_blame::{file, Options};
use regex::Regex;

// Open a repository
let repo = gix::open("/path/to/repo")?;

// Set up blame options
let options = Options::default();

// Run blame on the file
let file_path = "src/security.rs";
let resource_cache = &mut gix_diff::blob::Platform::default();
let outcome = file(
    repo.objects(), 
    repo.head_commit()?.id, 
    repo.cache.commit_graph(),
    resource_cache,
    file_path.as_bytes().into(),
    options
)?;

// Look for potentially insecure code patterns
let potential_vulnerability = Regex::new(r"exec\s*\(\s*.*\$.*\s*\)")?; // Example: looking for shell injection

for (entry, lines) in outcome.entries_with_lines() {
    for (i, line) in lines.iter().enumerate() {
        let line_str = String::from_utf8_lossy(line);
        
        if potential_vulnerability.is_match(&line_str) {
            let commit = repo.find_commit(entry.commit_id)?;
            let line_num = entry.start_in_blamed_file as usize + i + 1;
            
            println!("Potential vulnerability found at line {}:", line_num);
            println!("  {}", line_str);
            println!("Introduced in commit {} by {}",
                commit.id(),
                String::from_utf8_lossy(commit.author()?.name)
            );
            println!("Commit message: {}", commit.message_subject()?);
            println!("Date: {}", commit.author_time()?.format_rfc2822()?);
        }
    }
}
```

## Future Use Cases

As the crate continues to develop, these additional use cases will become more powerful:

### 1. Code Ownership Analysis

Once the performance improvements (noted in crate-status.md) are implemented, `gix-blame` will efficiently identify code ownership patterns across large repositories, helping with:

- Identifying knowledge silos in the codebase
- Assigning reviewers based on historical contribution patterns
- Tracking maintenance responsibilities

### 2. Historical Refactoring Tracking

With the implementation of rename tracking, `gix-blame` will be able to:

- Track file renames through history
- Maintain attribution accuracy even when files are moved
- Provide continuous history for refactored code

### 3. Live Blame with Working Directory Changes

Once worktree changes support is added, `gix-blame` will enable:

- "Preview" blame that includes uncommitted changes
- Real-time blame feedback during editing
- Attribution analysis for work-in-progress code