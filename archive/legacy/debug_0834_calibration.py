#!/usr/bin/env python3
"""
Debug script for 0834+555 calibration failure analysis.

This script investigates why bandpass solutions are poor for VLA calibrator
0834+555:
- 90% of solutions flagged due to SNR < 3
- SPW mismatch (bandpass table only has SPW 0, MS has 16 SPWs)
- Many antennas completely flagged
- High amplitude scatter (53.9% of median)

Based on analysis of calibration log from 2025-11-05 01:40:13.
"""

import sys
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import casacore.tables as ct
    CASA_AVAILABLE = True
except ImportError:
    logger.warning("casacore not available - some functions will be limited")
    CASA_AVAILABLE = False


def analyze_ms_structure(ms_path: str) -> Dict[str, Any]:
    """
    Analyze MS structure to understand field, SPW, and antenna configuration.
    
    Args:
        ms_path: Path to MS file
        
    Returns:
        Dictionary with MS structure analysis
    """
    if not CASA_AVAILABLE:
        return {"error": "casacore not available"}
    
    if not Path(ms_path).exists():
        return {"error": f"MS does not exist: {ms_path}"}
    
    results = {}
    
    try:
        # Main table info
        with ct.table(ms_path, readonly=True) as tb:
            results['nrows'] = tb.nrows()
            results['columns'] = tb.colnames()
        
        # Field table
        with ct.table(f"{ms_path}::FIELD", readonly=True) as tb:
            field_names = tb.getcol('NAME')
            phase_dirs = tb.getcol('PHASE_DIR')
            ref_dirs = tb.getcol('REFERENCE_DIR')
            
            results['fields'] = {
                'count': len(field_names),
                'names': field_names.tolist(),
                'phase_dirs': phase_dirs.tolist(),
                'ref_dirs': ref_dirs.tolist()
            }
        
        # Spectral window table
        with ct.table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as tb:
            chan_freqs = tb.getcol('CHAN_FREQ')
            chan_widths = tb.getcol('CHAN_WIDTH')
            nchans = tb.getcol('NUM_CHAN')
            
            results['spectral_windows'] = {
                'count': len(nchans),
                'channels_per_spw': nchans.tolist(),
                'total_channels': int(np.sum(nchans)),
                'freq_ranges': []
            }
            
            for i, (freqs, widths) in enumerate(zip(chan_freqs, chan_widths)):
                freq_min = np.min(freqs) / 1e9  # Convert to GHz
                freq_max = np.max(freqs) / 1e9
                results['spectral_windows']['freq_ranges'].append({
                    'spw': i,
                    'freq_min_ghz': freq_min,
                    'freq_max_ghz': freq_max,
                    'bandwidth_mhz': np.sum(widths) / 1e6
                })
        
        # Antenna table
        with ct.table(f"{ms_path}::ANTENNA", readonly=True) as tb:
            ant_names = tb.getcol('NAME')
            ant_positions = tb.getcol('POSITION')
            
            results['antennas'] = {
                'count': len(ant_names),
                'names': ant_names.tolist(),
                'position_range': {
                    'x_range': [
                        float(np.min(ant_positions[:, 0])),
                        float(np.max(ant_positions[:, 0]))
                    ],
                    'y_range': [
                        float(np.min(ant_positions[:, 1])),
                        float(np.max(ant_positions[:, 1]))
                    ],
                    'z_range': [
                        float(np.min(ant_positions[:, 2])),
                        float(np.max(ant_positions[:, 2]))
                    ]
                }
            }
        
        # Data description table
        with ct.table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as tb:
            spw_ids = tb.getcol('SPECTRAL_WINDOW_ID')
            pol_ids = tb.getcol('POLARIZATION_ID')
            
            results['data_description'] = {
                'count': len(spw_ids),
                'spw_mapping': spw_ids.tolist(),
                'pol_mapping': pol_ids.tolist()
            }
        
        # Check data columns
        with ct.table(ms_path, readonly=True) as tb:
            results['data_columns'] = {
                'has_data': 'DATA' in tb.colnames(),
                'has_model_data': 'MODEL_DATA' in tb.colnames(),
                'has_corrected_data': 'CORRECTED_DATA' in tb.colnames(),
                'has_weight': 'WEIGHT' in tb.colnames(),
                'has_flag': 'FLAG' in tb.colnames()
            }
        
    except Exception as e:
        results['error'] = f"Failed to analyze MS structure: {e}"
    
    return results


