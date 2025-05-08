# gix-ignore Use Cases

This document describes the primary use cases for the gix-ignore crate, who its intended audience is, what problems it solves, and how it solves them.

## Intended Audience

The gix-ignore crate is primarily intended for:

1. **Git Client Developers**: Developers building Git clients or similar version control tools that need to implement .gitignore functionality
2. **Build Tool Developers**: Creators of build systems, file watchers, or tools that need to respect Git ignore rules
3. **Gitoxide Component Developers**: Internal users developing other components in the gitoxide ecosystem that need to handle ignored files
4. **Repository Analysis Tool Developers**: Creators of tools that analyze Git repositories and need to respect ignore rules

## Core Use Cases

### 1. Implementing `.gitignore` Functionality in Git Clients

#### Problem

Git's `.gitignore` system has a specific set of rules and behaviors that must be correctly implemented for a Git-compatible client. These include:

- Multiple sources of ignore patterns (global, per-repository, per-directory)
- Specific pattern matching semantics (including wildcards, directory-only patterns, etc.)
- Pattern precedence rules where more specific patterns override more general ones
- Support for negated patterns with `!` prefix to re-include previously ignored files
- Support for precious files with `$` prefix that are ignored but protected from removal

#### Solution

The gix-ignore crate provides a complete implementation of Git's ignore system that can be used in Git clients:

```rust
use std::path::{Path, PathBuf};
use gix_ignore::{Search, Kind};
use gix_glob::pattern::Case;
use bstr::{BStr, BString, ByteSlice};

/// Determines if a path should be ignored by Git operations
fn is_ignored(
    repo_path: &Path,
    relative_path: &str,
    is_dir: bool
) -> Result<Option<Kind>, Box<dyn std::error::Error>> {
    let git_dir = repo_path.join(".git");
    let mut buf = Vec::new();
    
    // Load ignore patterns from global config, .git/info/exclude, etc.
    let mut search = Search::from_git_dir(
        &git_dir,
        // Optional path to user's global excludes file
        get_global_excludes_file()?,
        &mut buf
    )?;
    
    // Add patterns from all .gitignore files in the path hierarchy
    add_gitignore_files_in_path(&mut search, repo_path, Path::new(relative_path), &mut buf)?;
    
    // Check if the path matches any ignore pattern
    let path_bstr = BString::from(relative_path);
    let case = determine_case_sensitivity(repo_path);
    
    let match_result = search.pattern_matching_relative_path(
        &path_bstr,
        Some(is_dir),
        case
    );
    
    Ok(match_result.map(|m| m.kind))
}

/// Add all .gitignore files from repository root to the given path
fn add_gitignore_files_in_path(
    search: &mut Search,
    repo_root: &Path,
    relative_path: &Path,
    buf: &mut Vec<u8>
) -> Result<(), Box<dyn std::error::Error>> {
    let mut current = PathBuf::new();
    
    // For each component in the path
    for component in relative_path.parent().unwrap_or(Path::new("")).components() {
        current.push(component);
        let gitignore_path = repo_root.join(&current).join(".gitignore");
        
        // Add .gitignore file if it exists
        if gitignore_path.exists() {
            std::fs::read(&gitignore_path).map(|content| {
                search.add_patterns_buffer(
                    &content,
                    gitignore_path.clone(),
                    Some(repo_root)
                );
            })?;
        }
    }
    
    Ok(())
}

// Helper functions (implementation would depend on environment)
fn get_global_excludes_file() -> Result<Option<PathBuf>, Box<dyn std::error::Error>> {
    // In a real implementation, this would check Git's config
    // For example: ~/.config/git/ignore or value from core.excludesFile
    Ok(None)
}

fn determine_case_sensitivity(_repo_path: &Path) -> Case {
    // In a real implementation, this would check the filesystem
    // or Git's config (core.ignoreCase)
    Case::Sensitive
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let repo_path = Path::new("/path/to/repo");
    
    for entry in ["file.txt", "build/output", "node_modules/package.json"] {
        let is_dir = entry.ends_with("/");
        match is_ignored(repo_path, entry, is_dir)? {
            Some(Kind::Expendable) => println!("{} is ignored (expendable)", entry),
            Some(Kind::Precious) => println!("{} is ignored but precious", entry),
            None => println!("{} is tracked", entry),
        }
    }
    
    Ok(())
}
```

