use pyo3::prelude::*;
use pyo3::types::PyDict;

/// A Git configuration object
///
/// This class provides access to the repository's configuration.
#[pyclass(unsendable)]
pub struct Config {
    // Hold a reference to the repository to get config on demand
    repo: gix::Repository,
}

impl Config {
    /// Create a new config object from a repository
    pub fn new(repo: &gix::Repository) -> Self {
        Self { repo: repo.clone() }
    }
}

#[pymethods]
impl Config {
    /// Get a boolean value from the configuration
    ///
    /// Args:
    ///     key: The configuration key (e.g., "core.bare")
    ///
    /// Returns:
    ///     The boolean value if the key exists and is a valid boolean,
    ///     or None if the key doesn't exist
    fn boolean(&self, key: &str) -> Option<bool> {
        self.repo.config_snapshot().boolean(key)
    }

    /// Get an integer value from the configuration
    ///
    /// Args:
    ///     key: The configuration key (e.g., "core.compression")
    ///
    /// Returns:
    ///     The integer value if the key exists and is a valid integer,
    ///     or None if the key doesn't exist
    fn integer(&self, key: &str) -> Option<i64> {
        self.repo.config_snapshot().integer(key)
    }

    /// Get a string value from the configuration
    ///
    /// Args:
    ///     key: The configuration key (e.g., "user.name")
    ///
    /// Returns:
    ///     The string value if the key exists, or None if the key doesn't exist
    fn string(&self, key: &str) -> Option<String> {
        self.repo.config_snapshot().string(key).map(|s| s.to_string())
    }

    /// Get a list of values from a multi-valued configuration key
    ///
    /// Args:
    ///     key: The configuration key (e.g., "remote.origin.fetch")
    ///
    /// Returns:
    ///     A list of string values associated with the key, or an empty list if the key doesn't exist
    fn values(&self, key: &str) -> Vec<String> {
        let mut result = Vec::new();

        // First try to get the key as a single value
        if let Some(value) = self.repo.config_snapshot().string(key) {
            result.push(value.to_string());
        }

        // For multi-valued keys, check for indexed entries (key.0, key.1, etc.)
        let config = self.repo.config_snapshot();
        let mut idx = 0;
        loop {
            let indexed_key = format!("{}.{}", key, idx);
            if let Some(value) = config.string(&indexed_key) {
                result.push(value.to_string());
                idx += 1;
            } else {
                break;
            }
        }

        result
    }

    /// List configuration entries for common sections
    ///
    /// Returns:
    ///     A dictionary of {key: value} pairs for common configuration sections
    fn entries(&self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new(py);
        let config = self.repo.config_snapshot();

        // Define common section-key pairs to check
        let sections = [
            (
                "core",
                vec!["bare", "filemode", "ignorecase", "compression", "worktree"],
            ),
            ("user", vec!["name", "email"]),
            ("remote.origin", vec!["url", "fetch"]),
            ("branch.main", vec!["remote", "merge"]),
            ("init", vec!["defaultBranch"]),
        ];

        // Add values to the dictionary
        for (section, keys) in sections.iter() {
            for key in keys {
                let full_key = format!("{}.{}", section, key);

                // Try to get value as string first
                if let Some(value) = config.string(&full_key) {
                    let _ = dict.set_item(&full_key, value.to_string());
                    continue;
                }

                // Try boolean
                if let Some(value) = config.boolean(&full_key) {
                    let _ = dict.set_item(&full_key, value.to_string());
                    continue;
                }

                // Try integer
                if let Some(value) = config.integer(&full_key) {
                    let _ = dict.set_item(&full_key, value.to_string());
                }
            }
        }

        dict.into()
    }

    /// Check if a configuration key exists
    ///
    /// Args:
    ///     key: The configuration key to check
    ///
    /// Returns:
    ///     True if the key exists, False otherwise
    fn has_key(&self, key: &str) -> bool {
        let config = self.repo.config_snapshot();
        config.string(key).is_some() || config.boolean(key).is_some() || config.integer(key).is_some()
    }
}
