"""
Tests for the gitoxide Repository functionality.
"""

import os
import tempfile
import pytest
import gitoxide


class TestRepository:
    """Tests for the Repository class."""

    def test_init_regular_repo(self):
        """Test initializing a regular repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a regular repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)

            # Check repository properties
            assert os.path.isdir(repo.git_dir())
            assert repo.work_dir() is not None
            assert not repo.is_bare()

            # Try to open the repository again
            reopened = gitoxide.Repository.open(temp_dir)
            assert reopened.git_dir() == repo.git_dir()

    def test_init_bare_repo(self):
        """Test initializing a bare repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bare_path = os.path.join(temp_dir, "bare.git")

            # Initialize a bare repository
            repo = gitoxide.Repository.init(bare_path, bare=True)

            # Check repository properties
            assert os.path.isdir(repo.git_dir())
            assert repo.work_dir() is None
            assert repo.is_bare()

            # Try to open the repository again
            reopened = gitoxide.Repository.open(bare_path)
            assert reopened.git_dir() == repo.git_dir()

    def test_open_nonexistent_repo(self):
        """Test opening a non-existent repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_repo_path = os.path.join(temp_dir, "nonexistent")
            os.makedirs(non_repo_path)

            # Attempting to open a directory that's not a Git repository should raise an error
            with pytest.raises(Exception) as excinfo:
                gitoxide.Repository.open(non_repo_path)
            assert "does not appear to be a git repository" in str(
                excinfo.value)

    def test_head_on_new_repo(self):
        """Test getting HEAD on a new repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = gitoxide.Repository.init(temp_dir, bare=False)

            # A new repo should have HEAD pointing to refs/heads/master or refs/heads/main,
            # but might throw an error if HEAD is not set
            try:
                head = repo.head()
                assert head.startswith("refs/heads/")
            except Exception as e:
                assert "HEAD is not set" in str(e)
