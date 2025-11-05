
#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to script directory
cd "$SCRIPT_DIR"

# Create virtual environment in script's directory
python3 -m venv pyvenv

# Activate virtual environment
source pyvenv/bin/activate

# Upgrade pip
pip install -U pip

# Install requirements if file exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi