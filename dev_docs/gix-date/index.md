# gix-date

## Overview

`gix-date` is a specialized crate in the gitoxide ecosystem focused on parsing and formatting dates in Git's various formats. It provides functionality to handle the wide variety of date formats that Git supports, including RFC2822, ISO8601, raw timestamp formats, and relative dates like "2 weeks ago". The crate is specifically designed to match Git's date parsing behavior rather than serve as a general-purpose date/time library.

## Architecture

The crate is organized around a core `Time` type that represents a moment in time with timezone offset information. This type provides a unified representation that can be parsed from and formatted to various Git-compatible date formats.

The architecture consists of three main components:

1. **Parsing**: Functions to interpret date strings in various formats that Git understands
2. **Representation**: The `Time` type that stores seconds since Unix epoch and timezone offset
3. **Formatting**: Methods to convert the internal time representation to formatted strings

This architecture allows the crate to handle the complex requirements of Git's date handling, including:
- Parsing a wide variety of input formats
- Maintaining timezone information
- Supporting relative dates (which require a reference "now" time)
- Converting between different formats consistently

## Core Components

### Structs

| Struct | Description | Usage |
|--------|-------------|-------|
| `Time` | Represents a timestamp with timezone information | Core type representing dates in the crate |
| `TimeBuf` | Buffer for efficiently serializing Time objects | Used to avoid allocations when converting Time to strings |
| `CustomFormat` | Wrapper for format string patterns | Defines custom date format patterns |

### Traits

| Trait | Description | Implementors |
|-------|-------------|-------------|
| `std::fmt::Display` | Format a time as a string for display | Implemented for `Time` |
| `std::str::FromStr` | Parse a string into a time | Implemented for `Time` |
| `std::io::Write` | Write binary data | Implemented for `TimeBuf` |

### Functions

| Function | Description | Signature |
|----------|-------------|-----------|
| `parse` | Parse a date string in any Git-compatible format | `fn parse(input: &str, now: Option<SystemTime>) -> Result<Time, Error>` |
| `parse_header` | Parse a date in Git commit header format | `fn parse_header(input: &str) -> Option<Time>` |
| `Time::now_utc` | Get the current time in UTC | `fn now_utc() -> Self` |
| `Time::now_local` | Get the current time in the local timezone | `fn now_local() -> Option<Self>` |
| `Time::format` | Format a time according to a specific format | `fn format(&self, format: impl Into<Format>) -> String` |
| `Time::write_to` | Serialize a time to a writer | `fn write_to(&self, out: &mut dyn std::io::Write) -> std::io::Result<()>` |

### Enums

| Enum | Description | Variants |
|------|-------------|----------|
| `Format` | Defines different date formatting options | `Custom`, `Unix`, `Raw` |
| `parse::Error` | Error types for date parsing operations | `InvalidDateString`, `RelativeTimeConversion`, `InvalidDate`, `MissingCurrentTime` |

## Dependencies

### Internal Dependencies

| Crate | Usage |
|-------|-------|
| `gix-hash` | Used in tests only |
| `gix-testtools` | Used in tests only |

### External Dependencies

| Crate | Usage |
|-------|-------|
| `jiff` | Core date/time functionality |
| `bstr` | Byte string utilities for efficient string handling |
| `smallvec` | Efficient small vector implementation for `TimeBuf` |
| `thiserror` | Error type definitions |
| `itoa` | Fast integer to string conversion |
| `serde` (optional) | Serialization/deserialization support |

## Feature Flags

| Flag | Description | Dependencies Enabled |
|------|-------------|---------------------|
| `serde` | Enables serialization/deserialization for data structures | `serde`, `bstr/serde` |

## Examples

### Parsing Dates in Various Formats

