#!/usr/bin/env python3
"""
Test runner script for DSA-110 pipeline.

This script provides a convenient way to run the test suite
with different configurations and options.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests(test_path: str = None, verbose: bool = False, 
              coverage: bool = False, environment: str = "testing") -> int:
    """
    Run the test suite.
    
    Args:
        test_path: Specific test path to run (optional)
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        environment: Test environment to use
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Set up environment variables
        env = os.environ.copy()
        env['DSA110_ENV'] = environment
        
        # Build pytest command
        cmd = ['python', '-m', 'pytest']
        
        if verbose:
            cmd.append('-v')
        
        if coverage:
            cmd.extend(['--cov=core', '--cov-report=html', '--cov-report=term'])
        
        # Add test path
        if test_path:
            cmd.append(test_path)
        else:
            cmd.append('tests/')
        
        # Add additional options
        cmd.extend([
            '--tb=short',
            '--strict-markers',
            '--disable-warnings'
        ])
        
        print(f"Running tests with command: {' '.join(cmd)}")
        print(f"Environment: {environment}")
        
        # Run tests
        result = subprocess.run(cmd, env=env, cwd=project_root)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")
        
        return result.returncode
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description='Run DSA-110 pipeline tests')
    parser.add_argument('--test-path', help='Specific test path to run')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='Enable coverage reporting')
    parser.add_argument('--environment', '-e', default='testing',
                       choices=['testing', 'development', 'production'],
                       help='Test environment to use')
    
    args = parser.parse_args()
    
    exit_code = run_tests(
        test_path=args.test_path,
        verbose=args.verbose,
        coverage=args.coverage,
        environment=args.environment
    )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