### 2. Excluding Files in Build Systems and File Watchers

#### Problem

Build systems, file watchers, and other development tools need to respect Git's ignore rules to avoid processing files that are explicitly excluded from version control.

#### Solution

The gix-ignore crate can be integrated into build systems to efficiently filter out ignored files:

```rust
use std::path::{Path, PathBuf};
use gix_ignore::Search;
use gix_glob::pattern::Case;
use bstr::BString;
use std::time::Instant;

struct BuildSystem {
    ignore_search: Search,
    repo_root: PathBuf,
}

impl BuildSystem {
    // Initialize the build system with Git ignore rules
    fn new(repo_path: PathBuf) -> Result<Self, Box<dyn std::error::Error>> {
        let git_dir = repo_path.join(".git");
        let mut buf = Vec::new();
        
        // Create search from Git's ignore files
        let mut ignore_search = Search::from_git_dir(&git_dir, None, &mut buf)?;
        
        // Add build-specific ignores as overrides
        let build_ignores = [
            "*.tmp",              // Temporary build files
            "build/intermediate/", // Intermediate build outputs
        ];
        
        // Merge the build ignores into the search
        let build_overrides = Search::from_overrides(build_ignores);
        ignore_search.patterns.extend(build_overrides.patterns);
        
        Ok(Self {
            ignore_search,
            repo_root: repo_path,
        })
    }
    
    // Process files for the build, skipping ignored ones
    fn process_files(&self) -> Result<(), Box<dyn std::error::Error>> {
        let start = Instant::now();
        let mut processed = 0;
        let mut skipped = 0;
        
        // Walk the directory tree
        self.walk_directory(&self.repo_root, |path| {
            let relative_path = path.strip_prefix(&self.repo_root)
                .unwrap()
                .to_string_lossy();
                
            // Check if the path is ignored
            let is_dir = path.is_dir();
            let path_bstr = BString::from(relative_path.as_bytes());
            
            if self.ignore_search.pattern_matching_relative_path(
                &path_bstr,
                Some(is_dir),
                Case::Sensitive,
            ).is_some() {
                // Skip ignored files
                skipped += 1;
            } else {
                // Process non-ignored files
                self.process_file(path);
                processed += 1;
            }
        })?;
        
        println!("Build completed in {:?}", start.elapsed());
        println!("Files processed: {}", processed);
        println!("Files skipped (ignored): {}", skipped);
        
        Ok(())
    }
    
    // Helper to walk the directory recursively
    fn walk_directory<F>(&self, dir: &Path, mut callback: F) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnMut(&Path)
    {
        if !dir.is_dir() {
            return Ok(());
        }
        
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            
            callback(&path);
            
            if path.is_dir() {
                self.walk_directory(&path, &mut callback)?;
            }
        }
        
        Ok(())
    }
    
    // Process a single file
    fn process_file(&self, path: &Path) {
        // In a real build system, this would compile, minify, etc.
        println!("Processing: {}", path.display());
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let build_system = BuildSystem::new(PathBuf::from("."))?;
    build_system.process_files()?;
    Ok(())
}
```

### 3. Implementing Clean Commands with Precious File Protection

#### Problem

Git's `clean` command removes untracked files, but should respect both regular ignore patterns and the special "precious" file designation (patterns prefixed with `$`). Precious files should be ignored for status reporting but protected from removal.

#### Solution

The gix-ignore crate's `Kind` enum allows distinguishing between expendable and precious ignored files:

