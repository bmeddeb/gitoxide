# gix-mailmap Use Cases

This document describes typical use cases for the `gix-mailmap` crate, which provides functionality for parsing and working with Git mailmap files.

## Intended Audience

- Developers building Git tools or integrations
- Repository analysis tools that need to normalize author/committer information
- Project maintainers who need to consolidate contributor identities
- Git client implementations that need to support mailmap functionality

## Use Case 1: Parsing a Mailmap File

### Problem

You need to parse a Git mailmap file to understand the mappings it defines.

### Solution

Use the `parse()` or `parse_ignore_errors()` functions to create mapping entries from mailmap content.

```rust
use bstr::ByteSlice;
use gix_mailmap::{parse, parse_ignore_errors};

fn parse_mailmap_file(file_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Read the mailmap file content
    let content = std::fs::read(file_path)?;
    
    println!("Parsing mailmap file: {}", file_path);
    println!("Valid entries:");
    
    // Option 1: Process all entries, handling errors explicitly
    for (i, result) in parse(&content).enumerate() {
        match result {
            Ok(entry) => {
                println!("Entry {}: ", i + 1);
                if let Some(new_name) = entry.new_name() {
                    println!("  New Name: {}", new_name);
                }
                if let Some(new_email) = entry.new_email() {
                    println!("  New Email: {}", new_email);
                }
                if let Some(old_name) = entry.old_name() {
                    println!("  Old Name: {}", old_name);
                }
                println!("  Old Email: {}", entry.old_email());
            }
            Err(err) => println!("Error on line {}: {}", i + 1, err),
        }
    }
    
    // Option 2: Process only valid entries, silently ignoring errors
    println!("\nValid entries only (ignoring errors):");
    for (i, entry) in parse_ignore_errors(&content).enumerate() {
        println!("Entry {}: {} -> {}", 
            i + 1,
            match entry.old_name() {
                Some(name) => format!("{} <{}>", name, entry.old_email()),
                None => format!("<{}>", entry.old_email()),
            },
            match (entry.new_name(), entry.new_email()) {
                (Some(name), Some(email)) => format!("{} <{}>", name, email),
                (Some(name), None) => format!("{} <{}>", name, entry.old_email()),
                (None, Some(email)) => format!("<{}>", email),
                (None, None) => unreachable!("Entries always have at least new name or email"),
            }
        );
    }
    
    Ok(())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    parse_mailmap_file("/path/to/.mailmap")?;
    Ok(())
}
```

## Use Case 2: Resolving Author/Committer Information in a Git Repository

### Problem

You have a Git repository with inconsistent author/committer names and emails across commits, and want to normalize them using a mailmap file.

### Solution

Use `Snapshot` to create a lookup data structure and resolve signatures.

```rust
use bstr::ByteSlice;
use gix_actor::SignatureRef;
use gix_mailmap::Snapshot;

fn normalize_author_information(
    mailmap_content: &[u8],
    authors: &[(&str, &str)], // (name, email) pairs
) -> Result<(), Box<dyn std::error::Error>> {
    // Create a snapshot from the mailmap content
    let snapshot = Snapshot::from_bytes(mailmap_content);
    
    println!("Original vs. Normalized Authors:");
    println!("===============================");
    
    // Process each author
    for (name, email) in authors {
        // Create a signature reference (time field is required but not used in this example)
        let signature = SignatureRef {
            name: name.as_bytes().as_bstr(),
            email: email.as_bytes().as_bstr(),
            time: "0 +0000".as_bytes(),
        };
        
        // Resolve the signature using the mailmap
        let resolved = snapshot.resolve_cow(signature);
        
        println!("Original: {} <{}>", name, email);
        println!("Resolved: {} <{}>", resolved.name, resolved.email);
        println!("---");
    }
    
    Ok(())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Example mailmap content
    let mailmap_content = b"
        # Consolidated author information
        Jane Doe <jane.doe@example.com> <jane@old-domain.com>
        Jane Doe <jane.doe@example.com> Jane D <jane.d@example.com>
        John Smith <john.smith@example.com> Johnny <john@personal.net>
    ";
    
    // Example list of authors
    let authors = vec![
        ("Jane D", "jane.d@example.com"),
        ("Jane", "jane@old-domain.com"),
        ("Johnny", "john@personal.net"),
        ("Unknown Author", "unknown@example.com"), // Not in mailmap
    ];
    
    normalize_author_information(mailmap_content, &authors)?;
    
    Ok(())
}
```

