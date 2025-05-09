"""
Tests for Git object operations in gitoxide.
"""

import os
import tempfile
import subprocess
import pytest
import gitoxide


class TestObjectOperations:
    """Tests for Git object operations."""

    @pytest.fixture
    def repo_with_commit(self):
        """Create a repository with a single commit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize the repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)
            
            # Configure Git
            subprocess.run(["git", "config", "--global", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "config", "--global", "user.name", "Test User"], check=True)
            
            # Add a file and commit it
            readme_path = os.path.join(temp_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write("# Test Repository\n\nThis is a test repository.")
            
            subprocess.run(["git", "add", "README.md"], cwd=temp_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)
            
            # Get commit ID
            commit_id = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                cwd=temp_dir, 
                universal_newlines=True
            ).strip()
            
            yield repo, commit_id

    def test_has_object(self, repo_with_commit):
        """Test has_object method."""
        repo, commit_id = repo_with_commit
        
        # The commit should exist
        assert repo.has_object(commit_id)
        
        # A non-existent object should not exist
        non_existent_id = "0" * 40
        assert not repo.has_object(non_existent_id)
        
        # Test with an invalid ID format
        with pytest.raises(Exception):
            repo.has_object("not-a-valid-id")

    def test_find_header(self, repo_with_commit):
        """Test find_header method."""
        repo, commit_id = repo_with_commit
        
        # Get the header for the commit
        header = repo.find_header(commit_id)
        
        # Check header properties
        assert header.kind == "Commit"
        assert header.size > 0
        
        # Test with a non-existent object
        non_existent_id = "0" * 40
        with pytest.raises(Exception):
            repo.find_header(non_existent_id)

    def test_find_object(self, repo_with_commit):
        """Test find_object method."""
        repo, commit_id = repo_with_commit

        # Get the object
        obj = repo.find_object(commit_id)

        # Check object properties
        assert obj.id == commit_id
        assert obj.kind == "Commit"
        assert len(obj.data) > 0

        # Test with a non-existent object
        non_existent_id = "0" * 40
        with pytest.raises(Exception):
            repo.find_object(non_existent_id)

    def test_find_commit(self, repo_with_commit):
        """Test find_commit method."""
        repo, commit_id = repo_with_commit

        # Get the commit
        commit = repo.find_commit(commit_id)

        # Check commit properties
        assert commit.id == commit_id
        assert commit.kind == "Commit"
        assert len(commit.data) > 0

    def test_find_tree(self, repo_with_commit):
        """Test find_tree method."""
        repo, commit_id = repo_with_commit

        # Get the tree from the commit
        tree_id = subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=os.path.dirname(repo.git_dir()),
            universal_newlines=True
        ).strip()

        # Get the tree
        tree = repo.find_tree(tree_id)

        # Check tree properties
        assert tree.id == tree_id
        assert tree.kind == "Tree"
        assert len(tree.data) > 0

    def test_find_blob(self, repo_with_commit):
        """Test find_blob method."""
        repo, commit_id = repo_with_commit

        # Get blob ID for README.md
        readme_path = os.path.join(os.path.dirname(repo.git_dir()), "README.md")
        blob_id = subprocess.check_output(
            ["git", "hash-object", readme_path],
            cwd=os.path.dirname(repo.git_dir()),
            universal_newlines=True
        ).strip()

        # Get the blob
        blob = repo.find_blob(blob_id)

        # Check blob properties
        assert blob.id == blob_id
        assert blob.kind == "Blob"
        assert b"# Test Repository" in blob.data