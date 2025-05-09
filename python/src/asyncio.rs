use pyo3::prelude::*;

pub fn init_module(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // We'll implement async functionality later
    Ok(())
}
