#!/usr/bin/env python3
"""
Box64 Cross-Compilation Script for Android SDK Toolchain
=======================================================

This script cross-compiles box64 from source code using the Android SDK/NDK toolchain
on a local development machine. It handles Android SDK detection, toolchain setup,
and compilation process for various Android architectures.

Usage:
    python3 compile-box64/android-sdk.py [options]

Examples:
    # Basic cross-compilation with auto-detection
    python3 compile-box64/android-sdk.py

    # Cross-compile for specific Android architecture
    python3 compile-box64/android-sdk.py --arch arm64-v8a

    # Cross-compile with custom Android SDK path
    python3 compile-box64/android-sdk.py --android-sdk /path/to/android-sdk

    # Cross-compile with custom build options
    python3 compile-box64/android-sdk.py --cmake-args "-DCMAKE_BUILD_TYPE=Debug"

    # Cross-compile and install to custom location
    python3 compile-box64/android-sdk.py --install-prefix /path/to/install
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
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AndroidBox64Builder:
    """Box64 cross-compiler for Android using Android SDK/NDK toolchain."""
    
    def __init__(self, source_dir: str = None, build_dir: str = None):
        self.script_dir = Path(__file__).parent.resolve()
        
        # Default paths
        if source_dir is None:
            self.source_dir = self.script_dir / "dependencies" / "box64"
        else:
            self.source_dir = Path(source_dir).resolve()
            
        if build_dir is None:
            self.build_dir = self.script_dir / "build" / "box64" / "android"
        else:
            self.build_dir = Path(build_dir).resolve()
        
        # Host system detection
        self.host_arch = platform.machine().lower()
        self.host_system = platform.system().lower()
        
        # Build configuration
        self.cmake_args = []
        self.make_args = []
        self.install_prefix = "/tmp/box64/android"
        
        # Android SDK/NDK paths
        self.android_sdk = None
        self.android_ndk = None
        self.ndk_version = None
        
        # Android architecture configurations
        self.android_archs = {
            'arm64-v8a': {
                'cmake_args': ['-DANDROID=ON', '-DARM64=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'ARM64 (64-bit)',
                'abi': 'arm64-v8a',
                'toolchain': 'aarch64-linux-android'
            },
            'armeabi-v7a': {
                'cmake_args': ['-DANDROID=ON', '-DARM64=OFF', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'ARM (32-bit)',
                'abi': 'armeabi-v7a',
                'toolchain': 'arm-linux-androideabi'
            },
            'x86_64': {
                'cmake_args': ['-DANDROID=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'x86_64 (64-bit)',
                'abi': 'x86_64',
                'toolchain': 'x86_64-linux-android'
            },
            'x86': {
                'cmake_args': ['-DANDROID=ON', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                'description': 'x86 (32-bit)',
                'abi': 'x86',
                'toolchain': 'i686-linux-android'
            }
        }
    
    def detect_android_sdk(self) -> bool:
        """Detect Android SDK installation."""
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
                break
        
        if not self.android_sdk:
            logger.error("Android SDK not found!")
            logger.info("Please install Android SDK and set ANDROID_SDK_ROOT environment variable")
            logger.info("Or specify the path with --android-sdk option")
            return False
        
        # Detect NDK
        return self.detect_android_ndk()
    
    def detect_android_ndk(self) -> bool:
        """Detect Android NDK installation."""
        logger.info("Detecting Android NDK...")
        
        if not self.android_sdk:
            return False
        
        # Look for NDK in SDK
        ndk_paths = [
            self.android_sdk / "ndk",
            self.android_sdk / "ndk-bundle",
            self.android_sdk / "ndk" / "latest"
        ]
        
        # Also check for standalone NDK
        standalone_ndk_paths = [
            os.environ.get('ANDROID_NDK_ROOT'),
            os.environ.get('ANDROID_NDK'),
            os.path.expanduser('~/Android/Sdk/ndk'),
            os.path.expanduser('~/android-ndk'),
            '/opt/android-ndk',
            '/usr/local/android-ndk'
        ]
        
        all_ndk_paths = ndk_paths + [Path(p) for p in standalone_ndk_paths if p]
        
        for ndk_path in all_ndk_paths:
            if ndk_path.exists():
                # Check if it's a valid NDK
                if self._is_valid_ndk(ndk_path):
                    self.android_ndk = ndk_path.resolve()
                    self.ndk_version = self._get_ndk_version(ndk_path)
                    logger.info(f"Found Android NDK at: {self.android_ndk}")
                    logger.info(f"NDK version: {self.ndk_version}")
                    return True
        
        logger.error("Android NDK not found!")
        logger.info("Please install Android NDK and set ANDROID_NDK_ROOT environment variable")
        logger.info("Or specify the path with --android-ndk option")
        return False
    
    def _is_valid_ndk(self, ndk_path: Path) -> bool:
        """Check if the path contains a valid Android NDK."""
        required_files = [
            'build/cmake/android.toolchain.cmake',
            'toolchains/llvm/prebuilt/linux-x86_64/bin/clang',
            'toolchains/llvm/prebuilt/linux-x86_64/bin/clang++'
        ]
        
        for file_path in required_files:
            if not (ndk_path / file_path).exists():
                return False
        
        return True
    
    def _get_ndk_version(self, ndk_path: Path) -> str:
        """Get NDK version."""
        try:
            # Try to read from source.properties
            props_file = ndk_path / "source.properties"
            if props_file.exists():
                with open(props_file, 'r') as f:
                    for line in f:
                        if line.startswith('Pkg.Revision'):
                            return line.split('=')[1].strip()
            
            # Try to read from CMakeLists.txt
            cmake_file = ndk_path / "CMakeLists.txt"
            if cmake_file.exists():
                with open(cmake_file, 'r') as f:
                    content = f.read()
                    if 'set(ANDROID_NDK_VERSION' in content:
                        for line in content.split('\n'):
                            if 'set(ANDROID_NDK_VERSION' in line:
                                version = line.split('"')[1]
                                return version
        except:
            pass
        
        return "unknown"
    
    def setup_toolchain(self, arch: str) -> bool:
        """Set up Android toolchain for cross-compilation."""
        logger.info(f"Setting up Android toolchain for {arch}")
        
        if arch not in self.android_archs:
            logger.error(f"Unsupported Android architecture: {arch}")
            return False
        
        arch_config = self.android_archs[arch]
        
        # Set up toolchain paths
        toolchain_dir = self.android_ndk / "toolchains" / "llvm" / "prebuilt" / "linux-x86_64"
        
        if not toolchain_dir.exists():
            logger.error(f"Toolchain directory not found: {toolchain_dir}")
            return False
        
        # Set up environment variables
        os.environ['ANDROID_NDK_ROOT'] = str(self.android_ndk)
        os.environ['ANDROID_SDK_ROOT'] = str(self.android_sdk)
        
        # Configure CMake arguments for Android
        self.cmake_args.extend([
            f'-DCMAKE_TOOLCHAIN_FILE={self.android_ndk}/build/cmake/android.toolchain.cmake',
            f'-DANDROID_ABI={arch_config["abi"]}',
            f'-DANDROID_PLATFORM=android-24',  # Minimum API level
            '-DANDROID_STL=c++_shared',
            '-DANDROID_TOOLCHAIN=clang',
            '-DANDROID_ARM_NEON=ON' if 'arm' in arch else '',
            '-DCMAKE_ANDROID_ARCH_ABI=' + arch_config["abi"],
            '-DCMAKE_ANDROID_NDK=' + str(self.android_ndk),
            '-DCMAKE_SYSTEM_NAME=Android',
            '-DCMAKE_SYSTEM_VERSION=24',
            '-DCMAKE_ANDROID_STL_TYPE=c++_shared'
        ])
        
        # Add architecture-specific arguments
        self.cmake_args.extend(arch_config['cmake_args'])
        
        # Add Android-specific optimizations
        self.cmake_args.extend([
            '-DANDROID=ON',
            '-DBAD_SIGNAL=ON',  # Workaround for Android signal handling
            '-DNOALIGN=ON',     # Disable alignment for better compatibility
            '-DUSE_CCACHE=OFF'  # CCache might not work well with cross-compilation
        ])
        
        logger.info("Android toolchain configured successfully")
        return True
    
    def clone_box64_source(self) -> bool:
        """Clone box64 source code if not present."""
        if self.source_dir.exists() and (self.source_dir / "CMakeLists.txt").exists():
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
    
    def configure_build(self, arch: str, custom_args: List[str] = None) -> bool:
        """Configure the build with CMake."""
        logger.info(f"Configuring build for Android architecture: {arch}")
        
        if arch not in self.android_archs:
            logger.error(f"Unsupported Android architecture: {arch}")
            return False
        
        arch_config = self.android_archs[arch]
        logger.info(f"Architecture description: {arch_config['description']}")
        
        # Base CMake command
        cmake_cmd = ['cmake', str(self.source_dir)]
        
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
            jobs = os.cpu_count() or 4
        
        make_cmd = ['cmake', '--build', '.', f'-j{jobs}']
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
    
    def create_android_package(self, arch: str) -> bool:
        """Create an Android package with box64 binary."""
        logger.info(f"Creating Android package for {arch}...")
        
        package_dir = self.build_dir / f"box64/android-{arch}"
        package_dir.mkdir(exist_ok=True)
        
        # Copy box64 binary
        box64_binary = self.build_dir / "box64"
        if box64_binary.exists():
            shutil.copy2(box64_binary, package_dir / "box64")
            os.chmod(package_dir / "box64", 0o755)
        else:
            logger.error("Box64 binary not found after build")
            return False
        
        # Create installation script
        install_script = package_dir / "install.sh"
        install_content = f"""#!/bin/bash
