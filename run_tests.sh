#!/bin/bash

# Run tests for the Autonomous AI Architect backend

cd "$(dirname "$0")"

# Set up Python path for imports
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check if specific test file was provided
if [ $# -eq 0 ]; then
    # Run all tests
    echo "Running all tests..."
    python -m pytest backend/tests/ -v
else
    # Run specific test file
    echo "Running test file: $1"
    python -m pytest "$1" -v
fi
