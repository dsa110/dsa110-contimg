"""
UVW geometry validation utilities.

Provides high-signal checks to build confidence that antenna positions and
resulting UVW coordinates in a Measurement Set (MS) are correct.

Usage (programmatic):
    from core.utils.uvw_validator import UVWValidator
    report = UVWValidator().validate_ms('data/ms/example.ms')

The validator is read-only and does not modify inputs.
"""

from __future__ import annotations

import os
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Tuple

import numpy as np
from pyuvdata import UVData


@dataclass
class UVWValidationThresholds:
    max_abs_delta_m: float = 0.02           # 2 cm absolute tolerance
    max_rms_delta_m: float = 0.005          # 5 mm RMS tolerance
    max_uvw_abs_m: float = 10000.0          # 10 km sanity bound
    min_autos_imag_ratio: float = 1e-12     # autos imag/real ratio should be tiny


@dataclass
class UVWValidationReport:
    success: bool
    checks: Dict[str, Any]
    warnings: List[str]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'checks': self.checks,
            'warnings': self.warnings,
            'errors': self.errors,
        }


class UVWValidator:
    def __init__(self, thresholds: Optional[UVWValidationThresholds] = None) -> None:
        self.thresholds = thresholds or UVWValidationThresholds()

    def _compute_baseline_lengths_from_positions(self, antenna_positions: np.ndarray) -> Tuple[float, float]:
        max_baseline = 0.0
        count = 0
        acc = 0.0
        n = antenna_positions.shape[0]
        for i in range(n):
            for j in range(i + 1, n):
                bl = float(np.linalg.norm(antenna_positions[j] - antenna_positions[i]))
                max_baseline = max(max_baseline, bl)
                acc += bl
                count += 1
        mean_baseline = acc / count if count else 0.0
        return mean_baseline, max_baseline

    def _summarize_complex_autos(self, uv: UVData) -> Dict[str, Any]:
        # autos are where ant1 == ant2
        ant1 = uv.ant_1_array
        ant2 = uv.ant_2_array
        mask = ant1 == ant2
        if not np.any(mask):
            return {'present': False}
        data = uv.data_array[mask]
        real = np.abs(np.real(data))
        imag = np.abs(np.imag(data))
        max_imag = float(np.max(imag)) if imag.size else 0.0
        ratio = float(np.max(np.divide(imag, np.maximum(real, 1e-30)))) if imag.size else 0.0
        return {
            'present': True,
            'max_imag': max_imag,
            'max_imag_over_real': ratio,
        }

    def validate_ms(self, ms_path: str) -> UVWValidationReport:
        checks: Dict[str, Any] = {}
        warnings: List[str] = []
        errors: List[str] = []

        if not os.path.isdir(ms_path):
            return UVWValidationReport(False, checks, warnings, [f"MS path is not a directory: {ms_path}"])

        # Load MS via PyUVData
        uv = UVData()
        uv.read_ms(ms_path, ignore_single_chan=True)

        checks['n_antennas'] = int(getattr(uv, 'Nants_telescope', 0))
        checks['n_baselines'] = int(getattr(uv, 'Nbls', 0))
        checks['n_times'] = int(getattr(uv, 'Ntimes', 0))
        checks['n_freqs'] = int(getattr(uv, 'Nfreqs', 0))

        # Sanity on UVW magnitude
        uvw_abs = np.abs(uv.uvw_array)
        uvw_abs_max = float(np.max(uvw_abs)) if uvw_abs.size else 0.0
        uvw_abs_rms = float(np.sqrt(np.mean(uv.uvw_array ** 2))) if uv.uvw_array.size else 0.0
        checks['uvw_abs_max_m'] = uvw_abs_max
        checks['uvw_abs_rms_m'] = uvw_abs_rms
        if uvw_abs_max > self.thresholds.max_uvw_abs_m:
            warnings.append(f"UVW absolute exceeds {self.thresholds.max_uvw_abs_m} m (max={uvw_abs_max:.3f})")

        # Baseline stats from antenna positions
        antenna_positions = getattr(uv.telescope, 'antenna_positions', None)
        if antenna_positions is None:
            errors.append('Missing uv.telescope.antenna_positions')
        else:
            mean_bl, max_bl = self._compute_baseline_lengths_from_positions(antenna_positions)
            checks['antenna_mean_baseline_m'] = float(mean_bl)
            checks['antenna_max_baseline_m'] = float(max_bl)

        # Recompute UVW from antenna positions and compare
        uvw_before = uv.uvw_array.copy()
        uv.set_uvws_from_antenna_positions(update_vis=False)
        delta = uv.uvw_array - uvw_before
        delta_norm = np.linalg.norm(delta, axis=1) if delta.size else np.array([0.0])
        delta_abs_max = float(np.max(delta_norm)) if delta_norm.size else 0.0
        delta_rms = float(np.sqrt(np.mean(delta_norm ** 2))) if delta_norm.size else 0.0
        checks['uvw_delta_max_m'] = delta_abs_max
        checks['uvw_delta_rms_m'] = delta_rms

        if delta_abs_max > self.thresholds.max_abs_delta_m:
            errors.append(f"Max |Δuvw| {delta_abs_max:.4f} m > {self.thresholds.max_abs_delta_m} m")
        if delta_rms > self.thresholds.max_rms_delta_m:
            errors.append(f"RMS |Δuvw| {delta_rms:.4f} m > {self.thresholds.max_rms_delta_m} m")

        # Autos must be effectively real
        autos = self._summarize_complex_autos(uv)
        checks['autos'] = autos
        if autos.get('present'):
            if autos.get('max_imag_over_real', 0.0) > self.thresholds.min_autos_imag_ratio:
                warnings.append(
                    f"Auto-correlation imag/real ratio high: {autos['max_imag_over_real']:.2e}"
                )

        # Optional: simple temporal sanity – times should be non-decreasing
        if hasattr(uv, 'time_array') and uv.time_array.size:
            if np.any(np.diff(uv.time_array) < -1e-9):
                errors.append('time_array is not monotonic non-decreasing')

        success = len(errors) == 0
        return UVWValidationReport(success, checks, warnings, errors)


