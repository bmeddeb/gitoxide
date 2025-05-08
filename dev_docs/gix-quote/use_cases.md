# gix-quote Use Cases

This document describes typical use cases for the `gix-quote` crate, which provides functionality for quoting and unquoting strings with different quoting styles.

## Intended Audience

- Developers working with Git command-line operations
- Implementers of Git clients or tools that need to parse Git configuration
- Developers handling Git path operations with special characters
- Anyone working with shell commands and needing to escape arguments safely

## Use Case 1: Safely Passing Arguments to Shell Commands

### Problem

When executing Git commands via shell, arguments containing special characters (spaces, quotes, exclamation marks) can cause command injection issues or incorrect behavior.

### Solution

Use the `single()` function to properly quote arguments for shell execution.

```rust
use bstr::ByteSlice;
use gix_quote::single;

fn prepare_safe_git_command(path: &str) -> String {
    // Convert the path to a byte string and apply single quoting
    let quoted_path = single(path.as_bytes().as_bstr());
    
    // Format the complete command with the safely quoted path
    format!("git add {}", quoted_path.to_str().unwrap())
}

// Example usage
fn main() {
    // Path with spaces and special characters
    let path = "my docs/file with 'quotes' and !marks.txt";
    
    // Get a safe command string to execute
    let safe_command = prepare_safe_git_command(path);
    println!("{}", safe_command);
    // Output: git add 'my docs/file with '\''quotes'\'' and '\!'marks.txt'
    
    // The command can now be safely passed to a shell executor
}
```

## Use Case 2: Parsing Git Config Files with Quoted Values

### Problem

Git configuration files may contain quoted strings using ANSI C style quoting (with escape sequences) that need to be properly interpreted.

### Solution

Use the `ansi_c::undo()` function to parse and interpret quoted configuration values.

```rust
use bstr::ByteSlice;
use gix_quote::ansi_c;
use std::borrow::Cow;

fn parse_git_config_value(raw_value: &str) -> Result<String, Box<dyn std::error::Error>> {
    // Convert the raw value to a byte string
    let raw_bytes = raw_value.as_bytes().as_bstr();
    
    // Use the ansi_c::undo function to unquote the value
    let (unquoted, _) = ansi_c::undo(raw_bytes)?;
    
    // Convert the result back to a String
    match unquoted {
        Cow::Borrowed(bytes) => Ok(bytes.to_str()?.to_string()),
        Cow::Owned(bytes) => Ok(bytes.to_str()?.to_string()),
    }
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Example quoted values from a Git config file
    let config_values = [
        r#""~/path/to/repo""#,
        r#""line1\nline2""#,
        r#""special chars: \"\\\t\r""#,
    ];
    
    for value in &config_values {
        let parsed = parse_git_config_value(value)?;
        println!("Raw: {}\nParsed: {}\n", value, parsed);
    }
    
    // Output:
    // Raw: "~/path/to/repo"
    // Parsed: ~/path/to/repo
    //
    // Raw: "line1\nline2"
    // Parsed: line1
    // line2
    //
    // Raw: "special chars: \"\\\t\r"
    // Parsed: special chars: "\\	<carriage return>
    
    Ok(())
}
```

## Use Case 3: Processing Output from Git Commands with Escape Sequences

### Problem

Git commands sometimes produce output with escape sequences that need to be properly interpreted, especially when dealing with paths containing special characters.

### Solution

Use `ansi_c::undo()` to process the escaped output from Git commands.

