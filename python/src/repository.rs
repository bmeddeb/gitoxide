use gix_hash::ObjectId;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyType};
use std::path::Path;

use crate::config::Config;
use crate::errors::repository_error;

#[pyclass(unsendable)]
struct GitObject {
    #[pyo3(get)]
    id: String,
    #[pyo3(get)]
    kind: String,
    #[pyo3(get)]
    data: Py<PyBytes>,
}

#[pyclass(unsendable)]
struct ObjectHeader {
    #[pyo3(get)]
    kind: String,
    #[pyo3(get)]
    size: u64,
}

#[pyclass(unsendable)]
struct GitReference {
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    target: String,
    #[pyo3(get)]
    is_symbolic: bool,
}

/// A Git repository
#[pyclass(unsendable)]
pub struct Repository {
    inner: gix::Repository,
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

    /// Find a Git object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject containing the object's ID, kind, and data
    fn find_object(&self, id: &str) -> PyResult<GitObject> {
        let object_id =
            ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

        self.inner
            .find_object(object_id)
            .map_err(|err| {
                let msg = format!("Failed to find object {}: {}", id, err);
                repository_error(msg)
            })
            .map(|obj| {
                Python::with_gil(|py| {
                    let bytes = PyBytes::new(py, &obj.data);
                    GitObject {
                        id: obj.id.to_string(),
                        kind: format!("{:?}", obj.kind),
                        data: bytes.into(),
                    }
                })
            })
    }

    /// Find a blob object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Blob"
    fn find_blob(&self, id: &str) -> PyResult<GitObject> {
        let object_id =
            ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

        self.inner
            .find_blob(object_id)
            .map_err(|err| {
                let msg = format!("Failed to find blob {}: {}", id, err);
                repository_error(msg)
            })
            .map(|blob| {
                Python::with_gil(|py| {
                    let bytes = PyBytes::new(py, &blob.data);
                    GitObject {
                        id: blob.id.to_string(),
                        kind: "Blob".to_string(),
                        data: bytes.into(),
                    }
                })
            })
    }

    /// Find a commit object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Commit"
    fn find_commit(&self, id: &str) -> PyResult<GitObject> {
        let object_id =
            ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

        self.inner
            .find_commit(object_id)
            .map_err(|err| {
                let msg = format!("Failed to find commit {}: {}", id, err);
                repository_error(msg)
            })
            .map(|commit| {
                Python::with_gil(|py| {
                    let bytes = PyBytes::new(py, &commit.data);
                    GitObject {
                        id: commit.id.to_string(),
                        kind: "Commit".to_string(),
                        data: bytes.into(),
                    }
                })
            })
    }

    /// Find a tree object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Tree"
    fn find_tree(&self, id: &str) -> PyResult<GitObject> {
        let object_id =
            ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

        self.inner
            .find_tree(object_id)
            .map_err(|err| {
                let msg = format!("Failed to find tree {}: {}", id, err);
                repository_error(msg)
            })
            .map(|tree| {
                Python::with_gil(|py| {
                    let bytes = PyBytes::new(py, &tree.data);
                    GitObject {
                        id: tree.id.to_string(),
                        kind: "Tree".to_string(),
                        data: bytes.into(),
                    }
                })
            })
    }

    /// Find a tag object by its ID
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Tag"
    fn find_tag(&self, id: &str) -> PyResult<GitObject> {
        let object_id =
            ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

        self.inner
            .find_tag(object_id)
            .map_err(|err| {
                let msg = format!("Failed to find tag {}: {}", id, err);
                repository_error(msg)
            })
            .map(|tag| {
                Python::with_gil(|py| {
                    let bytes = PyBytes::new(py, &tag.data);
                    GitObject {
                        id: tag.id.to_string(),
                        kind: "Tag".to_string(),
                        data: bytes.into(),
                    }
                })
            })
    }

    /// Get information about an object without fully decoding it
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     An ObjectHeader containing the object's kind and size
    fn find_header(&self, id: &str) -> PyResult<ObjectHeader> {
        let object_id =
            ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

        self.inner
            .find_header(object_id)
            .map_err(|err| {
                let msg = format!("Failed to find header for {}: {}", id, err);
                repository_error(msg)
            })
            .map(|header| {
                let kind = header.kind();
                let size = header.size();

                ObjectHeader {
                    kind: format!("{:?}", kind),
                    size,
                }
            })
    }

