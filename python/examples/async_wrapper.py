#!/usr/bin/env python
"""
A wrapper that demonstrates how to use the async Repository.
"""

import asyncio

# Basic wrapper over the async implementation
try:
    import gitoxide
    # If building with --features=async, the AsyncRepository should be available
    if hasattr(gitoxide, 'AsyncRepository'):
        AsyncRepository = gitoxide.AsyncRepository
        ASYNC_AVAILABLE = gitoxide.ASYNC_AVAILABLE if hasattr(gitoxide, 'ASYNC_AVAILABLE') else True
    else:
        ASYNC_AVAILABLE = False
except ImportError:
    ASYNC_AVAILABLE = False

if not ASYNC_AVAILABLE:
    print("AsyncRepository is not available. Please build with --features=async")
    exit(1)

async def main():
    """Demonstrate how to use the AsyncRepository."""
    import tempfile
    import os
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Creating repository in {temp_dir}")
        
        # Initialize a new repository
        repo = await AsyncRepository.init(temp_dir, False)
        print(f"Repository initialized at {temp_dir}")
        
        # Get basic repository information
        print(f"Git directory: {repo.git_dir()}")
        print(f"Work directory: {repo.work_dir()}")
        print(f"Is bare: {repo.is_bare()}")
        print(f"Is shallow: {repo.is_shallow()}")
        print(f"Object hash: {repo.object_hash()}")
        
        # Try an async method
        try:
            head = await repo.head()
            print(f"HEAD: {head}")
        except Exception as e:
            print(f"Error getting HEAD: {e}")
        
        # Get shallow commits
        shallow_commits = await repo.shallow_commits()
        print(f"Shallow commits: {shallow_commits}")
        
        # Try to create a reference
        try:
            ref = await repo.create_reference("refs/heads/test-branch", "HEAD", True, False)
            print(f"Created reference: {ref.name} -> {ref.target}")
        except Exception as e:
            print(f"Failed to create reference: {e}")

if __name__ == "__main__":
    asyncio.run(main())