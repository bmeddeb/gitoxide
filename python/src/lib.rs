use pyo3::prelude::*;

// Module definitions
#[cfg(feature = "async")]
mod asyncio;
mod errors;
mod repository;

/// Python bindings for gitoxide - a fast, safe Git implementation in Rust
#[pymodule]
fn gitoxide(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Register custom exception types
    register_exceptions(m)?;

    // Register the sync API
    m.add_class::<repository::Repository>()?;

    // Register the async API if enabled
    #[cfg(feature = "async")]
    {
        // Add AsyncRepository directly at the top level
        m.add_class::<asyncio::Repository>()?;
        m.add("ASYNC_AVAILABLE", true)?;
    }
    #[cfg(not(feature = "async"))]
    {
        m.add("ASYNC_AVAILABLE", false)?;
    }

    Ok(())
}

// Register all custom exceptions
fn register_exceptions(m: &Bound<'_, PyModule>) -> PyResult<()> {
    errors::register(m.py(), m)
}