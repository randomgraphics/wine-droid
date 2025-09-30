#!/usr/bin/env python3
"""
Box64 Compilation Script for Android Termux
==========================================

This script compiles box64 from source code directly on an Android phone
running inside the Termux environment. It handles all the necessary
dependencies, platform detection, and compilation process.

Usage:
    python3 compile-box64-termux.py [options]

Examples:
    # Basic compilation with auto-detection
    python3 compile-box64-termux.py

    # Compile with specific platform
    python3 compile-box64-termux.py --platform snapdragon-8gen2

    # Compile with custom build options
    python3 compile-box64-termux.py --cmake-args "-DCMAKE_BUILD_TYPE=Debug"

    # Compile and install to custom location
    python3 compile-box64-termux.py --install-prefix /data/data/com.termux/files/usr/local
"""

import os
import sys
import subprocess
import shutil
import platform
import argparse
import logging
import tempfile
import urllib.request
import tarfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TermuxBox64Builder:
    """Box64 builder specifically designed for Termux on Android."""
    
    def __init__(self, source_dir: str = None, build_dir: str = None):
        self.script_dir = Path(__file__).parent.resolve()
        
        # Default paths for Termux
        if source_dir is None:
            self.source_dir = Path.home() / "box64-source"
        else:
            self.source_dir = Path(source_dir).resolve()
            
        if build_dir is None:
            self.build_dir = Path.home() / "box64-build"
        else:
            self.build_dir = Path(build_dir).resolve()
        
        # Platform detection
        self.host_arch = platform.machine().lower()
        self.host_system = platform.system().lower()
        
        # Build configuration
        self.cmake_args = []
        self.make_args = []
        self.install_prefix = "/data/data/com.termux/files/usr/local"
        
        # Termux-specific platform configurations
        self.platform_configs = {
            # Snapdragon platforms (most common on Android)
            'snapdragon-845': {
                'cmake_args': ['-DSD845=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Snapdragon 845 (Android)'
            },
            'snapdragon-855': {
                'cmake_args': ['-DSD855=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Snapdragon 855 (Android)'
            },
            'snapdragon-865': {
                'cmake_args': ['-DSD865=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Snapdragon 865 (Android)'
            },
            'snapdragon-888': {
                'cmake_args': ['-DSD888=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Snapdragon 888 (Android)'
            },
            'snapdragon-8gen1': {
                'cmake_args': ['-DSD8G1=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Snapdragon 8 Gen 1 (Android)'
            },
            'snapdragon-8gen2': {
                'cmake_args': ['-DSD8G2=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Snapdragon 8 Gen 2 (Android)'
            },
            'snapdragon-8gen3': {
                'cmake_args': ['-DSD8G3=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Snapdragon 8 Gen 3 (Android)'
            },
            
            # Other ARM64 platforms
            'generic-arm64': {
                'cmake_args': ['-DARM64=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Generic ARM64 (Android)'
            },
            'termux': {
                'cmake_args': ['-DTERMUX=ON', '-DCMAKE_C_COMPILER=clang', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Termux (Android)'
            },
            'android': {
                'cmake_args': ['-DANDROID=ON', '-DBAD_SIGNAL=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'Android'
            }
        }
    
    def check_termux_environment(self) -> bool:
        """Check if running in Termux environment."""
        logger.info("Checking Termux environment...")
        
        # Check for Termux-specific environment variables
        if 'TERMUX' not in os.environ:
            logger.error("Not running in Termux environment!")
            logger.info("This script is designed to run inside Termux on Android.")
            logger.info("Please install Termux from F-Droid or GitHub and run this script there.")
            return False
        
        # Check for Termux-specific paths
        termux_paths = [
            '/data/data/com.termux/files/usr',
            '/data/data/com.termux/files/home'
        ]
        
        for path in termux_paths:
            if not os.path.exists(path):
                logger.warning(f"Termux path not found: {path}")
        
        logger.info("Termux environment detected successfully")
        return True
    
    def detect_android_platform(self) -> str:
        """Detect the Android platform/SoC."""
        logger.info("Detecting Android platform...")
        
        # Check for Snapdragon
        if self._is_snapdragon():
            sd_model = self._get_snapdragon_model()
            if sd_model:
                logger.info(f"Detected Snapdragon: {sd_model}")
                return sd_model
        
        # Check for other ARM64 platforms
        if self.host_arch in ['aarch64', 'arm64']:
            logger.info("Detected generic ARM64 platform")
            return 'generic-arm64'
        
        # Default to Termux configuration
        logger.info("Using Termux configuration")
        return 'termux'
    
    def _is_snapdragon(self) -> bool:
        """Check if running on Snapdragon SoC."""
        try:
            # Check CPU info
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'qualcomm' in cpuinfo.lower() or 'snapdragon' in cpuinfo.lower()
        except:
            pass
        
        # Check device model
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().lower()
                return 'snapdragon' in model or 'qualcomm' in model
        except:
            pass
        
        return False
    
    def _get_snapdragon_model(self) -> Optional[str]:
        """Get Snapdragon model."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                
                # Check for specific Snapdragon models
                if '845' in cpuinfo:
                    return 'snapdragon-845'
                elif '855' in cpuinfo:
                    return 'snapdragon-855'
                elif '865' in cpuinfo:
                    return 'snapdragon-865'
                elif '888' in cpuinfo:
                    return 'snapdragon-888'
                elif '8 gen 1' in cpuinfo.lower():
                    return 'snapdragon-8gen1'
                elif '8 gen 2' in cpuinfo.lower():
                    return 'snapdragon-8gen2'
                elif '8 gen 3' in cpuinfo.lower():
                    return 'snapdragon-8gen3'
        except:
            pass
        
        return None
    
    def install_termux_dependencies(self) -> bool:
        """Install required dependencies in Termux."""
        logger.info("Installing Termux dependencies...")
        
        # Update package lists
        logger.info("Updating package lists...")
        success, result = self._run_command("pkg update -y")
        if not success:
            logger.error("Failed to update package lists")
            return False
        
        # Install essential packages
        packages = [
            "git", "wget", "curl", "unzip", "tar", "python", "python-pip",
            "build-essential", "cmake", "pkg-config", "clang", "make",
            "libc6-dev", "libstdc++", "zlib", "libffi", "openssl"
        ]
        
        for package in packages:
            logger.info(f"Installing {package}...")
            success, result = self._run_command(f"pkg install -y {package}")
            if not success:
                logger.warning(f"Failed to install {package}: {result.stderr if result else 'Unknown error'}")
        
        # Install Python packages
        python_packages = ["setuptools", "wheel"]
        for package in python_packages:
            logger.info(f"Installing Python package {package}...")
            success, result = self._run_command(f"pip install {package}")
            if not success:
                logger.warning(f"Failed to install Python package {package}")
        
        logger.info("Dependencies installation completed")
        return True
    
    def clone_box64_source(self) -> bool:
        """Clone box64 source code."""
        if self.source_dir.exists():
            logger.info(f"Box64 source already exists at: {self.source_dir}")
            return True
        
        logger.info("Cloning box64 source code...")
        
        # Create source directory
        self.source_dir.mkdir(parents=True, exist_ok=True)
        
        # Clone repository
        clone_cmd = [
            'git', 'clone', 
            'https://github.com/ptitSeb/box64.git',
            str(self.source_dir)
        ]
        
        success, result = self._run_command(' '.join(clone_cmd))
        if not success:
            logger.error(f"Failed to clone box64 repository: {result.stderr if result else 'Unknown error'}")
            return False
        
        logger.info("Successfully cloned box64 repository")
        return True
    
    def setup_build_environment(self) -> bool:
        """Set up the build environment."""
        logger.info("Setting up build environment...")
        
        # Create build directory
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        # Change to build directory
        os.chdir(self.build_dir)
        logger.info(f"Build directory: {self.build_dir}")
        
        return True
    
    def configure_build(self, platform: str, custom_args: List[str] = None) -> bool:
        """Configure the build with CMake."""
        logger.info(f"Configuring build for platform: {platform}")
        
        if platform not in self.platform_configs:
            logger.error(f"Unknown platform: {platform}")
            logger.info(f"Available platforms: {', '.join(self.platform_configs.keys())}")
            return False
        
        config = self.platform_configs[platform]
        logger.info(f"Platform description: {config['description']}")
        
        # Base CMake command
        cmake_cmd = ['cmake', str(self.source_dir)]
        
        # Add platform-specific arguments
        self.cmake_args.extend(config['cmake_args'])
        
        # Add Termux-specific optimizations
        self.cmake_args.extend([
            '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
            '-DCMAKE_INSTALL_PREFIX=' + self.install_prefix,
            '-DUSE_CCACHE=OFF',  # CCache might not be available in Termux
            '-DNOALIGN=ON',      # Disable alignment for better compatibility
        ])
        
        # Add custom arguments
        if custom_args:
            self.cmake_args.extend(custom_args)
        
        # Add all CMake arguments
        cmake_cmd.extend(self.cmake_args)
        
        logger.info(f"CMake command: {' '.join(cmake_cmd)}")
        
        success, result = self._run_command(' '.join(cmake_cmd))
        if not success:
            logger.error(f"CMake configuration failed: {result.stderr if result else 'Unknown error'}")
            return False
        
        logger.info("CMake configuration successful")
        return True
    
    def build(self, jobs: int = None) -> bool:
        """Build box64."""
        logger.info("Building box64...")
        
        if jobs is None:
            # Use fewer jobs for mobile devices to avoid overheating
            jobs = min(2, os.cpu_count() or 2)
        
        make_cmd = ['make', f'-j{jobs}']
        self.make_args.extend(make_cmd)
        
        logger.info(f"Make command: {' '.join(self.make_args)}")
        
        success, result = self._run_command(' '.join(self.make_args))
        if not success:
            logger.error(f"Build failed: {result.stderr if result else 'Unknown error'}")
            return False
        
        logger.info("Build successful")
        return True
    
    def install(self) -> bool:
        """Install box64."""
        logger.info("Installing box64...")
        
        success, result = self._run_command('make install')
        if not success:
            logger.error(f"Installation failed: {result.stderr if result else 'Unknown error'}")
            return False
        
        logger.info("Installation successful")
        return True
    
    def create_launch_script(self) -> bool:
        """Create a launch script for easy usage."""
        logger.info("Creating launch script...")
        
        script_path = Path.home() / "box64-launch.sh"
        script_content = f"""#!/bin/bash
# Box64 Launch Script for Termux

export BOX64_PATH="{self.install_prefix}/bin/box64"
export PATH="{self.install_prefix}/bin:$PATH"

echo "Box64 environment loaded!"
echo "Box64 path: $BOX64_PATH"
echo ""
echo "Usage:"
echo "  box64 <x86_64_program>"
echo "  box64 wine <windows_program>"
echo ""
echo "Examples:"
echo "  box64 /path/to/x86_64/program"
echo "  box64 wine notepad.exe"
"""

        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make executable
            os.chmod(script_path, 0o755)
            
            logger.info(f"Launch script created: {script_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create launch script: {e}")
            return False
    
    def run_tests(self) -> bool:
        """Run box64 tests."""
        logger.info("Running tests...")
        
        success, result = self._run_command('ctest -j2')
        if not success:
            logger.warning(f"Tests failed: {result.stderr if result else 'Unknown error'}")
            return False
        
        logger.info("Tests completed successfully")
        return True
    
    def clean(self):
        """Clean build directory."""
        logger.info("Cleaning build directory...")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            logger.info("Build directory cleaned")
    
    def _run_command(self, cmd: str) -> Tuple[bool, Optional[subprocess.CompletedProcess]]:
        """Run a shell command and return success status and result."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True
            )
            return result.returncode == 0, result
        except Exception as e:
            logger.error(f"Exception running command '{cmd}': {e}")
            return False, None
    
    def show_platforms(self):
        """Show available platforms."""
        print("\nAvailable platforms for Termux/Android:")
        print("=" * 50)
        
        for platform, config in self.platform_configs.items():
            print(f"{platform:<20} - {config['description']}")
        
        print("\nAuto-detection will be used if no platform is specified.")
    
    def build_box64(self, platform: str = None, custom_args: List[str] = None, 
                   jobs: int = None, install: bool = True, test: bool = False,
                   clean_build: bool = False, clone_source: bool = True):
        """Main build process."""
        logger.info("Starting box64 build process for Termux...")
        
        # Check Termux environment
        if not self.check_termux_environment():
            return False
        
        # Auto-detect platform if not specified
        if not platform:
            platform = self.detect_android_platform()
            logger.info(f"Auto-detected platform: {platform}")
        
        # Clean build if requested
        if clean_build:
            self.clean()
        
        # Install dependencies
        if not self.install_termux_dependencies():
            logger.error("Failed to install dependencies")
            return False
        
        # Clone source if needed
        if clone_source:
            if not self.clone_box64_source():
                return False
        
        # Set up build environment
        if not self.setup_build_environment():
            return False
        
        # Configure build
        if not self.configure_build(platform, custom_args):
            return False
        
        # Build
        if not self.build(jobs):
            return False
        
        # Run tests if requested
        if test:
            if not self.run_tests():
                logger.warning("Tests failed, but continuing...")
        
        # Install if requested
        if install:
            if not self.install():
                return False
            
            # Create launch script
            self.create_launch_script()
        
        logger.info("Box64 build process completed successfully!")
        logger.info(f"Box64 installed at: {self.install_prefix}/bin/box64")
        logger.info(f"Launch script: {Path.home() / 'box64-launch.sh'}")
        return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Box64 Compilation Script for Android Termux',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Auto-detect platform and build
  %(prog)s --platform snapdragon-8gen2       # Build for Snapdragon 8 Gen 2
  %(prog)s --cmake-args "-DCMAKE_BUILD_TYPE=Debug"  # Custom CMake arguments
  %(prog)s --jobs 2 --test                   # Build with 2 jobs and run tests
  %(prog)s --clean --platform snapdragon-845 # Clean build for Snapdragon 845
  %(prog)s --list-platforms                  # Show available platforms
        """
    )
    
    parser.add_argument('--platform', '-p',
                       help='Target platform (auto-detect if not specified)')
    parser.add_argument('--cmake-args', nargs='*', default=[],
                       help='Additional CMake arguments')
    parser.add_argument('--jobs', '-j', type=int, default=None,
                       help='Number of parallel build jobs (default: 2 for mobile)')
    parser.add_argument('--no-install', action='store_true',
                       help='Build without installing')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Run tests after building')
    parser.add_argument('--clean', action='store_true',
                       help='Clean build directory before building')
    parser.add_argument('--list-platforms', action='store_true',
                       help='List available platforms and exit')
    parser.add_argument('--source-dir',
                       help='Source directory (default: ~/box64-source)')
    parser.add_argument('--build-dir',
                       help='Build directory (default: ~/box64-build)')
    parser.add_argument('--install-prefix',
                       default='/data/data/com.termux/files/usr/local',
                       help='Installation prefix (default: /data/data/com.termux/files/usr/local)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--no-clone', action='store_true',
                       help='Skip cloning source (use existing source)')
    
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create builder instance
    builder = TermuxBox64Builder(args.source_dir, args.build_dir)
    builder.install_prefix = args.install_prefix
    
    # Show platforms if requested
    if args.list_platforms:
        builder.show_platforms()
        return 0
    
    # Build box64
    success = builder.build_box64(
        platform=args.platform,
        custom_args=args.cmake_args,
        jobs=args.jobs,
        install=not args.no_install,
        test=args.test,
        clean_build=args.clean,
        clone_source=not args.no_clone
    )
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