## Use Case 3: Building a Repository Contributor Dashboard

### Problem

You're building a dashboard showing repository contributors and want to consolidate multiple identities of the same person.

### Solution

Use `Snapshot` to map different identities to their canonical form when generating contributor statistics.

```rust
use std::collections::HashMap;
use bstr::ByteSlice;
use gix_actor::{SignatureRef, Signature};
use gix_mailmap::Snapshot;

// Example commit structure
struct Commit {
    author: (String, String), // (name, email)
    message: String,
    date: String,
    // Other commit data...
}

fn generate_contributor_stats(
    commits: Vec<Commit>,
    mailmap_content: &[u8],
) -> HashMap<String, ContributorStats> {
    // Create mailmap snapshot
    let snapshot = Snapshot::from_bytes(mailmap_content);
    
    // Map to store contributor statistics
    let mut stats: HashMap<String, ContributorStats> = HashMap::new();
    
    for commit in commits {
        // Create signature from commit author
        let sig_ref = SignatureRef {
            name: commit.author.0.as_bytes().as_bstr(),
            email: commit.author.1.as_bytes().as_bstr(),
            time: "0 +0000".as_bytes(), // Not used in this example
        };
        
        // Resolve to canonical identity
        let resolved = snapshot.resolve(sig_ref);
        
        // Use the canonical email as the key
        let key = resolved.email.to_string();
        
        // Update stats
        let entry = stats.entry(key).or_insert_with(|| ContributorStats {
            name: resolved.name.to_string(),
            email: resolved.email.to_string(),
            commit_count: 0,
            original_identities: Vec::new(),
        });
        
        entry.commit_count += 1;
        
        // Track original identity if different
        let original_identity = format!("{} <{}>", commit.author.0, commit.author.1);
        let canonical_identity = format!("{} <{}>", resolved.name, resolved.email);
        
        if original_identity != canonical_identity 
            && !entry.original_identities.contains(&original_identity) {
            entry.original_identities.push(original_identity);
        }
    }
    
    stats
}

// Structure to hold contributor statistics
struct ContributorStats {
    name: String,
    email: String,
    commit_count: usize,
    original_identities: Vec<String>,
}

// Example usage
fn main() {
    // Example mailmap content
    let mailmap = b"
        # Canonical identities
        Jane Doe <jane.doe@example.com> <jane@old-domain.com>
        Jane Doe <jane.doe@example.com> Jane D <jane.d@example.com>
    ";
    
    // Example commit data
    let commits = vec![
        Commit {
            author: ("Jane D".to_string(), "jane.d@example.com".to_string()),
            message: "Fix bug in authentication".to_string(),
            date: "2023-01-15".to_string(),
        },
        Commit {
            author: ("Jane".to_string(), "jane@old-domain.com".to_string()),
            message: "Initial commit".to_string(),
            date: "2022-12-01".to_string(),
        },
        Commit {
            author: ("Jane Doe".to_string(), "jane.doe@example.com".to_string()),
            message: "Update documentation".to_string(),
            date: "2023-02-10".to_string(),
        },
    ];
    
    let stats = generate_contributor_stats(commits, mailmap);
    
    // Display results
    println!("Contributor Statistics:");
    for (_, stat) in stats {
        println!("Name: {}", stat.name);
        println!("Email: {}", stat.email);
        println!("Commits: {}", stat.commit_count);
        
        if !stat.original_identities.isEmpty() {
            println!("Also known as:");
            for identity in stat.original_identities {
                println!("  - {}", identity);
            }
        }
        println!("---");
    }
}
```