# Box64 Android Installation Script for {arch}

echo "Installing box64 for Android {arch}..."

# Create installation directory
INSTALL_DIR="/data/local/tmp/box64"
mkdir -p "$INSTALL_DIR"

# Copy box64 binary
cp box64 "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/box64"

echo "Box64 installed to: $INSTALL_DIR/box64"
echo ""
echo "Usage:"
echo "  $INSTALL_DIR/box64 <x86_64_program>"
echo "  $INSTALL_DIR/box64 wine <windows_program>"
echo ""
echo "To add to PATH, run:"
echo "  export PATH=\"$INSTALL_DIR:$PATH\""
"""
        
        with open(install_script, 'w') as f:
            f.write(install_content)
        os.chmod(install_script, 0o755)
        
        # Create README
        readme_file = package_dir / "README.md"
        readme_content = f"""# Box64 for Android ({arch})

This package contains box64 cross-compiled for Android {arch} architecture.

## Installation

1. Copy this package to your Android device
2. Run: `bash install.sh`

## Usage

```bash
# Run x86_64 programs
./box64 /path/to/x86_64/program

# Run Wine with box64
./box64 wine /path/to/windows/program.exe
```

## Notes

- This binary was cross-compiled using Android SDK/NDK toolchain
- Compatible with Android API level 24+
- Requires root access for some operations
- Performance may vary depending on device architecture
"""
        
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        # Create archive
        archive_name = f"box64/android-{arch}.tar.gz"
        archive_path = self.build_dir / archive_name
        
        logger.info(f"Creating archive: {archive_path}")
        success, result = self._run_command(f"tar -czf {archive_path} -C {self.build_dir} box64/android-{arch}")
        if not success:
            logger.error(f"Failed to create archive: {result.stderr if result else 'Unknown error'}")
            return False
        
        logger.info(f"Android package created: {archive_path}")
        return True
    
    def run_tests(self) -> bool:
        """Run box64 tests (if possible on host system)."""
        logger.info("Running tests...")
        
        # Note: Cross-compiled binaries can't be tested on host system
        # This is a placeholder for future testing on Android devices
        logger.info("Cross-compiled binary cannot be tested on host system")
        logger.info("Please test on target Android device")
        return True
    
    def clean(self):
        """Clean build directory."""
        logger.info("Cleaning build directory...")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            logger.info("Build directory cleaned")
    
    def _run_command(self, cmd: str, custom_env : dict = {}) -> Tuple[bool, Optional[subprocess.CompletedProcess]]:
        """Run a shell command and return success status and result."""
        try:
            my_env = os.environ | custom_env
            result = subprocess.run(
                cmd, shell=True, env = my_env
            )
            return result.returncode == 0, result
        except Exception as e:
            logger.error(f"Exception running command '{cmd}': {e}")
            return False, None
    
    def show_architectures(self):
        """Show available Android architectures."""
        print("\nAvailable Android architectures:")
        print("=" * 50)
        
        for arch, config in self.android_archs.items():
            print(f"{arch:<15} - {config['description']}")
        
        print("\nNote: ARM64 (arm64-v8a) is recommended for most modern Android devices.")
    
    def build_box64(self, arch: str = None, custom_args: List[str] = None, 
                   jobs: int = None, install: bool = True, test: bool = False,
                   clean_build: bool = False, clone_source: bool = True,
                   create_package: bool = True):
        """Main build process."""
        logger.info("Starting box64 cross-compilation for Android...")
        
        # Detect Android SDK/NDK
        if not self.detect_android_sdk():
            return False
        
        # Default to ARM64 if no architecture specified
        if not arch:
            arch = 'arm64-v8a'
            logger.info(f"Using default architecture: {arch}")
        
        # Clean build if requested
        if clean_build:
            self.clean()
        
        # Clone source if needed
        if clone_source:
            if not self.clone_box64_source():
                return False
        
        # Set up build environment
        if not self.setup_build_environment():
            return False
        
        # Set up toolchain
        if not self.setup_toolchain(arch):
            return False
        
        # Configure build
        if not self.configure_build(arch, custom_args):
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
        
        # Create Android package
        if create_package:
            if not self.create_android_package(arch):
                return False
        
        logger.info("Box64 cross-compilation completed successfully!")
        logger.info(f"Build directory: {self.build_dir}")
        logger.info(f"Install prefix: {self.install_prefix}")
        return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Box64 Cross-Compilation Script for Android SDK',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Cross-compile for ARM64
  %(prog)s --arch arm64-v8a                  # Cross-compile for ARM64
  %(prog)s --arch armeabi-v7a                # Cross-compile for ARM32
  %(prog)s --android-sdk /path/to/sdk        # Use custom Android SDK
  %(prog)s --cmake-args "-DCMAKE_BUILD_TYPE=Debug"  # Custom CMake arguments
  %(prog)s --jobs 8 --create-package         # Build with 8 jobs and create package
  %(prog)s --clean --arch x86_64             # Clean build for x86_64
  %(prog)s --list-archs                       # Show available architectures
        """
    )
    
    parser.add_argument('--arch', '-a', default='arm64-v8a',
                       help='Target Android architecture (default: arm64-v8a)')
    parser.add_argument('--android-sdk',
                       help='Android SDK path (auto-detect if not specified)')
    parser.add_argument('--android-ndk',
                       help='Android NDK path (auto-detect if not specified)')
    parser.add_argument('--cmake-args', nargs='*', default=[],
                       help='Additional CMake arguments')
    parser.add_argument('--jobs', '-j', type=int, default=None,
                       help='Number of parallel build jobs (default: auto-detect)')
    parser.add_argument('--no-install', action='store_true',
                       help='Build without installing')
    parser.add_argument('--no-package', action='store_true',
                       help='Build without creating Android package')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Run tests after building')
    parser.add_argument('--clean', action='store_true',
                       help='Clean build directory before building')
    parser.add_argument('--list-archs', action='store_true',
                       help='List available Android architectures and exit')
    parser.add_argument('--source-dir',
                       help='Source directory (default: dependencies/box64)')
    parser.add_argument('--build-dir',
                       help='Build directory (default: build/box64/android)')
    parser.add_argument('--install-prefix',
                       default='/tmp/box64/android',
                       help='Installation prefix (default: /tmp/box64/android)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--no-clone', action='store_true',
                       help='Skip cloning source (use existing source)')
    
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create builder instance
    builder = AndroidBox64Builder(args.source_dir, args.build_dir)
    builder.install_prefix = args.install_prefix
    
    # Override SDK/NDK paths if specified
    if args.android_sdk:
        builder.android_sdk = Path(args.android_sdk).resolve()
    if args.android_ndk:
        builder.android_ndk = Path(args.android_ndk).resolve()
    
    # Show architectures if requested
    if args.list_archs:
        builder.show_architectures()
        return 0
    
    # Build box64
    success = builder.build_box64(
        arch=args.arch,
        custom_args=args.cmake_args,
        jobs=args.jobs,
        install=not args.no_install,
        test=args.test,
        clean_build=args.clean,
        clone_source=not args.no_clone,
        create_package=not args.no_package
    )
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
