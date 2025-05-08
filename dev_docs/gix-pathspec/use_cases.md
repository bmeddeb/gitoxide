# gix-pathspec Use Cases

This document describes the primary use cases for the gix-pathspec crate, who its intended audience is, what problems it solves, and how it solves them.

## Intended Audience

The gix-pathspec crate is primarily intended for:

1. **Git Client Developers**: Developers building Git clients or tools that need to implement Git's pathspec functionality
2. **Command-Line Tool Authors**: Developers creating tools that need Git-compatible path filtering
3. **Gitoxide Component Developers**: Internal users developing other components in the gitoxide ecosystem
4. **Build Tool Developers**: Creators of build systems that want to support Git-style path specifications

## Core Use Cases

### 1. Implementing `git add` Path Filtering

#### Problem

Git's `add` command allows users to specify which files to add to the staging area using complex path specifications. These specifications can include glob patterns, attribute-based filtering, case sensitivity options, and more. Implementing this functionality requires correctly parsing and matching these pathspecs.

#### Solution

The gix-pathspec crate provides the exact functionality needed to implement Git's path filtering for the `add` command:

```rust
use std::path::{Path, PathBuf};
use gix_pathspec::{parse, Defaults, Search, MagicSignature, SearchMode};
use bstr::{BStr, ByteSlice};
use gix_attributes::search::Outcome;

struct AddCommand {
    repo_path: PathBuf,
    pathspecs: Vec<String>,
    ignore_case: bool,
}

impl AddCommand {
    fn new(repo_path: PathBuf, pathspecs: Vec<String>, ignore_case: bool) -> Self {
        Self {
            repo_path,
            pathspecs,
            ignore_case,
        }
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Create default settings based on command flags
        let mut defaults = Defaults::default();
        if self.ignore_case {
            defaults.signature |= MagicSignature::ICASE;
        }
        
        // Parse pathspecs
        let mut patterns = Vec::new();
        for spec in &self.pathspecs {
            match parse(spec.as_bytes(), defaults) {
                Ok(pattern) => patterns.push(pattern),
                Err(e) => println!("Warning: Invalid pathspec '{}': {}", spec, e),
            }
        }
        
        // Create a search from the patterns
        let mut search = Search::new(patterns);
        
        // Find all files in the repository
        let files = self.list_repository_files()?;
        let mut files_to_add = Vec::new();
        
        // Attribute handler (simplified for example)
        let mut attribute_handler = |_: &BStr, _, _, _: &mut Outcome| true;
        
        // Match files against pathspecs
        for file in &files {
            let relative_path = file.strip_prefix(&self.repo_path)?;
            let path_str = relative_path.to_string_lossy();
            let path_bstr = path_str.as_bytes().as_bstr();
            
            let is_dir = file.is_dir();
            
            // Check if this file matches any pathspec
            if let Some(matched) = search.pattern_matching_relative_path(
                path_bstr,
                Some(is_dir),
                &mut attribute_handler,
            ) {
                if !matched.is_excluded() {
                    files_to_add.push(file.clone());
                }
            }
        }
        
        // Process matched files (add to index)
        println!("Adding {} files to index", files_to_add.len());
        for file in files_to_add {
            println!("  {}", file.display());
            // In a real implementation, we would add the file to the index here
        }
        
        Ok(())
    }
    
    // Helper to list all files in the repository
    fn list_repository_files(&self) -> Result<Vec<PathBuf>, Box<dyn std::error::Error>> {
        let mut result = Vec::new();
        self.walk_directory(&self.repo_path, |path| {
            result.push(path.to_path_buf());
            Ok(())
        })?;
        Ok(result)
    }
    
    // Helper to recursively walk directories
    fn walk_directory<F>(&self, dir: &Path, mut callback: F) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnMut(&Path) -> Result<(), Box<dyn std::error::Error>>
    {
        if !dir.is_dir() {
            return Ok(());
        }
        
        callback(dir)?;
        
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_dir() {
                // Skip .git directory
                if path.file_name().map_or(false, |name| name == ".git") {
                    continue;
                }
                
                self.walk_directory(&path, &mut callback)?;
            } else {
                callback(&path)?;
            }
        }
        
        Ok(())
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let command = AddCommand::new(
        PathBuf::from("."), 
        vec![
            "src/**/*.rs".to_string(),        // All Rust files in src directory
            ":(attr:text)*.md".to_string(),   // All Markdown files with text attribute
            "!*_test.rs".to_string(),         // Exclude test files
        ],
        false, // Case sensitive
    );
    
    command.run()
}
```

