#!/usr/bin/env python3
"""
Run tests for a specific YAML test file.

This script allows running tests for a specific YAML test file instead of running all tests.
It's particularly useful for validating a single test case after making changes.
"""

import argparse
import os
import sys
import pytest
from pathlib import Path

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

# Define the repo root for easier path resolution
REPO_ROOT = Path(__file__).parents[3].absolute()


def ensure_test_file_exists(file_path: str) -> bool:
    """
    Ensure the test file exists.

    Args:
        file_path: Path to the test file

    Returns:
        True if the file exists, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"Error: Test file does not exist: {file_path}")
        return False

    return True


def run_tests_for_file(yaml_file_path: str, verbose: bool = False,
                      no_capture: bool = False) -> int:
    """
    Run tests for a specific YAML file using the obd_yaml_testrunner.

    Args:
        yaml_file_path: Path to the YAML test file
        verbose: Whether to run in verbose mode
        no_capture: Whether to disable output capture

    Returns:
        The exit code (0 for success, non-zero for failure)
    """
    # Make sure the file path is absolute
    yaml_file_path = os.path.abspath(yaml_file_path)

    # Import test modules from schemas
    from signals_testing import obd_yaml_testrunner

    print(f"Running tests for: {yaml_file_path}")
    obd_yaml_testrunner(yaml_file_path)
    print("Tests passed successfully!")
    return 0


def main():
    parser = argparse.ArgumentParser(description='Run tests for a specific YAML test file')
    parser.add_argument('yaml_file', help='Path to the YAML test file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--no-capture', '-s', action='store_true',
                        help='Disable output capture (show print statements)')

    args = parser.parse_args()

    # Resolve the file path against the repo root if it's not absolute
    yaml_file_path = args.yaml_file
    if not os.path.isabs(yaml_file_path):
        yaml_file_path = os.path.join(REPO_ROOT, yaml_file_path)

    # Ensure the file exists
    if not ensure_test_file_exists(yaml_file_path):
        sys.exit(1)

    # Run the tests for the file
    exit_code = run_tests_for_file(
        yaml_file_path,
        verbose=args.verbose,
        no_capture=args.no_capture
    )

    sys.exit(exit_code)


if __name__ == '__main__':
    main()