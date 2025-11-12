#!/usr/bin/env python
"""
Read-only scanner for incoming HDF5 files.

Policy:
- Treat the incoming directory as immutable (no writes, renames, or deletes).
- Select only files that appear stable: modified at least --min-age-min minutes ago.
- Print a JSON summary of candidates; never modify source.
"""

from __future__ import print_function
import argparse
import json
import os
import sys
import time
import fnmatch


def list_hdf5_files(root, pattern):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            if fnmatch.fnmatch(name, pattern):
                full = os.path.join(dirpath, name)
                try:
                    if os.path.isfile(full):
                        files.append(full)
                except Exception:
                    continue
    return files


def is_stable(path, min_age_seconds):
    try:
        st = os.stat(path)
    except OSError:
        return False
    age = time.time() - st.st_mtime
    return age >= float(min_age_seconds)


def isoformat_mtime(path):
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.stat(path).st_mtime))
    except Exception:
        return ""


def summarize(files):
    total = 0
    infos = []
    for p in files:
        try:
            st = os.stat(p)
        except OSError:
            continue
        total += st.st_size
        infos.append({
            "path": p,
            "size_bytes": int(st.st_size),
            "mtime_iso": isoformat_mtime(p),
        })
    infos.sort(key=lambda x: x.get("path", ""))
    return {
        "count": len(infos),
        "total_size_bytes": int(total),
        "total_size_gb": round(total / float(1024**3), 3),
        "files": infos,
    }


def main():
    ap = argparse.ArgumentParser(description="Read-only scan of incoming HDF5 files with stability guard")
    ap.add_argument("--incoming", default="/data/incoming", help="Incoming directory (read-only)")
    ap.add_argument("--pattern", default="*.hdf5", help="Glob pattern for files")
    ap.add_argument("--min-age-min", type=float, default=10.0, help="Minimum age (minutes) since last mtime to consider stable")
    ap.add_argument("--limit", type=int, default=50, help="Max files to list (after stability filter)")
    ap.add_argument("--json", action="store_true", help="Emit JSON to stdout (default)")
    args = ap.parse_args()

    incoming = args.incoming
    if not (os.path.exists(incoming) and os.path.isdir(incoming)):
        print(json.dumps({"success": False, "error": "Incoming dir not found: %s" % incoming}))
        return 2

    all_files = list_hdf5_files(incoming, args.pattern)
    min_age_seconds = float(args.min_age_min) * 60.0
    stable_files = [p for p in all_files if is_stable(p, min_age_seconds)]

    try:
        stable_files.sort(key=lambda p: (os.stat(p).st_mtime, p))
    except Exception:
        stable_files.sort()

    limited = stable_files[: max(0, int(args.limit))]

    result = {
        "success": True,
        "incoming": incoming,
        "pattern": args.pattern,
        "min_age_min": float(args.min_age_min),
        "found_total": len(all_files),
        "stable_total": len(stable_files),
        "returned": len(limited),
        "summary": summarize(limited),
        "note": "Dry-run; no modifications performed; source directory treated as immutable.",
    }

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


