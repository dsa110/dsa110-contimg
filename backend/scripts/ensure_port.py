#!/usr/bin/env python3
"""
Ensure a port is available by killing any processes using it.

Similar to frontend's ensure-port.cjs but for Python/backend use.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from typing import List, NamedTuple, Optional


class ProcessInfo(NamedTuple):
    """Information about a process using a port."""
    pid: int
    command: str


def get_processes_on_port(port: int) -> List[ProcessInfo]:
    """Get list of processes listening on the given port."""
    try:
        # Use lsof to find processes on the port
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        
        pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
        
        # Get command names for each PID
        processes = []
        for pid in pids:
            try:
                # Read command from /proc
                with open(f"/proc/{pid}/comm", "r") as f:
                    command = f.read().strip()
                processes.append(ProcessInfo(pid=pid, command=command))
            except (FileNotFoundError, PermissionError):
                processes.append(ProcessInfo(pid=pid, command="<unknown>"))
        
        return processes
    except FileNotFoundError:
        print("[ensure-port] Error: 'lsof' command not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ensure-port] Error checking port: {e}", file=sys.stderr)
        return []


def kill_processes(processes: List[ProcessInfo], force: bool = False) -> bool:
    """
    Kill the given processes.
    
    Args:
        processes: List of processes to kill
        force: If True, use SIGKILL instead of SIGTERM
    
    Returns:
        True if all processes were killed successfully
    """
    sig = signal.SIGKILL if force else signal.SIGTERM
    sig_name = "SIGKILL" if force else "SIGTERM"
    
    all_killed = True
    for proc in processes:
        try:
            os.kill(proc.pid, sig)
            print(f"[ensure-port] Sent {sig_name} to PID {proc.pid} ({proc.command})")
        except ProcessLookupError:
            # Process already gone
            pass
        except PermissionError:
            print(f"[ensure-port] Permission denied killing PID {proc.pid}", file=sys.stderr)
            all_killed = False
        except Exception as e:
            print(f"[ensure-port] Error killing PID {proc.pid}: {e}", file=sys.stderr)
            all_killed = False
    
    return all_killed


def ensure_port_available(port: int, max_attempts: int = 5, initial_delay: float = 0.5) -> bool:
    """
    Ensure the given port is available, killing processes if necessary.
    
    Uses exponential backoff between attempts.
    
    Args:
        port: Port number to free
        max_attempts: Maximum number of attempts to free the port
        initial_delay: Initial delay in seconds between attempts
    
    Returns:
        True if port is available, False if could not free it
    """
    delay = initial_delay
    
    for attempt in range(1, max_attempts + 1):
        processes = get_processes_on_port(port)
        
        if not processes:
            print(f"[ensure-port] OK Port {port} is now available (attempt {attempt})")
            return True
        
        print(f"[ensure-port] Found {len(processes)} process(es) on port {port}:")
        for proc in processes:
            print(f"[ensure-port]   PID {proc.pid}: {proc.command}")
        
        # Try graceful termination first, then force kill on later attempts
        force = attempt >= 3
        kill_processes(processes, force=force)
        
        # Wait for processes to die
        time.sleep(delay)
        delay = min(delay * 2, 5.0)  # Exponential backoff, max 5 seconds
    
    # Final check
    processes = get_processes_on_port(port)
    if not processes:
        print(f"[ensure-port] OK Port {port} is now available")
        return True
    
    print(f"[ensure-port] ERROR: Could not free port {port} after {max_attempts} attempts", file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Ensure a port is available by killing any processes using it."
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port to ensure is available (default: 8000)"
    )
    parser.add_argument(
        "--max-attempts", "-m",
        type=int,
        default=5,
        help="Maximum attempts to free the port (default: 5)"
    )
    
    args = parser.parse_args()
    
    success = ensure_port_available(args.port, max_attempts=args.max_attempts)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
