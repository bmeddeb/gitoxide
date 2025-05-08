# gix-chunk Use Cases

This document outlines the primary use cases for the `gix-chunk` crate, detailing who might use it, for what purposes, and with example code.

## Intended Audience

- **Git Format Implementers**: Developers working on Git file format support in gitoxide
- **Performance-Critical Applications**: Applications needing efficient access to Git data structures
- **Git Extension Developers**: Those creating tools that need to read or write Multi-Pack-Index or commit-graph files

## Use Cases

### 1. Reading Multi-Pack-Index (MIDX) Files

**Problem**:  
Efficiently accessing and parsing Multi-Pack-Index files, which are used to optimize object lookup across multiple packfiles in large repositories.

**Solution**:  
The `gix-chunk` crate provides low-level primitives to access specific chunks of data within MIDX files without having to reimplement the chunked file format parsing logic.

**Example Code**:
```rust
use gix_chunk::{Id, file::Index};
use std::fs::File;
use std::io::Read;
use std::ops::Range;

// Read the MIDX file
let mut file = File::open("multi-pack-index")?;
let mut data = Vec::new();
file.read_to_end(&mut data)?;

// MIDX header is 12 bytes (\\xfeMIDX + version + hash type + chunk count)
let toc_offset = 12;
let num_chunks = data[11]; // Last byte of header is chunk count

// Parse the table of contents
let index = Index::from_bytes(&data, toc_offset as usize, num_chunks as u32)?;

// Access different chunks by their identifiers
let oidx_data = index.data_by_id(&data, *b"OIDX")?; // Object ID chunk
let pnam_data = index.data_by_id(&data, *b"PNAM")?; // Pack names chunk
let oidl_data = index.data_by_id(&data, *b"OIDL")?; // Object ID lookup chunk

// Process the data from each chunk according to the MIDX format
// For example, parse the pack names from PNAM
let mut pack_names = Vec::new();
let mut pos = 0;
while pos < pnam_data.len() {
    let end = pnam_data[pos..].iter().position(|&b| b == 0).unwrap_or(pnam_data.len() - pos) + pos;
    if end > pos {
        let pack_name = &pnam_data[pos..end];
        pack_names.push(pack_name);
    }
    pos = end + 1;
}

println!("Found {} packfiles in MIDX", pack_names.len());
```

### 2. Reading Commit-Graph Files

**Problem**:  
Parsing commit-graph files, which store precomputed commit relationship data to accelerate commit graph traversal.

**Solution**:  
The `gix-chunk` crate allows accessing specific chunks within commit-graph files where different types of data are stored.

**Example Code**:
```rust
use gix_chunk::{Id, file::Index};
use std::fs::File;
use std::io::Read;

// Read the commit-graph file
let mut file = File::open("commit-graph")?;
let mut data = Vec::new();
file.read_to_end(&mut data)?;

// Commit-graph header is 8 bytes (CGPH + version + hash type + chunk count)
let toc_offset = 8;
let num_chunks = data[7]; // Last byte of header is chunk count

// Parse the table of contents
let index = Index::from_bytes(&data, toc_offset as usize, num_chunks as u32)?;

// Access different chunks of the commit-graph
let oidf_data = index.data_by_id(&data, *b"OIDF")?; // OID Fanout
let oidl_data = index.data_by_id(&data, *b"OIDL")?; // OID Lookup
let comm_data = index.data_by_id(&data, *b"COMM")?; // Commit data
let edge_data = index.data_by_id(&data, *b"EDGE")?; // Edge list

// Process the OID fanout table to understand the distribution of commits
let mut fanout = [0u32; 256];
for i in 0..256 {
    let start = i * 4;
    let end = start + 4;
    fanout[i] = u32::from_be_bytes([
        oidf_data[start], oidf_data[start+1], 
        oidf_data[start+2], oidf_data[start+3]
    ]);
}

// Total number of commits is the last entry in fanout
let commit_count = fanout[255];
println!("Commit-graph contains {} commits", commit_count);
```

### 3. Creating a New Commit-Graph File

**Problem**:  
Creating a new commit-graph file with various data chunks, each having different content but needing to adhere to the chunked file format.

**Solution**:  
The `gix-chunk` crate allows planning and writing chunks in a structured way, ensuring proper offsets and chunk sizes.

