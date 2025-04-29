from casatools import table
import numpy as np
from astropy.stats import median_absolute_deviation

def compute_antenna_quality(cal_table):

    # Parameters for outlier detection
    MAD_THRESHOLD = 10.0       # threshold in units of global MAD (if non-zero)
    MIN_VALID_FRACTION = 0.5   # require at least 50% non-default channels

    # For amplitude, assume a default solution of 1.0
    DEFAULT_VALUE = 1.0
    TOL = 1e-3               # tolerance to decide if an amplitude value is default

    # For phase, assume default phase is 0.0 degrees (from a default gain of 1+0j)
    DEFAULT_PHASE = 0.0
    TOL_PHASE = 1e-2         # tolerance (in degrees) to decide if a phase is default

    try:
        bcal_table = table()
        bcal_table.open(cal_table, nomodify=True)
        cparam = bcal_table.getcol("CPARAM")  # shape: (n_pol, n_chan, n_row)
        antenna_ids = bcal_table.getcol("ANTENNA1")
    except Exception as e:
        raise RuntimeError(f"Error reading calibration table: {e}")
    finally:
        if bcal_table is not None:
            bcal_table.close()

    if cparam.size == 0:
        raise ValueError("CPARAM is empty!")
    
    # Transpose CPARAM from (n_pol, n_chan, n_row) to (n_row, n_chan, n_pol)
    cparam = cparam.transpose(2, 1, 0)

    # Compute amplitude and phase (in degrees) from CPARAM.
    amp = np.abs(cparam)
    phase = np.angle(cparam, deg=True)

    # Average over polarizations if more than one exists
    if amp.ndim == 3 and amp.shape[2] > 1:
        amp = np.mean(amp, axis=2)
    if phase.ndim == 3 and phase.shape[2] > 1:
        # Unwrap phase along the channel axis for each solution and polarization
        for i in range(phase.shape[0]):
            for j in range(phase.shape[2]):
                phase[i, :, j] = np.unwrap(phase[i, :, j], discont=180)
        phase = np.mean(phase, axis=2)

    antenna_ids_unique = np.unique(antenna_ids)
    ant_stats = {}
    amp_medians = []
    phase_medians = []

    for ant in antenna_ids_unique:
        ant_mask = (antenna_ids == ant)
        ant_amp = amp[ant_mask, ...]       # shape: (n_sol, n_chan)
        ant_phase = phase[ant_mask, ...]     # shape: (n_sol, n_chan)

        ant_amp_flat = ant_amp.flatten()
        ant_phase_flat = ant_phase.flatten()

        if ant_amp_flat.size == 0 or ant_phase_flat.size == 0:
            continue

        # Amplitude statistics
        med_amp = np.median(ant_amp_flat)
        mad_amp = median_absolute_deviation(ant_amp_flat)
        valid_amp = np.sum(np.abs(ant_amp_flat - DEFAULT_VALUE) > TOL)
        frac_valid_amp = valid_amp / ant_amp_flat.size

        # Phase statistics
        med_phase = np.median(ant_phase_flat)
        mad_phase = median_absolute_deviation(ant_phase_flat)
        valid_phase = np.sum(np.abs(ant_phase_flat - DEFAULT_PHASE) > TOL_PHASE)
        frac_valid_phase = valid_phase / ant_phase_flat.size

        ant_stats[ant] = {
            "amp": (med_amp, mad_amp, ant_amp_flat.size, frac_valid_amp),
            "phase": (med_phase, mad_phase, ant_phase_flat.size, frac_valid_phase)
        }
        amp_medians.append(med_amp)
        phase_medians.append(med_phase)

    amp_medians = np.array(amp_medians)
    phase_medians = np.array(phase_medians)
    
    # Global amplitude statistics
    global_amp_med = np.median(amp_medians)
    global_amp_mad = median_absolute_deviation(amp_medians) if np.any(amp_medians != global_amp_med) else 0.0

    # Global phase statistics
    global_phase_med = np.median(phase_medians)
    global_phase_mad = median_absolute_deviation(phase_medians) if np.any(phase_medians != global_phase_med) else 0.0

    bad_antennas = []
    header = ("{:>10s} {:>15s} {:>15s} {:>10s} {:>15s} | "
              "{:>15s} {:>15s} {:>10s} {:>15s} {:>15s}")
    print("Antenna Quality Summary:")
    print(header.format("Antenna", "Med Amp", "MAD(amp)", "n_sol", "Valid(amp)",
                          "Med Phase", "MAD(phase)", "n_sol", "Valid(phase)", "Amp Dev (MAD)"))
    print("-" * 120)
    
    for ant in sorted(ant_stats.keys()):
        med_amp, mad_amp, n_sol_amp, frac_valid_amp = ant_stats[ant]["amp"]
        med_phase, mad_phase, n_sol_phase, frac_valid_phase = ant_stats[ant]["phase"]
        amp_deviation = np.abs(med_amp - global_amp_med) / global_amp_mad if global_amp_mad > 0 else 0.0
        phase_deviation = np.abs(med_phase - global_phase_med) / global_phase_mad if global_phase_mad > 0 else 0.0

        print("{:10d} {:15.4f} {:15.4f} {:10d} {:15.2f} | {:15.4f} {:15.4f} {:10d} {:15.2f} {:15.2f}"
              .format(ant, med_amp, mad_amp, n_sol_amp, frac_valid_amp,
                      med_phase, mad_phase, n_sol_phase, frac_valid_phase,
                      amp_deviation))
        # Flag if either amplitude or phase statistics are off:
        if (amp_deviation > MAD_THRESHOLD or frac_valid_amp < MIN_VALID_FRACTION or
            phase_deviation > MAD_THRESHOLD or frac_valid_phase < MIN_VALID_FRACTION):
            bad_antennas.append(ant)

    print("\nGlobal amplitude median: {:.4f} MAD: {:.4f}".format(global_amp_med, global_amp_mad))
    print("Global phase median: {:.4f} MAD: {:.4f}".format(global_phase_med, global_phase_mad))
    return ant_stats, bad_antennas

# Run the improved quality check on the calibration table
#cal_table_name = "/data/jfaber/dsa110-contimg/sandbox/2025-02-14_1459+716_JF/multifield/J1459_716.bcal"
#ant_stats, bad_antennas = compute_antenna_quality(cal_table_name)
#print(f"\nIdentified {len(bad_antennas)} bad antennas: {bad_antennas}")
#ant_add_pad = ['pad' + str(i+1) for i in bad_antennas]
#ant_names = ', '.join(ant_add_pad)
#print(ant_names)
