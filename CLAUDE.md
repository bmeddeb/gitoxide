# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current Objective - Create `dev_docs` Documentation

The primary task is to create comprehensive documentation for each crate in the gitoxide workspace. This entails:

1. Consult dev_docs/documentation_plan.md, Check dev_docs/index.md for the current status of documentation.
3. Creating detailed markdown documentation for each crate covering:
   - Architecture and design
   - All structs, functions, methods, and traits
   - Relationships between components
   - Dependencies and how they're used
   - Feature flags and their effects
   - Examples of usage

4. follow the template in dev_docs/template.md to create a new documentation page
5. Create use_cases.md to generate use cases as follow: Intended Audience, problems -> solution, with example code when applicable. Create other markdown files as needed.
6. add the new page to  index.md



This comprehensive documentation effort will serve as a guide for development and help in understanding the entire codebase.

## Project Overview

Gitoxide is a Git implementation written in Rust, providing:
- `gix`: Low-level plumbing commands for validating API functionality and specialized use cases
- `ein`: High-level porcelain commands for user-friendly Git operations

The project is structured as a workspace with many crates, each responsible for specific Git functionality (hash handling, object management, references, etc.)

## Build and Development Commands

### Building the Project

```bash
# Build with default features (max)
cargo build

# Build with specific feature sets
cargo build --no-default-features --features max-pure  # Pure Rust implementation
cargo build --no-default-features --features small     # Minimal build
cargo build --no-default-features --features lean      # Smaller CLI, faster build
cargo build --no-default-features --features lean-async  # Async support
```

### Just Commands

The project uses a `justfile` for common development tasks. Run `just` to see all available commands.

```bash
# Run all tests (clippy, unit tests, journey tests, doc tests)
just test

# Run only unit tests
just unit-tests

# Run journey tests with specific features
just journey-tests-pure  # max-pure features
just journey-tests-small  # small features
just journey-tests-async  # lean-async features

# Run nextest for faster test execution
just nextest
# or alias
just nt

# Run checks
just check

# Run clippy
just clippy

# Format code
just fmt
```

### Running Specific Tests

```bash
# Test a specific crate
cargo nextest run -p gix-hash

# Test with specific features
cargo nextest run -p gix --no-default-features --features max-performance-safe

# Run documentation tests
cargo test --workspace --doc --no-fail-fast
```

## Architecture

Gitoxide follows a modular architecture with many specialized crates:

- `gix`: Top-level crate that acts as hub to all functionality
- `gix-*`: Plumbing crates that implement specific Git functionality
- `gitoxide-core`: Implementation library backing the CLI commands

### Key Components

1. **Repository Layer**:
   - Repository discovery, initialization, and access
   - Reference management (branches, tags)
   - Object storage and retrieval
   - Configuration handling

2. **Object Layer**:
   - Parse and create Git objects (commit, tree, blob, tag)
   - Hash computation and verification
   - Object store access (loose objects, packfiles)

3. **Network Layer**:
   - Transport protocols (git://, http://, ssh://)
   - Remote operations (fetch, push)
   - Protocol negotiation

4. **Filesystem Layer**:
   - Index management
   - Worktree interaction
   - Sparse checkout
   - Attribute and ignore handling

## Development Practices

1. **Commit Messages**: Uses a 'purposeful conventional commits' style:
   - Breaking changes: `change!:` or `remove!:` prefix
   - Features: `feat:` prefix
   - Fixes: `fix:` prefix

2. **Feature Flags**: Several feature sets are available:
   - `max`: Default, fastest with all external dependencies
   - `max-pure`: Pure Rust implementation
   - `lean`: Smaller CLI with faster build times
   - `small`: Minimal feature set
   - Many more fine-grained features for specific functionality

3. **Error Handling**:
   - Never use `.unwrap()`, prefer `.expect("reason")`
   - Use `thiserror` for error types
   - Proper error chains for better debugging

4. **Testing**:
   - Test-first development
   - Use Git as a reference implementation
   - Journey tests for CLI validation
   - Unit tests for API verification

5. **Async Support**:
   - Conditional compilation for both sync and async APIs
   - Feature flags for async implementations

## Common Development Tasks

When implementing new features or fixing bugs:

1. Study the modular structure to identify the right crate(s) to modify
2. Follow the existing patterns for error handling, API design, and testing
3. Run `just check` to validate the changes work across all build configurations
4. Run `just clippy` to ensure code quality
5. Run `just test` to verify all tests pass
6. Run `just fmt` for code formatting

## Stability and Versioning

The project follows semver and has a stability guide (STABILITY.md) to indicate how much churn can be expected for each crate:

- Stability Tier 1: Production grade with solid API
- Stability Tier 2: Stabilizing with few API changes expected
- Stabilization Candidates: Feature complete but need more testing
- Initial Development: Usable but potentially incomplete
- Very Early/Idea: Experimental or placeholder
