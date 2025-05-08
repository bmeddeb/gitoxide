# gix-macros

## Overview

`gix-macros` is a foundational crate in the gitoxide ecosystem that provides procedural macros specifically designed to simplify and optimize code across the gitoxide codebase. The crate currently focuses on reducing monomorphization costs through its `momo` macro, which stands for "MOnomorphization to MOrphization" - a technique that converts monomorphized code to code that uses trait objects.

The crate serves as a utility to prevent code bloat and unnecessary monomorphization in the gitoxide codebase, improving compile times and binary sizes without sacrificing the ergonomics of generic programming.

## Architecture

`gix-macros` follows a simple architecture focused on procedural macro implementation:

### Core Design Principles

1. **Reduce Monomorphization** - The primary goal is to reduce the code bloat that comes from excessive monomorphization, which is a common issue in Rust codebases that make heavy use of generics.

2. **Maintain API Ergonomics** - The macros allow developers to write ergonomic, generic code while automatically generating more efficient implementations behind the scenes.

3. **Zero gix-internal Dependencies** - As a level 0 crate, it has no dependencies on other gitoxide crates, making it foundational to the gitoxide dependency tree.

4. **Focus on Performance-critical Paths** - The crate is designed to be used selectively on performance-critical paths where monomorphization would otherwise cause bloat.

### Module Structure

The crate has a minimalist structure:

- **lib.rs** - Exports the public macros and contains high-level documentation
- **momo.rs** - Implements the `momo` macro for de-monomorphization

## Core Components

### The `momo` Macro

```rust
#[momo]
fn some_function<T: Into<String>>(value: T) -> String {
    value.into()
}
```

The `momo` macro is the primary component of the crate. It transforms functions that use generic trait bounds into functions that:

1. Maintain the original signature for API compatibility
2. Generate an inner implementation that uses trait objects (`&dyn Trait`) instead of generics
3. Call the inner implementation with the appropriate trait conversions

This reduces the number of monomorphized function instantiations in the final binary while maintaining the ergonomic API of using generics.

#### Supported Conversions

The `momo` macro currently supports the following trait conversions:

- `Into<T>` → `.into()`
- `AsRef<T>` → `.as_ref()`
- `AsMut<T>` → `.as_mut()`

#### Generated Code Structure

For a function like:

```rust
#[momo]
fn process<T: Into<String>>(value: T) -> String {
    // Implementation
}
```

The macro generates code similar to:

```rust
fn process<T: Into<String>>(value: T) -> String {
    fn _process_inner_generated_by_gix_macro_momo(value: String) -> String {
        // Original implementation with direct String instead of T
    }
    
    _process_inner_generated_by_gix_macro_momo(value.into())
}
```

This pattern reduces the number of monomorphized instantiations needed while retaining the convenient generic API.

## Dependencies

`gix-macros` has the following external dependencies:

- **syn** - For parsing Rust syntax in the procedural macro
- **quote** - For generating Rust code in the procedural macro
- **proc-macro2** - For low-level procedural macro operations

It has no dependencies on other gitoxide crates, keeping it at the foundation of the dependency hierarchy.

## Feature Flags

`gix-macros` doesn't define any feature flags of its own. This keeps the crate simple and focused on its core functionality.

## Examples

### Basic Function De-monomorphization

```rust
use gix_macros::momo;

// Before: Each combination of parameter types generates a new monomorphized version
fn process_raw<T: Into<String>, U: AsRef<str>>(name: T, reference: U) -> String {
    let mut result = name.into();
    result.push_str(reference.as_ref());
    result
}

// After: A single inner implementation handles all combinations
#[momo]
fn process<T: Into<String>, U: AsRef<str>>(name: T, reference: U) -> String {
    let mut result = name.into();
    result.push_str(reference.as_ref());
    result
}

// Usage remains the same
fn main() {
    let result1 = process("hello", "world");    // T = &str, U = &str
    let result2 = process(String::from("hello"), "world");  // T = String, U = &str
    println!("{} {}", result1, result2);
}
```

### Method De-monomorphization

```rust
use gix_macros::momo;

struct Repository {
    // some fields
}

impl Repository {
    // Before: Each path type creates a new monomorphized version
    fn open_raw<P: AsRef<std::path::Path>>(path: P) -> Self {
        // open repository at the given path
        Self { /* ... */ }
    }
    
    // After: A single implementation handles all path types
    #[momo]
    fn open<P: AsRef<std::path::Path>>(path: P) -> Self {
        // open repository at the given path
        Self { /* ... */ }
    }
    
    // Methods with self parameters work too
    #[momo]
    fn get_file<P: AsRef<std::path::Path>>(&self, path: P) -> Vec<u8> {
        // read file at path
        Vec::new()
    }
}
```

### Multiple Trait Bounds

```rust
use gix_macros::momo;

// Works with multiple trait bounds and conversions
#[momo]
fn complex_example<S, P, M>(
    name: S, 
    path: P,
    mut buffer: M
) -> String 
where
    S: Into<String>,
    P: AsRef<std::path::Path>,
    M: AsMut<[u8]>,
{
    let name = name.into();
    let path = path.as_ref();
    let buffer = buffer.as_mut();
    
    // Use the converted values
    format!("Name: {}, Path: {}, Buffer len: {}", 
            name, path.display(), buffer.len())
}
```

### Where to Use `momo`

The `momo` macro is particularly useful in scenarios like:

1. Public API functions that need to be generic for ergonomics
2. Functions that are called frequently but don't need monomorphization for performance
3. Code that needs to reduce compile times and binary size

## Implementation Details

### De-monomorphization Process

The `momo` macro follows these steps during macro expansion:

1. **Analyze Function Signature** - Parses the function signature to identify generic type parameters with relevant trait bounds (`Into<T>`, `AsRef<T>`, `AsMut<T>`)

2. **Create Inner Function** - Generates an inner function with the same logic but using concrete types instead of generic parameters

3. **Replace Generic Parameters** - Modifies the argument list to call the appropriate trait methods (`.into()`, `.as_ref()`, `.as_mut()`)

4. **Handle Self Types** - Special handling for methods to ensure that `self` and `Self` references work correctly

5. **Preserve Documentation** - Retains original documentation comments on the public function

### Special Cases

The implementation handles several special cases:

#### Methods vs. Free Functions

For methods (functions within `impl` blocks), the macro has special handling to ensure that `self` and `Self` references work correctly. It detects whether the function uses `self` or `Self` and generates the appropriate code structure.

#### Different `self` Receiver Types

The macro supports various self receiver types:
- `self`
- `&self`
- `&mut self`
- `self: Self`
- `self: Pin<&mut Self>`

#### Error Handling

The macro includes error handling for cases where:
- It's applied to a non-function item (e.g., struct, enum)
- No trait conversions are applied (the macro would have no effect)

### Performance Considerations

The `momo` macro is designed to be used selectively, not universally. It's most beneficial in scenarios where:

1. The function contains substantial logic
2. The function is called with many different generic parameter types
3. The performance benefit of monomorphization is minimal

For very small functions or performance-critical hot paths, direct monomorphization might still be preferred.

### Usage in gitoxide

In the gitoxide codebase, the `momo` macro is used to:

1. Reduce the binary size of CLI tools
2. Improve compile times during development
3. Maintain ergonomic APIs while reducing code bloat

This approach aligns with gitoxide's philosophy of being performance-conscious while maintaining developer ergonomics.