def analyze_model_data_quality(
        ms_path: str, field_id: int = 0) -> Dict[str, Any]:
    """
    Analyze MODEL_DATA quality for calibration source.
    
    Args:
        ms_path: Path to MS file
        field_id: Field ID to analyze (default 0)
        
    Returns:
        Dictionary with MODEL_DATA analysis
    """
    if not CASA_AVAILABLE:
        return {"error": "casacore not available"}
    
    results = {}
    
    try:
        with ct.table(ms_path, readonly=True) as tb:
            # Query for specific field
            query = f"FIELD_ID == {field_id}"
            subtb = tb.query(query)
            
            if subtb.nrows() == 0:
                return {"error": f"No data found for field {field_id}"}
            
            # Get MODEL_DATA
            if 'MODEL_DATA' not in tb.colnames():
                return {"error": "MODEL_DATA column not found"}
            
            model_data = subtb.getcol('MODEL_DATA')
            flags = subtb.getcol('FLAG')
            
            # Apply flags
            model_data_unflagged = model_data[~flags]
            
            if len(model_data_unflagged) == 0:
                return {"error": "All MODEL_DATA is flagged"}
            
            # Calculate statistics
            amplitudes = np.abs(model_data_unflagged)
            phases = np.angle(model_data_unflagged)
            
            results = {
                'shape': model_data.shape,
                'total_points': model_data.size,
                'unflagged_points': len(model_data_unflagged),
                'flagged_fraction': 1.0 - (
                    len(model_data_unflagged) / model_data.size
                ),
                'amplitude_stats': {
                    'min': float(np.min(amplitudes)),
                    'max': float(np.max(amplitudes)),
                    'mean': float(np.mean(amplitudes)),
                    'median': float(np.median(amplitudes)),
                    'std': float(np.std(amplitudes))
                },
                'phase_stats': {
                    'mean': float(np.mean(phases)),
                    'std': float(np.std(phases)),
                    'wrap_around': bool(
                        np.any(np.abs(np.diff(phases)) > np.pi)
                    )
                }
            }
            
            # Check for expected flux (2.5 Jy for 0834+555)
            expected_flux = 2.5  # Jy
            median_amp = results['amplitude_stats']['median']
            flux_ratio = median_amp / expected_flux
            
            results['flux_validation'] = {
                'expected_jy': expected_flux,
                'observed_jy': median_amp,
                'ratio': flux_ratio,
                'reasonable': 0.5 <= flux_ratio <= 2.0  # Within factor of 2
            }
            
            subtb.close()
        
    except Exception as e:
        results['error'] = f"Failed to analyze MODEL_DATA: {e}"
    
    return results