### 2. Implementing `git checkout` Path Selection

#### Problem

Git's `checkout` command allows checking out specific files or directories from a commit or branch. Users can specify which paths to check out using pathspecs, and these need to be properly matched against the repository contents.

#### Solution

The gix-pathspec crate can be used to implement path selection for checkout operations:

```rust
use std::path::{Path, PathBuf};
use gix_pathspec::{parse, Defaults, Search, SearchMode};
use bstr::{BStr, ByteSlice};
use gix_attributes::search::Outcome;

struct CheckoutCommand {
    repo_path: PathBuf,
    pathspecs: Vec<String>,
    ref_name: String,
}

impl CheckoutCommand {
    fn new(repo_path: PathBuf, ref_name: String, pathspecs: Vec<String>) -> Self {
        Self {
            repo_path,
            ref_name,
            pathspecs,
        }
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Parse pathspecs
        let defaults = Defaults::default();
        let patterns = self.pathspecs.iter()
            .filter_map(|spec| parse(spec.as_bytes(), defaults).ok())
            .collect::<Vec<_>>();
        
        // Create a search from the patterns
        let mut search = Search::new(patterns);
        
        // In a real implementation, we would:
        // 1. Resolve the reference to a commit
        // 2. Get the tree for that commit
        // 3. Traverse the tree, filtering entries with our pathspecs
        
        // For this example, we'll just simulate finding files in the commit
        let commit_files = self.simulate_commit_files();
        let mut files_to_checkout = Vec::new();
        
        // Attribute handler (simplified)
        let mut attribute_handler = |_: &BStr, _, _, _: &mut Outcome| true;
        
        // Match files against pathspecs
        for file in &commit_files {
            let relative_path = file.strip_prefix(&self.repo_path)?;
            let path_str = relative_path.to_string_lossy();
            let path_bstr = path_str.as_bytes().as_bstr();
            
            let is_dir = file.is_dir();
            
            // If we have pathspecs, check for matches
            if search.patterns().count() > 0 {
                // Check if this file matches any pathspec
                if let Some(matched) = search.pattern_matching_relative_path(
                    path_bstr,
                    Some(is_dir),
                    &mut attribute_handler,
                ) {
                    if !matched.is_excluded() {
                        files_to_checkout.push(file.clone());
                    }
                }
            } else {
                // No pathspecs means checkout everything
                files_to_checkout.push(file.clone());
            }
        }
        
        // Process matched files (checkout from commit)
        println!("Checking out {} files from '{}'", files_to_checkout.len(), self.ref_name);
        for file in files_to_checkout {
            println!("  {}", file.display());
            // In a real implementation, we would check out the file here
        }
        
        Ok(())
    }
    
    // Simulate finding files in a commit (for example purposes)
    fn simulate_commit_files(&self) -> Vec<PathBuf> {
        vec![
            self.repo_path.join("src/main.rs"),
            self.repo_path.join("src/lib.rs"),
            self.repo_path.join("src/utils/mod.rs"),
            self.repo_path.join("README.md"),
            self.repo_path.join("Cargo.toml"),
        ]
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let command = CheckoutCommand::new(
        PathBuf::from("."),
        "feature-branch".to_string(),
        vec![
            "src/*.rs".to_string(),      // Rust files in src, but not subdirectories
            ":(glob,icase)*.md".to_string(), // Markdown files, case insensitive
        ],
    );
    
    command.run()
}
```

### 3. Implementing `git grep` with Path Filtering

#### Problem

