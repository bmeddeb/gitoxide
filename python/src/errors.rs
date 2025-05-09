use pyo3::prelude::*;
use pyo3::PyErr;

// Using Python's built-in exceptions directly
pub mod exceptions {
    use pyo3::create_exception;
    use pyo3::exceptions::PyException;

    // Create a hierarchy of exceptions
    create_exception!(gitoxide, GitoxideError, PyException);
    create_exception!(gitoxide, RepositoryError, GitoxideError);
    create_exception!(gitoxide, ObjectError, GitoxideError);
    create_exception!(gitoxide, ReferenceError, GitoxideError);
    create_exception!(gitoxide, ConfigError, GitoxideError);
    create_exception!(gitoxide, IndexError, GitoxideError);
    create_exception!(gitoxide, DiffError, GitoxideError);
    create_exception!(gitoxide, TraverseError, GitoxideError);
    create_exception!(gitoxide, WorktreeError, GitoxideError);
    create_exception!(gitoxide, RevisionError, GitoxideError);
    create_exception!(gitoxide, RemoteError, GitoxideError);
    create_exception!(gitoxide, TransportError, GitoxideError);
    create_exception!(gitoxide, ProtocolError, GitoxideError);
    create_exception!(gitoxide, PackError, GitoxideError);
    create_exception!(gitoxide, FSError, GitoxideError);
}

// Import all exceptions for easier access
use exceptions::*;

// Helper functions to create exceptions
pub fn repository_error(message: impl Into<String>) -> PyErr {
    RepositoryError::new_err(message.into())
}

#[allow(dead_code)]
pub fn object_error(message: impl Into<String>) -> PyErr {
    ObjectError::new_err(message.into())
}

#[allow(dead_code)]
pub fn reference_error(message: impl Into<String>) -> PyErr {
    ReferenceError::new_err(message.into())
}

#[allow(dead_code)]
pub fn config_error(message: impl Into<String>) -> PyErr {
    ConfigError::new_err(message.into())
}

#[allow(dead_code)]
pub fn index_error(message: impl Into<String>) -> PyErr {
    IndexError::new_err(message.into())
}

#[allow(dead_code)]
pub fn diff_error(message: impl Into<String>) -> PyErr {
    DiffError::new_err(message.into())
}

#[allow(dead_code)]
pub fn traverse_error(message: impl Into<String>) -> PyErr {
    TraverseError::new_err(message.into())
}

#[allow(dead_code)]
pub fn worktree_error(message: impl Into<String>) -> PyErr {
    WorktreeError::new_err(message.into())
}

#[allow(dead_code)]
pub fn revision_error(message: impl Into<String>) -> PyErr {
    RevisionError::new_err(message.into())
}

#[allow(dead_code)]
pub fn remote_error(message: impl Into<String>) -> PyErr {
    RemoteError::new_err(message.into())
}

#[allow(dead_code)]
pub fn transport_error(message: impl Into<String>) -> PyErr {
    TransportError::new_err(message.into())
}

#[allow(dead_code)]
pub fn protocol_error(message: impl Into<String>) -> PyErr {
    ProtocolError::new_err(message.into())
}

#[allow(dead_code)]
pub fn pack_error(message: impl Into<String>) -> PyErr {
    PackError::new_err(message.into())
}

#[allow(dead_code)]
pub fn fs_error(message: impl Into<String>) -> PyErr {
    FSError::new_err(message.into())
}

/// Trait to convert from Rust errors to Python exceptions
pub trait IntoPyErr {
    fn into_py_err(self) -> PyErr;
}

// Specific implementations for particular error types

/// Specialized conversion for gix::open errors to RepositoryError
impl IntoPyErr for gix::open::Error {
    fn into_py_err(self) -> PyErr {
        repository_error(self.to_string())
    }
}

/// Specialized conversion for gix::init errors to RepositoryError
impl IntoPyErr for gix::init::Error {
    fn into_py_err(self) -> PyErr {
        repository_error(self.to_string())
    }
}

/// For any Result<T, E> where E implements IntoPyErr, this converts to PyResult<T>
#[allow(dead_code)]
pub trait IntoPyResult<T> {
    fn into_py_result(self) -> PyResult<T>;
}

#[allow(dead_code)]
impl<T, E: IntoPyErr> IntoPyResult<T> for Result<T, E> {
    fn into_py_result(self) -> PyResult<T> {
        self.map_err(|e| e.into_py_err())
    }
}

/// Register all exception types with the Python module
pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add exception types to the module
    m.add("GitoxideError", py.get_type::<exceptions::GitoxideError>())?;
    m.add("RepositoryError", py.get_type::<exceptions::RepositoryError>())?;
    m.add("ObjectError", py.get_type::<exceptions::ObjectError>())?;
    m.add("ReferenceError", py.get_type::<exceptions::ReferenceError>())?;
    m.add("ConfigError", py.get_type::<exceptions::ConfigError>())?;
    m.add("IndexError", py.get_type::<exceptions::IndexError>())?;
    m.add("DiffError", py.get_type::<exceptions::DiffError>())?;
    m.add("TraverseError", py.get_type::<exceptions::TraverseError>())?;
    m.add("WorktreeError", py.get_type::<exceptions::WorktreeError>())?;
    m.add("RevisionError", py.get_type::<exceptions::RevisionError>())?;
    m.add("RemoteError", py.get_type::<exceptions::RemoteError>())?;
    m.add("TransportError", py.get_type::<exceptions::TransportError>())?;
    m.add("ProtocolError", py.get_type::<exceptions::ProtocolError>())?;
    m.add("PackError", py.get_type::<exceptions::PackError>())?;
    m.add("FSError", py.get_type::<exceptions::FSError>())?;

    Ok(())
}
