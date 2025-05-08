# gix-config-value Use Cases

## Intended Audience

The `gix-config-value` crate is intended for:

1. **Git Implementation Developers**: Creators of Git clients, servers, and tools that need to parse and handle Git configuration values
2. **Git Extension Developers**: Developers creating Git hooks, extensions, and integrations
3. **Repository Management Tool Developers**: Developers of tools that interact with Git repositories and need to understand Git configuration
4. **Users of the `gix` Ecosystem**: Developers building applications on top of the `gix` library who need to work with Git configuration values

## Problems and Solutions

### Problem: Parsing Git's Boolean Values

**Challenge**: Git allows boolean values to be specified in multiple formats (`true`, `yes`, `on`, `false`, `no`, `off`, and numeric values). Consistently handling all these formats correctly is error-prone.

**Solution**: The `Boolean` type encapsulates all the Git-specific boolean parsing rules in one place.

```rust
use gix_config_value::Boolean;
use std::convert::TryFrom;
use bstr::ByteSlice;

// Function that handles Git boolean config from various sources
fn handle_auto_crlf(value: &str) -> bool {
    match Boolean::try_from(value.as_bytes().as_bstr()) {
        Ok(boolean) => boolean.is_true(),
        Err(_) => {
            // Default behavior for invalid or missing values
            false
        }
    }
}

// These all evaluate to true
assert!(handle_auto_crlf("true"));
assert!(handle_auto_crlf("yes"));
assert!(handle_auto_crlf("on"));
assert!(handle_auto_crlf("1"));

// These all evaluate to false
assert!(!handle_auto_crlf("false"));
assert!(!handle_auto_crlf("no"));
assert!(!handle_auto_crlf("off"));
assert!(!handle_auto_crlf("0"));
assert!(!handle_auto_crlf(""));
```

### Problem: Handling Size Values with Suffixes

**Challenge**: Git configuration allows specifying size values with suffixes (like `1k`, `5m`, or `2g`), which need to be correctly parsed and converted to actual byte counts.

**Solution**: The `Integer` type with its suffix handling provides a clean way to parse and work with these values.

```rust
use gix_config_value::Integer;
use std::convert::TryFrom;
use bstr::ByteSlice;

// Function to get maximum pack size from config
fn get_pack_size_limit(config_value: &str) -> Option<u64> {
    // Parse the value with potential suffix
    let size = Integer::try_from(config_value.as_bytes().as_bstr()).ok()?;
    
    // Convert to actual bytes, handling size suffix
    match size.to_decimal() {
        Some(bytes) if bytes > 0 => Some(bytes as u64),
        _ => None,
    }
}

// Different ways to specify the same 1MB limit
assert_eq!(get_pack_size_limit("1048576"), Some(1048576));
assert_eq!(get_pack_size_limit("1024k"), Some(1048576));
assert_eq!(get_pack_size_limit("1m"), Some(1048576));

// Different units for the same 1GB value
assert_eq!(get_pack_size_limit("1g"), Some(1073741824));
assert_eq!(get_pack_size_limit("1024m"), Some(1073741824));
assert_eq!(get_pack_size_limit("1048576k"), Some(1073741824));
```

### Problem: Expanding Path References in Configuration

**Challenge**: Git configuration can contain path values that need expansion, such as `~/` for the home directory or `~user/` for other user directories. These need to be handled in a platform-specific way.

**Solution**: The `Path` type with its interpolation functionality handles all Git path expansions.

```rust
use gix_config_value::Path;
use gix_config_value::path::interpolate::Context;
use bstr::ByteSlice;
use std::path::PathBuf;

// Function to resolve a template directory path from config
fn resolve_template_dir(config_value: &str) -> Result<PathBuf, Box<dyn std::error::Error>> {
    // Create a Path from the config value
    let path = Path::from(config_value.as_bytes().as_bstr().into());
    
    // Set up context for interpolation
    let context = Context {
        git_install_dir: Some(&PathBuf::from("/usr/local/git")),
        home_dir: Some(&PathBuf::from("/home/user")),
        home_for_user: Some(|username| {
            if username == "git" {
                Some(PathBuf::from("/home/git"))
            } else {
                None
            }
        }),
    };
    
    // Interpolate the path
    let path = path.interpolate(context)?;
    Ok(path.into_owned())
}

// Home directory expansion
assert_eq!(
    resolve_template_dir("~/templates").unwrap(),
    PathBuf::from("/home/user/templates")
);

// User-specific expansion
assert_eq!(
    resolve_template_dir("~git/templates").unwrap(),
    PathBuf::from("/home/git/templates")
);

// Git installation path expansion
assert_eq!(
    resolve_template_dir("%(prefix)/share/git-templates").unwrap(),
    PathBuf::from("/usr/local/git/share/git-templates")
);
```

### Problem: Working with Git's Color Specifications

**Challenge**: Git has a rich syntax for specifying colors in the UI, including named colors, RGB values, and text attributes. Parsing these correctly and converting them to usable values is complex.

**Solution**: The `Color` type provides comprehensive parsing of Git's color syntax.