Git's `grep` command searches for patterns in tracked files, with the ability to filter which files to search using pathspecs. This requires efficiently filtering files before performing expensive content searches.

#### Solution

The gix-pathspec crate enables implementing path filtering for grep operations with optimizations like common prefix detection:

```rust
use std::path::{Path, PathBuf};
use gix_pathspec::{parse, Defaults, Search, SearchMode};
use bstr::{BStr, ByteSlice};
use gix_attributes::search::Outcome;
use std::fs;
use std::io::{self, BufRead};
use regex::Regex;

struct GrepCommand {
    repo_path: PathBuf,
    pattern: String,
    pathspecs: Vec<String>,
}

impl GrepCommand {
    fn new(repo_path: PathBuf, pattern: String, pathspecs: Vec<String>) -> Self {
        Self {
            repo_path,
            pattern,
            pathspecs,
        }
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Compile the search pattern
        let regex = Regex::new(&self.pattern)?;
        
        // Parse pathspecs
        let defaults = Defaults::default();
        let patterns = self.pathspecs.iter()
            .filter_map(|spec| parse(spec.as_bytes(), defaults).ok())
            .collect::<Vec<_>>();
        
        // Create a search from the patterns
        let mut search = Search::new(patterns);
        
        // Get the common prefix directory if available
        // This is an optimization - we only need to scan directories that could contain matches
        let common_prefix = search.prefix_directory();
        let start_dir = if common_prefix.as_ref().as_os_str().is_empty() {
            self.repo_path.clone()
        } else {
            self.repo_path.join(common_prefix)
        };
        
        let files = self.find_tracked_files(&start_dir)?;
        let mut match_count = 0;
        
        // Attribute handler (simplified)
        let mut attribute_handler = |_: &BStr, _, _, _: &mut Outcome| true;
        
        // For each file, check if it matches the pathspecs
        for file in &files {
            let relative_path = file.strip_prefix(&self.repo_path)?;
            let path_str = relative_path.to_string_lossy();
            let path_bstr = path_str.as_bytes().as_bstr();
            
            // Skip directories, we only grep files
            if file.is_dir() {
                continue;
            }
            
            // Check if file matches pathspecs (or if no pathspecs were provided)
            let matches_pathspec = if search.patterns().count() > 0 {
                search.pattern_matching_relative_path(
                    path_bstr,
                    Some(false), // Not a directory
                    &mut attribute_handler,
                ).map_or(false, |matched| !matched.is_excluded())
            } else {
                true // No pathspecs means grep all files
            };
            
            if matches_pathspec {
                // Now search the file content
                match self.grep_file(&regex, file) {
                    Ok(line_matches) => {
                        if !line_matches.is_empty() {
                            println!("{}:", relative_path.display());
                            for (line_num, line) in line_matches {
                                println!("{}:{}", line_num, line);
                            }
                            match_count += line_matches.len();
                        }
                    }
                    Err(e) => println!("Error searching {}: {}", file.display(), e),
                }
            }
        }
        
        println!("\nFound {} matches", match_count);
        Ok(())
    }
    
    // Find all tracked files (in a real implementation, this would check the index)
    fn find_tracked_files(&self, start_dir: &Path) -> Result<Vec<PathBuf>, Box<dyn std::error::Error>> {
        let mut result = Vec::new();
        self.walk_directory(start_dir, |path| {
            // Skip .git directory
            if path.file_name().map_or(false, |name| name == ".git") {
                return Ok(());
            }
            
            // In a real implementation, we would check if the file is tracked
            // For this example, assume all files are tracked
            result.push(path.to_path_buf());
            Ok(())
        })?;
        Ok(result)
    }
    
    // Helper to recursively walk directories
    fn walk_directory<F>(&self, dir: &Path, mut callback: F) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnMut(&Path) -> Result<(), Box<dyn std::error::Error>>
    {
        if !dir.is_dir() {
            return Ok(());
        }
        
        callback(dir)?;
        
        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_dir() {
                self.walk_directory(&path, &mut callback)?;
            } else {
                callback(&path)?;
            }
        }
        
        Ok(())
    }
    
    // Search a file for the pattern
    fn grep_file(&self, regex: &Regex, file: &Path) -> io::Result<Vec<(usize, String)>> {
        let file = fs::File::open(file)?;
        let reader = io::BufReader::new(file);
        
        let mut matches = Vec::new();
        for (i, line) in reader.lines().enumerate() {
            let line = line?;
            if regex.is_match(&line) {
                matches.push((i + 1, line));
            }
        }
        
        Ok(matches)
    }
}

// Example usage (note: regex crate would need to be added as a dependency)
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let command = GrepCommand::new(
        PathBuf::from("."),
        r"fn\s+main".to_string(),  // Find main functions
        vec![
            "src/**/*.rs".to_string(),  // Only in Rust files
            "!**/test_*.rs".to_string(), // But not in test files
        ],
    );
    
    command.run()
}
```

