use gix_hash::ObjectId;
use pyo3::prelude::*;

use crate::errors::repository_error;
use crate::repository::core::{GitReference, Repository};

/// Get all references in the repository
pub(crate) fn references(repo: &Repository) -> PyResult<Vec<GitReference>> {
    let platform = match repo.inner.references() {
        Ok(platform) => platform,
        Err(err) => {
            let msg = format!("Failed to get references: {}", err);
            return Err(repository_error(msg));
        }
    };

    let refs_iter = match platform.all() {
        Ok(iter) => iter,
        Err(err) => {
            let msg = format!("Failed to get references: {}", err);
            return Err(repository_error(msg));
        }
    };

    let mut refs = Vec::new();
    for result in refs_iter {
        match result {
            Ok(r) => {
                // Convert the target based on its type
                let (target, is_symbolic) = match r.inner.target {
                    gix_ref::Target::Symbolic(name) => (name.as_bstr().to_string(), true),
                    gix_ref::Target::Object(id) => (id.to_string(), false),
                };

                refs.push(GitReference {
                    name: r.inner.name.as_bstr().to_string(),
                    target,
                    is_symbolic,
                });
            }
            Err(err) => {
                let msg = format!("Error with reference: {}", err);
                return Err(repository_error(msg));
            }
        }
    }

    Ok(refs)
}

/// Get a list of all reference names in the repository
pub(crate) fn reference_names(repo: &Repository) -> PyResult<Vec<String>> {
    let platform = match repo.inner.references() {
        Ok(platform) => platform,
        Err(err) => {
            let msg = format!("Failed to get references: {}", err);
            return Err(repository_error(msg));
        }
    };

    let refs_iter = match platform.all() {
        Ok(iter) => iter,
        Err(err) => {
            let msg = format!("Failed to get references: {}", err);
            return Err(repository_error(msg));
        }
    };

    let mut names = Vec::new();
    for result in refs_iter {
        match result {
            Ok(r) => {
                names.push(r.inner.name.as_bstr().to_string());
            }
            Err(err) => {
                let msg = format!("Error with reference: {}", err);
                return Err(repository_error(msg));
            }
        }
    }

    Ok(names)
}

/// Find a reference by name
pub(crate) fn find_reference(repo: &Repository, name: &str) -> PyResult<GitReference> {
    repo.inner
        .find_reference(name)
        .map_err(|err| {
            let msg = format!("Failed to find reference '{}': {}", name, err);
            repository_error(msg)
        })
        .map(|r| {
            let (target, is_symbolic) = match r.inner.target {
                gix_ref::Target::Symbolic(name) => (name.as_bstr().to_string(), true),
                gix_ref::Target::Object(id) => (id.to_string(), false),
            };

            GitReference {
                name: r.inner.name.as_bstr().to_string(),
                target,
                is_symbolic,
            }
        })
}

/// Create a new reference
pub(crate) fn create_reference(
    repo: &Repository,
    name: &str,
    target: &str,
    is_symbolic: bool,
    force: bool,
) -> PyResult<GitReference> {
    let constraint = if force {
        gix_ref::transaction::PreviousValue::Any
    } else {
        gix_ref::transaction::PreviousValue::MustNotExist
    };

    if is_symbolic {
        // Create symbolic reference
        let full_name = match name.try_into() {
            Ok(name) => name,
            Err(_) => {
                let msg = format!("Invalid reference name: {}", name);
                return Err(repository_error(msg));
            }
        };

        let target_name = match target.try_into() {
            Ok(name) => name,
            Err(_) => {
                let msg = format!("Invalid target reference name: {}", target);
                return Err(repository_error(msg));
            }
        };

        let log_message = format!("create: {}", name);

        let edit = gix_ref::transaction::RefEdit {
            change: gix_ref::transaction::Change::Update {
                log: gix_ref::transaction::LogChange {
                    mode: gix_ref::transaction::RefLog::AndReference,
                    force_create_reflog: false,
                    message: log_message.into(),
                },
                expected: constraint,
                new: gix_ref::Target::Symbolic(target_name),
            },
            name: full_name,
            deref: false,
        };

        match repo.inner.edit_reference(edit) {
            Ok(_) => find_reference(repo, name),
            Err(err) => {
                let msg = format!("Failed to create symbolic reference '{}': {}", name, err);
                Err(repository_error(msg))
            }
        }
    } else {
        // Create direct reference
        let object_id = match ObjectId::from_hex(target.as_bytes()) {
            Ok(id) => id,
            Err(_) => {
                let msg = format!("Invalid object ID: {}", target);
                return Err(repository_error(msg));
            }
        };

        let log_message = format!("create: {}", name);

        match repo.inner.reference(name, object_id, constraint, log_message) {
            Ok(r) => Ok(GitReference {
                name: r.inner.name.as_bstr().to_string(),
                target: object_id.to_string(),
                is_symbolic: false,
            }),
            Err(err) => {
                let msg = format!("Failed to create reference '{}': {}", name, err);
                Err(repository_error(msg))
            }
        }
    }
}

/// Get the name of the HEAD reference (e.g., "refs/heads/main")
/// or the commit ID if HEAD is detached
pub(crate) fn head(repo: &Repository) -> PyResult<String> {
    repo.inner
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
