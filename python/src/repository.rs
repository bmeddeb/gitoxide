use pyo3::prelude::*;
use pyo3::types::PyType;
use std::path::Path;

use crate::errors::repository_error;

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
}
