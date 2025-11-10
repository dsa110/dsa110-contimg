"""
Quicklook QA utilities based on shadeMS and ragavi-vis.

These helpers mirror the converter's optional quicklook flow but can be
invoked independently to avoid rerunning the full UVH5→MS conversion.
"""

import argparse
import logging
import os
import sys
import subprocess
import time
from typing import List, Optional

from .fast_plots import run_fast_plots


LOG = logging.getLogger(__name__)


def _resolve_state_dir(state_dir: Optional[str]) -> str:
    return os.path.abspath(state_dir or os.getenv("PIPELINE_STATE_DIR", "state"))


def _record_artifacts(stem: str, out_dir: str, artifacts: List[str]) -> None:
    """Persist artifact metadata into the products SQLite database (best effort)."""
    if not artifacts:
        return
    try:
        from sqlite3 import connect

        db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = connect(db_path)
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS qa_artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    UNIQUE(group_id, name)
                )
                """
            )
            for artifact in artifacts:
                path = os.path.join(out_dir, artifact)
                try:
                    ts = os.path.getmtime(path)
                except Exception:
                    ts = time.time()
                conn.execute(
                    "INSERT OR REPLACE INTO qa_artifacts(group_id,name,path,created_at) VALUES (?,?,?,?)",
                    (stem, artifact, path, ts),
                )
    except Exception as exc:  # pragma: no cover - best effort
        LOG.debug("QA DB record skipped: %s", exc)


def run_shadems_quicklooks(
    ms_path: str,
    *,
    state_dir: Optional[str] = None,
    resid: bool = False,
    max_plots: int = 4,
    timeout: int = 600,
) -> List[str]:
    """
    Generate quicklook plots using shadeMS for a Measurement Set.

    Returns the list of artifact filenames created (relative to the output directory).
    """
    state_dir = _resolve_state_dir(state_dir)
    base = os.path.basename(ms_path)
    stem = base[:-3] if base.endswith(".ms") else base
    out_dir = os.path.join(state_dir, "qa", stem)
    os.makedirs(out_dir, exist_ok=True)

    plots = [
        ("TIME", "DATA:amp", "amp_vs_time"),
        ("FREQ", "DATA:amp", "amp_vs_freq"),
        ("u", "v", "uv_plane"),
    ]
    if resid:
        plots.append(("uv", "CORRECTED_DATA-MODEL_DATA:amp", "residual_uv_amp"))

    env = os.environ.copy()
    env.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    # Ensure shadems is locatable even if the current PATH was stripped.
    python_bin = os.path.dirname(sys.executable)
    current_path = env.get("PATH", "")
    if python_bin and python_bin not in current_path.split(os.pathsep):
        env["PATH"] = (
            python_bin + os.pathsep + current_path if current_path else python_bin
        )

    generated: List[str] = []
    ran = 0
    for x, y, label in plots:
        if ran >= max_plots:
            break
        png_template = f"{label}"
        cmd = [
            "shadems",
            "--xaxis",
            x,
            "--yaxis",
            y,
            "--png",
            png_template,
            "--dir",
            ".",
            ms_path,
        ]
        try:
            LOG.debug("Running shadeMS: %s", " ".join(cmd))
            proc = subprocess.run(
                cmd,
                cwd=out_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            candidate = os.path.join(out_dir, f"{png_template}.png")
            if os.path.exists(candidate):
                generated.append(os.path.basename(candidate))
                ran += 1
            else:
                LOG.warning(
                    "shadeMS did not produce expected artifact %s; stderr tail: %s",
                    candidate,
                    proc.stderr.splitlines()[-5:] if proc.stderr else "n/a",
                )
        except FileNotFoundError:
            raise RuntimeError("shadems not found on PATH")
        except Exception as exc:  # pragma: no cover - log and continue
            LOG.warning("shadeMS plot (%s,%s) failed: %s", x, y, exc)

    LOG.info("shadeMS artifacts (%d) saved to %s", len(generated), out_dir)
    _record_artifacts(stem, out_dir, generated)
    return generated


def run_ragavi_vis(
    ms_path: str,
    *,
    state_dir: Optional[str] = None,
    timeout: int = 600,
) -> Optional[str]:
    """
    Generate a ragavi-vis HTML inspector for a Measurement Set.

    Returns the artifact filename if successful.
    """
    state_dir = _resolve_state_dir(state_dir)
    base = os.path.basename(ms_path)
    stem = base[:-3] if base.endswith(".ms") else base
    out_dir = os.path.join(state_dir, "qa", stem)
    os.makedirs(out_dir, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    python_bin = os.path.dirname(sys.executable)
    current_path = env.get("PATH", "")
    if python_bin and python_bin not in current_path.split(os.pathsep):
        env["PATH"] = (
            python_bin + os.pathsep + current_path if current_path else python_bin
        )
    html_base = f"ragavi_{stem}"
    html_name = f"{html_base}.html"
    cmd = [
        "ragavi-vis",
        "--ms",
        ms_path,
        "--xaxis",
        "time",
        "--yaxis",
        "amplitude",
        "--htmlname",
        html_base,
    ]
    try:
        LOG.debug("Running ragavi-vis: %s", " ".join(cmd))
        proc = subprocess.run(
            cmd,
            cwd=out_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        raise RuntimeError("ragavi-vis not found on PATH")
    except Exception as exc:  # pragma: no cover
        LOG.warning("ragavi-vis failed: %s", exc)
        return None

    artifact_path = os.path.join(out_dir, html_name)
    if not os.path.exists(artifact_path):
        LOG.warning(
            "ragavi-vis did not produce expected artifact %s; stderr tail: %s",
            artifact_path,
            proc.stderr.splitlines()[-5:] if proc.stderr else "n/a",
        )
        return None

    _record_artifacts(stem, out_dir, [html_name])
    LOG.info("ragavi-vis artifact saved to %s", os.path.join(out_dir, html_name))
    return html_name


def run_quicklooks(
    ms_path: str,
    *,
    state_dir: Optional[str] = None,
    shadems: bool = True,
    shadems_resid: bool = False,
    shadems_max: int = 4,
    shadems_timeout: int = 600,
    ragavi: bool = False,
    ragavi_timeout: int = 600,
    fast_plots: bool = False,
    fast_include_residual: bool = False,
) -> List[str]:
    """Convenience helper to run shadeMS and ragavi quicklooks in one call."""
    artifacts: List[str] = []
    resolved_state = _resolve_state_dir(state_dir)
    stem = os.path.basename(ms_path)
    stem = stem[:-3] if stem.endswith(".ms") else stem

    if shadems:
        artifacts.extend(
            run_shadems_quicklooks(
                ms_path,
                state_dir=resolved_state,
                resid=shadems_resid,
                max_plots=shadems_max,
                timeout=shadems_timeout,
            )
        )
    if ragavi:
        html = run_ragavi_vis(
            ms_path,
            state_dir=resolved_state,
            timeout=ragavi_timeout,
        )
        if html:
            artifacts.append(html)
    if fast_plots:
        fast_dir = os.path.join(resolved_state, "qa", stem)
        fast_artifacts = run_fast_plots(
            ms_path,
            output_dir=fast_dir,
            include_residual=fast_include_residual,
        )
        if fast_artifacts:
            _record_artifacts(stem, fast_dir, fast_artifacts)
            artifacts.extend(fast_artifacts)
    return artifacts


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate shadeMS / ragavi quicklooks for an existing MS."
    )
    parser.add_argument("--ms", required=True, help="Path to the Measurement Set")
    parser.add_argument(
        "--state-dir",
        default=None,
        help="Base state directory for QA artifacts (default: PIPELINE_STATE_DIR or 'state')",
    )
    parser.add_argument(
        "--no-shadems",
        action="store_true",
        help="Skip shadeMS plots",
    )
    parser.add_argument(
        "--shadems-resid",
        action="store_true",
        help="Include residual plot (CORRECTED_DATA-MODEL_DATA:amp) when running shadeMS",
    )
    parser.add_argument(
        "--shadems-max",
        type=int,
        default=4,
        help="Maximum number of shadeMS plots to attempt (default: 4)",
    )
    parser.add_argument(
        "--shadems-timeout",
        type=int,
        default=600,
        help="Per-plot timeout in seconds for shadeMS (default: 600)",
    )
    parser.add_argument(
        "--ragavi",
        action="store_true",
        help="Generate ragavi-vis HTML inspector",
    )
    parser.add_argument(
        "--ragavi-timeout",
        type=int,
        default=600,
        help="Timeout in seconds for ragavi-vis (default: 600)",
    )
    parser.add_argument(
        "--fast-plots",
        action="store_true",
        help="Generate lightweight matplotlib quicklook plots",
    )
    parser.add_argument(
        "--fast-include-residual",
        action="store_true",
        help="Include residual amplitude plot when fast plots are enabled",
    )

    args = parser.parse_args(argv)

    artifacts = run_quicklooks(
        args.ms,
        state_dir=args.state_dir,
        shadems=not args.no_shadems,
        shadems_resid=args.shadems_resid,
        shadems_max=args.shadems_max,
        shadems_timeout=args.shadems_timeout,
        ragavi=args.ragavi,
        ragavi_timeout=args.ragavi_timeout,
        fast_plots=args.fast_plots,
        fast_include_residual=args.fast_include_residual,
    )
    if artifacts:
        print("Artifacts:")
        for artifact in artifacts:
            print(f" - {artifact}")
    else:
        print("No artifacts generated.")


if __name__ == "__main__":  # pragma: no cover
    main()
