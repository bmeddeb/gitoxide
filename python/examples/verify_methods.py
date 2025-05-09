#!/usr/bin/env python3
"""
Unified test script for gitoxide Python bindings.

This script combines functionality from various test scripts to provide
a comprehensive test of the gitoxide Python bindings.
"""

import os
import sys
import tempfile
import subprocess
import argparse
import importlib
from typing import Optional, Dict, Any, List


def print_separator(char='-', length=70):
    """Print a separator line."""
    print(char * length)


def test_basic_import():
    """Test basic import of gitoxide."""
    print_separator('=')
    print("TESTING BASIC IMPORT")
    print_separator('=')

    try:
        import gitoxide
        print("Successfully imported gitoxide")
        print(f"Version: {gitoxide.__version__}")
        print(f"Available attributes: {', '.join(sorted(dir(gitoxide)))}")

        # Check for asyncio module
        if hasattr(gitoxide, 'asyncio'):
            print("\nAsyncio module is available")
            print(
                f"Asyncio attributes: {', '.join(sorted(dir(gitoxide.asyncio)))}")
        else:
            print("\nAsyncio module is NOT available")

        # Try direct import with importlib
        try:
            asyncio_module = importlib.import_module('gitoxide.asyncio')
            print("\nSuccessfully imported gitoxide.asyncio with importlib")
            print(
                f"Available attributes: {', '.join(sorted(dir(asyncio_module)))}")
        except ImportError as e:
            print(f"\nFailed to import gitoxide.asyncio with importlib: {e}")

        return True
    except ImportError as e:
        print(f"Failed to import gitoxide: {e}")
        return False


def test_error_types():
    """Test that all error types are accessible."""
    print_separator('=')
    print("TESTING ERROR TYPES")
    print_separator('=')

    import gitoxide

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

    error_types = []
    for name in expected_error_names:
        if hasattr(gitoxide, name):
            error_type = getattr(gitoxide, name)
            if isinstance(error_type, type) and issubclass(error_type, Exception):
                error_types.append(error_type)

    print(
        f"Found {len(error_types)} of {len(expected_error_names)} expected error types:")
    for error_type in sorted(error_types, key=lambda t: t.__name__):
        print(f"  - {error_type.__name__}")

    # Verify error hierarchy
    base_error = gitoxide.GitoxideError if hasattr(
        gitoxide, 'GitoxideError') else None

    if base_error:
        hierarchy_correct = True
        for error_type in error_types:
            if error_type is not base_error:
                if not issubclass(error_type, base_error):
                    print(
                        f"ERROR: {error_type.__name__} is not a subclass of GitoxideError")
                    hierarchy_correct = False

        if hierarchy_correct:
            print("\nError hierarchy is set up correctly.")
        else:
            print("\nError hierarchy has issues.")
    else:
        print("\nBase GitoxideError not found, cannot verify hierarchy.")

    return len(error_types) > 0


def test_repository_info(repo_path=None):
    """Test basic repository information functions."""
    print_separator('=')
    print("TESTING REPOSITORY INFO")
    print_separator('=')

    import gitoxide

    if repo_path is None:
        repo_path = os.path.abspath(os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))))

    print(f"Opening repository at: {repo_path}")

    try:
        # Open the repository
        repo = gitoxide.Repository.open(repo_path)

        # Basic repository information
        print(f"Git directory: {repo.git_dir()}")
        print(f"Working directory: {repo.work_dir() or 'None'}")
        print(f"Is bare: {repo.is_bare()}")

        # Test additional methods if available
        if hasattr(repo, 'is_shallow'):
            print(f"Is shallow: {repo.is_shallow()}")
        else:
            print("Method 'is_shallow' not available")

        if hasattr(repo, 'object_hash'):
            print(f"Object hash: {repo.object_hash()}")
        else:
            print("Method 'object_hash' not available")

        # HEAD information
        try:
            head = repo.head()
            print(f"\nHEAD: {head}")
        except Exception as e:
            print(f"\nError getting HEAD: {e}")

        return True
    except Exception as e:
        print(f"Error opening repository: {e}")
        return False


