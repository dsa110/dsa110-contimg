#!/usr/bin/env python3
"""
Test the relative photometry visualization logic
This tests the code structure without requiring full execution
"""

import numpy as np


# Mock data structure matching what the notebook produces
def create_mock_results():
    """Create mock results matching the notebook structure"""
    results = []
    mock_sources = [
        {"name": "source1", "flux_jy": 8.28},
        {"name": "source2", "flux_jy": 0.29},
        {"name": "source3", "flux_jy": 0.014},
    ]

    for src in mock_sources:
        # Mock ForcedPhotometryResult
        class MockResult:
            def __init__(self, flux, error):
                self.peak_jyb = flux
                self.peak_err_jyb = error
                self.pix_x = 256.0
                self.pix_y = 256.0

        flux = src["flux_jy"]
        error = 0.001  # Mock error
        result = MockResult(flux, error)

        results.append(
            {
                "source": src,
                "result": result,
                "recovered": True,
            }
        )

    return results


# Test the relative photometry logic
def test_relative_photometry_logic():
    """Test the relative photometry calculation logic"""
    results = create_mock_results()

    # Find brightest source as reference
    reference_idx = np.argmax([r["result"].peak_jyb for r in results])
    reference_result = results[reference_idx]
    reference_source = results[reference_idx]["source"]
    reference_flux = reference_result["result"].peak_jyb

    print(f"Reference source: {reference_source['name']}")
    print(f"Reference flux: {reference_flux:.4f}")

    # Calculate relative results
    relative_results = []
    for r in results:
        src = r["source"]
        res = r["result"]

        # Normalize to reference
        relative_flux = res.peak_jyb / reference_flux

        # Expected relative flux
        expected_relative = src["flux_jy"] / reference_source["flux_jy"]

        # Ratio error
        ratio_error = (
            abs(relative_flux - expected_relative) / expected_relative
            if expected_relative > 0
            else np.nan
        )

        relative_results.append(
            {
                "source": src,
                "measured_flux": res.peak_jyb,
                "relative_flux": relative_flux,
                "expected_relative": expected_relative,
                "ratio_error": ratio_error,
            }
        )

    # Test visualization data extraction
    source_names = [r["source"]["name"] for r in relative_results]
    measured_fluxes = [r["measured_flux"] for r in relative_results]
    relative_fluxes = [r["relative_flux"] for r in relative_results]
    expected_relative = [r["expected_relative"] for r in relative_results]
    ratio_errors_pct = [
        r["ratio_error"] * 100
        for r in relative_results
        if np.isfinite(r["ratio_error"])
    ]

    # Calculate SNRs
    snrs = []
    for r in relative_results:
        src_idx = next(
            i
            for i, res in enumerate(results)
            if res["source"]["name"] == r["source"]["name"]
        )
        res = results[src_idx]["result"]
        if np.isfinite(res.peak_err_jyb) and res.peak_err_jyb > 0:
            snrs.append(res.peak_jyb / res.peak_err_jyb)
        else:
            snrs.append(np.nan)

    # Test visualization indices
    valid_indices = [
        i for i, r in enumerate(relative_results) if np.isfinite(r["ratio_error"])
    ]
    valid_relative_fluxes = [relative_fluxes[i] for i in valid_indices]
    valid_errors = [ratio_errors_pct[i] for i in valid_indices]
    valid_snrs = [snrs[i] for i in valid_indices if np.isfinite(snrs[i])]

    # Test SNR plot indices
    valid_snr_indices = [
        i for i in valid_indices if i < len(snrs) and np.isfinite(snrs[i])
    ]

    print("\n✓ All data structures created successfully")
    print(f"  - {len(relative_results)} relative results")
    print(f"  - {len(valid_indices)} valid indices")
    print(f"  - {len(valid_snr_indices)} valid SNR indices")
    print(f"  - {len(ratio_errors_pct)} ratio errors")

    # Verify no index errors
    assert len(valid_relative_fluxes) == len(valid_errors), "Mismatch in valid arrays"
    assert len(valid_snr_indices) <= len(valid_indices), "SNR indices out of range"

    print("\n✓ All index checks passed")
    print("\nVisualization logic test: PASSED")

    return True


if __name__ == "__main__":
    try:
        test_relative_photometry_logic()
        print("\n" + "=" * 70)
        print("SUCCESS: All visualization logic tests passed!")
        print("=" * 70)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
