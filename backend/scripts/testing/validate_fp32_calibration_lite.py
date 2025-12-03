#!/usr/bin/env python3
"""
LIGHTWEIGHT FP32 vs FP64 Calibration Precision Validation

This is a SAFE version that uses small test sizes to avoid memory issues.
For full-scale testing, use real CASA calibration on actual MS files.

Memory budget: < 500 MB total
Time budget: < 60 seconds total
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import numpy as np

# Hard limits to prevent system overload
MAX_MEMORY_MB = 500
MAX_TIME_SECONDS = 60
MAX_ANTENNAS = 32  # Safe limit
MAX_CHANNELS = 64  # Safe limit


@dataclass
class TestResult:
    name: str
    passed: bool
    fp64_value: float
    fp32_value: float
    difference: float
    threshold: float
    unit: str


def estimate_memory_mb(n_ant: int, n_chan: int, n_time: int) -> float:
    """Estimate memory usage in MB."""
    n_bl = n_ant * (n_ant - 1) // 2
    # complex128 = 16 bytes, we need ~4 copies during computation
    bytes_needed = n_bl * n_chan * n_time * 16 * 4
    return bytes_needed / 1e6


def run_safe_tests(n_ant: int = 16, n_chan: int = 32, n_time: int = 5) -> List[TestResult]:
    """Run precision tests with safe parameters."""
    
    results = []
    start_time = time.time()
    
    # Enforce limits
    n_ant = min(n_ant, MAX_ANTENNAS)
    n_chan = min(n_chan, MAX_CHANNELS)
    
    mem_est = estimate_memory_mb(n_ant, n_chan, n_time)
    if mem_est > MAX_MEMORY_MB:
        print(f"⚠️  Reducing size: {mem_est:.0f} MB exceeds {MAX_MEMORY_MB} MB limit")
        n_ant = 16
        n_chan = 32
        n_time = 5
    
    n_bl = n_ant * (n_ant - 1) // 2
    print(f"\nTest configuration:")
    print(f"  Antennas:  {n_ant}")
    print(f"  Baselines: {n_bl}")
    print(f"  Channels:  {n_chan}")
    print(f"  Times:     {n_time}")
    print(f"  Est. memory: {estimate_memory_mb(n_ant, n_chan, n_time):.1f} MB")
    print()
    
    # =========================================================================
    # Test 1: Complex multiplication precision (gain application)
    # =========================================================================
    print("Test 1: Complex multiplication (gain application)...")
    
    np.random.seed(42)
    
    # Create test data
    vis_fp64 = (np.random.randn(n_bl, n_chan) + 1j * np.random.randn(n_bl, n_chan)).astype(np.complex128)
    gains_fp64 = (0.9 + 0.2 * np.random.rand(n_ant, n_chan) + 
                  1j * 0.1 * np.random.randn(n_ant, n_chan)).astype(np.complex128)
    
    # Apply gains in FP64
    corrected_fp64 = vis_fp64.copy()
    bl_idx = 0
    for i in range(n_ant):
        for j in range(i + 1, n_ant):
            corrected_fp64[bl_idx] = vis_fp64[bl_idx] * gains_fp64[i] * np.conj(gains_fp64[j])
            bl_idx += 1
    
    # Apply gains in FP32
    vis_fp32 = vis_fp64.astype(np.complex64)
    gains_fp32 = gains_fp64.astype(np.complex64)
    corrected_fp32 = vis_fp32.copy()
    bl_idx = 0
    for i in range(n_ant):
        for j in range(i + 1, n_ant):
            corrected_fp32[bl_idx] = vis_fp32[bl_idx] * gains_fp32[i] * np.conj(gains_fp32[j])
            bl_idx += 1
    
    # Compare
    diff = np.abs(corrected_fp64 - corrected_fp32.astype(np.complex128))
    max_diff = np.max(diff)
    rel_diff = max_diff / np.max(np.abs(corrected_fp64))
    
    threshold = 1e-6  # FP32 has ~7 decimal digits
    results.append(TestResult(
        name="Gain Application",
        passed=rel_diff < threshold,
        fp64_value=0.0,
        fp32_value=float(rel_diff),
        difference=float(rel_diff),
        threshold=threshold,
        unit="relative error"
    ))
    print(f"  Relative error: {rel_diff:.2e} (threshold: {threshold:.0e}) {'✓' if rel_diff < threshold else '✗'}")
    
    # Clean up
    del vis_fp64, vis_fp32, gains_fp64, gains_fp32, corrected_fp64, corrected_fp32
    
    if time.time() - start_time > MAX_TIME_SECONDS:
        print("⚠️  Time limit reached, stopping tests")
        return results
    
    # =========================================================================
    # Test 2: Accumulation precision (chi-squared computation)
    # =========================================================================
    print("\nTest 2: Accumulation precision (chi-squared)...")
    
    # Simulate residual accumulation
    residuals = np.random.randn(n_bl * n_chan).astype(np.float64) * 1e-3
    
    chi2_fp64 = np.sum(residuals ** 2)
    chi2_fp32 = np.sum(residuals.astype(np.float32) ** 2)
    
    rel_error = abs(chi2_fp64 - chi2_fp32) / chi2_fp64
    threshold = 1e-5
    
    results.append(TestResult(
        name="Chi-squared Accumulation",
        passed=rel_error < threshold,
        fp64_value=float(chi2_fp64),
        fp32_value=float(chi2_fp32),
        difference=float(rel_error),
        threshold=threshold,
        unit="relative error"
    ))
    print(f"  Relative error: {rel_error:.2e} (threshold: {threshold:.0e}) {'✓' if rel_error < threshold else '✗'}")
    
    del residuals
    
    # =========================================================================
    # Test 3: Phase precision
    # =========================================================================
    print("\nTest 3: Phase computation precision...")
    
    # Complex gains with known phases
    phases_deg = np.linspace(-180, 180, n_ant * n_chan)
    gains = np.exp(1j * np.deg2rad(phases_deg))
    
    # Extract phases in FP64 and FP32
    phase_fp64 = np.rad2deg(np.angle(gains.astype(np.complex128)))
    phase_fp32 = np.rad2deg(np.angle(gains.astype(np.complex64)))
    
    phase_diff = np.max(np.abs(phase_fp64 - phase_fp32))
    threshold = 0.01  # 0.01 degree
    
    results.append(TestResult(
        name="Phase Extraction",
        passed=phase_diff < threshold,
        fp64_value=0.0,
        fp32_value=float(phase_diff),
        difference=float(phase_diff),
        threshold=threshold,
        unit="degrees"
    ))
    print(f"  Max phase difference: {phase_diff:.4f}° (threshold: {threshold}°) {'✓' if phase_diff < threshold else '✗'}")
    
    del gains, phase_fp64, phase_fp32
    
    # =========================================================================
    # Test 4: FFT precision (imaging)
    # =========================================================================
    print("\nTest 4: FFT precision (imaging)...")
    
    # Small 2D FFT test
    img_size = 256
    x = np.random.randn(img_size, img_size) + 1j * np.random.randn(img_size, img_size)
    
    fft_fp64 = np.fft.fft2(x.astype(np.complex128))
    fft_fp32 = np.fft.fft2(x.astype(np.complex64))
    
    fft_diff = np.max(np.abs(fft_fp64 - fft_fp32.astype(np.complex128)))
    fft_rel = fft_diff / np.max(np.abs(fft_fp64))
    threshold = 1e-6
    
    results.append(TestResult(
        name="2D FFT (256x256)",
        passed=fft_rel < threshold,
        fp64_value=0.0,
        fp32_value=float(fft_rel),
        difference=float(fft_rel),
        threshold=threshold,
        unit="relative error"
    ))
    print(f"  Relative error: {fft_rel:.2e} (threshold: {threshold:.0e}) {'✓' if fft_rel < threshold else '✗'}")
    
    del x, fft_fp64, fft_fp32
    
    # =========================================================================
    # Test 5: Matrix inversion (small scale)
    # =========================================================================
    print("\nTest 5: Matrix inversion (calibration solver)...")
    
    # Small matrix that fits in memory
    mat_size = min(n_ant, 32)
    A = np.random.randn(mat_size, mat_size).astype(np.float64)
    A = A @ A.T + np.eye(mat_size)  # Make positive definite
    
    inv_fp64 = np.linalg.inv(A.astype(np.float64))
    inv_fp32 = np.linalg.inv(A.astype(np.float32))
    
    inv_diff = np.linalg.norm(inv_fp64 - inv_fp32.astype(np.float64)) / np.linalg.norm(inv_fp64)
    threshold = 1e-5
    
    results.append(TestResult(
        name=f"Matrix Inversion ({mat_size}x{mat_size})",
        passed=inv_diff < threshold,
        fp64_value=0.0,
        fp32_value=float(inv_diff),
        difference=float(inv_diff),
        threshold=threshold,
        unit="relative Frobenius error"
    ))
    print(f"  Relative error: {inv_diff:.2e} (threshold: {threshold:.0e}) {'✓' if inv_diff < threshold else '✗'}")
    
    return results


def print_summary(results: List[TestResult]) -> bool:
    """Print summary and return overall pass/fail."""
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    n_passed = sum(1 for r in results if r.passed)
    n_total = len(results)
    all_passed = n_passed == n_total
    
    print(f"\nPassed: {n_passed}/{n_total}")
    
    for r in results:
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(f"  {status}: {r.name} ({r.difference:.2e} {r.unit})")
    
    print("\n" + "-" * 60)
    if all_passed:
        print("✓ FP32 precision is ACCEPTABLE for DSA-110 calibration")
        print("\nRecommendation:")
        print("  • Use FP32 for gain application (GPU-accelerate)")
        print("  • Use FP32 for FFT/gridding (GPU-accelerate)")
        print("  • Use FP64 for solver accumulations (keep on CPU)")
    else:
        print("✗ Some precision tests FAILED")
        print("\nRecommendation:")
        print("  • Review failed tests before using FP32")
        print("  • Consider FP64 for affected operations")
    
    print("-" * 60)
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Lightweight FP32 vs FP64 precision validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--antennas", type=int, default=16,
                        help=f"Number of antennas (max {MAX_ANTENNAS})")
    parser.add_argument("--channels", type=int, default=32,
                        help=f"Number of channels (max {MAX_CHANNELS})")
    parser.add_argument("--output", "-o", help="Output JSON path")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  FP32 vs FP64 Precision Validation (Lightweight)")
    print("=" * 60)
    print(f"\nMemory limit: {MAX_MEMORY_MB} MB")
    print(f"Time limit: {MAX_TIME_SECONDS} seconds")
    
    start = time.time()
    results = run_safe_tests(
        n_ant=args.antennas,
        n_chan=args.channels,
    )
    elapsed = time.time() - start
    
    print(f"\nCompleted in {elapsed:.1f} seconds")
    
    all_passed = print_summary(results)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                "results": [asdict(r) for r in results],
                "all_passed": all_passed,
                "elapsed_seconds": elapsed,
            }, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
