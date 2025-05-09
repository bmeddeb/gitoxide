use pyo3::exceptions::PyException;
use pyo3::prelude::*;

/// Creates a new Python exception type.
/// Used to define custom exception hierarchy.
#[pyclass(extends=PyException)]
pub struct GitoxideError {}

/// Repository-specific errors
#[pyclass(extends=PyException)]
pub struct RepositoryError {}

/// Object-specific errors
#[pyclass(extends=PyException)]
pub struct ObjectError {}

/// Reference-specific errors
#[pyclass(extends=PyException)]
pub struct ReferenceError {}

// Implementation helpers to create exceptions
impl GitoxideError {
    pub fn new_err(message: impl Into<String>) -> PyErr {
        PyException::new_err(message.into())
    }
}

impl RepositoryError {
    pub fn new_err(message: impl Into<String>) -> PyErr {
        PyException::new_err(message.into())
    }
}

impl ObjectError {
    pub fn new_err(message: impl Into<String>) -> PyErr {
        PyException::new_err(message.into())
    }
}

impl ReferenceError {
    pub fn new_err(message: impl Into<String>) -> PyErr {
        PyException::new_err(message.into())
    }
}

/// Register all exception types with the Python module
pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add exception types to the module
    m.add("GitoxideError", py.get_type::<GitoxideError>())?;
    m.add("RepositoryError", py.get_type::<RepositoryError>())?;
    m.add("ObjectError", py.get_type::<ObjectError>())?;
    m.add("ReferenceError", py.get_type::<ReferenceError>())?;

    Ok(())
}
