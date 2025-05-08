# gix-trace Usage Guide

This document provides detailed usage patterns, examples, and scenarios for using the `gix-trace` crate in different contexts. It demonstrates how tracing can be applied to various use cases within the gitoxide ecosystem.

## Use Cases

### 1. Performance Profiling and Optimization

**Use Case**: Analyzing and optimizing performance-critical operations in git operations

**Users**:
- Gitoxide core developers optimizing repository operations
- Application developers building performance-sensitive tools on gitoxide
- CI/CD pipeline maintainers monitoring git operation performance

**Example**:
```rust
pub fn clone_repository(url: &str, path: &Path) -> Result<Repository, Error> {
    let span = gix_trace::coarse!("clone_repository", 
        url = url, 
        target_path = ?path
    );
    
    // Initialization stage
    let init_span = gix_trace::detail!("init_repository");
    let mut repo = Repository::init(path)?;
    init_span.record("repo_id", repo.id().to_string());
    drop(init_span);
    
    // Fetch stage with detailed timing
    {
        let fetch_span = gix_trace::detail!("fetch_remote_data");
        let remote = repo.remote_add("origin", url)?;
        let fetch_result = remote.fetch()?;
        
        // Record detailed statistics about the fetch
        fetch_span.record("objects_transferred", fetch_result.objects_transferred);
        fetch_span.record("bytes_transferred", fetch_result.bytes_transferred);
        // The span is automatically dropped at the end of this block
    }
    
    // Checkout stage
    let checkout_span = gix_trace::detail!("checkout_head");
    repo.checkout_head()?;
    drop(checkout_span);
    
    span.record("success", true);
    Ok(repo)
}
```

### 2. Debugging Complex Git Operations

**Use Case**: Troubleshooting unexpected behavior in git operations

**Users**:
- Developers debugging edge cases in git repository interactions
- Support engineers diagnosing issues in production systems
- Test engineers investigating test failures

**Example**:
```rust
pub fn merge_branches(repo: &Repository, source: &str, target: &str) -> Result<(), Error> {
    let span = gix_trace::coarse!("merge_branches", 
        source = source, 
        target = target,
        repo_path = ?repo.path()
    );
    
    // Resolve references
    let source_ref = match repo.find_reference(source) {
        Ok(r) => {
            span.record("source_ref_found", true);
            r
        },
        Err(e) => {
            gix_trace::error!("Failed to resolve source reference: {}", e);
            span.record("source_ref_found", false);
            return Err(e.into());
        }
    };
    
    let target_ref = match repo.find_reference(target) {
        Ok(r) => {
            span.record("target_ref_found", true);
            r
        },
        Err(e) => {
            gix_trace::error!("Failed to resolve target reference: {}", e);
            span.record("target_ref_found", false);
            return Err(e.into());
        }
    };
    
    // Log reference details
    gix_trace::info!(
        "Merging references",
        source_commit = ?source_ref.peel_to_commit()?.id(),
        target_commit = ?target_ref.peel_to_commit()?.id()
    );
    
    // Perform the merge
    let result = gix_trace::detail!("perform_merge").into_scope(|| {
        let source_commit = source_ref.peel_to_commit()?;
        let target_commit = target_ref.peel_to_commit()?;
        
        // Check for conflicts potential
        if let Some(merge_base) = repo.merge_base(&source_commit, &target_commit)? {
            gix_trace::debug!("Merge base found", base = ?merge_base);
        } else {
            gix_trace::warn!("No merge base found between commits");
        }
        
        // Actually perform merge
        repo.merge(&source_commit, &target_commit)
    });
    
    // Record the outcome
    match &result {
        Ok(_) => span.record("success", true),
        Err(e) => {
            span.record("success", false);
            span.record("error_type", e.to_string());
            gix_trace::error!("Merge failed: {}", e);
        }
    }
    
    result
}
```

### 3. Production Monitoring

**Use Case**: Monitoring git operations in deployed applications

**Users**:
- SRE teams monitoring production systems
- Application developers building observability tools
- System administrators tracking repository operations

