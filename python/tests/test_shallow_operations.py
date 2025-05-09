"""
Tests for the shallow repository operations in gitoxide.
"""

import os
import tempfile
import pytest
import gitoxide


class TestShallowOperations:
    """Tests for shallow repository operations."""

    def test_is_shallow(self):
        """Test the is_shallow method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a regular repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)
            
            # A new repository should not be shallow
            assert not repo.is_shallow()
            
    def test_shallow_file(self):
        """Test the shallow_file method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a regular repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)
            
            # Check that shallow_file returns a path
            shallow_path = repo.shallow_file()
            assert isinstance(shallow_path, str)
            assert "shallow" in shallow_path
            
    def test_shallow_commits(self):
        """Test the shallow_commits method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a regular repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)
            
            # A new repository shouldn't have shallow commits
            result = repo.shallow_commits()
            assert result is None

    def test_object_hash(self):
        """Test the object_hash method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a regular repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)
            
            # Check the hash algorithm (should be SHA-1 by default)
            hash_algo = repo.object_hash()
            assert isinstance(hash_algo, str)
            assert hash_algo.lower() == "sha1"