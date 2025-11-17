#!/opt/miniforge/envs/casa6/bin/python
"""
Error Detection Wrapper (pexpect or subprocess backend)
Runs any command and kills execution immediately if errors are detected in output

Usage:
    ./scripts/run-with-error-detection.py <command> [args...]
    ./scripts/run-with-error-detection.py pytest tests/ -v
    ./scripts/run-with-error-detection.py python script.py

Features:
    - Real-time error detection (detects errors as they occur)
    - Immediate termination on error detection
    - Detects common error patterns in output
    - Checks exit codes
    - Preserves full output (unbuffered, logged)
    - Context-aware error detection (avoids false positives)
    - Structured pytest parsing (supports --junitxml)
    - Works with or without pexpect (falls back to subprocess)

Backends:
    - pexpect (preferred): Better for interactive commands, handles TTY/PTY
    - subprocess (fallback): Standard library only, works for non-interactive commands
"""

import os
import re
import signal
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# Try to import pexpect, but don't fail if it's not available
# We'll fall back to subprocess if pexpect is unavailable
try:
    import pexpect

    PEXPECT_AVAILABLE = True
except ImportError:
    PEXPECT_AVAILABLE = False
    import subprocess

# Colors for output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color


def error(msg: str) -> None:
    """Print error message."""
    print(f"{RED}[ERROR-DETECTION]{NC} {msg}", file=sys.stderr)


def warning(msg: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}[WARNING]{NC} {msg}", file=sys.stderr)


def info(msg: str) -> None:
    """Print info message."""
    print(f"{BLUE}[INFO]{NC} {msg}")


def success(msg: str) -> None:
    """Print success message."""
    print(f"{GREEN}[SUCCESS]{NC} {msg}")


