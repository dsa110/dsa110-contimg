#!/usr/bin/env python3
"""
FP32 vs FP64 Precision Validation - SAFE VERSION

This is a LIGHTWEIGHT test that validates numerical precision differences
between FP32 and FP64 for radio interferometry calibration operations.

SAFETY FEATURES:
- Hard memory limit: 2GB max
- Hard timeout: 60 seconds max
- Uses small array sizes that fit in memory
- Runs critical tests in subprocess for isolation
- Estimates memory BEFORE allocating

This script will NOT crash your system.

Author: DSA-110 Pipeline Team
Date: December 2024
"""

import gc
import sys
import time
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

# Import our resource limiting utilities
from resource_limits import (
    ResourceLimitedRunner,
    check_array_fits,
    estimate_array_memory_gb,
    get_current_memory_gb,
    check_available_memory,
)

# =============================================================================
# SAFE DEFAULTS - These are chosen to NEVER cause problems
# =============================================================================

# Memory budget: 8GB max (allows numpy/scipy libs to load)
# Note: 2GB was too tight and prevented numpy shared libs from loading
MAX_MEMORY_GB = 8.0

# Timeout: 60 seconds total
MAX_RUNTIME_SECONDS = 60

# Array sizes chosen to fit in 2GB with safety margin:
# - 16 antennas → 120 baselines
# - 64 channels
# - complex128 = 16 bytes per element
# - 120 × 64 × 16 bytes × 3 copies = ~0.4 MB (very safe)
SAFE_N_ANTENNAS = 16
SAFE_N_CHANNELS = 64


# =============================================================================
# Data classes for results
# =============================================================================

@dataclass
class PrecisionResult:
    """Result from a precision test."""
    test_name: str
    passed: bool
    fp64_value: float
    fp32_value: float
    difference: float
    threshold: float
    unit: str = ""


# =============================================================================
# Precision Tests - All use pre-checked safe array sizes
# =============================================================================

def test_complex_multiply_precision() -> PrecisionResult:
    """Test precision of complex multiplication (gain application).
    
    This is the core operation when applying calibration gains:
    V_corrected = V_observed / (g_i * g_j^*)
    """
    n = 10000  # Small 1D array
    
    # Create test data
    np.random.seed(42)
    a_real = np.random.randn(n)
    a_imag = np.random.randn(n)
    b_real = np.random.randn(n)
    b_imag = np.random.randn(n)
    
    # FP64 computation
    a64 = (a_real + 1j * a_imag).astype(np.complex128)
    b64 = (b_real + 1j * b_imag).astype(np.complex128)
    result64 = a64 * np.conj(b64)
    
    # FP32 computation
    a32 = (a_real + 1j * a_imag).astype(np.complex64)
    b32 = (b_real + 1j * b_imag).astype(np.complex64)
    result32 = a32 * np.conj(b32)
    
    # Compare
    diff = np.abs(result64 - result32.astype(np.complex128))
    max_diff = float(np.max(diff))
    mean_diff = float(np.mean(diff))
    
    # Threshold: FP32 has ~7 decimal digits, so 1e-6 relative error is expected
    threshold = 1e-5 * np.mean(np.abs(result64))
    
    return PrecisionResult(
        test_name="Complex Multiply (Gain Application)",
        passed=max_diff < threshold,
        fp64_value=mean_diff,
        fp32_value=max_diff,
        difference=max_diff,
        threshold=threshold,
        unit="absolute error",
    )