## Use Case 4: Creating and Updating a Mailmap File

### Problem

You want to programmatically create or update a mailmap file to consolidate contributor identities.

### Solution

Use `Entry` constructors and generate mailmap content from entries.

```rust
use bstr::ByteSlice;
use gix_mailmap::{Entry, Snapshot};
use std::collections::HashMap;
use std::fs;

fn update_mailmap_file(
    file_path: &str,
    new_mappings: Vec<(Option<&str>, Option<&str>, Option<&str>, &str)>,
) -> Result<(), Box<dyn std::error::Error>> {
    // Read existing mailmap if present
    let existing_content = if std::path::Path::new(file_path).exists() {
        fs::read(file_path)?
    } else {
        Vec::new()
    };
    
    // Parse existing entries
    let existing_snapshot = Snapshot::from_bytes(&existing_content);
    let mut entries = existing_snapshot.entries();
    
    // Add new mappings
    for (new_name, new_email, old_name, old_email) in new_mappings {
        let entry = match (new_name, new_email, old_name) {
            (Some(name), None, None) => 
                Entry::change_name_by_email(name, old_email),
            (None, Some(email), None) => 
                Entry::change_email_by_email(email, old_email),
            (None, Some(email), Some(name)) => 
                Entry::change_email_by_name_and_email(email, name, old_email),
            (Some(name), Some(email), None) => 
                Entry::change_name_and_email_by_email(name, email, old_email),
            (Some(name), Some(email), Some(old_n)) => 
                Entry::change_name_and_email_by_name_and_email(name, email, old_n, old_email),
            _ => continue, // Skip invalid combinations
        };
        
        entries.push(entry);
    }
    
    // Create a new snapshot and generate mailmap content
    let updated_snapshot = Snapshot::new(entries);
    let updated_entries = updated_snapshot.entries();
    
    // Write the updated mailmap file
    let mut content = String::from("# Mailmap file - maps author/committer identities\n");
    content.push_str("# Generated on ");
    content.push_str(&chrono::Local::now().to_string());
    content.push_str("\n\n");
    
    for entry in updated_entries {
        match (entry.new_name(), entry.new_email(), entry.old_name()) {
            (Some(name), Some(email), Some(old_name)) => {
                content.push_str(&format!("{} <{}> {} <{}>\n", 
                    name, email, old_name, entry.old_email()));
            }
            (Some(name), Some(email), None) => {
                content.push_str(&format!("{} <{}> <{}>\n", 
                    name, email, entry.old_email()));
            }
            (Some(name), None, None) => {
                content.push_str(&format!("{} <{}>\n", 
                    name, entry.old_email()));
            }
            (None, Some(email), Some(old_name)) => {
                content.push_str(&format!("<{}> {} <{}>\n", 
                    email, old_name, entry.old_email()));
            }
            (None, Some(email), None) => {
                content.push_str(&format!("<{}> <{}>\n", 
                    email, entry.old_email()));
            }
            _ => {} // Skip invalid combinations
        }
    }
    
    fs::write(file_path, content)?;
    println!("Updated mailmap file: {}", file_path);
    
    Ok(())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // New mappings to add: (new_name, new_email, old_name, old_email)
    let new_mappings = vec![
        (
            Some("Jane Doe"), 
            Some("jane.doe@example.com"), 
            Some("Jane D"), 
            "jane.d@example.com"
        ),
        (
            Some("Jane Doe"), 
            Some("jane.doe@example.com"), 
            None, 
            "jane@old-domain.com"
        ),
        (
            Some("John Smith"), 
            Some("john.smith@example.com"), 
            Some("Johnny"), 
            "john@personal.net"
        ),
    ];
    
    update_mailmap_file(".mailmap", new_mappings)?;
    
    Ok(())
}
```

## Use Case 5: Using Mailmap in a Git History Analysis Tool

### Problem

You're building a tool to analyze the history of a Git repository and need to consolidate multiple identities of contributors.

### Solution

Use `Snapshot` to resolve author information when analyzing commit history.