# Comprehensive error patterns
ERROR_PATTERNS = [
    # General error pattern (catches any occurrence of "error" word)
    # This is the primary pattern - catches most errors
    r"\b(error|ERROR|Error)\b",
    # Specific patterns for errors that don't contain the word "error"
    r"Traceback",
    r"Exception:",
    r"^FAILED",  # FAILED at start of line
    r"\bFAILED\b",  # FAILED as standalone word
    r"^FAILURE",  # FAILURE at start of line
    r"\bFAILURE\b",  # FAILURE as standalone word
    r"^failure",  # failure at start of line
    r"\bfailure\b",  # failure as standalone word (but not in test names)
    r"Fatal",
    r"fatal",
    r"CRITICAL",
    r"CRITICAL:",
    r"FATAL:",
    r"SEVERE",
    r"Aborted",
    r"aborted",
    r"Killed",
    r"killed",
    # Python exception types (many contain "Error" but some don't)
    r"SyntaxError",
    r"TypeError",
    r"ValueError",
    r"AttributeError",
    r"ImportError",
    r"ModuleNotFoundError",
    r"FileNotFoundError",
    r"PermissionError",
    r"OSError",
    r"RuntimeError",
    r"KeyError",
    r"IndexError",
    r"NameError",
    r"UnboundLocalError",
    r"AssertionError",
    r"IndentationError",
    r"ZeroDivisionError",
    r"OverflowError",
    r"MemoryError",
    r"RecursionError",
    r"KeyboardInterrupt",
    r"SystemExit",
    r"BrokenPipeError",
    r"ProcessLookupError",
    r"InterruptedError",
    r"NotImplementedError",
    r"StopIteration",
    r"GeneratorExit",
    r"ReferenceError",
    r"SystemError",
    r"UnicodeError",
    r"UnicodeDecodeError",
    r"UnicodeEncodeError",
    r"UnicodeTranslateError",
    r"sqlite3\.OperationalError",
    r"sqlite3\.IntegrityError",
    r"sqlite3\.DatabaseError",
    r"sqlite3\.ProgrammingError",
    r"sqlite3\.InterfaceError",
    r"sqlite3\.InternalError",
    r"sqlite3\.NotSupportedError",
    # Test failures (more specific patterns to avoid false positives)
    r"\d+.*tests? failed",  # X tests failed (with number)
    r"tests? failed\b",  # tests failed (as phrase, not in test names)
    r"assert.*failed\b",  # assert ... failed (as word)
    # Note: "test.*failed" pattern removed to avoid false positives in test names
    # Actual test failures are caught by "tests failed" or exit codes
    # Shell/system errors
    r"command not found",
    r"Permission denied",
    r"No such file or directory",
    r"^Cannot",
    r"^can't",
    r"^Unable to",
    r"^unable to",
    r"^Failed to",
    r"^failed to",
    r"Error occurred",
    r"error occurred",
    # CASA errors
    r"SEVERE",
    r"Exception Reported",
    r"Table.*does not exist",
    r"invalid table",
    # Database errors
    r"OperationalError",
    r"IntegrityError",
    r"DatabaseError",
    r"ProgrammingError",
    r"InterfaceError",
    r"InternalError",
    r"NotSupportedError",
    r"table.*has no column",
    r"no such table",
    r"database.*locked",
    r"database.*corrupt",
    r"database.*error",
    r"database.*failed",
    r"SQL.*error",
    r"SQL.*failed",
    r"query.*failed",
    r"query.*error",
    # Build/compilation errors
    r"Build failed",
    r"Compilation error",
    r"Compilation failed",
    r"build error",
    r"compilation error",
    # Network/API errors
    r"ConnectionError",
    r"TimeoutError",
    r"HTTPError",
    r"URLError",
    r"Connection refused",
    r"Connection timeout",
    r"Network error",
    r"network.*error",
    r"connection.*failed",
    r"connection.*error",
    r"timeout.*error",
    r"timeout.*failed",
    r"DNS.*error",
    r"DNS.*failed",
    r"SSL.*error",
    r"TLS.*error",
    r"certificate.*error",
    r"certificate.*failed",
    # System-level errors
    r"Segmentation fault",
    r"segfault",
    r"core dumped",
    r"Abort trap",
    r"Bus error",
    r"bus error",
    r"Floating point exception",
    r"floating point exception",
    r"Illegal instruction",
    r"illegal instruction",
    r"Stack overflow",
    r"stack overflow",
    r"Out of memory",
    r"out of memory",
    r"Memory allocation failed",
    r"memory allocation failed",
    # pytest specific errors
    r"pytest\.UsageError",
    r"pytest\.Failed",
    r"pytest.*failed",
    r"pytest.*error",
    r"INTERNALERROR",
    r"INTERNAL ERROR",
    r"UsageError",
    r"usage error",
    # Exit codes that indicate failure
    r"exit code.*[1-9]",
    r"exit.*[1-9]",
    r"return code.*[1-9]",
    r"return.*[1-9]",
]

# Warning patterns that should also trigger termination
# Strategy: Use general "warning" pattern + specific warning types
WARNING_PATTERNS = [
    # General warning pattern (catches any occurrence of "warning" word)
    # This is the primary pattern - catches most warnings
    r"\b(warning|WARNING|Warning)\b",
    # Specific warning types that might not contain "warning" explicitly
    r"DeprecationWarning",
    r"PendingDeprecationWarning",
    r"FutureWarning",
    # Test warnings that indicate problems
    r"^WARNING.*test.*skipped",  # Tests being skipped unexpectedly
    r"^WARNING.*test.*failed",  # Test failures in warnings
    r"^WARNING.*assertion",  # Assertion warnings
    # Database warnings
    r"^WARNING.*database",  # Database-related warnings
    r"^WARNING.*table",  # Table-related warnings
    r"^WARNING.*column",  # Column-related warnings
    r"^WARNING.*schema",  # Schema-related warnings
    # CASA warnings
    r"^WARNING.*SEVERE",  # Severe warnings from CASA
    r"^WARNING.*Exception",  # Exception warnings
    # Build/compilation warnings
    r"^WARNING.*build",  # Build warnings
    r"^WARNING.*compilation",  # Compilation warnings
    r"^WARNING.*compile",  # Compile warnings
    # System warnings
    r"^WARNING.*Permission",  # Permission warnings
    r"^WARNING.*Access",  # Access warnings
    r"^WARNING.*denied",  # Denied warnings
    # General critical warnings
    r"^WARNING.*CRITICAL",  # Critical warnings
    r"^WARNING.*FATAL",  # Fatal warnings
    r"^WARNING.*Error",  # Error warnings
    r"^WARNING.*Failed",  # Failed warnings
    r"^WARNING.*Failure",  # Failure warnings
    # Data quality warnings
    r"^WARNING.*invalid",  # Invalid data warnings
    r"^WARNING.*corrupt",  # Corrupt data warnings
    r"^WARNING.*missing",  # Missing data warnings
    r"^WARNING.*not found",  # Not found warnings
    # Configuration warnings
    r"^WARNING.*config",  # Configuration warnings
    r"^WARNING.*setting",  # Setting warnings
    r"^WARNING.*parameter",  # Parameter warnings
]

