# gix-mailmap

A crate in the gitoxide project for parsing and working with Git mailmap files, which allow mapping author and committer identities.

## Overview

The `gix-mailmap` crate provides functionality for parsing Git's `.mailmap` files and resolving author/committer signatures based on the mappings defined in those files. Git mailmap files are used to consolidate different variations of names and email addresses to consistent canonical forms, which is particularly useful in projects with many contributors who might use different email addresses or name variations over time.

This crate provides:
- Parsing of mailmap file content into mapping entries
- An optimized data structure (`Snapshot`) for efficient lookups
- Functions to resolve signatures based on mailmap rules
- Support for the various mapping formats that Git's mailmap files allow

## Architecture & Components

The crate consists of three main components:

### 1. Parser

The parser component reads mailmap file content and converts it into `Entry` instances that represent individual mapping rules:

- `parse()` function: Parses mailmap content line by line, returning an iterator of `Result<Entry, Error>`
- `parse_ignore_errors()` function: Similar to `parse()` but automatically skips lines with parsing errors
- `Lines` iterator: Handles the line-by-line parsing state

### 2. Entry

The `Entry` struct represents a single mailmap entry, which can be one of several mapping types:

- Change name by email
- Change email by email
- Change email by name and email
- Change name and email by email
- Change name and email by name and email

Each `Entry` contains combinations of:
- `new_name`: The name to map to
- `new_email`: The email to map to
- `old_name`: The name to look for and replace (optional)
- `old_email`: The email to look for and replace (always required)

### 3. Snapshot

The `Snapshot` struct provides an optimized data structure for efficient, case-insensitive lookups of mappings:

- Organizes entries by old email for fast lookup
- Supports resolving `gix_actor::SignatureRef` instances into their mapped form
- Provides multiple resolution strategies including copy-on-write variants
- Handles normalization of email addresses for better matching

## Dependencies

- `bstr`: For byte string handling, offering better support for non-UTF8 content
- `gix-actor`: For working with Git author/committer signatures
- `gix-date`: For handling Git-formatted dates in signatures
- `thiserror`: For error type definitions
- Optional `serde` support for serialization/deserialization

## Feature Flags

- `serde`: Enables serialization/deserialization of data structures using serde.

## Implementation Details

### Mailmap File Format

Git mailmap files follow a specific format:
- Lines beginning with `#` are comments
- Empty lines are ignored
- Valid lines contain one or two "name <email>" pairs

The syntax supports various mapping formats:
```
# Format: New Name <new@email> Old Name <old@email>
# Or other variations:
New Name <new@email>                 # Changes name based on email
<new@email> <old@email>              # Changes email only
New Name <new@email> <old@email>     # Changes name and email based on email
<new@email> Old Name <old@email>     # Changes email based on name+email
New Name <new@email> Old Name <old@email>  # Changes both based on name+email
```

### Parsing Logic

The parser processes mailmap content line by line:
1. Skips comments and empty lines
2. For each valid line, extracts name-email pairs
3. Determines the type of mapping based on the extracted pairs
4. Creates an appropriate `Entry` instance

### Lookup Mechanism

The `Snapshot` struct provides optimized lookup:
1. Entries are stored in vectors sorted by old_email
2. Lookups use binary search for efficient matching
3. Case-insensitive matching is used for emails
4. A cascading approach is used: first match by email, then by name if available

### Error Handling

The crate defines specific error types for the parser:
- `UnconsumedInput`: When a line has too many name/email pairs or none at all
- `Malformed`: For lines with invalid format (e.g., missing closing bracket in email)

## Usage Examples

See the [use cases](use_cases.md) document for detailed examples of how to use the mailmap functionality in various scenarios.