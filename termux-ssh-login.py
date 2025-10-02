#!/usr/bin/env python3
"""
Termux SSH Login Script
=======================

This script reads server information from termux-user.txt and connects
to a Termux instance running on an Android device via SSH.

Usage:
    python3 termux-ssh-login.py [options]

Examples:
    # Basic connection
    python3 termux-ssh-login.py

    # Connect with specific command
    python3 termux-ssh-login.py --command "ls -la"

    # Connect with interactive shell
    python3 termux-ssh-login.py --interactive

    # Show connection info without connecting
    python3 termux-ssh-login.py --info
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TermuxSSHClient:
    """SSH client for connecting to Termux on Android devices."""
    
    def __init__(self, config_file: str = "termux-user.txt"):
        self.script_dir = Path(__file__).parent.resolve()
        self.config_file = self.script_dir / config_file
        self.config = {}
        
    def read_config(self) -> bool:
        """Read server configuration from termux-user.txt."""
        logger.info(f"Reading configuration from: {self.config_file}")
        
        if not self.config_file.exists():
            logger.error(f"Configuration file not found: {self.config_file}")
            logger.info("Please create termux-user.txt with the following format:")
            logger.info("  host=your_termux_host")
            logger.info("  port=8022")
            logger.info("  user=your_termux_user")
            return False
        
        try:
            with open(self.config_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        self.config[key] = value
                    else:
                        logger.warning(f"Invalid line {line_num}: {line}")
            
            # Validate required fields
            required_fields = ['host', 'port', 'user']
            missing_fields = [field for field in required_fields if field not in self.config]
            
            if missing_fields:
                logger.error(f"Missing required fields: {', '.join(missing_fields)}")
                return False
            
            logger.info("Configuration loaded successfully")
            logger.info(f"Host: {self.config['host']}")
            logger.info(f"Port: {self.config['port']}")
            logger.info(f"User: {self.config['user']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error reading configuration file: {e}")
            return False
    
    def check_ssh_client(self) -> bool:
        """Check if SSH client is available."""
        logger.info("Checking SSH client availability...")
        
        # Check if ssh command is available
        try:
            result = subprocess.run(['ssh', '-V'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"SSH client found: {result.stderr.strip()}")
                return True
        except FileNotFoundError:
            pass
        
        logger.error("SSH client not found!")
        logger.info("Please install OpenSSH client:")
        logger.info("  Ubuntu/Debian: sudo apt install openssh-client")
        logger.info("  Arch Linux: sudo pacman -S openssh")
        logger.info("  Fedora: sudo dnf install openssh-clients")
        logger.info("  macOS: brew install openssh")
        return False
    
    def connect_interactive(self) -> bool:
        """Connect to Termux with interactive shell."""
        logger.info("Connecting to Termux with interactive shell...")
        
        host = self.config['host']
        port = self.config['port']
        user = self.config['user']
        
        # Build SSH command
        ssh_cmd = ['ssh', '-p', port, f'{user}@{host}']
        
        logger.info(f"SSH command: {' '.join(ssh_cmd)}")
        logger.info("Connecting... (use 'exit' to disconnect)")
        
        try:
            # Run SSH interactively
            subprocess.run(ssh_cmd)
            return True
        except KeyboardInterrupt:
            logger.info("Connection interrupted by user")
            return True
        except Exception as e:
            logger.error(f"SSH connection error: {e}")
            return False
    
    def execute_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Execute a command on the Termux server."""
        logger.info(f"Executing command: {command}")
        
        host = self.config['host']
        port = self.config['port']
        user = self.config['user']
        
        # Build SSH command
        ssh_cmd = ['ssh', '-p', port, f'{user}@{host}', command]
        
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("Command executed successfully")
                return True, result.stdout
            else:
                logger.error(f"Command failed: {result.stderr}")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            logger.error("Command execution timed out")
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return False, str(e)
    
    def show_info(self):
        """Show connection information without connecting."""
        print("\nTermux SSH Connection Information")
        print("=" * 40)
        print(f"Host: {self.config['host']}")
        print(f"Port: {self.config['port']}")
        print(f"User: {self.config['user']}")
        print(f"Config file: {self.config_file}")
        print()
        print("SSH command:")
        print(f"  ssh -p {self.config['port']} {self.config['user']}@{self.config['host']}")
        print()
        print("Available options:")
        print("  --interactive    Connect with interactive shell")
        print("  --command CMD    Execute specific command")
        print("  --info          Show this information")
        print("  --copy-key      Copy public key to Termux")
    
    def copy_public_key(self) -> bool:
        """Copy public key to Termux using ssh-copy-id."""
        logger.info("Copying public key to Termux...")
        
        host = self.config['host']
        port = self.config['port']
        user = self.config['user']
        
        # Check if ssh-copy-id is available
        try:
            result = subprocess.run(['ssh-copy-id', '-V'], capture_output=True, text=True)
            if result.returncode != 0 and result.returncode != 1:
                logger.error("ssh-copy-id not found!")
                logger.info("Please install OpenSSH client:")
                logger.info("  Ubuntu/Debian: sudo apt install openssh-client")
                logger.info("  Arch Linux: sudo pacman -S openssh")
                logger.info("  Fedora: sudo dnf install openssh-clients")
                return False
        except FileNotFoundError:
            logger.error("ssh-copy-id not found!")
            logger.info("Please install OpenSSH client:")
            logger.info("  Ubuntu/Debian: sudo apt install openssh-client")
            logger.info("  Arch Linux: sudo pacman -S openssh")
            logger.info("  Fedora: sudo dnf install openssh-clients")
            return False
        
        # Check if public key exists
        public_key_path = Path.home() / '.ssh' / 'id_rsa.pub'
        if not public_key_path.exists():
            logger.error(f"Public key not found at: {public_key_path}")
            logger.info("Please generate an SSH key pair first:")
            logger.info("  ssh-keygen -t rsa -b 4096 -C 'your_email@example.com'")
            return False
        
        # Build ssh-copy-id command
        ssh_copy_id_cmd = ['ssh-copy-id', '-p', port, f'{user}@{host}']
        
        logger.info(f"SSH copy-id command: {' '.join(ssh_copy_id_cmd)}")
        logger.info("This will copy your public key to the Termux device")
        logger.info("You may be prompted for the Termux user password")
        
        try:
            # Run ssh-copy-id
            result = subprocess.run(ssh_copy_id_cmd, timeout=60)
            if result.returncode == 0:
                logger.info("Public key copied successfully!")
                logger.info("You can now connect without a password using:")
                logger.info(f"  ssh -p {port} {user}@{host}")
                return True
            else:
                logger.error("Failed to copy public key")
                return False
        except subprocess.TimeoutExpired:
            logger.error("ssh-copy-id timed out")
            return False
        except Exception as e:
            logger.error(f"Error running ssh-copy-id: {e}")
            return False

    def setup_termux_ssh(self) -> bool:
        """Help user set up SSH on Termux."""
        logger.info("Setting up SSH on Termux...")
        
        print("\nTo enable SSH on your Termux device:")
        print("1. Open Termux on your Android device")
        print("2. Install OpenSSH:")
        print("   pkg install openssh")
        print("3. Start SSH service:")
        print("   sshd")
        print("4. Set a password for your user:")
        print("   passwd")
        print("5. Get your IP address:")
        print("   ip route get 1.1.1.1 | awk '{print $7}'")
        print("6. Update termux-user.txt with your device's IP address")
        print()
        print("Note: Make sure your Android device and computer are on the same network")
        
        return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='SSH Login Script for Termux on Android',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Connect with interactive shell
  %(prog)s --command "ls -la"        # Execute specific command
  %(prog)s --interactive             # Connect with interactive shell
  %(prog)s --info                    # Show connection info
  %(prog)s --setup                   # Help with Termux SSH setup
  %(prog)s --copy-key                # Copy public key to Termux
        """
    )
    
    parser.add_argument('--config', '-c', default='termux-user.txt',
                       help='Configuration file (default: termux-user.txt)')
    parser.add_argument('--command', '-cmd',
                       help='Execute specific command and exit')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Connect with interactive shell (default)')
    parser.add_argument('--info', action='store_true',
                       help='Show connection information')
    parser.add_argument('--setup', action='store_true',
                       help='Show Termux SSH setup instructions')
    parser.add_argument('--copy-key', action='store_true',
                       help='Copy public key to Termux using ssh-copy-id')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create SSH client
    client = TermuxSSHClient(args.config)
    
    # Show setup instructions if requested
    if args.setup:
        client.setup_termux_ssh()
        return 0
    
    # Read configuration
    if not client.read_config():
        return 1
    
    # Copy public key if requested
    if args.copy_key:
        if not client.copy_public_key():
            return 1
        return 0
    
    # Show info if requested
    if args.info:
        client.show_info()
        return 0
    
    # Check SSH client
    if not client.check_ssh_client():
        return 1
    
    # Execute command if specified
    if args.command:
        success, output = client.execute_command(args.command)
        if success:
            print(output)
            return 0
        else:
            logger.error(f"Command failed: {output}")
            return 1
    
    # Default: interactive connection
    client.connect_interactive()
    return 0

if __name__ == '__main__':
    sys.exit(main())
