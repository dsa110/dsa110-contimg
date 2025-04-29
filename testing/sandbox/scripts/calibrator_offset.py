from astropy.coordinates import Angle, SkyCoord
import astropy.units as u
import math
from casatools import msmetadata


source_coords_hms = "14h59m07.583867s  71d40m19.867740s"
source_coords = SkyCoord(source_coords_hms, frame='icrs')

ra_deg_source = source_coords.ra.deg
dec_deg_source = source_coords.dec.deg

print('RA: ', ra_deg_source)
print('Dec: ', dec_deg_source)

msmd = msmetadata()
msmd.open('/data/jfaber/nsfrb_cand/calmsdir/bpcal/J1459_716/2025-02-07T13:37:47_ra224.687_dec+71.740.ms')

nfields = msmd.nfields()
field_names = msmd.fieldnames()

# Function to convert radians -> degrees
rad2deg = lambda x: ((x * 180.0 / math.pi) + 360) % 360

best_field = None
min_sep = 999.0   # large initial value

for fid in range(nfields):
    name = field_names[fid]
    pc = msmd.phasecenter(fid)  # returns {'m0':{}, 'm1':{}, ...} for RA, Dec
    ra_rad = pc['m0']['value']
    dec_rad = pc['m1']['value']
    
    # Convert to degrees
    ra_deg = rad2deg(ra_rad)
    dec_deg = rad2deg(dec_rad)

    #print(ra_deg)
    #print(dec_deg)

    # Rough angular separation (in degrees)
    # For small separations, you can just do sqrt(dRA^2 + dDec^2).
    # If you needed more accuracy for large separations, you'd do a proper spherical calc.
    d_ra  = ra_deg - ra_deg_source
    #print('d_ra: ', d_ra)
    d_dec = dec_deg - dec_deg_source
    #print('d_dec: ', d_dec)
    sep_deg = math.sqrt(d_ra**2 + d_dec**2)

    #print(f"Field {fid} ({name}): RA={ra_deg:.4f}, Dec={dec_deg:.4f}, sep from 3C48={sep_deg:.4f} deg")

    # Keep track of the field that is closest
    if sep_deg < min_sep:
        min_sep = sep_deg
        best_field = fid

msmd.close()

print(f"\n==> The field closest to the calibrator is Field {best_field} ({field_names[best_field]}) with ~{min_sep:.4f} deg separation.")
