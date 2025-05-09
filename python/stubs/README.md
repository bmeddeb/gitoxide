# Gitoxide Type Stubs

This directory contains type stubs for the gitoxide Python bindings. These stubs provide type information for Python IDEs and type checkers like mypy, pyright, or Pylance.

## What Are Type Stubs?

Type stubs are files with a `.pyi` extension that contain type annotations for Python modules. They allow tools to understand the types of function parameters, return values, and class properties, even if the underlying implementation (in this case, written in Rust) doesn't contain Python type hints.

## Benefits

- **Better IDE experience**: Auto-completion, parameter info, and documentation tooltips
- **Static type checking**: Find type errors before runtime
- **Improved code navigation**: Jump to definitions, see references
- **Better refactoring support**: Safely rename symbols

## Usage

The stubs are included with the gitoxide package and should be automatically discovered by type checkers and IDEs. No additional configuration is required.

### IDE Support

These stubs work with:

- Visual Studio Code (with Pylance or Pyright extension)
- PyCharm
- Other IDEs that support PEP 561 type stubs

### Type Checking

Use mypy to check your code:

```bash
mypy your_script.py
```

## Examples

See `../examples/typed_stub_demo.py` for a demonstration of how type annotations are used with gitoxide.

## Structure

- `__init__.pyi`: Type stubs for the main gitoxide module
- `asyncio.pyi`: Type stubs for the gitoxide.asyncio module (when the async feature is enabled)
- `py.typed`: Marker file indicating that this package supports type checking

## Development

If you're adding new features to gitoxide, please update these stubs to match the new functionality.

### Adding a New Method

When adding a new method to a class in the Rust implementation, make sure to:

1. Add appropriate type annotations in the `.pyi` file
2. Include docstrings with parameter and return value descriptions
3. Update overloaded methods if needed (e.g., for supporting both str and Path)