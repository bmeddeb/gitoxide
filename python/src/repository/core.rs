use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyType};
use std::path::Path;

use crate::errors::repository_error;

#[pyclass(unsendable)]
pub struct GitObject {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub kind: String,
    #[pyo3(get)]
    pub data: Py<PyBytes>,
}

#[pyclass(unsendable)]
pub struct ObjectHeader {
    #[pyo3(get)]
    pub kind: String,
    #[pyo3(get)]
    pub size: u64,
}

#[pyclass(unsendable)]
pub struct GitReference {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub is_symbolic: bool,
}

/// A Git repository
#[pyclass(unsendable)]
pub struct Repository {
    pub(crate) inner: gix::Repository,
}

#[pymethods]
impl Repository {
    /// Open an existing repository at the given path
    ///
    /// The path can be the repository's `.git` directory, or the working directory.
    #[classmethod]
    fn open(_cls: &Bound<'_, PyType>, path: &str) -> PyResult<Self> {
        let path = Path::new(path);

        gix::open(path)
            .map_err(|err| {
                let msg = format!("Failed to open repository at {}: {}", path.display(), err);
                repository_error(msg)
            })
            .map(|repo| Repository { inner: repo })
    }

    /// Initialize a new repository at the given path
    ///
    /// Args:
    ///     path: The path where the repository will be created
    ///     bare: If True, create a bare repository without a working directory
    #[classmethod]
    fn init(_cls: &Bound<'_, PyType>, path: &str, bare: bool) -> PyResult<Self> {
        let path = Path::new(path);

        // Use the appropriate init method
        let result = if bare { gix::init_bare(path) } else { gix::init(path) };

        result
            .map_err(|err| {
                let msg = format!("Failed to initialize repository at {}: {}", path.display(), err);
                repository_error(msg)
            })
            .map(|repo| Repository { inner: repo })
    }

    /// Get the path to the repository's .git directory
    fn git_dir(&self) -> String {
        self.inner.git_dir().to_string_lossy().into_owned()
    }

    /// Get the path to the repository's working directory, if it has one
    fn work_dir(&self) -> Option<String> {
        self.inner.workdir().map(|p| p.to_string_lossy().into_owned())
    }

    /// Check if the repository is bare (has no working directory)
    fn is_bare(&self) -> bool {
        self.inner.is_bare()
    }

    /// Check if the repository is a shallow clone
    ///
    /// A shallow repository contains history only up to a certain depth.
    fn is_shallow(&self) -> bool {
        self.inner.is_shallow()
    }

    /// Get the path to the shallow file
    ///
    /// The shallow file contains hashes, one per line, that describe commits
    /// that don't have their parents within this repository.
    /// Note that the file may not exist if the repository isn't actually shallow.
    fn shallow_file(&self) -> String {
        self.inner.shallow_file().to_string_lossy().into_owned()
    }

    /// Get the list of shallow commits
    ///
    /// The list of shallow commits represents the shallow boundary, beyond which
    /// we are lacking all (parent) commits. Returns None if the repository isn't
    /// a shallow clone.
    fn shallow_commits(&self) -> PyResult<Option<Vec<String>>> {
        match self.inner.shallow_commits() {
            Ok(Some(commits)) => {
                let commit_strs = commits.iter().map(|id| id.to_string()).collect();
                Ok(Some(commit_strs))
            }
            Ok(None) => Ok(None),
            Err(err) => {
                let msg = format!("Failed to get shallow commits: {}", err);
                Err(repository_error(msg))
            }
        }
    }

    /// Get the hash algorithm used for Git objects in this repository
    fn object_hash(&self) -> String {
        format!("{:?}", self.inner.object_hash())
    }

    // Object-related methods

    /// Find a Git object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject containing the object's ID, kind, and data
    fn find_object(&self, id: &str) -> PyResult<GitObject> {
        crate::repository::objects::find_object(self, id)
    }

    /// Find a blob object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Blob"
    fn find_blob(&self, id: &str) -> PyResult<GitObject> {
        crate::repository::objects::find_blob(self, id)
    }

    /// Find a commit object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Commit"
    fn find_commit(&self, id: &str) -> PyResult<GitObject> {
        crate::repository::objects::find_commit(self, id)
    }

    /// Find a tree object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Tree"
    fn find_tree(&self, id: &str) -> PyResult<GitObject> {
        crate::repository::objects::find_tree(self, id)
    }

