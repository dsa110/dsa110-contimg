"""
Lightweight Measurement Set QA plots using dask-ms and matplotlib.

Generates quick diagnostic plots without invoking CASA (`plotms`) so we can
inspect a freshly written MS in seconds:
  * Amplitude vs time (per baseline average)
  * Amplitude vs frequency (per SPW)
  * UV-plane coverage coloured by amplitude
  * Optional residual amplitude vs UV distance when CORRECTED/MODEL data exist

Usage (CLI):
    python -m dsa110_contimg.qa.fast_plots --ms <path/to.ms> --output-dir state/qa
"""

import argparse
import logging
import os
from typing import Dict, Iterable, List, Optional, Tuple

import dask.array as da
import matplotlib
import numpy as np
from casacore.tables import table
from daskms import xds_from_ms

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt  # noqa  E402  (after setting backend)


LOG = logging.getLogger(__name__)


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _num_antennas(ms_path: str) -> int:
    try:
        with table(f"{ms_path}::ANTENNA", readonly=True) as ant_tab:
            return ant_tab.nrows()
    except Exception:  # pragma: no cover - best effort
        return 0


def _antenna_positions(ms_path: str) -> Optional[np.ndarray]:
    """Return antenna ITRF positions (N x 3) in meters, or None."""
    try:
        with table(f"{ms_path}::ANTENNA", readonly=True) as ant_tab:
            pos = ant_tab.getcol("POSITION")
            return np.asarray(pos)
    except Exception:  # pragma: no cover - best effort
        return None


def _data_description_to_freqs(ms_path: str) -> Dict[int, np.ndarray]:
    """
    Map DATA_DESC_ID -> CHAN_FREQ (Hz) using casacore tables.

    Returns an empty dict if the tables cannot be read.
    """
    try:
        dd_tab = table(f"{ms_path}::DATA_DESCRIPTION", readonly=True)
        spw_ids = dd_tab.getcol("SPECTRAL_WINDOW_ID")
        dd_tab.close()

        spw_tab = table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True)
        chan_freq = spw_tab.getcol("CHAN_FREQ")
        spw_tab.close()
    except Exception as exc:  # pragma: no cover - best effort
        LOG.debug("Unable to read spectral window information: %s", exc)
        return {}

    mapping: Dict[int, np.ndarray] = {}
    for ddid, spw in enumerate(spw_ids):
        if 0 <= spw < len(chan_freq):
            mapping[ddid] = chan_freq[spw]
    return mapping


def _available_columns(ms_path: str) -> set:
    try:
        with table(ms_path, readonly=True) as t:
            return set(t.colnames())
    except Exception:
        return set()


def _mask_amplitude(data: da.Array, dataset) -> da.Array:
    """Return amplitude array with flag/flag_row set to NaN."""
    amp = da.abs(da.asarray(data))
    if "FLAG" in dataset:
        amp = da.where(da.asarray(dataset.FLAG.data), np.nan, amp)
    if "FLAG_ROW" in dataset:
        flag_row = da.asarray(dataset.FLAG_ROW.data)
        amp = da.where(flag_row[:, None, None], np.nan, amp)
    return amp


def _as_numpy(array) -> np.ndarray:
    """Convert dask or numpy array-like to numpy ndarray."""
    if hasattr(array, "compute"):
        array = array.compute()
    return np.asarray(array)


def _concatenate(parts: Iterable[np.ndarray]) -> np.ndarray:
    arrays = [p for p in parts if p.size]
    return np.concatenate(arrays) if arrays else np.empty((0,), dtype=float)


