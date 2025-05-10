use gix_hash::ObjectId;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::errors::repository_error;
use crate::repository::core::{GitObject, ObjectHeader, Repository};

/// Find a Git object by its ID
pub(crate) fn find_object(repo: &Repository, id: &str) -> PyResult<GitObject> {
    let object_id =
        ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

    repo.inner
        .find_object(object_id)
        .map_err(|err| {
            let msg = format!("Failed to find object {}: {}", id, err);
            repository_error(msg)
        })
        .and_then(|obj| {
            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &obj.data);
                Ok(GitObject {
                    id: obj.id.to_string(),
                    kind: format!("{:?}", obj.kind),
                    data: bytes.into(),
                })
            })
        })
}

/// Find a blob object by its ID
pub(crate) fn find_blob(repo: &Repository, id: &str) -> PyResult<GitObject> {
    let object_id =
        ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

    repo.inner
        .find_blob(object_id)
        .map_err(|err| {
            let msg = format!("Failed to find blob {}: {}", id, err);
            repository_error(msg)
        })
        .and_then(|blob| {
            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &blob.data);
                Ok(GitObject {
                    id: blob.id.to_string(),
                    kind: "Blob".to_string(),
                    data: bytes.into(),
                })
            })
        })
}

/// Find a commit object by its ID
pub(crate) fn find_commit(repo: &Repository, id: &str) -> PyResult<GitObject> {
    let object_id =
        ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

    repo.inner
        .find_commit(object_id)
        .map_err(|err| {
            let msg = format!("Failed to find commit {}: {}", id, err);
            repository_error(msg)
        })
        .and_then(|commit| {
            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &commit.data);
                Ok(GitObject {
                    id: commit.id.to_string(),
                    kind: "Commit".to_string(),
                    data: bytes.into(),
                })
            })
        })
}

/// Find a tree object by its ID
pub(crate) fn find_tree(repo: &Repository, id: &str) -> PyResult<GitObject> {
    let object_id =
        ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

    repo.inner
        .find_tree(object_id)
        .map_err(|err| {
            let msg = format!("Failed to find tree {}: {}", id, err);
            repository_error(msg)
        })
        .and_then(|tree| {
            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &tree.data);
                Ok(GitObject {
                    id: tree.id.to_string(),
                    kind: "Tree".to_string(),
                    data: bytes.into(),
                })
            })
        })
}

/// Find a tag object by its ID
pub(crate) fn find_tag(repo: &Repository, id: &str) -> PyResult<GitObject> {
    let object_id =
        ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

    repo.inner
        .find_tag(object_id)
        .map_err(|err| {
            let msg = format!("Failed to find tag {}: {}", id, err);
            repository_error(msg)
        })
        .and_then(|tag| {
            Python::with_gil(|py| {
                let bytes = PyBytes::new(py, &tag.data);
                Ok(GitObject {
                    id: tag.id.to_string(),
                    kind: "Tag".to_string(),
                    data: bytes.into(),
                })
            })
        })
}

/// Get information about an object without fully decoding it
pub(crate) fn find_header(repo: &Repository, id: &str) -> PyResult<ObjectHeader> {
    let object_id =
        ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

    repo.inner
        .find_header(object_id)
        .map_err(|err| {
            let msg = format!("Failed to find header for {}: {}", id, err);
            repository_error(msg)
        })
        .map(|header| {
            let kind = header.kind();
            let size = header.size();

            ObjectHeader {
                kind: format!("{:?}", kind),
                size,
            }
        })
}

/// Check if an object exists in the repository
pub(crate) fn has_object(repo: &Repository, id: &str) -> PyResult<bool> {
    let object_id =
        ObjectId::from_hex(id.as_bytes()).map_err(|_| repository_error(format!("Invalid object ID: {}", id)))?;

    Ok(repo.inner.has_object(&object_id))
}
