#!/usr/bin/env python3
"""
Wine Container Initialization Script

This script initializes a Wine container and installs DXVK files.
Default target folder is ./container-01, but can be customized.
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"Error output: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command '{cmd}': {e}")
        return False


def initialize_wine_container(container_path):
    """Initialize a Wine container with default Windows files."""
    print(f"Initializing Wine container at: {container_path}")
    
    # Create container directory if it doesn't exist
    container_path.mkdir(parents=True, exist_ok=True)
    
    # Set WINEPREFIX environment variable
    env = os.environ.copy()
    env['WINEPREFIX'] = str(container_path.absolute())
    
    # Initialize Wine (this creates the default Windows file structure)
    print("Creating Wine prefix...")
    cmd = "wineboot --init"
    try:
        result = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: wineboot returned non-zero exit code: {result.returncode}")
            print(f"Output: {result.stdout}")
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error running wineboot: {e}")
        return False
    
    print("Wine container initialized successfully!")
    return True


def copy_dxvk_files(container_path, dxvk_path):
    """Copy DXVK files to the Wine container's system directories."""
    print("Installing DXVK files...")
    
    # Define target directories
    system32_path = container_path / "drive_c" / "windows" / "system32"
    syswow64_path = container_path / "drive_c" / "windows" / "syswow64"
    
    # Create directories if they don't exist
    system32_path.mkdir(parents=True, exist_ok=True)
    syswow64_path.mkdir(parents=True, exist_ok=True)
    
    # Copy x64 files to system32 (64-bit applications)
    x64_src = dxvk_path / "x64"
    if x64_src.exists():
        print("Copying x64 DXVK files to system32 (64-bit)...")
        for file in x64_src.glob("*.dll"):
            shutil.copy2(file, system32_path)
            print(f"  Copied: {file.name}")
    else:
        print("Warning: x64 DXVK directory not found")
    
    # Copy x32 files to syswow64 (32-bit applications)
    x32_src = dxvk_path / "x32"
    if x32_src.exists():
        print("Copying x32 DXVK files to syswow64 (32-bit)...")
        for file in x32_src.glob("*.dll"):
            shutil.copy2(file, syswow64_path)
            print(f"  Copied: {file.name}")
    else:
        print("Warning: x32 DXVK directory not found")
    
    print("DXVK files installed successfully!")


def main():
    parser = argparse.ArgumentParser(description="Initialize Wine container with DXVK")
    parser.add_argument(
        "--container-path", 
        default="./container-01",
        help="Path to Wine container directory (default: ./container-01)"
    )
    parser.add_argument(
        "--dxvk-path",
        default="./dependencies/dxvk-2.7.1",
        help="Path to DXVK directory (default: ./dependencies/dxvk-2.7.1)"
    )
    parser.add_argument(
        "--skip-wine-init",
        action="store_true",
        help="Skip Wine initialization (useful if container already exists)"
    )
    
    args = parser.parse_args()
    
    # Convert to Path objects
    container_path = Path(args.container_path).resolve()
    dxvk_path = Path(args.dxvk_path).resolve()
    
    print(f"Container path: {container_path}")
    print(f"DXVK path: {dxvk_path}")
    
    # Check if DXVK path exists
    if not dxvk_path.exists():
        print(f"Error: DXVK path does not exist: {dxvk_path}")
        sys.exit(1)
    
    # Check if Wine is installed
    if not shutil.which("wine"):
        print("Error: Wine is not installed or not in PATH")
        sys.exit(1)
    
    # Initialize Wine container if not skipped
    if not args.skip_wine_init:
        if not initialize_wine_container(container_path):
            print("Failed to initialize Wine container")
            sys.exit(1)
    else:
        print("Skipping Wine initialization")
    
    # Copy DXVK files
    copy_dxvk_files(container_path, dxvk_path)
    
    print("\nWine container setup complete!")
    print(f"Container location: {container_path}")
    print(f"To use this container, set WINEPREFIX={container_path}")


if __name__ == "__main__":
    main()
