#!/usr/bin/env python
"""
API Test Runner Script

Run all API endpoint tests or specific test files.

Usage:
    python scripts/run_api_tests.py                    # Run all API tests
    python scripts/run_api_tests.py --auth             # Run auth tests only
    python scripts/run_api_tests.py --narrators        # Run narrators tests only
    python scripts/run_api_tests.py --stats            # Run stats tests only
    python scripts/run_api_tests.py --search           # Run search tests only
    python scripts/run_api_tests.py -v                 # Verbose output
    python scripts/run_api_tests.py --coverage         # With coverage report
"""

import sys
import subprocess
import argparse
from pathlib import Path

TEST_MAP = {
    "auth": "tests/test_auth_api.py",
    "narrators": "tests/test_narrators_api.py",
    "stats": "tests/test_stats_api.py",
    "search": "tests/test_search_api.py",
    "narratives": "tests/test_narratives.py",
    "upload": "tests/test_upload.py",
    "services": "tests/test_*_service.py",
    "integration": "tests/test_pipeline_integration.py",
}


def run_tests(test_files: list, verbose: bool = False, coverage: bool = False):
    """Run pytest with specified test files."""
    cmd = ["pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
    
    cmd.extend(test_files)
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run API endpoint tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/run_api_tests.py                    # Run all API tests
    python scripts/run_api_tests.py --auth             # Run auth tests
    python scripts/run_api_tests.py --all              # Run all tests
    python scripts/run_api_tests.py -v --coverage      # Verbose with coverage
        """
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests including services"
    )
    
    for test_name in TEST_MAP:
        parser.add_argument(
            f"--{test_name}",
            action="store_true",
            help=f"Run {test_name} tests"
        )
    
    args = parser.parse_args()
    
    test_files = []
    
    if args.all:
        test_files = ["tests/"]
    else:
        for test_name, test_path in TEST_MAP.items():
            if getattr(args, test_name, False):
                test_files.append(test_path)
    
    if not test_files:
        test_files = [
            "tests/test_auth_api.py",
            "tests/test_narrators_api.py",
            "tests/test_stats_api.py",
            "tests/test_search_api.py",
            "tests/test_narratives.py",
        ]
    
    returncode = run_tests(test_files, args.verbose, args.coverage)
    sys.exit(returncode)


if __name__ == "__main__":
    main()