# Patterns to exclude (false positives)
EXCLUDE_PATTERNS = [
    r"No errors",
    r"no errors",
    r"Error handling",
    r"error handling",
    r"Error recovery",
    r"error recovery",
    r"Error detection",  # Our own error detection messages
    r"ERROR-DETECTION",  # Our own error detection prefix
    r"error detection",  # Our own error detection messages
    r"def.*error",  # Function definitions containing "error"
    r"class.*error",  # Class definitions containing "error"
    r"function.*error",  # Function definitions containing "error"
    r"handle.*error",  # Error handling code
    r"catch.*error",  # Error catching code
    r"log.*error",  # Error logging code
    r"print.*error",  # Error printing code
    r"ERROR-DETECTION",  # Our own script messages
    r"Error patterns",  # Documentation
    r"error patterns",  # Documentation
    r"Error: 0",  # Zero errors
    r"errors: 0",  # Zero errors
    r"0 failed",  # Zero failures
    r"0 errors",  # Zero errors
    r"passed.*failed.*0",  # All passed, 0 failed
    r"#.*Error",  # Comments containing Error
    r"#.*error",  # Comments containing error
    r"def.*error",  # Function definitions
    r"class.*Error",  # Class definitions
    r"test.*error",  # Test names containing error
    r"test.*Error",  # Test names containing Error
    # Bash shell warnings (not actual errors)
    r"/bin/bash:.*warning.*shell level",  # Bash shell level warning
    r"shell level.*too high",  # Shell level too high
    r"resetting to 1",  # Shell reset message
]

# Commands that may legitimately exit with non-zero codes
EXPECTED_NONZERO_COMMANDS = [
    "grep",
    "diff",
    "test",
    "[",
]


def is_expected_nonzero(command: str) -> bool:
    """Check if command is expected to exit non-zero."""
    first_word = command.split()[0] if command.split() else ""
    return any(cmd in first_word or cmd in command for cmd in EXPECTED_NONZERO_COMMANDS)


def is_false_positive_line(line: str, pattern: str) -> bool:
    """Check if error pattern is in a false positive context. Robust against edge cases."""
    # Normalize line for processing
    line = line.strip()
    if not line:
        return True  # Empty lines are not errors

    # Check if line contains exclude patterns (highest priority)
    for exclude in EXCLUDE_PATTERNS:
        if re.search(exclude, line, re.IGNORECASE):
            return True

    # Check if error pattern appears in comment context
    # Handle both # and // style comments
    line_no_comment = re.sub(r"#.*$", "", line)  # Python/bash comments
    line_no_comment = re.sub(r"//.*$", "", line_no_comment)  # C/C++ comments
    # C-style block comments
    line_no_comment = re.sub(r"/\*.*?\*/", "", line_no_comment, flags=re.DOTALL)

    # If pattern only in comment portion, it's a false positive
    if re.search(pattern, line, re.IGNORECASE | re.MULTILINE) and not re.search(
        pattern, line_no_comment, re.IGNORECASE | re.MULTILINE
    ):
        return True

    # If pattern exists outside comment, check if it's in a safe context
    if re.search(pattern, line_no_comment, re.IGNORECASE | re.MULTILINE):
        # Check for function/class definitions that might contain error words
        if re.search(r"(def|class|function|import|from)\s+.*" + pattern, line, re.IGNORECASE):
            return True
        # Check for variable assignments or declarations
        if re.search(
            r"^\s*(var|let|const|int|str|bool|float|list|dict|set)\s+.*" + pattern,
            line,
            re.IGNORECASE,
        ):
            return True
        # Check for string literals that might contain error words
        if re.search(r'["\'].*' + pattern + r'.*["\']', line, re.IGNORECASE):
            # If it's in quotes and looks like a string literal, might be false positive
            # But if it's clearly an error message, it's not a false positive
            # We'll be conservative and only exclude if it's clearly a definition
            pass
        # Pattern exists in actual code/output - not a false positive
        return False

    return False


