# gix-command Use Cases

This document outlines common use cases for the `gix-command` crate, showing how it can be used to safely and efficiently execute Git commands and external processes within the Gitoxide ecosystem.

## Intended Audience

- **Gitoxide Core Developers**: Building functionality that needs to execute external Git commands or plugins
- **Git Plugin Authors**: Implementing custom Git commands that need to spawn other Git commands
- **Git Tooling Developers**: Creating tools that interact with Git processes

## Use Case: Executing Git Hooks

### Problem

Git hooks are executable scripts or programs that need to be run with specific environment variables and working directory settings. They may be shell scripts or binary executables, and their output needs to be captured and handled appropriately.

### Solution

```rust
use std::path::Path;
use gix_command::{prepare, Context};

fn execute_pre_commit_hook(git_dir: &Path, worktree_dir: &Path) -> std::io::Result<bool> {
    let hook_path = git_dir.join("hooks").join("pre-commit");
    
    // Skip if hook doesn't exist or isn't executable
    if !hook_path.exists() {
        return Ok(true);
    }
    
    // Prepare context with repository information
    let context = Context {
        git_dir: Some(git_dir.to_path_buf()),
        worktree_dir: Some(worktree_dir.to_path_buf()),
        ..Default::default()
    };
    
    // Execute the hook with proper detection of script type
    let output = prepare(&hook_path)
        .with_context(context)
        .command_may_be_shell_script()
        .spawn()?
        .wait()?;
    
    // Hook success is indicated by exit code 0
    Ok(output.success())
}
```

This approach handles:
- Shell scripts with or without shebangs
- Binary executables
- Proper working directory and Git environment variables
- Windows/Unix path differences

## Use Case: Invoking Git Credential Helpers

### Problem

Git credential helpers can be external executables, shell scripts, or built-in commands. They need to receive data on stdin and produce output on stdout with specific formatting.

### Solution

```rust
use std::io::Write;
use std::process::{Command, Stdio};
use gix_command::{prepare, Context};

fn invoke_credential_helper(
    helper: &str,
    operation: &str, 
    url: &str
) -> std::io::Result<String> {
    // Start with "git-credential-" prefix as Git does
    let helper_cmd = if !helper.starts_with("git-credential-") {
        format!("git-credential-{}", helper)
    } else {
        helper.to_string()
    };
    
    // Set up the command with proper IO configuration
    let mut child = prepare(helper_cmd)
        .arg(operation)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .command_may_be_shell_script()
        .spawn()?;
    
    // Write URL data to stdin
    if let Some(mut stdin) = child.stdin.take() {
        writeln!(stdin, "url={}", url)?;
        // Flush and drop stdin to signal EOF
        stdin.flush()?;
    }
    
    // Read and return output
    let output = child.wait_with_output()?;
    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}
```

## Use Case: Executing Git Commands in a Repository

### Problem

Many Git operations need to be run within the context of a specific repository, with proper environment variables set and outputs captured.

### Solution

```rust
use std::path::Path;
use gix_command::{prepare, Context};

fn run_git_command(
    repo_path: &Path,
    args: &[&str]
) -> std::io::Result<Vec<u8>> {
    // Extract git directory and worktree paths
    let git_dir = repo_path.join(".git");
    let worktree_dir = repo_path.to_path_buf();
    
    // Set up Git context
    let context = Context {
        git_dir: Some(git_dir),
        worktree_dir: Some(worktree_dir),
        // Disable reference replacement for consistency
        no_replace_objects: Some(true),
        // Use case-sensitive path matching
        icase_pathspecs: Some(false),
        ..Default::default()
    };
    
    // Execute command with context
    let output = prepare("git")
        .args(args)
        .with_context(context)
        .spawn()?
        .wait_with_output()?;
    
    if output.status.success() {
        Ok(output.stdout)
    } else {
        Err(std::io::Error::new(
            std::io::ErrorKind::Other, 
            format!("Git command failed: {}", 
                String::from_utf8_lossy(&output.stderr))
        ))
    }
}
```

## Use Case: Running External Diff Tools

### Problem

Git can be configured to use external diff tools that may have complex command-line requirements, including shell-specific features like redirection or piping.

### Solution

```rust
use std::path::Path;
use gix_command::{prepare, Context};

fn run_external_diff(
    repo_path: &Path,
    old_file: &Path,
    new_file: &Path,
    diff_command: &str
) -> std::io::Result<()> {
    // Replace placeholders in diff command
    let command = diff_command
        .replace("%oldfile", old_file.to_str().unwrap())
        .replace("%newfile", new_file.to_str().unwrap());
    
    // Set up Git context
    let context = Context {
        git_dir: Some(repo_path.join(".git")),
        worktree_dir: Some(repo_path.to_path_buf()),
        ..Default::default()
    };
    
    // Run command, forcing shell mode since it likely contains redirection
    let status = prepare(command)
        .with_context(context)
        .with_shell()  // Force shell usage for complex commands
        .spawn()?
        .wait()?;
    
    if status.success() {
        Ok(())
    } else {
        Err(std::io::Error::new(
            std::io::ErrorKind::Other,
            format!("Diff command failed with status: {}", status)
        ))
    }
}
```

