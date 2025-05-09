use pyo3::prelude::*;

// Module definitions
#[cfg(feature = "async")]
mod asyncio;
mod errors;
mod repository;

/// Python bindings for gitoxide - a fast, safe Git implementation in Rust
#[pymodule]
fn gitoxide(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Register custom exception types
    register_exceptions(m)?;

    // Register the sync API
    m.add_class::<repository::Repository>()?;

    // Register the async API if enabled
    #[cfg(feature = "async")]
    {
        // Create the asyncio submodule
        let asyncio_module = PyModule::new(m.py(), "asyncio")?;
        asyncio::init_module(m.py(), &asyncio_module)?;
        m.add_submodule(&asyncio_module)?;
    }

    Ok(())
}

// Register all custom exceptions
fn register_exceptions(m: &Bound<'_, PyModule>) -> PyResult<()> {
    errors::register(m.py(), m)
}
