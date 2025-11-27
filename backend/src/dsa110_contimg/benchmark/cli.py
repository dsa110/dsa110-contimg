"""
CLI interface for DSA-110 pipeline performance benchmarks.

This module provides a user-friendly wrapper around airspeed-velocity (asv)
for running pipeline performance benchmarks. It handles environment setup,
commit tracking, and result persistence automatically.

Usage
-----
    # Quick check (single iteration, ~5-10 minutes)
    dsa110-benchmark quick

    # Full run with statistics (~30-60 minutes)
    dsa110-benchmark run

    # Run specific benchmark class
    dsa110-benchmark run --filter Calibration

    # Generate HTML report
    dsa110-benchmark report

    # Show current results
    dsa110-benchmark show
"""

import os
import subprocess
import sys
from pathlib import Path

import click

# Determine paths
REPO_ROOT = Path(__file__).parents[4]  # backend/src/dsa110_contimg/benchmark -> repo root
BENCHMARK_DIR = REPO_ROOT / "benchmarks"
ASV_RESULTS = BENCHMARK_DIR / ".asv" / "results"
ASV_HTML = BENCHMARK_DIR / ".asv" / "html"


def _get_git_hash() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:12]
    except subprocess.CalledProcessError:
        return "unknown"


def _run_asv(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run asv command in benchmark directory."""
    env = os.environ.copy()
    # Ensure we use the casa6 environment
    env.setdefault("CASA6_PYTHON", "/opt/miniforge/envs/casa6/bin/python")
    
    cmd = ["asv"] + args
    click.echo(f"Running: {' '.join(cmd)}")
    click.echo(f"  in: {BENCHMARK_DIR}")
    click.echo()
    
    return subprocess.run(
        cmd,
        cwd=BENCHMARK_DIR,
        env=env,
        check=check,
    )


@click.group()
@click.version_option(version="1.0.0", prog_name="dsa110-benchmark")
def cli():
    """DSA-110 Pipeline Performance Benchmarks.
    
    Run statistical performance benchmarks against the DSA-110 continuum imaging
    pipeline using airspeed-velocity (asv). Tracks timing regressions across
    commits and generates detailed reports.
    
    \b
    Quick Start:
        dsa110-benchmark quick     # Single iteration (~5 min)
        dsa110-benchmark run       # Full stats (~30 min)
        dsa110-benchmark report    # Generate HTML report
    
    \b
    Benchmark Categories:
        - conversion:   HDF5 → MS file conversion (stages to SSD)
        - calibration:  Bandpass, gain calibration, applycal
        - flagging:     Flag reset, zero flagging
        - imaging:      WSClean imaging (disabled by default)
    
    For detailed documentation, see:
        - benchmarks/README.md
        - docs/guides/benchmarking.md
    """
    # Verify benchmark directory exists
    if not BENCHMARK_DIR.exists():
        click.echo(f"Error: Benchmark directory not found: {BENCHMARK_DIR}", err=True)
        sys.exit(1)
    
    if not (BENCHMARK_DIR / "asv.conf.json").exists():
        click.echo(f"Error: asv.conf.json not found in {BENCHMARK_DIR}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--filter", "-f", "bench_filter",
    help="Filter benchmarks by name pattern (e.g., 'Calibration', 'time_bandpass')"
)
@click.option(
    "--verbose", "-v", is_flag=True,
    help="Show verbose output"
)
def quick(bench_filter: str | None, verbose: bool):
    """Run quick benchmark check (single iteration).
    
    Executes each benchmark once to verify functionality and get approximate
    timings. Use this for development and quick validation.
    
    \b
    Examples:
        dsa110-benchmark quick                    # All benchmarks
        dsa110-benchmark quick -f Calibration     # Only calibration
        dsa110-benchmark quick -f time_bandpass   # Only bandpass benchmark
    
    \b
    Typical runtime: 5-15 minutes (depending on filter)
    """
    commit_hash = _get_git_hash()
    click.echo(f"Quick benchmark check at commit {commit_hash}")
    click.echo("=" * 60)
    
    args = ["run", "--quick", "--python=same", f"--set-commit-hash={commit_hash}"]
    
    if bench_filter:
        args.extend(["--bench", bench_filter])
    
    if verbose:
        args.append("--verbose")
    
    result = _run_asv(args, check=False)
    
    if result.returncode == 0:
        click.echo()
        click.echo("✓ Quick benchmark completed successfully")
        click.echo(f"  Results saved for commit: {commit_hash}")
    else:
        click.echo()
        click.echo("✗ Benchmark run had errors (see output above)", err=True)
    
    sys.exit(result.returncode)


@cli.command()
@click.option(
    "--filter", "-f", "bench_filter",
    help="Filter benchmarks by name pattern (e.g., 'Calibration', 'time_bandpass')"
)
@click.option(
    "--samples", "-n", default=None, type=int,
    help="Number of samples per benchmark (default: asv auto-detect)"
)
@click.option(
    "--verbose", "-v", is_flag=True,
    help="Show verbose output"
)
def run(bench_filter: str | None, samples: int | None, verbose: bool):
    """Run full benchmark suite with statistics.
    
    Executes multiple iterations of each benchmark to collect statistical data.
    Results are saved and can be compared across commits to detect regressions.
    
    \b
    Examples:
        dsa110-benchmark run                      # All benchmarks
        dsa110-benchmark run -f Calibration       # Only calibration
        dsa110-benchmark run -n 5                 # Force 5 samples
    
    \b
    Typical runtime: 30-60 minutes
    """
    commit_hash = _get_git_hash()
    click.echo(f"Full benchmark run at commit {commit_hash}")
    click.echo("=" * 60)
    
    args = ["run", "--python=same", f"--set-commit-hash={commit_hash}"]
    
    if bench_filter:
        args.extend(["--bench", bench_filter])
    
    if samples:
        args.extend(["--attribute", f"repeat={samples}"])
    
    if verbose:
        args.append("--verbose")
    
    result = _run_asv(args, check=False)
    
    if result.returncode == 0:
        click.echo()
        click.echo("✓ Full benchmark completed successfully")
        click.echo(f"  Results saved for commit: {commit_hash}")
        click.echo()
        click.echo("Generate HTML report with: dsa110-benchmark report")
    else:
        click.echo()
        click.echo("✗ Benchmark run had errors (see output above)", err=True)
    
    sys.exit(result.returncode)


@cli.command()
@click.option(
    "--open", "-o", "open_browser", is_flag=True,
    help="Open report in browser after generating"
)
def report(open_browser: bool):
    """Generate HTML benchmark report.
    
    Creates an interactive HTML report from benchmark results. The report
    shows timing trends, comparisons across commits, and regression detection.
    
    \b
    Output: benchmarks/.asv/html/index.html
    """
    click.echo("Generating HTML benchmark report...")
    click.echo("=" * 60)
    
    # Publish results to HTML
    result = _run_asv(["publish"], check=False)
    
    if result.returncode != 0:
        click.echo("✗ Failed to generate report", err=True)
        sys.exit(result.returncode)
    
    html_index = ASV_HTML / "index.html"
    click.echo()
    click.echo(f"✓ Report generated: {html_index}")
    
    if open_browser:
        # Start preview server
        click.echo()
        click.echo("Starting preview server (Ctrl+C to stop)...")
        _run_asv(["preview"], check=False)
    else:
        click.echo()
        click.echo("View report with:")
        click.echo(f"  cd {BENCHMARK_DIR} && asv preview")
        click.echo("  Or open in browser: file://{html_index}")


@cli.command()
def show():
    """Show latest benchmark results.
    
    Displays a summary of the most recent benchmark results for quick reference.
    """
    click.echo("Latest benchmark results")
    click.echo("=" * 60)
    
    # Find latest results
    if not ASV_RESULTS.exists():
        click.echo("No benchmark results found. Run benchmarks first:")
        click.echo("  dsa110-benchmark quick")
        sys.exit(1)
    
    # List available result files
    machine_dirs = [d for d in ASV_RESULTS.iterdir() if d.is_dir()]
    if not machine_dirs:
        click.echo("No benchmark results found.")
        sys.exit(1)
    
    for machine_dir in machine_dirs:
        json_files = sorted(machine_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if json_files:
            latest = json_files[-1]
            click.echo(f"Machine: {machine_dir.name}")
            click.echo(f"Latest result: {latest.name}")
            click.echo()
            
            # Show using asv show
            _run_asv(["show", latest.stem], check=False)


@cli.command()
def check():
    """Verify benchmark configuration.
    
    Checks that all benchmarks are properly defined and can be discovered.
    Run this after adding or modifying benchmarks.
    """
    click.echo("Checking benchmark configuration...")
    click.echo("=" * 60)
    
    result = _run_asv(["check"], check=False)
    
    if result.returncode == 0:
        click.echo()
        click.echo("✓ All benchmarks valid")
    else:
        click.echo()
        click.echo("✗ Benchmark validation failed", err=True)
    
    sys.exit(result.returncode)


@cli.command()
@click.argument("baseline", default="HEAD~1")
@click.argument("target", default="HEAD")
@click.option(
    "--factor", "-f", default=1.1, type=float,
    help="Regression threshold factor (default: 1.1 = 10%)"
)
def compare(baseline: str, target: str, factor: float):
    """Compare benchmark results between commits.
    
    Detects performance regressions by comparing two commits. Reports any
    benchmark that regressed by more than the threshold factor.
    
    \b
    Arguments:
        BASELINE    Base commit for comparison (default: HEAD~1)
        TARGET      Target commit to compare (default: HEAD)
    
    \b
    Examples:
        dsa110-benchmark compare                  # Compare HEAD to HEAD~1
        dsa110-benchmark compare main HEAD        # Compare to main branch
        dsa110-benchmark compare abc123 def456    # Compare specific commits
    """
    click.echo(f"Comparing {baseline} → {target} (factor={factor})")
    click.echo("=" * 60)
    
    result = _run_asv(
        ["continuous", baseline, target, "--factor", str(factor)],
        check=False
    )
    
    if result.returncode == 0:
        click.echo()
        click.echo("✓ No significant regressions detected")
    elif result.returncode == 1:
        click.echo()
        click.echo("⚠ Performance regressions detected (see above)", err=True)
    else:
        click.echo()
        click.echo("✗ Comparison failed", err=True)
    
    sys.exit(result.returncode)


@cli.command()
def info():
    """Show benchmark environment information.
    
    Displays information about the benchmark configuration, available
    benchmarks, and system environment.
    """
    click.echo("Benchmark Environment Information")
    click.echo("=" * 60)
    click.echo()
    
    click.echo(f"Repository root:     {REPO_ROOT}")
    click.echo(f"Benchmark directory: {BENCHMARK_DIR}")
    click.echo(f"Results directory:   {ASV_RESULTS}")
    click.echo(f"HTML output:         {ASV_HTML}")
    click.echo()
    
    click.echo("Git commit: " + _get_git_hash())
    click.echo()
    
    # List benchmark files
    click.echo("Benchmark files:")
    for f in sorted(BENCHMARK_DIR.glob("bench_*.py")):
        click.echo(f"  - {f.name}")
    click.echo()
    
    # Machine info
    machine_json = BENCHMARK_DIR / ".asv" / "machine.json"
    if machine_json.exists():
        click.echo(f"Machine config: {machine_json}")
        import json
        with open(machine_json) as f:
            machine = json.load(f)
        click.echo(f"  hostname: {machine.get('machine', 'unknown')}")
        click.echo(f"  os:       {machine.get('os', 'unknown')}")
        click.echo(f"  cpu:      {machine.get('cpu', 'unknown')}")
        click.echo(f"  ram:      {machine.get('ram', 'unknown')}")
    else:
        click.echo("Machine config: Not found (will be created on first run)")


def main():
    """Entry point for dsa110-benchmark CLI."""
    cli()


if __name__ == "__main__":
    main()