    /// Check if an object exists in the repository
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     True if the object exists, False otherwise
    fn has_object(&self, id: &str) -> PyResult<bool> {
        let object_id =
            ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

        Ok(self.inner.has_object(&object_id))
    }

    /// Get all references in the repository
    ///
    /// Returns a list of all references (branches, tags, etc.)
    fn references(&self) -> PyResult<Vec<GitReference>> {
        let platform = match self.inner.references() {
            Ok(platform) => platform,
            Err(err) => {
                let msg = format!("Failed to get references: {}", err);
                return Err(repository_error(msg));
            }
        };

        let refs_iter = match platform.all() {
            Ok(iter) => iter,
            Err(err) => {
                let msg = format!("Failed to get references: {}", err);
                return Err(repository_error(msg));
            }
        };

        let mut refs = Vec::new();
        for result in refs_iter {
            match result {
                Ok(r) => {
                    // Convert the target based on its type
                    let (target, is_symbolic) = match r.inner.target {
                        gix_ref::Target::Symbolic(name) => (name.as_bstr().to_string(), true),
                        gix_ref::Target::Object(id) => (id.to_string(), false),
                    };

                    refs.push(GitReference {
                        name: r.inner.name.as_bstr().to_string(),
                        target,
                        is_symbolic,
                    });
                }
                Err(err) => {
                    let msg = format!("Error with reference: {}", err);
                    return Err(repository_error(msg));
                }
            }
        }

        Ok(refs)
    }

    /// Get a list of all reference names in the repository
    fn reference_names(&self) -> PyResult<Vec<String>> {
        let platform = match self.inner.references() {
            Ok(platform) => platform,
            Err(err) => {
                let msg = format!("Failed to get references: {}", err);
                return Err(repository_error(msg));
            }
        };

        let refs_iter = match platform.all() {
            Ok(iter) => iter,
            Err(err) => {
                let msg = format!("Failed to get references: {}", err);
                return Err(repository_error(msg));
            }
        };

        let mut names = Vec::new();
        for result in refs_iter {
            match result {
                Ok(r) => {
                    names.push(r.inner.name.as_bstr().to_string());
                }
                Err(err) => {
                    let msg = format!("Error with reference: {}", err);
                    return Err(repository_error(msg));
                }
            }
        }

        Ok(names)
    }

    /// Find a reference by name
    ///
    /// Args:
    ///     name: The reference name (e.g., "HEAD", "refs/heads/main", or "main")
    ///
    /// Returns:
    ///     A GitReference if found
    fn find_reference(&self, name: &str) -> PyResult<GitReference> {
        self.inner
            .find_reference(name)
            .map_err(|err| {
                let msg = format!("Failed to find reference '{}': {}", name, err);
                repository_error(msg)
            })
            .map(|r| {
                let (target, is_symbolic) = match r.inner.target {
                    gix_ref::Target::Symbolic(name) => (name.as_bstr().to_string(), true),
                    gix_ref::Target::Object(id) => (id.to_string(), false),
                };

                GitReference {
                    name: r.inner.name.as_bstr().to_string(),
                    target,
                    is_symbolic,
                }
            })
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
        let constraint = if force {
            gix_ref::transaction::PreviousValue::Any
        } else {
            gix_ref::transaction::PreviousValue::MustNotExist
        };

        if is_symbolic {
            // Create symbolic reference
            let full_name = match name.try_into() {
                Ok(name) => name,
                Err(_) => {
                    let msg = format!("Invalid reference name: {}", name);
                    return Err(repository_error(msg));
                }
            };

            let target_name = match target.try_into() {
                Ok(name) => name,
                Err(_) => {
                    let msg = format!("Invalid target reference name: {}", target);
                    return Err(repository_error(msg));
                }
            };

            let log_message = format!("create: {}", name);

            let edit = gix_ref::transaction::RefEdit {
                change: gix_ref::transaction::Change::Update {
                    log: gix_ref::transaction::LogChange {
                        mode: gix_ref::transaction::RefLog::AndReference,
                        force_create_reflog: false,
                        message: log_message.into(),
                    },
                    expected: constraint,
                    new: gix_ref::Target::Symbolic(target_name),
                },
                name: full_name,
                deref: false,
            };

            match self.inner.edit_reference(edit) {
                Ok(_) => self.find_reference(name),
                Err(err) => {
                    let msg = format!("Failed to create symbolic reference '{}': {}", name, err);
                    Err(repository_error(msg))
                }
            }
        } else {
            // Create direct reference
            let object_id = match ObjectId::from_hex(target.as_bytes()) {
                Ok(id) => id,
                Err(_) => {
                    let msg = format!("Invalid object ID: {}", target);
                    return Err(repository_error(msg));
                }
            };

            let log_message = format!("create: {}", name);

            match self.inner.reference(name, object_id, constraint, log_message) {
                Ok(r) => Ok(GitReference {
                    name: r.inner.name.as_bstr().to_string(),
                    target: object_id.to_string(),
                    is_symbolic: false,
                }),
                Err(err) => {
                    let msg = format!("Failed to create reference '{}': {}", name, err);
                    Err(repository_error(msg))
                }
            }
        }
    }

