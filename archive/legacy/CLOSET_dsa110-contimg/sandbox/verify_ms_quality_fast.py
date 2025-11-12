#!/usr/bin/env python
"""
Fast data quality verification script for DSA-110 Measurement Sets.
Uses chunked reading to avoid memory issues and provides progress updates.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from casatools import table, msmetadata

def verify_ms_quality(ms_path, output_dir='qa_plots', max_rows_per_chunk=50000):
    """
    Comprehensive quality assessment of a Measurement Set using chunked reading.
    
    Parameters
    ----------
    ms_path : str
        Path to the MS file
    output_dir : str
        Directory to save QA plots and reports
    max_rows_per_chunk : int
        Number of rows to read at once (memory management)
    """
    
    print("="*70)
    print("DSA-110 MS Quality Verification (Fast Mode)")
    print("="*70)
    print(f"MS: {ms_path}")
    print(f"Output: {output_dir}/")
    print()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Open MS
    tb = table()
    msmd = msmetadata()
    
    try:
        print("1. Opening MS and reading metadata...")
        tb.open(ms_path)
        msmd.open(ms_path)
        
        nrow = tb.nrows()
        print(f"   Total rows: {nrow:,}")
        
        # Get a sample row to determine shape
        sample_data = tb.getcol('DATA', startrow=0, nrow=1)
        npol, nchan = sample_data.shape[0], sample_data.shape[1]
        print(f"   Shape per row: {nchan} channels × {npol} pols")
        
        # ===== FREQUENCY INFO =====
        print("\n2. Frequency Information:")
        freqs = msmd.chanfreqs(0)  # SPW 0
        freq_ghz = freqs / 1e9
        print(f"   Channels: {len(freqs)}")
        print(f"   Frequency range: {freq_ghz[0]:.4f} - {freq_ghz[-1]:.4f} GHz")
        print(f"   Bandwidth: {(freq_ghz[-1] - freq_ghz[0])*1000:.2f} MHz")
        print(f"   Channel width: {(freqs[1] - freqs[0])/1e3:.2f} kHz")
        
        # ===== CHUNKED DATA READING =====
        print(f"\n3. Processing data in chunks of {max_rows_per_chunk:,} rows...")
        
        # Statistics accumulators
        total_vis = 0
        flagged_vis = 0
        flag_per_pol = np.zeros(npol, dtype=np.int64)
        flag_per_chan = np.zeros(nchan, dtype=np.int64)
        
        amp_sum = np.zeros(npol)
        amp_sum_sq = np.zeros(npol)
        amp_count = np.zeros(npol)
        amp_min = np.full(npol, np.inf)
        amp_max = np.full(npol, -np.inf)
        
        amp_per_chan_sum = np.zeros((npol, nchan))
        amp_per_chan_count = np.zeros((npol, nchan))
        
        n_zeros = 0
        n_nans = 0
        n_infs = 0
        
        # For UV coverage (subsample)
        uv_subsample = []
        subsample_stride = max(1, nrow // 5000)  # Keep ~5000 points
        
        n_chunks = (nrow + max_rows_per_chunk - 1) // max_rows_per_chunk
        
        for chunk_idx in range(n_chunks):
            start_row = chunk_idx * max_rows_per_chunk
            end_row = min(start_row + max_rows_per_chunk, nrow)
            chunk_size = end_row - start_row
            
            print(f"   Chunk {chunk_idx+1}/{n_chunks}: rows {start_row:,}-{end_row:,} "
                  f"({100*(chunk_idx+1)/n_chunks:.1f}%)")
            
            # Read chunk
            data = tb.getcol('DATA', startrow=start_row, nrow=chunk_size)
            flags = tb.getcol('FLAG', startrow=start_row, nrow=chunk_size)
            
            # Subsample UV coordinates
            if chunk_idx == 0 or start_row % subsample_stride == 0:
                uvw_chunk = tb.getcol('UVW', startrow=start_row, nrow=min(100, chunk_size))
                uv_subsample.append(uvw_chunk)
            
            # Compute amplitudes
            amps = np.abs(data)
            
            # Flag statistics
            total_vis += flags.size
            flagged_vis += np.sum(flags)
            
            for pol in range(npol):
                flag_per_pol[pol] += np.sum(flags[pol, :, :])
            
            for ch in range(nchan):
                flag_per_chan[ch] += np.sum(flags[:, ch, :])
            
            # Amplitude statistics (unflagged only)
            for pol in range(npol):
                unflagged = ~flags[pol, :, :]
                unflagged_amps = amps[pol, :, :][unflagged]
                
                if len(unflagged_amps) > 0:
                    amp_sum[pol] += np.sum(unflagged_amps)
                    amp_sum_sq[pol] += np.sum(unflagged_amps**2)
                    amp_count[pol] += len(unflagged_amps)
                    amp_min[pol] = min(amp_min[pol], np.min(unflagged_amps))
                    amp_max[pol] = max(amp_max[pol], np.max(unflagged_amps))
                    
                    # Check for problematic values
                    n_zeros += np.sum(unflagged_amps == 0)
                    n_nans += np.sum(np.isnan(unflagged_amps))
                    n_infs += np.sum(np.isinf(unflagged_amps))
                
                # Per-channel statistics
                for ch in range(nchan):
                    ch_unflagged = unflagged[ch, :]
                    if np.sum(ch_unflagged) > 0:
                        ch_amps = amps[pol, ch, :][ch_unflagged]
                        amp_per_chan_sum[pol, ch] += np.sum(ch_amps)
                        amp_per_chan_count[pol, ch] += len(ch_amps)
        
        tb.close()
        msmd.close()
        
        # ===== COMPUTE FINAL STATISTICS =====
        print("\n4. Computing statistics...")
        
        flag_percent = 100.0 * flagged_vis / total_vis
        amp_mean = amp_sum / np.maximum(amp_count, 1)
        amp_std = np.sqrt(amp_sum_sq / np.maximum(amp_count, 1) - amp_mean**2)
        
        chan_median_amps = np.zeros((npol, nchan))
        for pol in range(npol):
            for ch in range(nchan):
                if amp_per_chan_count[pol, ch] > 0:
                    chan_median_amps[pol, ch] = amp_per_chan_sum[pol, ch] / amp_per_chan_count[pol, ch]
                else:
                    chan_median_amps[pol, ch] = np.nan
        
        chan_flag_percent = 100.0 * flag_per_chan / (flag_per_chan.sum() / nchan * npol)
        
        # UV coverage
        uvw = np.concatenate(uv_subsample, axis=1)
        u = uvw[0, :]
        v = uvw[1, :]
        w = uvw[2, :]
        uv_dist = np.sqrt(u**2 + v**2)
        
        # ===== PRINT SUMMARY =====
        print("\n" + "="*70)
        print("QUALITY ASSESSMENT SUMMARY")
        print("="*70)
        
        print("\nDATA SUMMARY:")
        print(f"  Rows: {nrow:,}")
        print(f"  Channels: {nchan}")
        print(f"  Polarizations: {npol}")
        print(f"  Total visibilities: {total_vis:,}")
        
        print("\nFLAGS:")
        print(f"  Flagged: {flagged_vis:,} ({flag_percent:.2f}%)")
        print(f"  Unflagged: {total_vis - flagged_vis:,} ({100-flag_percent:.2f}%)")
        for pol in range(npol):
            pol_total = flag_per_pol[pol]
            pol_size = nchan * nrow
            print(f"  Pol {pol}: {100.0*pol_total/pol_size:.2f}% flagged")
        
        print("\nAMPLITUDES (unflagged):")
        for pol in range(npol):
            if amp_count[pol] > 0:
                print(f"  Pol {pol}:")
                print(f"    Min: {amp_min[pol]:.4e} Jy")
                print(f"    Max: {amp_max[pol]:.4e} Jy")
                print(f"    Mean: {amp_mean[pol]:.4e} Jy")
                print(f"    Std: {amp_std[pol]:.4e} Jy")
        
        if n_zeros > 0:
            print(f"  ⚠ Warning: {n_zeros:,} zero amplitudes")
        if n_nans > 0:
            print(f"  ⚠ Warning: {n_nans:,} NaN values")
        if n_infs > 0:
            print(f"  ⚠ Warning: {n_infs:,} Inf values")
        
        print("\nUV COVERAGE (subsampled):")
        print(f"  UV distance range: {np.min(uv_dist):.1f} - {np.max(uv_dist):.1f} m")
        print(f"  Max |W|: {np.max(np.abs(w)):.1f} m")
        
        # ===== GENERATE PLOTS =====
        print("\n5. Generating diagnostic plots...")
        
        # Plot 1: Amplitude vs frequency
        print("   - Amplitude vs frequency...")
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for pol in range(npol):
            ax.plot(freq_ghz, chan_median_amps[pol, :], 'o-', 
                   label=f'Pol {pol}', alpha=0.7, markersize=2)
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Mean Amplitude (Jy)')
        ax.set_title('Amplitude vs Frequency')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'amplitude_vs_frequency.png'), dpi=150)
        plt.close()
        
        # Plot 2: Flags vs frequency
        print("   - Flags vs frequency...")
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(freq_ghz, chan_flag_percent, 'o-', alpha=0.7, markersize=2, color='red')
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Flagged (%)')
        ax.set_title('Flags vs Frequency')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'flags_vs_frequency.png'), dpi=150)
        plt.close()
        
        # Plot 3: UV coverage
        print("   - UV coverage...")
        fig, ax = plt.subplots(figsize=(10, 10))
        
        u_km = u / 1e3
        v_km = v / 1e3
        
        ax.plot(u_km, v_km, '.', markersize=0.5, alpha=0.3, color='blue')
        ax.plot(-u_km, -v_km, '.', markersize=0.5, alpha=0.3, color='blue')
        
        ax.set_xlabel('U (km)')
        ax.set_ylabel('V (km)')
        ax.set_title('UV Coverage')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'uv_coverage.png'), dpi=150)
        plt.close()
        
        print(f"\n✓ Plots saved to {output_dir}/")
        
        # ===== WRITE REPORT =====
        report_file = os.path.join(output_dir, 'qa_report.txt')
        with open(report_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("DSA-110 MS Quality Assessment Report\n")
            f.write("="*70 + "\n\n")
            f.write(f"MS: {ms_path}\n")
            f.write(f"Date: {os.popen('date').read().strip()}\n\n")
            
            f.write("DATA SUMMARY:\n")
            f.write(f"  Rows: {nrow:,}\n")
            f.write(f"  Channels: {nchan}\n")
            f.write(f"  Polarizations: {npol}\n")
            f.write(f"  Total visibilities: {total_vis:,}\n\n")
            
            f.write("FLAGS:\n")
            f.write(f"  Flagged: {flagged_vis:,} ({flag_percent:.2f}%)\n")
            f.write(f"  Unflagged: {total_vis - flagged_vis:,} ({100-flag_percent:.2f}%)\n")
            for pol in range(npol):
                pol_total = flag_per_pol[pol]
                pol_size = nchan * nrow
                f.write(f"  Pol {pol}: {100.0*pol_total/pol_size:.2f}% flagged\n")
            f.write("\n")
            
            f.write("AMPLITUDES (unflagged):\n")
            for pol in range(npol):
                if amp_count[pol] > 0:
                    f.write(f"  Pol {pol}:\n")
                    f.write(f"    Min: {amp_min[pol]:.4e} Jy\n")
                    f.write(f"    Max: {amp_max[pol]:.4e} Jy\n")
                    f.write(f"    Mean: {amp_mean[pol]:.4e} Jy\n")
                    f.write(f"    Std: {amp_std[pol]:.4e} Jy\n")
            f.write("\n")
            
            f.write("FREQUENCY:\n")
            f.write(f"  Range: {freq_ghz[0]:.4f} - {freq_ghz[-1]:.4f} GHz\n")
            f.write(f"  Bandwidth: {(freq_ghz[-1] - freq_ghz[0])*1000:.2f} MHz\n\n")
            
            f.write("UV COVERAGE:\n")
            f.write(f"  UV distance: {np.min(uv_dist):.1f} - {np.max(uv_dist):.1f} m\n")
            f.write(f"  Max |W|: {np.max(np.abs(w)):.1f} m\n\n")
            
            # Data quality assessment
            f.write("QUALITY ASSESSMENT:\n")
            if flag_percent > 50:
                f.write("  ⚠ WARNING: >50% of data is flagged\n")
            elif flag_percent > 20:
                f.write("  ℹ INFO: >20% of data is flagged (may be normal for RFI)\n")
            else:
                f.write("  ✓ Flag percentage is reasonable\n")
            
            if n_zeros > 0:
                f.write(f"  ℹ INFO: {n_zeros:,} zero-valued visibilities\n")
            
            if n_nans > 0 or n_infs > 0:
                f.write("  ⚠ WARNING: Invalid values (NaN/Inf) detected\n")
            else:
                f.write("  ✓ No invalid values detected\n")
            
            f.write("\n")
        
        print(f"✓ Report saved to {report_file}")
        
        print("\n" + "="*70)
        print("Quality verification complete!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if 'tb' in locals() and tb.isopened():
            tb.close()
        if 'msmd' in locals() and msmd.isopened():
            msmd.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python verify_ms_quality_fast.py <ms_path> [output_dir]")
        sys.exit(1)
    
    ms_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'qa_plots'
    
    success = verify_ms_quality(ms_path, output_dir)
    sys.exit(0 if success else 1)