def check_spw_combine_issue(ms_path: str) -> Dict[str, Any]:
    """
    Check for SPW combination issues that could cause bandpass problems.
    
    Args:
        ms_path: Path to MS file
        
    Returns:
        Analysis of SPW combination issues
    """
    if not CASA_AVAILABLE:
        return {"error": "casacore not available"}
    
    results = {}
    
    try:
        # Check spectral window structure
        with ct.table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as tb:
            chan_freqs = tb.getcol('CHAN_FREQ')
            chan_widths = tb.getcol('CHAN_WIDTH')
            nchans = tb.getcol('NUM_CHAN')
            
            results['spw_count'] = len(nchans)
            results['spw_details'] = []
            
            for i, (freqs, widths, nch) in enumerate(zip(chan_freqs, chan_widths, nchans)):
                freq_ghz = freqs / 1e9
                width_mhz = widths / 1e6
                
                spw_info = {
                    'spw_id': i,
                    'nchans': int(nch),
                    'freq_min_ghz': float(np.min(freq_ghz)),
                    'freq_max_ghz': float(np.max(freq_ghz)),
                    'chan_width_mhz': float(np.mean(width_mhz)),
                    'total_bandwidth_mhz': float(np.sum(width_mhz))
                }
                
                results['spw_details'].append(spw_info)
        
        # Check data distribution across SPWs
        with ct.table(ms_path, readonly=True) as tb:
            data_desc_ids = tb.getcol('DATA_DESCRIPTION_ID')
            
            # Count points per DATA_DESCRIPTION_ID
            unique_ddids, counts = np.unique(data_desc_ids, return_counts=True)
            
            results['data_distribution'] = []
            for ddid, count in zip(unique_ddids, counts):
                results['data_distribution'].append({
                    'data_desc_id': int(ddid),
                    'visibility_count': int(count)
                })
        
        # Check DATA_DESCRIPTION mapping
        with ct.table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as tb:
            spw_mapping = tb.getcol('SPECTRAL_WINDOW_ID')
            
            results['ddid_to_spw_mapping'] = spw_mapping.tolist()
        
        # Analysis
        results['analysis'] = {
            'has_multiple_spws': results['spw_count'] > 1,
            'spw_frequency_gaps': [],
            'bandwidth_consistency': True
        }
        
        if results['spw_count'] > 1:
            # Check for frequency gaps
            spw_details = sorted(results['spw_details'], key=lambda x: x['freq_min_ghz'])
            
            for i in range(len(spw_details) - 1):
                curr_max = spw_details[i]['freq_max_ghz']
                next_min = spw_details[i + 1]['freq_min_ghz']
                gap_mhz = (next_min - curr_max) * 1000
                
                if gap_mhz > 1.0:  # Gap > 1 MHz
                    results['analysis']['spw_frequency_gaps'].append({
                        'between_spws': [spw_details[i]['spw_id'], spw_details[i + 1]['spw_id']],
                        'gap_mhz': gap_mhz
                    })
            
            # Check bandwidth consistency
            bandwidths = [spw['total_bandwidth_mhz'] for spw in results['spw_details']]
            bw_std = np.std(bandwidths)
            bw_mean = np.mean(bandwidths)
            
            if bw_std / bw_mean > 0.1:  # >10% variation
                results['analysis']['bandwidth_consistency'] = False
                results['analysis']['bandwidth_variation_percent'] = (bw_std / bw_mean) * 100
        
    except Exception as e:
        results['error'] = f"Failed to check SPW combination: {e}"
    
    return results


