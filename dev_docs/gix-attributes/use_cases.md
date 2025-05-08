# gix-attributes Use Cases

This document outlines the primary use cases for the `gix-attributes` crate, including target audiences, problems solved, and example code demonstrating solutions.

## Intended Audience

- Git implementation developers
- Build system developers who need Git attribute awareness
- Version control tool developers
- Developers creating Git-aware applications
- CI/CD pipeline creators who need to respect Git attributes

## Use Cases

### 1. Determining Text vs Binary Files

**Problem**: A developer needs to determine whether files should be treated as text or binary based on Git attributes to handle them appropriately during operations.

**Solution**: Use `gix-attributes` to check for the `text` and `binary` attributes.

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search, StateRef};
use gix_glob::pattern::Case;
use std::path::Path;

fn is_binary_file(repo_path: &Path, file_path: &str) -> Result<bool, Box<dyn std::error::Error>> {
    // Set up search infrastructure
    let mut collection = MetadataCollection::default();
    let mut buf = Vec::new();
    
    // First look for global attributes
    let mut search = Search::new_globals(
        [
            Path::new("/etc/gitattributes"),
            Path::new("~/.config/git/attributes"),
        ].into_iter(),
        &mut buf,
        &mut collection,
    )?;
    
    // Then repository-specific attributes
    search.add_patterns_file(
        repo_path.join(".gitattributes"),
        false, // Don't error if file doesn't exist
        None,
        &mut buf,
        &mut collection,
        true, // Allow macros
    )?;
    
    // Initialize search outcome
    let mut outcome = gix_attributes::search::Outcome::default();
    outcome.initialize(&collection);
    
    // Find attributes for the specific path
    let path = file_path.as_bytes().as_bstr();
    search.pattern_matching_relative_path(
        path,
        Case::Sensitive,
        None,
        &mut outcome,
    );
    
    // Check for binary/text attributes
    let mut is_binary = false;
    let mut is_text = false;
    
    for m in outcome.iter() {
        if m.assignment.name.as_str() == "binary" && m.assignment.state == StateRef::Set {
            is_binary = true;
        }
        if m.assignment.name.as_str() == "text" && m.assignment.state == StateRef::Set {
            is_text = true;
        }
        // Binary attribute explicitly unset
        if m.assignment.name.as_str() == "binary" && m.assignment.state == StateRef::Unset {
            is_binary = false;
        }
        // Text attribute explicitly unset
        if m.assignment.name.as_str() == "text" && m.assignment.state == StateRef::Unset {
            is_text = false;
        }
    }
    
    // binary attribute takes precedence over text
    if is_binary {
        return Ok(true);
    }
    
    // text attribute means not binary
    if is_text {
        return Ok(false);
    }
    
    // Default heuristic: check file extension
    Ok(matches!(
        Path::new(file_path).extension().and_then(|e| e.to_str()),
        Some("exe" | "bin" | "obj" | "dll" | "so" | "o")
    ))
}
```

### 2. Determining Line Ending Handling

**Problem**: A developer needs to determine how line endings should be handled for specific files based on Git attributes.

**Solution**: Use `gix-attributes` to check for the `eol` attribute and its value.

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search, StateRef, state};
use gix_glob::pattern::Case;
use std::path::Path;

#[derive(Debug, PartialEq, Eq)]
enum LineEndingMode {
    CRLF,
    LF,
    Native,
    Keep,
}

fn get_line_ending_mode(repo_path: &Path, file_path: &str) -> Result<LineEndingMode, Box<dyn std::error::Error>> {
    // Set up search infrastructure
    let mut collection = MetadataCollection::default();
    let mut buf = Vec::new();
    let mut search = Search::default();
    
    // Add repository attributes
    search.add_patterns_file(
        repo_path.join(".gitattributes"),
        false, // Don't error if file doesn't exist
        None,
        &mut buf,
        &mut collection,
        true, // Allow macros
    )?;
    
    // Initialize search outcome
    let mut outcome = gix_attributes::search::Outcome::default();
    outcome.initialize(&collection);
    
    // Find attributes for the specific path
    let path = file_path.as_bytes().as_bstr();
    search.pattern_matching_relative_path(
        path,
        Case::Sensitive,
        None,
        &mut outcome,
    );
    
    // Check for eol attribute
    for m in outcome.iter() {
        if m.assignment.name.as_str() == "eol" {
            if let StateRef::Value(value) = m.assignment.state {
                let value_str = value.as_bytes().as_bstr().to_str()?;
                return Ok(match value_str {
                    "crlf" => LineEndingMode::CRLF,
                    "lf" => LineEndingMode::LF,
                    "native" => LineEndingMode::Native,
                    _ => LineEndingMode::Native, // Default to native on unknown value
                });
            }
        }
        
        // Check for text=auto which implies native line endings
        if m.assignment.name.as_str() == "text" {
            if let StateRef::Value(value) = m.assignment.state {
                let value_str = value.as_bytes().as_bstr().to_str()?;
                if value_str == "auto" {
                    return Ok(LineEndingMode::Native);
                }
            } else if m.assignment.state == StateRef::Set {
                return Ok(LineEndingMode::Native); // text attribute set implies native
            }
        }
    }
    
    // Default: Keep existing line endings
    Ok(LineEndingMode::Keep)
}
```

