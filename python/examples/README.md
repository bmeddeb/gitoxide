# Gitoxide Python Examples

This directory contains example scripts demonstrating how to use the gitoxide Python bindings.

## Examples

### Basic Usage (`basic_usage.py`)

Demonstrates the fundamental operations with gitoxide:
- Opening existing repositories
- Creating new repositories
- Accessing basic repository properties

```bash
python basic_usage.py
```

### Repository Information Tool (`repository_info.py`)

A more complete example that shows how to build a command-line tool to display information about a Git repository:
- Detailed repository information
- HEAD and branch information
- Error handling

```bash
# Check the current directory
python repository_info.py

# Check a specific repository
python repository_info.py /path/to/repository
```

## Running the Examples

Make sure you have the gitoxide Python bindings installed:

```bash
cd ../  # Go to the python directory
maturin develop
cd examples/
```

Then run any of the example scripts.