def recommend_outrigger_refants(
    antenna_analysis: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Recommend outrigger antennas for reference antenna selection.
    
    DSA-110 outrigger antennas (103-117) provide long baselines essential for
    calibration. From 0834+555 log, ant 103 was chosen but completely flagged.
    
    Priority order based on typical array geometry and performance:
    - Central outriggers (104-108): Best for most observations
    - Northern outriggers (109-113): Good azimuth coverage
    - Western/peripheral (114-117, 103): Extreme baselines
    
    Args:
        antenna_analysis: Optional list of antenna statistics from
            flagging analysis
        
    Returns:
        Dictionary with refant recommendations
    """
    # DSA-110 outrigger antennas (IDs 103-117)
    # per DSA110_Station_Coordinates.csv
    outriggers = list(range(103, 118))  # Antennas 103-117 (15 total)
    
    # Default priority order (central → peripheral for best coverage)
    default_priority = [
        104, 105, 106, 107, 108,  # Eastern (best baseline coverage)
        109, 110, 111, 112, 113,  # Northern (good azimuth)
        114, 115, 116, 103, 117   # Western/peripheral (extreme)
    ]
    
    recommendations = {
        'outrigger_antennas': outriggers,
        'default_refant_list': default_priority,
        'default_refant_string': ','.join(map(str, default_priority))
    }
    
    # If antenna statistics provided, rank by health
    if antenna_analysis:
        # Extract outrigger antenna stats
        outrigger_stats = [
            ant for ant in antenna_analysis
            if ant['antenna_id'] in outriggers
        ]        # Sort by flagged fraction (lower is better)
        healthy_outriggers = sorted(
            outrigger_stats,
            key=lambda x: x['flagged_fraction']
        )
        
        # Filter to reasonably healthy antennas (<50% flagged)
        good_outriggers = [
            ant for ant in healthy_outriggers
            if ant['flagged_fraction'] < 0.5
        ]
        
        if good_outriggers:
            # Determine health status
            def get_health_status(frac):
                if frac < 0.1:
                    return 'excellent'
                elif frac < 0.3:
                    return 'good'
                else:
                    return 'fair'
            
            recommendations['healthy_outriggers'] = [
                {
                    'antenna_id': ant['antenna_id'],
                    'flagged_fraction': ant['flagged_fraction'],
                    'health_status': get_health_status(
                        ant['flagged_fraction']
                    )
                }
                for ant in good_outriggers
            ]
            
            # Build optimized refant string from healthy antennas
            top_5 = [
                str(ant['antenna_id']) for ant in good_outriggers[:5]
            ]
            top_ant = good_outriggers[0]
            recommendations['recommended_refant'] = top_ant['antenna_id']
            recommendations['recommended_refant_string'] = ','.join(top_5)
            
            note = (
                f"Top choice: antenna {top_ant['antenna_id']} "
                f"({top_ant['flagged_fraction']*100:.1f}% flagged)"
            )
            recommendations['note'] = note
        else:
            recommendations['warning'] = (
                "No healthy outrigger antennas found (<50% flagged)"
            )
            recommendations['recommended_refant'] = default_priority[0]
            recommendations['recommended_refant_string'] = (
                recommendations['default_refant_string']
            )
            recommendations['note'] = (
                "Using default priority - check array status"
            )
        
        # Identify problematic outriggers
        bad_outriggers = [
            ant for ant in outrigger_stats
            if ant['flagged_fraction'] > 0.8
        ]
        
        if bad_outriggers:
            recommendations['problematic_outriggers'] = [
                {
                    'antenna_id': ant['antenna_id'],
                    'flagged_fraction': ant['flagged_fraction']
                }
                for ant in bad_outriggers
            ]
    else:
        # No statistics provided - use defaults
        recommendations['recommended_refant'] = default_priority[0]
        recommendations['recommended_refant_string'] = (
            recommendations['default_refant_string']
        )
        recommendations['note'] = (
            "No antenna statistics available - using default priority order"
        )
    
    return recommendations


def analyze_antenna_flagging_pattern(caltable_path: str) -> Dict[str, Any]:
    """
    Analyze antenna flagging patterns in calibration table.
    
    Includes recommendations for outrigger reference antenna selection.
    
    Args:
        caltable_path: Path to calibration table
        
    Returns:
        Analysis of antenna flagging patterns with refant recommendations
    """
    if not CASA_AVAILABLE:
        return {"error": "casacore not available"}
    
    if not Path(caltable_path).exists():
        return {"error": f"Calibration table does not exist: {caltable_path}"}
    
    results = {}
    
    try:
        with ct.table(caltable_path, readonly=True) as tb:
            antenna_ids = tb.getcol('ANTENNA1')
            flags = tb.getcol('FLAG')
            gains = tb.getcol('CPARAM')
            
            # Get unique antennas
            unique_ants = np.unique(antenna_ids)
            
            results['antenna_analysis'] = []
            results['summary'] = {
                'total_antennas': len(unique_ants),
                'completely_flagged_antennas': 0,
                'partially_flagged_antennas': 0,
                'unflagged_antennas': 0
            }
            
            for ant_id in unique_ants:
                ant_mask = antenna_ids == ant_id
                ant_flags = flags[ant_mask]
                ant_gains = gains[ant_mask]
                
                total_solutions = ant_flags.size
                flagged_solutions = np.sum(ant_flags)
                if total_solutions > 0:
                    flagged_fraction = flagged_solutions / total_solutions
                else:
                    flagged_fraction = 1.0
                
                # Calculate gain statistics for unflagged solutions
                unflagged_gains = ant_gains[~ant_flags]
                
                if len(unflagged_gains) > 0:
                    gain_amps = np.abs(unflagged_gains)
                    gain_phases = np.angle(unflagged_gains)
                    
                    gain_stats = {
                        'amp_mean': float(np.mean(gain_amps)),
                        'amp_std': float(np.std(gain_amps)),
                        'phase_mean': float(np.mean(gain_phases)),
                        'phase_std': float(np.std(gain_phases))
                    }
                else:
                    gain_stats = None
                
                ant_info = {
                    'antenna_id': int(ant_id),
                    'total_solutions': int(total_solutions),
                    'flagged_solutions': int(flagged_solutions),
                    'flagged_fraction': float(flagged_fraction),
                    'gain_stats': gain_stats
                }
                
                results['antenna_analysis'].append(ant_info)
                
                # Update summary
                if flagged_fraction >= 1.0:
                    results['summary']['completely_flagged_antennas'] += 1
                elif flagged_fraction > 0.0:
                    results['summary']['partially_flagged_antennas'] += 1
                else:
                    results['summary']['unflagged_antennas'] += 1
            
            # Overall statistics
            overall_flagged_fraction = np.sum(flags) / flags.size
            results['overall_flagged_fraction'] = (
                float(overall_flagged_fraction)
            )
            
            # Check for patterns in antenna IDs
            completely_flagged_ants = [
                ant['antenna_id'] for ant in results['antenna_analysis']
                if ant['flagged_fraction'] >= 1.0
            ]
            
            results['flagged_antenna_patterns'] = (
                analyze_antenna_id_patterns(completely_flagged_ants)
            )
            
            # Generate outrigger refant recommendations
            refant_recs = recommend_outrigger_refants(
                results['antenna_analysis']
            )
            results['refant_recommendations'] = refant_recs
        
    except Exception as e:
        results['error'] = f"Failed to analyze antenna flagging: {e}"
    
    return results


def analyze_antenna_id_patterns(flagged_ant_ids: List[int]) -> Dict[str, Any]:
    """
    Look for patterns in flagged antenna IDs that might indicate
    systematic issues.
    
    Args:
        flagged_ant_ids: List of completely flagged antenna IDs
        
    Returns:
        Analysis of antenna ID patterns
    """
    if not flagged_ant_ids:
        return {"no_patterns": "No completely flagged antennas"}
    
    flagged_ant_ids = sorted(flagged_ant_ids)
    
    patterns = {
        'consecutive_ranges': [],
        'id_distribution': {
            'low_ids': [aid for aid in flagged_ant_ids if aid < 50],
            'mid_ids': [aid for aid in flagged_ant_ids if 50 <= aid < 100],
            'high_ids': [aid for aid in flagged_ant_ids if aid >= 100]
        },
        'potential_issues': []
    }
    
    # Find consecutive ranges
    if len(flagged_ant_ids) > 1:
        start = flagged_ant_ids[0]
        end = start
        
        for i in range(1, len(flagged_ant_ids)):
            if flagged_ant_ids[i] == end + 1:
                end = flagged_ant_ids[i]
            else:
                if end > start:
                    patterns['consecutive_ranges'].append([start, end])
                start = flagged_ant_ids[i]
                end = start
        
        # Add final range
        if end > start:
            patterns['consecutive_ranges'].append([start, end])
    
    # Analyze patterns for potential issues
    if len(patterns['id_distribution']['high_ids']) > 10:
        patterns['potential_issues'].append(
            "Many high antenna IDs flagged - possible hardware bank issue"
        )
    
    if patterns['consecutive_ranges']:
        patterns['potential_issues'].append(
            "Consecutive antenna ranges flagged - "
            "possible systematic hardware issue"
        )
    
    if len(flagged_ant_ids) > 30:
        patterns['potential_issues'].append(
            "Excessive antenna flagging (>30 antennas) - "
            "check array status"
        )
    
    return patterns


def diagnose_calibration_failure(
    ms_path: str,
    caltable_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive diagnosis of calibration failure for 0834+555.
    
    Args:
        ms_path: Path to MS file
        caltable_path: Optional path to calibration table
        
    Returns:
        Comprehensive diagnosis report
    """
    print("🔍 Diagnosing 0834+555 Calibration Failure")
    print("=" * 50)
    
    diagnosis = {
        'ms_path': ms_path,
        'caltable_path': caltable_path,
        'timestamp': '2025-11-05'
    }
    
    # 1. MS Structure Analysis
    print("\n1️⃣ Analyzing MS Structure...")
    ms_analysis = analyze_ms_structure(ms_path)
    diagnosis['ms_structure'] = ms_analysis
    
    if 'error' not in ms_analysis:
        print(f"   ✓ Found {ms_analysis['fields']['count']} field(s)")
        print(f"   ✓ Found {ms_analysis['spectral_windows']['count']} SPW(s)")
        print(f"   ✓ Found {ms_analysis['antennas']['count']} antenna(s)")
    else:
        print(f"   ❌ Error: {ms_analysis['error']}")
    
    # 2. MODEL_DATA Quality Analysis
    print("\n2️⃣ Analyzing MODEL_DATA Quality...")
    model_analysis = analyze_model_data_quality(ms_path, field_id=0)
    diagnosis['model_data'] = model_analysis
    
    if 'error' not in model_analysis:
        flux_validation = model_analysis.get('flux_validation', {})
        flux_ok = flux_validation.get('reasonable', False)
        median_flux = model_analysis['amplitude_stats']['median']
        print(f"   ✓ MODEL_DATA flux: {median_flux:.3f} Jy")
        status = 'PASS' if flux_ok else 'FAIL'
        icon = '✓' if flux_ok else '❌'
        print(f"   {icon} Flux validation: {status}")
    else:
        print(f"   ❌ Error: {model_analysis['error']}")
    
    # 3. SPW Combination Analysis
    print("\n3️⃣ Analyzing SPW Combination...")
    spw_analysis = check_spw_combine_issue(ms_path)
    diagnosis['spw_analysis'] = spw_analysis
    
    if 'error' not in spw_analysis:
        print(f"   ✓ Found {spw_analysis['spw_count']} SPWs")
        if spw_analysis['analysis']['spw_frequency_gaps']:
            ngaps = len(spw_analysis['analysis']['spw_frequency_gaps'])
            print(f"   ⚠️  Found {ngaps} frequency gaps")
        else:
            print("   ✓ No significant frequency gaps")
    else:
        print(f"   ❌ Error: {spw_analysis['error']}")
    
    # 4. Calibration Table Analysis (if provided)
    if caltable_path:
        print("\n4️⃣ Analyzing Calibration Table...")
        cal_analysis = analyze_antenna_flagging_pattern(caltable_path)
        diagnosis['calibration_table'] = cal_analysis
        
        if 'error' not in cal_analysis:
            flagged_frac = cal_analysis['overall_flagged_fraction']
            summary = cal_analysis['summary']
            completely_flagged = summary['completely_flagged_antennas']
            print(f"   ✓ Overall flagged fraction: {flagged_frac:.1%}")
            print(f"   ✓ Completely flagged antennas: {completely_flagged}")
            
            if completely_flagged > 20:
                print("   ⚠️  Excessive antenna flagging detected")
            
            # Display refant recommendations if available
            if 'refant_recommendations' in cal_analysis:
                refant = cal_analysis['refant_recommendations']
                print("\n   📡 Outrigger Refant Recommendations:")
                if 'recommended_refant' in refant:
                    rec_ant = refant['recommended_refant']
                    rec_str = refant['recommended_refant_string']
                    print(f"      Best: antenna {rec_ant}")
                    print(f"      Fallback chain: {rec_str}")
                    if 'note' in refant:
                        print(f"      Note: {refant['note']}")
                else:
                    def_str = refant['default_refant_string']
                    print(f"      Default: {def_str}")
        else:
            print(f"   ❌ Error: {cal_analysis['error']}")
    
    # 5. Generate Recommendations
    print("\n💡 Diagnosis Summary and Recommendations")
    print("-" * 40)
    
    recommendations = []
    
    # Check for common issues based on 0834+555 log
    if 'error' not in ms_analysis:
        spw_count = ms_analysis['spectral_windows']['count']
        if spw_count == 16:
            recommendations.append(
                "SPW Structure: 16 SPWs detected - "
                "verify combine-spw is working correctly"
            )
    
    if 'error' not in model_analysis:
        flux_validation = model_analysis.get('flux_validation', {})
        if not flux_validation.get('reasonable', False):
            obs_flux = flux_validation.get('observed_jy', 0)
            recommendations.append(
                f"MODEL_DATA Issue: Flux {obs_flux:.3f} Jy "
                f"differs from expected 2.5 Jy"
            )
    
    if caltable_path and 'error' not in diagnosis.get('calibration_table', {}):
        cal_analysis = diagnosis['calibration_table']
        if cal_analysis['overall_flagged_fraction'] > 0.8:
            recommendations.append(
                "Excessive Flagging: >80% solutions flagged - "
                "check data quality and flagging criteria"
            )
        
        summary = cal_analysis['summary']
        completely_flagged = summary['completely_flagged_antennas']
        if completely_flagged > 20:
            recommendations.append(
                f"Antenna Issues: {completely_flagged} antennas "
                f"completely flagged - check array status"
            )
        
        # Add refant recommendation
        if 'refant_recommendations' in cal_analysis:
            refant = cal_analysis['refant_recommendations']
            if 'recommended_refant' in refant:
                rec_str = refant['recommended_refant_string']
                recommendations.append(
                    f"Refant Selection: Use outrigger antennas - "
                    f"recommended: {rec_str}"
                )
            else:
                def_str = refant['default_refant_string']
                recommendations.append(
                    f"Refant Selection: Use outrigger antennas - "
                    f"default chain: {def_str}"
                )
    
    if not recommendations:
        recommendations.append(
            "No obvious issues detected - further investigation needed"
        )
    
    diagnosis['recommendations'] = recommendations
    
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    return diagnosis


def main():
    """Main diagnostic function."""
    
    if len(sys.argv) < 2:
        print(
            "Usage: python debug_0834_calibration.py "
            "<ms_path> [caltable_path]"
        )
        print("\nExample:")
        print(
            "  python debug_0834_calibration.py "
            "/data/ms/2025-10-29T13:54:17.ms"
        )
        print(
            "  python debug_0834_calibration.py "
            "/data/ms/2025-10-29T13:54:17.ms "
            "/data/ms/2025-10-29T13:54:17_0_bpcal"
        )
        sys.exit(1)
    
    ms_path = sys.argv[1]
    caltable_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Run comprehensive diagnosis
    diagnosis = diagnose_calibration_failure(ms_path, caltable_path)
    
    print("\n📋 Full diagnosis saved to debug_results for further analysis")
    
    # Save detailed results (if needed for debugging)
    import json
    output_file = f"0834_calibration_diagnosis_{Path(ms_path).stem}.json"
    with open(output_file, 'w') as f:
        json.dump(diagnosis, f, indent=2, default=str)
    
    print(f"📄 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
