#!/bin/bash
set -e
echo "Installing Python dependencies..."
pip install -r src/requirements.txt
echo "Build complete."