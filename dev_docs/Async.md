## Async initial
Created a separate branch for the async implementation to keep it isolated from the sync version
Set up the directory structure with an async_api module
Implemented AsyncRepository with initial methods mirroring the sync API
Added a working async method that demonstrates how to use Python's asyncio with Rust's tokio
Created an example script that shows how to use the async API
Fixed several issues with PyO3's async bindings
The implementation now correctly:
Uses the Tokio runtime for async operations
Properly converts between Rust futures and Python coroutines
Supports concurrent operations with asyncio.gather()
Maintains a clean API that follows Python conventions

build with Async :
```bash
maturin develop --features async
```

## Next
Async fetch/push/pull operations that don't block the main thread
Async clone for downloading repositories in the background
Progress reporting through async callbacks or streams
More complex concurrent operations that leverage both Rust and Python's async ecosystems
When you're ready to merge this back to the main branch, you'll need to:
Ensure all tests pass
Make sure the async functionality is properly gated behind the feature flag
Update the documentation to cover both sync and async APIs
Consider if any parts of the implementation could be shared between sync and async versions
