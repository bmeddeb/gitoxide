#!/usr/bin/env python3
import sys
import importlib

# Try to import gitoxide
try:
    import gitoxide
    print("Successfully imported gitoxide")
    print("Version:", gitoxide.__version__)
    print("Dir:", dir(gitoxide))
    
    # Try to access the asyncio module
    if hasattr(gitoxide, 'asyncio'):
        print("asyncio module is available")
        print("Dir:", dir(gitoxide.asyncio))
    else:
        print("asyncio module is NOT available")
    
    # Try direct import with importlib
    try:
        asyncio_module = importlib.import_module('gitoxide.asyncio')
        print("Successfully imported gitoxide.asyncio with importlib")
        print("Dir:", dir(asyncio_module))
    except ImportError as e:
        print(f"Failed to import gitoxide.asyncio with importlib: {e}")
    
except ImportError as e:
    print(f"Failed to import gitoxide: {e}")