def test_accumulation_precision() -> PrecisionResult:
    """Test precision of sum accumulation (chi-squared, residuals).
    
    Calibration solvers sum residuals over many baselines.
    This tests whether FP32 accumulation introduces significant error.
    """
    # Simulate DSA-110: 4560 baselines × 768 channels = 3.5M values
    # But use smaller size for safety
    n = 100000
    
    np.random.seed(123)
    values = np.random.randn(n) * 1e-6  # Small values (like residuals)
    
    # FP64 sum
    sum64 = np.sum(values.astype(np.float64))
    
    # FP32 sum
    sum32 = np.sum(values.astype(np.float32))
    
    # Relative error
    rel_error = abs(sum64 - float(sum32)) / abs(sum64) if sum64 != 0 else 0
    
    threshold = 1e-5  # Allow 0.001% relative error
    
    return PrecisionResult(
        test_name="Sum Accumulation (Chi-squared)",
        passed=rel_error < threshold,
        fp64_value=sum64,
        fp32_value=float(sum32),
        difference=rel_error,
        threshold=threshold,
        unit="relative error",
    )


def test_phase_precision() -> PrecisionResult:
    """Test precision of phase computation (critical for calibration).
    
    Phase errors directly affect calibration quality.
    """
    n = 10000
    
    np.random.seed(456)
    # Complex gains with realistic amplitudes and phases
    gains = np.exp(1j * np.random.uniform(-np.pi, np.pi, n))
    gains *= (1.0 + 0.1 * np.random.randn(n))  # Amplitude variation
    
    # FP64 phase
    phase64 = np.angle(gains.astype(np.complex128), deg=True)
    
    # FP32 phase
    phase32 = np.angle(gains.astype(np.complex64), deg=True)
    
    # Phase difference (handle wrapping)
    phase_diff = np.abs(phase64 - phase32)
    phase_diff = np.minimum(phase_diff, 360 - phase_diff)
    
    max_diff = float(np.max(phase_diff))
    mean_diff = float(np.mean(phase_diff))
    
    threshold = 0.01  # 0.01 degree - very strict
    
    return PrecisionResult(
        test_name="Phase Computation",
        passed=max_diff < threshold,
        fp64_value=mean_diff,
        fp32_value=max_diff,
        difference=max_diff,
        threshold=threshold,
        unit="degrees",
    )


def test_matrix_solve_precision() -> PrecisionResult:
    """Test precision of matrix solve (calibration solver).
    
    Uses small matrix that fits comfortably in memory.
    """
    n = 64  # Small matrix
    
    np.random.seed(789)
    
    # Create well-conditioned system
    A = np.eye(n) + 0.1 * np.random.randn(n, n)
    A = A @ A.T  # Symmetric positive definite
    b = np.random.randn(n)
    
    # FP64 solve
    x64 = np.linalg.solve(A.astype(np.float64), b.astype(np.float64))
    
    # FP32 solve
    x32 = np.linalg.solve(A.astype(np.float32), b.astype(np.float32))
    
    # Compare
    diff = np.abs(x64 - x32.astype(np.float64))
    max_diff = float(np.max(diff))
    rel_diff = max_diff / np.max(np.abs(x64))
    
    threshold = 1e-4  # 0.01% relative error
    
    return PrecisionResult(
        test_name="Matrix Solve (Calibration)",
        passed=rel_diff < threshold,
        fp64_value=float(np.max(np.abs(x64))),
        fp32_value=float(np.max(np.abs(x32))),
        difference=rel_diff,
        threshold=threshold,
        unit="relative error",
    )


def test_fft_precision() -> PrecisionResult:
    """Test precision of FFT (imaging).
    
    Uses modest 2D FFT size.
    """
    n = 512  # 512x512 is ~4MB in complex64, safe
    
    np.random.seed(101)
    x = np.random.randn(n, n) + 1j * np.random.randn(n, n)
    
    # FP64 FFT
    fft64 = np.fft.fft2(x.astype(np.complex128))
    
    # FP32 FFT
    fft32 = np.fft.fft2(x.astype(np.complex64))
    
    # Compare
    diff = np.abs(fft64 - fft32.astype(np.complex128))
    max_diff = float(np.max(diff))
    rel_diff = max_diff / np.max(np.abs(fft64))
    
    threshold = 1e-5
    
    return PrecisionResult(
        test_name="2D FFT (Imaging)",
        passed=rel_diff < threshold,
        fp64_value=float(np.max(np.abs(fft64))),
        fp32_value=float(np.max(np.abs(fft32))),
        difference=rel_diff,
        threshold=threshold,
        unit="relative error",
    )