**Example**:
```rust
pub fn process_push_hook(repo: &Repository, ref_updates: &[RefUpdate]) -> Result<(), Error> {
    let span = gix_trace::coarse!("process_push_hook", 
        repo_name = repo.name(),
        update_count = ref_updates.len()
    );
    
    // Track stats for monitoring
    let mut added_objects = 0;
    let mut updated_refs = 0;
    
    for update in ref_updates {
        let ref_span = gix_trace::detail!("process_ref_update", 
            ref_name = update.name,
            old_oid = ?update.old_id,
            new_oid = ?update.new_id,
            is_deletion = update.old_id.is_null()
        );
        
        // Process received objects
        if !update.new_id.is_null() {
            if let Some(objects) = update.objects.as_ref() {
                // Count received objects for metrics
                added_objects += objects.len();
                
                gix_trace::info!(
                    "Processing objects for ref",
                    ref_name = update.name,
                    object_count = objects.len()
                );
                
                // Process objects
                for obj in objects {
                    gix_trace::detail!("store_object",
                        object_id = ?obj.id(),
                        object_type = ?obj.kind()
                    ).into_scope(|| {
                        repo.object_database().write(obj)?;
                        Result::<_, Error>::Ok(())
                    })?;
                }
            }
            
            // Update the reference
            gix_trace::detail!("update_reference").into_scope(|| {
                repo.references_mut().update(update.name, update.new_id, &format!("push from hook"))?;
                updated_refs += 1;
                Result::<_, Error>::Ok(())
            })?;
        }
        
        drop(ref_span);
    }
    
    // Record final metrics for monitoring systems
    span.record("added_objects", added_objects);
    span.record("updated_refs", updated_refs);
    
    gix_trace::info!(
        "Push hook processed successfully",
        added_objects,
        updated_refs,
        duration_ms = ?std::time::Instant::now().duration_since(std::time::Instant::now()).as_millis()
    );
    
    Ok(())
}
```

### 4. Educational and Development Tooling

**Use Case**: Understanding git internals through observation

**Users**:
- Developers learning git internals
- Educators teaching git concepts
- Tool developers creating git visualization tools

**Example**:
```rust
pub fn explain_repository_structure(repo_path: &Path) -> Result<RepositoryInsights, Error> {
    let span = gix_trace::coarse!("explain_repository", 
        path = ?repo_path
    );
    
    // Open and analyze repository
    let repo = gix::open(repo_path)?;
    
    // Gather ref information
    let ref_span = gix_trace::detail!("analyze_references");
    let refs = repo.references()?;
    let ref_count = refs.count();
    ref_span.record("count", ref_count);
    drop(ref_span);
    
    // Analyze objects
    let object_span = gix_trace::detail!("analyze_objects");
    let mut commit_count = 0;
    let mut tree_count = 0;
    let mut blob_count = 0;
    let mut tag_count = 0;
    
    // Walk objects for analysis
    for obj_result in repo.objects()?.iter() {
        let obj = obj_result?;
        match obj.kind() {
            gix::object::Kind::Commit => commit_count += 1,
            gix::object::Kind::Tree => tree_count += 1,
            gix::object::Kind::Blob => blob_count += 1,
            gix::object::Kind::Tag => tag_count += 1,
        }
        
        // Emit detailed trace for each object
        gix_trace::debug!(
            "Found object",
            id = ?obj.id(),
            kind = ?obj.kind(),
            size = obj.data().len()
        );
    }
    
    object_span.record("commit_count", commit_count);
    object_span.record("tree_count", tree_count);
    object_span.record("blob_count", blob_count);
    object_span.record("tag_count", tag_count);
    drop(object_span);
    
    // Emit summary information
    gix_trace::info!(
        "Repository analysis complete",
        total_refs = ref_count,
        total_objects = commit_count + tree_count + blob_count + tag_count,
        commit_count,
        tree_count,
        blob_count,
        tag_count
    );
    
    // Create and return insights
    let insights = RepositoryInsights {
        ref_count,
        commit_count,
        tree_count,
        blob_count,
        tag_count,
    };
    
    span.record("success", true);
    Ok(insights)
}
```

## Detailed Use Case Examples

### Git Server Implementation

**Scenario**: Building a high-performance git server that needs observability

