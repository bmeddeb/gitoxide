// Submodules
mod config;
mod core;
mod objects;
mod references;
mod revisions;

// Re-export the Repository struct for the public API
pub use config::Config;
pub use core::Repository;

// Re-export any other public items
