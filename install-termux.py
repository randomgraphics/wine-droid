#!/usr/bin/env python3
"""
Android Phone Wine + box64 Setup Script

This script sets up a Wine environment with box64 on a connected Android phone via ADB.
It handles installation of box64, Wine, and necessary dependencies for running Windows applications.

For SSH-based compilation, the script requires:
- paramiko: pip install paramiko
- SSH server running on Termux device
- termux-user.txt file with SSH connection details
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
import termux_utils
# # Import termux utilities
# try:
#     from termux_utils import (
#         read_termux_ssh_config, run_command, run_ssh_command, 
#         push_file_to_android, push_directory_to_android, execute_ssh_command,
#         create_temp_file, push_content_to_android, make_executable_on_android,
#         create_directory_on_android, download_and_push_to_android
#     )
# except ImportError:
#     print("Error: termux-utils.py not found")
#     print("Please make sure termux-utils.py is in the same directory")
#     sys.exit(1)




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
    success, result = termux_utils.run_command("adb devices", check=False)
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




def run_adb_command(cmd):
    """Run a command on Android device via ADB shell."""
    full_cmd = f"adb shell '{cmd}'"
    return termux_utils.run_command(full_cmd, check=False)




def install_termux_on_android():
    """Install Termux on Android device if not present."""
    print("Checking for Termux installation...")
    
    # Check if Termux is installed
    success, result = run_adb_command("pm list packages | grep com.termux")
    termux_installed = success and "com.termux" in result.stdout
    if termux_installed:
        print("Termux is already installed")
    else:
        # Try tnstall termux apk via adb
        # Paths to local APK files in dependencies folder
        termux_apk_path = "dependencies/com.termux_1022.apk"

        # Check if Termux APK exists
        if not os.path.exists(termux_apk_path):
            print(f"Error: Termux APK not found at {termux_apk_path}")
            return False

        # Install Termux APK via adb
        print("Installing Termux APK via adb...")
        success, result = termux_utils.run_command(f"adb install -r {termux_apk_path}", check=False)
        if not success or (result and "Success" not in result.stdout):
            print(f"Failed to install Termux APK: {result.stderr if result else 'Unknown error'}")
            return False
        
        print("Termux installed successfully!")

    # Check if Termux X11 is installed
    success_x11, result_x11 = run_adb_command("pm list packages | grep com.termux.x11")
    termux_x11_installed = success_x11 and "com.termux.x11" in result_x11.stdout
    if termux_x11_installed:
        print("Termux X11 is already installed")
    else:
        # Try to install termux x11 apk via adb
        # Paths to local APK files in dependencies folder
        termux_x11_apk_path = "dependencies/termux-x11-app-arm64-v8a-debug-nightly-release-20250609.apk"

        # Check if Termux X11 APK exists
        if not os.path.exists(termux_x11_apk_path):
            print(f"Error: Termux X11 APK not found at {termux_x11_apk_path}")
            return False

        # Install Termux X11 APK via adb
        print("Installing Termux X11 APK via adb...")
        success, result = termux_utils.run_command(f"adb install -r {termux_x11_apk_path}", check=False)
        if not success or (result and "Success" not in result.stdout):
            print(f"Failed to install Termux X11 APK: {result.stderr if result else 'Unknown error'}")
            return False
        
        print("Termux X11 installed successfully!")

    # Done
    return True

def main():
    if not install_termux_on_android():
        sys.exit(1)

if __name__ == "__main__":
    main()