def detect_error_in_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Detect error pattern in a single line. Returns (pattern, line) if error found.
    Robust against multi-line errors, partial lines, and encoding issues.
    """
    if not line or not line.strip():
        return None

    # Normalize line - handle encoding issues
    try:
        # Ensure line is a string and handle any encoding issues
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        line = str(line)
    except Exception:
        # If we can't decode, try to process as-is
        pass

    # Split multi-line strings into individual lines for processing
    # This ensures we catch errors that span multiple lines
    lines_to_check = line.split("\n")

    for single_line in lines_to_check:
        single_line = single_line.strip()
        if not single_line:
            continue

        # Use MULTILINE flag so ^ matches start of each line, not just start of string
        # This is important because pexpect can accumulate multiple lines
        for pattern in ERROR_PATTERNS:
            try:
                if re.search(pattern, single_line, re.IGNORECASE | re.MULTILINE):
                    if not is_false_positive_line(single_line, pattern):
                        return (pattern, single_line)
            except re.error:
                # Invalid regex pattern - skip it
                continue
            except Exception:
                # Any other error - continue checking other patterns
                continue

    return None


def detect_warning_in_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Detect warning pattern in a single line. Returns (pattern, line) if warning found.
    Robust against multi-line warnings, partial lines, and encoding issues.
    """
    if not line or not line.strip():
        return None

    # Normalize line - handle encoding issues
    try:
        # Ensure line is a string and handle any encoding issues
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        line = str(line)
    except Exception:
        # If we can't decode, try to process as-is
        pass

    # Split multi-line strings into individual lines for processing
    # This ensures we catch warnings that span multiple lines
    lines_to_check = line.split("\n")

    for single_line in lines_to_check:
        single_line = single_line.strip()
        if not single_line:
            continue

        # Use MULTILINE flag so ^ matches start of each line, not just start of string
        # This is important because pexpect can accumulate multiple lines
        for pattern in WARNING_PATTERNS:
            try:
                if re.search(pattern, single_line, re.IGNORECASE | re.MULTILINE):
                    if not is_false_positive_line(single_line, pattern):
                        return (pattern, single_line)
            except re.error:
                # Invalid regex pattern - skip it
                continue
            except Exception:
                # Any other error - continue checking other patterns
                continue

    return None


def parse_pytest_junitxml(junit_file: str) -> Tuple[int, int]:
    """Parse pytest JUnit XML file. Returns (failures, errors)."""
    if not os.path.exists(junit_file):
        return (0, 0)

    try:
        with open(junit_file, "r") as f:
            content = f.read()

        # Extract failures and errors from JUnit XML
        failures_match = re.search(r'failures="(\d+)"', content)
        errors_match = re.search(r'errors="(\d+)"', content)

        failures = int(failures_match.group(1)) if failures_match else 0
        errors = int(errors_match.group(1)) if errors_match else 0

        return (failures, errors)
    except Exception as e:
        warning(f"Failed to parse JUnit XML: {e}")
        return (0, 0)