    /// Get the name of the HEAD reference (e.g., "refs/heads/main")
    /// or the commit ID if HEAD is detached
    fn head(&self) -> PyResult<String> {
        self.inner
            .head_ref()
            .map_err(|err| {
                let msg = format!("Failed to get HEAD: {}", err);
                repository_error(msg)
            })
            .and_then(|opt_ref| match opt_ref {
                Some(reference) => Ok(reference.name().as_bstr().to_string()),
                None => Err(repository_error("Repository HEAD is not set")),
            })
    }

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
        // Parse the first commit ID
        let first_id = ObjectId::from_hex(one.as_bytes())
            .map_err(|_| repository_error(format!("Invalid object ID for first commit: {}", one)))?;

        // Parse the other commit IDs
        let mut other_ids = Vec::with_capacity(others.len());
        for (idx, other) in others.iter().enumerate() {
            let id = ObjectId::from_hex(other.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID for other commit {}: {}", idx, other)))?;
            other_ids.push(id);
        }

        // Get the commit graph
        let cache = self
            .inner
            .commit_graph_if_enabled()
            .map_err(|err| repository_error(format!("Failed to retrieve commit graph: {}", err)))?;
        let mut graph = self.inner.revision_graph(cache.as_ref());

        // Find the merge bases
        self.inner
            .merge_bases_many_with_graph(first_id, &other_ids, &mut graph)
            .map_err(|err| repository_error(format!("Failed to find merge bases: {}", err)))
            .map(|bases| bases.iter().map(|id| id.to_string()).collect())
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
        // Parse the commit IDs
        let first_id = ObjectId::from_hex(one.as_bytes())
            .map_err(|_| repository_error(format!("Invalid object ID for first commit: {}", one)))?;

        let second_id = ObjectId::from_hex(two.as_bytes())
            .map_err(|_| repository_error(format!("Invalid object ID for second commit: {}", two)))?;

        // Find the merge base
        self.inner
            .merge_base(first_id, second_id)
            .map_err(|err| repository_error(format!("Failed to find merge base: {}", err)))
            .map(|id| id.to_string())
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
        self.inner
            .rev_parse_single(spec)
            .map_err(|err| repository_error(format!("Failed to parse revision '{}': {}", spec, err)))
            .map(|id| id.to_string())
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
        // Check if we have at least one commit
        if commits.is_empty() {
            return Err(repository_error(
                "No commits provided for merge_base_octopus".to_string(),
            ));
        }

        // Convert string IDs to ObjectIds
        let commit_ids: Result<Vec<_>, _> = commits
            .iter()
            .map(|id_str| {
                ObjectId::from_hex(id_str.as_bytes())
                    .map_err(|_| repository_error(format!("Invalid object ID: {}", id_str)))
            })
            .collect();

        let commit_ids = commit_ids?;

        // Get the commit graph
        let _cache = self
            .inner
            .commit_graph_if_enabled()
            .map_err(|err| repository_error(format!("Failed to retrieve commit graph: {}", err)))?;

        // Find the merge base
        self.inner
            .merge_base_octopus(commit_ids)
            .map_err(|err| repository_error(format!("Failed to find merge base octopus: {}", err)))
            .map(|id| id.to_string())
    }

    /// Access the repository's configuration
    ///
    /// Returns a Config object that provides access to the repository's configuration.
    ///
    /// Returns:
    ///     A Config object for accessing configuration values
    fn config(&self) -> Config {
        Config::new(&self.inner)
    }
}