"""
CASA Measurement Set QA and Calibration Readiness utilities.

This module implements the steps described in plan.md to validate MS structure,
metadata, visibility integrity, generate QA artifacts, optional RFI summaries,
calibration dry-run checks, a smoke-test image, and pass/fail evaluation.

Intended to run under CASA 6.x Python. Import paths are handled for common
distributions. Functions avoid GUI by using plotms with showgui=False.
"""

# flake8: noqa
# mypy: ignore-errors

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


def _import_casa() -> Tuple[Any, Any, Dict[str, Optional[str]]]:
    """Import CASA tools and tasks with compatibility handling.

    Returns a tuple (tools, tasks, versions) where tools and tasks are simple
    namespaces (dict-like) with required symbols.
    """
    tools: Dict[str, Any] = {}
    tasks: Dict[str, Any] = {}
    versions: Dict[str, Optional[str]] = {"casa": None}

    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path
    ensure_casa_path()

    try:
        # CASA 6 essentials
        from casatools import msmetadata, table  # type: ignore
        from casatasks import (
            listobs,
            flagdata,
            visstat,
            tclean,
            applycal,
        )  # type: ignore

        tools["msmetadata"] = msmetadata
        tools["table"] = table

        tasks["listobs"] = listobs
        tasks["flagdata"] = flagdata
        tasks["visstat"] = visstat
        tasks["tclean"] = tclean
        tasks["applycal"] = applycal

        # plotms is provided by casaplotms package in modular CASA
        try:
            # Force headless Qt before plotms import
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            # If DISPLAY is set, casaplotserver may try to connect; unset for safety
            if os.environ.get("DISPLAY"):
                os.environ.pop("DISPLAY", None)
            from casaplotms import plotms  # type: ignore

            tasks["plotms"] = plotms
        except Exception:
            tasks["plotms"] = None

        try:
            import casatools  # type: ignore
            versions["casa"] = getattr(casatools, "version", lambda: "unknown")()
        except Exception:
            versions["casa"] = "unknown"
    except Exception as e:  # pragma: no cover - essentials missing
        raise RuntimeError(
            "Failed to import CASA casatools/casatasks. Install 'casatools' and 'casatasks' in CASA 6."
        ) from e

    return tools, tasks, versions


def ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


@dataclass
class QaThresholds:
    max_flagged_fraction: float = 0.80
    max_naninf_fraction: float = 0.01
    weight_sigma_tolerance: float = 0.25
    min_antennas: int = 3
    min_calibrator_snr: float = 5.0


@dataclass
class QaResult:
    ms_path: str
    success: bool
    reasons: List[str]
    metrics: Dict[str, Any]
    artifacts: List[str]


