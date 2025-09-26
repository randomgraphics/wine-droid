#!/usr/bin/env python3
"""
Android Phone Wine + box64 Setup Script

This script sets up a Wine environment with box64 on a connected Android phone via ADB.
It handles installation of box64, Wine, and necessary dependencies for running Windows applications.
"""

import os
import sys
import shutil
import subprocess
import argparse
import platform
import urllib.request
import zipfile
import tarfile
import tempfile
from pathlib import Path


def run_command(cmd, cwd=None, env=None, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, env=env, capture_output=True, text=True
        )
        if check and result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"Error output: {result.stderr}")
            return False, result
        return True, result
    except Exception as e:
        print(f"Exception running command '{cmd}': {e}")
        return False, None


def check_adb_connection():
    """Check if ADB is available and a device is connected."""
    print("Checking ADB connection...")
    
    # Check if ADB is installed
    if not shutil.which("adb"):
        print("Error: ADB (Android Debug Bridge) is not installed or not in PATH")
        print("Please install ADB first:")
        print("  Ubuntu/Debian: sudo apt install android-tools-adb")
        print("  Arch Linux: sudo pacman -S android-tools")
        print("  Fedora: sudo dnf install android-tools")
        return False
    
    # Check if device is connected
    success, result = run_command("adb devices", check=False)
    if not success:
        print("Error: Failed to run adb devices")
        return False
    
    # Parse device list
    lines = result.stdout.strip().split('\n')[1:]  # Skip header
    devices = [line for line in lines if line.strip() and 'device' in line]
    
    if not devices:
        print("Error: No Android device connected")
        print("Please connect your Android device and enable USB debugging")
        print("Make sure to allow USB debugging when prompted on your device")
        return False
    
    print(f"Found {len(devices)} connected device(s)")
    for device in devices:
        print(f"  {device}")
    
    return True


def download_file(url, destination):
    """Download a file from URL to destination."""
    print(f"Downloading {url} to {destination}")
    try:
        urllib.request.urlretrieve(url, destination)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def push_file_to_android(local_path, android_path):
    """Push a file to Android device via ADB."""
    print(f"Pushing {local_path} to {android_path}")
    cmd = f"adb push {local_path} {android_path}"
    success, result = run_command(cmd, check=False)
    if not success:
        print(f"Error pushing file: {result.stderr if result else 'Unknown error'}")
        return False
    return True


def run_adb_command(cmd):
    """Run a command on Android device via ADB shell."""
    full_cmd = f"adb shell '{cmd}'"
    return run_command(full_cmd, check=False)


def install_termux_on_android():
    """Install Termux on Android device if not present."""
    print("Checking for Termux installation...")
    
    # Check if Termux is installed
    success, result = run_adb_command("pm list packages | grep com.termux")
    if success and "com.termux" in result.stdout:
        print("Termux is already installed")
        return True
    
    print("Termux not found. Please install Termux from:")
    print("  F-Droid: https://f-droid.org/packages/com.termux/")
    print("  GitHub: https://github.com/termux/termux-app/releases")
    print("After installing Termux, run this script again.")
    return False


