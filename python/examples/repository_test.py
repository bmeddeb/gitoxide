import os
import sys
import gitoxide

def main():
    # Get the current repository path
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    print(f"Opening repository at: {repo_path}")
    
    # Open the repository
    repo = gitoxide.Repository.open(repo_path)
    
    # Basic repository information
    print(f"Git directory: {repo.git_dir()}")
    print(f"Working directory: {repo.work_dir()}")
    print(f"Is bare: {repo.is_bare()}")
    print(f"Is shallow: {repo.is_shallow()}")
    print(f"Object hash: {repo.object_hash()}")
    
    # References
    print("\nReferences:")
    try:
        refs = repo.references()
        for ref in refs[:5]:  # Just print the first 5 to keep output manageable
            print(f"  {ref.name} -> {ref.target} (symbolic: {ref.is_symbolic})")
        print(f"  ... and {len(refs) - 5} more references")
    except Exception as e:
        print(f"Error getting references: {e}")
    
    # HEAD
    try:
        print(f"\nHEAD: {repo.head()}")
    except Exception as e:
        print(f"Error getting HEAD: {e}")
    
    # Find reference
    try:
        head = repo.find_reference("HEAD")
        print(f"\nHEAD reference: {head.name} -> {head.target} (symbolic: {head.is_symbolic})")
    except Exception as e:
        print(f"Error finding HEAD reference: {e}")
    
    # Try to find a commit
    try:
        # Get the HEAD reference and target
        head_ref = repo.find_reference("HEAD")
        if head_ref.is_symbolic:
            # HEAD points to a branch, find that branch
            branch_ref = repo.find_reference(head_ref.target)
            commit_id = branch_ref.target
        else:
            # HEAD is detached
            commit_id = head_ref.target

        # Now find the commit header
        header = repo.find_header(commit_id)
        print(f"\nCommit {commit_id} header:")
        print(f"  Kind: {header.kind}")
        print(f"  Size: {header.size}")
    except Exception as e:
        print(f"Error finding commit: {e}")

if __name__ == "__main__":
    main()