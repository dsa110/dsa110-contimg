import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from casatools import ms

output_pdf = 'amp_time_ants.pdf'

ms_tool = ms()
ms_tool.open('./msdir/2025_01_30T03h_15m_45m/2025-01-30T03:27:35_ra063.212_dec+69.005.ms')

data_dict = ms_tool.getdata(items=["amplitude", "time", "antenna1"])
ms_tool.close()

amp = data_dict["amplitude"]   # shape (npol, nchan, nvis)
amp = np.nansum(amp, axis=1)
times = data_dict["time"]      # shape (nvis,)
ant1 = data_dict["antenna1"]   # shape (nvis,)

# Identify the unique antenna IDs that appear in the data
unique_antennas = np.unique(ant1, return_index=True)
times_pol1 = times[unique_antennas[1]]
amp_pol1 = amp[0, unique_antennas[1]]
times_pol2 = times[unique_antennas[1]]
amp_pol2 = amp[1, unique_antennas[1]]

# Create a multi-page PDF
with PdfPages(output_pdf) as pdf:

    # Loop over each antenna
    for ant in unique_antennas[0]:

        # Create a figure for this antenna
        fig, axs = plt.subplots(nrows=2, ncols=1, figsize=(12, 8), sharex=True)

        axs[0].plot(amp_pol1, label=f'Antenna {ant}')
        axs[0].set_ylabel("Amp")
        axs[1].plot(amp_pol2, label=f'Antenna {ant}')

        axs[-1].set_xlabel("Time")
        axs[0].grid(True)

        plt.tight_layout()
        pdf.savefig(fig)   # Save this figure (one page) in the PDF
        plt.close(fig)

print(f"Saved amplitude plots per antenna to {output_pdf}")
