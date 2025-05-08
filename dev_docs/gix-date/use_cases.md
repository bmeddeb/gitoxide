# gix-date Use Cases

## Intended Audience

- **Git Tool Developers**: Building Git-compatible tools that need to parse and format Git dates
- **Repository Analysis Tools**: Applications that work with Git repository metadata
- **Git Interface Implementers**: Developers creating interfaces to Git repositories

## Use Cases

### 1. Parsing Git Commit Timestamps

**Problem**: Git commit metadata contains timestamps in a specific format that needs to be parsed.

**Solution**: Use `gix-date` to parse dates in Git's raw format:

```rust
// Parse a Git commit's date field
let commit_date_str = "1660874655 +0800";
if let Some(time) = gix_date::parse_header(commit_date_str) {
    println!("Commit timestamp: {} seconds since epoch", time.seconds);
    println!("Timezone offset: {} seconds", time.offset);
}
```

**Result**: Reliable parsing of Git commit timestamps that matches Git's behavior.

### 2. Handling Multiple Date Formats

**Problem**: Users input dates in various formats when interacting with Git tools.

**Solution**: Use the flexible parsing capabilities of `gix-date`:

```rust
// Parse dates in various formats that Git accepts
let dates = [
    "2022-08-17",                              // SHORT format
    "Thu, 18 Aug 2022 12:45:06 +0800",        // RFC2822 format
    "2022-08-17T21:43:13+08:00",              // ISO8601_STRICT format
    "123456789",                               // Unix timestamp
    "1 week ago"                               // Relative format
];

let now = std::time::SystemTime::now();
for date_str in dates {
    match gix_date::parse(date_str, Some(now)) {
        Ok(time) => println!("Parsed '{}' to {}", date_str, time),
        Err(_) => println!("Failed to parse '{}'", date_str),
    }
}
```

**Result**: User-friendly date input that accepts a wide range of formats.

### 3. Date Formatting for Git Output

**Problem**: Git-compatible tools need to output dates in Git's standard formats.

**Solution**: Use `gix-date`'s formatting options:

```rust
use gix_date::{Time, time::format};

// Create a time representing a specific moment
let time = Time::new(1660797906, 28800); // 2022-08-18 in UTC+8

// Format in different Git styles
println!("Default format: {}", time.format(format::DEFAULT));    // Thu Aug 18 12:45:06 2022 +0800
println!("ISO format: {}", time.format(format::ISO8601));        // 2022-08-18 12:45:06 +0800
println!("RFC2822: {}", time.format(format::RFC2822));           // Thu, 18 Aug 2022 12:45:06 +0800
println!("Raw format: {}", time.format(format::RAW));            // 1660797906 +0800
```

**Result**: Consistent date formatting that matches Git's output styles.

### 4. Working with Relative Dates

**Problem**: Git commands support relative dates like "2 weeks ago" that need a reference time.

**Solution**: Parse relative dates with a reference time:

```rust
use std::time::SystemTime;

// Get a reference time (usually "now")
let now = SystemTime::now();

// Parse relative dates
let dates = ["5 minutes ago", "1 day ago", "3 weeks ago", "2 months ago"];

for date_str in dates {
    match gix_date::parse(date_str, Some(now)) {
        Ok(time) => {
            let seconds_ago = gix_date::Time::now_utc().seconds - time.seconds;
            println!("'{}' was {} seconds ago", date_str, seconds_ago);
        },
        Err(e) => println!("Failed to parse '{}': {}", date_str, e),
    }
}
```

**Result**: Natural date expressions that match Git's behavior.

### 5. Efficient Date Serialization

**Problem**: Git operations need to serialize dates efficiently for commit creation.

**Solution**: Use `TimeBuf` to avoid allocations during serialization:

```rust
use gix_date::{Time, parse::TimeBuf};

// Create a buffer once and reuse it
let mut buffer = TimeBuf::default();

// Process many dates efficiently
let times = [
    Time::new(1660797906, 28800),  // 2022-08-18 in UTC+8
    Time::new(1659933906, 28800),  // 2022-08-08 in UTC+8
    Time::new(1112911993, 3600),   // 2005-04-08 in UTC+1
];

for time in times {
    // Zero-allocation conversion to string
    let formatted = time.to_str(&mut buffer);
    // Use the formatted string...
    println!("{}", formatted);
}
```

**Result**: Memory-efficient date formatting for high-performance applications.

### 6. Timezone-Aware Date Handling

**Problem**: Git dates include timezone information that must be preserved.

**Solution**: Use `Time`'s timezone offset field:

```rust
use gix_date::Time;

// Create dates with different timezone offsets
let utc_time = Time::new(1660797906, 0);          // UTC
let est_time = Time::new(1660797906, -18000);     // UTC-5 (EST)
let ist_time = Time::new(1660797906, 19800);      // UTC+5:30 (IST)

// Times have same epoch seconds but different representations
println!("UTC time: {}", utc_time);               // 1660797906 +0000
println!("EST time: {}", est_time);               // 1660797906 -0500
println!("IST time: {}", ist_time);               // 1660797906 +0530
```

**Result**: Correct handling of timezone offsets in Git dates.

## Key Benefits

1. **Git Compatibility**: Parses and formats dates exactly like Git does
2. **Format Flexibility**: Handles the wide variety of date formats Git accepts
3. **Relative Dates**: Supports natural language date expressions
4. **Performance**: Provides efficient, allocation-minimizing APIs
5. **Timezone Awareness**: Properly handles and preserves timezone information