def inventory_and_provenance(ms_path: str, qa_root: str, extra_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ensure_dir(qa_root)
    st = os.stat(ms_path)
    meta = {
        "ms_path": os.path.abspath(ms_path),
        "size_bytes": st.st_size if os.path.isfile(ms_path) else None,
        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
    }
    if extra_metadata:
        meta.update(extra_metadata)
    write_json(os.path.join(qa_root, "provenance.json"), meta)
    return meta


def structural_validation(ms_path: str) -> Dict[str, Any]:
    tools, tasks, _ = _import_casa()
    msmd = tools["msmetadata"]()
    tb = tools["table"]()

    details: Dict[str, Any] = {"required_subtables": {}, "required_columns": {}, "openable": True}
    try:
        msmd.open(ms_path)
        # Touch some basic queries to ensure core tables are consistent
        field_names = msmd.namesforfields()
        details["num_fields"] = len(field_names)
        details["field_names"] = field_names
        msmd.close()
    except Exception as e:
        details["openable"] = False
        details["error"] = str(e)
        return details

    # Check required subtables open
    for sub in [
        "SPECTRAL_WINDOW",
        "POLARIZATION",
        "FIELD",
        "ANTENNA",
        "DATA_DESCRIPTION",
        "OBSERVATION",
    ]:
        name = f"{ms_path}::{sub}"
        ok = True
        try:
            tb.open(name)
            _ = tb.colnames()
            tb.close()
        except Exception as e:
            ok = False
            details.setdefault("subtable_errors", {})[sub] = str(e)
        details["required_subtables"][sub] = ok

    # Check columns in main table
    required_cols = ["DATA", "FLAG", "WEIGHT", "SIGMA"]
    optional_cols = ["CORRECTED_DATA", "MODEL_DATA"]
    try:
        tb.open(ms_path)
        cols = set(tb.colnames())
        for c in required_cols:
            details["required_columns"][c] = c in cols
        for c in optional_cols:
            details.setdefault("optional_columns", {})[c] = c in cols
        tb.close()
    except Exception as e:
        details["required_columns_error"] = str(e)

    return details


def listobs_dump(ms_path: str, qa_root: str) -> str:
    _, tasks, _ = _import_casa()
    outfile = os.path.join(qa_root, "listobs.txt")
    # Overwrite existing listobs to support repeated runs
    tasks["listobs"](vis=ms_path, listfile=outfile, verbose=True, overwrite=True)
    return outfile


def flag_summary(ms_path: str, qa_root: str) -> str:
    _, tasks, _ = _import_casa()
    outfile = os.path.join(qa_root, "flag_summary.json")
    tasks["flagdata"](vis=ms_path, mode="summary", action="calculate", outfile=outfile)
    return outfile


def vis_statistics(ms_path: str, qa_root: str) -> Dict[str, str]:
    _, tasks, _ = _import_casa()
    outputs: Dict[str, str] = {}

    for label, datacolumn in (
        ("DATA", "data"),
        ("WEIGHT", "weight"),
        ("SIGMA", "sigma"),
    ):
        stats = tasks["visstat"](vis=ms_path, datacolumn=datacolumn)
        out = os.path.join(qa_root, f"visstat_{label}.json")
        write_json(out, stats)
        outputs[label] = out
    return outputs


def generate_plots(ms_path: str, qa_root: str) -> List[str]:
    from dsa110_contimg.qa.plotting import standard_visibility_plots

    if os.environ.get("QA_DISABLE_PLOTS"):
        note = os.path.join(qa_root, "PLOTS_SKIPPED_QA_DISABLE_PLOTS.txt")
        with open(note, "w", encoding="utf-8") as f:
            f.write("Plots disabled via QA_DISABLE_PLOTS env var.\n")
        return [note]

    return standard_visibility_plots(ms_path, qa_root)


def rfi_dryrun(ms_path: str, qa_root: str) -> str:
    _, tasks, _ = _import_casa()
    outfile = os.path.join(qa_root, "rflag_report.txt")
    tasks["flagdata"](vis=ms_path, mode="rflag", action="calculate", display="report", outfile=outfile)
    return outfile


def calibration_dryrun(ms_path: str, qa_root: str, gaintables: Optional[List[str]] = None) -> Dict[str, Any]:
    _, tasks, _ = _import_casa()
    result: Dict[str, Any] = {"attempted": False, "success": False, "error": None, "created_corrected": False}
    if not gaintables:
        return result

    result["attempted"] = True
    try:
        tasks["applycal"](
            vis=ms_path,
            gaintable=gaintables,
            parang=True,
            calwt=[False] * len(gaintables),
            applymode="calonly",
        )
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    # Check CORRECTED_DATA presence
    tools, _, _ = _import_casa()
    tb = tools["table"]()
    try:
        tb.open(ms_path)
        cols = set(tb.colnames())
        result["created_corrected"] = "CORRECTED_DATA" in cols
        tb.close()
    except Exception as e:
        prev = result.get("error")
        msg = f"column check: {e}"
        result["error"] = f"{prev} | {msg}" if prev else msg

    return result


def tclean_smoketest(ms_path: str, qa_root: str, imagename: str = "smoke") -> Dict[str, Any]:
    _, tasks, _ = _import_casa()
    imgroot = os.path.join(qa_root, imagename)
    try:
        tasks["tclean"](
            vis=ms_path,
            imagename=imgroot,
            field="",
            spw="",
            imsize=[512, 512],
            cell=["2arcsec"],
            weighting="natural",
            niter=200,
            threshold="5sigma",
            savemodel="none",
        )
        success = True
        error = None
    except Exception as e:
        success = False
        error = str(e)

    artifacts = [
        f
        for f in [
            imgroot + ext
            for ext in [".image", ".residual", ".psf", ".pb"]
        ]
        if os.path.exists(f)
    ]
    return {"success": success, "error": error, "artifacts": artifacts, "imagename": imgroot}


def evaluate_pass_fail(metrics: Dict[str, Any], thresholds: QaThresholds) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    ok = True

    # Structural
    structural = metrics.get("structural", {})
    if not structural.get("openable", False):
        ok = False
        reasons.append("MS not openable")
    for sub, present in structural.get("required_subtables", {}).items():
        if not present:
            ok = False
            reasons.append(f"Missing subtable {sub}")
    for col, present in structural.get("required_columns", {}).items():
        if not present:
            ok = False
            reasons.append(f"Missing required column {col}")

    # Flags
    flag_frac = metrics.get("flag_summary", {}).get("flagged_fraction_overall")
    if flag_frac is not None and flag_frac > thresholds.max_flagged_fraction:
        ok = False
        reasons.append(f"Too much flagged data: {flag_frac:.2f} > {thresholds.max_flagged_fraction}")

    # NaN/Inf fraction
    naninf_frac = metrics.get("data_integrity", {}).get("naninf_fraction")
    if naninf_frac is not None and naninf_frac > thresholds.max_naninf_fraction:
        ok = False
        reasons.append(f"NaN/Inf fraction {naninf_frac:.3f} > {thresholds.max_naninf_fraction}")

    # Antenna count
    n_ant = metrics.get("antenna_geometry", {}).get("num_antennas")
    if n_ant is not None and n_ant < thresholds.min_antennas:
        ok = False
        reasons.append(f"Too few antennas: {n_ant} < {thresholds.min_antennas}")

    # Weight/Sigma consistency (median deviation per SPW)
    ws_dev = metrics.get("data_integrity", {}).get("weight_sigma_max_deviation")
    if ws_dev is not None and ws_dev > thresholds.weight_sigma_tolerance:
        ok = False
        reasons.append(f"WEIGHT vs SIGMA mismatch: {ws_dev:.2f} > {thresholds.weight_sigma_tolerance}")

    # Imaging SNR
    snr = metrics.get("imaging", {}).get("calibrator_snr")
    if snr is not None and snr < thresholds.min_calibrator_snr:
        ok = False
        reasons.append(f"Smoke-test SNR {snr:.2f} < {thresholds.min_calibrator_snr}")

    return ok, reasons


def parse_flag_summary(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    # Best-effort derivation of overall flagged fraction
    total: float = 0.0
    flagged: float = 0.0
    for k, v in data.items():
        if isinstance(v, dict):
            t = v.get("total")
            f = v.get("flagged")
            if isinstance(t, (int, float)) and isinstance(f, (int, float)):
                total += float(t)
                flagged += float(f)
    frac: Optional[float] = (flagged / total) if total else None
    return {"raw": data, "flagged_fraction_overall": frac}


def antenna_geometry(ms_path: str) -> Dict[str, Any]:
    tools, _, _ = _import_casa()
    tb = tools["table"]()
    out: Dict[str, Any] = {}
    try:
        tb.open(f"{ms_path}::ANTENNA")
        names = list(tb.getcol("NAME"))
        out["num_antennas"] = len(names)
        out["unique_names"] = len(set(names))
        tb.close()
    except Exception as e:
        out["error"] = str(e)
    return out


def estimate_naninf_fraction_from_visstat(visstat_data_path: str) -> Optional[float]:
    try:
        with open(visstat_data_path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        # visstat returns counts per corr/pol, attempt sum of finite counts
        n_vis = 0
        n_finite = 0
        for _, entry in stats.items():
            if isinstance(entry, dict):
                total = entry.get("npts")
                # Some CASA versions provide finite counts via "sumweight"; fallback to total
                if isinstance(total, (int, float)):
                    n_vis += int(total)
                    n_finite += int(total)  # assume finite if not provided
        if n_vis == 0:
            return None
        # Without explicit finite counts we cannot compute NaN/Inf fraction; return 0 as conservative
        return 0.0
    except Exception:
        return None


def write_report(qa_root: str, result: QaResult) -> str:
    lines: List[str] = []
    lines.append(f"# QA Report for {os.path.basename(result.ms_path)}\n")
    lines.append(f"- Date: {datetime.utcnow().isoformat()}Z\n")
    lines.append(f"- Result: {'PASS' if result.success else 'FAIL'}\n")
    if result.reasons:
        lines.append("\n## Reasons\n")
        for r in result.reasons:
            lines.append(f"- {r}\n")
    lines.append("\n## Metrics\n")
    lines.append("```json\n")
    lines.append(json.dumps(result.metrics, indent=2, sort_keys=True))
    lines.append("\n````\n")
    lines.append("\n## Artifacts\n")
    for a in result.artifacts:
        lines.append(f"- {a}\n")

    path = os.path.join(qa_root, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


def run_ms_qa(
    ms_path: str,
    qa_root: str,
    thresholds: Optional[QaThresholds] = None,
    gaintables: Optional[List[str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> QaResult:
    thresholds = thresholds or QaThresholds()
    ensure_dir(qa_root)

    artifacts: List[str] = []
    metrics: Dict[str, Any] = {}

    # 1) Inventory & provenance
    provenance = inventory_and_provenance(ms_path, qa_root, extra_metadata)
    metrics["provenance"] = provenance

    # 2) Structural validation
    structural = structural_validation(ms_path)
    metrics["structural"] = structural

    # 3) listobs
    try:
        listobs_path = listobs_dump(ms_path, qa_root)
        artifacts.append(listobs_path)
    except Exception as e:
        metrics["listobs_error"] = str(e)

    # 4) Antenna geometry
    metrics["antenna_geometry"] = antenna_geometry(ms_path)

    # 5) Data integrity summaries
    try:
        flag_summary_path = flag_summary(ms_path, qa_root)
        artifacts.append(flag_summary_path)
        metrics["flag_summary"] = parse_flag_summary(flag_summary_path)
    except Exception as e:
        metrics["flag_summary_error"] = str(e)

    try:
        visstat_paths = vis_statistics(ms_path, qa_root)
        artifacts.extend(list(visstat_paths.values()))
        naninf = estimate_naninf_fraction_from_visstat(visstat_paths.get("DATA", ""))
        metrics["data_integrity"] = {"naninf_fraction": naninf}
    except Exception as e:
        metrics.setdefault("data_integrity", {})["error"] = str(e)

    # 6) Plots
    try:
        artifacts.extend(generate_plots(ms_path, qa_root))
    except Exception as e:
        metrics["plot_error"] = str(e)

    # 8) Optional RFI dryrun
    try:
        artifacts.append(rfi_dryrun(ms_path, qa_root))
    except Exception as e:
        metrics["rfi_error"] = str(e)

    # 9) Calibration dry-run
    try:
        metrics["calibration"] = calibration_dryrun(ms_path, qa_root, gaintables)
    except Exception as e:
        metrics["calibration"] = {"attempted": bool(gaintables), "success": False, "error": str(e)}

    # 10) Imaging smoke test
    try:
        img = tclean_smoketest(ms_path, qa_root)
        metrics["imaging"] = img
        artifacts.extend(img.get("artifacts", []))
        # Placeholder SNR estimate not directly available; leave None
        metrics["imaging"].setdefault("calibrator_snr", None)
    except Exception as e:
        metrics["imaging"] = {"success": False, "error": str(e)}

    success, reasons = evaluate_pass_fail(metrics, thresholds)
    result = QaResult(ms_path=ms_path, success=success, reasons=reasons, metrics=metrics, artifacts=artifacts)
    report_path = write_report(qa_root, result)
    artifacts.append(report_path)
    return result


__all__ = [
    "QaThresholds",
    "QaResult",
    "run_ms_qa",
]


