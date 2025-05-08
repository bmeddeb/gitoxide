# gix-actor Use Cases

## Intended Audience

- **Git Tool Developers**: Building Git extensions, tools, or alternative clients
- **Repository Analysis Tools**: Applications that analyze Git repository metadata
- **Git Hosting Platforms**: Services that display Git commit information
- **Version Control System Developers**: Teams working on Git-compatible version control systems

## Use Cases

### 1. Commit Authorship Analysis

**Problem**: Analyzing contribution patterns in a Git repository requires extracting and processing author information.

**Solution**: Use gix-actor to parse and analyze commit signatures:

```rust
use gix_actor::SignatureRef;
use std::collections::HashMap;

fn analyze_author_contributions(
    commit_signatures: &[&[u8]]
) -> HashMap<String, usize> {
    let mut contributions = HashMap::new();
    
    for sig_bytes in commit_signatures {
        if let Ok(signature) = SignatureRef::from_bytes::<()>(sig_bytes) {
            // Normalize author name and email by trimming whitespace
            let trimmed = signature.trim();
            let author_id = format!(
                "{} <{}>",
                trimmed.name.to_str().unwrap_or("?"),
                trimmed.email.to_str().unwrap_or("?")
            );
            
            // Count contributions
            *contributions.entry(author_id).or_insert(0) += 1;
        }
    }
    
    contributions
}
```

**Result**: Accurate contribution statistics even with varying whitespace or formatting in author information.

### 2. Identity Normalization

**Problem**: Git authors may appear under different variations of their name and email due to inconsistent configurations.

**Solution**: Normalize Git identities to establish consistent author attribution:

```rust
use gix_actor::{IdentityRef, Identity};
use bstr::ByteSlice;

fn normalize_identity(identity_bytes: &[u8]) -> Result<Identity, String> {
    // Parse the identity
    let identity = IdentityRef::from_bytes::<()>(identity_bytes)
        .map_err(|e| format!("Invalid identity format: {:?}", e))?;
    
    // Trim whitespace and normalize capitalization
    let name = identity.name.trim().to_str()
        .map_err(|_| "Invalid UTF-8 in name")?
        .to_lowercase();
    
    let email = identity.email.trim().to_str()
        .map_err(|_| "Invalid UTF-8 in email")?
        .to_lowercase();
    
    // Create normalized identity
    Ok(Identity {
        name: name.into(),
        email: email.into(),
    })
}
```

**Result**: Consistent identity representation across varying Git configurations.

### 3. Commit Creation

**Problem**: Creating valid Git commits requires properly formatted author and committer information.

**Solution**: Use the Signature type to create valid Git signatures:

```rust
use gix_actor::Signature;
use gix_date::Time;

fn create_commit_signatures(
    author_name: &str,
    author_email: &str,
    committer_name: &str,
    committer_email: &str
) -> Result<(Signature, Signature), Box<dyn std::error::Error>> {
    // Current time in UTC
    let now = Time::now_utc();
    
    // Create author signature
    let author = Signature {
        name: author_name.into(),
        email: author_email.into(),
        time: now,
    };
    
    // Create committer signature (often the same person, but can differ)
    let committer = Signature {
        name: committer_name.into(),
        email: committer_email.into(),
        time: now,
    };
    
    // Validate the signatures by attempting to serialize them
    let mut buf = Vec::new();
    author.write_to(&mut buf)?;
    buf.clear();
    committer.write_to(&mut buf)?;
    
    Ok((author, committer))
}
```

**Result**: Valid Git signatures for commit creation that comply with Git's format requirements.

### 4. Author Validation

**Problem**: Git hosting platforms need to validate user-provided author information before accepting commits.

**Solution**: Use gix-actor's validation checks to ensure compliance with Git's format requirements:

```rust
use gix_actor::Identity;

enum ValidationError {
    InvalidChars,
    MissingName,
    MissingEmail,
}

fn validate_author_info(
    name: &str,
    email: &str
) -> Result<(), ValidationError> {
    // Check for required fields
    if name.trim().is_empty() {
        return Err(ValidationError::MissingName);
    }
    
    if email.trim().is_empty() {
        return Err(ValidationError::MissingEmail);
    }
    
    // Create identity for validation
    let identity = Identity {
        name: name.into(),
        email: email.into(),
    };
    
    // Try serializing to validate format
    let mut buf = Vec::new();
    if identity.write_to(&mut buf).is_err() {
        return Err(ValidationError::InvalidChars);
    }
    
    Ok(())
}
```