def check_test_results(output: str, exit_code: int, command: str) -> Tuple[bool, Optional[str]]:
    """Check test results. Returns (is_success, error_message)."""
    # Check for pytest-style test results
    if not re.search(r"pytest|test.*passed|test.*failed", output, re.IGNORECASE):
        return (True, None)

    # Try to find JUnit XML file
    junit_file = None
    if "--junitxml" in command:
        # Extract path from command - handle both --junitxml=path and --junitxml path formats
        match = re.search(r"--junitxml=([^\s]+)", command)
        if match:
            junit_file = match.group(1)
        else:
            match = re.search(r"--junitxml\s+([^\s]+)", command)
            if match:
                junit_file = match.group(1)
    else:
        # Check common locations
        for loc in ["junit.xml", "test-results.xml", "pytest.xml"]:
            if os.path.exists(loc):
                junit_file = loc
                break

    # Use JUnit XML if available (more reliable)
    if junit_file and os.path.exists(junit_file):
        failures, errors = parse_pytest_junitxml(junit_file)
        if failures > 0 or errors > 0:
            return (False, f"JUnit XML reports: {failures} failures, {errors} errors")
    else:
        # Fall back to text parsing
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        errors_match = re.search(r"(\d+)\s+error", output)

        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        errors = int(errors_match.group(1)) if errors_match else 0

        # Also check for "FAILED" in test names (but exclude false positives)
        failed_tests = len(
            [
                l
                for l in output.split("\n")
                if re.search(r"FAILED|failed", l)
                and not re.search(r"#.*FAILED|test.*failed|def.*failed", l)
            ]
        )

        if failed > 0 or errors > 0 or failed_tests > 0:
            return (False, f"Test failures detected: {failed} failed, {errors} errors")

        # Check for "no tests collected" or similar
        if re.search(r"no tests collected|no tests found", output, re.IGNORECASE):
            if exit_code != 0:
                return (False, f"No tests found and exit code is {exit_code}")

        # If no tests passed and exit code is non-zero, that's suspicious
        if passed == 0 and exit_code != 0 and failed == 0 and errors == 0:
            warning(f"No tests executed and exit code is {exit_code} (might be setup error)")

    return (True, None)