### 3. Checking if a File Should Be Diffable

**Problem**: A tool needs to determine whether to generate diffs for specific files based on Git attributes.

**Solution**: Use `gix-attributes` to check for the `diff` attribute.

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search, StateRef};
use gix_glob::pattern::Case;
use std::path::Path;

fn is_diffable(repo_path: &Path, file_path: &str) -> Result<bool, Box<dyn std::error::Error>> {
    // Set up search infrastructure
    let mut collection = MetadataCollection::default();
    let mut buf = Vec::new();
    let mut search = Search::default();
    
    // Add repository and global attributes
    let mut search = Search::new_globals(
        std::iter::empty::<std::path::PathBuf>(), // No global attributes in this example
        &mut buf,
        &mut collection,
    )?;
    
    search.add_patterns_file(
        repo_path.join(".gitattributes"),
        false, // Don't error if file doesn't exist
        None,
        &mut buf,
        &mut collection,
        true, // Allow macros
    )?;
    
    // Initialize search outcome
    let mut outcome = gix_attributes::search::Outcome::default();
    outcome.initialize(&collection);
    
    // Find attributes for the specific path
    let path = file_path.as_bytes().as_bstr();
    search.pattern_matching_relative_path(
        path,
        Case::Sensitive,
        None,
        &mut outcome,
    );
    
    // Check for diff attribute
    for m in outcome.iter() {
        if m.assignment.name.as_str() == "diff" {
            match m.assignment.state {
                StateRef::Set => return Ok(true),
                StateRef::Unset => return Ok(false),
                _ => {} // Continue checking other attributes
            }
        }
        
        // Check for binary attribute, which implies -diff
        if m.assignment.name.as_str() == "binary" && m.assignment.state == StateRef::Set {
            return Ok(false);
        }
    }
    
    // Default: Files are diffable unless they're detected as binary
    Ok(true)
}
```

### 4. Custom Attribute Handling for Specialized Tools

**Problem**: A specialized tool needs to check for custom attributes that control its behavior.

**Solution**: Use `gix-attributes` to look for tool-specific attributes and their values.

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search, StateRef};
use gix_glob::pattern::Case;
use std::path::Path;

#[derive(Debug, Default)]
struct CustomToolConfig {
    process: bool,
    priority: String,
    flags: Vec<String>,
}

fn get_tool_config(repo_path: &Path, file_path: &str) -> Result<CustomToolConfig, Box<dyn std::error::Error>> {
    // Set up search infrastructure
    let mut collection = MetadataCollection::default();
    let mut buf = Vec::new();
    let mut search = Search::default();
    
    // Add repository attributes
    search.add_patterns_file(
        repo_path.join(".gitattributes"),
        false, // Don't error if file doesn't exist
        None,
        &mut buf,
        &mut collection,
        true, // Allow macros
    )?;
    
    // Initialize search outcome
    let mut outcome = gix_attributes::search::Outcome::default();
    outcome.initialize(&collection);
    
    // Find attributes for the specific path
    let path = file_path.as_bytes().as_bstr();
    search.pattern_matching_relative_path(
        path,
        Case::Sensitive,
        None,
        &mut outcome,
    );
    
    // Build tool configuration
    let mut config = CustomToolConfig::default();
    
    for m in outcome.iter() {
        match m.assignment.name.as_str() {
            "tool-process" => {
                config.process = m.assignment.state == StateRef::Set;
            }
            "tool-priority" => {
                if let StateRef::Value(value) = m.assignment.state {
                    config.priority = value.as_bytes().as_bstr().to_str()?.to_string();
                }
            }
            "tool-flags" => {
                if let StateRef::Value(value) = m.assignment.state {
                    let flags = value.as_bytes().as_bstr().to_str()?;
                    config.flags = flags.split(',').map(|s| s.trim().to_string()).collect();
                }
            }
            _ => {} // Ignore other attributes
        }
    }
    
    Ok(config)
}
```

