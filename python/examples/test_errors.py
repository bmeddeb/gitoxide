#!/usr/bin/env python3
"""
Test script to verify that all error types are accessible from Python.
"""

import gitoxide
import inspect
import sys


def list_error_types():
    """List all error types in the gitoxide module."""
    error_types = []

    # Directly check for expected error types
    expected_error_names = [
        "GitoxideError",
        "RepositoryError",
        "ObjectError",
        "ReferenceError",
        "ConfigError",
        "IndexError",
        "DiffError",
        "TraverseError",
        "WorktreeError",
        "RevisionError",
        "RemoteError",
        "TransportError",
        "ProtocolError",
        "PackError",
        "FSError"
    ]

    for name in expected_error_names:
        if hasattr(gitoxide, name):
            error_type = getattr(gitoxide, name)
            if isinstance(error_type, type) and issubclass(error_type, Exception):
                error_types.append(error_type)

    return error_types


def verify_error_hierarchy(error_types):
    """Verify that the error hierarchy is set up correctly."""
    # Check that we have error types to test
    if not error_types:
        print("No error types found!")
        return False

    # GitoxideError should be the base error type
    base_error = gitoxide.GitoxideError

    for error_type in error_types:
        if error_type is not base_error:
            # All other errors should be subclasses of GitoxideError
            if not issubclass(error_type, base_error):
                print(
                    f"ERROR: {error_type.__name__} is not a subclass of GitoxideError")
                return False

    return True


def main():
    print(f"Gitoxide version: {gitoxide.__version__}")
    print()

    # List all error types
    error_types = list_error_types()
    print(f"Found {len(error_types)} error types:")

    for error_type in sorted(error_types, key=lambda t: t.__name__):
        print(f"  - {error_type.__name__}")

    # Verify error hierarchy
    if verify_error_hierarchy(error_types):
        print("\nError hierarchy is set up correctly.")
    else:
        print("\nError hierarchy has issues.")
        return 1

    # Test raising and catching errors
    error_count = 0
    for error_type in error_types:
        try:
            # Create and raise an error
            raise error_type(f"Test {error_type.__name__}")
        except gitoxide.GitoxideError as e:
            error_count += 1
            print(f"\nSuccessfully caught {error_type.__name__}: {e}")

    print(f"\nSuccessfully tested {error_count} error types.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
