# Git Blame Architecture and Algorithm Analysis

## Core Data Structures

Git’s blame engine revolves around three primary structures:

1. **`blame_origin`**: Represents a specific file blob in a commit, including its content and any pending blame entries.
2. **`blame_entry`**: Represents a contiguous range of lines attributed to one origin (commit blob), including line offsets and metadata.
3. **`blame_scoreboard`**: Orchestrates the blame process, holding the target file’s final content, a priority queue of commits to process, and the list of finalized blame entries.

```c
struct blame_origin {
    struct commit *commit;
    struct blame_entry *suspects;
    mmfile_t file;
    struct object_id blob_oid;
    char path[FLEX_ARRAY];
};

struct blame_entry {
    struct blame_entry *next;
    int lno;                
    int num_lines;          
    struct blame_origin *suspect;
    int s_lno;              
    unsigned score;
    int ignored, unblamable;
};

struct blame_scoreboard {
    struct commit *final;
    struct prio_queue commits;
    const char *path;
    const char *final_buf;
    unsigned long final_buf_size;
    struct blame_entry *ent;
    unsigned move_score, copy_score;
    struct blame_bloom_data *bloom_data;
    // ...additional fields for progress and flags...
};
```

## Initialization and Data Loading

1. **Prepare the Scoreboard**: Load the final commit’s file contents into memory, split into lines, and create an initial `blame_origin`.
2. **Set Initial Blame Entry**: Create a single `blame_entry` covering all lines, linking it into the origin’s suspect list.
3. **Enqueue Starting Commit**: Push the final commit onto the scoreboard’s priority queue.

## Commit Traversal with Priority Queue

- Commits are processed in reverse chronological order using a priority queue sorted by commit date.
- For each commit, Git diffs the suspect lines against each parent:
  - Unchanged lines are passed back to the parent (moving blame entries accordingly).
  - Changed or new lines remain blamed on the current commit (and are finalized).
- Parents receiving new blame entries are enqueued if not already processed.
- The process continues until all lines are attributed.

## Rename, Copy, and Move Detection

- **Similarity Scoring**: Uses fingerprinting of line 2-grams to detect moved or copied code blocks.
- **Thresholds**: Default move score is 20 lines; copy score is 40 lines.
- **Origin Spawning**: When a moved/copied block is detected, blame entries may spawn new origins for the source file in the parent commit.

## Optimizations and Memory Management

- **Bloom Filters**: Uses commit-graph bloom filters to skip commits that did not affect the target file path.
- **Blob Caching**: Each commit’s blob is read only once and reused via `blame_origin`, with reference counting to manage lifetimes.
- **Entry Coalescing**: Adjacent blame entries attributed to the same commit are merged before output.
- **Lazy Fingerprinting**: Fingerprints are computed only when move/copy heuristics or ignore heuristics require them.

## Output Generation

- Final blame entries are sorted by line number and coalesced.
- Output formats include:
  - **Default**: Abbreviated commit hash, author info, line number, and content.
  - **Porcelain**: Full SHA-1, original and final line numbers, author/committer metadata.
  - **Incremental**: Streamed updates as chunks are resolved.

## Summary

Git’s `blame` combines diff-based line tracing, commit-graph optimizations, and fingerprint-based similarity detection to efficiently attribute each line of a file to the commit that last modified it. The interplay of `blame_scoreboard`, `blame_origin`, and `blame_entry` drives the traversal of history, enabling accurate and performant blame output.

