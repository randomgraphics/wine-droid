#!/usr/bin/env python3
"""
Wine Container Initialization Script

This script initializes a Wine container, installs Steam dependencies, DXVK files, and vkd3d-proton.
Default target folder is ./container-01, but can be customized.
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None, env=None):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"Error output: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command '{cmd}': {e}")
        return False


def run_wine_command(cmd, container_path):
    """Run a Wine command with the specified container path."""
    env = os.environ.copy()
    env["WINEPREFIX"] = str(container_path.absolute())
    return run_command(cmd, env=env)


def initialize_wine_container(container_path):
    """Initialize a Wine container with default Windows files."""
    print(f"Initializing Wine container at: {container_path}")

    # Create container directory if it doesn't exist
    container_path.mkdir(parents=True, exist_ok=True)

    # Set WINEPREFIX environment variable
    env = os.environ.copy()
    env["WINEPREFIX"] = str(container_path.absolute())

    # Initialize Wine (this creates the default Windows file structure)
    print("Creating Wine prefix...")
    cmd = "wineboot --init"
    try:
        result = subprocess.run(
            cmd, shell=True, env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Warning: wineboot returned non-zero exit code: {result.returncode}")
            print(f"Output: {result.stdout}")
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Error running wineboot: {e}")
        return False

    print("Wine container initialized successfully!")
    return True


def install_steam_dependencies(container_path):
    """Install Steam dependencies using winetricks."""
    print("Installing Steam dependencies...")

    # Check if winetricks is available
    if not shutil.which("winetricks"):
        print("Error: winetricks is not installed or not in PATH")
        print("Please install winetricks first:")
        print("  Ubuntu/Debian: sudo apt install winetricks")
        print("  Arch Linux: sudo pacman -S winetricks")
        print("  Fedora: sudo dnf install winetricks")
        return False

    # Use winetricks to install Steam and all its dependencies
    print("Installing Steam and dependencies with winetricks...")
    cmd = "winetricks -q steam"
    if not run_wine_command(cmd, container_path):
        print("Warning: Steam installation failed, but continuing...")
        return False

    print("Steam dependencies installation completed!")
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


def copy_vkd3d_proton_files(container_path, vkd3d_path):
    """Copy vkd3d-proton files to the Wine container's system directories."""
    print("Installing vkd3d-proton files...")

    # Define target directories
    system32_path = container_path / "drive_c" / "windows" / "system32"
    syswow64_path = container_path / "drive_c" / "windows" / "syswow64"

    # Create directories if they don't exist
    system32_path.mkdir(parents=True, exist_ok=True)
    syswow64_path.mkdir(parents=True, exist_ok=True)

    # Copy x64 files to system32 (64-bit applications)
    x64_src = vkd3d_path / "x64"
    if x64_src.exists():
        print("Copying x64 vkd3d-proton files to system32 (64-bit)...")
        for file in x64_src.glob("*.dll"):
            shutil.copy2(file, system32_path)
            print(f"  Copied: {file.name}")
    else:
        print("Warning: x64 vkd3d-proton directory not found")

    # Copy x32 files to syswow64 (32-bit applications)
    x32_src = vkd3d_path / "x86"
    if x32_src.exists():
        print("Copying x32 vkd3d-proton files to syswow64 (32-bit)...")
        for file in x32_src.glob("*.dll"):
            shutil.copy2(file, syswow64_path)
            print(f"  Copied: {file.name}")
    else:
        print("Warning: x32 vkd3d-proton directory not found")

    print("vkd3d-proton files installed successfully!")


def setup_dxvk_registry(container_path, script_dir):
    """Configure Wine registry to use DXVK DLLs by importing the .reg file."""
    print("Configuring Wine registry for DXVK...")

    # Path to the registry file
    reg_file = script_dir / "dxvk-overrides.reg"

    if not reg_file.exists():
        print(f"Error: DXVK registry file not found: {reg_file}")
        return False

    print(f"Importing DXVK registry settings: {reg_file}")

    # Import the registry file using wine regedit
    cmd = f"wine regedit {reg_file}"
    if not run_wine_command(cmd, container_path):
        print("Warning: DXVK registry configuration failed, but continuing...")
        return False

    print("DXVK registry configuration completed successfully!")
    return True