def _phase_pages_per_antenna(
    ms_path: str,
    *,
    output_dir: str,
    refant: int,
    panels_per_page: int = 25,
    rows_per_spw: int = 50000,
    unwrap_phase: bool = False,
) -> List[str]:
    """Generate per‑antenna phase vs frequency pages across the full band.

    Accumulates per‑SPW phase(f) samples for baselines involving the reference
    antenna, then concatenates/sorts by frequency to plot a continuous curve
    per antenna.
    """
    artifacts: List[str] = []
    ddid_to_freq = _data_description_to_freqs(ms_path)
    dsets = xds_from_ms(ms_path, chunks={"row": 100000}, columns=["DATA", "FLAG", "ANTENNA1", "ANTENNA2"])

    # Gather per-antenna samples across SPWs
    ant_series: Dict[int, List[Tuple[np.ndarray, np.ndarray]]] = {}
    for ds in dsets:
        ddid = ds.attrs.get("DATA_DESC_ID")
        freq = ddid_to_freq.get(ddid)
        if freq is None or freq.size == 0:
            continue
        chan_x = freq / 1e9
        ant1 = _as_numpy(ds.ANTENNA1.data).astype(int)
        ant2 = _as_numpy(ds.ANTENNA2.data).astype(int)
        sel = (ant1 == refant) | (ant2 == refant)
        idx = np.nonzero(sel)[0]
        if idx.size == 0:
            continue
        if idx.size > rows_per_spw:
            rng = np.random.default_rng(42)
            idx = rng.choice(idx, size=rows_per_spw, replace=False)
        other = np.where(ant1[idx] == refant, ant2[idx], ant1[idx])
        conj_mask = (ant2[idx] == refant)
        data_sub = ds.DATA.data[idx, :, :].compute()
        flag_sub = ds.FLAG.data[idx, :, :].compute()
        with np.errstate(divide="ignore", invalid="ignore"):
            ph = data_sub / np.maximum(np.abs(data_sub), 1e-12)
        ph[flag_sub] = np.nan
        ph[conj_mask, :, :] = np.conj(ph[conj_mask, :, :])

        for ant in np.unique(other):
            rmask = (other == ant)
            if not np.any(rmask):
                continue
            ph_ant = ph[rmask, :, :]
            real = np.nanmean(np.real(ph_ant), axis=(0, 2))
            imag = np.nanmean(np.imag(ph_ant), axis=(0, 2))
            phase = np.arctan2(imag, real)
            ant_series.setdefault(int(ant), []).append((chan_x.copy(), phase.copy()))

    if not ant_series:
        return artifacts

    ncols = 5
    nrows = max(1, panels_per_page // ncols)
    panels = nrows * ncols
    ants = sorted(ant_series.keys())
    page = 0
    for start in range(0, len(ants), panels):
        end = min(start + panels, len(ants))
        subset = ants[start:end]
        fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 3.2, nrows * 2.5), squeeze=False)
        for i, ant in enumerate(subset):
            ax = axes[i // ncols][i % ncols]
            segs = ant_series[ant]
            # Concatenate and sort by frequency
            x = np.concatenate([s[0] for s in segs])
            y = np.concatenate([s[1] for s in segs])
            order = np.argsort(x)
            x = x[order]
            y = y[order]
            if unwrap_phase:
                try:
                    y_proc = np.unwrap(y)
                except Exception:
                    y_proc = y
            else:
                y_proc = y
            y_unw = np.degrees(y_proc)
            ax.plot(x, y_unw, linewidth=0.8)
            ax.set_xlabel("GHz")
            ax.set_ylabel("deg")
            ax.set_title(f"ant {ant}", fontsize=9)
            ax.grid(True, alpha=0.3)
        for j in range((end - start), panels):
            axes[j // ncols][j % ncols].axis("off")
        plt.tight_layout()
        out = os.path.join(output_dir, f"phase_per_antenna_page{page}.png")
        plt.savefig(out, dpi=130)
        plt.close(fig)
        artifacts.append(os.path.basename(out))
        page += 1
    return artifacts


def run_fast_plots(
    ms_path: str,
    *,
    output_dir: str,
    max_uv_points: int = 200_000,
    include_residual: bool = False,
    phase_per_antenna: bool = False,
    refant_auto: Optional[int] = None,
    unwrap_phase: bool = False,
) -> List[str]:
    """Generate quick QA plots and return list of artifact filenames."""
    output_dir = _ensure_dir(output_dir)
    available_columns = _available_columns(ms_path)
    extra_cols: List[str] = []
    if include_residual and "CORRECTED_DATA" in available_columns:
        extra_cols.append("CORRECTED_DATA")
        if "MODEL_DATA" in available_columns:
            extra_cols.append("MODEL_DATA")
    extra_cols.extend([col for col in ("ANTENNA1", "ANTENNA2") if col in available_columns])

    datasets = xds_from_ms(
        ms_path,
        chunks={"row": 50_000},
        columns=["DATA", "FLAG", "FLAG_ROW", "TIME", "UVW"] + extra_cols,
    )

    ddid_to_freq = _data_description_to_freqs(ms_path)

    n_ant = _num_antennas(ms_path)
    sum_amp = np.zeros(n_ant, dtype=float)
    sum_amp_sq = np.zeros(n_ant, dtype=float)
    count_amp = np.zeros(n_ant, dtype=float)
    total_rows = np.zeros(n_ant, dtype=float)
    flagged_rows = np.zeros(n_ant, dtype=float)
    sum_cos = np.zeros(n_ant, dtype=float)
    sum_sin = np.zeros(n_ant, dtype=float)
    phase_counts = np.zeros(n_ant, dtype=float)

    time_chunks: List[np.ndarray] = []
    amp_chunks: List[np.ndarray] = []
    freq_results: List[Tuple[int, np.ndarray]] = []
    phase_results: List[Tuple[int, np.ndarray]] = []
    uv_u_chunks: List[np.ndarray] = []
    uv_v_chunks: List[np.ndarray] = []
    uv_amp_chunks: List[np.ndarray] = []
    resid_amp_chunks: List[np.ndarray] = []
    uv_dist_chunks: List[np.ndarray] = []
    phase_chunk_data: List[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []

    for ds in datasets:
        amp = _mask_amplitude(ds.DATA.data, ds)
        row_vis = da.nanmean(ds.DATA.data, axis=(1, 2))
        row_vis_np = np.asarray(row_vis.compute())
        row_amp_np = np.abs(row_vis_np)

        time_np = _as_numpy(ds.TIME.data)
        mask = np.isfinite(row_amp_np) & np.isfinite(time_np)
        ant1 = ant2 = None
        if "ANTENNA1" in ds and "ANTENNA2" in ds:
            ant1 = _as_numpy(ds.ANTENNA1.data).astype(int)
            ant2 = _as_numpy(ds.ANTENNA2.data).astype(int)
        flag_row_np = _as_numpy(ds.FLAG_ROW.data).astype(float)
        if ant1 is not None:
            total_rows += np.bincount(ant1, np.ones_like(ant1, dtype=float), minlength=n_ant)
            total_rows += np.bincount(ant2, np.ones_like(ant2, dtype=float), minlength=n_ant)
            flagged_rows += np.bincount(ant1, flag_row_np, minlength=n_ant)
            flagged_rows += np.bincount(ant2, flag_row_np, minlength=n_ant)

            ant1_valid = ant1[mask]
            ant2_valid = ant2[mask]
            amp_values = row_amp_np[mask]
            sum_amp += np.bincount(ant1_valid, amp_values, minlength=n_ant)
            sum_amp += np.bincount(ant2_valid, amp_values, minlength=n_ant)
            sum_amp_sq += np.bincount(ant1_valid, amp_values ** 2, minlength=n_ant)
            sum_amp_sq += np.bincount(ant2_valid, amp_values ** 2, minlength=n_ant)
            counts = np.ones_like(amp_values)
            count_amp += np.bincount(ant1_valid, counts, minlength=n_ant)
            count_amp += np.bincount(ant2_valid, counts, minlength=n_ant)

        vis_valid = row_vis_np[mask]
        nonzero = np.abs(vis_valid) > 0
        if ant1 is not None and np.any(nonzero):
            ant1_phase = ant1_valid[nonzero]
            ant2_phase = ant2_valid[nonzero]
            phasor = vis_valid[nonzero] / np.abs(vis_valid[nonzero])
            cos = np.real(phasor)
            sin = np.imag(phasor)
            sum_cos += np.bincount(ant1_phase, cos, minlength=n_ant)
            sum_cos += np.bincount(ant2_phase, cos, minlength=n_ant)
            sum_sin += np.bincount(ant1_phase, sin, minlength=n_ant)
            sum_sin += np.bincount(ant2_phase, sin, minlength=n_ant)
            ones = np.ones_like(cos)
            phase_counts += np.bincount(ant1_phase, ones, minlength=n_ant)
            phase_counts += np.bincount(ant2_phase, ones, minlength=n_ant)
            phase_chunk_data.append(
                (
                    time_np[mask][nonzero],
                    ant1_phase,
                    ant2_phase,
                    phasor,
                )
            )
        time_chunks.append(time_np[mask])
        amp_chunks.append(row_amp_np[mask])

        # frequency summary per channel / SPW
        try:
            chan_amp = da.nanmean(amp, axis=(0, 2)).compute()
        except Exception:
            valid = da.isfinite(amp)
            chan_amp = (
                da.sum(da.where(valid, amp, 0.0), axis=(0, 2))
                / da.maximum(valid.sum(axis=(0, 2)), 1)
            ).compute()
        ddid = ds.attrs.get("DATA_DESC_ID")
        freq_results.append((ddid if ddid is not None else -1, np.asarray(chan_amp)))

        # phase vs frequency (circular mean over rows and correlations)
        try:
            data_arr = da.asarray(ds.DATA.data)
            # unit phasor; avoid divide by zero
            phasor = data_arr / da.maximum(da.abs(data_arr), 1e-12)
            # mask flagged by propagating NaNs from amplitude mask
            phasor = da.where(da.isfinite(amp), phasor, da.nan)
            real = da.real(phasor)
            imag = da.imag(phasor)
            real_mean = da.nanmean(real, axis=(0, 2))
            imag_mean = da.nanmean(imag, axis=(0, 2))
        except Exception:
            # manual nanmean
            data_arr = da.asarray(ds.DATA.data)
            phasor = data_arr / da.maximum(da.abs(data_arr), 1e-12)
            phasor = da.where(da.isfinite(amp), phasor, da.nan)
            real = da.real(phasor)
            imag = da.imag(phasor)
            valid_r = da.isfinite(real)
            valid_i = da.isfinite(imag)
            real_mean = da.sum(da.where(valid_r, real, 0.0), axis=(0, 2)) / da.maximum(
                valid_r.sum(axis=(0, 2)), 1
            )
            imag_mean = da.sum(da.where(valid_i, imag, 0.0), axis=(0, 2)) / da.maximum(
                valid_i.sum(axis=(0, 2)), 1
            )
        chan_phase = np.arctan2(_as_numpy(imag_mean), _as_numpy(real_mean))
        phase_results.append((ddid if ddid is not None else -1, chan_phase))

        # UV scatter
        uvw = _as_numpy(ds.UVW.data)
        if uvw.size:
            uv_u_chunks.append(uvw[mask, 0])
            uv_v_chunks.append(uvw[mask, 1])
            uv_amp_chunks.append(row_amp_np[mask])

        # Residual amplitudes (optional)
        if include_residual and hasattr(ds, "CORRECTED_DATA"):
            corr = _mask_amplitude(ds.CORRECTED_DATA.data, ds)
            if hasattr(ds, "MODEL_DATA"):
                model = da.asarray(ds.MODEL_DATA.data)
                if "FLAG" in ds:
                    model = da.where(da.asarray(ds.FLAG.data), np.nan, model)
                if "FLAG_ROW" in ds:
                    flag_row = da.asarray(ds.FLAG_ROW.data)
                    model = da.where(flag_row[:, None, None], np.nan, model)
                resid = da.abs(corr - model)
            else:
                resid = corr
            resid_row = da.nanmean(resid, axis=(1, 2)).compute()
            resid_np = np.asarray(resid_row)
            mask_resid = np.isfinite(resid_np) & np.isfinite(uvw[:, 0])
            resid_amp_chunks.append(resid_np[mask_resid])
            uv_dist_chunks.append(np.sqrt(uvw[mask_resid, 0] ** 2 + uvw[mask_resid, 1] ** 2))

    artifacts: List[str] = []

    # Amplitude vs Time
    times = _concatenate(time_chunks)
    amps = _concatenate(amp_chunks)
    if times.size and amps.size:
        order = np.argsort(times)
        times = times[order]
        amps = amps[order]
        times_rel_min = (times - times.min()) / 60.0  # seconds -> minutes
        plt.figure(figsize=(9, 4))
        plt.scatter(times_rel_min, amps, s=1, alpha=0.6, c=amps, cmap="viridis")
        plt.xlabel("Time since start (minutes)")
        plt.ylabel("Mean baseline amplitude")
        plt.title("Amplitude vs Time")
        plt.tight_layout()
        fname = os.path.join(output_dir, "amp_vs_time_fast.png")
        plt.savefig(fname, dpi=150)
        plt.close()
        artifacts.append(os.path.basename(fname))

    # Amplitude vs Frequency
    if freq_results:
        plt.figure(figsize=(9, 4))
        plotted = False
        for ddid, chan_amp in freq_results:
            if chan_amp.size == 0 or np.all(np.isnan(chan_amp)):
                continue
            freq = ddid_to_freq.get(ddid)
            if freq is not None and freq.size == chan_amp.size:
                x = freq / 1e9  # GHz
                label = f"DDID {ddid}"
                plt.plot(x, chan_amp, linewidth=1.0, label=label)
                plt.xlabel("Frequency (GHz)")
            else:
                x = np.arange(chan_amp.size)
                plt.plot(x, chan_amp, linewidth=1.0, label=f"DDID {ddid}")
                plt.xlabel("Channel")
            plotted = True
        if plotted:
            plt.ylabel("Mean amplitude")
            plt.title("Amplitude vs Frequency / Channel")
            if len(freq_results) > 1:
                plt.legend(fontsize="small", ncol=2)
            plt.tight_layout()
            fname = os.path.join(output_dir, "amp_vs_freq_fast.png")
            plt.savefig(fname, dpi=150)
            plt.close()
            artifacts.append(os.path.basename(fname))
        else:
            plt.close()

    # Phase vs Frequency (circular mean)
    if phase_results:
        plt.figure(figsize=(9, 4))
        plotted = False
        for ddid, chan_phase in phase_results:
            if chan_phase.size == 0 or np.all(np.isnan(chan_phase)):
                continue
            # optional unwrap to show slopes
            if unwrap_phase:
                try:
                    phase_unw = np.unwrap(chan_phase)
                except Exception:
                    phase_unw = chan_phase
            else:
                phase_unw = chan_phase
            freq = ddid_to_freq.get(ddid)
            if freq is not None and freq.size == phase_unw.size:
                x = freq / 1e9
                plt.plot(x, np.degrees(phase_unw), linewidth=1.0, label=f"DDID {ddid}")
                plt.xlabel("Frequency (GHz)")
            else:
                x = np.arange(phase_unw.size)
                plt.plot(x, np.degrees(phase_unw), linewidth=1.0, label=f"DDID {ddid}")
                plt.xlabel("Channel")
            plotted = True
        if plotted:
            plt.ylabel("Phase (deg)" + (" (unwrapped)" if unwrap_phase else ""))
            plt.title("Phase vs Frequency / Channel")
            if len(phase_results) > 1:
                plt.legend(fontsize="small", ncol=2)
            plt.tight_layout()
            fname = os.path.join(output_dir, "phase_vs_freq_fast.png")
            plt.savefig(fname, dpi=150)
            plt.close()
            artifacts.append(os.path.basename(fname))
        else:
            plt.close()

    # UV-plane scatter (sampled)
    u = _concatenate(uv_u_chunks)
    v = _concatenate(uv_v_chunks)
    amp_uv = _concatenate(uv_amp_chunks)
    mask_uv = np.isfinite(u) & np.isfinite(v) & np.isfinite(amp_uv)
    u, v, amp_uv = u[mask_uv], v[mask_uv], amp_uv[mask_uv]
    if u.size:
        sample_size = min(max_uv_points, u.size)
        if sample_size < u.size:
            rng = np.random.default_rng(0)
            idx = rng.choice(u.size, size=sample_size, replace=False)
            u, v, amp_uv = u[idx], v[idx], amp_uv[idx]

        # Convert to kilo-lambda if average frequency known
        avg_freq = None
        if ddid_to_freq:
            freq_vals = [np.nanmean(freq) for freq in ddid_to_freq.values() if freq.size]
            if freq_vals:
                avg_freq = float(np.nanmean(freq_vals))
        if avg_freq:
            c = 299_792_458.0
            scale = avg_freq / c / 1e3  # metres -> kilo-lambda
            u_plot = u * scale
            v_plot = v * scale
            xlabel = "u (kλ)"
            ylabel = "v (kλ)"
        else:
            u_plot = u / 1e3
            v_plot = v / 1e3
            xlabel = "u (km)"
            ylabel = "v (km)"

        plt.figure(figsize=(6, 6))
        sc = plt.scatter(u_plot, v_plot, c=amp_uv, s=1, cmap="viridis", alpha=0.5)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title("UV Coverage (coloured by amplitude)")
        plt.colorbar(sc, label="Mean amplitude")
        plt.tight_layout()
        fname = os.path.join(output_dir, "uv_plane_fast.png")
        plt.savefig(fname, dpi=150)
        plt.close()
        artifacts.append(os.path.basename(fname))

    # Residual amplitude vs UV distance
    if include_residual and resid_amp_chunks:
        resid_amp = _concatenate(resid_amp_chunks)
        uv_dist = _concatenate(uv_dist_chunks)
        mask_resid = np.isfinite(resid_amp) & np.isfinite(uv_dist)
        resid_amp, uv_dist = resid_amp[mask_resid], uv_dist[mask_resid]
        if resid_amp.size:
            sample_size = min(max_uv_points, resid_amp.size)
            if sample_size < resid_amp.size:
                rng = np.random.default_rng(1)
                idx = rng.choice(resid_amp.size, size=sample_size, replace=False)
                resid_amp = resid_amp[idx]
                uv_dist = uv_dist[idx]
            plt.figure(figsize=(8, 4))
            plt.scatter(uv_dist / 1e3, resid_amp, s=1, alpha=0.5, c=resid_amp, cmap="plasma")
            plt.xlabel("UV distance (km)")
            plt.ylabel("Residual amplitude")
            plt.title("Residual amplitude vs UV distance")
            plt.tight_layout()
            fname = os.path.join(output_dir, "residual_uv_fast.png")
            plt.savefig(fname, dpi=150)
            plt.close()
            artifacts.append(os.path.basename(fname))

    # Per-antenna metrics
    ant_ids = np.arange(n_ant)
    valid = count_amp > 0
    mean_amp = np.full(n_ant, np.nan)
    mean_amp[valid] = np.divide(sum_amp[valid], count_amp[valid], where=count_amp[valid] > 0)
    var_amp = np.full(n_ant, np.nan)
    var_amp[valid] = np.maximum(
        np.divide(sum_amp_sq[valid], count_amp[valid], where=count_amp[valid] > 0) - mean_amp[valid] ** 2,
        0.0,
    )

    flagged_frac = np.full(n_ant, np.nan)
    nonzero_total = total_rows > 0
    flagged_frac[nonzero_total] = np.divide(
        flagged_rows[nonzero_total], total_rows[nonzero_total], where=total_rows[nonzero_total] > 0
    )

    phase_std_deg = np.full(n_ant, np.nan)
    mean_phase = np.full(n_ant, np.nan)
    coherence = np.zeros(n_ant, dtype=float)
    valid_phase = phase_counts > 0
    if np.any(valid_phase):
        sum_cos_valid = sum_cos[valid_phase]
        sum_sin_valid = sum_sin[valid_phase]
        counts_valid = phase_counts[valid_phase]
        R = np.sqrt(sum_cos_valid ** 2 + sum_sin_valid ** 2)
        coherence_vals = np.clip(np.divide(R, counts_valid, where=counts_valid > 0), 1e-6, 1.0)
        phase_std = np.sqrt(-2.0 * np.log(coherence_vals))
        phase_std_deg[valid_phase] = np.degrees(phase_std)
        mean_phase[valid_phase] = np.arctan2(sum_sin_valid, sum_cos_valid)
        coherence[valid_phase] = coherence_vals

    if n_ant and np.any(count_amp > 0):
        fig, axes = plt.subplots(4, 1, figsize=(10, 12), sharex=True)
        axes[0].bar(ant_ids, np.nan_to_num(mean_amp, nan=0.0))
        axes[0].set_ylabel("Mean amp")
        axes[0].set_title("Per-antenna metrics")

        axes[1].bar(ant_ids, np.nan_to_num(phase_std_deg, nan=0.0))
        axes[1].set_ylabel("Phase σ (deg)")

        axes[2].bar(ant_ids, np.nan_to_num(flagged_frac, nan=0.0))
        axes[2].set_ylabel("Flagged frac")
        axes[2].set_ylim(0, 1)

        axes[3].bar(ant_ids, np.nan_to_num(var_amp, nan=0.0))
        axes[3].set_ylabel("Amp variance")
        axes[3].set_xlabel("Antenna ID")

        for ax in axes:
            ax.grid(True, axis="y", alpha=0.3)

        plt.tight_layout()
        fname = os.path.join(output_dir, "per_antenna_metrics_fast.png")
        plt.savefig(fname, dpi=150)
        plt.close()
        artifacts.append(os.path.basename(fname))

        # Phase σ sorted bar chart
        order = np.argsort(np.nan_to_num(phase_std_deg, nan=np.inf))
        plt.figure(figsize=(10, 6))
        plt.bar(range(n_ant), np.nan_to_num(phase_std_deg[order], nan=0.0), color="steelblue")
        plt.xticks(range(n_ant), ant_ids[order], rotation=90)
        plt.ylabel("Phase σ (deg)")
        plt.title("Per-antenna phase stability (sorted)")
        plt.tight_layout()
        fname = os.path.join(output_dir, "phase_sigma_sorted_fast.png")
        plt.savefig(fname, dpi=150)
        plt.close()
        artifacts.append(os.path.basename(fname))

        # Coherence vs flagged fraction scatter
        plt.figure(figsize=(7, 6))
        plt.scatter(coherence, flagged_frac, c=mean_amp, cmap="viridis", s=30, edgecolor="k", linewidths=0.3)
        plt.xlabel("Phase coherence (R)")
        plt.ylabel("Flagged fraction")
        plt.title("Coherence vs. flagged fraction")
        cbar = plt.colorbar()
        cbar.set_label("Mean amplitude")
        for ant in range(n_ant):
            if np.isfinite(coherence[ant]) and np.isfinite(flagged_frac[ant]):
                plt.text(coherence[ant], flagged_frac[ant], str(ant), fontsize=6, ha="center", va="bottom")
        plt.tight_layout()
        fname = os.path.join(output_dir, "coherence_vs_flagged_fast.png")
        plt.savefig(fname, dpi=150)
        plt.close()
        artifacts.append(os.path.basename(fname))

        # Polar plot for top antennas by coherence
        if np.any(valid_phase):
            top = np.argsort(-coherence[valid_phase])
            idx_map = np.flatnonzero(valid_phase)[top[: min(20, top.size)]]
            polar_fig, polar_ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(6, 6))
            polar_ax.set_title("Top antenna phasors (by coherence)")
            for ant in idx_map:
                theta = mean_phase[ant]
                r = coherence[ant]
                color = plt.cm.viridis(1.0 - np.nan_to_num(phase_std_deg[ant], nan=180.0) / 180.0)
                polar_ax.arrow(theta, 0, 0, r, width=0.01, color=color, alpha=0.8, length_includes_head=True)
                polar_ax.text(theta, r + 0.03, str(ant), fontsize=7, ha="center", va="bottom")
            polar_ax.set_rlim(0, max(0.3, float(np.nanmax(coherence[idx_map]) * 1.1 if idx_map.size else 1.0)))
            polar_ax.grid(True, alpha=0.3)
            fname = os.path.join(output_dir, "per_antenna_phase_polar_fast.png")
            polar_fig.savefig(fname, dpi=150, bbox_inches="tight")
            plt.close(polar_fig)
            artifacts.append(os.path.basename(fname))

        # Phase heatmap over time bins
        if phase_chunk_data and times.size:
            num_bins = min(24, max(4, int(np.ceil(times.size / 20000))))
            t_min = times.min()
            t_max = times.max() if times.max() > t_min else t_min + 1.0
            bin_edges = np.linspace(t_min, t_max, num_bins + 1)
            bin_cos = np.zeros((num_bins, n_ant))
            bin_sin = np.zeros((num_bins, n_ant))
            bin_counts = np.zeros((num_bins, n_ant))
            for chunk_time, chunk_ant1, chunk_ant2, chunk_phasor in phase_chunk_data:
                bin_idx = np.clip(np.digitize(chunk_time, bin_edges) - 1, 0, num_bins - 1)
                cos = np.real(chunk_phasor)
                sin = np.imag(chunk_phasor)
                np.add.at(bin_cos, (bin_idx, chunk_ant1), cos)
                np.add.at(bin_cos, (bin_idx, chunk_ant2), cos)
                np.add.at(bin_sin, (bin_idx, chunk_ant1), sin)
                np.add.at(bin_sin, (bin_idx, chunk_ant2), sin)
                ones = np.ones_like(cos)
                np.add.at(bin_counts, (bin_idx, chunk_ant1), ones)
                np.add.at(bin_counts, (bin_idx, chunk_ant2), ones)

            with np.errstate(divide="ignore", invalid="ignore"):
                R = np.sqrt(bin_cos**2 + bin_sin**2)
                coh = np.clip(np.divide(R, bin_counts, where=bin_counts > 0), 1e-6, 1.0)
                phase_sigma = np.degrees(np.sqrt(-2.0 * np.log(coh)))
                phase_sigma[bin_counts == 0] = np.nan

            plt.figure(figsize=(10, 5))
            extent = [0, (t_max - t_min) / 60.0, 0, n_ant]
            vmax = np.nanmax(phase_sigma) if np.isfinite(np.nanmax(phase_sigma)) else 90.0
            plt.imshow(
                phase_sigma.T,
                origin="lower",
                aspect="auto",
                extent=extent,
                cmap="magma",
                vmin=0,
                vmax=max(10.0, min(120.0, vmax)),
            )
            plt.colorbar(label="Phase σ (deg)")
            plt.xlabel("Time since start (minutes)")
            plt.ylabel("Antenna ID")
            plt.title("Phase stability heatmap")
            fname = os.path.join(output_dir, "phase_heatmap_fast.png")
            plt.savefig(fname, dpi=150, bbox_inches="tight")
            plt.close()
            artifacts.append(os.path.basename(fname))

        # Recommend reference antenna via composite score and save ranking (single computation)
        positions = _antenna_positions(ms_path)
        center_factor = np.ones(n_ant, dtype=float)
        if positions is not None and positions.size:
            xy = positions[:, :2]
            center = np.nanmean(xy, axis=0)
            r = np.linalg.norm(xy - center, axis=1)
            r_max = np.nanmax(r) if np.isfinite(np.nanmax(r)) and np.nanmax(r) > 0 else 1.0
            center_factor = np.clip(1.0 - (r / r_max), 0.0, 1.0)

        # Normalizations and composite score
        amp_norm = np.nan_to_num(mean_amp / np.nanmax(mean_amp) if np.nanmax(mean_amp) > 0 else mean_amp, nan=0.0)
        coh = np.nan_to_num(coherence, nan=0.0)
        good_frac = np.nan_to_num(1.0 - flagged_frac, nan=0.0)
        phase_sigma_safe = np.nan_to_num(phase_std_deg, nan=180.0)
        stability = 1.0 / (1.0 + (phase_sigma_safe / 45.0))
        center_f = np.nan_to_num(center_factor, nan=0.5)

        score = (amp_norm ** 0.5) * (coh ** 1.0) * (good_frac ** 1.0) * (stability ** 1.0) * (center_f ** 0.5)
        score[np.isnan(score)] = 0.0
        ranking_idx = np.argsort(-score)

        # Save JSON/CSV once
        ranking = []
        for idx in ranking_idx:
            ranking.append(
                {
                    "antenna_id": int(idx),
                    "score": float(score[idx]),
                    "mean_amp": float(np.nan_to_num(mean_amp[idx], nan=0.0)),
                    "phase_sigma_deg": float(np.nan_to_num(phase_std_deg[idx], nan=180.0)),
                    "coherence": float(np.nan_to_num(coherence[idx], nan=0.0)),
                    "flagged_fraction": float(np.nan_to_num(flagged_frac[idx], nan=1.0)),
                    "center_factor": float(center_f[idx]),
                }
            )
        rec = ranking[0] if ranking else None
        import json
        rec_path = os.path.join(output_dir, "refant_ranking.json")
        with open(rec_path, "w", encoding="utf-8") as f:
            json.dump({"recommended": rec, "ranking": ranking}, f, indent=2)
        artifacts.append(os.path.basename(rec_path))

        csv_path = os.path.join(output_dir, "refant_ranking.csv")
        try:
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("antenna_id,score,mean_amp,phase_sigma_deg,coherence,flagged_fraction,center_factor\n")
                for row in ranking:
                    f.write(
                        f"{row['antenna_id']},{row['score']:.6f},{row['mean_amp']:.6f},{row['phase_sigma_deg']:.3f},"
                        f"{row['coherence']:.6f},{row['flagged_fraction']:.6f},{row['center_factor']:.6f}\n"
                    )
            artifacts.append(os.path.basename(csv_path))
        except Exception:
            pass

        # Optional per‑antenna phase pages
        if phase_per_antenna:
            chosen = refant_auto if refant_auto is not None else (rec["antenna_id"] if rec else 0)
            phase_dir = _ensure_dir(os.path.join(output_dir, "phase_per_antenna"))
            artifacts.extend(
                _phase_pages_per_antenna(
                    ms_path, output_dir=phase_dir, refant=int(chosen), panels_per_page=25, unwrap_phase=unwrap_phase
                )
            )

    return artifacts


def _configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Fast MS QA plots (no CASA).")
    parser.add_argument("--ms", required=True, help="Path to the Measurement Set (.ms)")
    parser.add_argument(
        "--output-dir",
        default="qa_fast",
        help="Directory for output PNGs (default: ./qa_fast)",
    )
    parser.add_argument(
        "--max-uv-points",
        type=int,
        default=200_000,
        help="Maximum UV samples for scatter (default: 200000)",
    )
    parser.add_argument(
        "--include-residual",
        action="store_true",
        help="Plot residual amplitude vs UV distance if CORRECTED/MODEL columns exist",
    )
    parser.add_argument(
        "--phase-per-antenna",
        action="store_true",
        help="Generate per-antenna phase-vs-frequency pages using auto-picked refant",
    )
    parser.add_argument(
        "--unwrap-phase",
        action="store_true",
        help="Unwrap phases along frequency for phase plots",
    )
    parser.add_argument(
        "--refant",
        type=int,
        default=None,
        help="Override auto-picked reference antenna ID for per-antenna phase pages",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    artifacts = run_fast_plots(
        args.ms,
        output_dir=args.output_dir,
        max_uv_points=args.max_uv_points,
        include_residual=args.include_residual,
        phase_per_antenna=args.phase_per_antenna,
        refant_auto=args.refant,
        unwrap_phase=args.unwrap_phase,
    )
    if artifacts:
        print("Generated fast QA artifacts:")
        for art in artifacts:
            print(f" - {art}")
    else:
        print("No fast QA artifacts generated.")


if __name__ == "__main__":  # pragma: no cover
    main()
