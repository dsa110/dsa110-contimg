from casacore.tables import table
import numpy as np
from astropy.stats import median_absolute_deviation

# Parameters for outlier detection
MAD_THRESHOLD = 10.0  # threshold in units of global MAD (if non-zero)
MIN_VALID_FRACTION = 0.5  # require at least 50% non-default channels
DEFAULT_VALUE = 1.0
TOL = 1e-3  # tolerance to decide if a value is default

def compute_antenna_quality(cal_table):
    try:
        bcal_table = table(cal_table, readonly=True)
        cparam = bcal_table.getcol("CPARAM")  # shape: (n_rows, n_chan, n_pol)
        antenna_ids = bcal_table.getcol("ANTENNA1")
    except Exception as e:
        raise RuntimeError(f"Error reading calibration table: {e}")
    finally:
        bcal_table.close()

    if cparam.size == 0:
        raise ValueError("CPARAM is empty!")

    # Average over polarizations if applicable
    amp = np.abs(cparam)
    if amp.ndim == 3 and amp.shape[2] > 1:
        amp = np.mean(amp, axis=2)

    antenna_ids_unique = np.unique(antenna_ids)
    ant_stats = {}
    medians = []
    valid_fractions = []
    for ant in antenna_ids_unique:
        ant_mask = (antenna_ids == ant)
        ant_amp = amp[ant_mask, ...]  # shape: (n_sol, n_chan)
        ant_amp_flat = ant_amp.flatten()

        if ant_amp_flat.size == 0:
            continue
        med_amp = np.median(ant_amp_flat)
        mad_amp = median_absolute_deviation(ant_amp_flat)

        # Count valid (non-default) solutions
        valid = np.sum(np.abs(ant_amp_flat - DEFAULT_VALUE) > TOL)
        frac_valid = valid / ant_amp_flat.size

        ant_stats[ant] = (med_amp, mad_amp, ant_amp_flat.size, frac_valid)
        medians.append(med_amp)
        valid_fractions.append(frac_valid)

    medians = np.array(medians)
    valid_fractions = np.array(valid_fractions)
    
    global_med = np.median(medians)
    global_mad = median_absolute_deviation(medians) if np.any(medians != global_med) else 0.0

    bad_antennas = []
    print("Antenna Quality Summary:")
    print("{:>10s} {:>15s} {:>15s} {:>10s} {:>15s} {:>15s}".format("Antenna", "Med Amp", "MAD", "n_sol", "Valid Frac", "Deviation (MAD)"))
    for ant in sorted(ant_stats.keys()):
        med_amp, mad_amp, n_sol, frac_valid = ant_stats[ant]
        if global_mad > 0:
            deviation = np.abs(med_amp - global_med) / global_mad
        else:
            deviation = 0.0
        print("{:>10d} {:15.4f} {:15.4f} {:10d} {:15.2f} {:15.2f}".format(ant, med_amp, mad_amp, n_sol, frac_valid, deviation))
        # Flag if deviation is high OR the fraction of valid channels is too low
        if deviation > MAD_THRESHOLD or frac_valid < MIN_VALID_FRACTION:
            bad_antennas.append(ant)

    return ant_stats, bad_antennas

# Run the improved quality check on the calibration table
cal_table_name = "/data/jfaber/dsa110-contimg/sandbox/2025-02-14_1459+716_JF/multifield/J1459_716.bcal"
ant_stats, bad_antennas = compute_antenna_quality(cal_table_name)
print(f"\nIdentified {len(bad_antennas)} bad antennas: {bad_antennas}")
ant_add_pad = ['pad' + str(i+1) for i in bad_antennas]
ant_names = ', '.join(ant_add_pad)
print(ant_names)