```rust
use gix_config_value::Color;
use gix_config_value::color::{Name, Attribute};
use std::convert::TryFrom;
use bstr::ByteSlice;

// Function to parse color config and apply to UI elements
fn apply_diff_color(config_value: &str) -> String {
    // Default to red if parsing fails
    let color = Color::try_from(config_value.as_bytes().as_bstr())
        .unwrap_or(Color {
            foreground: Some(Name::Red),
            background: None,
            attributes: Attribute::empty(),
        });
    
    // Build terminal escape sequence based on the color
    let mut result = String::from("\x1b[");
    
    // Add foreground color code
    if let Some(fg) = color.foreground {
        match fg {
            Name::Red => result.push_str("31"),
            Name::Green => result.push_str("32"),
            Name::Blue => result.push_str("34"),
            // ... handle other colors
            _ => result.push_str("31"), // Default to red
        }
    }
    
    // Add attributes
    if color.attributes.contains(Attribute::BOLD) {
        result.push_str(";1");
    }
    if color.attributes.contains(Attribute::ITALIC) {
        result.push_str(";3");
    }
    
    result.push('m');
    result
}

// Basic color
assert_eq!(apply_diff_color("red"), "\x1b[31m");

// Color with attributes
assert_eq!(apply_diff_color("bold red"), "\x1b[31;1m");

// Complex styling
assert_eq!(apply_diff_color("bold italic red"), "\x1b[31;1;3m");
```

### Problem: Validating Configuration Values

**Challenge**: User-provided configuration values need to be validated against Git's expected formats before use.

**Solution**: The crate's type-specific `TryFrom` implementations provide built-in validation.

```rust
use gix_config_value::{Boolean, Integer, Color, Path};
use std::convert::TryFrom;
use bstr::ByteSlice;

// Function to validate a configuration value based on its expected type
fn validate_config_value(key: &str, value: &str) -> Result<String, String> {
    // Determine expected type based on key
    match key {
        key if key.ends_with(".enabled") || key.ends_with(".auto") => {
            // Should be a boolean
            Boolean::try_from(value.as_bytes().as_bstr())
                .map(|_| format!("Valid boolean: {}", value))
                .map_err(|e| format!("Invalid boolean: {}", e))
        }
        key if key.ends_with(".maxsize") || key.ends_with(".limit") => {
            // Should be an integer with optional suffix
            Integer::try_from(value.as_bytes().as_bstr())
                .map(|_| format!("Valid integer: {}", value))
                .map_err(|e| format!("Invalid integer: {}", e))
        }
        key if key.ends_with(".color") => {
            // Should be a color
            Color::try_from(value.as_bytes().as_bstr())
                .map(|_| format!("Valid color: {}", value))
                .map_err(|e| format!("Invalid color: {}", e))
        }
        key if key.ends_with(".path") || key.ends_with("dir") => {
            // Should be a path
            let path = Path::from(value.as_bytes().as_bstr().into());
            // Just validate it's not empty
            if path.is_empty() {
                Err("Path cannot be empty".to_string())
            } else {
                Ok(format!("Valid path: {}", value))
            }
        }
        _ => Ok(format!("Unknown type for key {}, accepting value: {}", key, value)),
    }
}

// Validate various config values
assert!(validate_config_value("core.autocrlf", "true").is_ok());
assert!(validate_config_value("core.autocrlf", "invalid").is_err());

assert!(validate_config_value("pack.sizelimit", "1g").is_ok());
assert!(validate_config_value("pack.sizelimit", "1z").is_err());

assert!(validate_config_value("color.diff", "bold red").is_ok());
assert!(validate_config_value("color.diff", "rainbow").is_err());

assert!(validate_config_value("core.templatedir", "~/templates").is_ok());
assert!(validate_config_value("core.templatedir", "").is_err());
```

### Problem: Consistent Environment Variable Parsing

**Challenge**: Git can be configured through environment variables (like `GIT_CONFIG_KEY_0=value`), which need to be parsed using the same rules as configuration files.

**Solution**: The same value parsers can be applied to environment variables.

```rust
use gix_config_value::Boolean;
use std::convert::TryFrom;
use std::env;
use bstr::ByteSlice;

// Function to check if feature is enabled via Git config or environment
fn is_feature_enabled(feature_name: &str, default: bool) -> bool {
    // First check environment variable
    let env_var_name = format!("GIT_FEATURE_{}", feature_name.to_uppercase());
    if let Ok(value) = env::var(env_var_name) {
        if let Ok(boolean) = Boolean::try_from(value.as_bytes().as_bstr()) {
            return boolean.is_true();
        }
    }
    
    // Fallback to config value (simplified - normally would read from Git config)
    // ...
    
    // Return default if not configured
    default
}

// Usage example
// GIT_FEATURE_MANYFILES=yes would enable the feature
// GIT_FEATURE_MANYFILES=off would disable it
assert_eq!(is_feature_enabled("manyfiles", true), true);
```

## Integration with Other Components

The `gix-config-value` crate integrates with other parts of the gitoxide ecosystem:

1. **`gix-config`**: Provides the value parsing and representation for the main configuration parser
2. **`gix`**: Enables consistent handling of configuration values throughout the Git implementation
3. **`gix-path`**: Interacts with path handling for path interpolation
4. **CLI Tools**: Helps validate and parse command-line arguments that mirror Git configuration values

These integrations ensure that configuration values are handled consistently throughout the entire codebase, regardless of whether they come from config files, environment variables, or command-line arguments.