def _run_with_pexpect(command: str, log_fd, error_lines: List[str], output_lines: List[str]) -> int:
    """Run command with pexpect backend. Returns exit code."""
    errors_detected = False
    exit_code = 0

    # Spawn process with pexpect
    # Use bash -c to handle complex commands properly
    child = pexpect.spawn("/bin/bash", ["-c", command], encoding="utf-8", timeout=None)

    # Set logfile to None so we can process output ourselves
    child.logfile_read = None

    # Monitor output in real-time
    # Use expect with timeout to avoid blocking indefinitely
    buffer = ""
    while True:
        try:
            # Check if process is still alive first
            if not child.isalive():
                # Process finished, process remaining buffer
                if buffer.strip():
                    print(buffer)
                    log_fd.write(buffer + "\n")
                    log_fd.flush()
                    output_lines.append(buffer)
                    error_result = detect_error_in_line(buffer)
                    if error_result:
                        pattern, error_line = error_result
                        error_lines.append(f"Line: {error_line}")
                        errors_detected = True

                    warning_result = detect_warning_in_line(buffer)
                    if warning_result:
                        pattern, warning_line = warning_result
                        error_lines.append(f"Warning Line: {warning_line}")
                        errors_detected = True
                break

            # Use expect with short timeout to read available output
            # This prevents blocking indefinitely
            try:
                # Try to read a line (or timeout quickly)
                index = child.expect([pexpect.EOF, pexpect.TIMEOUT, r".+"], timeout=0.1)

                if index == 0:  # EOF - process finished
                    # Read remaining output
                    remaining = child.before
                    if remaining:
                        for line in remaining.split("\n"):
                            if line.strip():
                                print(line)
                                log_fd.write(line + "\n")
                                log_fd.flush()
                                output_lines.append(line)

                                # Check for errors
                                error_result = detect_error_in_line(line)
                                if error_result:
                                    pattern, error_line = error_result
                                    error_lines.append(f"Line: {error_line}")
                                    errors_detected = True

                                # Check for warnings
                                warning_result = detect_warning_in_line(line)
                                if warning_result:
                                    pattern, warning_line = warning_result
                                    error_lines.append(f"Warning Line: {warning_line}")
                                    errors_detected = True
                    break

                elif index == 1:  # TIMEOUT - no data available
                    # Check if process is still alive
                    if not child.isalive():
                        break
                    continue

                else:  # Got some output
                    line = child.before + child.match.group(0) if child.match else child.before
                    if line.strip():
                        print(line.rstrip("\n\r"))
                        log_fd.write(line)
                        log_fd.flush()
                        output_lines.append(line.rstrip("\n\r"))

                        # Real-time error detection
                        error_result = detect_error_in_line(line)
                        if error_result:
                            pattern, error_line = error_result
                            error_lines.append(f"Line: {error_line}")
                            error(f"Error pattern '{pattern}' detected in real-time!")
                            error("Terminating command immediately...")
                            errors_detected = True

                            # Kill immediately - aggressive multi-method approach
                            try:
                                # Method 1: Try graceful termination first
                                child.terminate(force=True)
                                time.sleep(0.05)  # Very short wait

                                # Method 2: If still alive, send SIGKILL
                                if child.isalive():
                                    child.kill(signal.SIGKILL)
                                    time.sleep(0.05)

                                # Method 3: If still alive, kill process group
                                if child.isalive():
                                    try:
                                        pgid = os.getpgid(child.pid)
                                        os.killpg(pgid, signal.SIGKILL)
                                    except (OSError, ProcessLookupError):
                                        pass

                                # Method 4: Last resort - kill by PID directly
                                if child.isalive():
                                    try:
                                        os.kill(child.pid, signal.SIGKILL)
                                    except (OSError, ProcessLookupError):
                                        pass
                            except Exception as e:
                                # If all else fails, try to kill process group
                                try:
                                    if child.pid:
                                        os.killpg(os.getpgid(child.pid), signal.SIGKILL)
                                except Exception:
                                    pass

                            # Break out of monitoring loop immediately
                            break

                        # Real-time warning detection (also terminates)
                        # Only check warnings if no error was detected (errors take priority)
                        if not error_result:
                            warning_result = detect_warning_in_line(line)
                            if warning_result:
                                pattern, warning_line = warning_result
                                error_lines.append(f"Warning Line: {warning_line}")
                                error(f"Warning pattern '{pattern}' detected in real-time!")
                                error("Terminating command immediately due to warning...")
                                errors_detected = True

                                # Kill immediately - same aggressive approach as errors
                                try:
                                    # Method 1: Try graceful termination first
                                    child.terminate(force=True)
                                    time.sleep(0.05)  # Very short wait

                                    # Method 2: If still alive, send SIGKILL
                                    if child.isalive():
                                        child.kill(signal.SIGKILL)
                                        time.sleep(0.05)

                                    # Method 3: If still alive, kill process group
                                    if child.isalive():
                                        try:
                                            pgid = os.getpgid(child.pid)
                                            os.killpg(pgid, signal.SIGKILL)
                                        except (OSError, ProcessLookupError):
                                            pass

                                    # Method 4: Last resort - kill by PID directly
                                    if child.isalive():
                                        try:
                                            os.kill(child.pid, signal.SIGKILL)
                                        except (OSError, ProcessLookupError):
                                            pass
                                except Exception as e:
                                    # If all else fails, try to kill process group
                                    try:
                                        if child.pid:
                                            os.killpg(os.getpgid(child.pid), signal.SIGKILL)
                                    except Exception:
                                        pass

                                # Break out of monitoring loop immediately
                                break

            except pexpect.exceptions.EOF:
                # Process finished
                remaining = child.before
                if remaining:
                    for line in remaining.split("\n"):
                        if line.strip():
                            print(line)
                            log_fd.write(line + "\n")
                            log_fd.flush()
                            output_lines.append(line)
                            error_result = detect_error_in_line(line)
                            if error_result:
                                pattern, error_line = error_result
                                error_lines.append(f"Line: {error_line}")
                                errors_detected = True

                            warning_result = detect_warning_in_line(line)
                            if warning_result:
                                pattern, warning_line = warning_result
                                error_lines.append(f"Warning Line: {warning_line}")
                                errors_detected = True
                break

        except KeyboardInterrupt:
            warning("Interrupted by user")
            # Kill immediately on user interrupt
            try:
                child.terminate(force=True)
                time.sleep(0.1)
                if child.isalive():
                    child.kill(signal.SIGKILL)
            except Exception:
                pass
            return 130

    # Wait for process to finish and get exit code
    # If we detected errors and killed the process, don't wait
    if not errors_detected:
        if child.isalive():
            child.wait()
        exit_code = (
            child.exitstatus
            if child.exitstatus is not None
            else (child.signalstatus if child.signalstatus else 0)
        )
    else:
        # Process was killed due to error detection
        exit_code = 1
        # Ensure process is really dead
        try:
            if child.isalive():
                child.kill(signal.SIGKILL)
        except Exception:
            pass

    return exit_code