def test_references(repo_path=None):
    """Test repository reference functions."""
    print_separator('=')
    print("TESTING REFERENCES")
    print_separator('=')

    import gitoxide

    if repo_path is None:
        repo_path = os.path.abspath(os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))))

    print(f"Opening repository at: {repo_path}")

    try:
        # Open the repository
        repo = gitoxide.Repository.open(repo_path)

        if not hasattr(repo, 'references'):
            print("Method 'references' not available")
            return False

        # List all references
        refs = repo.references()
        print(f"Found {len(refs)} references:")
        for i, ref in enumerate(refs[:5]):  # Just print the first 5
            ref_type = "symbolic" if ref.is_symbolic else "direct"
            print(f"  - {ref.name} -> {ref.target} ({ref_type})")

        if len(refs) > 5:
            print(f"  ... and {len(refs) - 5} more references")

        # Get reference names if available
        if hasattr(repo, 'reference_names'):
            ref_names = repo.reference_names()
            print(f"\nFound {len(ref_names)} reference names (first 5):")
            for name in ref_names[:5]:
                print(f"  - {name}")

            if len(ref_names) > 5:
                print(f"  ... and {len(ref_names) - 5} more")
        else:
            print("\nMethod 'reference_names' not available")

        # Find a specific reference
        try:
            head_ref = repo.find_reference("HEAD")
            print(
                f"\nFound HEAD reference: {head_ref.name} -> {head_ref.target}")
        except Exception as e:
            print(f"\nError finding HEAD reference: {e}")

        return True
    except Exception as e:
        print(f"Error testing references: {e}")
        return False


def test_objects(repo_path=None):
    """Test repository object functions."""
    print_separator('=')
    print("TESTING OBJECTS")
    print_separator('=')

    import gitoxide

    if repo_path is None:
        repo_path = os.path.abspath(os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))))

    print(f"Opening repository at: {repo_path}")

    try:
        # Open the repository
        repo = gitoxide.Repository.open(repo_path)

        # Skip if object methods are not available
        if not hasattr(repo, 'find_header') or not hasattr(repo, 'has_object'):
            print("Object methods not available")
            return False

        # Get commit ID using git command
        try:
            commit_id = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                universal_newlines=True
            ).strip()
            print(f"HEAD commit ID: {commit_id}")

            # Check if object exists
            exists = repo.has_object(commit_id)
            print(f"Object exists: {exists}")

            if exists:
                # Get object header
                header = repo.find_header(commit_id)
                print(
                    f"Object header: kind={header.kind}, size={header.size} bytes")

                # Find commit object
                if hasattr(repo, 'find_commit'):
                    commit = repo.find_commit(commit_id)
                    print(f"Found commit object: {commit.id} ({commit.kind})")

                # Get tree from commit
                tree_id = subprocess.check_output(
                    ["git", "rev-parse", "HEAD^{tree}"],
                    cwd=repo_path,
                    universal_newlines=True
                ).strip()

                # Find tree object
                if hasattr(repo, 'find_tree'):
                    tree = repo.find_tree(tree_id)
                    print(f"Found tree object: {tree.id} ({tree.kind})")

            return True
        except subprocess.CalledProcessError as e:
            print(f"Error getting commit ID: {e}")
            return False
    except Exception as e:
        print(f"Error testing objects: {e}")
        return False


def test_async(repo_path=None):
    """Test async repository functions if available."""
    print_separator('=')
    print("TESTING ASYNC API")
    print_separator('=')

    import gitoxide
    import asyncio

    if not hasattr(gitoxide, 'asyncio'):
        print("Async API not available. Make sure to build with --features async")
        return False

    if repo_path is None:
        repo_path = os.path.abspath(os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))))

    async def test_async_repo():
        # Try to use the async API
        try:
            repo = await gitoxide.asyncio.Repository.open(repo_path)
            print(
                f"Successfully opened repository at {repo_path} using async API")

            # Test basic methods
            print(f"Git directory: {await repo.git_dir()}")
            print(f"Is bare: {await repo.is_bare()}")

            if hasattr(repo, 'object_hash'):
                print(f"Object hash: {await repo.object_hash()}")

            # Test head method
            try:
                head = await repo.head()
                print(f"HEAD: {head}")
            except Exception as e:
                print(f"Error getting HEAD: {e}")

            # Test shallow_commits method if available
            if hasattr(repo, 'shallow_commits'):
                try:
                    commits = await repo.shallow_commits()
                    if commits:
                        print(f"Shallow commits: {len(commits)} found")
                    else:
                        print("No shallow commits (not a shallow repository)")
                except Exception as e:
                    print(f"Error getting shallow commits: {e}")

            return True
        except Exception as e:
            print(f"Error in async test: {e}")
            return False

    # Run the async function
    try:
        result = asyncio.run(test_async_repo())
        return result
    except Exception as e:
        print(f"Error running async test: {e}")
        return False