```rust
use std::path::{Path, PathBuf};
use gix_ignore::{Search, Kind};
use gix_glob::pattern::Case;
use bstr::BString;

enum FileStatus {
    Tracked,
    Untracked,
    Ignored(Kind),
}

struct CleanCommand {
    repo_path: PathBuf,
    ignore_search: Search,
}

impl CleanCommand {
    fn new(repo_path: PathBuf) -> Result<Self, Box<dyn std::error::Error>> {
        let git_dir = repo_path.join(".git");
        let mut buf = Vec::new();
        
        // Load ignore patterns
        let ignore_search = Search::from_git_dir(&git_dir, None, &mut buf)?;
        
        Ok(Self {
            repo_path,
            ignore_search,
        })
    }
    
    fn get_file_status(&self, relative_path: &str, is_dir: bool) -> FileStatus {
        // In a real implementation, we'd check if the file is tracked in the index
        let is_tracked = false; // Placeholder
        
        if is_tracked {
            return FileStatus::Tracked;
        }
        
        // Check ignore status
        let path_bstr = BString::from(relative_path);
        match self.ignore_search.pattern_matching_relative_path(
            &path_bstr,
            Some(is_dir),
            Case::Sensitive,
        ) {
            Some(matched) => FileStatus::Ignored(matched.kind),
            None => FileStatus::Untracked,
        }
    }
    
    fn clean(&self, dry_run: bool) -> Result<(), Box<dyn std::error::Error>> {
        let mut removed = Vec::new();
        let mut would_remove = Vec::new();
        let mut protected = Vec::new();
        
        self.walk_directory(&self.repo_path, |path| {
            if path == &self.repo_path {
                return; // Skip root
            }
            
            // Get path relative to repository root
            let relative_path = path.strip_prefix(&self.repo_path)
                .unwrap()
                .to_string_lossy()
                .to_string();
                
            // Check file status
            let is_dir = path.is_dir();
            match self.get_file_status(&relative_path, is_dir) {
                FileStatus::Tracked => {
                    // Do nothing with tracked files
                }
                FileStatus::Untracked => {
                    // Untracked files should be removed
                    if dry_run {
                        would_remove.push(relative_path);
                    } else {
                        // Remove the file or directory
                        if is_dir {
                            std::fs::remove_dir_all(path)?;
                        } else {
                            std::fs::remove_file(path)?;
                        }
                        removed.push(relative_path);
                    }
                }
                FileStatus::Ignored(Kind::Expendable) => {
                    // Regular ignored files are also removed
                    if dry_run {
                        would_remove.push(relative_path);
                    } else {
                        // Remove the file or directory
                        if is_dir {
                            std::fs::remove_dir_all(path)?;
                        } else {
                            std::fs::remove_file(path)?;
                        }
                        removed.push(relative_path);
                    }
                }
                FileStatus::Ignored(Kind::Precious) => {
                    // Precious ignored files are protected
                    protected.push(relative_path);
                }
            }
            
            Ok::<_, Box<dyn std::error::Error>>(())
        })?;
        
        // Print summary
        if dry_run {
            println!("Would remove the following files:");
            for path in would_remove {
                println!("  {}", path);
            }
        } else {
            println!("Removed the following files:");
            for path in removed {
                println!("  {}", path);
            }
        }
        
        println!("Protected the following precious files:");
        for path in protected {
            println!("  {}", path);
        }
        
        Ok(())
    }
    
    fn walk_directory<F>(&self, dir: &Path, mut callback: F) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnMut(&Path) -> Result<(), Box<dyn std::error::Error>>
    {
        if !dir.is_dir() {
            return Ok(());
        }
        
        // Process all entries in the directory
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            
            callback(&path)?;
            
            // Recursively process subdirectories
            if path.is_dir() {
                self.walk_directory(&path, &mut callback)?;
            }
        }
        
        Ok(())
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let clean_cmd = CleanCommand::new(PathBuf::from("."))?;
    
    // First do a dry run
    clean_cmd.clean(true)?;
    
    // Ask for confirmation
    println!("Proceed with removal? (y/n)");
    let mut input = String::new();
    std::io::stdin().read_line(&mut input)?;
    
    if input.trim().to_lowercase() == "y" {
        clean_cmd.clean(false)?;
    }
    
    Ok(())
}
```

### 4. Integrating Git Ignore Rules in File Browsers and Editors

#### Problem

Code editors, file browsers, and other development tools often need to respect Git's ignore rules to hide files that are not part of the project.

#### Solution

The gix-ignore crate can be used to filter files in UI components:

