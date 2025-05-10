mod core;

// Re-export the Config struct for the public API
pub use core::Config;

// Function to create a Config from a Repository
pub fn config(repo: &crate::repository::core::Repository) -> Config {
    Config::new(&repo.inner)
}
