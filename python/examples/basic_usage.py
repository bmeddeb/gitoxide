#!/usr/bin/env python3
"""
Basic usage examples for gitoxide.
"""

import os
import tempfile
import shutil

def sync_example():
    """Example using the synchronous API."""
    from gitoxide.sync import Repository
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize a new repository
        repo_path = os.path.join(temp_dir, "test_repo")
        repo = Repository.init(repo_path)
        
        # Print repository information
        print(f"Repository path: {repo.path}")
        print(f"Working directory: {repo.workdir}")
        print(f"Is bare: {repo.is_bare}")
        print(f"Is empty: {repo.is_empty}")
        
        # Open an existing repository
        reopened_repo = Repository.open(repo_path)
        print(f"Reopened repository: {reopened_repo}")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

async def async_example():
    """Example using the asynchronous API."""
    import asyncio
    from gitoxide.asyncio import Repository
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize a new repository
        repo_path = os.path.join(temp_dir, "test_repo")
        repo = await Repository.init(repo_path)
        
        # Print repository information
        print(f"Repository path: {await repo.path}")
        print(f"Working directory: {await repo.workdir}")
        print(f"Is bare: {await repo.is_bare}")
        print(f"Is empty: {await repo.is_empty}")
        
        # Open an existing repository
        reopened_repo = await Repository.open(repo_path)
        print(f"Reopened repository: {reopened_repo}")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    print("Running synchronous example:")
    sync_example()
    
    print("\nRunning asynchronous example:")
    import asyncio
    asyncio.run(async_example())