# gix-command

## Overview

The `gix-command` crate provides a Git-specific command execution interface similar to Rust's standard `Command` API but with enhanced capabilities tailored for Git operations. It handles shell script execution, cross-platform compatibility, environment variable management, and other Git-specific concerns when invoking external processes.

## Architecture

The crate is designed around a builder pattern that configures command execution with Git-specific context. It focuses on these key areas:

1. **Command Configuration**: Flexible preparation of commands with appropriate arguments and environment.
2. **Shell Handling**: Smart detection and handling of shell scripts with proper quoting and argument passing.
3. **Platform Compatibility**: Cross-platform handling of command execution with special Windows-specific logic.
4. **Git Context**: Passing proper Git environment variables to subprocesses.
5. **Shebang Handling**: Parsing and execution of scripts with shebang directives.

The primary workflow involves creating a `Prepare` instance with `prepare()`, configuring it through the builder API, and finally spawning the command with `spawn()`.

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Prepare` | Main configuration structure used for preparing command execution. | Used to configure and spawn commands with Git-specific settings. |
| `Context` | Holds additional Git-specific contextual information for spawned processes. | Provides Git repository context like directory paths and environment variables. |
| `shebang::Data` | Contains parsed shebang information from script files. | Stores interpreter path and arguments extracted from shebang lines. |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `prepare` | Creates a new `Prepare` instance for a command. | `fn prepare(cmd: impl Into<OsString>) -> Prepare` |
| `extract_interpreter` | Parses shebang information from an executable file. | `fn extract_interpreter(executable: &Path) -> Option<shebang::Data>` |
| `win_path_lookup` | Windows-specific helper to find executables in PATH. | `fn win_path_lookup(command: &Path, path_value: &std::ffi::OsStr) -> Option<PathBuf>` |
| `shebang::parse` | Parses shebang information from a buffer. | `fn parse(buf: &BStr) -> Option<Data>` |

### Implementations for Structs

#### Prepare Builder Methods

| Method | Description |
|--------|-------------|
| `command_may_be_shell_script` | Enables shell usage if the command contains shell-specific characters. |
| `with_shell` | Forces the use of a shell for command execution. |
| `with_quoted_command` | Quotes the command when run in a shell to preserve the path. |
| `with_shell_program` | Specifies a custom shell program to use. |
| `without_shell` | Disables shell usage. |
| `with_context` | Sets Git-specific context information. |
| `command_may_be_shell_script_allow_manual_argument_splitting` | Enables manual argument splitting for performance when safe. |
| `command_may_be_shell_script_disallow_manual_argument_splitting` | Prevents manual argument splitting. |
| `stdin`, `stdout`, `stderr` | Configure standard IO streams. |
| `arg`, `args` | Add arguments to the command. |
| `env` | Add environment variables to the command. |
| `spawn` | Execute the command and return a handle to the spawned process. |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-trace` | Used for logging command execution for debugging. |
| `gix-path` | Used for path manipulation and conversions. |
| `gix-quote` | Used for shell-safe quoting of command arguments. |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `bstr` | Used for binary string handling to support non-UTF8 paths and arguments. |
| `shell-words` | Used for splitting shell commands into arguments. |

## Feature Flags

The crate doesn't declare any feature flags of its own, relying on features from its dependencies.

## Examples

### Basic Command Execution

```rust
// Execute a simple command
let status = gix_command::prepare("git")
    .arg("status")
    .spawn()?
    .wait()?;
```

### Using Git-specific Context

```rust
// Execute a Git command with repository context
let repo_path = "/path/to/repo/.git";
let context = gix_command::Context {
    git_dir: Some(repo_path.into()),
    ..Default::default()
};

let output = gix_command::prepare("git")
    .arg("rev-parse")
    .arg("HEAD")
    .with_context(context)
    .spawn()?
    .wait_with_output()?;
```

### Handling Shell Scripts

```rust
// Execute a command that may contain shell-specific syntax
let output = gix_command::prepare("grep -r 'TODO' --include='*.rs'")
    .command_may_be_shell_script()
    .spawn()?
    .wait_with_output()?;
```

## Implementation Details

### Command Execution Strategy

The `gix-command` crate implements a sophisticated strategy for executing commands that closely mirrors Git's own approach. Key implementation details include:

1. **Shell Script Detection**: The crate automatically detects if a command contains shell metacharacters like `|`, `&`, `;`, `<`, `>`, `(`, `)`, `$`, etc. If found, it executes the command through a shell.

2. **Argument Passing**: When executing commands through a shell, arguments are passed as `"$@"` positional parameters, which ensures proper handling of spaces and special characters.

3. **Manual Argument Splitting**: On Windows, the crate attempts to manually split arguments (using `shell-words`) to avoid shell overhead when possible, which can improve performance significantly.

4. **Shebang Handling**: For script files with shebangs, the crate extracts the interpreter and arguments from the first line and invokes the script accordingly.

5. **Windows Path Lookup**: On Windows, the crate implements a custom PATH lookup algorithm similar to Git's, with special handling for `.exe` extensions.

6. **Git Environment Variables**: The crate manages Git-specific environment variables like `GIT_DIR`, `GIT_WORK_TREE`, `GIT_NAMESPACE`, etc.

### Platform-Specific Considerations

The implementation handles platform differences carefully:

1. **Windows Specifics**:
   - Prevents terminal windows from popping up during command execution
   - Special handling for `.exe` extensions
   - Custom PATH lookup algorithm
   - Default to allowing manual argument splitting for performance

2. **Unix Specifics**:
   - Better handling of script files with shebangs
   - Support for shell builtins
   - Default to using the shell when shell metacharacters are detected

### Security Considerations

The crate implements several security measures:

1. **Shebang Safety**: When executing scripts with shebangs, interpreter options are only preserved if the script is located in a trusted path (i.e., found in PATH rather than a relative path).

2. **Path Sanitization**: The crate is careful about how it handles paths, especially on Windows, to prevent path traversal vulnerabilities.

3. **Shell Escaping**: Proper quoting and escaping is applied to arguments to prevent shell injection attacks.

## Testing Strategy

The `gix-command` crate is tested extensively through unit tests that verify:

1. **Command Preparation**: Tests for the builder pattern and configuration options.
2. **Shell Handling**: Tests for correctly detecting and handling shell scripts.
3. **Argument Passing**: Tests for properly passing and escaping arguments.
4. **Environment Variables**: Tests for setting and inheriting environment variables.
5. **Shebang Parsing**: Tests for extracting interpreter information from scripts.
6. **Windows PATH Lookup**: Tests for finding executables in the PATH on Windows.
7. **Cross-Platform Execution**: Tests that run on both Unix and Windows systems.

The test suite includes both unit tests for individual components and integration tests that execute real commands to verify actual behavior.