**Example Code**:
```rust
use gix_chunk::{Id, file::Index};
use std::fs::File;
use std::io::{Write, BufWriter};

// Prepare data for each chunk
let oidf_data = prepare_oid_fanout_data()?;      // 1024 bytes
let oidl_data = prepare_oid_lookup_data()?;      // Variable size
let comm_data = prepare_commit_data()?;          // Variable size
let edge_data = prepare_edge_list_data()?;       // Variable size

// Create a new file
let file = File::create("new-commit-graph")?;
let mut writer = BufWriter::new(file);

// Write the header (CGPH + version 1 + SHA1 + 4 chunks)
let header = b"CGPH\x01\x01\x04";
writer.write_all(header)?;

// Create an index for writing
let mut index = Index::for_writing();

// Plan chunks with their exact sizes
index.plan_chunk(*b"OIDF", oidf_data.len() as u64);
index.plan_chunk(*b"OIDL", oidl_data.len() as u64);
index.plan_chunk(*b"COMM", comm_data.len() as u64);
index.plan_chunk(*b"EDGE", edge_data.len() as u64);

// Convert the index to a chunk writer, starting after the header
let mut chunk_writer = index.into_write(writer, header.len())?;

// Write each chunk in sequence
if let Some(chunk_id) = chunk_writer.next_chunk() {
    assert_eq!(&chunk_id, b"OIDF");
    chunk_writer.write_all(&oidf_data)?;
}

if let Some(chunk_id) = chunk_writer.next_chunk() {
    assert_eq!(&chunk_id, b"OIDL");
    chunk_writer.write_all(&oidl_data)?;
}

if let Some(chunk_id) = chunk_writer.next_chunk() {
    assert_eq!(&chunk_id, b"COMM");
    chunk_writer.write_all(&comm_data)?;
}

if let Some(chunk_id) = chunk_writer.next_chunk() {
    assert_eq!(&chunk_id, b"EDGE");
    chunk_writer.write_all(&edge_data)?;
}

// Finalize the file
let writer = chunk_writer.into_inner();
writer.flush()?;

println!("Created new commit-graph file");

// Helper functions (placeholders)
fn prepare_oid_fanout_data() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Implementation omitted
    Ok(vec![0; 1024])
}

fn prepare_oid_lookup_data() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Implementation omitted
    Ok(vec![0; 2048])
}

fn prepare_commit_data() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Implementation omitted
    Ok(vec![0; 4096])
}

fn prepare_edge_list_data() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Implementation omitted
    Ok(vec![0; 1536])
}
```

### 4. Updating an Existing Chunk File

**Problem**:  
Modifying an existing chunk file by replacing or adding chunks while preserving the chunked file structure.

**Solution**:  
Using `gix-chunk` to read the existing chunks, then planning and writing a new file with updated chunks.

**Example Code**:
```rust
use gix_chunk::{Id, file::Index};
use std::fs::{File, OpenOptions};
use std::io::{Read, Write, BufWriter, Seek, SeekFrom};
use std::collections::HashMap;

// Read the existing chunk file
let mut file = File::open("existing-chunk-file")?;
let mut data = Vec::new();
file.read_to_end(&mut data)?;

// For this example, assume we know the header size and chunk count
let header_size = 8;
let num_chunks = data[7] as u32;

// Parse the existing TOC
let original_index = Index::from_bytes(&data, header_size, num_chunks)?;

// Collect all chunk data we want to preserve
let mut chunks_to_keep = HashMap::new();
for &chunk_id in &[*b"OIDF", *b"OIDL"] {
    if let Ok(chunk_data) = original_index.data_by_id(&data, chunk_id) {
        chunks_to_keep.insert(chunk_id, chunk_data.to_vec());
    }
}

// Create new data for chunks we want to update
let new_comm_data = generate_new_commit_data()?;
let new_edge_data = generate_new_edge_data()?;

// Create a new file for the updated content
let out_file = File::create("updated-chunk-file")?;
let mut writer = BufWriter::new(out_file);

// Write the header (preserve the original)
writer.write_all(&data[0..header_size])?;

// Create an index for writing
let mut index = Index::for_writing();

// Plan chunks with their exact sizes (preserving original chunks)
for (&chunk_id, chunk_data) in &chunks_to_keep {
    index.plan_chunk(chunk_id, chunk_data.len() as u64);
}

// Plan our updated chunks
index.plan_chunk(*b"COMM", new_comm_data.len() as u64);
index.plan_chunk(*b"EDGE", new_edge_data.len() as u64);

// Convert the index to a chunk writer
let mut chunk_writer = index.into_write(writer, header_size)?;

// Write all chunks in the order they were planned
for _ in 0..index.num_chunks() {
    if let Some(chunk_id) = chunk_writer.next_chunk() {
        // Write preserved chunks
        if let Some(chunk_data) = chunks_to_keep.get(&chunk_id) {
            chunk_writer.write_all(chunk_data)?;
        } 
        // Write updated chunks
        else if chunk_id == *b"COMM" {
            chunk_writer.write_all(&new_comm_data)?;
        } else if chunk_id == *b"EDGE" {
            chunk_writer.write_all(&new_edge_data)?;
        }
    }
}

// Finalize the file
let writer = chunk_writer.into_inner();
writer.flush()?;

println!("Updated chunk file created");

// Helper functions
fn generate_new_commit_data() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Implementation omitted
    Ok(vec![0; 5120])
}

fn generate_new_edge_data() -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    // Implementation omitted
    Ok(vec![0; 2048])
}
```

