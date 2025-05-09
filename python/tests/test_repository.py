"""
Tests for the Repository class.
"""

import os
import pytest
import tempfile
import shutil

class TestSyncRepository:
    """Tests for the synchronous Repository class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_init_repository(self, temp_dir):
        """Test initializing a new repository."""
        from gitoxide.sync import Repository
        
        repo_path = os.path.join(temp_dir, "test_repo")
        repo = Repository.init(repo_path)
        
        assert os.path.isdir(repo_path)
        assert os.path.isdir(os.path.join(repo_path, ".git"))
        assert repo.path.endswith(".git")
        assert repo.workdir == repo_path
        assert not repo.is_bare
        assert repo.is_empty
    
    def test_init_bare_repository(self, temp_dir):
        """Test initializing a new bare repository."""
        from gitoxide.sync import Repository
        
        repo_path = os.path.join(temp_dir, "test_repo.git")
        repo = Repository.init(repo_path, bare=True)
        
        assert os.path.isdir(repo_path)
        assert not os.path.isdir(os.path.join(repo_path, ".git"))
        assert repo.path == repo_path
        assert repo.workdir is None
        assert repo.is_bare
        assert repo.is_empty
    
    def test_open_repository(self, temp_dir):
        """Test opening an existing repository."""
        from gitoxide.sync import Repository
        
        # First create a repository
        repo_path = os.path.join(temp_dir, "test_repo")
        Repository.init(repo_path)
        
        # Then open it
        repo = Repository.open(repo_path)
        
        assert repo.path.endswith(".git")
        assert repo.workdir == repo_path
        assert not repo.is_bare
        assert repo.is_empty
    
    def test_open_nonexistent_repository(self, temp_dir):
        """Test opening a nonexistent repository."""
        from gitoxide.sync import Repository
        from gitoxide.common import RepositoryError
        
        repo_path = os.path.join(temp_dir, "nonexistent")
        
        with pytest.raises(RepositoryError):
            Repository.open(repo_path)


@pytest.mark.asyncio
class TestAsyncRepository:
    """Tests for the asynchronous Repository class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    async def test_init_repository(self, temp_dir):
        """Test initializing a new repository."""
        from gitoxide.asyncio import Repository
        
        repo_path = os.path.join(temp_dir, "test_repo")
        repo = await Repository.init(repo_path)
        
        assert os.path.isdir(repo_path)
        assert os.path.isdir(os.path.join(repo_path, ".git"))
        assert (await repo.path).endswith(".git")
        assert await repo.workdir == repo_path
        assert not await repo.is_bare
        assert await repo.is_empty
    
    async def test_init_bare_repository(self, temp_dir):
        """Test initializing a new bare repository."""
        from gitoxide.asyncio import Repository
        
        repo_path = os.path.join(temp_dir, "test_repo.git")
        repo = await Repository.init(repo_path, bare=True)
        
        assert os.path.isdir(repo_path)
        assert not os.path.isdir(os.path.join(repo_path, ".git"))
        assert await repo.path == repo_path
        assert await repo.workdir is None
        assert await repo.is_bare
        assert await repo.is_empty
    
    async def test_open_repository(self, temp_dir):
        """Test opening an existing repository."""
        from gitoxide.asyncio import Repository
        
        # First create a repository
        repo_path = os.path.join(temp_dir, "test_repo")
        await Repository.init(repo_path)
        
        # Then open it
        repo = await Repository.open(repo_path)
        
        assert (await repo.path).endswith(".git")
        assert await repo.workdir == repo_path
        assert not await repo.is_bare
        assert await repo.is_empty
    
    async def test_open_nonexistent_repository(self, temp_dir):
        """Test opening a nonexistent repository."""
        from gitoxide.asyncio import Repository
        from gitoxide.common import RepositoryError
        
        repo_path = os.path.join(temp_dir, "nonexistent")
        
        with pytest.raises(RepositoryError):
            await Repository.open(repo_path)