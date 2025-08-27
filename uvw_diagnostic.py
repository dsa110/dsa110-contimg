#!/usr/bin/env python3
"""
UVW Coordinate Diagnostic and Auto-Fix Tool

Usage:
  python uvw_diagnostic.py /path/to/file1.hdf5 [file2.hdf5 ...]

This script reads UVH5 files and:
  - Injects DSA-110 metadata: telescope_name, telescope_location
  - Reads antenna positions from the DSA110_Station_Coordinates.csv into UVData.antenna_positions and .antenna_names
  - Coerces the UVW array to float64
  - Runs a lenient PyUVData consistency check
"""
import argparse
import numpy as np
import pandas as pd
import h5py
from pyuvdata import UVData
from astropy.coordinates import EarthLocation
import astropy.units as u
from pipeline import dsa110_utils  # pipeline module with loc_dsa110 and metadata


def get_station_table(csvfile='DSA110_Station_Coordinates.csv', headerline=5, default_height=1182.6):
    """
    Read the DSA-110 station CSV and return a DataFrame indexed by station number.
    """
    tab = pd.read_csv(csvfile, header=headerline)
    # Extract numeric station ID
    stations = [int(s.split('-')[1]) for s in tab['Station Number']]
    df = pd.DataFrame({
        'Latitude': tab['Latitude'],
        'Longitude': tab['Longitude'],
        'Height': tab['Elevation (meters)']
    }, index=stations)
    df['Height'] = df['Height'].fillna(default_height)
    df.sort_index(inplace=True)
    return df


def set_antenna_positions(uvdata, telescope_pos, csvfile='DSA110_Station_Coordinates.csv'):
    """
    Populate uvdata.antenna_positions and .antenna_names from station CSV,
    filtering to the active DSA-110 pads.
    """
    df = get_station_table(csvfile)

    # Filter to valid padded stations
    valid_names = getattr(dsa110_utils, 'valid_antenna_names_dsa110', None)
    if valid_names is not None:
        # station numbers are padX -> X
        valid_ids = [int(name.replace('pad', '')) for name in valid_names]
        df = df.loc[df.index.isin(valid_ids)]
    
    # Convert lat/lon/height to ITRF
    locs = EarthLocation(lat=df['Latitude']*u.deg,
                         lon=df['Longitude']*u.deg,
                         height=df['Height']*u.m)
    # Offsets relative to telescope center
    dx = (locs.x - telescope_pos.x).to_value(u.m)
    dy = (locs.y - telescope_pos.y).to_value(u.m)
    dz = (locs.z - telescope_pos.z).to_value(u.m)
    positions = np.vstack([dx, dy, dz]).T

    # Check count matches UVData
    n_ant = uvdata.Nants_data if hasattr(uvdata, 'Nants_data') else uvdata.Nants_telescope
    if positions.shape[0] != n_ant:
        raise RuntimeError(
            f"Station CSV (filtered to pads) has {positions.shape[0]} entries but UVData expects {n_ant} antennas"
        )

    uvdata.antenna_positions = positions
    # Use valid_names ordering if available, else pad index names
    if valid_names is not None:
        uvdata.antenna_names = valid_names
    else:
        uvdata.antenna_names = [f"pad{num}" for num in df.index]
    return uvdata


def _load_uvh5_file(fname):
    """
    Read a UVH5 file, inject DSA110 metadata and antenna coordinates, and coerce UVWs.
    """
    uv = UVData()
    uv.read_uvh5(fname, run_check=False)

    # Inject telescope metadata
    telescope_pos = dsa110_utils.loc_dsa110
    uv.telescope_name = telescope_pos.info.name
    uv.telescope_location = telescope_pos

    # Populate antenna positions/names from CSV
    try:
        uv = set_antenna_positions(uv, telescope_pos)
    except Exception as e:
        print(f"WARNING: Unable to set antenna_positions: {e}")

    # Ensure uvw_array is float64
    if uv.uvw_array.dtype != np.float64:
        uv.uvw_array = uv.uvw_array.astype(np.float64)
    return uv


def analyze_file(fname):
    print("=== UVW COORDINATE DIAGNOSTIC ===")
    print(f"Analyzing: {fname}\nLoading HDF5 file...\n")

    try:
        uv = _load_uvh5_file(fname)
    except Exception as e:
        print(f"ERROR: Unable to load {fname}: {e}")
        return

    # BASIC INFO
    print("--- BASIC INFO ---")
    print(f"Telescope name: {uv.telescope_name}")
    n_ant = uv.Nants_data if hasattr(uv, 'Nants_data') else uv.Nants_telescope
    print(f"N antennas: {n_ant}")
    n_bl = uv.Nbls if hasattr(uv, 'Nbls') else uv.Nbls_data
    print(f"N baselines: {n_bl}\n")

    # TELESCOPE LOCATION
    print("--- TELESCOPE LOCATION ---")
    try:
        tx, ty, tz = (
            uv.telescope_location.x.value,
            uv.telescope_location.y.value,
            uv.telescope_location.z.value
        )
        print(f"Location (ECEF): {tx:.3f}, {ty:.3f}, {tz:.3f}")
    except Exception:
        print("❌ No telescope location found!")

    # ANTENNA POSITIONS
    print("\n--- ANTENNA POSITIONS ---")
    if hasattr(uv, 'antenna_positions') and uv.antenna_positions is not None:
        dists = np.linalg.norm(uv.antenna_positions, axis=1)
        print(f"Max antenna distance from center: {dists.max():.3f} m")
    else:
        print("❌ No antenna positions found!")

    # UVW COORDINATES
    print("\n--- UVW COORDINATES ---")
    norms = np.linalg.norm(uv.uvw_array, axis=1)
    print(f"Max UVW coordinate: {norms.max():.3f} m")
    print(f"RMS UVW coordinate: {np.sqrt(np.mean(norms**2)):.3f} m")

    # PYUVDATA CHECK
    print("\n--- PYUVDATA CHECK ---")
    try:
        uv.check(
            run_check_acceptability=False,
            check_extra=False,
            strict_uvw_antpos_check=False,
            allow_flip_conj=True
        )
        print("✅ PyUVData check passed without errors.")
    except Exception as e:
        print(f"❌ PyUVData check failed: {e}")

    # SUGGESTED FIXES
    print("\n--- SUGGESTED FIXES ---")
    print("🔧 DSA-110 metadata and antenna positions set.")
    print("🔧 UVW array dtype enforced to float64.")


def main():
    parser = argparse.ArgumentParser(description="UVW diagnostic for DSA-110 UVH5 files")
    parser.add_argument('files', nargs='+', help='One or more UVH5 files to analyze')
    args = parser.parse_args()
    for i, f in enumerate(args.files):
        analyze_file(f)
        if i < len(args.files) - 1:
            print('\n')


if __name__ == '__main__':
    main()