```rust
use std::time::SystemTime;
use gix_date::{Time, parse, parse_header};

// Parse a date in the ISO8601 format
let iso_date = parse("2022-08-17 22:04:58 +0200", None).unwrap();
assert_eq!(iso_date.seconds, 1660766698);
assert_eq!(iso_date.offset, 7200);

// Parse a date in RFC2822 format
let rfc_date = parse("Thu, 18 Aug 2022 12:45:06 +0800", None).unwrap();
assert_eq!(rfc_date.seconds, 1660797906);
assert_eq!(rfc_date.offset, 28800);

// Parse a date in Git's raw format (commit header format)
let raw_date = parse_header("1660874655 +0800").unwrap();
assert_eq!(raw_date.seconds, 1660874655);
assert_eq!(raw_date.offset, 28800);

// Parse a relative date (requires a reference "now" time)
let now = SystemTime::now();
let relative_date = parse("2 weeks ago", Some(now)).unwrap();
// relative_date will be 2 weeks before now
```

### Getting the Current Time

```rust
use gix_date::Time;

// Current time in UTC
let now_utc = Time::now_utc();

// Current time in local timezone
if let Some(now_local) = Time::now_local() {
    println!("Current local time: {}", now_local);
} else {
    println!("Couldn't determine local time");
}

// Safe version that falls back to UTC if local time can't be determined
let now = Time::now_local_or_utc();
```

### Formatting Dates

```rust
use gix_date::{Time, time::format};

// Create a time representing January 1, 2022, UTC
let time = Time::new(1640995200, 0);

// Format as ISO8601
let iso_formatted = time.format(format::ISO8601);
assert_eq!(iso_formatted, "2022-01-01 00:00:00 +0000");

// Format as RFC2822
let rfc_formatted = time.format(format::RFC2822);
assert_eq!(rfc_formatted, "Sat, 01 Jan 2022 00:00:00 +0000");

// Format as raw (commit header format)
let raw_formatted = time.format(format::RAW);
assert_eq!(raw_formatted, "1640995200 +0000");

// Format as Unix timestamp
let unix_formatted = time.format(format::UNIX);
assert_eq!(unix_formatted, "1640995200");
```

### Efficient String Conversion

```rust
use gix_date::{Time, parse::TimeBuf};

let time = Time::new(1640995200, 0);
let mut buf = TimeBuf::default();

// Convert to string with reusable buffer (zero allocations)
let s = time.to_str(&mut buf);
assert_eq!(s, "1640995200 +0000");
```

## Implementation Details

### Time Representation

The `Time` struct uses two fields:
- `seconds`: A 64-bit signed integer representing seconds since Unix epoch (January 1, 1970)
- `offset`: A 32-bit signed integer representing timezone offset in seconds

This representation allows the crate to handle dates both before and after the Unix epoch, which is a slight deviation from Git's original implementation (which only supports dates after Unix epoch). The crate can represent dates billions of years in the past and future, limited only by the i64 range.

### Date Parsing Strategy

The `parse` function tries multiple parsing strategies in sequence:
1. Short format (YYYY-MM-DD)
2. RFC2822 format 
3. ISO8601 format
4. ISO8601 strict format
5. Custom Gitoxide format
6. Default Git format
7. Unix timestamp
8. Relative date format
9. Raw (commit header) format

This approach ensures maximum compatibility with the various date formats that Git accepts.

### Relative Date Parsing

Relative dates (like "2 weeks ago") are handled by:
1. Parsing the quantity and unit from the string
2. Converting to a duration
3. Subtracting from the provided reference "now" time

This implementation matches Git's behavior for relative dates, though it requires the caller to provide the current time as a reference point.

### Threading and Safety

The crate is thread-safe as `Time` implements `Send` and `Sync`. There are no internal mutexes or shared state that would cause thread safety issues.

## Testing Strategy

The crate employs several testing strategies:

1. **Format Verification**: Tests verify that parsing and formatting round-trip correctly for all supported formats.

2. **Git Compatibility**: Tests use Git's own behavior as a reference to ensure compatibility.

3. **Edge Cases**: Special tests for unusual cases like negative timestamps or malformed input.

4. **Fuzzing**: The crate has fuzzing targets to identify parsing issues with unexpected inputs.

5. **Relative Date Testing**: Comprehensive tests for relative date parsing with various units and quantities.

These tests ensure that the crate matches Git's behavior across the wide variety of date formats it supports.