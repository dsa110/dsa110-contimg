#!/opt/miniforge/envs/casa6/bin/python
"""
CLI for the calibration registry database.

Examples:
  python -m pipeline.pipeline.database.registry_cli init --db pipeline/cal_registry.sqlite3
  python -m pipeline.pipeline.database.registry_cli register-prefix \
      --db pipeline/cal_registry.sqlite3 \
      --name 2025-10-06_J1234+5678 \
      --prefix /data/ms/2025-10-06_J1234+5678 \
      --cal-field J1234+5678 --refant 23 \
      --valid-start 60295.20 --valid-end 60295.45
  python -m pipeline.pipeline.database.registry_cli active --db pipeline/cal_registry.sqlite3 --mjd 60295.30
  python -m pipeline.pipeline.database.registry_cli list-sets --db pipeline/cal_registry.sqlite3
  python -m pipeline.pipeline.database.registry_cli retire --db pipeline/cal_registry.sqlite3 --name 2025-10-06_J1234+5678
"""

import argparse
import json
from pathlib import Path
from typing import List, Optional

from . import registry


def cmd_init(args: argparse.Namespace) -> int:
    registry.ensure_db(Path(args.db))
    print(f"Initialized registry DB: {args.db}")
    return 0


def cmd_register_prefix(args: argparse.Namespace) -> int:
    rows = registry.register_set_from_prefix(
        Path(args.db),
        set_name=args.name,
        prefix=Path(args.prefix),
        cal_field=args.cal_field,
        refant=args.refant,
        valid_start_mjd=args.valid_start,
        valid_end_mjd=args.valid_end,
        status=args.status,
    )
    print(json.dumps([r.__dict__ for r in rows], indent=2))
    return 0


def cmd_active(args: argparse.Namespace) -> int:
    applylist = registry.get_active_applylist(Path(args.db), args.mjd, set_name=args.set)
    print(json.dumps({"applylist": applylist}, indent=2))
    return 0 if applylist else 1


def cmd_list_sets(args: argparse.Namespace) -> int:
    items = registry.list_sets(Path(args.db))
    print(
        json.dumps(
            [{"set": s, "rows": n, "active": a, "min_order": m} for s, n, a, m in items],
            indent=2,
        )
    )
    return 0


def cmd_retire(args: argparse.Namespace) -> int:
    registry.retire_set(Path(args.db), args.name, reason=args.reason)
    print(f"Retired set: {args.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Calibration registry CLI")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("init", help="Initialize/create the registry DB")
    sp.add_argument("--db", required=True)
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("register-prefix", help="Register a set from a filename prefix")
    sp.add_argument("--db", required=True)
    sp.add_argument("--name", required=True, help="Logical set name")
    sp.add_argument("--prefix", required=True, help="Path prefix of cal tables")
    sp.add_argument("--cal-field")
    sp.add_argument("--refant")
    sp.add_argument("--valid-start", dest="valid_start", type=float)
    sp.add_argument("--valid-end", dest="valid_end", type=float)
    sp.add_argument("--status", default="active")
    sp.set_defaults(func=cmd_register_prefix)

    sp = sub.add_parser("active", help="Get active applylist for a given MJD")
    sp.add_argument("--db", required=True)
    sp.add_argument("--mjd", type=float, required=True)
    sp.add_argument("--set", help="Restrict to a specific set name")
    sp.set_defaults(func=cmd_active)

    sp = sub.add_parser("list-sets", help="List registered calibration sets")
    sp.add_argument("--db", required=True)
    sp.set_defaults(func=cmd_list_sets)

    sp = sub.add_parser("retire", help="Retire a set (mark inactive)")
    sp.add_argument("--db", required=True)
    sp.add_argument("--name", required=True)
    sp.add_argument("--reason")
    sp.set_defaults(func=cmd_retire)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, "func"):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
