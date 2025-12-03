
# --- CASA log directory setup ---
# Ensure CASA logs go to centralized directory, not CWD
import os as _os
try:
    from pathlib import Path as _Path
    _REPO_ROOT = _Path(__file__).resolve().parents[3]
    _sys_path_entry = str(_REPO_ROOT / 'backend' / 'src')
    import sys as _sys
    if _sys_path_entry not in _sys.path:
        _sys.path.insert(0, _sys_path_entry)
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    _casa_log_dir = derive_casa_log_dir()
    _os.makedirs(str(_casa_log_dir), exist_ok=True)
    _os.chdir(str(_casa_log_dir))
except (ImportError, OSError):
    pass  # Best effort - CASA logs may go to CWD
# --- End CASA log directory setup ---

import casatools
import numpy as np
import os
import sys


def check_ms(ms_path):
    ms = casatools.ms()
    try:
        ms.open(ms_path)
    except Exception as e:
        print(f"Failed to open MS {ms_path}: {e}")
        return

    # Number of fields
    summary = ms.summary()
    nfields = summary.get('nfields', 0)
    print(f"MS: {ms_path}")
    print(f"Number of fields: {nfields}")

    # Number of SPWs
    spwinfo = ms.getspectralwindowinfo()
    nspw = len(spwinfo)
    print(f"Number of SPWs: {nspw}")

    # Check if uncalibrated (CORRECTED_DATA all zeros or missing)
    try:
        tb = casatools.table()
        tb.open(ms_path)
        try:
            colnames = tb.colnames()
        finally:
            tb.close()
    except Exception as e:
        print(f"Error getting colnames: {e}")
        colnames = []

    if 'CORRECTED_DATA' not in colnames:
        print("CORRECTED_DATA column missing - uncalibrated")
        is_uncalib = True
        mean_abs = 0.0
    else:
        try:
            # Sample first 1000 rows to check
            data = ms.getdata(['corrected_data'], start=0, nrow=1000)
            corrected_data = data['corrected_data']
            mean_abs = np.mean(np.abs(corrected_data))
            is_uncalib = np.allclose(mean_abs, 0.0, atol=1e-10)
            print(f"Uncalibrated (CORRECTED_DATA zeros): {is_uncalib} (mean abs of sample: {mean_abs})")
        except Exception as e:
            print(f"Error checking CORRECTED_DATA: {e}")
            is_uncalib = False
            mean_abs = -1

    # Phase centers
    try:
        tb = casatools.table()
        tb.open(ms_path + '/FIELD')
        try:
            phase_dirs = tb.getcol('PHASE_DIR')
            for field_id in range(nfields):
                ra = phase_dirs[0, 0, field_id]  # Assuming num_poly=1
                dec = phase_dirs[1, 0, field_id]
                print(f"Field {field_id}: PHASE_DIR RA={np.degrees(ra):.6f} deg, Dec={np.degrees(dec):.6f} deg")
        finally:
            tb.close()
    except Exception as e:
        print(f"Error getting PHASE_DIR: {e}")

    ms.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_ms_properties.py <ms_dir>")
        sys.exit(1)

    ms_dir = sys.argv[1]
    for item in sorted(os.listdir(ms_dir)):
        full_path = os.path.join(ms_dir, item)
        if os.path.isdir(full_path) and item.endswith('.ms'):
            check_ms(full_path)
            print("\n")
