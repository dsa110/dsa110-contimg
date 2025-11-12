#!/usr/bin/env python3
"""
Wrapper script that monitors output for warnings and stops immediately if detected.

This script:
1. Runs the target script as a subprocess
2. Captures all stdout/stderr output in real-time
3. Monitors for warning patterns (Python logging + CASA output)
4. Kills the process immediately if warnings are detected
5. Writes all output to a log file for review
"""

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Queue, Empty


class WarningMonitor:
    """Monitors subprocess output for warnings and kills process if detected."""

    # Warning patterns to detect (case-insensitive)
    WARNING_PATTERNS = [
        # Logging levels
        "warning",
        "WARNING",
        "warn",
        "WARN",
        "error",
        "ERROR",
        "SEVERE",  # CASA severity level
        "FATAL",
        "fatal",
        # Fallback/compromise patterns
        "fallback",
        "falling back",
        "using default",
        "defaulting to",
        # Failure patterns
        "failed",
        "failure",
        "cannot",
        "can't",
        "unable to",
        "abort",
        "aborting",
        # Exception patterns
        "exception",
        "Exception",
        "traceback",
        "Traceback",
        "RuntimeError",
        "ValueError",
        "KeyError",
        "FileNotFoundError",
        "PermissionError",
        # File system issues
        "permission denied",
        "no such file",
        "no space left",
        "disk full",
        "read-only",
        # Database issues
        "database is locked",
        "sqlite error",
        "connection failed",
        # Calibration-specific
        "calibration failed",
        "no valid data",
        "insufficient data",
        "calibrator not found",
        "no calibrator",
        # CASA task failures
        "task failed",
        "Task failed",
        "cannot proceed",
        # Resource issues
        "MemoryError",
        "out of memory",
        "timeout",
        "Timeout",
        # Configuration issues
        "missing required",
        "invalid configuration",
        "not configured",
        "not found",
    ]

    # Patterns that are OK (not actual warnings)
    IGNORE_PATTERNS = [
        "debug",  # DEBUG level is fine
        "info",  # INFO level is fine
        "completed",  # "completed successfully" is fine
        "success",  # Success messages are fine
    ]

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.warning_detected = False
        self.warning_line = None
        self.output_queue = Queue()
        self.log_handle = open(log_file, "w")

    def _is_warning(self, line: str) -> bool:
        """Check if a line contains a warning pattern."""
        line_lower = line.lower()

        # Check ignore patterns first
        for ignore in self.IGNORE_PATTERNS:
            if ignore in line_lower:
                return False

        # Check warning patterns
        for pattern in self.WARNING_PATTERNS:
            if pattern in line_lower:
                # Additional context check for "error" - only if it's not "no error"
                if pattern == "error":
                    if "no error" in line_lower or "without error" in line_lower:
                        continue
                return True

        return False

    def _read_stream(self, stream, prefix: str):
        """Read from a stream and queue lines for processing."""
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break
                line = line.rstrip("\n\r")
                self.output_queue.put((prefix, line))
        except Exception as e:
            self.output_queue.put(("ERROR", f"Stream read error: {e}"))
        finally:
            stream.close()

    def monitor_process(self, process: subprocess.Popen) -> int:
        """Monitor process output and kill if warnings detected.

        Returns:
            Exit code of the process (or 1 if killed due to warning)
        """
        # Start threads to read stdout and stderr
        stdout_thread = threading.Thread(
            target=self._read_stream, args=(process.stdout, "STDOUT"), daemon=True
        )
        stderr_thread = threading.Thread(
            target=self._read_stream, args=(process.stderr, "STDERR"), daemon=True
        )

        stdout_thread.start()
        stderr_thread.start()

        # Process output lines
        while process.poll() is None:
            try:
                prefix, line = self.output_queue.get(timeout=0.1)

                # Write to log file
                self.log_handle.write(f"[{prefix}] {line}\n")
                self.log_handle.flush()

                # Also print to console
                print(f"[{prefix}] {line}")

                # Check for warnings
                if self._is_warning(line):
                    self.warning_detected = True
                    self.warning_line = line
                    print(f"\n{'='*80}")
                    print(f"WARNING DETECTED: {line}")
                    print(f"{'='*80}\n")
                    break

            except Empty:
                continue

        # If warning detected, kill the process
        if self.warning_detected:
            print("Killing process due to warning detection...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            self.log_handle.close()
            return 1

        # Process remaining output
        while True:
            try:
                prefix, line = self.output_queue.get(timeout=0.1)
                self.log_handle.write(f"[{prefix}] {line}\n")
                self.log_handle.flush()
                print(f"[{prefix}] {line}")
            except Empty:
                break

        # Wait for threads to finish
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

        self.log_handle.close()
        return process.returncode if process.returncode is not None else 0


def main():
    parser = argparse.ArgumentParser(description="Run a script with warning monitoring")
    parser.add_argument(
        "script",
        help="Script to run (e.g., run_first_mosaic.py)",
    )
    parser.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="Arguments to pass to the script",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("run_with_monitor.log"),
        help="Log file to write output to",
    )
    parser.add_argument(
        "--python",
        default="/opt/miniforge/envs/casa6/bin/python3",
        help="Python interpreter to use",
    )

    args = parser.parse_args()

    # Build command
    script_path = Path(args.script)
    if not script_path.is_absolute():
        # Assume it's in the same directory
        script_path = Path(__file__).parent / script_path

    cmd = [args.python, str(script_path)] + args.script_args

    print(f"Running: {' '.join(cmd)}")
    print(f"Log file: {args.log_file}")
    print(f"{'='*80}\n")

    # Start process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        cwd=Path(__file__).parent.parent.parent.parent,
    )

    # Monitor output
    monitor = WarningMonitor(args.log_file)
    exit_code = monitor.monitor_process(process)

    if monitor.warning_detected:
        print(f"\n{'='*80}")
        print("PROCESS STOPPED DUE TO WARNING DETECTION")
        print(f"Warning line: {monitor.warning_line}")
        print(f"Full log: {args.log_file}")
        print(f"{'='*80}\n")
        return 1

    print(f"\n{'='*80}")
    print("PROCESS COMPLETED SUCCESSFULLY")
    print(f"Exit code: {exit_code}")
    print(f"Full log: {args.log_file}")
    print(f"{'='*80}\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