### 4. Supporting Attribute-Based Path Filtering

#### Problem

Git supports filtering files based on their attributes (defined in `.gitattributes` files). This allows operations like checkout, add, or grep to filter files based on attributes like `binary`, `text`, or custom attributes.

#### Solution

The gix-pathspec crate integrates with the gix-attributes crate to support attribute-based filtering:

```rust
use std::path::{Path, PathBuf};
use gix_pathspec::{parse, Defaults, Search};
use gix_attributes::{Assignment, search::Outcome};
use bstr::{BStr, ByteSlice};

struct AttributeFilterCommand {
    repo_path: PathBuf,
    pathspec: String,
}

impl AttributeFilterCommand {
    fn new(repo_path: PathBuf, pathspec: String) -> Self {
        Self {
            repo_path,
            pathspec,
        }
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Parse the pathspec with attribute filtering
        let defaults = Defaults::default();
        let pattern = parse(self.pathspec.as_bytes(), defaults)?;
        
        // Check if the pathspec has attribute specifications
        if pattern.attributes.is_empty() {
            println!("No attributes specified in pathspec");
            return Ok(());
        }
        
        println!("Filtering files with the following attributes:");
        for attr in &pattern.attributes {
            println!("  {}", attr);
        }
        
        // Create a search with the pattern
        let mut search = Search::new(vec![pattern]);
        
        // List all files in the repository
        let files = self.list_repository_files()?;
        
        // Set up attribute lookup (in a real implementation, this would use gitattributes files)
        let attributes = self.load_attributes()?;
        
        // Create an attribute handler function
        let mut attribute_handler = |path: &BStr, _case, is_dir, outcome: &mut Outcome| {
            // In a real implementation, this would look up attributes from gitattributes files
            // For this example, we'll use our simplified attributes map
            let path_str = String::from_utf8_lossy(path).to_string();
            
            if let Some(attrs) = attributes.get(&path_str) {
                // Found attributes for this path
                for attr in attrs {
                    outcome.add(attr.clone());
                }
                true // We have attributes for this path
            } else {
                false // No attributes for this path
            }
        };
        
        // Match files against the pathspec
        let mut matching_files = Vec::new();
        
        for file in &files {
            let relative_path = file.strip_prefix(&self.repo_path)?;
            let path_str = relative_path.to_string_lossy();
            let path_bstr = path_str.as_bytes().as_bstr();
            
            let is_dir = file.is_dir();
            
            // Check if this file matches the pathspec including attributes
            if let Some(matched) = search.pattern_matching_relative_path(
                path_bstr,
                Some(is_dir),
                &mut attribute_handler,
            ) {
                if !matched.is_excluded() {
                    matching_files.push(file.clone());
                }
            }
        }
        
        // Display results
        println!("\nMatching files:");
        for file in matching_files {
            println!("  {}", file.strip_prefix(&self.repo_path)?.display());
        }
        
        Ok(())
    }
    
    // Helper to list all files in the repository
    fn list_repository_files(&self) -> Result<Vec<PathBuf>, Box<dyn std::error::Error>> {
        let mut result = Vec::new();
        self.walk_directory(&self.repo_path, |path| {
            // Skip .git directory
            if path.file_name().map_or(false, |name| name == ".git") {
                return Ok(());
            }
            
            result.push(path.to_path_buf());
            Ok(())
        })?;
        Ok(result)
    }
    
    // Helper to recursively walk directories
    fn walk_directory<F>(&self, dir: &Path, mut callback: F) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnMut(&Path) -> Result<(), Box<dyn std::error::Error>>
    {
        if !dir.is_dir() {
            return Ok(());
        }
        
        callback(dir)?;
        
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_dir() {
                self.walk_directory(&path, &mut callback)?;
            } else {
                callback(&path)?;
            }
        }
        
        Ok(())
    }
    
    // Simulate loading attributes from .gitattributes files
    fn load_attributes(&self) -> Result<std::collections::HashMap<String, Vec<Assignment>>, Box<dyn std::error::Error>> {
        use std::collections::HashMap;
        
        // In a real implementation, this would parse .gitattributes files
        // For this example, we'll hard-code some attributes
        let mut attributes = HashMap::new();
        
        // Add some example attributes
        attributes.insert(
            "src/main.rs".to_string(),
            vec![
                Assignment::from_name_and_value("text", Some("")).unwrap(),
                Assignment::from_name_and_value("eol", Some("lf")).unwrap(),
            ],
        );
        
        attributes.insert(
            "README.md".to_string(),
            vec![
                Assignment::from_name_and_value("text", Some("")).unwrap(),
                Assignment::from_name_and_value("documentation", Some("")).unwrap(),
            ],
        );
        
        attributes.insert(
            "images/logo.png".to_string(),
            vec![
                Assignment::from_name_and_value("binary", Some("")).unwrap(),
                Assignment::from_name_and_value("diff", None).unwrap(), // Unset attribute
            ],
        );
        
        Ok(attributes)
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let command = AttributeFilterCommand::new(
        PathBuf::from("."),
        ":(attr:text !binary)".to_string(), // Find text files that are not binary
    );
    
    command.run()
}
```