def setup_termux_environment():
    """Set up Termux environment with necessary packages."""
    print("Setting up Termux environment...")
    
    # Update package lists
    print("Updating Termux packages...")
    success, result = run_adb_command("termux-change-repo")
    if not success:
        print("Warning: Failed to change Termux repository")
    
    # Install essential packages
    packages = [
        "git", "wget", "curl", "unzip", "tar", "python", "python-pip",
        "build-essential", "cmake", "pkg-config", "libc6-dev"
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        success, result = run_adb_command(f"pkg install -y {package}")
        if not success:
            print(f"Warning: Failed to install {package}")
    
    print("Termux environment setup completed!")
    return True


def install_box64_on_android(install_dir):
    """Install box64 on Android device."""
    print("Installing box64 on Android...")
    
    # Create install directory
    run_adb_command(f"mkdir -p {install_dir}")
    
    # Download box64 for ARM64
    box64_url = "https://github.com/ptitSeb/box64/releases/latest/download/box64-linux-arm64.tar.gz"
    
    # Download to temporary location first
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    if not download_file(box64_url, tmp_path):
        print("Failed to download box64")
        return None
    
    # Push to Android device
    android_tmp = "/data/local/tmp/box64.tar.gz"
    if not push_file_to_android(tmp_path, android_tmp):
        print("Failed to push box64 to Android device")
        os.unlink(tmp_path)
        return None
    
    # Extract on Android device
    success, result = run_adb_command(f"cd {install_dir} && tar -xzf {android_tmp}")
    if not success:
        print("Failed to extract box64 on Android device")
        return None
    
    # Make box64 executable
    run_adb_command(f"chmod +x {install_dir}/box64")
    
    # Clean up
    run_adb_command(f"rm {android_tmp}")
    os.unlink(tmp_path)
    
    print(f"box64 installed at: {install_dir}/box64")
    return f"{install_dir}/box64"


def install_wine_on_android(install_dir, box64_path):
    """Install Wine on Android device."""
    print("Installing Wine on Android...")
    
    # Create wine directory
    wine_dir = f"{install_dir}/wine"
    run_adb_command(f"mkdir -p {wine_dir}")
    
    # Download Wine source
    print("Downloading Wine source...")
    success, result = run_adb_command(f"cd {wine_dir} && git clone https://github.com/wine-mirror/wine.git .")
    if not success:
        print("Failed to clone Wine repository")
        return None
    
    # Configure Wine for Android
    print("Configuring Wine...")
    configure_cmd = f"cd {wine_dir} && ./configure --with-wine64 --prefix={wine_dir}"
    success, result = run_adb_command(configure_cmd)
    if not success:
        print("Failed to configure Wine")
        return None
    
    # Build Wine
    print("Building Wine (this may take a while)...")
    build_cmd = f"cd {wine_dir} && make -j4"
    success, result = run_adb_command(build_cmd)
    if not success:
        print("Failed to build Wine")
        return None
    
    # Install Wine
    print("Installing Wine...")
    install_cmd = f"cd {wine_dir} && make install"
    success, result = run_adb_command(install_cmd)
    if not success:
        print("Failed to install Wine")
        return None
    
    print(f"Wine installed at: {wine_dir}")
    return wine_dir


def setup_wine_prefix_on_android(container_path, wine_path, box64_path):
    """Initialize a Wine prefix on Android device."""
    print(f"Setting up Wine prefix at: {container_path}")
    
    # Create container directory
    run_adb_command(f"mkdir -p {container_path}")
    
    # Set up environment and initialize Wine prefix
    env_vars = f"WINEPREFIX={container_path} WINEARCH=win64"
    wine_cmd = f"{box64_path} {wine_path}/bin/wine"
    
    print("Initializing Wine prefix...")
    init_cmd = f"{env_vars} {wine_cmd} wineboot --init"
    success, result = run_adb_command(init_cmd)
    if not success:
        print(f"Warning: Wine initialization failed: {result.stderr if result else 'Unknown error'}")
        return False
    
    print("Wine prefix initialized successfully!")
    return True


def install_winetricks_on_android(container_path, wine_path, box64_path):
    """Install winetricks on Android device."""
    print("Installing winetricks...")
    
    # Download winetricks
    winetricks_url = "https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks"
    winetricks_path = f"{container_path}/winetricks"
    
    # Download to temporary location
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    if not download_file(winetricks_url, tmp_path):
        print("Failed to download winetricks")
        return False
    
    # Push to Android device
    if not push_file_to_android(tmp_path, winetricks_path):
        print("Failed to push winetricks to Android device")
        os.unlink(tmp_path)
        return False
    
    # Make winetricks executable
    run_adb_command(f"chmod +x {winetricks_path}")
    
    # Clean up
    os.unlink(tmp_path)
    
    print("winetricks installed successfully!")
    return True


def create_launch_script_on_android(install_dir, container_path, wine_path, box64_path):
    """Create a launch script on Android device."""
    print("Creating launch script...")
    
    launch_script = f"{install_dir}/launch-wine.sh"
    
    script_content = f"""#!/bin/bash
# Android Wine + box64 Launch Script

export WINEPREFIX="{container_path}"
export WINEARCH="win64"
export PATH="{wine_path}/bin:$PATH"

# Use box64 to run Wine commands
alias wine="{box64_path} {wine_path}/bin/wine"
alias winecfg="{box64_path} {wine_path}/bin/winecfg"
alias wineboot="{box64_path} {wine_path}/bin/wineboot"

echo "Android Wine + box64 environment loaded!"
echo "Wine prefix: $WINEPREFIX"
echo "Wine architecture: $WINEARCH"
echo ""
echo "Available commands:"
echo "  wine <command>     - Run a Windows application"
echo "  winecfg           - Configure Wine"
echo "  wineboot          - Wine boot commands"
echo ""
echo "Example: wine notepad.exe"
"""
    
    # Write script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        tmp_file.write(script_content)
        tmp_path = tmp_file.name
    
    # Push to Android device
    if not push_file_to_android(tmp_path, launch_script):
        print("Failed to push launch script to Android device")
        os.unlink(tmp_path)
        return None
    
    # Make script executable
    run_adb_command(f"chmod +x {launch_script}")
    
    # Clean up
    os.unlink(tmp_path)
    
    print(f"Launch script created: {launch_script}")
    return launch_script


def create_android_app_launcher(install_dir, launch_script):
    """Create an Android app launcher for easy access."""
    print("Creating Android app launcher...")
    
    # Create a simple launcher script that can be run from Android
    launcher_script = f"{install_dir}/start-wine.sh"
    
    launcher_content = f"""#!/bin/bash
# Android Wine Launcher

echo "Starting Wine environment..."
echo "Make sure you're running this in Termux!"

# Source the Wine environment
source {launch_script}

echo ""
echo "Wine environment is now active!"
echo "You can now run Windows applications."
echo ""
echo "To exit, type 'exit' or press Ctrl+C"
echo ""

# Start an interactive shell
bash
"""
    
    # Write launcher to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        tmp_file.write(launcher_content)
        tmp_path = tmp_file.name
    
    # Push to Android device
    if not push_file_to_android(tmp_path, launcher_script):
        print("Failed to push launcher script to Android device")
        os.unlink(tmp_path)
        return None
    
    # Make launcher executable
    run_adb_command(f"chmod +x {launcher_script}")
    
    # Clean up
    os.unlink(tmp_path)
    
    print(f"Android launcher created: {launcher_script}")
    return launcher_script


def main():
    parser = argparse.ArgumentParser(
        description="Set up Wine + box64 environment on connected Android phone"
    )
    parser.add_argument(
        "--install-dir",
        default="/data/data/com.termux/files/home/android-wine",
        help="Directory to install Wine and box64 on Android (default: /data/data/com.termux/files/home/android-wine)",
    )
    parser.add_argument(
        "--container-path",
        default="/data/data/com.termux/files/home/wine-prefix",
        help="Path to Wine prefix directory on Android (default: /data/data/com.termux/files/home/wine-prefix)",
    )
    parser.add_argument(
        "--skip-termux-setup",
        action="store_true",
        help="Skip Termux environment setup",
    )
    parser.add_argument(
        "--skip-box64",
        action="store_true",
        help="Skip box64 installation",
    )
    parser.add_argument(
        "--skip-wine",
        action="store_true",
        help="Skip Wine installation",
    )

    args = parser.parse_args()

    print("Android Phone Wine + box64 Setup Script")
    print("=" * 50)
    print(f"Install directory: {args.install_dir}")
    print(f"Wine prefix: {args.container_path}")
    print()

    # Check ADB connection
    if not check_adb_connection():
        sys.exit(1)

    # Check for Termux
    if not install_termux_on_android():
        sys.exit(1)

    # Set up Termux environment
    if not args.skip_termux_setup:
        if not setup_termux_environment():
            print("Warning: Termux environment setup failed, but continuing...")

    # Install box64
    box64_path = None
    if not args.skip_box64:
        box64_path = install_box64_on_android(args.install_dir)
        if not box64_path:
            print("Failed to install box64")
            sys.exit(1)
    else:
        print("Skipping box64 installation")
        # Try to find existing box64
        success, result = run_adb_command("which box64")
        if success and result.stdout.strip():
            box64_path = result.stdout.strip()
        else:
            print("Error: box64 not found and --skip-box64 specified")
            sys.exit(1)

    # Install Wine
    wine_path = None
    if not args.skip_wine:
        wine_path = install_wine_on_android(args.install_dir, box64_path)
        if not wine_path:
            print("Failed to install Wine")
            sys.exit(1)
    else:
        print("Skipping Wine installation")
        # Try to find existing Wine
        success, result = run_adb_command("which wine")
        if success and result.stdout.strip():
            wine_binary = result.stdout.strip()
            wine_path = str(Path(wine_binary).parent.parent)  # Get wine directory
        else:
            print("Error: Wine not found and --skip-wine specified")
            sys.exit(1)

    # Set up Wine prefix
    if not setup_wine_prefix_on_android(args.container_path, wine_path, box64_path):
        print("Failed to set up Wine prefix")
        sys.exit(1)

    # Install winetricks
    if not install_winetricks_on_android(args.container_path, wine_path, box64_path):
        print("Warning: winetricks installation failed, but continuing...")

    # Create launch script
    launch_script = create_launch_script_on_android(args.install_dir, args.container_path, wine_path, box64_path)
    if not launch_script:
        print("Failed to create launch script")
        sys.exit(1)

    # Create Android app launcher
    launcher_script = create_android_app_launcher(args.install_dir, launch_script)
    if not launcher_script:
        print("Failed to create Android launcher")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Android Phone Wine + box64 setup complete!")
    print("=" * 60)
    print(f"Install directory: {args.install_dir}")
    print(f"Wine prefix: {args.container_path}")
    print(f"Launch script: {launch_script}")
    print(f"Android launcher: {launcher_script}")
    print()
    print("To use Wine on your Android device:")
    print("1. Open Termux on your Android device")
    print(f"2. Run: bash {launcher_script}")
    print("3. Or run: source {launch_script}")
    print()
    print("Then you can run Windows applications with:")
    print("  wine your_app.exe")
    print()
    print("For configuration, run:")
    print("  winecfg")
    print()
    print("Note: Performance may vary depending on your Android device.")
    print("Some applications may not work due to ARM64/x86_64 compatibility issues.")


if __name__ == "__main__":
    main()
