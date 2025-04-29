import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from casacore.tables import table

# Open the spectral window table
ms_path = "/data/jfaber/nsfrb_cand/calmsdir/bpcal/J0841_708/2025-01-30T07:56:37_ra130.686_dec+69.164_avg.ms"  # Path to your measurement set
spw_table = table(f"{ms_path}/SPECTRAL_WINDOW", readonly=True)

# Extract frequency information
frequencies = spw_table.getcol("CHAN_FREQ")  # Frequencies for each channel
spw_ids = spw_table.getcol("NAME")  # Spectral window IDs (optional, for reference)

# Close the spectral window table
spw_table.close()

# Open the .bcal table
bcal_table = table("/data/jfaber/nsfrb_cand/calmsdir/bpcal/J0841_708.bcal", readonly=True)

# Extract relevant columns
cparam = bcal_table.getcol("CPARAM")  # Shape: (n_rows, n_channels, n_polarizations)
spw_ids_bcal = bcal_table.getcol("SPECTRAL_WINDOW_ID")  # Spectral window IDs in the .bcal table
antenna_ids = bcal_table.getcol("ANTENNA1")  # Antenna IDs

# Close the .bcal table
bcal_table.close()

# Map frequencies to bandpass solutions
# Assuming all solutions in the .bcal table use the same spectral window
unique_spw_ids = np.unique(spw_ids_bcal)
if len(unique_spw_ids) > 1:
    print("Warning: Multiple spectral windows found in the .bcal table.")
spw_id = unique_spw_ids[0]  # Use the first spectral window ID (or loop over all if needed)
frequencies_for_bcal = frequencies[spw_id]  # Frequencies for this spectral window

import matplotlib.pyplot as plt

# Plot amplitude and phase for each antenna and polarization
n_antennas = len(np.unique(antenna_ids))
n_polarizations = cparam.shape[2]

with PdfPages("/data/jfaber/nsfrb_cand/calmsdir/bpcal/J0841_708.bcal.pdf") as pdf:
    for ant in range(n_antennas):
        plt.figure(figsize=(12, 8))  # Create a new figure for each antenna
        for pol in range(n_polarizations):
            plt.subplot(n_polarizations, 1, pol + 1)  # One column of subplots per polarization
            plt.plot(frequencies_for_bcal, np.abs(cparam[ant, :, pol]), label=f"Antenna {ant}, Pol {pol}")
            plt.xlabel("Frequency (Hz)")
            plt.ylabel("Amplitude")
            plt.title(f"Antenna {ant}, Pol {pol}")
            plt.legend()
            plt.grid(True)
        plt.tight_layout()  # Adjust layout to prevent overlap
        pdf.savefig()  # Save the current figure as a page in the PDF
        plt.close()  # Close the figure to free up memory