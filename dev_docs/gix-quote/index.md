# gix-quote

A crate in the gitoxide project that provides functionality for quoting and unquoting strings with different quoting styles commonly used in Git operations.

## Overview

The `gix-quote` crate implements string quoting and unquoting functionality with support for different quoting styles:

1. **Single Quotes**: Transforms strings to be suitable for use as Bourne shell arguments by wrapping them in single quotes and escaping special characters.
2. **ANSI C Style Quotes**: Unquotes strings formatted according to ANSI C quoting conventions, handling escape sequences like `\n`, `\t`, etc.

These quoting mechanisms are essential for safely handling file paths, command arguments, and configuration values within Git operations, especially when dealing with special characters or whitespace.

## Architecture & Components

The crate has a simple architecture with two main modules:

1. **single**: Provides functionality for single-quote style quoting.
   - `single()` function: Transforms a string to be safe for use as a Bourne shell argument.

2. **ansi_c**: Provides functionality for handling ANSI C style quoted strings.
   - `undo()` function: Unquotes an ANSI C style quoted string, handling various escape sequences.
   - `undo::Error` type: Error handling for ANSI C unquoting operations.

## Dependencies

- **bstr**: Used for byte string operations, providing efficient handling of non-UTF8 strings.
- **thiserror**: Used for error handling and definition.
- **gix-utils**: A dependency from within the gitoxide project, specifically using its `btoi` module for byte-to-integer conversion.

## Implementation Details

### Single Quoting

The `single()` function:
- Encloses the input string in single quotes (`'`)
- Escapes any embedded single quotes (`'`) as `'\''`
- Escapes exclamation marks (`!`) as `'\!'`

This ensures strings are properly quoted for shell operations, mitigating potential command injection issues.

### ANSI C Style Unquoting

The `undo()` function in the `ansi_c` module:
- Processes strings enclosed in double quotes (`"`)
- Handles common escape sequences like `\n`, `\r`, `\t`
- Supports octal numeric escape sequences (e.g., `\346\277\261`)
- Returns the unquoted string along with the number of consumed bytes from the input

This allows parsing of complex quoted strings while preserving their intended meaning and special characters.

## Error Handling

The `ansi_c::undo` module defines an `Error` enum with two variants:
- `InvalidInput`: For general parsing errors, providing a message and the problematic input.
- `UnsupportedEscapeByte`: For unsupported escape sequences, indicating the specific byte and input.

These error types ensure that malformed quoted strings are properly detected and reported.

## Usage Examples

See the [use cases](use_cases.md) document for detailed examples of how to use the quoting and unquoting functionality in various scenarios.