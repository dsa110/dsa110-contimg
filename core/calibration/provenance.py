import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict


def _default_serialize(obj: Any):
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return str(obj)


def write_provenance(obj: Dict[str, Any], output_dir: str, basename: str) -> str:
    """
    Write a structured provenance JSON alongside calibration artifacts.

    Args:
        obj: dictionary payload to serialize
        output_dir: directory to write into
        basename: base filename without extension

    Returns:
        Path to the written JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(output_dir, f"{basename}.{ts}.json")
    with open(path, "w") as f:
        json.dump(obj, f, default=_default_serialize, indent=2)
    # Keep/refresh a latest symlink for convenience
    latest = os.path.join(output_dir, f"{basename}.latest.json")
    try:
        if os.path.islink(latest) or os.path.exists(latest):
            os.remove(latest)
        os.symlink(os.path.basename(path), latest)
    except Exception:
        # Non-fatal on systems without symlink permissions
        pass
    return path


