#!/usr/bin/env python3
"""
Example demonstrating working with Git objects and references in gitoxide.
"""

import os
import tempfile
import subprocess
import gitoxide


def create_test_repo():
    """Create a test repository with a commit and references."""
    temp_dir = tempfile.mkdtemp()
    
    # Initialize the repository
    repo = gitoxide.Repository.init(temp_dir, False)
    
    # Configure Git
    subprocess.run(["git", "config", "--global", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "config", "--global", "user.name", "Test User"], check=True)
    
    # Add a file and commit it
    readme_path = os.path.join(temp_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write("# Test Repository\n\nThis is a test repository.")
    
    subprocess.run(["git", "add", "README.md"], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)
    
    # Create a branch
    subprocess.run(["git", "checkout", "-b", "test-branch"], cwd=temp_dir, check=True)
    
    # Add a tag
    subprocess.run(["git", "tag", "v1.0"], cwd=temp_dir, check=True)
    
    return temp_dir, repo


def main():
    """Demonstrate repository operations with objects and references."""
    print("Gitoxide version:", gitoxide.__version__)
    
    # Create a test repository
    repo_path, repo = create_test_repo()
    print(f"\nCreated test repository at {repo_path}")
    
    try:
        # Working with references
        print("\n=== REFERENCES ===")
        
        # List all references
        refs = repo.references()
        print(f"Found {len(refs)} references:")
        for ref in refs:
            ref_type = "symbolic" if ref.is_symbolic else "direct"
            print(f"  - {ref.name} -> {ref.target} ({ref_type})")
        
        # Get reference names
        ref_names = repo.reference_names()
        print(f"\nReference names: {ref_names}")
        
        # Find a specific reference
        try:
            head_ref = repo.find_reference("HEAD")
            print(f"\nFound HEAD reference: {head_ref.name} -> {head_ref.target}")
        except Exception as e:
            print(f"Error finding HEAD: {e}")
        
        # Create a new reference
        try:
            # Create a reference to the current HEAD (symbolic)
            feature_ref = repo.create_reference("refs/heads/new-feature", "HEAD", True, False)
            print(f"\nCreated feature reference: {feature_ref.name} -> {feature_ref.target}")
        except Exception as e:
            print(f"Error creating reference: {e}")
        
        # Working with objects
        print("\n=== OBJECTS ===")
        
        # Get commit ID
        commit_id = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            cwd=repo_path, 
            universal_newlines=True
        ).strip()
        print(f"HEAD commit ID: {commit_id}")
        
        # Check if object exists
        exists = repo.has_object(commit_id)
        print(f"Object exists: {exists}")
        
        # Get object header
        header = repo.find_header(commit_id)
        print(f"Object header: kind={header.kind}, size={header.size} bytes")
        
        # Find commit object
        commit = repo.find_commit(commit_id)
        print(f"Found commit object: {commit.id} ({commit.kind})")
        commit_data = commit.data.decode('utf-8', errors='replace')
        print("Commit data preview:", commit_data[:100], "...")
        
        # Get tree from commit
        tree_id = subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=repo_path,
            universal_newlines=True
        ).strip()
        
        # Find tree object
        tree = repo.find_tree(tree_id)
        print(f"\nFound tree object: {tree.id} ({tree.kind})")
        print("Tree data preview:", tree.data[:20].hex(), "...")
        
        # Get a blob ID (README.md)
        readme_path = os.path.join(repo_path, "README.md")
        blob_id = subprocess.check_output(
            ["git", "hash-object", readme_path],
            cwd=repo_path,
            universal_newlines=True
        ).strip()
        
        # Find blob object
        blob = repo.find_blob(blob_id)
        print(f"\nFound blob object: {blob.id} ({blob.kind})")
        print("Blob content:", blob.data.decode('utf-8'))
        
    finally:
        # Clean up
        import shutil
        shutil.rmtree(repo_path)
        print(f"\nCleaned up {repo_path}")


if __name__ == "__main__":
    main()