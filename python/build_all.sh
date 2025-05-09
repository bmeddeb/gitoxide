#!/bin/bash
echo "Building regular gitoxide package..."
maturin build

echo "Building gitoxide_async package..."
cp pyproject.toml pyproject.toml.bak
python3 -c "content = open(\"pyproject.toml\").read().replace(\"name = \\"gitoxide\\"\", \"name = \\"gitoxide_async\\"\"); open(\"pyproject.toml\", \"w\").write(content)"
maturin build --features async
