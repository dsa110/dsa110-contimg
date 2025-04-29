from casatools import table
import numpy as np
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u

# Open the component list
tb = table()
tb.open('/data/jfaber/dsa110-contimg/sandbox/2025-02-14_1459+716_JF/nvss_top10_225p303_71p740.cl')

# Get the data from the component list
flux = tb.getcol('Flux')  # Flux values (Jy)
direction = tb.getcol('Reference_Direction')  # Source coordinates (radians)

# Close the table
tb.close()

# Sum the Stokes I flux for each source
stokes_I_flux = flux[0, :]  # Assuming Stokes I is the first row

# Find the index of the brightest source
brightest_index = np.argmax(stokes_I_flux)

# Get the data for the brightest source
brightest_flux = np.real(stokes_I_flux[brightest_index])
brightest_direction = direction[:, brightest_index]  # Coordinates in radians

# Convert direction from radians to degrees and sexagesimal format
ra_rad, dec_rad = brightest_direction

rad2deg = lambda x: ((x * 180.0 / np.pi) + 360) % 360 
ra_deg = rad2deg(ra_rad) * u.deg
dec_deg = rad2deg(dec_rad) * u.deg
source_coords = SkyCoord(ra_deg, dec_deg, frame='icrs')

# Convert RA and Dec to sexagesimal format
ra_hms = source_coords.ra.to_string(unit=u.hourangle, sep=':', precision=3)

# Ensure the hours part has two digits
if ra_hms[1] == ':':  # Check if the hours part is a single digit
    ra_hms = '0' + ra_hms  # Add a leading zero

dec_dms = source_coords.dec.to_string(unit=u.degree, sep=':', precision=3)

# Print the results
source_name = f'J{ra_hms.replace(":", "")}_{dec_dms.replace(":", "")}'

# Extract RA components (hours, minutes, seconds)
ra_hms_var = source_coords.ra.hms
ra_str_var = f"{int(ra_hms_var.h):02d}h{int(ra_hms_var.m):02d}m{ra_hms_var.s:05.2f}s"

# Extract Dec components (degrees, arcminutes, arcseconds)
dec_dms_var = source_coords.dec.dms
dec_str_var = f"{int(dec_dms_var.d):02d}d{int(abs(dec_dms_var.m)):02d}m{abs(dec_dms_var.s):05.2f}s"

print(f"Params for Brightest Source: {source_name}")
print(f"Coordinates (J2000): J2000 {ra_str_var} {dec_str_var}")
print(f"Coordinates (Deg): RA = {round(ra_deg.value, 3)}, Dec = {round(dec_deg.value, 3)}")
print(f"Flux (Stokes I): {brightest_flux} Jy")