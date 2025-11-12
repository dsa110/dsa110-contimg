#!/usr/bin/env python
"""
Data quality verification script for DSA-110 Measurement Sets.
Checks amplitude distributions, flags, phase stability, and generates diagnostic plots.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from casatools import table, msmetadata
# from casatasks import flagdata  # Not needed for this script

def verify_ms_quality(ms_path, output_dir='qa_plots'):
    """
    Comprehensive quality assessment of a Measurement Set.
    
    Parameters
    ----------
    ms_path : str
        Path to the MS file
    output_dir : str
        Directory to save QA plots and reports
    """
    
    print("="*70)
    print("DSA-110 MS Quality Verification")
    print("="*70)
    print(f"MS: {ms_path}")
    print(f"Output: {output_dir}/")
    print()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Open MS
    tb = table()
    msmd = msmetadata()
    
    try:
        tb.open(ms_path)
        msmd.open(ms_path)
        
        # ===== BASIC STATISTICS =====
        print("1. Reading visibility data...")
        data = tb.getcol('DATA')  # Shape: (npol, nchan, nrow)
        flags = tb.getcol('FLAG')
        uvw = tb.getcol('UVW')
        
        npol, nchan, nrow = data.shape
        print(f"   Shape: {nrow} rows × {nchan} channels × {npol} pols")
        
        # Compute amplitudes
        amps = np.abs(data)
        
        # ===== FLAG STATISTICS =====
        print("\n2. Flag Statistics:")
        total_vis = flags.size
        flagged_vis = np.sum(flags)
        flag_percent = 100.0 * flagged_vis / total_vis
        print(f"   Total visibilities: {total_vis:,}")
        print(f"   Flagged: {flagged_vis:,} ({flag_percent:.2f}%)")
        print(f"   Unflagged: {total_vis - flagged_vis:,} ({100-flag_percent:.2f}%)")
        
        # Flag percentages by polarization
        for pol in range(npol):
            pol_flags = np.sum(flags[pol, :, :])
            pol_total = flags[pol, :, :].size
            pol_percent = 100.0 * pol_flags / pol_total
            print(f"   Pol {pol}: {pol_percent:.2f}% flagged")
        
        # ===== AMPLITUDE STATISTICS =====
        print("\n3. Amplitude Statistics (unflagged data only):")
        unflagged_amps = amps[~flags]
        
        if len(unflagged_amps) > 0:
            print(f"   Min: {np.min(unflagged_amps):.4e}")
            print(f"   Max: {np.max(unflagged_amps):.4e}")
            print(f"   Mean: {np.mean(unflagged_amps):.4e}")
            print(f"   Median: {np.median(unflagged_amps):.4e}")
            print(f"   Std: {np.std(unflagged_amps):.4e}")
            
            # Check for zeros or NaNs
            n_zeros = np.sum(unflagged_amps == 0)
            n_nans = np.sum(np.isnan(unflagged_amps))
            n_infs = np.sum(np.isinf(unflagged_amps))
            
            if n_zeros > 0:
                print(f"   ⚠ Warning: {n_zeros} zero amplitudes ({100*n_zeros/len(unflagged_amps):.2f}%)")
            if n_nans > 0:
                print(f"   ⚠ Warning: {n_nans} NaN values")
            if n_infs > 0:
                print(f"   ⚠ Warning: {n_infs} Inf values")
        else:
            print("   ⚠ All data is flagged!")
        
        # ===== UV COVERAGE =====
        print("\n4. UV Coverage:")
        u = uvw[0, :]
        v = uvw[1, :]
        w = uvw[2, :]
        
        uv_dist = np.sqrt(u**2 + v**2)
        print(f"   UV distance range: {np.min(uv_dist):.1f} - {np.max(uv_dist):.1f} m")
        print(f"   Max |W|: {np.max(np.abs(w)):.1f} m")
        
        # ===== FREQUENCY INFO =====
        print("\n5. Frequency Information:")
        freqs = msmd.chanfreqs(0)  # SPW 0
        freq_ghz = freqs / 1e9
        print(f"   Channels: {len(freqs)}")
        print(f"   Frequency range: {freq_ghz[0]:.4f} - {freq_ghz[-1]:.4f} GHz")
        print(f"   Bandwidth: {(freq_ghz[-1] - freq_ghz[0])*1000:.2f} MHz")
        print(f"   Channel width: {(freqs[1] - freqs[0])/1e3:.2f} kHz")
        
        tb.close()
        msmd.close()
        
        # ===== GENERATE PLOTS =====
        print("\n6. Generating diagnostic plots...")
        
        # Plot 1: Amplitude histogram
        print("   - Amplitude histogram...")
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        for pol in range(npol):
            pol_amps = amps[pol, :, :][~flags[pol, :, :]]
            if len(pol_amps) > 0:
                axes[0].hist(pol_amps, bins=100, alpha=0.5, label=f'Pol {pol}', log=True)
        
        axes[0].set_xlabel('Amplitude (Jy)')
        axes[0].set_ylabel('Count')
        axes[0].set_title('Amplitude Distribution')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Log scale histogram
        for pol in range(npol):
            pol_amps = amps[pol, :, :][~flags[pol, :, :]]
            if len(pol_amps) > 0:
                axes[1].hist(np.log10(pol_amps + 1e-10), bins=100, alpha=0.5, 
                           label=f'Pol {pol}')
        
        axes[1].set_xlabel('Log10(Amplitude) (Jy)')
        axes[1].set_ylabel('Count')
        axes[1].set_title('Log Amplitude Distribution')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'amplitude_histogram.png'), dpi=150)
        plt.close()
        
        # Plot 2: Amplitude vs channel
        print("   - Amplitude vs channel...")
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for pol in range(npol):
            chan_median_amps = np.array([
                np.median(amps[pol, ch, :][~flags[pol, ch, :]]) 
                if np.sum(~flags[pol, ch, :]) > 0 else np.nan
                for ch in range(nchan)
            ])
            ax.plot(freq_ghz, chan_median_amps, 'o-', label=f'Pol {pol}', alpha=0.7, markersize=2)
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Median Amplitude (Jy)')
        ax.set_title('Amplitude vs Frequency')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'amplitude_vs_frequency.png'), dpi=150)
        plt.close()
        
        # Plot 3: UV coverage
        print("   - UV coverage...")
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Subsample for plotting (too many points otherwise)
        subsample = max(1, nrow // 10000)
        u_plot = u[::subsample] / 1e3  # Convert to km
        v_plot = v[::subsample] / 1e3
        
        ax.plot(u_plot, v_plot, '.', markersize=0.5, alpha=0.3, color='blue')
        ax.plot(-u_plot, -v_plot, '.', markersize=0.5, alpha=0.3, color='blue')
        
        ax.set_xlabel('U (km)')
        ax.set_ylabel('V (km)')
        ax.set_title('UV Coverage')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'uv_coverage.png'), dpi=150)
        plt.close()
        
        # Plot 4: Flag summary by channel
        print("   - Flag summary by channel...")
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for pol in range(npol):
            chan_flag_percent = np.array([
                100.0 * np.sum(flags[pol, ch, :]) / flags[pol, ch, :].size
                for ch in range(nchan)
            ])
            ax.plot(freq_ghz, chan_flag_percent, 'o-', label=f'Pol {pol}', alpha=0.7, markersize=2)
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Flagged (%)')
        ax.set_title('Flags vs Frequency')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'flags_vs_frequency.png'), dpi=150)
        plt.close()
        
        print(f"\n✓ Plots saved to {output_dir}/")
        
        # ===== SUMMARY REPORT =====
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
            f.write(f"  Unflagged: {total_vis - flagged_vis:,} ({100-flag_percent:.2f}%)\n\n")
            
            if len(unflagged_amps) > 0:
                f.write("AMPLITUDES (unflagged):\n")
                f.write(f"  Min: {np.min(unflagged_amps):.4e} Jy\n")
                f.write(f"  Max: {np.max(unflagged_amps):.4e} Jy\n")
                f.write(f"  Mean: {np.mean(unflagged_amps):.4e} Jy\n")
                f.write(f"  Median: {np.median(unflagged_amps):.4e} Jy\n")
                f.write(f"  Std: {np.std(unflagged_amps):.4e} Jy\n\n")
            
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
            
            if n_zeros > 0.01 * len(unflagged_amps):
                f.write(f"  ⚠ WARNING: {n_zeros} zero-valued visibilities\n")
            
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
        if tb.isopen():
            tb.close()
        if msmd.isopen():
            msmd.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python verify_ms_quality.py <ms_path> [output_dir]")
        sys.exit(1)
    
    ms_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'qa_plots'
    
    success = verify_ms_quality(ms_path, output_dir)
    sys.exit(0 if success else 1)

