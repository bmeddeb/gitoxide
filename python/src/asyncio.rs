use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyType};
use std::path::Path;
use gix_hash::ObjectId;
use gix_odb;
use pyo3_async_runtimes::tokio;

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

/// A Git repository with async operations
#[pyclass(unsendable)]
pub struct Repository {
    inner: gix::Repository,
}

#[pymethods]
impl Repository {
    /// Open an existing repository at the given path asynchronously
    ///
    /// The path can be the repository's `.git` directory, or the working directory.
    #[classmethod]
    #[pyo3(text_signature = "(cls, path)")]
    fn open<'py>(
        cls: &Bound<'_, PyType>,
        path: &str,
        py: Python<'py>,
    ) -> PyResult<&'py PyAny> {
        let path = Path::new(path).to_owned();
        tokio::future_into_py(py, async move {
            let result = gix::open(&path);
            match result {
                Ok(repo) => Ok(Repository { inner: repo }),
                Err(err) => {
                    let msg = format!("Failed to open repository at {}: {}", path.display(), err);
                    Err(repository_error(msg))
                }
            }
        })
    }

    /// Initialize a new repository at the given path asynchronously
    ///
    /// Args:
    ///     path: The path where the repository will be created
    ///     bare: If True, create a bare repository without a working directory
    #[classmethod]
    #[pyo3(text_signature = "(cls, path, bare=False)")]
    fn init<'py>(
        cls: &Bound<'_, PyType>,
        path: &str,
        bare: Option<bool>,
        py: Python<'py>,
    ) -> PyResult<&'py PyAny> {
        let path = Path::new(path).to_owned();
        let bare = bare.unwrap_or(false);
        tokio::future_into_py(py, async move {
            // Use the appropriate init method
            let result = if bare {
                gix::init_bare(&path)
            } else {
                gix::init(&path)
            };

            match result {
                Ok(repo) => Ok(Repository { inner: repo }),
                Err(err) => {
                    let msg = format!("Failed to initialize repository at {}: {}", path.display(), err);
                    Err(repository_error(msg))
                }
            }
        })
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

    /// Get the list of shallow commits asynchronously
    ///
    /// The list of shallow commits represents the shallow boundary, beyond which
    /// we are lacking all (parent) commits. Returns None if the repository isn't
    /// a shallow clone.
    fn shallow_commits<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            match repo.shallow_commits() {
                Ok(Some(commits)) => {
                    let commit_strs = commits.iter().map(|id| id.to_string()).collect::<Vec<_>>();
                    Ok(Some(commit_strs))
                }
                Ok(None) => Ok(None),
                Err(err) => {
                    let msg = format!("Failed to get shallow commits: {}", err);
                    Err(repository_error(msg))
                }
            }
        })
    }

    /// Get the hash algorithm used for Git objects in this repository
    fn object_hash(&self) -> String {
        format!("{:?}", self.inner.object_hash())
    }

    /// Find a Git object by its ID asynchronously
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject containing the object's ID, kind, and data
    fn find_object<'py>(&self, id: &str, py: Python<'py>) -> PyResult<&'py PyAny> {
        let id = id.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let object_id = ObjectId::from_hex(id.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

            let obj = repo.find_object(object_id)
                .map_err(|err| {
                    let msg = format!("Failed to find object {}: {}", id, err);
                    repository_error(msg)
                })?;

            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &obj.data);
                Ok(GitObject {
                    id: obj.id.to_string(),
                    kind: format!("{:?}", obj.kind),
                    data: bytes.into(),
                })
            })
        })
    }

    /// Find a blob object by its ID asynchronously
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Blob"
    fn find_blob<'py>(&self, id: &str, py: Python<'py>) -> PyResult<&'py PyAny> {
        let id = id.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let object_id = ObjectId::from_hex(id.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

            let blob = repo.find_blob(object_id)
                .map_err(|err| {
                    let msg = format!("Failed to find blob {}: {}", id, err);
                    repository_error(msg)
                })?;

            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &blob.data);
                Ok(GitObject {
                    id: blob.id.to_string(),
                    kind: "Blob".to_string(),
                    data: bytes.into(),
                })
            })
        })
    }

    /// Find a commit object by its ID asynchronously
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Commit"
    fn find_commit<'py>(&self, id: &str, py: Python<'py>) -> PyResult<&'py PyAny> {
        let id = id.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let object_id = ObjectId::from_hex(id.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

            let commit = repo.find_commit(object_id)
                .map_err(|err| {
                    let msg = format!("Failed to find commit {}: {}", id, err);
                    repository_error(msg)
                })?;

            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &commit.data);
                Ok(GitObject {
                    id: commit.id.to_string(),
                    kind: "Commit".to_string(),
                    data: bytes.into(),
                })
            })
        })
    }

    /// Find a tree object by its ID asynchronously
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Tree"
    fn find_tree<'py>(&self, id: &str, py: Python<'py>) -> PyResult<&'py PyAny> {
        let id = id.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let object_id = ObjectId::from_hex(id.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

            let tree = repo.find_tree(object_id)
                .map_err(|err| {
                    let msg = format!("Failed to find tree {}: {}", id, err);
                    repository_error(msg)
                })?;

            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &tree.data);
                Ok(GitObject {
                    id: tree.id.to_string(),
                    kind: "Tree".to_string(),
                    data: bytes.into(),
                })
            })
        })
    }

    /// Find a tag object by its ID asynchronously
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     A GitObject with kind="Tag"
    fn find_tag<'py>(&self, id: &str, py: Python<'py>) -> PyResult<&'py PyAny> {
        let id = id.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let object_id = ObjectId::from_hex(id.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

            let tag = repo.find_tag(object_id)
                .map_err(|err| {
                    let msg = format!("Failed to find tag {}: {}", id, err);
                    repository_error(msg)
                })?;

            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &tag.data);
                Ok(GitObject {
                    id: tag.id.to_string(),
                    kind: "Tag".to_string(),
                    data: bytes.into(),
                })
            })
        })
    }

    /// Get information about an object without fully decoding it asynchronously
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     An ObjectHeader containing the object's kind and size
    fn find_header<'py>(&self, id: &str, py: Python<'py>) -> PyResult<&'py PyAny> {
        let id = id.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let object_id = ObjectId::from_hex(id.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

            let header = repo.find_header(object_id)
                .map_err(|err| {
                    let msg = format!("Failed to find header for {}: {}", id, err);
                    repository_error(msg)
                })?;

            let kind = header.kind();
            let size = header.size();

            Ok(ObjectHeader {
                kind: format!("{:?}", kind),
                size,
            })
        })
    }

    /// Check if an object exists in the repository asynchronously
    ///
    /// Args:
    ///     id: The object ID (SHA) as a string
    ///
    /// Returns:
    ///     True if the object exists, False otherwise
    fn has_object<'py>(&self, id: &str, py: Python<'py>) -> PyResult<&'py PyAny> {
        let id = id.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let object_id = ObjectId::from_hex(id.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

            Ok(repo.has_object(&object_id))
        })
    }

    /// Get all references in the repository asynchronously
    ///
    /// Returns a list of all references (branches, tags, etc.)
    fn references<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let refs_iter = match repo.references() {
                Ok(iter) => iter.all(),
                Err(err) => {
                    let msg = format!("Failed to get references: {}", err);
                    return Err(repository_error(msg));
                }
            };

            let mut refs = Vec::new();
            for iter_result in refs_iter {
                match iter_result {
                    Ok(reference_iter) => {
                        for ref_result in reference_iter {
                            match ref_result {
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
                    }
                    Err(err) => {
                        let msg = format!("Error iterating references: {}", err);
                        return Err(repository_error(msg));
                    }
                }
            }

            Ok(refs)
        })
    }

    /// Get a list of all reference names in the repository asynchronously
    fn reference_names<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let refs_iter = match repo.references() {
                Ok(iter) => iter.all(),
                Err(err) => {
                    let msg = format!("Failed to get references: {}", err);
                    return Err(repository_error(msg));
                }
            };

            let mut names = Vec::new();
            for iter_result in refs_iter {
                match iter_result {
                    Ok(reference_iter) => {
                        for ref_result in reference_iter {
                            match ref_result {
                                Ok(r) => {
                                    names.push(r.inner.name.as_bstr().to_string());
                                }
                                Err(err) => {
                                    let msg = format!("Error with reference: {}", err);
                                    return Err(repository_error(msg));
                                }
                            }
                        }
                    }
                    Err(err) => {
                        let msg = format!("Error iterating references: {}", err);
                        return Err(repository_error(msg));
                    }
                }
            }

            Ok(names)
        })
    }

    /// Find a reference by name asynchronously
    ///
    /// Args:
    ///     name: The reference name (e.g., "HEAD", "refs/heads/main", or "main")
    ///
    /// Returns:
    ///     A GitReference if found
    fn find_reference<'py>(&self, name: &str, py: Python<'py>) -> PyResult<&'py PyAny> {
        let name = name.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let r = repo.find_reference(&name)
                .map_err(|err| {
                    let msg = format!("Failed to find reference '{}': {}", name, err);
                    repository_error(msg)
                })?;

            let (target, is_symbolic) = match r.inner.target {
                gix_ref::Target::Symbolic(name) => (name.as_bstr().to_string(), true),
                gix_ref::Target::Object(id) => (id.to_string(), false),
            };

            Ok(GitReference {
                name: r.inner.name.as_bstr().to_string(),
                target,
                is_symbolic,
            })
        })
    }

    /// Create a new reference asynchronously
    ///
    /// Args:
    ///     name: The reference name (e.g., "refs/heads/branch-name")
    ///     target: The target object ID or reference name
    ///     is_symbolic: If True, create a symbolic reference pointing to another reference
    ///     force: If True, overwrite the reference if it already exists
    ///
    /// Returns:
    ///     A GitReference representing the newly created reference
    fn create_reference<'py>(&self, name: &str, target: &str, is_symbolic: bool, force: bool, py: Python<'py>) -> PyResult<&'py PyAny> {
        let name = name.to_string();
        let target = target.to_string();
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            let constraint = if force {
                gix_ref::transaction::PreviousValue::Any
            } else {
                gix_ref::transaction::PreviousValue::MustNotExist
            };

            if is_symbolic {
                // Create symbolic reference
                let full_name = match name.as_str().try_into() {
                    Ok(name) => name,
                    Err(_) => {
                        let msg = format!("Invalid reference name: {}", name);
                        return Err(repository_error(msg));
                    }
                };

                let target_name = match target.as_str().try_into() {
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

                match repo.edit_reference(edit) {
                    Ok(_) => {
                        let r = repo.find_reference(&name)
                            .map_err(|err| {
                                let msg = format!("Failed to retrieve created reference '{}': {}", name, err);
                                repository_error(msg)
                            })?;

                        let (target, is_symbolic) = match r.inner.target {
                            gix_ref::Target::Symbolic(name) => (name.as_bstr().to_string(), true),
                            gix_ref::Target::Object(id) => (id.to_string(), false),
                        };

                        Ok(GitReference {
                            name: r.inner.name.as_bstr().to_string(),
                            target,
                            is_symbolic,
                        })
                    },
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

                match repo.reference(&name, object_id, constraint, log_message) {
                    Ok(r) => {
                        Ok(GitReference {
                            name: r.inner.name.as_bstr().to_string(),
                            target: object_id.to_string(),
                            is_symbolic: false,
                        })
                    }
                    Err(err) => {
                        let msg = format!("Failed to create reference '{}': {}", name, err);
                        Err(repository_error(msg))
                    }
                }
            }
        })
    }

    /// Get the name of the HEAD reference (e.g., "refs/heads/main")
    /// or the commit ID if HEAD is detached
    fn head<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let repo = self.inner.clone();
        tokio::future_into_py(py, async move {
            repo.head_ref()
                .map_err(|err| {
                    let msg = format!("Failed to get HEAD: {}", err);
                    repository_error(msg)
                })
                .and_then(|opt_ref| match opt_ref {
                    Some(reference) => Ok(reference.name().as_bstr().to_string()),
                    None => Err(repository_error("Repository HEAD is not set")),
                })
        })
    }
}

pub fn init_module(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Repository>()?;
    Ok(())
}