```rust
use std::path::{Path, PathBuf};
use gix_ignore::Search;
use gix_glob::pattern::Case;
use bstr::BString;

struct FileExplorer {
    root_path: PathBuf,
    ignore_search: Option<Search>,
    show_ignored: bool,
}

impl FileExplorer {
    fn new(root_path: PathBuf) -> Self {
        Self {
            root_path,
            ignore_search: None,
            show_ignored: false,
        }
    }
    
    fn initialize_git_integration(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        // Check if directory is a Git repository
        let git_dir = self.root_path.join(".git");
        if git_dir.exists() {
            let mut buf = Vec::new();
            let ignore_search = Search::from_git_dir(&git_dir, None, &mut buf)?;
            self.ignore_search = Some(ignore_search);
            println!("Git integration enabled - respecting .gitignore rules");
        } else {
            println!("Not a Git repository - showing all files");
        }
        
        Ok(())
    }
    
    fn list_files(&self, dir: &Path) -> Result<Vec<PathBuf>, Box<dyn std::error::Error>> {
        let mut files = Vec::new();
        
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            
            // Skip entries according to ignore rules
            if !self.should_display(&path)? {
                continue;
            }
            
            files.push(path);
        }
        
        // Sort files for display
        files.sort();
        
        Ok(files)
    }
    
    fn should_display(&self, path: &Path) -> Result<bool, Box<dyn std::error::Error>> {
        // Always show files if no Git integration or if showing ignored files
        if self.ignore_search.is_none() || self.show_ignored {
            return Ok(true);
        }
        
        // Get path relative to root
        let relative_path = path.strip_prefix(&self.root_path)?;
        let path_str = relative_path.to_string_lossy();
        let is_dir = path.is_dir();
        
        // Check if path matches an ignore pattern
        let path_bstr = BString::from(path_str.as_bytes());
        
        Ok(self.ignore_search.as_ref().unwrap().pattern_matching_relative_path(
            &path_bstr,
            Some(is_dir),
            Case::Sensitive,
        ).is_none())
    }
    
    fn toggle_show_ignored(&mut self) {
        self.show_ignored = !self.show_ignored;
        println!(
            "Now {} ignored files", 
            if self.show_ignored { "showing" } else { "hiding" }
        );
    }
    
    // Simulate user interaction with the file explorer
    fn run_interactive_session(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        println!("File Explorer - {} ({}ignored files)",
            self.root_path.display(),
            if self.show_ignored { "showing " } else { "hiding " }
        );
        
        let files = self.list_files(&self.root_path)?;
        println!("Files in current directory:");
        
        for (i, path) in files.iter().enumerate() {
            let name = path.file_name().unwrap().to_string_lossy();
            let is_dir = path.is_dir();
            println!("{:2}. {}{}", i + 1, name, if is_dir { "/" } else { "" });
        }
        
        println!("\nOptions:");
        println!("  t = Toggle showing ignored files");
        println!("  q = Quit");
        
        // In a real UI, this would be handled by the application framework
        // Here we just simulate a simple command
        let command = "t"; // Simulate user pressing 't'
        
        match command {
            "t" => self.toggle_show_ignored(),
            "q" => return Ok(()),
            _ => println!("Unknown command"),
        }
        
        Ok(())
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut explorer = FileExplorer::new(PathBuf::from("."));
    explorer.initialize_git_integration()?;
    explorer.run_interactive_session()?;
    Ok(())
}
```

### 5. Repository Analysis and Metrics

#### Problem

Tools that analyze repositories or generate metrics about codebase size, composition, or activity need to respect Git's ignore rules to provide accurate information.

#### Solution

The gix-ignore crate can be used to filter files during repository analysis:

