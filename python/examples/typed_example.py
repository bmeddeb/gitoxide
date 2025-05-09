#!/usr/bin/env python3
"""
Example of using gitoxide with type hints.

This example demonstrates how to use gitoxide with type
annotations and how they can help with IDE code completion
and static type checking.
"""

import os
import sys
import pathlib
from typing import Optional, List, Dict, Any


def get_repo_info(repo_path: str) -> Dict[str, Any]:
    """
    Get information about a Git repository with proper typing.

    Args:
        repo_path: Path to a Git repository

    Returns:
        A dictionary with repository information

    Raises:
        Exception: If the repository cannot be opened
    """
    import gitoxide

    try:
        # Open the repository - IDE will know this returns a Repository object
        repo = gitoxide.Repository.open(repo_path)

        # Collect information - IDE will know the return types of these methods
        info = {
            "git_dir": repo.git_dir(),           # IDE knows this is str
            "work_dir": repo.work_dir(),         # IDE knows this is Optional[str]
            "is_bare": repo.is_bare(),           # IDE knows this is bool
            "head": None
        }

        # Try to get HEAD
        try:
            info["head"] = repo.head()  # IDE knows this is str
        except gitoxide.RepositoryError as e:
            info["head_error"] = str(e)

        return info

    except Exception as e:
        print(f"Error opening repository: {e}")
        raise


def process_repositories(paths: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Process multiple repositories and return their information.

    Args:
        paths: List of paths to Git repositories

    Returns:
        Dictionary mapping repository paths to their information
    """
    results: Dict[str, Dict[str, Any]] = {}

    for path in paths:
        try:
            info = get_repo_info(path)
            results[path] = info
        except Exception as e:
            results[path] = {"error": str(e)}

    return results


def create_test_repo(path: str) -> Optional[str]:
    """
    Create a test repository at the specified path.

    Args:
        path: Where to create the repository

    Returns:
        Path to git directory if successful, None otherwise
    """
    import gitoxide

    try:
        # Create a repository
        repo = gitoxide.Repository.init(path, bare=False)
        return repo.git_dir()
    except Exception as e:
        print(f"Error creating repository: {e}")
        return None


def main() -> int:
    """
    Main function with type annotations.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    import tempfile
    import gitoxide

    print(f"Gitoxide version: {gitoxide.__version__}")

    # Create a temporary repository
    with tempfile.TemporaryDirectory() as temp_dir:
        git_dir = create_test_repo(temp_dir)

        if not git_dir:
            print("Failed to create test repository")
            return 1

        print(f"Created test repository at: {temp_dir}")

        # Process the repository
        repos_to_check = [temp_dir]

        # Try to add the current directory if it's a Git repository
        try:
            current_dir = os.getcwd()
            gitoxide.Repository.open(current_dir)
            repos_to_check.append(current_dir)
        except Exception:
            pass

        # Process repositories
        results = process_repositories(repos_to_check)

        # Display results
        for path, info in results.items():
            print(f"\nRepository: {path}")
            for key, value in info.items():
                print(f"  {key}: {value}")

    return 0


if __name__ == "__main__":
    sys.exit(main())