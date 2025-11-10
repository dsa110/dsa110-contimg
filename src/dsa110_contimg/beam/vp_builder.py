import os
from typing import Optional

import numpy as np

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()

try:
    import h5py  # type: ignore[import]
except Exception:  # pragma: no cover
    h5py = None  # type: ignore[assignment]

from casatools import coordsys as _coordsys  # type: ignore[import]
from casatools import image as _image  # type: ignore[import]
from casatools import vpmanager as _vpmanager  # type: ignore[import]


def _choose_freq_index(freqs_hz: np.ndarray, prefer_hz: Optional[float]) -> int:
    if prefer_hz is None or not np.isfinite(prefer_hz):
        return int(len(freqs_hz) // 2)
    idx = int(np.argmin(np.abs(freqs_hz - float(prefer_hz))))
    return int(idx)


def _to_degrees(vals: np.ndarray, units: Optional[str]) -> np.ndarray:
    if units is None:
        return np.rad2deg(vals) if float(vals.max()) <= 2 * np.pi + 1e-6 else vals
    u = units.lower().strip()
    if u.startswith("rad"):
        return np.rad2deg(vals)
    return vals


def _make_coordsys(
    phi_deg: np.ndarray,
    theta_deg: np.ndarray,
    refcode: str = "AZEL",
) -> object:
    cs = _coordsys()
    # Build a regular grid direction coordinate centered on boresight
    nx = int(phi_deg.size)
    ny = int(theta_deg.size)
    dphi = float(phi_deg[1] - phi_deg[0]) if nx > 1 else 1.0
    dth = float(theta_deg[1] - theta_deg[0]) if ny > 1 else 1.0
    refpix = [float((nx - 1) / 2.0), float((ny - 1) / 2.0)]
    # Use a benign reference value at boresight to avoid ill-conditioned WCS
    refval = [0.0, 0.0]
    # Create a coordsys with direction+stokes+spectral, then set parameters
    cs.newcoordsys(direction=True, spectral=True, stokes=["XX", "XY", "YX", "YY"])  # type: ignore[arg-type]
    # Set units first so values are interpreted in degrees
    cs.setunits(["deg", "deg", "", "Hz"])  # dir units in degrees
    cs.setreferencecode(refcode, "direction")
    cs.setreferencepixel(refpix, "direction")
    cs.setreferencevalue(refval, "direction")
    cs.setincrement([abs(dphi), abs(dth)], "direction")
    return cs.torecord()


def build_vp_table(
    h5_path: str,
    out_vp_table: str,
    *,
    telescope: Optional[str] = None,
    prefer_freq_hz: Optional[float] = None,
) -> str:
    """Create a CASA VP table from a DSA-110 beam model H5 file.

    The H5 is expected to contain datasets:
    - 'freq_Hz' (nfreq,)
    - 'theta_pts' (ntheta,) and 'phi_pts' (nphi,)
    - 'X_pol_Efields/ephi' and 'X_pol_Efields/etheta' (nfreq, ntheta, nphi)
    - 'Y-pol_Efields/ephi' and 'Y-pol_Efields/etheta' (nfreq, ntheta, nphi)

    Mapping to feed Jones (XX, XY, YX, YY):
    - J_xx = X.ephi
    - J_xy = -X.etheta   (Y sky ≈ -e_theta)
    - J_yx = Y.ephi
    - J_yy = -Y.etheta

    Returns the path to the saved VP table.
    """
    if h5py is None:  # pragma: no cover
        raise RuntimeError("h5py is required to build VP table")
    with h5py.File(h5_path, "r") as f:
        freqs = np.asarray(f["freq_Hz"], dtype=float)
        theta = np.asarray(f["theta_pts"], dtype=float)
        phi = np.asarray(f["phi_pts"], dtype=float)
        # Units if present
        try:
            _phi = f["Metadata/theta/phi_units"][0]
            phi_units = _phi.decode() if hasattr(_phi, "decode") else str(_phi)
        except Exception:
            phi_units = None
        try:
            _ = f["Metadata/freq_units"][0]
        except Exception:
            _ = None
        idx = _choose_freq_index(freqs, prefer_freq_hz)
        # Load Jones components at the selected frequency index
        X_ephi = np.asarray(f["X_pol_Efields/ephi"][idx], dtype=np.complex128)
        X_eth = np.asarray(f["X_pol_Efields/etheta"][idx], dtype=np.complex128)
        Y_ephi = np.asarray(f["Y-pol_Efields/ephi"][idx], dtype=np.complex128)
        Y_eth = np.asarray(f["Y-pol_Efields/etheta"][idx], dtype=np.complex128)
    # Convert to degrees for coordsys (phi->Az, theta->El)
    phi_deg = _to_degrees(phi, phi_units)
    theta_deg = _to_degrees(theta, "rad")
    el_deg = 90.0 - theta_deg  # convert polar angle to elevation
    # Build Jones cube in order (XX,XY,YX,YY)
    # Input arrays are (ntheta, nphi); image expects (ny, nx, npol, nchan)
    ny, nx = X_ephi.shape
    jones = np.zeros((ny, nx, 4, 1), dtype=np.complex128)
    jones[:, :, 0, 0] = X_ephi
    jones[:, :, 1, 0] = -X_eth
    jones[:, :, 2, 0] = Y_ephi
    jones[:, :, 3, 0] = -Y_eth
    # Create an image and save as a VP table via vpmanager
    cs_rec = _make_coordsys(phi_deg, el_deg, refcode="AZEL")
    # Write a temporary complex image
    complex_img = os.path.join(os.path.dirname(out_vp_table), "dsa110_vp_tmp.im")
    if os.path.isdir(complex_img):
        import shutil

        shutil.rmtree(complex_img, ignore_errors=True)
    ia = _image()
    try:
        ia.fromarray(
            outfile=complex_img, pixels=jones, csys=cs_rec
        )  # type: ignore[arg-type]
        vp = _vpmanager()
        # Register the complex image for all antennas ('*')
        try:
            vp.setpbimage(compleximage=complex_img, antnames=["*"])
        except Exception:
            # Fallback to telescope binding if required by this CASA build
            vp.setpbimage(compleximage=complex_img, telescope=telescope or "")
        # Persist to a table on disk
        if os.path.isdir(out_vp_table):
            import shutil

            shutil.rmtree(out_vp_table, ignore_errors=True)
        vp.saveastable(out_vp_table)
        # If telescope is provided, set user default for it
        if telescope:
            try:
                vp.setuserdefault(telescope=telescope)
            except Exception:
                pass
    finally:
        try:
            ia.done()
        except Exception:
            pass
    return out_vp_table