### 5. Implementing Efficient Directory Walking with Early Pruning

#### Problem

When performing operations on large repositories, traversing the entire directory structure can be expensive. Using pathspecs to prune the traversal early can significantly improve performance.

#### Solution

The gix-pathspec crate provides utilities like `common_prefix()`, `prefix_directory()`, and `can_match_relative_path()` to efficiently prune directory traversal:

```rust
use std::path::{Path, PathBuf};
use gix_pathspec::{parse, Defaults, Search};
use bstr::{BStr, ByteSlice};
use gix_attributes::search::Outcome;
use std::time::Instant;

struct EfficientWalker {
    repo_path: PathBuf,
    pathspecs: Vec<String>,
}

impl EfficientWalker {
    fn new(repo_path: PathBuf, pathspecs: Vec<String>) -> Self {
        Self {
            repo_path,
            pathspecs,
        }
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Parse pathspecs
        let defaults = Defaults::default();
        let patterns = self.pathspecs.iter()
            .filter_map(|spec| parse(spec.as_bytes(), defaults).ok())
            .collect::<Vec<_>>();
        
        // Create a search from the patterns
        let mut search = Search::new(patterns);
        
        // Get the common prefix directory
        let common_prefix = search.prefix_directory();
        println!("Common prefix directory: {:?}", common_prefix);
        
        // Start directory for traversal
        let start_dir = if common_prefix.as_ref().as_os_str().is_empty() {
            self.repo_path.clone()
        } else {
            self.repo_path.join(common_prefix)
        };
        
        // Count files with and without pruning
        let start_time = Instant::now();
        let (files_matched, dirs_pruned) = self.walk_with_pruning(&start_dir, &search)?;
        let duration = start_time.elapsed();
        
        // Now count all files without pruning for comparison
        let start_time_naive = Instant::now();
        let total_files = self.count_all_files(&self.repo_path)?;
        let duration_naive = start_time_naive.elapsed();
        
        // Print results
        println!("\nResults:");
        println!("  Total files in repository: {}", total_files);
        println!("  Files matched with pathspecs: {}", files_matched.len());
        println!("  Directories pruned during traversal: {}", dirs_pruned);
        println!("  With pruning: {:?} ({} files/sec)", duration, files_matched.len() as f64 / duration.as_secs_f64());
        println!("  Without pruning: {:?} ({} files/sec)", duration_naive, total_files as f64 / duration_naive.as_secs_f64());
        
        Ok(())
    }
    
    // Walk directory tree with pruning
    fn walk_with_pruning(&self, start_dir: &Path, search: &Search) -> Result<(Vec<PathBuf>, usize), Box<dyn std::error::Error>> {
        let mut matching_files = Vec::new();
        let mut dirs_pruned = 0;
        
        // Attribute handler (simplified)
        let mut attribute_handler = |_: &BStr, _, _, _: &mut Outcome| true;
        
        // Stack for depth-first traversal
        let mut stack = vec![start_dir.to_path_buf()];
        
        while let Some(dir) = stack.pop() {
            let relative_dir = dir.strip_prefix(&self.repo_path)?;
            let dir_str = relative_dir.to_string_lossy();
            let dir_bstr = dir_str.as_bytes().as_bstr();
            
            // Check if this directory could contain any matches
            let could_match = search.can_match_relative_path(dir_bstr, Some(true));
            
            if !could_match {
                dirs_pruned += 1;
                continue; // Prune this directory
            }
            
            // Process this directory
            for entry in std::fs::read_dir(&dir)? {
                let entry = entry?;
                let path = entry.path();
                
                if path.is_dir() {
                    // Skip .git directory
                    if path.file_name().map_or(false, |name| name == ".git") {
                        continue;
                    }
                    
                    // Add to stack for processing
                    stack.push(path);
                } else {
                    // Check if this file matches any pathspec
                    let relative_path = path.strip_prefix(&self.repo_path)?;
                    let path_str = relative_path.to_string_lossy();
                    let path_bstr = path_str.as_bytes().as_bstr();
                    
                    let matches = if search.patterns().count() > 0 {
                        search.pattern_matching_relative_path(
                            path_bstr,
                            Some(false), // Not a directory
                            &mut attribute_handler,
                        ).map_or(false, |matched| !matched.is_excluded())
                    } else {
                        true // No pathspecs means match everything
                    };
                    
                    if matches {
                        matching_files.push(path);
                    }
                }
            }
        }
        
        Ok((matching_files, dirs_pruned))
    }
    
    // Count all files without pruning
    fn count_all_files(&self, start_dir: &Path) -> Result<usize, Box<dyn std::error::Error>> {
        let mut count = 0;
        
        // Stack for depth-first traversal
        let mut stack = vec![start_dir.to_path_buf()];
        
        while let Some(dir) = stack.pop() {
            for entry in std::fs::read_dir(&dir)? {
                let entry = entry?;
                let path = entry.path();
                
                if path.is_dir() {
                    // Skip .git directory
                    if path.file_name().map_or(false, |name| name == ".git") {
                        continue;
                    }
                    
                    // Add to stack for processing
                    stack.push(path);
                } else {
                    count += 1;
                }
            }
        }
        
        Ok(count)
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let command = EfficientWalker::new(
        PathBuf::from("."),
        vec![
            "src/module1/**/*.rs".to_string(),  // All Rust files in src/module1
            "src/module2/**/*.rs".to_string(),  // All Rust files in src/module2
            "!**/test_*.rs".to_string(),        // But not test files
        ],
    );
    
    command.run()
}
```

