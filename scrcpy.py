#!/usr/bin/env python3
"""
Scrcpy Runner Script

This script runs scrcpy using ADB from the Android SDK instead of system ADB.
It automatically detects the Android SDK installation and uses the appropriate ADB executable.

Usage:
    python3 scrcpy.py [script-options] [-- scrcpy-options]

Examples:
    # Basic scrcpy execution
    python3 scrcpy.py

    # Run scrcpy with specific options
    python3 scrcpy.py -- --max-size 1024 --bit-rate 2M

    # Run scrcpy with custom Android SDK path
    python3 scrcpy.py --android-sdk /path/to/android-sdk

    # List available devices
    python3 scrcpy.py --list-devices

    # Run with multiple scrcpy options
    python3 scrcpy.py -- --fullscreen --no-audio --max-fps 30
"""

import os
import sys
import subprocess
import shutil
import argparse
import logging
from pathlib import Path
from typing import Optional, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScrcpyRunner:
    """Scrcpy runner using Android SDK ADB."""
    
    def __init__(self, android_sdk_path: Optional[str] = None):
        """Initialize the scrcpy runner."""
        self.android_sdk = None
        self.adb_path = None
        self.scrcpy_path = None
        
        # Set Android SDK path if provided
        if android_sdk_path:
            self.android_sdk = Path(android_sdk_path).resolve()
        
        # Detect paths
        self._detect_android_sdk()
        self._detect_adb()
        self._detect_scrcpy()
    
    def _detect_android_sdk(self) -> bool:
        """Detect Android SDK installation."""
        if self.android_sdk and self.android_sdk.exists():
            logger.info(f"Using specified Android SDK: {self.android_sdk}")
            return True
        
        logger.info("Detecting Android SDK...")
        
        # Common Android SDK locations
        sdk_paths = [
            os.environ.get('ANDROID_SDK_ROOT'),
            os.environ.get('ANDROID_HOME'),
            os.environ.get('ANDROID_SDK'),
            os.path.expanduser('~/Android/Sdk'),
            os.path.expanduser('~/android-sdk'),
            '/opt/android-sdk',
            '/usr/local/android-sdk',
            '/home/chenli/Android/Sdk'
        ]
        
        for sdk_path in sdk_paths:
            if sdk_path and os.path.exists(sdk_path):
                self.android_sdk = Path(sdk_path).resolve()
                logger.info(f"Found Android SDK at: {self.android_sdk}")
                return True
        
        logger.error("Android SDK not found!")
        logger.info("Please install Android SDK and set ANDROID_SDK_ROOT environment variable")
        logger.info("Or specify the path with --android-sdk option")
        return False
    
    def _detect_adb(self) -> bool:
        """Detect ADB executable in Android SDK."""
        if not self.android_sdk:
            return False
        
        # Common ADB locations in Android SDK
        adb_paths = [
            self.android_sdk / 'platform-tools' / 'adb',
            self.android_sdk / 'platform-tools' / 'adb.exe',
            self.android_sdk / 'tools' / 'adb',
            self.android_sdk / 'tools' / 'adb.exe',
        ]
        
        for adb_path in adb_paths:
            if adb_path.exists():
                self.adb_path = adb_path
                logger.info(f"Found ADB at: {self.adb_path}")
                return True
        
        logger.error(f"ADB not found in Android SDK: {self.android_sdk}")
        logger.info("Please ensure platform-tools are installed in your Android SDK")
        return False
    
    def _detect_scrcpy(self) -> bool:
        """Detect scrcpy executable."""
        # Check for scrcpy in dependencies directory
        scrcpy_paths = [
            Path(__file__).parent / 'dependencies' / 'scrcpy' / 'scrcpy',
            Path(__file__).parent / 'dependencies' / 'scrcpy' / 'scrcpy.exe',
        ]
        
        # Also check system PATH
        system_scrcpy = shutil.which('scrcpy')
        if system_scrcpy:
            scrcpy_paths.append(Path(system_scrcpy))
        
        for scrcpy_path in scrcpy_paths:
            if scrcpy_path and scrcpy_path.exists():
                self.scrcpy_path = scrcpy_path
                logger.info(f"Found scrcpy at: {self.scrcpy_path}")
                return True
        
        logger.error("scrcpy executable not found!")
        logger.info("Please ensure scrcpy is installed or available in dependencies/scrcpy/")
        return False
    
    def check_adb_connection(self) -> bool:
        """Check if ADB is working and devices are connected."""
        if not self.adb_path:
            logger.error("ADB not found")
            return False
        
        logger.info("Checking ADB connection...")
        
        try:
            # Run adb devices command
            result = subprocess.run(
                [str(self.adb_path), 'devices'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"ADB command failed: {result.stderr}")
                return False
            
            # Parse device list
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = [line for line in lines if line.strip() and 'device' in line]
            
            if not devices:
                logger.error("No Android device connected")
                logger.info("Please connect your Android device and enable USB debugging")
                logger.info("Make sure to allow USB debugging when prompted on your device")
                return False
            
            logger.info(f"Found {len(devices)} connected device(s)")
            for device in devices:
                logger.info(f"  {device}")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("ADB command timed out")
            return False
        except Exception as e:
            logger.error(f"Error checking ADB connection: {e}")
            return False
    
    def list_devices(self) -> List[str]:
        """List connected Android devices."""
        if not self.adb_path:
            return []
        
        try:
            result = subprocess.run(
                [str(self.adb_path), 'devices'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = []
            for line in lines:
                if line.strip() and 'device' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
            
            return devices
            
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []
    
    def run_scrcpy(self, scrcpy_args: List[str] = None) -> bool:
        """Run scrcpy with the detected ADB."""
        if not self.scrcpy_path:
            logger.error("scrcpy executable not found")
            return False
        
        if not self.adb_path:
            logger.error("ADB executable not found")
            return False
        
        # Check ADB connection first
        if not self.check_adb_connection():
            return False
        
        # Prepare scrcpy command
        cmd = [str(self.scrcpy_path)]
        
        # Add scrcpy arguments if provided
        if scrcpy_args:
            cmd.extend(scrcpy_args)
        
        # Set ADB path for scrcpy
        env = os.environ.copy()
        env['ADB'] = str(self.adb_path)
        
        logger.info(f"Running scrcpy with ADB: {self.adb_path}")
        logger.info(f"Command: {' '.join(cmd)}")
        
        try:
            # Run scrcpy
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Stream output
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            
            # Wait for process to complete
            return_code = process.wait()
            
            if return_code != 0:
                stderr_output = process.stderr.read()
                if stderr_output:
                    logger.error(f"scrcpy error: {stderr_output}")
                return False
            
            return True
            
        except KeyboardInterrupt:
            logger.info("scrcpy interrupted by user")
            process.terminate()
            return False
        except Exception as e:
            logger.error(f"Error running scrcpy: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run scrcpy using ADB from Android SDK',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run scrcpy with default settings
  %(prog)s -- --max-size 1024                 # Run with max size 1024
  %(prog)s -- --bit-rate 2M                   # Run with bit rate 2M
  %(prog)s --list-devices                      # List connected devices
  %(prog)s --android-sdk /path/to/sdk         # Use custom Android SDK path
  %(prog)s -- --fullscreen --no-audio         # Run fullscreen without audio
        """
    )
    
    # Script-specific options
    parser.add_argument('--android-sdk',
                       help='Path to Android SDK (auto-detected if not specified)')
    parser.add_argument('--list-devices', action='store_true',
                       help='List connected devices and exit')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    # Parse known args and get remaining args for scrcpy
    args, scrcpy_args = parser.parse_known_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create scrcpy runner
    runner = ScrcpyRunner(args.android_sdk)
    
    # List devices if requested
    if args.list_devices:
        devices = runner.list_devices()
        if devices:
            print("Connected devices:")
            for device in devices:
                print(f"  {device}")
        else:
            print("No devices connected")
        return 0
    
    # Run scrcpy with all remaining arguments
    success = runner.run_scrcpy(scrcpy_args)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