```rust
use bstr::ByteSlice;
use gix_quote::ansi_c;

fn process_git_ls_files_output(output_line: &str) -> Result<String, Box<dyn std::error::Error>> {
    // Git sometimes outputs paths with octal escape sequences for special chars
    // Convert the output to a byte string
    let bytes = output_line.as_bytes().as_bstr();
    
    // Unquote the string using ANSI C style unquoting
    let (unquoted, _) = ansi_c::undo(bytes)?;
    
    // Convert to a regular String
    Ok(unquoted.to_str()?.to_string())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Example output from a git command that includes escape sequences
    // For example, what you might get from `git ls-files --stage`
    let git_output_lines = [
        r#""src/main.rs""#,
        r#""path/with/\346\277\261\351\207\216/japanese.txt""#,  // Path with Japanese characters
        r#""file\ with\ spaces.txt""#,
    ];
    
    for line in &git_output_lines {
        let processed = process_git_ls_files_output(line)?;
        println!("Original: {}\nProcessed: {}\n", line, processed);
    }
    
    // Output:
    // Original: "src/main.rs"
    // Processed: src/main.rs
    //
    // Original: "path/with/\346\277\261\351\207\216/japanese.txt"
    // Processed: path/with/濱野/japanese.txt
    //
    // Original: "file\ with\ spaces.txt"
    // Processed: file with spaces.txt
    
    Ok(())
}
```

## Use Case 4: Building Command Arguments with Special Characters

### Problem

When programmatically constructing Git commands, arguments may need to be properly quoted to handle special characters.

### Solution

Use the `single()` function to safely quote command arguments.

```rust
use bstr::ByteSlice;
use gix_quote::single;
use std::process::Command;

fn add_file_to_git(repo_path: &str, file_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    // Quote both the repository path and file path
    let quoted_repo = single(repo_path.as_bytes().as_bstr()).to_str()?.to_string();
    let quoted_file = single(file_path.as_bytes().as_bstr()).to_str()?.to_string();
    
    // Build a command with the properly quoted arguments
    // In real code, you would construct the Command directly rather than building a shell command string
    println!("Command to execute: git -C {} add {}", quoted_repo, quoted_file);
    
    // This simulates executing the command safely
    // Command::new("git")
    //     .arg("-C")
    //     .arg(repo_path)  // Command::arg handles escaping internally
    //     .arg("add")
    //     .arg(file_path)  // So we don't need single() when using Command directly
    //     .status()?;
    
    Ok(())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let repo_path = "/path/to/repo with spaces";
    let file_path = "document with 'quotes' and !exclamation.txt";
    
    add_file_to_git(repo_path, file_path)?;
    // Output: Command to execute: git -C '/path/to/repo with spaces' add 'document with '\''quotes'\'' and '\!'exclamation.txt'
    
    Ok(())
}
```

## Advanced Use Case: Combining Quote Styles for Complex Processing

### Problem

Sometimes Git operations involve processing data that uses multiple quoting styles in sequence, such as parsing output from complex commands or preparing nested commands.

### Solution

Combine the quoting and unquoting functions to handle complex cases.

```rust
use bstr::{BString, ByteSlice, ByteVec};
use gix_quote::{ansi_c, single};
use std::borrow::Cow;

fn process_complex_git_output(output: &str) -> Result<String, Box<dyn std::error::Error>> {
    // First, handle ANSI C style quoting in the output
    let bytes = output.as_bytes().as_bstr();
    let (unquoted_ansi, _) = ansi_c::undo(bytes)?;
    
    // The result might still contain characters that need shell quoting
    // for further processing or display
    let shell_safe = match unquoted_ansi {
        Cow::Borrowed(b) => single(b),
        Cow::Owned(b) => single(b.as_bstr()),
    };
    
    Ok(shell_safe.to_str()?.to_string())
}

// Example usage
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Complex output with nested quoting
    let complex_output = r#""file with \"quotes\" and \n newlines""#;
    
    let processed = process_complex_git_output(complex_output)?;
    println!("Original: {}\nProcessed: {}", complex_output, processed);
    // Output:
    // Original: "file with \"quotes\" and \n newlines"
    // Processed: 'file with "quotes" and 
    // newlines'
    
    Ok(())
}
```

These use cases demonstrate how the `gix-quote` crate can be used to handle various string quoting scenarios in Git operations, ensuring proper handling of special characters and preventing command injection issues when interacting with shells or parsing Git-formatted output.