    /// Find a tag object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Tag"
    fn find_tag(&self, id: &str) -> PyResult<GitObject> {
        crate::repository::objects::find_tag(self, id)
    }

    /// Get information about an object without fully decoding it
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     An ObjectHeader containing the object's kind and size
    fn find_header(&self, id: &str) -> PyResult<ObjectHeader> {
        crate::repository::objects::find_header(self, id)
    }

    /// Check if an object exists in the repository
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     True if the object exists, False otherwise
    fn has_object(&self, id: &str) -> PyResult<bool> {
        crate::repository::objects::has_object(self, id)
    }

    // Reference-related methods

    /// Get all references in the repository
    ///
    /// Returns a list of all references (branches, tags, etc.)
    fn references(&self) -> PyResult<Vec<GitReference>> {
        crate::repository::references::references(self)
    }

    /// Get a list of all reference names in the repository
    fn reference_names(&self) -> PyResult<Vec<String>> {
        crate::repository::references::reference_names(self)
    }

    /// Find a reference by name
    ///
    /// Args:
    ///     name: The reference name (e.g., "HEAD", "refs/heads/main", or "main")
    ///
    /// Returns:
    ///     A GitReference if found
    fn find_reference(&self, name: &str) -> PyResult<GitReference> {
        crate::repository::references::find_reference(self, name)
    }

    /// Create a new reference
    ///
    /// Args:
    ///     name: The reference name (e.g., "refs/heads/branch-name")
    ///     target: The target object ID or reference name
    ///     is_symbolic: If True, create a symbolic reference pointing to another reference
    ///     force: If True, overwrite the reference if it already exists
    ///
    /// Returns:
    ///     A GitReference representing the newly created reference
    fn create_reference(&self, name: &str, target: &str, is_symbolic: bool, force: bool) -> PyResult<GitReference> {
        crate::repository::references::create_reference(self, name, target, is_symbolic, force)
    }

    /// Get the name of the HEAD reference (e.g., "refs/heads/main")
    /// or the commit ID if HEAD is detached
    fn head(&self) -> PyResult<String> {
        crate::repository::references::head(self)
    }

    // Revision-related methods

    /// Find all merge bases between one commit and multiple other commits
    ///
    /// Args:
    ///     one: First commit ID as a string
    ///     others: List of other commit IDs to find merge bases with
    ///
    /// Returns:
    ///     List of commit IDs that are merge bases
    ///
    /// Raises:
    ///     RepositoryError: If one of the commit IDs is invalid
    fn merge_bases(&self, one: &str, others: Vec<String>) -> PyResult<Vec<String>> {
        crate::repository::revisions::merge_bases(self, one, others)
    }

    /// Find the best merge base between two commits
    ///
    /// Args:
    ///     one: First commit ID as a string
    ///     two: Second commit ID as a string
    ///
    /// Returns:
    ///     The commit ID of the merge base
    ///
    /// Raises:
    ///     RepositoryError: If a commit ID is invalid or no merge base exists
    fn merge_base(&self, one: &str, two: &str) -> PyResult<String> {
        crate::repository::revisions::merge_base(self, one, two)
    }

    /// Parse a revision specification and return a single commit/object ID
    ///
    /// Args:
    ///     spec: The revision specification (e.g., "HEAD", "main~3", "v1.0^{}")
    ///
    /// Returns:
    ///     The object ID that the revision specification resolves to
    ///
    /// Raises:
    ///     RepositoryError: If the specification is invalid or cannot be resolved
    fn rev_parse(&self, spec: &str) -> PyResult<String> {
        crate::repository::revisions::rev_parse(self, spec)
    }

    /// Find the best merge base among multiple commits
    ///
    /// Args:
    ///     commits: A list of commit IDs
    ///
    /// Returns:
    ///     The best common ancestor commit ID
    ///
    /// Raises:
    ///     RepositoryError: If no commits are provided, if any commit ID is invalid, or if no merge base exists
    fn merge_base_octopus(&self, commits: Vec<String>) -> PyResult<String> {
        crate::repository::revisions::merge_base_octopus(self, commits)
    }

    // Config-related methods

    /// Access the repository's configuration
    ///
    /// Returns a Config object that provides access to the repository's configuration.
    ///
    /// Returns:
    ///     A Config object for accessing configuration values
    fn config(&self) -> crate::repository::Config {
        crate::repository::config::config(self)
    }
}