### 5. Building a File Filter Based on Attributes

**Problem**: A developer needs to filter files in a repository based on Git attributes for operations like archiving.

**Solution**: Use `gix-attributes` to build a filter function based on attribute patterns.

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search, StateRef};
use gix_glob::pattern::Case;
use std::path::{Path, PathBuf};

fn filter_files_by_attribute(
    repo_path: &Path,
    files: &[PathBuf],
    attribute_name: &str,
    wanted_state: StateRef<'_>,
) -> Result<Vec<PathBuf>, Box<dyn std::error::Error>> {
    // Set up search infrastructure
    let mut collection = MetadataCollection::default();
    let mut buf = Vec::new();
    let mut search = Search::default();
    
    // Add repository attributes
    search.add_patterns_file(
        repo_path.join(".gitattributes"),
        false, // Don't error if file doesn't exist
        None,
        &mut buf,
        &mut collection,
        true, // Allow macros
    )?;
    
    // Initialize search outcome
    let mut outcome = gix_attributes::search::Outcome::default();
    outcome.initialize(&collection);
    
    // Filter files based on attribute state
    let mut matching_files = Vec::new();
    
    for file in files {
        let rel_path = file.strip_prefix(repo_path)
            .map_err(|_| "File is not in repository")?;
        
        // Reset the outcome for the next file
        outcome.reset();
        
        // Find attributes for this file
        let path = rel_path.to_str()
            .ok_or("Invalid UTF-8 in path")?
            .as_bytes().as_bstr();
            
        search.pattern_matching_relative_path(
            path,
            Case::Sensitive,
            None,
            &mut outcome,
        );
        
        // Check if this file has the attribute with the wanted state
        let mut matches = false;
        
        for m in outcome.iter() {
            if m.assignment.name.as_str() == attribute_name && m.assignment.state == wanted_state {
                matches = true;
                break;
            }
        }
        
        if matches {
            matching_files.push(file.clone());
        }
    }
    
    Ok(matching_files)
}