## Use Case: Safely Running User-Provided Commands

### Problem

Git often needs to run commands provided by the user in configuration files, which requires careful handling to prevent shell injection vulnerabilities.

### Solution

```rust
use gix_command::prepare;

fn run_user_command(command: &str, args: &[&str]) -> std::io::Result<bool> {
    // First try to run without shell to prevent injection attacks
    let direct_result = prepare(command)
        .args(args)
        .spawn();
    
    match direct_result {
        Ok(mut child) => {
            // Command executed directly without shell
            let status = child.wait()?;
            Ok(status.success())
        },
        Err(_) => {
            // If direct execution fails, try with shell but sanitize
            // Check if this is actually a shell script
            let cmd = prepare(command)
                .args(args)
                // Only use shell if necessary
                .command_may_be_shell_script()
                // Quote the command to prevent injection when reasonable
                .with_quoted_command()
                .spawn()?
                .wait()?;
            
            Ok(cmd.success())
        }
    }
}
```

## Use Case: Cross-Platform Script Execution

### Problem

Git needs to handle script execution consistently across different platforms, especially Windows vs. Unix systems, which have different mechanisms for executing scripts.

### Solution

```rust
use std::path::Path;
use gix_command::{prepare, extract_interpreter};

fn execute_script(
    script_path: &Path, 
    args: &[&str]
) -> std::io::Result<()> {
    // Check if the file has a shebang
    if let Some(shebang) = extract_interpreter(script_path) {
        // If it has a shebang, use the specified interpreter
        let mut cmd = prepare(shebang.interpreter);
        // Add interpreter args
        cmd = cmd.args(&shebang.args);
        // Add script path and user args
        cmd = cmd.arg(script_path).args(args);
        cmd.spawn()?.wait().map(|_| ())
    } else {
        // No shebang, try to execute directly with potential shell handling
        prepare(script_path)
            .args(args)
            .command_may_be_shell_script()
            .spawn()?
            .wait()
            .map(|_| ())
    }
}
```

## Use Case: Performance-Optimized Command Execution

### Problem

Git operations may involve many process spawns, which can be slow, especially on Windows. Optimizing this process can significantly improve performance.

### Solution

```rust
use gix_command::prepare;

fn optimize_command_execution(command: &str, args: &[&str]) -> std::io::Result<Vec<u8>> {
    // Use manual argument splitting on Windows for better performance
    let output = prepare(command)
        .args(args)
        .command_may_be_shell_script_allow_manual_argument_splitting()
        .spawn()?
        .wait_with_output()?;
    
    if output.status.success() {
        Ok(output.stdout)
    } else {
        Err(std::io::Error::new(
            std::io::ErrorKind::Other,
            String::from_utf8_lossy(&output.stderr).to_string()
        ))
    }
}
```

## Use Case: Git LFS Filter Process

### Problem

Git LFS requires running long-lived filter processes with specific environment variables and handling their stdin/stdout interactively.

### Solution

```rust
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Stdio};
use gix_command::{prepare, Context};

fn start_lfs_filter_process(
    git_dir: &Path,
    worktree_dir: &Path
) -> std::io::Result<Child> {
    let context = Context {
        git_dir: Some(git_dir.to_path_buf()),
        worktree_dir: Some(worktree_dir.to_path_buf()),
        ..Default::default()
    };
    
    // Start the LFS process
    prepare("git-lfs")
        .arg("filter-process")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .with_context(context)
        .spawn()
}

fn process_lfs_command(child: &mut Child, command: &str) -> std::io::Result<String> {
    let stdin = child.stdin.as_mut()
        .ok_or_else(|| std::io::Error::new(
            std::io::ErrorKind::BrokenPipe, 
            "Failed to open stdin"))?;
    
    // Write command to the filter process
    writeln!(stdin, "{}", command)?;
    stdin.flush()?;
    
    // Read response
    let stdout = child.stdout.as_mut()
        .ok_or_else(|| std::io::Error::new(
            std::io::ErrorKind::BrokenPipe, 
            "Failed to capture stdout"))?;
    
    let mut reader = BufReader::new(stdout);
    let mut response = String::new();
    reader.read_line(&mut response)?;
    
    Ok(response)
}
```

These use cases demonstrate the flexibility and power of the `gix-command` crate in handling various Git-related command execution scenarios, from simple Git commands to complex shell scripts, always with proper handling of context, security, and platform differences.