def _run_with_subprocess(
    command: str, log_fd, error_lines: List[str], output_lines: List[str]
) -> int:
    """Run command with subprocess backend. Returns exit code."""
    import subprocess

    errors_detected = False
    exit_code = 0

    try:
        # Spawn process with subprocess
        # Use bash -c to handle complex commands properly
        # Create new process group for better signal handling
        proc = subprocess.Popen(
            ["/bin/bash", "-c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,  # Line buffered
            preexec_fn=os.setsid,  # Create new process group
        )

        # Monitor output in real-time
        while True:
            # Check if process is still alive
            if proc.poll() is not None:
                # Process finished, read remaining output
                remaining = proc.stdout.read()
                if remaining:
                    for line in remaining.split("\n"):
                        if line.strip():
                            print(line)
                            log_fd.write(line + "\n")
                            log_fd.flush()
                            output_lines.append(line)

                            # Check for errors
                            error_result = detect_error_in_line(line)
                            if error_result:
                                pattern, error_line = error_result
                                error_lines.append(f"Line: {error_line}")
                                errors_detected = True

                            # Check for warnings
                            warning_result = detect_warning_in_line(line)
                            if warning_result:
                                pattern, warning_line = warning_result
                                error_lines.append(f"Warning Line: {warning_line}")
                                errors_detected = True
                break

            # Read available output (non-blocking)
            line = proc.stdout.readline()
            if not line:
                # No more output available, check if process is still running
                if proc.poll() is not None:
                    break
                time.sleep(0.01)  # Small delay to avoid busy waiting
                continue

            # Process the line
            if line.strip():
                print(line.rstrip("\n\r"))
                log_fd.write(line)
                log_fd.flush()
                output_lines.append(line.rstrip("\n\r"))

                # Real-time error detection
                error_result = detect_error_in_line(line)
                if error_result:
                    pattern, error_line = error_result
                    error_lines.append(f"Line: {error_line}")
                    error(f"Error pattern '{pattern}' detected in real-time!")
                    error("Terminating command immediately...")
                    errors_detected = True

                    # Kill immediately - aggressive multi-method approach
                    try:
                        # Method 1: Try graceful termination first
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        time.sleep(0.05)

                        # Method 2: If still alive, send SIGKILL
                        if proc.poll() is None:
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                            time.sleep(0.05)

                        # Method 3: Last resort - kill by PID directly
                        if proc.poll() is None:
                            try:
                                os.kill(proc.pid, signal.SIGKILL)
                            except (OSError, ProcessLookupError):
                                pass
                    except Exception as e:
                        # If all else fails, try to kill process group
                        try:
                            if proc.pid:
                                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        except Exception:
                            pass

                    # Break out of monitoring loop immediately
                    break

                # Real-time warning detection (also terminates)
                # Only check warnings if no error was detected (errors take priority)
                if not error_result:
                    warning_result = detect_warning_in_line(line)
                    if warning_result:
                        pattern, warning_line = warning_result
                        error_lines.append(f"Warning Line: {warning_line}")
                        error(f"Warning pattern '{pattern}' detected in real-time!")
                        error("Terminating command immediately due to warning...")
                        errors_detected = True

                        # Kill immediately - same aggressive approach as errors
                        try:
                            # Method 1: Try graceful termination first
                            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                            time.sleep(0.05)

                            # Method 2: If still alive, send SIGKILL
                            if proc.poll() is None:
                                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                                time.sleep(0.05)

                            # Method 3: Last resort - kill by PID directly
                            if proc.poll() is None:
                                try:
                                    os.kill(proc.pid, signal.SIGKILL)
                                except (OSError, ProcessLookupError):
                                    pass
                        except Exception as e:
                            # If all else fails, try to kill process group
                            try:
                                if proc.pid:
                                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                            except Exception:
                                pass

                        # Break out of monitoring loop immediately
                        break

        # Wait for process to finish and get exit code
        if not errors_detected:
            proc.wait()
            exit_code = proc.returncode if proc.returncode is not None else 0
        else:
            # Process was killed due to error detection
            exit_code = 1
            # Ensure process is really dead
            try:
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass

        return exit_code

    except KeyboardInterrupt:
        warning("Interrupted by user")
        # Kill immediately on user interrupt
        try:
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(0.1)
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        return 130

    except Exception as e:
        error(f"subprocess error: {e}")
        error_lines.append(f"subprocess error: {e}")
        return 1


def main():
    """Main execution function."""
    # GUARD: Prevent recursion - if we're already in error detection, skip wrapping
    if os.environ.get("_IN_ERROR_DETECTION") == "1":
        # We're already in error detection, just run the command directly
        import subprocess

        sys.exit(subprocess.call(sys.argv[1:]))

    # Set guard to prevent recursion
    os.environ["_IN_ERROR_DETECTION"] = "1"

    if len(sys.argv) < 2:
        error("No command provided")
        print(f"Usage: {sys.argv[0]} <command> [args...]", file=sys.stderr)
        print(f"Example: {sys.argv[0]} pytest tests/ -v", file=sys.stderr)
        sys.exit(1)

    command = " ".join(sys.argv[1:])

    # Create log file with timestamp
    log_dir = os.environ.get("LOG_DIR", "/tmp")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"error-detection-{timestamp}.log")

    info(f"Running command: {command}")
    info(f"Log file: {log_file}")

    # Open log file
    try:
        log_fd = open(log_file, "w", buffering=1)  # Line buffered
    except Exception as e:
        error(f"Failed to open log file: {e}")
        sys.exit(1)

    errors_detected = False
    error_lines = []
    output_lines = []
    exit_code = 0

    # Choose backend: pexpect (preferred) or subprocess (fallback)
    if PEXPECT_AVAILABLE:
        try:
            exit_code = _run_with_pexpect(command, log_fd, error_lines, output_lines)
            if error_lines:
                errors_detected = True
        except Exception as e:
            error(f"pexpect execution failed: {e}")
            error("Falling back to subprocess...")
            exit_code = _run_with_subprocess(command, log_fd, error_lines, output_lines)
            if error_lines:
                errors_detected = True
    else:
        info("pexpect not available, using subprocess backend")
        exit_code = _run_with_subprocess(command, log_fd, error_lines, output_lines)
        if error_lines:
            errors_detected = True

    # Close log file
    log_fd.close()

    # Combine all output for final checks
    output = "\n".join(output_lines)

    # Check exit code (with exceptions for commands that legitimately exit non-zero)
    if exit_code != 0:
        if not is_expected_nonzero(command):
            error(f"Command exited with non-zero code: {exit_code}")
            errors_detected = True
        else:
            warning(
                f"Command exited with non-zero code: {exit_code} (expected for this command type)"
            )

    # If errors were detected in real-time, we already terminated
    if errors_detected:
        if error_lines:
            print("=== ERROR LINES DETECTED ===", file=sys.stderr)
            for line in error_lines[:10]:  # Show first 10
                print(line, file=sys.stderr)
    else:
        # Final check for errors in complete output (in case we missed something)
        for line in output_lines:
            error_result = detect_error_in_line(line)
            if error_result:
                pattern, error_line = error_result
                error_lines.append(f"Line: {error_line}")
                errors_detected = True

            warning_result = detect_warning_in_line(line)
            if warning_result:
                pattern, warning_line = warning_result
                error_lines.append(f"Warning Line: {warning_line}")
                errors_detected = True

        if error_lines:
            print("=== ERROR LINES DETECTED ===", file=sys.stderr)
            for line in error_lines[:10]:  # Show first 10
                print(line, file=sys.stderr)

    # Check test results if this looks like a test run
    test_success, test_error = check_test_results(output, exit_code, command)
    if not test_success:
        error(test_error)
        errors_detected = True

    # Final decision
    if errors_detected:
        error("==========================================")
        error("ERROR DETECTION: Command execution failed")
        error(f"Exit code: {exit_code}")
        error(f"Log file: {log_file}")
        error(f"Command: {command}")
        error("==========================================")
        sys.exit(1)
    else:
        success("Command completed successfully")
        info(f"Log file: {log_file}")
        sys.exit(0)


if __name__ == "__main__":
    main()