// Example usage:
// filter_files_by_attribute(repo_path, &all_files, "export", StateRef::Set) 
// - Returns all files marked with "export" attribute
// filter_files_by_attribute(repo_path, &all_files, "export", StateRef::Unset)
// - Returns all files marked with "-export" attribute
```

### 6. Generating File-Specific Configuration for Editors/IDEs

**Problem**: An editor or IDE needs to apply different settings (like tab size, indent style) based on file types, and wants to respect Git attributes.

**Solution**: Use `gix-attributes` to check for editor-specific attributes and generate appropriate configuration.

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search, StateRef};
use gix_glob::pattern::Case;
use std::path::Path;
use std::collections::HashMap;

#[derive(Debug, Default)]
struct EditorConfig {
    tab_width: Option<usize>,
    indent_style: Option<String>,
    charset: Option<String>,
    trim_trailing_whitespace: Option<bool>,
    insert_final_newline: Option<bool>,
}

fn get_editor_config(repo_path: &Path, file_path: &str) -> Result<EditorConfig, Box<dyn std::error::Error>> {
    // Set up search infrastructure
    let mut collection = MetadataCollection::default();
    let mut buf = Vec::new();
    let mut search = Search::default();
    
    // Add repository attributes
    search.add_patterns_file(
        repo_path.join(".gitattributes"),
        false, // Don't error if file doesn't exist
        None,
        &mut buf,
        &mut collection,
        true, // Allow macros
    )?;
    
    // Initialize search outcome
    let mut outcome = gix_attributes::search::Outcome::default();
    outcome.initialize(&collection);
    
    // Find attributes for the specific path
    let path = file_path.as_bytes().as_bstr();
    search.pattern_matching_relative_path(
        path,
        Case::Sensitive,
        None,
        &mut outcome,
    );
    
    // Build editor configuration
    let mut config = EditorConfig::default();
    
    for m in outcome.iter() {
        match m.assignment.name.as_str() {
            "editor.tabWidth" => {
                if let StateRef::Value(value) = m.assignment.state {
                    let width_str = value.as_bytes().as_bstr().to_str()?;
                    if let Ok(width) = width_str.parse::<usize>() {
                        config.tab_width = Some(width);
                    }
                }
            }
            "editor.indentStyle" => {
                if let StateRef::Value(value) = m.assignment.state {
                    config.indent_style = Some(value.as_bytes().as_bstr().to_str()?.to_string());
                }
            }
            "editor.charset" => {
                if let StateRef::Value(value) = m.assignment.state {
                    config.charset = Some(value.as_bytes().as_bstr().to_str()?.to_string());
                }
            }
            "editor.trimTrailingWhitespace" => {
                config.trim_trailing_whitespace = Some(m.assignment.state == StateRef::Set);
            }
            "editor.insertFinalNewline" => {
                config.insert_final_newline = Some(m.assignment.state == StateRef::Set);
            }
            _ => {} // Ignore other attributes
        }
    }
    
    // Apply defaults based on known file types if not set by attributes
    if config.tab_width.is_none() && file_path.ends_with(".rs") {
        config.tab_width = Some(4);
    }
    
    Ok(config)
}
```

## Integration Examples

### Integration with a Build System

This example shows how to integrate `gix-attributes` with a build system to determine how to process different files:

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search, StateRef};
use gix_glob::pattern::Case;
use std::path::{Path, PathBuf};
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Eq)]
enum BuildAction {
    Compile,
    Copy,
    Ignore,
    Custom(String),
}