**Result**: Prevents invalid commit metadata that would cause issues in Git repositories.

### 5. Repository Collaboration Analysis

**Problem**: Analyzing collaborative patterns in a repository requires understanding the timestamp patterns of contributions.

**Solution**: Extract and analyze timestamp information from commit signatures:

```rust
use gix_actor::SignatureRef;
use gix_date::Time;
use std::collections::HashMap;

struct CommitTimingAnalysis {
    commits_per_hour: [usize; 24],
    commits_per_day: [usize; 7],
    commits_per_timezone: HashMap<i32, usize>,
}

fn analyze_commit_timing(
    commit_signatures: &[&[u8]]
) -> CommitTimingAnalysis {
    let mut analysis = CommitTimingAnalysis {
        commits_per_hour: [0; 24],
        commits_per_day: [0; 7],
        commits_per_timezone: HashMap::new(),
    };
    
    for sig_bytes in commit_signatures {
        if let Ok(signature) = SignatureRef::from_bytes::<()>(sig_bytes) {
            if let Ok(time) = signature.time() {
                // Use gix-date functionality to extract datetime components
                let datetime = time_to_datetime(time);
                
                // Record hour of day (0-23)
                if let Some(hour) = datetime.hour {
                    analysis.commits_per_hour[hour as usize] += 1;
                }
                
                // Record day of week (0-6, where 0 is Sunday)
                if let Some(day) = datetime.day_of_week {
                    analysis.commits_per_day[day as usize] += 1;
                }
                
                // Record timezone
                *analysis.commits_per_timezone.entry(time.offset).or_insert(0) += 1;
            }
        }
    }
    
    analysis
}

// Helper function to convert Time to datetime components
fn time_to_datetime(time: Time) -> DateTimeComponents {
    // In a real implementation, this would use proper date/time libraries
    // to convert Unix timestamp to datetime components
    DateTimeComponents {
        hour: Some(12), // Placeholder implementation
        day_of_week: Some(0),
    }
}

struct DateTimeComponents {
    hour: Option<u8>,
    day_of_week: Option<u8>,
}
```

**Result**: Insights into contribution patterns, work schedules, and global distribution of contributors.

### 6. Historical Commit Verification

**Problem**: Verifying the integrity of repository history includes checking commit signatures for consistency.

**Solution**: Parse and validate signatures from historical commits:

```rust
use gix_actor::SignatureRef;
use gix_date::Time;

struct SignatureVerificationResult {
    valid_format: bool,
    future_dated: bool,
    too_old: bool,
}

fn verify_commit_signature(
    signature_bytes: &[u8],
    reference_time: Time
) -> SignatureVerificationResult {
    let mut result = SignatureVerificationResult {
        valid_format: false,
        future_dated: false,
        too_old: false,
    };
    
    // Try to parse the signature
    if let Ok(signature) = SignatureRef::from_bytes::<()>(signature_bytes) {
        result.valid_format = true;
        
        // Check timestamp (if parseable)
        if let Ok(time) = signature.time() {
            // Check if commit is dated in the future
            if time.seconds > reference_time.seconds {
                result.future_dated = true;
            }
            
            // Check if commit is suspiciously old (e.g., before Git existed)
            if time.seconds < 946684800 { // Jan 1, 2000
                result.too_old = true;
            }
        }
    }
    
    result
}
```

**Result**: Detection of potentially tampered or incorrectly dated commits in a repository's history.

## Key Benefits

1. **Format Compliance**: Ensures correct formatting according to Git's specifications
2. **Efficient Parsing**: Minimizes allocations when processing large repositories
3. **Flexibility**: Provides both immutable references and mutable owned versions
4. **Data Integrity**: Validates author/committer information to prevent corruption
5. **Comprehensive Support**: Handles all aspects of Git actor information including timestamps