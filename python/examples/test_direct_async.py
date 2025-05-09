#!/usr/bin/env python3
"""
Test direct access to AsyncRepository.
"""

import asyncio
import gitoxide

print("Gitoxide version:", gitoxide.__version__)

try:
    # Import the AsyncRepository directly if available
    from gitoxide.asyncio import Repository as AsyncRepository
    print("Successfully imported AsyncRepository")
except ImportError as e:
    print(f"Failed to import AsyncRepository: {e}")
    
    # Try to access it directly from the module
    if hasattr(gitoxide, 'asyncio'):
        print("gitoxide.asyncio exists")
        print("Contents:", dir(gitoxide.asyncio))
        if hasattr(gitoxide.asyncio, 'Repository'):
            print("Found AsyncRepository!")
            AsyncRepository = gitoxide.asyncio.Repository
        else:
            print("No Repository in asyncio")
    else:
        print("No asyncio module found")