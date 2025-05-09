#!/usr/bin/env python3
"""
Test the async API.
"""

import asyncio
import gitoxide

print("Gitoxide version:", gitoxide.__version__)
print("Has asyncio module:", hasattr(gitoxide, 'asyncio'))

if hasattr(gitoxide, 'asyncio'):
    print("asyncio attributes:", dir(gitoxide.asyncio))
    
    async def test_async_repo():
        # Try to use the async API
        try:
            repo = await gitoxide.asyncio.Repository.open('.')
            print("Successfully opened repository using async API")
            print(f"Git directory: {repo.git_dir()}")
            print(f"Is bare: {repo.is_bare()}")
            print(f"Object hash: {repo.object_hash()}")
            
            # Test async method
            try:
                head = await repo.head()
                print(f"HEAD: {head}")
            except Exception as e:
                print(f"Error getting HEAD: {e}")
                
            # Test shallow_commits method
            try:
                commits = await repo.shallow_commits()
                print(f"Shallow commits: {commits}")
            except Exception as e:
                print(f"Error getting shallow commits: {e}")
                
        except Exception as e:
            print(f"Error opening repository: {e}")
    
    # Run the async function
    asyncio.run(test_async_repo())
else:
    print("Async API not available. Make sure to build with --features async")