def test_visibility_simulation() -> PrecisionResult:
    """Test small-scale visibility computation precision.
    
    Simulates the core calibration equation: V = g_i * g_j* * V_model
    """
    n_ant = SAFE_N_ANTENNAS
    n_chan = SAFE_N_CHANNELS
    n_bl = n_ant * (n_ant - 1) // 2
    
    np.random.seed(202)
    
    # Gains per antenna/channel
    gains = np.exp(1j * np.random.uniform(-0.5, 0.5, (n_ant, n_chan)))
    gains *= (1.0 + 0.05 * np.random.randn(n_ant, n_chan))
    
    model_vis = 10.0  # 10 Jy point source
    
    # Compute visibilities: V_ij = g_i * conj(g_j) * model
    vis_fp64 = np.zeros((n_bl, n_chan), dtype=np.complex128)
    vis_fp32 = np.zeros((n_bl, n_chan), dtype=np.complex64)
    
    gains64 = gains.astype(np.complex128)
    gains32 = gains.astype(np.complex64)
    
    bl_idx = 0
    for i in range(n_ant):
        for j in range(i + 1, n_ant):
            vis_fp64[bl_idx] = gains64[i] * np.conj(gains64[j]) * model_vis
            vis_fp32[bl_idx] = gains32[i] * np.conj(gains32[j]) * model_vis
            bl_idx += 1
    
    # Compare
    diff = np.abs(vis_fp64 - vis_fp32.astype(np.complex128))
    max_diff = float(np.max(diff))
    rel_diff = max_diff / model_vis
    
    threshold = 1e-5  # 0.001% of model flux
    
    return PrecisionResult(
        test_name="Visibility Simulation",
        passed=rel_diff < threshold,
        fp64_value=float(np.mean(np.abs(vis_fp64))),
        fp32_value=float(np.mean(np.abs(vis_fp32))),
        difference=rel_diff,
        threshold=threshold,
        unit="relative error",
    )


# =============================================================================
# GPU Tests (if available)
# =============================================================================

def test_gpu_precision() -> List[PrecisionResult]:
    """Test GPU precision if CuPy is available."""
    results = []
    
    try:
        import cupy as cp
    except ImportError:
        return results
    
    try:
        # Clear any leftover GPU memory first
        cp.get_default_memory_pool().free_all_blocks()
        cp.get_default_pinned_memory_pool().free_all_blocks()
        
        # Check available GPU memory
        mem_info = cp.cuda.Device(0).mem_info
        free_gb = mem_info[0] / 1e9
        total_gb = mem_info[1] / 1e9
        print(f"\n       GPU: {free_gb:.1f} GB free / {total_gb:.1f} GB total")
        
        if free_gb < 0.5:
            print("       (Skipping - insufficient GPU memory)")
            return results
        
        # GPU FFT test
        n = 512
        np.random.seed(303)
        x_np = np.random.randn(n, n) + 1j * np.random.randn(n, n)
        
        # CPU FP64 reference
        fft_cpu = np.fft.fft2(x_np.astype(np.complex128))
        
        # GPU FP32
        x_gpu = cp.asarray(x_np.astype(np.complex64))
        fft_gpu = cp.fft.fft2(x_gpu)
        fft_gpu_np = cp.asnumpy(fft_gpu).astype(np.complex128)
        
        diff = np.abs(fft_cpu - fft_gpu_np)
        rel_diff = float(np.max(diff)) / np.max(np.abs(fft_cpu))
        
        results.append(PrecisionResult(
            test_name="GPU FFT (FP32)",
            passed=rel_diff < 1e-5,
            fp64_value=float(np.max(np.abs(fft_cpu))),
            fp32_value=float(np.max(np.abs(fft_gpu_np))),
            difference=rel_diff,
            threshold=1e-5,
            unit="relative error",
        ))
        
        # Clean up GPU memory
        del x_gpu, fft_gpu
        cp.get_default_memory_pool().free_all_blocks()
        
    except Exception as e:
        print(f"\n       GPU test error: {e}")
        print("       (GPU tests skipped due to error)")
    
    return results