```rust
use std::path::{Path, PathBuf};
use std::collections::HashMap;
use gix_ignore::Search;
use gix_glob::pattern::Case;
use bstr::BString;

struct RepositoryAnalyzer {
    repo_path: PathBuf,
    ignore_search: Search,
}

impl RepositoryAnalyzer {
    fn new(repo_path: PathBuf) -> Result<Self, Box<dyn std::error::Error>> {
        let git_dir = repo_path.join(".git");
        let mut buf = Vec::new();
        
        // Load ignore patterns
        let ignore_search = Search::from_git_dir(&git_dir, None, &mut buf)?;
        
        Ok(Self {
            repo_path,
            ignore_search,
        })
    }
    
    fn analyze_file_types(&self) -> Result<HashMap<String, usize>, Box<dyn std::error::Error>> {
        let mut file_types = HashMap::new();
        
        self.walk_tracked_files(&self.repo_path, |path| {
            if let Some(ext) = path.extension() {
                let ext = ext.to_string_lossy().to_lowercase();
                *file_types.entry(ext.to_string()).or_insert(0) += 1;
            }
            Ok(())
        })?;
        
        Ok(file_types)
    }
    
    fn calculate_loc(&self) -> Result<HashMap<String, usize>, Box<dyn std::error::Error>> {
        let mut loc_by_lang = HashMap::new();
        
        self.walk_tracked_files(&self.repo_path, |path| {
            if let Some(ext) = path.extension() {
                let ext = ext.to_string_lossy().to_lowercase();
                
                // Only count certain file types
                let language = match ext.as_str() {
                    "rs" => Some("Rust"),
                    "js" => Some("JavaScript"),
                    "py" => Some("Python"),
                    "c" | "h" => Some("C"),
                    "cpp" | "hpp" => Some("C++"),
                    _ => None,
                };
                
                if let Some(lang) = language {
                    // Count lines in the file
                    let content = std::fs::read_to_string(path)?;
                    let line_count = content.lines().count();
                    
                    *loc_by_lang.entry(lang.to_string()).or_insert(0) += line_count;
                }
            }
            Ok(())
        })?;
        
        Ok(loc_by_lang)
    }
    
    fn is_tracked(&self, path: &Path) -> Result<bool, Box<dyn std::error::Error>> {
        // Get path relative to repository root
        let relative_path = path.strip_prefix(&self.repo_path)?;
        let path_str = relative_path.to_string_lossy();
        let is_dir = path.is_dir();
        
        // Check if path matches an ignore pattern
        let path_bstr = BString::from(path_str.as_bytes());
        
        Ok(self.ignore_search.pattern_matching_relative_path(
            &path_bstr,
            Some(is_dir),
            Case::Sensitive,
        ).is_none())
    }
    
    fn walk_tracked_files<F>(&self, dir: &Path, mut callback: F) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnMut(&Path) -> Result<(), Box<dyn std::error::Error>>
    {
        if !dir.is_dir() {
            return Ok(());
        }
        
        // Skip the .git directory explicitly
        if dir.file_name().map_or(false, |name| name == ".git") {
            return Ok(());
        }
        
        // Skip directories that are ignored
        if dir != &self.repo_path && !self.is_tracked(dir)? {
            return Ok(());
        }
        
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_dir() {
                self.walk_tracked_files(&path, &mut callback)?;
            } else if self.is_tracked(&path)? {
                callback(&path)?;
            }
        }
        
        Ok(())
    }
    
    fn print_report(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Analyze file types
        let file_types = self.analyze_file_types()?;
        println!("File types in repository:");
        for (ext, count) in file_types.iter() {
            println!("  .{}: {} files", ext, count);
        }
        
        // Calculate lines of code
        let loc = self.calculate_loc()?;
        println!("\nLines of code by language:");
        for (lang, count) in loc.iter() {
            println!("  {}: {} lines", lang, count);
        }
        
        Ok(())
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let analyzer = RepositoryAnalyzer::new(PathBuf::from("."))?;
    analyzer.print_report()?;
    Ok(())
}
```

## Integration with Other Components

The gix-ignore crate is integrated with several other components in the gitoxide ecosystem:

### Integration with gix-status

The `gix-status` crate uses gix-ignore to determine which files should be excluded from status reporting:

