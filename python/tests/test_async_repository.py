import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

# Check if the async feature is available
try:
    from gitoxide.asyncio import Repository
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

pytestmark = pytest.mark.asyncio

# Skip all tests if async feature is not available
pytestmark = pytest.mark.skipif(not ASYNC_AVAILABLE, reason="Async feature not available")

# Fixture for creating a simple git repository
@pytest.fixture
async def simple_repo_path():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize a repository
        repo = await Repository.init(temp_dir, False)
        yield temp_dir
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

# Test basic repository operations
async def test_open_and_init(simple_repo_path):
    # Test init (already done in fixture)
    repo = await Repository.open(simple_repo_path)
    
    # Basic checks
    assert not repo.is_bare()
    assert repo.git_dir().endswith('.git')
    assert repo.work_dir() is not None

# Test shallow repository properties
async def test_shallow_properties(simple_repo_path):
    repo = await Repository.open(simple_repo_path)
    
    # This is a new repo, not a shallow clone
    assert not repo.is_shallow()
    assert repo.shallow_file() is not None  # Should return a path even if not shallow
    
    # Shallow commits should be None for non-shallow repos
    shallow_commits = await repo.shallow_commits()
    assert shallow_commits is None

# Test object hash property
async def test_object_hash(simple_repo_path):
    repo = await Repository.open(simple_repo_path)
    
    # Most git repos use SHA1 by default
    assert repo.object_hash() == "Sha1"

# Test repository HEAD
async def test_head(simple_repo_path):
    repo = await Repository.open(simple_repo_path)
    
    # A new repo might not have HEAD set to a branch yet
    # This might raise an exception, but we're just testing the async functionality
    try:
        head = await repo.head()
        assert isinstance(head, str)
    except Exception as e:
        # This is expected in a new repo with no commits
        assert "HEAD is not set" in str(e)

"""
# Additional tests for references and objects
# These tests require a repository with actual content
# Uncomment and modify these when testing with a repo that has commits

async def test_references(simple_repo_path):
    repo = await Repository.open(simple_repo_path)
    
    # Get all references
    refs = await repo.references()
    assert isinstance(refs, list)
    
    # Get reference names
    names = await repo.reference_names()
    assert isinstance(names, list)
    
    # Try to find HEAD reference
    try:
        head_ref = await repo.find_reference("HEAD")
        assert head_ref.name == "HEAD"
    except Exception:
        # May not exist in a new repo
        pass

async def test_create_reference(simple_repo_path):
    # This test requires a repository with at least one commit
    repo = await Repository.open(simple_repo_path)
    
    # To test this properly, we'd need a commit ID
    # For now, we're just testing that the async method exists and can be called
    try:
        # Create a symbolic reference
        await repo.create_reference("refs/heads/test-branch", "HEAD", True, False)
    except Exception as e:
        # This will likely fail in a new repo, but we're just testing the async API
        pass

async def test_object_operations(simple_repo_path):
    # This test requires a repository with objects
    repo = await Repository.open(simple_repo_path)
    
    # Need an object ID to test with
    # For a new repo, we won't have any, so these will fail
    # We're just testing that the async API exists and can be called
    try:
        # Try with a fake ID that won't exist
        fake_id = "1234567890123456789012345678901234567890"
        exists = await repo.has_object(fake_id)
        assert not exists
    except Exception:
        # Expected to fail with invalid ID
        pass
"""