### 5. Custom Chunk File Format Implementation

**Problem**:  
Creating a new custom file format based on Git's chunk approach for storing application-specific data.

**Solution**:  
Using `gix-chunk` as the foundation for implementing a new chunked file format, taking advantage of its robust parsing and writing capabilities.

**Example Code**:
```rust
use gix_chunk::{Id, file::Index};
use std::fs::File;
use std::io::{Read, Write, BufWriter};

// Define our custom chunk format with specific chunk IDs
const CHUNK_HEADER: &[u8] = b"CUST\x01\x00\x03"; // Custom format v1.0 with 3 chunks
const CHUNK_META: Id = *b"META"; // Metadata
const CHUNK_DATA: Id = *b"DATA"; // Primary data
const CHUNK_INDX: Id = *b"INDX"; // Index information

// Create sample data for our chunks
let metadata = prepare_metadata();
let primary_data = prepare_primary_data();
let index_data = prepare_index_data();

// Create a new file
let file = File::create("custom-chunk-file")?;
let mut writer = BufWriter::new(file);

// Write the header
writer.write_all(CHUNK_HEADER)?;

// Create an index for writing
let mut index = Index::for_writing();

// Plan the chunks
index.plan_chunk(CHUNK_META, metadata.len() as u64);
index.plan_chunk(CHUNK_DATA, primary_data.len() as u64);
index.plan_chunk(CHUNK_INDX, index_data.len() as u64);

// Convert the index to a chunk writer
let mut chunk_writer = index.into_write(writer, CHUNK_HEADER.len())?;

// Write each chunk
if let Some(chunk_id) = chunk_writer.next_chunk() {
    assert_eq!(chunk_id, CHUNK_META);
    chunk_writer.write_all(&metadata)?;
}

if let Some(chunk_id) = chunk_writer.next_chunk() {
    assert_eq!(chunk_id, CHUNK_DATA);
    chunk_writer.write_all(&primary_data)?;
}

if let Some(chunk_id) = chunk_writer.next_chunk() {
    assert_eq!(chunk_id, CHUNK_INDX);
    chunk_writer.write_all(&index_data)?;
}

// Finalize the file
let writer = chunk_writer.into_inner();
writer.flush()?;

// Now read it back
let mut file = File::open("custom-chunk-file")?;
let mut data = Vec::new();
file.read_to_end(&mut data)?;

// Parse the TOC (starting after our custom header)
let index = Index::from_bytes(&data, CHUNK_HEADER.len(), 3)?;

// Access data by chunk ID
let meta = index.data_by_id(&data, CHUNK_META)?;
let primary = index.data_by_id(&data, CHUNK_DATA)?;
let idx = index.data_by_id(&data, CHUNK_INDX)?;

println!(
    "Read custom chunk file: metadata={} bytes, primary={} bytes, index={} bytes",
    meta.len(), primary.len(), idx.len()
);

// Helper functions to generate sample data
fn prepare_metadata() -> Vec<u8> {
    // Sample implementation
    serde_json::to_vec(&serde_json::json!({
        "creation_time": chrono::Utc::now().to_rfc3339(),
        "version": "1.0.0",
        "app": "custom-chunk-example"
    })).unwrap_or_default()
}

fn prepare_primary_data() -> Vec<u8> {
    // For example, could be a binary blob of data 
    let mut data = Vec::with_capacity(1024);
    for i in 0..1024 {
        data.push((i % 256) as u8);
    }
    data
}

fn prepare_index_data() -> Vec<u8> {
    // Sample index data
    let mut data = Vec::new();
    for i in 0..100 {
        data.extend_from_slice(&(i as u32).to_be_bytes());
        data.extend_from_slice(&((i * 10) as u32).to_be_bytes());
    }
    data
}
```

## Benefits for Each Use Case

1. **Reading MIDX and Commit-Graph Files**:
   - Zero-copying access to chunks minimizes memory usage
   - Validation ensures corrupt files are detected early
   - Simple API simplifies integration with higher-level code

2. **Creating New Chunked Files**:
   - Automatic table of contents generation
   - Validation ensures chunks are properly sized
   - Simplified writer interface prevents errors in chunk order

3. **Updating Existing Files**:
   - Can selectively preserve or replace chunks
   - Ensures chunks remain properly aligned
   - Maintains file format integrity

4. **Custom Chunk Formats**:
   - Reuse of battle-tested chunked file logic
   - Consistent error handling
   - Easy extension to application-specific formats