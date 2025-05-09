#!/usr/bin/env python3
"""
Basic usage examples for the gitoxide Python bindings.
"""

import os
import sys
import tempfile
import gitoxide


def main():
    print(f"Gitoxide version: {gitoxide.__version__}")

    # Example 1: Open an existing repository
    try:
        # Try to open the current directory as a repository
        repo = gitoxide.Repository.open("/Users/ben/PycharmProjects/SER402-Team3")
        print(f"\nSuccessfully opened existing repository:")
        print(f"  Git directory: {repo.git_dir()}")
        print(f"  Working directory: {repo.work_dir()}")
        print(f"  Is bare: {repo.is_bare()}")
        print(f"  HEAD: {repo.head()}")
    except Exception as e:
        print(f"\nCould not open current directory as a repository: {e}")

    # Example 2: Create a new repository
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\nCreating a new repository in {temp_dir}")
        new_repo = gitoxide.Repository.init(temp_dir, bare=False)
        print(f"  Git directory: {new_repo.git_dir()}")
        print(f"  Working directory: {new_repo.work_dir()}")
        print(f"  Is bare: {new_repo.is_bare()}")

        try:
            head = new_repo.head()
            print(f"  HEAD: {head}")
        except Exception as e:
            print(f"  HEAD not set in new repository: {e}")

    # Example 3: Create a bare repository
    with tempfile.TemporaryDirectory() as temp_dir:
        bare_path = os.path.join(temp_dir, "bare-repo.git")
        print(f"\nCreating a bare repository in {bare_path}")
        bare_repo = gitoxide.Repository.init(bare_path, bare=True)
        print(f"  Git directory: {bare_repo.git_dir()}")
        print(f"  Working directory: {bare_repo.work_dir()}")
        print(f"  Is bare: {bare_repo.is_bare()}")

        try:
            head = bare_repo.head()
            print(f"  HEAD: {head}")
        except Exception as e:
            print(f"  HEAD not set in bare repository: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
