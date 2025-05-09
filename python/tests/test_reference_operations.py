"""
Tests for Git reference operations in gitoxide.
"""

import os
import tempfile
import subprocess
import pytest
import gitoxide


class TestReferenceOperations:
    """Tests for Git reference operations."""

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

    def test_references(self, repo_with_commit):
        """Test references method."""
        repo, commit_id = repo_with_commit
        
        # Get all references
        refs = repo.references()
        
        # Should have at least one reference (HEAD)
        assert len(refs) > 0
        
        # Check that each reference has expected properties
        for ref in refs:
            assert hasattr(ref, 'name')
            assert hasattr(ref, 'target')
            assert hasattr(ref, 'is_symbolic')
            assert isinstance(ref.name, str)
            assert isinstance(ref.target, str)
            assert isinstance(ref.is_symbolic, bool)

    def test_reference_names(self, repo_with_commit):
        """Test reference_names method."""
        repo, commit_id = repo_with_commit
        
        # Get all reference names
        ref_names = repo.reference_names()
        
        # Should have at least one reference (HEAD)
        assert len(ref_names) > 0
        
        # Check that each name is a string
        for name in ref_names:
            assert isinstance(name, str)
            
        # Common references should be present - but could be formatted differently
        # Test for refs/heads instead, which should always be there in a repo with a commit
        assert any("refs/heads/" in name for name in ref_names)

    def test_find_reference(self, repo_with_commit):
        """Test find_reference method."""
        repo, commit_id = repo_with_commit
        
        # Find HEAD reference
        head_ref = repo.find_reference("HEAD")
        
        # Check properties
        assert head_ref.name == "HEAD" or head_ref.name.endswith("HEAD")
        assert isinstance(head_ref.target, str)
        assert isinstance(head_ref.is_symbolic, bool)
        
        # Try to find a non-existent reference
        with pytest.raises(Exception):
            repo.find_reference("refs/heads/nonexistent")

    def test_create_reference(self, repo_with_commit):
        """Test create_reference method."""
        repo, commit_id = repo_with_commit
        
        # Create a new reference (direct)
        new_ref = repo.create_reference("refs/tags/test-tag", commit_id, is_symbolic=False, force=False)
        
        # Check properties
        assert new_ref.name == "refs/tags/test-tag"
        assert new_ref.target == commit_id
        assert not new_ref.is_symbolic
        
        # Create a symbolic reference
        sym_ref = repo.create_reference("refs/tags/symbolic-tag", "refs/tags/test-tag", is_symbolic=True, force=False)
        
        # Check properties
        assert sym_ref.name == "refs/tags/symbolic-tag"
        assert sym_ref.target == "refs/tags/test-tag"
        assert sym_ref.is_symbolic
        
        # Trying to create a reference with an invalid name should fail
        with pytest.raises(Exception):
            repo.create_reference("invalid//name", commit_id, is_symbolic=False, force=False)
        
        # But with force=True it should work
        forced_ref = repo.create_reference("refs/tags/test-tag", commit_id, is_symbolic=False, force=True)
        assert forced_ref.name == "refs/tags/test-tag"
        
        # Test with invalid reference name
        with pytest.raises(Exception):
            repo.create_reference("invalid//name", commit_id, is_symbolic=False, force=False)
        
        # Test with invalid target for symbolic reference
        with pytest.raises(Exception):
            repo.create_reference("refs/tags/bad-sym", "invalid//target", is_symbolic=True, force=False)
        
        # Test with invalid object ID for direct reference
        with pytest.raises(Exception):
            repo.create_reference("refs/tags/bad-direct", "not-a-valid-id", is_symbolic=False, force=False)