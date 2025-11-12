#!/usr/bin/env python3
"""
Comprehensive Measurement Set validation script.
Verifies that an MS is correctly structured and ready for calibration.
"""

import sys
import numpy as np
from casatools import table, msmetadata, ms

def validate_ms(ms_path):
    """
    Perform comprehensive validation of a Measurement Set.
    
    Args:
        ms_path: Path to the Measurement Set
    
    Returns:
        bool: True if all checks pass, False otherwise
    """
    print("=" * 70)
    print("Measurement Set Validation")
    print("=" * 70)
    print(f"MS: {ms_path}\n")
    
    all_checks_passed = True
    
    # Initialize tools
    tb = table()
    msmd = msmetadata()
    myms = ms()
    
    try:
        # Open the MS
        if not tb.open(ms_path):
            print("ERROR: Cannot open MS")
            return False
        tb.close()
        
        if not msmd.open(ms_path):
            print("ERROR: Cannot open MS with msmetadata")
            return False
        
        # ================================================================
        # 1. Basic Structure Checks
        # ================================================================
        print("1. BASIC STRUCTURE")
        print("-" * 70)
        
        # Check required columns exist
        tb.open(ms_path)
        required_cols = ['DATA', 'FLAG', 'WEIGHT', 'SIGMA', 'UVW', 
                        'ANTENNA1', 'ANTENNA2', 'TIME', 'FIELD_ID']
        cols = tb.colnames()
        tb.close()
        
        for col in required_cols:
            if col in cols:
                print(f"   ✓ Column '{col}' present")
            else:
                print(f"   ✗ Column '{col}' MISSING")
                all_checks_passed = False
        
        # ================================================================
        # 2. Phase Center / Field Information
        # ================================================================
        print("\n2. PHASE CENTER / FIELD INFORMATION")
        print("-" * 70)
        
        field_names = msmd.fieldnames()
        n_fields = msmd.nfields()
        print(f"   Number of fields: {n_fields}")
        
        for i in range(n_fields):
            field_name = field_names[i]
            phase_dir = msmd.phasecenter(i)
            ra_rad = phase_dir['m0']['value']
            dec_rad = phase_dir['m1']['value']
            ra_deg = np.degrees(ra_rad)
            dec_deg = np.degrees(dec_rad)
            
            print(f"\n   Field {i}: {field_name}")
            print(f"      RA  = {ra_deg:.4f}° ({ra_rad:.6f} rad)")
            print(f"      Dec = {dec_deg:.4f}° ({dec_rad:.6f} rad)")
            
            # Check if Dec is near +55.5° (the drift scan declination)
            expected_dec = 55.5
            dec_diff = abs(dec_deg - expected_dec)
            if dec_diff < 1.0:
                print(f"      ✓ Declination close to drift scan Dec (+55.5°)")
            else:
                print(f"      ⚠ Declination differs from expected +55.5° by {dec_diff:.2f}°")
        
        # ================================================================
        # 3. Spectral Window Information
        # ================================================================
        print("\n3. SPECTRAL WINDOW INFORMATION")
        print("-" * 70)
        
        n_spw = msmd.nspw()
        print(f"   Number of spectral windows: {n_spw}")
        
        for spw in range(n_spw):
            n_chan = msmd.nchan(spw)
            freqs = msmd.chanfreqs(spw)
            ref_freq = msmd.reffreq(spw)['m0']['value']
            chan_width = msmd.chanwidths(spw)
            
            print(f"\n   SPW {spw}:")
            print(f"      Channels: {n_chan}")
            print(f"      Ref freq: {ref_freq/1e9:.4f} GHz")
            print(f"      Freq range: {freqs[0]/1e9:.4f} - {freqs[-1]/1e9:.4f} GHz")
            print(f"      Channel width: {chan_width[0]/1e6:.4f} MHz")
            print(f"      Total bandwidth: {(freqs[-1] - freqs[0] + chan_width[0])/1e6:.2f} MHz")
        
        # ================================================================
        # 4. Antenna Information
        # ================================================================
        print("\n4. ANTENNA INFORMATION")
        print("-" * 70)
        
        antenna_names = msmd.antennanames()
        n_antennas = len(antenna_names)
        print(f"   Number of antennas: {n_antennas}")
        
        # Get antenna positions
        tb.open(ms_path + '/ANTENNA')
        positions = tb.getcol('POSITION')
        tb.close()
        
        # Check for reasonable antenna positions (should be non-zero)
        non_zero_pos = np.any(positions != 0, axis=0)
        n_valid_pos = np.sum(non_zero_pos)
        
        if n_valid_pos == n_antennas:
            print(f"   ✓ All {n_antennas} antennas have valid (non-zero) positions")
        else:
            print(f"   ✗ Only {n_valid_pos}/{n_antennas} antennas have valid positions")
            all_checks_passed = False
        
        # Show first few antennas
        print(f"\n   First 5 antennas:")
        for i in range(min(5, n_antennas)):
            print(f"      {i}: {antenna_names[i]}")
        
        # ================================================================
        # 5. Data Statistics
        # ================================================================
        print("\n5. DATA STATISTICS")
        print("-" * 70)
        
        tb.open(ms_path)
        
        # Get data shape
        data = tb.getcol('DATA', startrow=0, nrow=1)
        if len(data.shape) == 3:
            n_corr, n_chan_data, n_rows_sample = data.shape
        else:
            n_corr, n_chan_data = data.shape
        print(f"   Data shape: ({n_corr} correlations, {n_chan_data} channels)")
        
        # Sample some data
        n_rows = tb.nrows()
        print(f"   Total rows: {n_rows}")
        
        # Sample 1000 rows to check data validity
        sample_size = min(1000, n_rows)
        step = max(1, n_rows // sample_size)
        sample_rows = list(range(0, n_rows, step))[:sample_size]
        
        data_sample = []
        flag_sample = []
        for row in sample_rows:
            d = tb.getcol('DATA', startrow=row, nrow=1)
            f = tb.getcol('FLAG', startrow=row, nrow=1)
            data_sample.append(d)
            flag_sample.append(f)
        
        data_sample = np.array(data_sample)
        flag_sample = np.array(flag_sample)
        
        # Check for valid data
        finite_data = np.isfinite(data_sample)
        non_zero_data = (np.abs(data_sample) > 0)
        flagged_data = flag_sample
        
        pct_finite = 100 * np.mean(finite_data)
        pct_non_zero = 100 * np.mean(non_zero_data)
        pct_flagged = 100 * np.mean(flagged_data)
        
        print(f"\n   Data quality (sampled {sample_size} rows):")
        print(f"      Finite values: {pct_finite:.1f}%")
        print(f"      Non-zero values: {pct_non_zero:.1f}%")
        print(f"      Flagged data: {pct_flagged:.1f}%")
        
        if pct_finite < 95:
            print(f"      ⚠ Warning: {100-pct_finite:.1f}% of data is non-finite (NaN/Inf)")
            all_checks_passed = False
        else:
            print(f"      ✓ Data is finite")
        
        if pct_non_zero < 50:
            print(f"      ⚠ Warning: {100-pct_non_zero:.1f}% of data is zero")
            all_checks_passed = False
        else:
            print(f"      ✓ Data contains signal")
        
        if pct_flagged > 90:
            print(f"      ⚠ Warning: {pct_flagged:.1f}% of data is flagged")
        
        # Compute amplitude statistics on unflagged data
        unflagged_data = data_sample[~flag_sample]
        if len(unflagged_data) > 0:
            amp = np.abs(unflagged_data)
            print(f"\n   Amplitude statistics (unflagged data):")
            print(f"      Min:    {np.min(amp):.6e}")
            print(f"      Median: {np.median(amp):.6e}")
            print(f"      Mean:   {np.mean(amp):.6e}")
            print(f"      Max:    {np.max(amp):.6e}")
            print(f"      Std:    {np.std(amp):.6e}")
        
        # ================================================================
        # 6. UVW Coordinates
        # ================================================================
        print("\n6. UVW COORDINATES")
        print("-" * 70)
        
        uvw_sample = []
        for row in sample_rows:
            uvw = tb.getcol('UVW', startrow=row, nrow=1)
            uvw_sample.append(uvw)
        
        uvw_sample = np.array(uvw_sample).squeeze()
        
        # Check for reasonable UVW values
        uvw_zero = np.all(uvw_sample == 0, axis=1)
        pct_zero_uvw = 100 * np.mean(uvw_zero)
        
        if pct_zero_uvw > 10:
            print(f"   ⚠ Warning: {pct_zero_uvw:.1f}% of UVW coordinates are zero")
            all_checks_passed = False
        else:
            print(f"   ✓ UVW coordinates appear valid ({pct_zero_uvw:.1f}% zero)")
        
        print(f"\n   UVW statistics:")
        print(f"      U range: {np.min(uvw_sample[:,0]):.2f} to {np.max(uvw_sample[:,0]):.2f} m")
        print(f"      V range: {np.min(uvw_sample[:,1]):.2f} to {np.max(uvw_sample[:,1]):.2f} m")
        print(f"      W range: {np.min(uvw_sample[:,2]):.2f} to {np.max(uvw_sample[:,2]):.2f} m")
        
        baseline_lengths = np.sqrt(np.sum(uvw_sample**2, axis=1))
        print(f"      Baseline lengths: {np.min(baseline_lengths):.2f} to {np.max(baseline_lengths):.2f} m")
        
        tb.close()
        
        # ================================================================
        # 7. Time Range
        # ================================================================
        print("\n7. TIME RANGE")
        print("-" * 70)
        
        time_range = msmd.timerangeforobs(0)
        
        # Convert MJD seconds to readable format
        from datetime import datetime, timedelta
        mjd_epoch = datetime(1858, 11, 17)
        
        start_time = mjd_epoch + timedelta(seconds=time_range['begin']['m0']['value'])
        end_time = mjd_epoch + timedelta(seconds=time_range['end']['m0']['value'])
        duration = (time_range['end']['m0']['value'] - time_range['begin']['m0']['value']) / 60.0
        
        print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   Duration: {duration:.2f} minutes")
        
        # ================================================================
        # Summary
        # ================================================================
        print("\n" + "=" * 70)
        if all_checks_passed:
            print("✓ ALL VALIDATION CHECKS PASSED")
            print("=" * 70)
            return True
        else:
            print("✗ SOME VALIDATION CHECKS FAILED")
            print("=" * 70)
            return False
        
    except Exception as e:
        print(f"\n✗ VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        try:
            msmd.close()
        except:
            pass
        try:
            tb.close()
        except:
            pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python validate_ms.py <measurement_set>")
        sys.exit(1)
    
    ms_path = sys.argv[1]
    success = validate_ms(ms_path)
    
    sys.exit(0 if success else 1)

