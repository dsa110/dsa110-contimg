from astropy.time import Time, TimeDelta
from astropy.coordinates import EarthLocation, SkyCoord
import astropy.units as u
import pandas as pd
import ace_tools_open as tools
import argparse

parser = argparse.ArgumentParser(description="Give calibrator coordinates.")
parser.add_argument('--ra', type=str, help='Calibrator RA')
parser.add_argument('--dec', type=str, help='Calibrator Dec')
parser.add_argument('--name', type=str, help='Calibrator name')

args = parser.parse_args()
calibrator_ra = args.ra
calibrator_dec = args.dec
calibrator_name = args.name

# Define the location of DSA-110 (Owens Valley Radio Observatory)
dsa110_location = EarthLocation.of_site("ovro")

# Define the calibrator's RA and Dec
#calibrator_name = "J1459+716"
#calibrator_ra = "14h59m07.583867s"  # Replace with your calibrator's RA
#calibrator_dec = "71d40m19.867740s"   # Replace with your calibrator's Dec

#calibrator_name = "J2253+1608"
#calibrator_ra = "22h53m57.7479s"
#calibrator_dec = "+16d08m53.563s"
calibrator_name = "J0521+166"
calibrator_ra = "05h21m09.886021s"
calibrator_dec = "16d38m22.051220s"
calibrator_coord = SkyCoord(calibrator_ra, calibrator_dec, frame="icrs")
print("RA, Dec (hms): ", calibrator_ra, calibrator_dec)
print("RA, Dec (deg): ", calibrator_coord.ra.deg, calibrator_coord.dec.deg)

# Get the current UTC time
current_time = Time.now()

# Compute the current LST at DSA-110
lst_at_transit = current_time.sidereal_time('apparent', longitude=dsa110_location.lon)

# Calculate the difference between the calibrator RA and current LST
ra_diff = (calibrator_coord.ra - lst_at_transit).wrap_at(180 * u.deg)  # Ensure within ±12h range

# Convert RA difference from degrees to hours (1 hour = 15 degrees)
time_diff = ra_diff / (15 * u.deg/u.hour)

# Compute the most recent transit time
latest_transit = current_time + time_diff
if latest_transit > current_time:
    latest_transit -= TimeDelta(23.9345 * u.hour)  # Subtract one sidereal day if transit is in the future

# Calculate the last 10 transit times (each separated by one sidereal day)
sidereal_day = TimeDelta(23.9345 * u.hour)  # Length of a sidereal day in hours
last_10_transits = [latest_transit - i * sidereal_day for i in range(10)]

# Compute transit duration (beam width = 3° in RA)
beam_width_hours = (3 * u.deg) / (15 * u.deg/u.hour)  # Convert 3° to hours

# Create dataframe
transit_data = pd.DataFrame({
    "Transit Time (UTC)": [t.iso for t in last_10_transits],
    "Duration (hours)": [beam_width_hours.value] * 10
})

# Display the results
tools.display_dataframe_to_user(name=f"Last 10 Transit Times for Calibrator {calibrator_name}", dataframe=transit_data)