fn determine_build_actions(
    repo_path: &Path,
    files: &[PathBuf],
) -> Result<HashMap<PathBuf, BuildAction>, Box<dyn std::error::Error>> {
    // Set up search infrastructure
    let mut collection = MetadataCollection::default();
    let mut buf = Vec::new();
    let mut search = Search::default();
    
    // Add repository attributes
    search.add_patterns_file(
        repo_path.join(".gitattributes"),
        false, // Don't error if file doesn't exist
        None,
        &mut buf,
        &mut collection,
        true, // Allow macros
    )?;
    
    // Initialize search outcome
    let mut outcome = gix_attributes::search::Outcome::default();
    outcome.initialize(&collection);
    
    // Determine actions for each file
    let mut actions = HashMap::new();
    
    for file in files {
        let rel_path = file.strip_prefix(repo_path)
            .map_err(|_| "File is not in repository")?;
        
        // Reset the outcome for the next file
        outcome.reset();
        
        // Find attributes for this file
        let path = rel_path.to_str()
            .ok_or("Invalid UTF-8 in path")?
            .as_bytes().as_bstr();
            
        search.pattern_matching_relative_path(
            path,
            Case::Sensitive,
            None,
            &mut outcome,
        );
        
        // Determine action based on attributes
        let mut action = None;
        
        for m in outcome.iter() {
            match m.assignment.name.as_str() {
                "build" => {
                    if let StateRef::Value(value) = m.assignment.state {
                        let action_str = value.as_bytes().as_bstr().to_str()?;
                        action = Some(match action_str {
                            "compile" => BuildAction::Compile,
                            "copy" => BuildAction::Copy,
                            "ignore" => BuildAction::Ignore,
                            custom => BuildAction::Custom(custom.to_string()),
                        });
                    } else if m.assignment.state == StateRef::Set {
                        action = Some(BuildAction::Compile);
                    } else if m.assignment.state == StateRef::Unset {
                        action = Some(BuildAction::Ignore);
                    }
                }
                "nobuild" if m.assignment.state == StateRef::Set => {
                    action = Some(BuildAction::Ignore);
                }
                _ => {} // Ignore other attributes
            }
        }
        
        // Default action based on file extension if not specified by attributes
        if action.is_none() {
            action = Some(match file.extension().and_then(|e| e.to_str()) {
                Some("c" | "cpp" | "rs" | "go") => BuildAction::Compile,
                Some("html" | "css" | "jpg" | "png") => BuildAction::Copy,
                Some("md" | "txt" | "gitignore") => BuildAction::Ignore,
                _ => BuildAction::Copy, // Default to copy
            });
        }
        
        actions.insert(file.clone(), action.unwrap_or(BuildAction::Copy));
    }
    
    Ok(actions)
}
```

### Integration with a Version Control System

This example shows how to use `gix-attributes` to handle file-specific merge strategies in a VCS:

```rust
use bstr::ByteSlice;
use gix_attributes::{search::MetadataCollection, Search, StateRef};
use gix_glob::pattern::Case;
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq)]
enum MergeStrategy {
    Default,
    Ours,
    Theirs,
    Union,
    Binary,
    Custom(String),
    NoMerge,
}

fn determine_merge_strategy(
    repo_path: &Path, 
    file_path: &str
) -> Result<MergeStrategy, Box<dyn std::error::Error>> {
    // Set up search infrastructure
    let mut collection = MetadataCollection::default();
    let mut buf = Vec::new();
    let mut search = Search::default();
    
    // Add repository attributes
    search.add_patterns_file(
        repo_path.join(".gitattributes"),
        false, // Don't error if file doesn't exist
        None,
        &mut buf,
        &mut collection,
        true, // Allow macros
    )?;
    
    // Initialize search outcome
    let mut outcome = gix_attributes::search::Outcome::default();
    outcome.initialize(&collection);
    
    // Find attributes for the specific path
    let path = file_path.as_bytes().as_bstr();
    search.pattern_matching_relative_path(
        path,
        Case::Sensitive,
        None,
        &mut outcome,
    );
    
    // Determine merge strategy based on attributes
    for m in outcome.iter() {
        match m.assignment.name.as_str() {
            "merge" => {
                if let StateRef::Value(value) = m.assignment.state {
                    let strategy = value.as_bytes().as_bstr().to_str()?;
                    return Ok(match strategy {
                        "ours" => MergeStrategy::Ours,
                        "theirs" => MergeStrategy::Theirs,
                        "union" => MergeStrategy::Union,
                        "binary" => MergeStrategy::Binary,
                        custom => MergeStrategy::Custom(custom.to_string()),
                    });
                } else if m.assignment.state == StateRef::Set {
                    return Ok(MergeStrategy::Default);
                } else if m.assignment.state == StateRef::Unset {
                    return Ok(MergeStrategy::NoMerge);
                }
            }
            "binary" if m.assignment.state == StateRef::Set => {
                return Ok(MergeStrategy::Binary);
            }
            _ => {} // Ignore other attributes
        }
    }
    
    // Default strategy
    Ok(MergeStrategy::Default)
}
```