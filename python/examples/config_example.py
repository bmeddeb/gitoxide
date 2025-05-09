"""
Example demonstrating configuration access with gitoxide Python bindings.
"""

import os
import sys
import gitoxide


def main():
    print(f"Gitoxide version: {gitoxide.__version__}")

    # Open the current repository
    print(f"\nOpening the current repository")
    try:
        repo = gitoxide.Repository.open(
            "/Users/ben/PycharmProjects/SER402-Team3")
        print(f"  Git directory: {repo.git_dir()}")
        print(f"  Working directory: {repo.work_dir() or 'None'}")
        print(f"  Is bare: {repo.is_bare()}")

        # Access configuration
        config = repo.config()

        print("\nBasic configuration values:")
        print(f"  user.name = {config.string('user.name')}")
        print(f"  user.email = {config.string('user.email')}")
        print(f"  core.ignorecase = {config.boolean('core.ignorecase')}")
        print(f"  core.compression = {config.integer('core.compression')}")
        print(f"  core.bare = {config.boolean('core.bare')}")

        print("\nRemote configuration:")
        origins = config.values("remote.origin.fetch")
        if origins:
            print(f"  remote.origin.fetch has {len(origins)} values:")
            for i, value in enumerate(origins):
                print(f"    {i+1}. {value}")
        else:
            print("  No remote.origin.fetch values found")

        print("\nCommon config entries:")
        entries = config.entries()
        if entries:
            for key, value in entries.items():
                print(f"  {key} = {value}")
        else:
            print("  No entries found")

        print("\nKey existence checks:")
        print(f"  Has user.name? {config.has_key('user.name')}")
        print(f"  Has non-existent.key? {config.has_key('non-existent.key')}")

    except Exception as e:
        print(f"Error accessing repository: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
