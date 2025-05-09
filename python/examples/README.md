# Gitoxide Python Examples

This directory contains example scripts demonstrating how to use the Python bindings for gitoxide.

## Examples List

- **unified_test.py**: A comprehensive test script that tests all aspects of the gitoxide Python bindings. Run with `--all` flag to test everything, or use specific flags like `--test-repo` or `--test-objects` to test individual components.

- **basic_usage.py**: Simple example showing basic repository operations.

- **typed_example.py**: Shows how to use gitoxide with proper type annotations for better IDE support.

- **typed_stub_demo.py**: Demonstrates how the type stubs work (demonstration only).

- **async_repository.py**: Example of using the async repository interface.

- **async_wrapper.py**: Shows how to wrap synchronous operations in an async interface.

- **inspect_module.py**: Simple script to inspect the module structure.

## Running Examples

Most examples can be run directly:

```bash
python examples/unified_test.py --all  # Run all tests
python examples/basic_usage.py         # Run basic usage example
```

## Adding New Examples

When adding new examples, please:

1. Include proper docstrings
2. Add error handling
3. Make the script runnable directly with the Python interpreter
4. Update this README.md with a description of your example