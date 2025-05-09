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

    def test_merge_bases(self):
        """Test finding merge bases between commits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a new repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)

            # Print available methods to debug
            print("Available methods:", dir(repo))

            # We need to create a commit history with merge bases
            # Set up git user info
            os.system(f"cd {temp_dir} && git config user.name 'Test User'")
            os.system(
                f"cd {temp_dir} && git config user.email 'test@example.com'")

            # Create initial commit
            os.system(
                f"cd {temp_dir} && echo 'Initial content' > file.txt && git add file.txt && git commit -m 'Initial commit'")

            # Get the initial commit ID
            initial_commit = os.popen(
                f"cd {temp_dir} && git rev-parse HEAD").read().strip()

            # Create two branches from initial commit
            os.system(f"cd {temp_dir} && git checkout -b branch1")
            os.system(
                f"cd {temp_dir} && echo 'Branch 1 content' >> file.txt && git add file.txt && git commit -m 'Branch 1 commit'")
            branch1_commit = os.popen(
                f"cd {temp_dir} && git rev-parse HEAD").read().strip()

            os.system(
                f"cd {temp_dir} && git checkout -b branch2 {initial_commit}")
            os.system(
                f"cd {temp_dir} && echo 'Branch 2 content' >> file.txt && git add file.txt && git commit -m 'Branch 2 commit'")
            branch2_commit = os.popen(
                f"cd {temp_dir} && git rev-parse HEAD").read().strip()

            # Test merge_bases
            # The merge base of branch1_commit and branch2_commit should be initial_commit
            merge_bases = repo.merge_bases(branch1_commit, [branch2_commit])
            assert len(merge_bases) == 1
            assert merge_bases[0] == initial_commit

            # Test with invalid commit ID
            with pytest.raises(Exception) as excinfo:
                repo.merge_bases("invalidcommitid", [branch1_commit])
            assert "Invalid object ID" in str(excinfo.value)

    def test_merge_base(self):
        """Test finding the best merge base between two commits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a new repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)

            # Set up git user info
            os.system(f"cd {temp_dir} && git config user.name 'Test User'")
            os.system(
                f"cd {temp_dir} && git config user.email 'test@example.com'")

            # Create initial commit
            os.system(
                f"cd {temp_dir} && echo 'Initial content' > file.txt && git add file.txt && git commit -m 'Initial commit'")

            # Get the initial commit ID
            initial_commit = os.popen(
                f"cd {temp_dir} && git rev-parse HEAD").read().strip()

            # Create two branches from initial commit
            os.system(f"cd {temp_dir} && git checkout -b branch1")
            os.system(
                f"cd {temp_dir} && echo 'Branch 1 content' >> file.txt && git add file.txt && git commit -m 'Branch 1 commit'")
            branch1_commit = os.popen(
                f"cd {temp_dir} && git rev-parse HEAD").read().strip()

            os.system(
                f"cd {temp_dir} && git checkout -b branch2 {initial_commit}")
            os.system(
                f"cd {temp_dir} && echo 'Branch 2 content' >> file.txt && git add file.txt && git commit -m 'Branch 2 commit'")
            branch2_commit = os.popen(
                f"cd {temp_dir} && git rev-parse HEAD").read().strip()

            # Test merge_base
            # The merge base of branch1_commit and branch2_commit should be initial_commit
            merge_base = repo.merge_base(branch1_commit, branch2_commit)
            assert merge_base == initial_commit

            # Test with invalid commit ID
            with pytest.raises(Exception) as excinfo:
                repo.merge_base("invalidcommitid", branch1_commit)
            assert "Invalid object ID" in str(excinfo.value)

    def test_rev_parse(self):
        """Test parsing revision specifications."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize a new repository
            repo = gitoxide.Repository.init(temp_dir, bare=False)

            # Set up git user info
            os.system(f"cd {temp_dir} && git config user.name 'Test User'")
            os.system(
                f"cd {temp_dir} && git config user.email 'test@example.com'")

            # Create initial commit
            os.system(
                f"cd {temp_dir} && echo 'Initial content' > file.txt && git add file.txt && git commit -m 'Initial commit'")

            # Get the initial commit ID using git rev-parse
            initial_commit = os.popen(
                f"cd {temp_dir} && git rev-parse HEAD").read().strip()

            # Create a second commit
            os.system(
                f"cd {temp_dir} && echo 'Second content' >> file.txt && git add file.txt && git commit -m 'Second commit'")
            second_commit = os.popen(
                f"cd {temp_dir} && git rev-parse HEAD").read().strip()

            # Test various revision specifications
            # HEAD should resolve to the second commit
            head_commit = repo.rev_parse("HEAD")
            assert head_commit == second_commit

            # HEAD^ should resolve to the first commit
            parent_commit = repo.rev_parse("HEAD^")
            assert parent_commit == initial_commit

            # HEAD~1 should also resolve to the first commit
            parent_commit2 = repo.rev_parse("HEAD~1")
            assert parent_commit2 == initial_commit

            # Full SHA should resolve to itself
            full_sha = repo.rev_parse(second_commit)
            assert full_sha == second_commit

            # Test with an invalid revision specification
            with pytest.raises(Exception) as excinfo:
                repo.rev_parse("non-existent-branch")
            assert "Failed to parse revision" in str(excinfo.value)
