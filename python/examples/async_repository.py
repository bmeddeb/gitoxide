#!/usr/bin/env python3
"""
Example of using the asynchronous API of gitoxide Python bindings.

Note: This requires the async feature to be enabled.
Build with: `maturin develop --features=async`
"""

import asyncio
import tempfile
import shutil
import os

# Import the async Repository class
try:
    from gitoxide.asyncio import Repository
except ImportError:
    print("Error: Async feature is not available.")
    print("Build with: maturin develop --features=async")
    exit(1)


async def main():
    """Demonstrate basic async repository operations."""
    # Create a temporary directory for our repository
    temp_dir = tempfile.mkdtemp()

    try:
        print(f"Creating repository in {temp_dir}")

        # Initialize a new repository
        repo = await Repository.init(temp_dir, False)
        print(f"Repository initialized at {temp_dir}")

        # Get basic repository information
        print(f"Git directory: {repo.git_dir()}")
        print(f"Work directory: {repo.work_dir()}")
        print(f"Is bare: {repo.is_bare()}")
        print(f"Is shallow: {repo.is_shallow()}")
        print(f"Object hash: {repo.object_hash()}")

        # Get shallow repository information
        shallow_commits = await repo.shallow_commits()
        print(f"Shallow commits: {shallow_commits}")

        # Get reference information
        try:
            head = await repo.head()
            print(f"HEAD: {head}")
        except Exception as e:
            print(f"HEAD not set: {e}")

        # Get all references
        refs = await repo.references()
        print(f"References: {len(refs)}")
        for ref in refs:
            print(f"  - {ref.name} -> {ref.target} (symbolic: {ref.is_symbolic})")

        # Create a symbolic reference
        try:
            ref = await repo.create_reference("refs/heads/test-branch", "HEAD", True, False)
            print(f"Created reference: {ref.name} -> {ref.target}")
        except Exception as e:
            print(f"Failed to create reference: {e}")

        # List reference names
        names = await repo.reference_names()
        print(f"Reference names: {names}")

        # Try to find a reference
        try:
            head_ref = await repo.find_reference("HEAD")
            print(f"Found HEAD reference: {head_ref.name} -> {head_ref.target}")
        except Exception as e:
            print(f"Failed to find HEAD: {e}")

        # Object operations would require having objects in the repository
        # This would typically involve creating commits, which is beyond
        # the scope of this simple example

        # Run multiple async operations concurrently
        print("\nRunning multiple async operations concurrently...")
        results = await asyncio.gather(
            repo.shallow_commits(),
            repo.references(),
            repo.reference_names()
        )

        print(f"Gathered results: {len(results)} operations completed")

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"Cleaned up {temp_dir}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
