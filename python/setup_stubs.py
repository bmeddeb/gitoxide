#!/usr/bin/env python3
"""
Setup script for gitoxide stubs.

This script installs the gitoxide stubs for mypy and other type checkers.
"""

import os
import shutil
import site
import sys
from pathlib import Path

def main():
    """Install gitoxide stubs to the site-packages directory."""
    # Determine the site-packages directory
    for site_dir in site.getsitepackages():
        if site_dir.endswith('site-packages'):
            dest_dir = Path(site_dir) / 'gitoxide-stubs'
            break
    else:
        print("Could not find site-packages directory")
        return 1

    # Create destination directory if it doesn't exist
    if not dest_dir.exists():
        os.makedirs(dest_dir, exist_ok=True)
        print(f"Created directory: {dest_dir}")

    # Copy the stubs
    source_dir = Path(__file__).parent / 'stubs' / 'gitoxide'
    if not source_dir.exists():
        print(f"Stub source directory not found: {source_dir}")
        return 1

    # Create package structure
    os.makedirs(dest_dir / 'gitoxide', exist_ok=True)

    # Copy stub files
    for file in source_dir.glob('*.pyi'):
        shutil.copy2(file, dest_dir / 'gitoxide')
        print(f"Copied: {file.name}")

    # Copy py.typed file
    py_typed = source_dir / 'py.typed'
    if py_typed.exists():
        shutil.copy2(py_typed, dest_dir / 'gitoxide')
        print("Copied: py.typed")

    # Create package-level __init__.py
    with open(dest_dir / '__init__.py', 'w') as f:
        f.write('# gitoxide type stubs\n')

    # Create package-level py.typed
    with open(dest_dir / 'py.typed', 'w') as f:
        pass

    print(f"Successfully installed gitoxide stubs to {dest_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())