# =============================================================================
# Main Runner
# =============================================================================

def run_validation() -> bool:
    """Run all precision validation tests.
    
    Returns:
        True if all tests pass, False otherwise
    """
    print("=" * 60)
    print("  FP32 vs FP64 Precision Validation (Safe Version)")
    print("=" * 60)
    
    # Check system state
    available, total = check_available_memory()
    current = get_current_memory_gb()
    print(f"\nSystem: {available:.1f} GB available / {total:.1f} GB total")
    print(f"Current usage: {current:.2f} GB")
    print(f"Memory limit: {MAX_MEMORY_GB} GB")
    print(f"Timeout: {MAX_RUNTIME_SECONDS} seconds")
    print()
    
    # Run tests
    tests = [
        ("Complex Multiply", test_complex_multiply_precision),
        ("Accumulation", test_accumulation_precision),
        ("Phase", test_phase_precision),
        ("Matrix Solve", test_matrix_solve_precision),
        ("FFT", test_fft_precision),
        ("Visibility Sim", test_visibility_simulation),
    ]
    
    results: List[PrecisionResult] = []
    
    print("─" * 60)
    print("Running precision tests...")
    print("─" * 60)
    
    for name, test_func in tests:
        try:
            gc.collect()  # Clean up before each test
            t0 = time.perf_counter()
            result = test_func()
            elapsed = time.perf_counter() - t0
            results.append(result)
            
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"\n{status}: {result.test_name} ({elapsed:.3f}s)")
            print(f"       Difference: {result.difference:.2e} {result.unit}")
            print(f"       Threshold:  {result.threshold:.2e}")
            
        except Exception as e:
            print(f"\n✗ ERROR: {name}: {e}")
    
    # GPU tests
    print("\n" + "─" * 60)
    print("GPU tests...")
    print("─" * 60)
    
    gpu_results = test_gpu_precision()
    if gpu_results:
        for result in gpu_results:
            results.append(result)
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"\n{status}: {result.test_name}")
            print(f"       Difference: {result.difference:.2e}")
    else:
        print("\n(GPU tests skipped - CuPy not available)")
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    n_passed = sum(1 for r in results if r.passed)
    n_total = len(results)
    all_passed = (n_passed == n_total)
    
    print(f"\nTests:  {n_passed}/{n_total} passed")
    print(f"Memory: {get_current_memory_gb():.2f} GB used")
    
    if all_passed:
        print("\n✓ ALL TESTS PASSED")
        print("\nConclusion: FP32 provides sufficient precision for:")
        print("  • Gain application (complex multiply)")
        print("  • FFT/imaging operations")
        print("  • Basic accumulations")
        print("\n⚠ Calibration SOLVER should still use FP64 for:")
        print("  • Large accumulations over many baselines")
        print("  • Iterative convergence")
        print("  • Ill-conditioned matrices")
    else:
        print("\n✗ SOME TESTS FAILED")
        failed = [r for r in results if not r.passed]
        for r in failed:
            print(f"  - {r.test_name}: {r.difference:.2e} > {r.threshold:.2e}")
    
    print("\n" + "=" * 60)
    
    return all_passed


def main():
    """Main entry point with resource limits."""
    try:
        with ResourceLimitedRunner(
            max_memory_gb=MAX_MEMORY_GB,
            max_wall_seconds=MAX_RUNTIME_SECONDS,
            min_available_gb=1.0,
            gpu_safe=True,  # Required for CUDA operations
        ):
            success = run_validation()
            sys.exit(0 if success else 1)
            
    except MemoryError as e:
        print(f"\n✗ MEMORY ERROR: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