## Integration with Other Components

The gix-pathspec crate is integrated with several other components in the gitoxide ecosystem:

### Integration with gix-status

The gix-status crate uses gix-pathspec to filter which files to include in the status output:

```rust
use std::path::{Path, PathBuf};
use gix_pathspec::{parse, Defaults, Search};
use bstr::{BStr, ByteSlice};
use gix_attributes::search::Outcome;

// A simplified version of how gix-status might use pathspecs
struct StatusCommand {
    repo_path: PathBuf,
    pathspecs: Vec<String>,
}

impl StatusCommand {
    fn new(repo_path: PathBuf, pathspecs: Vec<String>) -> Self {
        Self {
            repo_path,
            pathspecs,
        }
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Parse pathspecs
        let defaults = Defaults::default();
        let patterns = self.pathspecs.iter()
            .filter_map(|spec| parse(spec.as_bytes(), defaults).ok())
            .collect::<Vec<_>>();
        
        // Create a search from the patterns
        let mut search = Search::new(patterns);
        
        // Find modified files (in a real implementation, this would compare index and working tree)
        let modified_files = self.find_modified_files()?;
        
        // Find untracked files (in a real implementation, this would check the index)
        let untracked_files = self.find_untracked_files()?;
        
        // Attribute handler (simplified)
        let mut attribute_handler = |_: &BStr, _, _, _: &mut Outcome| true;
        
        // Filter modified files by pathspecs
        let filtered_modified = if search.patterns().count() > 0 {
            modified_files.iter()
                .filter(|file| {
                    let relative_path = file.strip_prefix(&self.repo_path).unwrap();
                    let path_str = relative_path.to_string_lossy();
                    let path_bstr = path_str.as_bytes().as_bstr();
                    
                    search.pattern_matching_relative_path(
                        path_bstr,
                        Some(file.is_dir()),
                        &mut attribute_handler,
                    ).map_or(false, |matched| !matched.is_excluded())
                })
                .cloned()
                .collect::<Vec<_>>()
        } else {
            modified_files
        };
        
        // Filter untracked files by pathspecs
        let filtered_untracked = if search.patterns().count() > 0 {
            untracked_files.iter()
                .filter(|file| {
                    let relative_path = file.strip_prefix(&self.repo_path).unwrap();
                    let path_str = relative_path.to_string_lossy();
                    let path_bstr = path_str.as_bytes().as_bstr();
                    
                    search.pattern_matching_relative_path(
                        path_bstr,
                        Some(file.is_dir()),
                        &mut attribute_handler,
                    ).map_or(false, |matched| !matched.is_excluded())
                })
                .cloned()
                .collect::<Vec<_>>()
        } else {
            untracked_files
        };
        
        // Display status
        println!("Changes not staged for commit:");
        for file in filtered_modified {
            println!("  modified: {}", file.strip_prefix(&self.repo_path)?.display());
        }
        
        println!("\nUntracked files:");
        for file in filtered_untracked {
            println!("  {}", file.strip_prefix(&self.repo_path)?.display());
        }
        
        Ok(())
    }
    
    // Simulate finding modified files (in a real implementation, this would compare index and working tree)
    fn find_modified_files(&self) -> Result<Vec<PathBuf>, Box<dyn std::error::Error>> {
        Ok(vec![
            self.repo_path.join("src/main.rs"),
            self.repo_path.join("src/lib.rs"),
            self.repo_path.join("Cargo.toml"),
        ])
    }
    
    // Simulate finding untracked files (in a real implementation, this would check the index)
    fn find_untracked_files(&self) -> Result<Vec<PathBuf>, Box<dyn std::error::Error>> {
        Ok(vec![
            self.repo_path.join("new_file.txt"),
            self.repo_path.join("src/new_module.rs"),
            self.repo_path.join("docs/notes.md"),
        ])
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let command = StatusCommand::new(
        PathBuf::from("."),
        vec![
            "src/**/*.rs".to_string(),  // Only show Rust files in src directory
        ],
    );
    
    command.run()
}
```

