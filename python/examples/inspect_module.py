#!/usr/bin/env python3
"""
Inspect the gitoxide module to see what's available.
"""

import sys
import importlib.util

print("Python version:", sys.version)

# Try to import gitoxide
try:
    import gitoxide
    print("\nSuccessfully imported gitoxide")
    print("Version:", gitoxide.__version__)
    print("\nModule attributes:")
    for attr in dir(gitoxide):
        if not attr.startswith('__'):
            print(f"  - {attr}: {type(getattr(gitoxide, attr))}")
except ImportError as e:
    print(f"Failed to import gitoxide: {e}")