```rust
use std::collections::HashMap;
use bstr::ByteSlice;
use gix_actor::SignatureRef;
use gix_mailmap::Snapshot;

// Example commit data structure
struct CommitData {
    author_name: String,
    author_email: String,
    date: String,
    files_changed: Vec<String>,
    insertions: usize,
    deletions: usize,
}

fn analyze_repository_history(
    commits: Vec<CommitData>,
    mailmap_content: &[u8],
) -> Result<(), Box<dyn std::error::Error>> {
    // Create mailmap snapshot
    let snapshot = Snapshot::from_bytes(mailmap_content);
    
    // Map to track consolidated contributor statistics
    let mut contributor_stats: HashMap<String, ContributorStats> = HashMap::new();
    
    // Process each commit
    for commit in commits {
        // Create signature from commit author
        let sig_ref = SignatureRef {
            name: commit.author_name.as_bytes().as_bstr(),
            email: commit.author_email.as_bytes().as_bstr(),
            time: "0 +0000".as_bytes(), // Not used in this analysis
        };
        
        // Resolve to canonical identity
        let resolved = snapshot.resolve(sig_ref);
        
        // Use the canonical email as the key
        let key = resolved.email.to_string();
        
        // Update contributor stats
        let stats = contributor_stats.entry(key).or_insert_with(|| ContributorStats {
            name: resolved.name.to_string(),
            email: resolved.email.to_string(),
            commit_count: 0,
            files_modified: HashMap::new(),
            total_insertions: 0,
            total_deletions: 0,
            original_identities: HashMap::new(),
        });
        
        stats.commit_count += 1;
        stats.total_insertions += commit.insertions;
        stats.total_deletions += commit.deletions;
        
        // Track original identity if different
        let original_identity = format!("{} <{}>", commit.author_name, commit.author_email);
        let canonical_identity = format!("{} <{}>", resolved.name, resolved.email);
        
        if original_identity != canonical_identity {
            *stats.original_identities.entry(original_identity).or_insert(0) += 1;
        }
        
        // Track files modified
        for file in &commit.files_changed {
            *stats.files_modified.entry(file.clone()).or_insert(0) += 1;
        }
    }
    
    // Generate report
    println!("Repository Contribution Analysis (with Identity Consolidation)");
    println!("=============================================================");
    
    for (_, stats) in contributor_stats {
        println!("\nContributor: {} <{}>", stats.name, stats.email);
        println!("  Commits: {}", stats.commit_count);
        println!("  Insertions: {}", stats.total_insertions);
        println!("  Deletions: {}", stats.total_deletions);
        
        if !stats.original_identities.is_empty() {
            println!("  Also committed as:");
            for (identity, count) in stats.original_identities {
                println!("    - {} ({} commits)", identity, count);
            }
        }
        
        println!("  Top 5 files modified:");
        let mut files: Vec<_> = stats.files_modified.into_iter().collect();
        files.sort_by(|a, b| b.1.cmp(&a.1));
        
        for (file, count) in files.into_iter().take(5) {
            println!("    - {} ({} modifications)", file, count);
        }
    }
    
    Ok(())
}

// Structure to hold consolidated contributor statistics
struct ContributorStats {
    name: String,
    email: String,
    commit_count: usize,
    files_modified: HashMap<String, usize>,
    total_insertions: usize,
    total_deletions: usize,
    original_identities: HashMap<String, usize>,
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Example mailmap content
    let mailmap = b"
        Jane Doe <jane.doe@example.com> <jane@old-domain.com>
        Jane Doe <jane.doe@example.com> Jane D <jane.d@example.com>
        John Smith <john.smith@example.com> Johnny <john@personal.net>
    ";
    
    // Example commit data (would normally come from repository)
    let commits = vec![
        // ... sample commit data ...
    ];
    
    analyze_repository_history(commits, mailmap)?;
    
    Ok(())
}
```

These use cases demonstrate how the `gix-mailmap` crate can be used to parse, create, and apply Git mailmap files for identity consolidation in various Git-related tools and applications.