def create_test_repo():
    """Create a temporary test repository."""
    print_separator('=')
    print("CREATING TEST REPOSITORY")
    print_separator('=')

    import gitoxide

    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")

    try:
        # Initialize the repository
        repo = gitoxide.Repository.init(temp_dir, False)
        print(f"Initialized repository at: {temp_dir}")
        print(f"Git directory: {repo.git_dir()}")

        # Configure Git
        subprocess.run(["git", "config", "--global",
                       "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "config", "--global",
                       "user.name", "Test User"], check=True)
        print("Configured Git user")

        # Add a file and commit it
        readme_path = os.path.join(temp_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Test Repository\n\nThis is a test repository.")
        print("Created README.md file")

        subprocess.run(["git", "add", "README.md"], cwd=temp_dir, check=True)
        print("Added README.md to index")

        subprocess.run(["git", "commit", "-m", "Initial commit"],
                       cwd=temp_dir, check=True)
        print("Created initial commit")

        # Create a branch
        subprocess.run(["git", "checkout", "-b", "test-branch"],
                       cwd=temp_dir, check=True)
        print("Created test-branch")

        # Add a tag
        subprocess.run(["git", "tag", "v1.0"], cwd=temp_dir, check=True)
        print("Created tag v1.0")

        return temp_dir
    except Exception as e:
        print(f"Error creating test repository: {e}")
        shutil.rmtree(temp_dir)
        return None


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run tests for gitoxide Python bindings")
    parser.add_argument(
        "--repo", help="Path to a Git repository to use for testing")
    parser.add_argument("--test-import", action="store_true",
                        help="Test importing the module")
    parser.add_argument("--test-errors", action="store_true",
                        help="Test error types")
    parser.add_argument("--test-repo", action="store_true",
                        help="Test repository info")
    parser.add_argument("--test-refs", action="store_true",
                        help="Test references")
    parser.add_argument(
        "--test-objects", action="store_true", help="Test objects")
    parser.add_argument("--test-async", action="store_true",
                        help="Test async API")
    parser.add_argument("--create-repo", action="store_true",
                        help="Create a test repository")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    return parser.parse_args()


def main():
    """Main function."""
    import shutil

    args = parse_args()

    # If no specific tests are selected, run all tests
    if not any([
        args.test_import, args.test_errors, args.test_repo,
        args.test_refs, args.test_objects, args.test_async,
        args.create_repo, args.all
    ]):
        args.all = True

    # Keep track of test results
    results = {}
    temp_repo = None

    try:
        # Create test repo if needed
        if args.create_repo or args.all:
            temp_repo = create_test_repo()
            results["create_repo"] = temp_repo is not None

        # Run selected tests
        if args.test_import or args.all:
            results["import"] = test_basic_import()

        if args.test_errors or args.all:
            results["errors"] = test_error_types()

        if args.test_repo or args.all:
            results["repo"] = test_repository_info(args.repo or temp_repo)

        if args.test_refs or args.all:
            results["refs"] = test_references(args.repo or temp_repo)

        if args.test_objects or args.all:
            results["objects"] = test_objects(args.repo or temp_repo)

        if args.test_async or args.all:
            results["async"] = test_async(args.repo or temp_repo)

        # Print summary
        print_separator('=')
        print("TEST RESULTS SUMMARY")
        print_separator('=')

        for test, result in results.items():
            status = "PASS" if result else "FAIL"
            print(f"{test.ljust(15)}: {status}")

        # Return success if all tests passed
        return 0 if all(results.values()) else 1

    finally:
        # Clean up temporary repository
        if temp_repo and os.path.exists(temp_repo):
            print(f"\nCleaning up temporary repository: {temp_repo}")
            shutil.rmtree(temp_repo)


if __name__ == "__main__":
    sys.exit(main())