```rust
use std::path::{Path, PathBuf};
use gix_ignore::Search;
use gix_glob::pattern::Case;
use bstr::BString;

enum StatusEntry {
    Untracked,
    Modified,
    Deleted,
    Ignored,
    // Other status types...
}

struct StatusCommand {
    repo_path: PathBuf,
    ignore_search: Search,
}

impl StatusCommand {
    fn new(repo_path: PathBuf) -> Result<Self, Box<dyn std::error::Error>> {
        let git_dir = repo_path.join(".git");
        let mut buf = Vec::new();
        
        // Initialize ignore searching
        let ignore_search = Search::from_git_dir(&git_dir, None, &mut buf)?;
        
        Ok(Self {
            repo_path,
            ignore_search,
        })
    }
    
    fn get_file_status(&self, relative_path: &str) -> Result<StatusEntry, Box<dyn std::error::Error>> {
        let path = self.repo_path.join(relative_path);
        let is_dir = path.is_dir();
        
        // First check if the file is ignored
        let path_bstr = BString::from(relative_path);
        if self.ignore_search.pattern_matching_relative_path(
            &path_bstr,
            Some(is_dir),
            Case::Sensitive,
        ).is_some() {
            return Ok(StatusEntry::Ignored);
        }
        
        // If not ignored, determine actual status
        // (In a real implementation, this would check the index and HEAD)
        Ok(StatusEntry::Untracked)
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // In a real implementation, this would scan the working directory
        // and compare with the index and HEAD
        let paths = ["file.txt", "node_modules/package.json", "src/main.rs"];
        
        for path in paths {
            match self.get_file_status(path)? {
                StatusEntry::Untracked => println!("?? {}", path),
                StatusEntry::Modified => println!(" M {}", path),
                StatusEntry::Deleted => println!(" D {}", path),
                StatusEntry::Ignored => {} // Ignored files are not shown by default
            }
        }
        
        Ok(())
    }
}
```

### Integration with gix-diff

The `gix-diff` crate uses gix-ignore to filter out ignored files when generating diffs:

```rust
use std::path::{Path, PathBuf};
use gix_ignore::Search;
use gix_glob::pattern::Case;
use bstr::BString;

struct DiffCommand {
    repo_path: PathBuf,
    ignore_search: Search,
    include_ignored: bool,
}

impl DiffCommand {
    fn new(repo_path: PathBuf, include_ignored: bool) -> Result<Self, Box<dyn std::error::Error>> {
        let git_dir = repo_path.join(".git");
        let mut buf = Vec::new();
        
        // Initialize ignore searching
        let ignore_search = Search::from_git_dir(&git_dir, None, &mut buf)?;
        
        Ok(Self {
            repo_path,
            ignore_search,
            include_ignored,
        })
    }
    
    fn should_include(&self, relative_path: &str) -> Result<bool, Box<dyn std::error::Error>> {
        // If we're including ignored files, include everything
        if self.include_ignored {
            return Ok(true);
        }
        
        // Check if the file is ignored
        let path = self.repo_path.join(relative_path);
        let is_dir = path.is_dir();
        let path_bstr = BString::from(relative_path);
        
        Ok(self.ignore_search.pattern_matching_relative_path(
            &path_bstr,
            Some(is_dir),
            Case::Sensitive,
        ).is_none())
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // In a real implementation, this would scan for modified files
        // and generate diffs
        let modified_files = ["src/main.rs", "build/temp.o", "README.md"];
        
        for file in modified_files {
            if self.should_include(file)? {
                println!("Diffing {}", file);
                // Generate and show diff
            } else {
                println!("Skipping ignored file: {}", file);
            }
        }
        
        Ok(())
    }
}
```

## Conclusion

The gix-ignore crate provides a critical component for any Git implementation or tool that needs to respect Git's ignore rules. Its integration with other gitoxide components creates a cohesive system that accurately implements Git's behavior.

The key strengths of the crate are:

1. **Complete Implementation**: Supports all features of Git's ignore system, including pattern precedence, negation, and precious files
2. **Performance**: Efficiently handles large repositories with many ignore patterns
3. **Ease of Integration**: Simple API that can be easily incorporated into various tools
4. **Correctness**: Carefully tested against Git's own behavior

These capabilities make gix-ignore suitable for a wide range of applications, from full Git clients to build tools and file browsers that need to respect Git's ignore rules.