```rust
pub struct GitServer {
    repositories: HashMap<String, Repository>,
    active_connections: Arc<AtomicUsize>,
}

impl GitServer {
    pub fn handle_fetch_request(&self, request: FetchRequest) -> Result<FetchResponse, ServerError> {
        let span = gix_trace::coarse!("git_server_fetch",
            repo = request.repo_name,
            client_ip = request.client_address,
            protocol = request.protocol_version
        );
        
        // Update server metrics
        let connection_count = self.active_connections.fetch_add(1, Ordering::SeqCst);
        span.record("active_connections", connection_count + 1);
        
        // Start the fetch operation
        let result = gix_trace::detail!("process_fetch").into_scope(|| {
            // Find the repository
            let repo = match self.repositories.get(&request.repo_name) {
                Some(r) => r,
                None => {
                    gix_trace::error!("Repository not found", repo = request.repo_name);
                    return Err(ServerError::RepositoryNotFound);
                }
            };
            
            // Check permissions
            gix_trace::detail!("check_permissions", 
                user = ?request.user_id,
                access_type = "fetch",
                refs = ?request.ref_specs
            ).into_scope(|| {
                if !self.check_permissions(&request) {
                    gix_trace::warn!("Permission denied", 
                        user = ?request.user_id,
                        repo = request.repo_name
                    );
                    return Err(ServerError::PermissionDenied);
                }
                Ok(())
            })?;
            
            // Process wanted refs
            let wanted_refs = gix_trace::detail!("resolve_wanted_refs").into_scope(|| {
                let mut refs = Vec::new();
                for refspec in &request.ref_specs {
                    match repo.resolve_refspec(refspec) {
                        Ok(resolved) => refs.push(resolved),
                        Err(e) => {
                            gix_trace::warn!("Could not resolve refspec", 
                                refspec = refspec, 
                                error = ?e
                            );
                        }
                    }
                }
                
                gix_trace::debug!("Resolved references", count = refs.len());
                Ok(refs)
            })?;
            
            // Perform the pack negotiation
            let pack_data = gix_trace::detail!("pack_negotiation", 
                client_caps = ?request.capabilities,
                wanted_ref_count = wanted_refs.len()
            ).into_scope(|| {
                // Negotiate pack contents
                let negotiator = repo.pack_negotiator()?;
                let pack = negotiator.create_pack(
                    wanted_refs, 
                    request.have_commits.as_deref()
                )?;
                
                gix_trace::info!("Pack created", 
                    size_bytes = pack.size(),
                    object_count = pack.object_count()
                );
                
                Ok(pack)
            })?;
            
            // Return the response
            Ok(FetchResponse {
                pack_data,
                ref_updates: wanted_refs,
                server_capabilities: self.capabilities(),
            })
        });
        
        // Always decrement the connection counter
        self.active_connections.fetch_sub(1, Ordering::SeqCst);
        
        // Record outcome
        match &result {
            Ok(resp) => {
                span.record("success", true);
                span.record("bytes_sent", resp.pack_data.size());
                span.record("refs_sent", resp.ref_updates.len());
            },
            Err(e) => {
                span.record("success", false);
                span.record("error", format!("{:?}", e));
                gix_trace::error!("Fetch operation failed", error = ?e);
            }
        }
        
        result
    }
}
```

### Git CLI Tool Development

**Scenario**: Creating a custom git CLI with performance insights

```rust
pub struct GitCli {
    repo: Option<Repository>,
    config: Config,
}

impl GitCli {
    pub fn execute_command(&mut self, args: &[String]) -> Result<(), CliError> {
        let cmd_name = args.first().unwrap_or(&String::from("help"));
        
        let span = gix_trace::coarse!("git_cli_command", 
            command = cmd_name,
            arg_count = args.len() - 1,
            cwd = ?std::env::current_dir()
        );
        
        // Handle top-level commands
        match cmd_name.as_str() {
            "clone" => {
                if args.len() < 2 {
                    return Err(CliError::InvalidArgs("URL required".into()));
                }
                
                let url = &args[1];
                let target = args.get(2).map(Path::new).unwrap_or_else(|| {
                    // Default to last URL segment
                    Path::new(url.split('/').last().unwrap_or("repo"))
                });
                
                gix_trace::detail!("executing_clone",
                    url = url,
                    target = ?target
                ).into_scope(|| {
                    // Initialize progress reporting
                    let progress = gix_trace::detail!("progress_reporting").into_scope(|| {
                        let p = Progress::new();
                        
                        // Emit progress events
                        p.on_update(|stats| {
                            gix_trace::debug!(
                                "Clone progress",
                                objects_total = stats.total_objects,
                                objects_processed = stats.processed_objects,
                                bytes_transferred = stats.bytes_transferred,
                                percent_complete = ((stats.processed_objects as f64 / stats.total_objects as f64) * 100.0) as u8
                            );
                        });
                        
                        Ok(p)
                    })?;
                    
                    // Perform actual clone with progress
                    let result = gix::clone(url, target)
                        .with_progress(progress)
                        .run();
                    
                    match &result {
                        Ok(repo) => {
                            gix_trace::info!("Clone completed successfully",
                                elapsed_ms = ?std::time::Instant::now().elapsed().as_millis()
                            );
                            self.repo = Some(repo.clone());
                        },
                        Err(e) => {
                            gix_trace::error!("Clone failed", error = ?e);
                        }
                    }
                    
                    result.map_err(|e| e.into())
                })?;
            },
            "status" => {
                let repo = self.ensure_repository()?;
                
                gix_trace::detail!("executing_status").into_scope(|| {
                    let status = repo.status()?;
                    
                    // Log interesting information about repository state
                    gix_trace::info!(
                        "Repository status",
                        index_changes = status.index_changes().count(),
                        worktree_changes = status.worktree_changes().count(),
                        untracked_files = status.untracked_files().count()
                    );
                    
                    // Print status to user
                    println!("Status:");
                    for change in status.index_changes() {
                        println!("  {}: {}", change.status(), change.path().display());
                    }
                    // Other status output...
                    
                    Ok(())
                })?;
            },
            // Other commands...
            _ => {
                gix_trace::warn!("Unknown command", command = cmd_name);
                return Err(CliError::UnknownCommand(cmd_name.to_string()));
            }
        }
        
        span.record("success", true);
        span.record("duration_ms", std::time::Instant::now().elapsed().as_millis() as u64);
        Ok(())
    }
    
    fn ensure_repository(&self) -> Result<&Repository, CliError> {
        match &self.repo {
            Some(repo) => Ok(repo),
            None => {
                gix_trace::error!("No repository found in current context");
                Err(CliError::NoRepository)
            }
        }
    }
}
```

