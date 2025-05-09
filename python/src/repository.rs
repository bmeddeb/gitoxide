use pyo3::prelude::*;
use pyo3::types::PyType;
use std::path::Path;

use crate::errors::RepositoryError;

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

        match gix::open(path) {
            Ok(repo) => Ok(Repository { inner: repo }),
            Err(err) => {
                let msg = format!("Failed to open repository at {}: {}", path.display(), err);
                Err(RepositoryError::new_err(msg))
            }
        }
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

        match result {
            Ok(repo) => Ok(Repository { inner: repo }),
            Err(err) => {
                let msg = format!("Failed to initialize repository at {}: {}", path.display(), err);
                Err(RepositoryError::new_err(msg))
            }
        }
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

    /// Get the name of the HEAD reference (e.g., "refs/heads/main")
    /// or the commit ID if HEAD is detached
    fn head(&self) -> PyResult<String> {
        match self.inner.head_ref() {
            Ok(Some(reference)) => Ok(reference.name().as_bstr().to_string()),
            Ok(None) => Err(RepositoryError::new_err("Repository HEAD is not set")),
            Err(err) => {
                let msg = format!("Failed to get HEAD: {}", err);
                Err(RepositoryError::new_err(msg))
            }
        }
    }
}
