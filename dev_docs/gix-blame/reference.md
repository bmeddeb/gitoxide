# gix-blame Implementation Reference

This document contains reference information about Git's blame implementation to guide development of `gix-blame`. It includes key implementation details, data structures, and algorithms used in Git's C implementation.

## Key Concepts from Git's Implementation

### Core Data Structures

The core data structures in Git's blame implementation are:

1. **blame_origin**: Represents a blob in a commit that is being suspected
   ```c
   struct blame_origin {
       int refcnt;
       struct blame_origin *previous;
       struct blame_origin *next;
       struct commit *commit;
       struct blame_entry *suspects;
       mmfile_t file;
       int num_lines;
       struct fingerprint *fingerprints;
       struct object_id blob_oid;
       unsigned short mode;
       char guilty;
       char path[FLEX_ARRAY];
   };
   ```

2. **blame_entry**: Represents a group of lines with the same blame attribution
   ```c
   struct blame_entry {
       struct blame_entry *next;
       int lno;                /* first line number in the final file */
       int num_lines;          /* how many lines this entry has */
       struct blame_origin *suspect;
       int s_lno;              /* first line number in the suspect's file */
       unsigned score;
       int ignored;
       int unblamable;
   };
   ```

3. **blame_scoreboard**: The current state of blame assignment
   ```c
   struct blame_scoreboard {
       struct commit *final;
       struct prio_queue commits;
       struct repository *repo;
       struct rev_info *revs;
       const char *path;
       
       char *final_buf;
       unsigned long final_buf_size;
       
       struct blame_entry *ent;
       struct oidset ignore_list;
       
       int num_lines;
       int *lineno;
       
       /* stats */
       int num_read_blob;
       int num_get_patch;
       int num_commits;
       
       unsigned move_score;
       unsigned copy_score;
       
       const char *contents_from;
       
       /* flags */
       int reverse;
       int show_root;
       int xdl_opts;
       int no_whole_file_rename;
       int debug;
       
       /* callbacks */
       void(*on_sanity_fail)(struct blame_scoreboard *, int);
       void(*found_guilty_entry)(struct blame_entry *, void *);
       
       void *found_guilty_entry_data;
       struct blame_bloom_data *bloom_data;
   };
   ```

### Algorithm Overview

Git's blame algorithm works as follows:

1. **Initialization**:
   - Build a scoreboard with the target file contents
   - Create an initial blame entry for the entire file
   - Associate it with the starting commit

2. **Commit Processing**:
   - Use a priority queue sorted by commit date to process commits
   - For each commit with unresolved blame entries:
     - Find all parent commits
     - For each parent, compare file versions to identify changes
     - Split and assign blame entries based on the changes

3. **Rename and Copy Detection**:
   - When tracking changes fails, attempt to find similar content by:
     - Looking for exact matches (renames) in other files
     - Looking for similar content (copies) based on similarity scores
     - Using fingerprinting techniques to accelerate similarity detection

4. **Output Generation**:
   - Process blame entries to create the desired output format
   - In incremental mode, show results as they are computed

## Key Algorithms to Implement

### 1. Line Tracing Algorithm

The core of blame is tracing each line back through history. Git uses a combination of:

- Line-by-line comparisons using xdiff
- Tracking of line movements across edits
- Heuristics for identifying related lines

```c
/* Key function for tracing lines through diffs */
static int blame_chunk(struct blame_scoreboard *sb,
                     struct blame_origin *parent,
                     int tlno, int slno, int num,
                     struct blame_entry *entry)
{
    /* ... */
}
```

### 2. Copy/Move Detection

Git uses similarity scoring to detect code movement:

```c
/* Constants for copy/move detection */
#define BLAME_DEFAULT_MOVE_SCORE 20
#define BLAME_DEFAULT_COPY_SCORE 40

/* Score-based detection */
static void find_copy_in_blob(struct blame_scoreboard *sb,
                           struct blame_entry *e,
                           struct blame_origin *o,
                           int opt)
{
    /* ... */
}
```

Key parameters:
- `BLAME_DEFAULT_MOVE_SCORE`: Default threshold for considering a block moved
- `BLAME_DEFAULT_COPY_SCORE`: Default threshold for considering a block copied
- Scoring is based on character matches between blocks

### 3. Priority Queue for Commit Processing

Git processes commits in reverse chronological order using a priority queue:

```c
/* Extract from assign_blame function */
prio_queue_put(&sb->commits, commit);

while ((commit = prio_queue_get(&sb->commits)) != NULL) {
    /* Process this commit */
    /* ... */
    /* Add parents to queue */
    for (i = 0; i < commit->parents.nr; i++) {
        prio_queue_put(&sb->commits, commit->parents.items[i].item);
    }
}
```

### 4. Bloom Filter for Commit Filtering

Git uses bloom filters (when available) to quickly detect if a commit could have modified a file:

```c
/* Pseudocode based on Git's implementation */
if (sb->bloom_data && commit_graph_has_bloom_filters()) {
    if (!commit_graph_path_exists(commit, sb->path)) {
        /* Skip this commit - path doesn't exist */
        continue;
    }
}
```

## Important Implementation Details

### 1. Memory Management

Git is careful with memory usage:
- It frees blob contents when they're no longer needed
- Uses reference counting for origins
- Avoids duplicate entries when possible

### 2. Optimization Techniques

- Uses fingerprinting to accelerate similarity detection
- Caches computed scores for entries
- Uses the commit graph when available for faster traversal
- Avoids redundant blob lookups and diffs

### 3. Error Handling

Git's blame has robust error handling for various conditions:
- Missing blobs
- Repository corruption
- Ambiguous references
- Truncated or malformed files

### 4. Progress Reporting

Git provides progress feedback during blame operations:

```c
static void setup_progress(struct progress_info *info, struct blame_scoreboard *sb)
{
    info->progress = start_delayed_progress(_("Blaming lines"), sb->num_lines);
    info->blamed_lines = 0;
}

static void update_progress(struct progress_info *info, int num_lines)
{
    if (info->progress) {
        info->blamed_lines += num_lines;
        display_progress(info->progress, info->blamed_lines);
    }
}
```

## Output Formats

### 1. Default Format

Git's default blame output includes:
- Commit hash (abbreviated)
- Author information
- Line number
- Line content

### 2. Porcelain Format

A more structured output for machine consumption:
- Complete SHA-1 hash
- Line numbers (original and final)
- Complete author and committer information
- Filename in the original commit

### 3. Incremental Format

Output results as they are computed:
- Similar to porcelain format
- Provides updates as each portion of the blame is resolved
- Designed for interactive viewers

## Conclusion

When implementing `gix-blame`, it's important to understand these internals of Git's blame implementation. The core algorithms for line tracing, similarity detection, and commit traversal are particularly important to get right for performance and accuracy.

For the most up-to-date reference implementation, consult the Git source code, particularly:

- `blame.h`: Core data structures and function declarations
- `blame.c`: Main implementation of the blame algorithm
- `builtin/blame.c`: Command-line interface and output formatting

By studying and adapting these implementations, `gix-blame` can achieve both compatibility with Git's behavior and potentially improve upon its performance.