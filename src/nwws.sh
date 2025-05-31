#!/bin/sh
# Exit immediately if a command exits with a non-zero status.
set -e

# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate the virtual environment
if [ -f "../.venv/bin/activate" ]; then
    . "../.venv/bin/activate"
else
    echo "Error: Virtual environment not found at ../.venv. Please create one."
    exit 1
fi

# Run the python module
python3 -m nwws "$@"
