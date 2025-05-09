use pyo3::prelude::*;
use pyo3::types::PyType;
use pyo3::PyResult;
use pyo3::{Py, PyAny};
use std::path::Path;
use tokio::runtime::Runtime;

use crate::errors::repository_error;

/// An asynchronous Git repository
#[pyclass(unsendable)]
pub struct AsyncRepository {
    inner: gix::Repository,
    runtime: Runtime,
}

#[pymethods]
impl AsyncRepository {
    /// Open an existing repository at the given path (async version)
    ///
    /// The path can be the repository's `.git` directory, or the working directory.
    #[classmethod]
    fn open(_cls: &Bound<'_, PyType>, path: &str) -> PyResult<Self> {
        let path = Path::new(path);

        // Create a new runtime for this repository
        let runtime = Runtime::new().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create Tokio runtime: {}", e))
        })?;

        // Use the runtime to open the repository - this is still synchronous,
        // but we're preparing for async operations
        let repo = gix::open(path).map_err(|err| {
            let msg = format!("Failed to open repository at {}: {}", path.display(), err);
            repository_error(msg)
        })?;

        Ok(AsyncRepository { inner: repo, runtime })
    }

    /// Initialize a new repository at the given path (async version)
    ///
    /// Args:
    ///     path: The path where the repository will be created
    ///     bare: If True, create a bare repository without a working directory
    #[classmethod]
    fn init(_cls: &Bound<'_, PyType>, path: &str, bare: bool) -> PyResult<Self> {
        let path = Path::new(path);

        // Create a new runtime for this repository
        let runtime = Runtime::new().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create Tokio runtime: {}", e))
        })?;

        // Use the appropriate init method
        let repo = if bare { gix::init_bare(path) } else { gix::init(path) }.map_err(|err| {
            let msg = format!("Failed to initialize repository at {}: {}", path.display(), err);
            repository_error(msg)
        })?;

        Ok(AsyncRepository { inner: repo, runtime })
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

    /// Example of an async method that simulates an expensive operation
    #[pyo3(name = "simulate_network_operation")]
    fn simulate_network_operation_py<'py>(&self, py: Python<'py>, delay_ms: u64) -> PyResult<Py<PyAny>> {
        // Create a Python coroutine from a Rust future
        let py_future = pyo3_async_runtimes::tokio::future_into_py(py, async move {
            // Simulate a network operation with a delay
            tokio::time::sleep(tokio::time::Duration::from_millis(delay_ms)).await;

            // Return some meaningful data
            Ok(format!("Operation completed after {}ms", delay_ms))
        })?;

        // Convert Bound<PyAny> to Py<PyAny>
        Ok(py_future.into())
    }

    // TODO: Add more truly async methods here that leverage tokio runtime
    // For example, async commits, fetches, pushes, etc.
}
