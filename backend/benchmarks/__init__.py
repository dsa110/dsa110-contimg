"""
DSA-110 Pipeline Performance Benchmarks

This package contains ASV (Airspeed Velocity) benchmarks for tracking
pipeline performance over time.

Benchmark Categories:
- bench_calibration.py: Calibration operations (bandpass, gain, delay)
- bench_imaging.py: TCLEAN imaging operations
- bench_conversion.py: HDF5 to MS conversion
- bench_gpu.py: GPU-accelerated operations (CuPy)

Usage:
    # Run all benchmarks
    cd backend/benchmarks
    asv run

    # Run specific benchmark
    asv run --bench "bench_calibration"

    # Generate HTML report
    asv publish
    asv preview

    # Compare commits
    asv compare HEAD~5 HEAD

See: https://asv.readthedocs.io/
"""
