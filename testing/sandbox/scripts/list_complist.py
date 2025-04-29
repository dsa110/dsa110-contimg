import numpy as np
from casatools import componentlist

cl = componentlist()

# Load the componentlist tool
cl.open('/data/jfaber/nsfrb_cand/calmsdir/cldir/nvss_top10_063p212_69p005_avg.cl')  # Replace with your component list file

# Get the number of components in the list
n_components = cl.length()

# Loop through the components and print their details
for i in range(n_components):
    position = cl.getrefdir(i)  # Get position (reference direction)
    ra_rad = position['m0']['value']  # Right Ascension in radians
    dec_rad = position['m1']['value']  # Declination in radians
    
    # Convert RA and Dec to degrees
    ra_deg = np.degrees(ra_rad)
    dec_deg = np.degrees(dec_rad)
    
    flux = cl.getfluxvalue(i)  # Get flux value
    shape = cl.getshape(i)
    
    print(f"Component {i}:")
    print(f"  Position (RA, Dec): {ra_deg:.6f} deg, {dec_deg:.6f} deg")
    print(f"  Flux: {flux} Jy")
    print(f"  Shape: {shape}")

# Close the componentlist
cl.close()
