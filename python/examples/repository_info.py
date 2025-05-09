#!/usr/bin/env python3
"""
Repository information tool using gitoxide Python bindings.

This script accepts a path to a Git repository and displays detailed information about it.
"""

import argparse
import os
import sys
import gitoxide


def print_separator(char='-', length=50):
    """Print a separator line."""
    print(char * length)


def display_repository_info(repo_path):
    """Display information about a repository."""
    try:
        # Open the repository
        repo = gitoxide.Repository.open(repo_path)

        # Basic repository information
        print_separator("=")
        print(f"Repository Information: {repo_path}")
        print_separator("=")

        print(f"Git Directory: {repo.git_dir()}")

        if repo.is_bare():
            print("Repository Type: Bare repository (no working directory)")
        else:
            work_dir = repo.work_dir()
            print(f"Repository Type: Regular repository")
            print(f"Working Directory: {work_dir}")

        # Display HEAD information
        print_separator()
        print("Reference Information:")
        try:
            head = repo.head()
            print(f"HEAD: {head}")

            # Determine if HEAD is a branch or detached
            if head.startswith("refs/heads/"):
                branch_name = head.replace("refs/heads/", "")
                print(f"Current Branch: {branch_name}")
            else:
                print("HEAD is detached (not on any branch)")
        except gitoxide.RepositoryError as e:
            print(f"Could not retrieve HEAD: {e}")

        return 0
    except gitoxide.RepositoryError as e:
        print(f"Error: {e}")
        return 1


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Display Git repository information.")
    parser.add_argument("path", nargs="?", default=".",
                        help="Path to the Git repository (defaults to current directory)")

    args = parser.parse_args()
    repo_path = os.path.abspath(args.path)

    if not os.path.exists(repo_path):
        print(f"Error: The path {repo_path} does not exist.")
        return 1

    return display_repository_info(repo_path)


if __name__ == "__main__":
    sys.exit(main())
