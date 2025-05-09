#!/usr/bin/env python3
"""
Example demonstrating the async API in gitoxide.
"""

import os
import tempfile
import asyncio
import gitoxide


async def main():
    """Demonstrate basic async repository operations."""
    print(f"Gitoxide version: {gitoxide.__version__}")

    # Create a temporary directory for our repo
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\nInitializing repository in {temp_dir}")

        # Initialize a new repository
        repo = gitoxide.AsyncRepository.init(temp_dir, False)

        print(f"Is bare repository: {repo.is_bare()}")
        print(f"Git directory: {repo.git_dir()}")
        print(f"Work directory: {repo.work_dir()}")

        try:
            head = repo.head()
            print(f"HEAD: {head}")
        except gitoxide.RepositoryError as e:
            print(f"HEAD not set: {e}")

        # Demonstrate an async operation
        print("\nStarting async network operation simulation...")
        result = await repo.simulate_network_operation(1000)  # 1 second delay
        print(result)

        # Run multiple operations concurrently
        print("\nStarting multiple async operations concurrently...")
        results = await asyncio.gather(
            repo.simulate_network_operation(500),
            repo.simulate_network_operation(1000),
            repo.simulate_network_operation(1500)
        )

        for i, result in enumerate(results):
            print(f"Task {i+1} result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
