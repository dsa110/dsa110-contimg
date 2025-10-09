"""
CLI driver for CASA MS QA and Calibration Readiness.

Usage examples:
  python -m qa.run_ms_qa --ms /path/to/file.ms
  python -m qa.run_ms_qa --ms-dir /data/sets --qa-root /data/dsa110-contimg/qa
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:
    # When installed/used as a package
    from dsa110_contimg.qa.casa_ms_qa import run_ms_qa, QaThresholds
except Exception:
    # When running directly from the qa/ directory
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    from casa_ms_qa import run_ms_qa, QaThresholds  # type: ignore


def find_ms_in_dir(ms_dir: str) -> List[str]:
    paths: List[str] = []
    # Basic heuristics: *.ms directories and files ending with .ms
    for pattern in ["*.ms", "**/*.ms"]:
        paths.extend(glob.glob(os.path.join(ms_dir, pattern), recursive=True))
    # De-duplicate and keep only existing
    uniq = []
    seen = set()
    for p in paths:
        ap = os.path.abspath(p)
        if ap not in seen and os.path.exists(ap):
            uniq.append(ap)
            seen.add(ap)
    return uniq


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run CASA MS QA")
    parser.add_argument("--ms", action="append", help="Path to a .ms (repeat)")
    parser.add_argument("--ms-dir", help="Directory to search for .ms files")
    parser.add_argument(
        "--qa-root",
        default="/data/dsa110-contimg/qa",
        help="Root directory to write QA artifacts",
    )
    parser.add_argument(
        "--gaintable",
        action="append",
        help="Calibration table(s) to attempt applycal (repeat)",
    )
    parser.add_argument(
        "--max-flagged",
        type=float,
        default=0.80,
        help="Max acceptable flagged fraction (0-1)",
    )
    parser.add_argument(
        "--max-naninf",
        type=float,
        default=0.01,
        help="Max acceptable NaN/Inf fraction (0-1)",
    )
    parser.add_argument(
        "--min-antennas",
        type=int,
        default=3,
        help="Minimum number of antennas",
    )
    parser.add_argument(
        "--min-snr",
        type=float,
        default=5.0,
        help="Minimum SNR in smoke-test image",
    )

    args = parser.parse_args(argv)

    ms_list: List[str] = []
    if args.ms:
        ms_list.extend(args.ms)
    if args.ms_dir:
        ms_list.extend(find_ms_in_dir(args.ms_dir))
    ms_list = [os.path.abspath(p) for p in ms_list]

    if not ms_list:
        print("No measurement sets provided", file=sys.stderr)
        return 2

    thresholds = QaThresholds(
        max_flagged_fraction=args.max_flagged,
        max_naninf_fraction=args.max_naninf,
        min_antennas=args.min_antennas,
        min_calibrator_snr=args.min_snr,
    )

    overall: Dict[str, Any] = {"results": [], "pass": True}

    for ms_path in ms_list:
        ms_name = os.path.basename(ms_path).rstrip(os.sep)
        qa_root = os.path.join(args.qa_root, ms_name)
        result = run_ms_qa(
            ms_path=ms_path,
            qa_root=qa_root,
            thresholds=thresholds,
            gaintables=args.gaintable,
            extra_metadata=None,
        )
        overall["results"].append(
            {
                "ms_path": result.ms_path,
                "success": result.success,
                "reasons": result.reasons,
                "artifacts": result.artifacts,
            }
        )
        if not result.success:
            overall["pass"] = False

        result_json_path = os.path.join(qa_root, "result.json")
        with open(result_json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "success": result.success,
                    "reasons": result.reasons,
                    "metrics": result.metrics,
                    "artifacts": result.artifacts,
                },
                f,
                indent=2,
                sort_keys=True,
            )

    # Write overall summary at root
    os.makedirs(args.qa_root, exist_ok=True)
    summary_path = os.path.join(args.qa_root, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(overall, f, indent=2, sort_keys=True)

    return 0 if overall.get("pass", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())


