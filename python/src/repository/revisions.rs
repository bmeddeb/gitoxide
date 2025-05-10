use gix_hash::ObjectId;
use pyo3::prelude::*;

use crate::errors::repository_error;
use crate::repository::core::Repository;

/// Find all merge bases between one commit and multiple other commits
pub(crate) fn merge_bases(repo: &Repository, one: &str, others: Vec<String>) -> PyResult<Vec<String>> {
    // Parse the first commit ID
    let first_id = ObjectId::from_hex(one.as_bytes())
        .map_err(|_| repository_error(format!("Invalid object ID for first commit: {}", one)))?;

    // Parse the other commit IDs
    let mut other_ids = Vec::with_capacity(others.len());
    for (idx, other) in others.iter().enumerate() {
        let id = ObjectId::from_hex(other.as_bytes())
            .map_err(|_| repository_error(format!("Invalid object ID for other commit {}: {}", idx, other)))?;
        other_ids.push(id);
    }

    // Get the commit graph
    let cache = repo
        .inner
        .commit_graph_if_enabled()
        .map_err(|err| repository_error(format!("Failed to retrieve commit graph: {}", err)))?;
    let mut graph = repo.inner.revision_graph(cache.as_ref());

    // Find the merge bases
    repo.inner
        .merge_bases_many_with_graph(first_id, &other_ids, &mut graph)
        .map_err(|err| repository_error(format!("Failed to find merge bases: {}", err)))
        .map(|bases| bases.iter().map(|id| id.to_string()).collect())
}

/// Find the best merge base between two commits
pub(crate) fn merge_base(repo: &Repository, one: &str, two: &str) -> PyResult<String> {
    // Parse the commit IDs
    let first_id = ObjectId::from_hex(one.as_bytes())
        .map_err(|_| repository_error(format!("Invalid object ID for first commit: {}", one)))?;

    let second_id = ObjectId::from_hex(two.as_bytes())
        .map_err(|_| repository_error(format!("Invalid object ID for second commit: {}", two)))?;

    // Find the merge base
    repo.inner
        .merge_base(first_id, second_id)
        .map_err(|err| repository_error(format!("Failed to find merge base: {}", err)))
        .map(|id| id.to_string())
}

/// Parse a revision specification and return a single commit/object ID
pub(crate) fn rev_parse(repo: &Repository, spec: &str) -> PyResult<String> {
    repo.inner
        .rev_parse_single(spec)
        .map_err(|err| repository_error(format!("Failed to parse revision '{}': {}", spec, err)))
        .map(|id| id.to_string())
}

/// Find the best merge base among multiple commits
pub(crate) fn merge_base_octopus(repo: &Repository, commits: Vec<String>) -> PyResult<String> {
    // Check if we have at least one commit
    if commits.is_empty() {
        return Err(repository_error(
            "No commits provided for merge_base_octopus".to_string(),
        ));
    }

    // Convert string IDs to ObjectIds
    let commit_ids: Result<Vec<_>, _> = commits
        .iter()
        .map(|id_str| {
            ObjectId::from_hex(id_str.as_bytes())
                .map_err(|_| repository_error(format!("Invalid object ID: {}", id_str)))
        })
        .collect();

    let commit_ids = commit_ids?;

    // Get the commit graph
    let _cache = repo
        .inner
        .commit_graph_if_enabled()
        .map_err(|err| repository_error(format!("Failed to retrieve commit graph: {}", err)))?;

    // Find the merge base
    repo.inner
        .merge_base_octopus(commit_ids)
        .map_err(|err| repository_error(format!("Failed to find merge base octopus: {}", err)))
        .map(|id| id.to_string())
}