## Intended User Profiles

### Gitoxide Core Developers
- Need deep insights into performance characteristics
- Require zero-overhead instrumentation
- Want to identify bottlenecks in git operations

### Application Developers
- Building tools on top of gitoxide
- Need to understand how their code interacts with git
- Want to monitor git operations in their applications

### DevOps/SRE Teams
- Monitoring production git operations
- Tracking performance metrics over time
- Setting up alerts for abnormal git behavior

### Quality Assurance Engineers
- Verifying performance characteristics
- Reproducing and diagnosing issues
- Creating performance baselines

### Technical Educators
- Demonstrating git internals
- Creating visualizations of git operations
- Developing interactive learning tools

## Feature Selection Guide

| Use Case | Recommended Features | Notes |
|----------|----------------------|-------|
| Production monitoring | `tracing` | Basic coarse-grained tracing |
| Performance optimization | `tracing`, `tracing-detail` | Full detailed tracing |
| Debug builds | `tracing`, `tracing-detail` | Maximum instrumentation |
| Release builds | None or `tracing` | Minimal or no overhead |
| Testing/CI | `tracing`, `tracing-detail` | Full instrumentation |

## Advanced Usage Patterns

### Correlation IDs

```rust
fn handle_request(request: Request) {
    let span = gix_trace::coarse!("request",
        request_id = request.id,
        user = request.user
    );
    
    // All child operations are connected to the parent span
    span.into_scope(|| {
        let repo = open_repository(&request.repo_path)?;
        process_operation(repo, &request.operation)?;
        record_audit_log(&request);
        Ok(())
    })
}
```

### Sampling High-Volume Operations

```rust
fn log_index_operation(op: IndexOp) {
    // Only trace expensive operations
    if op.is_expensive() {
        gix_trace::detail!("index_operation", op = ?op);
    }
    
    // Or sample based on a percentage
    if rand::random::<f32>() < 0.01 {  // 1% sampling
        gix_trace::detail!("sampled_operation", op = ?op);
    }
}
```

### Conditional Tracing

```rust
fn expensive_operation(input: Input) {
    // Check if detailed tracing would be used before doing expensive debug work
    if gix_trace::MAX_LEVEL >= gix_trace::Level::Detail {
        let debug_data = input.generate_expensive_debug_info();
        gix_trace::detail!("operation_details", 
            debug_data = ?debug_data
        );
    }
    
    // Continue with normal operation
    // ...
}
```

### Custom Macro Wrappers

```rust
/// Custom macro to standardize spans for git object operations
macro_rules! object_span {
    ($op:expr, $obj:expr) => {
        gix_trace::detail!(
            $op,
            object_id = ?$obj.id(),
            object_type = ?$obj.kind(),
            object_size = $obj.size()
        )
    };
}

fn process_object(obj: &Object) -> Result<(), Error> {
    // Use our custom macro
    let span = object_span!("process_git_object", obj);
    
    // Do work
    // ...
    
    span.record("success", true);
    Ok(())
}
```

### Distributed Tracing Integration

```rust
fn process_hook_payload(payload: Vec<u8>, trace_context: Option<String>) {
    // Connect to external distributed tracing system
    let span = if let Some(ctx) = trace_context {
        gix_trace::coarse!("git_hook_process", 
            trace_parent = ctx,
            payload_size = payload.len()
        )
    } else {
        gix_trace::coarse!("git_hook_process", 
            payload_size = payload.len()
        )
    };
    
    // Process hook with distributed trace context
    // ...
}
```

This expanded documentation provides a comprehensive view of how `gix-trace` can be utilized across different scenarios and by different types of users in the gitoxide ecosystem.