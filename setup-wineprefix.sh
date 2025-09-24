#!/bin/bash
#
# Wine Prefix Setup Script
#
# This script sets up the WINEPREFIX environment variable using the target folder
# as the first argument, converting it to a full path.
#
# IMPORTANT: This script MUST be sourced (not executed) to set environment variables
# in the current shell session.
#

# Color codes for output
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print error messages in red
print_error() {
    echo -e "${RED}Error: $1${NC}"
}

# Check if script is being sourced (not executed)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    print_error "This script must be sourced, not executed directly."
    echo ""
    echo "Correct usage:"
    echo "  . $0 <target_folder>"
    echo "  source $0 <target_folder>"
    echo ""
    echo "Examples:"
    echo "  . $0 ./container-01"
    echo "  source $0 /home/user/wine-containers/my-game"
    echo "  . $0 container-01"
    echo ""
    echo "Why sourcing is required:"
    echo "  Environment variables set in a script only affect the current shell"
    echo "  when the script is sourced. Direct execution creates a subshell where"
    echo "  variables are lost when the script exits."
    exit 1
fi

# Function to display usage information
usage() {
    echo "Usage: . $0 <target_folder>"
    echo "   or: source $0 <target_folder>"
    echo ""
    echo "Arguments:"
    echo "  target_folder    Path to the Wine prefix directory"
    echo ""
    echo "Examples:"
    echo "  . $0 ./container-01"
    echo "  . $0 /home/user/wine-containers/my-game"
    echo "  . $0 container-01"
    echo ""
    echo "This script will:"
    echo "  1. Convert the target folder to an absolute path"
    echo "  2. Set the WINEPREFIX environment variable"
    echo "  3. Export the variable for the current shell session"
    echo ""
    return 1
}

# Check if target folder argument is provided
if [ $# -eq 0 ]; then
    print_error "No target folder specified"
    echo ""
    usage
    return 1
fi

# Get the target folder from the first argument
TARGET_FOLDER="$1"

# Convert to absolute path
if [ -d "$TARGET_FOLDER" ]; then
    # Directory exists, get absolute path
    WINEPREFIX_PATH=$(cd "$TARGET_FOLDER" && pwd)
elif [ -f "$TARGET_FOLDER" ]; then
    # Path exists but is a file, not a directory
    print_error "'$TARGET_FOLDER' is a file, not a directory"
    echo "Please provide a directory path for the Wine prefix"
    return 1
else
    # Path doesn't exist, but we can still convert to absolute path
    # This allows creating new Wine prefixes
    if [[ "$TARGET_FOLDER" = /* ]]; then
        # Already absolute path
        WINEPREFIX_PATH="$TARGET_FOLDER"
    else
        # Relative path, convert to absolute
        WINEPREFIX_PATH=$(cd "$(dirname "$TARGET_FOLDER")" 2>/dev/null && pwd)/$(basename "$TARGET_FOLDER")
    fi
fi

# Set and export the WINEPREFIX variable
export WINEPREFIX="$WINEPREFIX_PATH"

# Display the result
echo "WINEPREFIX has been set to: $WINEPREFIX"
echo ""
echo "You can now run Wine commands with this prefix."
echo "Example: wine winecfg"
echo ""
echo "Note: This variable is only set for the current shell session."
echo "To make it permanent, add the following to your shell profile:"
echo "export WINEPREFIX=\"$WINEPREFIX\""
