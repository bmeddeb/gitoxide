# gix-refspec Use Cases

This document describes the main use cases for the `gix-refspec` crate, which provides functionality for working with Git reference specifications.

## Intended Audience

- Developers implementing Git clients or servers
- Tools that interact with Git repositories
- Applications that need to handle refspecs for fetch or push operations

## Use Case 1: Validating User-Provided Refspecs

### Problem

When users provide refspecs through configuration or command-line arguments, they need to be validated before use.

### Solution

Use the `parse()` function to validate refspecs and detect any syntax or semantic errors.

```rust
use bstr::ByteSlice;
use gix_refspec::{parse, parse::Operation};

// Validate a user-provided refspec
fn validate_refspec(refspec: &str, is_push: bool) -> Result<String, String> {
    let operation = if is_push {
        Operation::Push
    } else {
        Operation::Fetch
    };
    
    let refspec_bstr = refspec.as_bytes().as_bstr();
    match parse(refspec_bstr, operation) {
        Ok(parsed) => {
            // Create a descriptive message about the refspec
            let description = match (parsed.source(), parsed.destination()) {
                (Some(src), Some(dst)) => format!("Valid refspec: maps '{}' to '{}'", src, dst),
                (Some(src), None) => format!("Valid refspec: references '{}'", src),
                (None, Some(dst)) => format!("Valid refspec: references '{}'", dst),
                (None, None) => format!("Valid refspec: references default"),
            };
            Ok(description)
        },
        Err(err) => Err(format!("Invalid refspec: {}", err)),
    }
}

// Example usage
fn main() {
    let refspecs = [
        ("+refs/heads/*:refs/remotes/origin/*", false),
        ("main:refs/heads/prod", true),
        ("broken:::spec", false),
    ];
    
    for (refspec, is_push) in &refspecs {
        match validate_refspec(refspec, *is_push) {
            Ok(message) => println!("{}", message),
            Err(error) => println!("{}", error),
        }
    }
}
```

## Use Case 2: Determining Specific Refspec Actions

### Problem

After parsing a refspec, you need to determine what specific action it represents.

### Solution

Use the `instruction()` method to get a concrete, type-safe instruction for the refspec.

```rust
use bstr::ByteSlice;
use gix_refspec::{parse, parse::Operation, Instruction, instruction::{Push, Fetch}};

fn describe_refspec_action(refspec: &str, is_push: bool) -> Result<String, Box<dyn std::error::Error>> {
    let operation = if is_push {
        Operation::Push
    } else {
        Operation::Fetch
    };
    
    let parsed = parse(refspec.as_bytes().as_bstr(), operation)?;
    let instruction = parsed.instruction();
    
    let description = match instruction {
        Instruction::Push(push) => match push {
            Push::AllMatchingBranches { allow_non_fast_forward } => {
                format!("Push all matching branches{}", 
                    if allow_non_fast_forward { " with force" } else { "" })
            },
            Push::Delete { ref_or_pattern } => {
                format!("Delete ref(s) matching '{}'", ref_or_pattern)
            },
            Push::Matching { src, dst, allow_non_fast_forward } => {
                format!("Push '{}' to '{}'{}", src, dst,
                    if allow_non_fast_forward { " with force" } else { "" })
            },
        },
        Instruction::Fetch(fetch) => match fetch {
            Fetch::Only { src } => {
                format!("Fetch '{}' without updating local refs", src)
            },
            Fetch::Exclude { src } => {
                format!("Exclude '{}' from fetch", src)
            },
            Fetch::AndUpdate { src, dst, allow_non_fast_forward } => {
                format!("Fetch '{}' and update '{}'{}",
                    src, dst, if allow_non_fast_forward { " with force" } else { "" })
            },
        },
    };
    
    Ok(description)
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let refspecs = [
        ("+refs/heads/*:refs/remotes/origin/*", false),
        ("refs/tags/*", false),
        ("^refs/pull/*/head", false),
        ("main:refs/heads/prod", true),
        (":refs/heads/old-branch", true),
    ];
    
    for (refspec, is_push) in &refspecs {
        match describe_refspec_action(refspec, *is_push) {
            Ok(action) => println!("{}: {}", refspec, action),
            Err(err) => println!("{}: Error - {}", refspec, err),
        }
    }
    
    Ok(())
}
```

## Use Case 3: Working with Pattern-Based Refspecs

### Problem

Refspecs can contain wildcard patterns, and you need to match reference names against these patterns.

### Solution

Use the `MatchGroup` functionality to match references against patterns and substitute matching portions.

```rust
use bstr::{BStr, BString, ByteSlice};
use gix_refspec::{parse, parse::Operation, MatchGroup};

fn find_matching_references(
    refspec: &str,
    references: &[&str]
) -> Result<Vec<(String, Option<String>)>, Box<dyn std::error::Error>> {
    // Parse as a fetch refspec (patterns work the same for push)
    let parsed = parse(refspec.as_bytes().as_bstr(), Operation::Fetch)?;
    
    // Get source and destination patterns
    let src_pattern = match parsed.source() {
        Some(src) => src,
        None => return Err("Source pattern missing".into()),
    };
    
    let dst_pattern = parsed.destination();
    
    // Check each reference against the pattern
    let matches = references.iter()
        .map(|&reference| {
            let ref_bstr = reference.as_bytes().as_bstr();
            
            // Try to match the reference against the pattern
            if let Some(match_group) = MatchGroup::from_pattern_and_candidate(src_pattern, ref_bstr) {
                // If matched and we have a destination pattern, apply the match
                let mapped = dst_pattern.map(|dst| {
                    let mut dst_bytes = BString::from(dst.to_owned());
                    match_group.replace_all_positional_parameters(&mut dst_bytes);
                    dst_bytes.to_str().unwrap_or_default().to_string()
                });
                
                (reference.to_string(), mapped)
            } else {
                // No match
                (reference.to_string(), None)
            }
        })
        .collect();
    
    Ok(matches)
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let references = [
        "refs/heads/main",
        "refs/heads/feature/auth",
        "refs/heads/feature/ui",
        "refs/tags/v1.0.0",
    ];
    
    let refspecs = [
        "refs/heads/*:refs/remotes/origin/*",
        "refs/heads/feature/*:refs/remotes/origin/feature/*",
        "refs/tags/*:refs/tags/*",
    ];
    
    for refspec in &refspecs {
        println!("Pattern: {}", refspec);
        
        let matches = find_matching_references(refspec, &references)?;
        for (reference, mapped) in matches {
            match mapped {
                Some(destination) => println!("  {} -> {}", reference, destination),
                None => println!("  {} (no match)", reference),
            }
        }
        
        println!();
    }
    
    Ok(())
}
```

These use cases demonstrate the key functionality provided by the `gix-refspec` crate for validating refspecs, determining specific actions, and working with pattern-based refspecs.