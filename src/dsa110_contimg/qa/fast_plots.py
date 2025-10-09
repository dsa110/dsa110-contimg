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


def run_fast_plots(
    ms_path: str,
    *,
    output_dir: str,
    max_uv_points: int = 200_000,
    include_residual: bool = False,
) -> List[str]:
    """Generate quick QA plots and return list of artifact filenames."""
    output_dir = _ensure_dir(output_dir)
    available_columns = _available_columns(ms_path)
    extra_cols: List[str] = []
    if include_residual and "CORRECTED_DATA" in available_columns:
        extra_cols.append("CORRECTED_DATA")
        if "MODEL_DATA" in available_columns:
            extra_cols.append("MODEL_DATA")

    datasets = xds_from_ms(
        ms_path,
        chunks={"row": 50_000},
        columns=["DATA", "FLAG", "FLAG_ROW", "TIME", "UVW"] + extra_cols,
    )

    ddid_to_freq = _data_description_to_freqs(ms_path)

    time_chunks: List[np.ndarray] = []
    amp_chunks: List[np.ndarray] = []
    freq_results: List[Tuple[int, np.ndarray]] = []
    uv_u_chunks: List[np.ndarray] = []
    uv_v_chunks: List[np.ndarray] = []
    uv_amp_chunks: List[np.ndarray] = []
    resid_amp_chunks: List[np.ndarray] = []
    uv_dist_chunks: List[np.ndarray] = []

    for ds in datasets:
        amp = _mask_amplitude(ds.DATA.data, ds)
        try:
            row_amp = da.nanmean(amp, axis=(1, 2))
        except Exception:
            # Fallback when nanmean unavailable (older dask)
            valid = da.isfinite(amp)
            row_amp = da.sum(da.where(valid, amp, 0.0), axis=(1, 2)) / da.maximum(
                valid.sum(axis=(1, 2)), 1
            )
        row_amp_np = np.asarray(row_amp.compute())

        time_np = _as_numpy(ds.TIME.data)
        mask = np.isfinite(row_amp_np) & np.isfinite(time_np)
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
    )
    if artifacts:
        print("Generated fast QA artifacts:")
        for art in artifacts:
            print(f" - {art}")
    else:
        print("No fast QA artifacts generated.")


if __name__ == "__main__":  # pragma: no cover
    main()