### Integration with gix-index

The gix-index crate uses gix-pathspec to implement path filtering for index operations:

```rust
use std::path::{Path, PathBuf};
use gix_pathspec::{parse, Defaults, Search};
use bstr::{BStr, ByteSlice};
use gix_attributes::search::Outcome;

// A simplified example of how gix-index might use pathspecs
struct UpdateIndexCommand {
    repo_path: PathBuf,
    pathspecs: Vec<String>,
    add: bool,
    remove: bool,
}

impl UpdateIndexCommand {
    fn new(repo_path: PathBuf, pathspecs: Vec<String>, add: bool, remove: bool) -> Self {
        Self {
            repo_path,
            pathspecs,
            add,
            remove,
        }
    }
    
    fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Parse pathspecs
        let defaults = Defaults::default();
        let patterns = self.pathspecs.iter()
            .filter_map(|spec| parse(spec.as_bytes(), defaults).ok())
            .collect::<Vec<_>>();
        
        // Create a search from the patterns
        let mut search = Search::new(patterns);
        
        // Find all files in the repository
        let files = self.list_repository_files()?;
        
        // Attribute handler (simplified)
        let mut attribute_handler = |_: &BStr, _, _, _: &mut Outcome| true;
        
        // Filter files by pathspecs
        let filtered_files = if search.patterns().count() > 0 {
            files.iter()
                .filter(|file| {
                    let relative_path = file.strip_prefix(&self.repo_path).unwrap();
                    let path_str = relative_path.to_string_lossy();
                    let path_bstr = path_str.as_bytes().as_bstr();
                    
                    search.pattern_matching_relative_path(
                        path_bstr,
                        Some(file.is_dir()),
                        &mut attribute_handler,
                    ).map_or(false, |matched| !matched.is_excluded())
                })
                .cloned()
                .collect::<Vec<_>>()
        } else {
            files
        };
        
        // Process files based on command flags
        if self.add {
            println!("Adding files to index:");
            for file in &filtered_files {
                if !file.is_dir() {
                    println!("  {}", file.strip_prefix(&self.repo_path)?.display());
                    // In a real implementation, would add the file to the index here
                }
            }
        }
        
        if self.remove {
            println!("\nRemoving files from index:");
            for file in &filtered_files {
                if !file.is_dir() {
                    println!("  {}", file.strip_prefix(&self.repo_path)?.display());
                    // In a real implementation, would remove the file from the index here
                }
            }
        }
        
        Ok(())
    }
    
    // Helper to list all files in the repository
    fn list_repository_files(&self) -> Result<Vec<PathBuf>, Box<dyn std::error::Error>> {
        let mut result = Vec::new();
        self.walk_directory(&self.repo_path, |path| {
            // Skip .git directory
            if path.file_name().map_or(false, |name| name == ".git") {
                return Ok(());
            }
            
            result.push(path.to_path_buf());
            Ok(())
        })?;
        Ok(result)
    }
    
    // Helper to recursively walk directories
    fn walk_directory<F>(&self, dir: &Path, mut callback: F) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnMut(&Path) -> Result<(), Box<dyn std::error::Error>>
    {
        if !dir.is_dir() {
            return Ok(());
        }
        
        callback(dir)?;
        
        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_dir() {
                self.walk_directory(&path, &mut callback)?;
            } else {
                callback(&path)?;
            }
        }
        
        Ok(())
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let command = UpdateIndexCommand::new(
        PathBuf::from("."),
        vec![
            "src/**/*.rs".to_string(),  // Only Rust files in src directory
            "!**/test_*.rs".to_string(), // But not test files
        ],
        true,  // Add files
        false, // Don't remove files
    );
    
    command.run()
}
```

## Conclusion

The gix-pathspec crate provides essential functionality for implementing Git's powerful path filtering system. Its integration with other gitoxide components creates a cohesive system that accurately implements Git's behavior.

The key strengths of the crate are:

1. **Complete Implementation**: Supports all features of Git's pathspec syntax, including magic signatures and attribute specifications
2. **Performance Optimizations**: Common prefix detection and early path pruning for efficient directory traversal
3. **Flexible Matching**: Support for different search modes and case sensitivity options
4. **Integration**: Seamless integration with other gitoxide components like gix-attributes

These capabilities make gix-pathspec suitable for implementing a wide range of Git operations that involve path filtering, from basic commands like `add` and `checkout` to more complex features like `grep` with attribute filtering.