def setup_vkd3d_proton_registry(container_path, script_dir):
    """Configure Wine registry to use vkd3d-proton DLLs by importing the .reg file."""
    print("Configuring Wine registry for vkd3d-proton...")

    # Path to the registry file
    reg_file = script_dir / "vkd3d-proton-overrides.reg"

    if not reg_file.exists():
        print(f"Error: vkd3d-proton registry file not found: {reg_file}")
        return False

    print(f"Importing vkd3d-proton registry settings: {reg_file}")

    # Import the registry file using wine regedit
    cmd = f"wine regedit {reg_file}"
    if not run_wine_command(cmd, container_path):
        print("Warning: vkd3d-proton registry configuration failed, but continuing...")
        return False

    print("vkd3d-proton registry configuration completed successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Initialize Wine container with Steam dependencies, DXVK, and vkd3d-proton"
    )
    parser.add_argument(
        "--container-path",
        default="./container-01",
        help="Path to Wine container directory (default: ./container-01)",
    )
    parser.add_argument(
        "--dxvk-path",
        default="./dependencies/dxvk-2.7.1",
        help="Path to DXVK directory (default: ./dependencies/dxvk-2.7.1)",
    )
    parser.add_argument(
        "--vkd3d-path",
        default="./dependencies/vkd3d-proton-2.14.1",
        help="Path to vkd3d-proton directory (default: ./dependencies/vkd3d-proton-2.14.1)",
    )
    parser.add_argument(
        "--skip-wine-init",
        action="store_true",
        help="Skip Wine initialization (useful if container already exists)",
    )
    parser.add_argument(
        "--skip-dxvk-registry",
        action="store_true",
        help="Skip DXVK registry configuration",
    )
    parser.add_argument(
        "--skip-steam-deps",
        action="store_true",
        help="Skip Steam dependencies installation",
    )
    parser.add_argument(
        "--skip-vkd3d",
        action="store_true",
        help="Skip vkd3d-proton installation",
    )

    args = parser.parse_args()

    # Get script directory for finding the registry file
    script_dir = Path(__file__).parent.resolve()

    # Convert to Path objects
    container_path = Path(args.container_path).resolve()
    dxvk_path = Path(args.dxvk_path).resolve()
    vkd3d_path = Path(args.vkd3d_path).resolve()

    print(f"Container path: {container_path}")
    print(f"DXVK path: {dxvk_path}")
    print(f"vkd3d-proton path: {vkd3d_path}")
    print(f"Script directory: {script_dir}")

    # Check if DXVK path exists
    if not dxvk_path.exists():
        print(f"Error: DXVK path does not exist: {dxvk_path}")
        sys.exit(1)

    # Check if vkd3d-proton path exists
    if not vkd3d_path.exists():
        print(f"Error: vkd3d-proton path does not exist: {vkd3d_path}")
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

    # Install Steam dependencies first if not skipped
    if not args.skip_steam_deps:
        if not install_steam_dependencies(container_path):
            print("Warning: Steam dependencies installation failed, but continuing...")
    else:
        print("Skipping Steam dependencies installation")

    # Copy DXVK files after Steam
    copy_dxvk_files(container_path, dxvk_path)

    # Configure Wine registry for DXVK if not skipped
    if not args.skip_dxvk_registry:
        if not setup_dxvk_registry(container_path, script_dir):
            print("Warning: DXVK registry configuration failed, but continuing...")
    else:
        print("Skipping DXVK registry configuration")

    # Copy vkd3d-proton files after DXVK
    if not args.skip_vkd3d:
        copy_vkd3d_proton_files(container_path, vkd3d_path)
        if not setup_vkd3d_proton_registry(container_path, script_dir):
            print(
                "Warning: vkd3d-proton registry configuration failed, but continuing..."
            )
    else:
        print("Skipping vkd3d-proton installation")

    print("\nWine container setup complete!")
    print(f"Container location: {container_path}")
    print(f"To use this container, set WINEPREFIX={container_path}")
    print("\nSteam and its dependencies have been installed.")
    print("DXVK is now configured to override Wine's built-in D3D libraries.")
    print("vkd3d-proton is now configured to provide DirectX 12 support.")
    print(
        "Registry settings imported from: dxvk-overrides.reg and vkd3d-proton-overrides.reg"
    )
    print("\nThe container is ready for Steam with DXVK and vkd3d-proton acceleration!")


if __name__ == "__main__":
    main()
