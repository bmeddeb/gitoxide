# gix-trace

## Overview

`gix-trace` is a foundational crate in the gitoxide ecosystem that provides tracing and instrumentation capabilities with zero-cost abstractions. It allows for fine-grained performance insights and debugging information while ensuring zero overhead when tracing is disabled.

The crate offers a thin wrapper around the `tracing` crate, with the key feature that all tracing macros and functions can be completely compiled out of the binary when not needed, resulting in zero runtime overhead.

## Architecture

`gix-trace` follows a clean, compile-time architecture based on Rust's feature flags system:

### Core Design Principles

1. **Zero-Cost Abstractions** - When the `tracing` feature flag is disabled, all tracing code compiles to no-ops with zero runtime overhead.

2. **Granular Tracing Levels** - The crate provides two primary tracing levels:
   - **Coarse** - For high-level operations with low frequency
   - **Detail** - For fine-grained operations within coarse spans (used only for performance-critical code paths)

3. **Feature-Driven Behavior** - All functionality is toggled via feature flags, allowing applications to opt-in only to what they need.

### Module Structure

The crate has a carefully designed internal structure to support its zero-cost philosophy:

- **enabled.rs** - Contains the real implementation when the `tracing` feature is enabled
- **disabled.rs** - Contains no-op implementations when the `tracing` feature is disabled
- **lib.rs** - Provides the public API and conditionally includes the appropriate implementation

## Core Components

### Trace Levels

```rust
pub enum Level {
    /// A coarse-grained trace level for entire operations with low frequency
    Coarse = 1,
    
    /// Finer grained trace level for significant-cost operations
    Detail = 2,
}
```

The `Level` enum defines the granularity at which tracing is performed. It allows filtering traces early at compile time to minimize runtime overhead.

### Span

The `Span` struct is the main tracing primitive, representing a time span during which code execution occurs:

```rust
// When tracing is enabled:
pub struct Span {
    id: Option<(Id, Dispatch, &'static Metadata<'static>)>,
}

// When tracing is disabled:
pub struct Span;
```

Key methods:
- `new(level, meta, values)` - Creates a new span
- `record(field, value)` - Records a field within the span
- `into_scope(f)` - Executes a function with the span active

### Macros

The crate provides several macros to create spans and events:

#### Span Macros

- `span!` - Create a span with the specified level
- `coarse!` - Create a Coarse-level span (high-level operations)
- `detail!` - Create a Detail-level span (finer grained operations)

#### Event Macros

- `event!` - Create an event with a specific level
- `error!` - Create an ERROR level event
- `warn!` - Create a WARN level event
- `info!` - Create an INFO level event
- `debug!` - Create a DEBUG level event
- `trace!` - Create a TRACE level event

## Dependencies

`gix-trace` has minimal dependencies:

- **tracing-core** (optional) - Used when the `tracing` feature is enabled
- **document-features** (optional) - Used only for documentation

## Feature Flags

The crate provides three feature flags:

- **default** - Empty, as the application is expected to opt-in explicitly
- **tracing** - Enables actual tracing with `tracing-core`
- **tracing-detail** - Enables Detail-level spans in addition to Coarse-level spans

The maximum allowed tracing level is determined at compile time:
```rust
// When tracing-detail is enabled
pub const MAX_LEVEL: Level = Level::Detail;

// When tracing-detail is not enabled
pub const MAX_LEVEL: Level = Level::Coarse;
```

## Examples

### Creating a Coarse Span

```rust
// Basic span with no fields
let span = gix_trace::coarse!("operation_name");

// Span with structured fields
let span = gix_trace::coarse!("operation_name", file_count = 42, repo_name = "my-repo");

// Execute code within a span
let result = gix_trace::coarse!("operation_name").into_scope(|| {
    // Code here will be associated with the span
    perform_operation()
});
```

### Creating a Detail Span

```rust
// Only created when tracing-detail feature is enabled
let span = gix_trace::detail!("detail_operation", object_count = count);
```

### Emitting Events

```rust
// Error event with formatted message
gix_trace::error!("Failed to read file: {}", path);

// Info event with structured data
gix_trace::info!(file_count = 42, repo_size = size);

// Debug event with debug formatting
gix_trace::debug!("Processing object {}", ?object_id);
```

## Implementation Details

### Conditional Compilation

The implementation uses conditional compilation to switch between real and no-op implementations:

```rust
#[cfg(feature = "tracing")]
mod enabled;

#[cfg(feature = "tracing")]
pub use enabled::{field, Span};

#[cfg(not(feature = "tracing"))]
mod disabled;

#[cfg(not(feature = "tracing"))]
pub use disabled::Span;
```

### Level Mapping

When tracing is enabled, the gitoxide-specific levels are mapped to tracing-core levels:

```rust
impl Level {
    pub const fn into_tracing_level(self) -> tracing_core::Level {
        match self {
            Level::Coarse => tracing_core::Level::INFO,
            Level::Detail => tracing_core::Level::DEBUG,
        }
    }
}
```

### Zero-Cost Design

When tracing is disabled, all spans and events become no-ops:

```rust
// From disabled.rs
pub struct Span;

impl Span {
    pub fn record<V>(&self, _field: &str, _value: V) -> &Self {
        self
    }
}

macro_rules! event {
    // All variants compile to {} (no-op)
    (target: $target:expr, $lvl:expr, { $($fields:tt)* } )=> ({});
    // ...other variants
}
```

## Usage Guidelines

1. **Use `coarse!` spans for high-level operations** - Application-level operations like repository operations, network calls, or user interactions.

2. **Use `detail!` spans sparingly** - Only for operations that have significant cost and need more detailed profiling.

3. **Prefer structured fields over messages** - `file_count = 42` is more useful for analysis than messages with string interpolation.

4. **Set spans in scopes** - Use `.into_scope(|| {...})` to ensure spans are automatically closed when the scope ends.

5. **Application opt-in** - Applications using gitoxide should explicitly enable tracing via `gix-features` when needed.