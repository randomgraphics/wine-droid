#!/usr/bin/env python3
"""
Termux Utilities Module

This module provides utilities for interacting with Termux on Android devices
via SSH and SCP. It includes functions for file transfer, command execution,
and configuration management.

Dependencies:
- paramiko: pip install paramiko
- SSH server running on Termux device
- termux-user.txt file with SSH connection details
"""

import os
import subprocess
import tempfile
try:
    import paramiko
except ImportError:
    print("Error: paramiko is required for SSH connections")
    print("Please install it with: pip install paramiko")
    raise


def read_termux_ssh_config():
    """Read SSH connection details from termux-user.txt file."""
    termux_config_path = "/home/chenli/work/wine/termux-user.txt"
    
    if not os.path.exists(termux_config_path):
        print(f"Error: termux-user.txt not found at {termux_config_path}")
        return None, None, None
    
    try:
        with open(termux_config_path, 'r') as f:
            lines = f.readlines()
        
        host = None
        port = 8022  # Default SSH port for Termux
        user = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('host='):
                host = line.split('=', 1)[1]
            elif line.startswith('port='):
                port = int(line.split('=', 1)[1])
            elif line.startswith('user='):
                user = line.split('=', 1)[1]
        
        if not host or not user:
            print("Error: Missing host or user in termux-user.txt")
            return None, None, None
        
        return host, port, user
    except Exception as e:
        print(f"Error reading termux-user.txt: {e}")
        return None, None, None


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


def run_ssh_command(host, port, user, cmd, timeout=300):
    """Run a command on Termux device via SSH."""
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to SSH server
        print(f"Connecting to {user}@{host}:{port}...")
        ssh.connect(host, port=port, username=user, timeout=30)
        
        # Execute command
        print(f"Executing command: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        
        # Get output
        stdout_data = stdout.read().decode('utf-8')
        stderr_data = stderr.read().decode('utf-8')
        exit_code = stdout.channel.recv_exit_status()
        
        # Close connection
        ssh.close()
        
        # Create a result object similar to subprocess.run
        class SSHResult:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr
        
        result = SSHResult(exit_code, stdout_data, stderr_data)
        
        if exit_code != 0:
            print(f"SSH command failed with exit code {exit_code}")
            print(f"Error output: {stderr_data}")
            return False, result
        
        return True, result
        
    except paramiko.AuthenticationException:
        print("SSH authentication failed")
        return False, None
    except paramiko.SSHException as e:
        print(f"SSH error: {e}")
        return False, None
    except Exception as e:
        print(f"Error connecting via SSH: {e}")
        return False, None


def push_file_to_android(local_path, android_path):
    """Push a file to Android device via SCP."""
    print(f"Pushing {local_path} to {android_path}")
    
    # Read SSH connection details
    host, port, user = read_termux_ssh_config()
    if not host or not user:
        print("Failed to read SSH connection details from termux-user.txt")
        return False
    
    # Use SCP to transfer the file
    cmd = f"scp -P {port} {local_path} {user}@{host}:{android_path}"
    success, result = run_command(cmd, check=False)
    if not success:
        print(f"Error pushing file: {result.stderr if result else 'Unknown error'}")
        return False
    return True


def push_directory_to_android(local_path, android_path):
    """Push a directory to Android device via SCP recursively."""
    print(f"Pushing directory {local_path} to {android_path}")
    
    # Read SSH connection details
    host, port, user = read_termux_ssh_config()
    if not host or not user:
        print("Failed to read SSH connection details from termux-user.txt")
        return False
    
    # Use SCP with recursive flag to transfer the directory
    cmd = f"scp -r -P {port} {local_path} {user}@{host}:{android_path}"
    success, result = run_command(cmd, check=False)
    if not success:
        print(f"Error pushing directory: {result.stderr if result else 'Unknown error'}")
        return False
    return True


def execute_ssh_command(cmd, timeout=300):
    """Execute a command on Termux device via SSH using config from termux-user.txt."""
    host, port, user = read_termux_ssh_config()
    if not host or not user:
        print("Failed to read SSH connection details from termux-user.txt")
        return False, None
    
    return run_ssh_command(host, port, user, cmd, timeout)


def create_temp_file(content, suffix="", prefix="tmp"):
    """Create a temporary file with the given content and return its path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, prefix=prefix, delete=False) as tmp_file:
        tmp_file.write(content)
        return tmp_file.name


def push_content_to_android(content, android_path, suffix="", prefix="tmp"):
    """Create a temporary file with content and push it to Android device."""
    # Create temporary file
    tmp_path = create_temp_file(content, suffix, prefix)
    
    try:
        # Push to Android
        success = push_file_to_android(tmp_path, android_path)
        return success
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def make_executable_on_android(android_path):
    """Make a file executable on Android device via SSH."""
    cmd = f"chmod +x {android_path}"
    success, result = execute_ssh_command(cmd)
    if not success:
        print(f"Failed to make file executable: {result.stderr if result else 'Unknown error'}")
        return False
    return True


def create_directory_on_android(android_path):
    """Create a directory on Android device via SSH."""
    cmd = f"mkdir -p {android_path}"
    success, result = execute_ssh_command(cmd)
    if not success:
        print(f"Failed to create directory: {result.stderr if result else 'Unknown error'}")
        return False
    return True


def check_file_exists_on_android(android_path):
    """Check if a file exists on Android device via SSH."""
    cmd = f"test -f {android_path}"
    success, result = execute_ssh_command(cmd)
    return success


def check_directory_exists_on_android(android_path):
    """Check if a directory exists on Android device via SSH."""
    cmd = f"test -d {android_path}"
    success, result = execute_ssh_command(cmd)
    return success


def get_file_info_on_android(android_path):
    """Get file information on Android device via SSH."""
    cmd = f"ls -la {android_path}"
    success, result = execute_ssh_command(cmd)
    if not success:
        return None
    return result.stdout.strip()


def download_and_push_to_android(url, android_path, timeout=300):
    """Download a file from URL and push it to Android device."""
    import urllib.request
    
    # Download to temporary location
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        print(f"Downloading {url}...")
        urllib.request.urlretrieve(url, tmp_path)
        
        # Push to Android
        success = push_file_to_android(tmp_path, android_path)
        return success
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
