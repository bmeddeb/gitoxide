#!/usr/bin/env python3


"""
Git Configuration Explorer

A tool to explore and display Git configuration values using the gitoxide Python bindings.
This example demonstrates how to use the Config class to access various types of configuration
values from a Git repository.
"""

import os
import sys
import argparse
import gitoxide


def display_section(title):
    """Display a section title with formatting."""
    print(f"\n{'-' * 80}")
    print(f" {title}")
    print(f"{'-' * 80}")


def display_config_value(key, value, indent=2):
    """Display a configuration key-value pair with proper indentation."""
    indent_str = " " * indent
    if value is None:
        print(f"{indent_str}{key} = <not set>")
    elif isinstance(value, list):
        if not value:
            print(f"{indent_str}{key} = <empty list>")
        else:
            print(f"{indent_str}{key} = <{len(value)} values>")
            for i, val in enumerate(value):
                print(f"{indent_str}  {i}: {val}")
    else:
        print(f"{indent_str}{key} = {value}")


def explore_config(repo_path):
    """Explore and display Git configuration for the given repository."""
    try:
        # Open the repository
        repo = gitoxide.Repository.open(repo_path)
        print(f"Repository opened: {repo_path}")
        print(f"  Git directory: {repo.git_dir()}")
        print(f"  Working directory: {repo.work_dir() or '<bare repository>'}")
        print(f"  Is bare: {repo.is_bare()}")

        # Access configuration
        config = repo.config()

        # Display user information
        display_section("User Information")
        display_config_value("user.name", config.string("user.name"))
        display_config_value("user.email", config.string("user.email"))
        display_config_value(
            "user.signingkey", config.string("user.signingkey"))

        # Display core settings
        display_section("Core Settings")
        display_config_value("core.bare", config.boolean("core.bare"))
        display_config_value("core.filemode", config.boolean("core.filemode"))
        display_config_value(
            "core.ignorecase", config.boolean("core.ignorecase"))
        display_config_value("core.compression",
                             config.integer("core.compression"))
        display_config_value("core.editor", config.string("core.editor"))
        display_config_value("core.pager", config.string("core.pager"))

        # Display branch information
        display_section("Branch Information")
        try:
            head_ref = repo.head().split("/")[-1]
            display_config_value(f"Current HEAD", head_ref)
            display_config_value(f"branch.{head_ref}.remote", config.string(
                f"branch.{head_ref}.remote"))
            display_config_value(f"branch.{head_ref}.merge", config.string(
                f"branch.{head_ref}.merge"))
        except Exception as e:
            print(f"  Error accessing HEAD: {e}")

        # Display remote information
        display_section("Remote Information")
        # First, gather remote names from the entries
        remotes = set()
        all_entries = config.entries()
        for key in all_entries.keys():
            if key.startswith("remote.") and "." in key[7:]:
                remote_name = key.split(".")[1]
                remotes.add(remote_name)

        # Display information for each remote
        for remote in sorted(remotes):
            print(f"  Remote: {remote}")
            display_config_value(f"remote.{remote}.url", config.string(
                f"remote.{remote}.url"), indent=4)
            fetch_values = config.values(f"remote.{remote}.fetch")
            display_config_value(
                f"remote.{remote}.fetch", fetch_values, indent=4)

        # Display all config entries
        display_section("All Configuration Entries")
        entries = config.entries()
        if entries:
            for key in sorted(entries.keys()):
                display_config_value(key, entries[key])
        else:
            print("  No configuration entries found")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


def main():
    """Main function to parse arguments and run the tool."""
    parser = argparse.ArgumentParser(
        description="Explore Git repository configuration using gitoxide Python bindings"
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        default=".",
        help="Path to the Git repository (default: current directory)",
    )
    args = parser.parse_args()

    # Print version info
    print(f"Gitoxide version: {gitoxide.__version__}")

    # Resolve repository path
    repo_path = os.path.abspath(args.repo_path)
    if not os.path.exists(repo_path):
        print(f"Error: Path does not exist: {repo_path}")
        return 1

    # Run configuration explorer
    return explore_config(repo_path)


if __name__ == "__main__":
    sys.exit(main())
