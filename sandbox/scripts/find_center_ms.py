import os
import numpy as np
from astropy.coordinates import SkyCoord, Angle, match_coordinates_sky
import astropy.units as u
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft
from casatools import componentlist, msmetadata

# Path to the measurement set
ms_path = '/data/jfaber/nsfrb_cand/msdir/2025_01_30T03h_15m_45m_avg/2025-01-30T03:27:35_ra063.212_dec+69.005_avg.ms'

# Open the measurement set
msmd = msmetadata()
msmd.open(ms_path)

# Get the total number of fields
num_fields = msmd.nfields()

# Retrieve phase centers for all fields
phase_centers = []
for field_id in range(num_fields):
    pc = msmd.phasecenter(field_id)
    ra = pc['m0']['value']  # RA in radians
    dec = pc['m1']['value']  # Dec in radians
    phase_centers.append((ra, dec))

# Convert to degrees for easier interpretation
phase_centers_deg = [(np.degrees(ra), np.degrees(dec)) for ra, dec in phase_centers]

# Calculate the geometric mean center (central coordinate)
center_ra = np.mean([coord[0] for coord in phase_centers_deg])
center_dec = np.mean([coord[1] for coord in phase_centers_deg])

coord = SkyCoord(ra=center_ra * u.deg, dec=center_dec * u.deg, frame='icrs')
ra_hms = coord.ra.to_string(unit=u.hour, sep=':')
dec_dms = coord.dec.to_string(unit=u.deg, sep=':')

print(f"RA (HMS): {ra_hms}")
print(f"Dec (DMS): {dec_dms}")