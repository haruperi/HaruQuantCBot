#!/usr/bin/env python3
"""
Automated Developer Environment Setup Script.

This script automates the setup of the HQT development environment:
- Checks Python version requirements
- Installs Python dependencies
- Verifies build tools (CMake, vcpkg)
- Runs test suite
- Generates coverage report
- Provides setup status summary

Usage:
    python scripts/setup_dev.py [--skip-tests] [--skip-deps]
"""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Tuple


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    @classmethod
    def disable(cls):
        """Disable colors for non-terminal output."""
        cls.HEADER = ""
        cls.OKBLUE = ""
        cls.OKCYAN = ""
        cls.OKGREEN = ""
        cls.WARNING = ""
        cls.FAIL = ""
        cls.ENDC = ""
        cls.BOLD = ""
        cls.UNDERLINE = ""


# Disable colors on Windows unless ANSICON or WT_SESSION is set
if platform.system() == "Windows":
    if not (os.environ.get("ANSICON") or os.environ.get("WT_SESSION")):
        Colors.disable()


def print_header(msg: str) -> None:
    """Print a header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_success(msg: str) -> None:
    """Print a success message."""
    print(f"{Colors.OKGREEN}[OK] {msg}{Colors.ENDC}")


def print_error(msg: str) -> None:
    """Print an error message."""
    print(f"{Colors.FAIL}[ERR] {msg}{Colors.ENDC}")


def print_warning(msg: str) -> None:
    """Print a warning message."""
    print(f"{Colors.WARNING}[WARN] {msg}{Colors.ENDC}")


def print_info(msg: str) -> None:
    """Print an info message."""
    print(f"{Colors.OKCYAN}[INFO] {msg}{Colors.ENDC}")


def run_command(cmd: list[str], cwd: Path | None = None, check: bool = True) -> Tuple[int, str, str]:
    """
    Run a command and return exit code, stdout, stderr.

    Args:
        cmd: Command and arguments as list
        cwd: Working directory (default: current directory)
        check: Raise exception on non-zero exit code

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def check_python_version() -> bool:
    """Check if Python version meets requirements (3.11+)."""
    print_info("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} (requirement: 3.11+)")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} (requirement: 3.11+)")
        print_error("Please install Python 3.11 or later")
        return False


def check_cmake() -> bool:
    """Check if CMake is installed."""
    print_info("Checking CMake...")
    returncode, stdout, stderr = run_command(["cmake", "--version"], check=False)
    if returncode == 0:
        version_line = stdout.split("\n")[0]
        print_success(f"CMake found: {version_line}")
        return True
    else:
        print_warning("CMake not found (optional for Python-only development)")
        print_info("Install CMake 3.25+ for C++ development: https://cmake.org/download/")
        return False


def check_vcpkg() -> bool:
    """Check if vcpkg is available."""
    print_info("Checking vcpkg...")
    vcpkg_root = os.environ.get("VCPKG_ROOT")
    if vcpkg_root:
        vcpkg_path = Path(vcpkg_root) / ("vcpkg.exe" if platform.system() == "Windows" else "vcpkg")
        if vcpkg_path.exists():
            print_success(f"vcpkg found at: {vcpkg_root}")
            return True
    print_warning("vcpkg not found (optional for C++ development)")
    print_info("Set VCPKG_ROOT environment variable or install vcpkg: https://vcpkg.io/")
    return False


def install_dependencies(root_dir: Path, skip: bool = False) -> bool:
    """Install Python dependencies."""
    if skip:
        print_info("Skipping dependency installation (--skip-deps)")
        return True

    print_info("Installing Python dependencies...")
    print_info("Running: pip install -e .[dev,test]")

    returncode, stdout, stderr = run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev,test]"],
        cwd=root_dir,
        check=False,
    )

    if returncode == 0:
        print_success("Dependencies installed successfully")
        return True
    else:
        print_error("Failed to install dependencies")
        print(stderr)
        return False


def run_tests(root_dir: Path, skip: bool = False) -> bool:
    """Run the test suite with coverage."""
    if skip:
        print_info("Skipping tests (--skip-tests)")
        return True

    print_info("Running test suite...")
    print_info("Running: pytest tests/ --cov=src/hqt/foundation --cov-report=term --cov-report=html")

    returncode, stdout, stderr = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=src/hqt/foundation",
            "--cov-report=term",
            "--cov-report=html",
            "-v",
        ],
        cwd=root_dir,
        check=False,
    )

    if returncode == 0:
        print_success("All tests passed!")
        # Extract coverage percentage from output
        for line in stdout.split("\n"):
            if "TOTAL" in line and "%" in line:
                print_success(f"Coverage: {line.split()[-1]}")
        print_info(f"HTML coverage report: {root_dir / 'htmlcov' / 'index.html'}")
        return True
    else:
        print_error("Tests failed")
        # Print last 20 lines of output for context
        print("\nTest output (last 20 lines):")
        print("\n".join(stdout.split("\n")[-20:]))
        return False


def verify_project_structure(root_dir: Path) -> bool:
    """Verify expected project structure exists."""
    print_info("Verifying project structure...")

    required_paths = [
        "src/hqt/foundation",
        "tests",
        "config",
        "docs",
        "pyproject.toml",
    ]

    missing = []
    for path in required_paths:
        if not (root_dir / path).exists():
            missing.append(path)

    if missing:
        print_error(f"Missing required paths: {', '.join(missing)}")
        return False
    else:
        print_success("Project structure verified")
        return True


def print_summary(results: dict[str, bool]) -> None:
    """Print setup summary."""
    print_header("Setup Summary")

    total = len(results)
    passed = sum(results.values())

    for check, status in results.items():
        if status:
            print_success(check)
        else:
            print_error(check)

    print(f"\n{Colors.BOLD}Total: {passed}/{total} checks passed{Colors.ENDC}")

    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}[SUCCESS] Development environment ready!{Colors.ENDC}")
        print(f"\n{Colors.OKCYAN}Next steps:{Colors.ENDC}")
        print("  1. Run tests: pytest tests/")
        print("  2. Check coverage: open htmlcov/index.html")
        print("  3. Start developing!")
    else:
        print(f"\n{Colors.WARNING}{Colors.BOLD}[WARNING] Setup incomplete - see errors above{Colors.ENDC}")
        if not results.get("Python Version", False):
            print(f"\n{Colors.FAIL}CRITICAL: Python 3.11+ is required{Colors.ENDC}")
        sys.exit(1)


def main():
    """Main setup routine."""
    parser = argparse.ArgumentParser(description="Setup HQT development environment")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-deps", action="store_true", help="Skip installing dependencies")
    args = parser.parse_args()

    # Get project root directory
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    print_header("HQT Trading System - Developer Setup")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"Project root: {root_dir}")

    results = {}

    # Required checks
    results["Python Version"] = check_python_version()
    results["Project Structure"] = verify_project_structure(root_dir)

    if not results["Python Version"]:
        print_error("Cannot continue without Python 3.11+")
        sys.exit(1)

    # Optional checks (won't fail setup)
    check_cmake()
    check_vcpkg()

    # Install dependencies
    results["Install Dependencies"] = install_dependencies(root_dir, skip=args.skip_deps)

    # Run tests
    results["Run Tests"] = run_tests(root_dir, skip=args.skip_tests)

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
