#!/usr/bin/env python3
"""
Enhanced Field Naming and Calibrator Detection for DSA-110 Pipeline.

This module implements the recommendations from the MS field structure
analysis:
1. Add calibrator name detection and field name updating in conversion
   workflow
2. Use catalog lookup results to set meaningful field names
3. Ensure field names match expected calibrator names for CASA calibration
   tasks

Based on analysis findings that:
- Field names are NOT automatically updated for calibrator sources
- Direct-subband approach creates generic "meridian_icrs" field names
- Calibrator information is tracked separately from field names
"""

import sys
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
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
    logger.warning("casacore not available - limiting functionality")
    CASA_AVAILABLE = False


def detect_calibrator_from_catalog(
        ra_deg: float, dec_deg: float,
        catalog_path: str,
        tolerance_arcmin: float = 5.0) -> Optional[Dict[str, Any]]:
    """
    Detect calibrator source from catalog based on position.
    
    Args:
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        catalog_path: Path to calibrator catalog (SQLite or CSV)
        tolerance_arcmin: Search tolerance in arcminutes
        
    Returns:
        Calibrator info dict if found, None otherwise
    """
    import sqlite3
    from pathlib import Path
    
    if not Path(catalog_path).exists():
        logger.error(f"Catalog not found: {catalog_path}")
        return None
    
    try:
        # Assume SQLite catalog (like vla_calibrators.sqlite3)
        conn = sqlite3.connect(catalog_path)
        cursor = conn.cursor()
        
        # Query for nearby sources within tolerance
        # Using simple angular separation approximation
        tolerance_deg = tolerance_arcmin / 60.0
        
        query = """
        SELECT name, ra_deg, dec_deg, flux_jy, freq_mhz
        FROM calibrators
        WHERE ABS(ra_deg - ?) < ? AND ABS(dec_deg - ?) < ?
        ORDER BY
            (ra_deg - ?) * (ra_deg - ?) + (dec_deg - ?) * (dec_deg - ?)
        LIMIT 1
        """
        
        cursor.execute(query, (
            ra_deg, tolerance_deg, dec_deg, tolerance_deg,
            ra_deg, ra_deg, dec_deg, dec_deg
        ))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            name, cat_ra, cat_dec, flux, freq = result
            
            # Calculate actual separation
            delta_ra = (ra_deg - cat_ra) * np.cos(np.radians(dec_deg))
            delta_dec = dec_deg - cat_dec
            separation_arcmin = np.sqrt(delta_ra**2 + delta_dec**2) * 60.0
            
            if separation_arcmin <= tolerance_arcmin:
                return {
                    'name': name,
                    'ra_deg': cat_ra,
                    'dec_deg': cat_dec,
                    'flux_jy': flux,
                    'freq_mhz': freq,
                    'separation_arcmin': separation_arcmin
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error querying catalog: {e}")
        return None


def get_ms_phase_center(
        ms_path: str, field_id: int = 0) -> Optional[Tuple[float, float]]:
    """
    Get phase center coordinates from MS FIELD table.
    
    Args:
        ms_path: Path to MS file
        field_id: Field ID to query (default 0)
        
    Returns:
        (ra_deg, dec_deg) tuple if successful, None otherwise
    """
    if not CASA_AVAILABLE:
        logger.error("casacore not available")
        return None
    
    try:
        with ct.table(f"{ms_path}::FIELD", readonly=True) as tb:
            if field_id >= tb.nrows():
                logger.error(f"Field ID {field_id} not found in {ms_path}")
                return None
            
            # Get PHASE_DIR (or REFERENCE_DIR if needed)
            phase_dirs = tb.getcol('PHASE_DIR')
            
            # PHASE_DIR shape is typically (nfields, npol, 2)
            # We want the first polarization [0] and RA/Dec [0,1]
            ra_rad = phase_dirs[field_id, 0, 0]
            dec_rad = phase_dirs[field_id, 0, 1]
            
            # Convert to degrees
            ra_deg = np.degrees(ra_rad)
            dec_deg = np.degrees(dec_rad)
            
            return ra_deg, dec_deg
            
    except Exception as e:
        logger.error(f"Error reading phase center: {e}")
        return None


def update_ms_field_name(
        ms_path: str, 
        field_id: int, 
        new_name: str) -> bool:
    """
    Update field name in MS FIELD table.
    
    Args:
        ms_path: Path to MS file
        field_id: Field ID to update
        new_name: New field name
        
    Returns:
        True if successful, False otherwise
    """
    if not CASA_AVAILABLE:
        logger.error("casacore not available")
        return False
    
    try:
        with ct.table(f"{ms_path}::FIELD", readonly=False) as tb:
            if field_id >= tb.nrows():
                logger.error(f"Field ID {field_id} not found")
                return False
            
            # Get current names
            names = tb.getcol('NAME')
            old_name = names[field_id]
            
            # Update name
            names[field_id] = new_name
            tb.putcol('NAME', names)
            
            logger.info(f"Updated field {field_id}: '{old_name}' -> '{new_name}'")
            return True
            
    except Exception as e:
        logger.error(f"Error updating field name: {e}")
        return False


def enhance_ms_field_names(
        ms_path: str, 
        catalog_path: str,
        tolerance_arcmin: float = 5.0,
        dry_run: bool = False) -> Dict[str, Any]:
    """
    Enhance MS field names by detecting calibrators from catalog.
    
    Args:
        ms_path: Path to MS file
        catalog_path: Path to calibrator catalog
        tolerance_arcmin: Search tolerance for calibrator matching
        dry_run: If True, don't actually update field names
        
    Returns:
        Dictionary with enhancement results
    """
    logger.info(f"Enhancing field names for: {ms_path}")
    logger.info(f"Using catalog: {catalog_path}")
    
    results = {
        'ms_path': ms_path,
        'catalog_path': catalog_path,
        'tolerance_arcmin': tolerance_arcmin,
        'dry_run': dry_run,
        'fields_processed': [],
        'calibrators_detected': [],
        'fields_updated': [],
        'errors': []
    }
    
    if not CASA_AVAILABLE:
        results['errors'].append("casacore not available")
        return results
    
    if not Path(ms_path).exists():
        results['errors'].append(f"MS not found: {ms_path}")
        return results
    
    if not Path(catalog_path).exists():
        results['errors'].append(f"Catalog not found: {catalog_path}")
        return results
    
    try:
        # Get all fields in MS
        with ct.table(f"{ms_path}::FIELD", readonly=True) as tb:
            field_names = tb.getcol('NAME')
            nfields = len(field_names)
        
        logger.info(f"Found {nfields} field(s) to process")
        
        # Process each field
        for field_id in range(nfields):
            current_name = field_names[field_id]
            
            logger.info(f"Processing field {field_id}: '{current_name}'")
            
            # Get phase center
            coords = get_ms_phase_center(ms_path, field_id)
            if not coords:
                results['errors'].append(
                    f"Could not get coordinates for field {field_id}"
                )
                continue
            
            ra_deg, dec_deg = coords
            
            # Try to detect calibrator
            calibrator = detect_calibrator_from_catalog(
                ra_deg, dec_deg, catalog_path, tolerance_arcmin
            )
            
            field_info = {
                'field_id': field_id,
                'current_name': current_name,
                'ra_deg': ra_deg,
                'dec_deg': dec_deg,
                'calibrator_detected': calibrator is not None
            }
            
            if calibrator:
                cal_name = calibrator['name']
                separation = calibrator['separation_arcmin']
                
                logger.info(
                    f"  ✓ Detected calibrator: {cal_name} "
                    f"(separation: {separation:.2f} arcmin)"
                )
                
                field_info.update({
                    'calibrator_name': cal_name,
                    'separation_arcmin': separation,
                    'calibrator_flux_jy': calibrator['flux_jy']
                })
                
                results['calibrators_detected'].append(calibrator)
                
                # Update field name if needed
                if current_name != cal_name:
                    if not dry_run:
                        success = update_ms_field_name(ms_path, field_id, cal_name)
                        if success:
                            field_info['name_updated'] = True
                            field_info['new_name'] = cal_name
                            results['fields_updated'].append(field_info)
                        else:
                            results['errors'].append(
                                f"Failed to update field {field_id} name"
                            )
                    else:
                        logger.info(f"  [DRY RUN] Would update: '{current_name}' -> '{cal_name}'")
                        field_info['name_updated'] = False
                        field_info['proposed_name'] = cal_name
                else:
                    logger.info(f"  ✓ Field name already correct: '{cal_name}'")
                    field_info['name_updated'] = False
                    field_info['already_correct'] = True
            else:
                logger.info(f"  ❌ No calibrator found within {tolerance_arcmin} arcmin")
                field_info['calibrator_name'] = None
            
            results['fields_processed'].append(field_info)
    
    except Exception as e:
        error_msg = f"Error processing MS: {e}"
        logger.error(error_msg)
        results['errors'].append(error_msg)
    
    # Summary
    n_detected = len(results['calibrators_detected'])
    n_updated = len(results['fields_updated'])
    
    logger.info(f"Enhancement complete:")
    logger.info(f"  Calibrators detected: {n_detected}")
    logger.info(f"  Fields updated: {n_updated}")
    logger.info(f"  Errors: {len(results['errors'])}")
    
    return results


def update_conversion_workflow_field_names():
    """
    Provide recommendations for updating conversion workflow to use enhanced field names.
    
    This function documents the integration points where enhanced field naming
    should be added to the DSA-110 pipeline.
    """
    
    recommendations = {
        'integration_points': [
            {
                'file': 'src/dsa110_contimg/conversion/strategies/direct_subband.py',
                'location': 'Line ~490 (phase_center_name assignment)',
                'current': 'Uses "meridian_icrs" or basename(part_out_path)',
                'enhancement': 'Call enhance_ms_field_names() after MS creation',
                'priority': 'HIGH'
            },
            {
                'file': 'src/dsa110_contimg/conversion/uvh5_to_ms.py', 
                'location': 'Line ~357 (phase() call with cat_name)',
                'current': 'Uses cat_name parameter from phase call',
                'enhancement': 'Integrate catalog lookup for field naming',
                'priority': 'MEDIUM'
            },
            {
                'file': 'src/dsa110_contimg/core/conversion/streaming_converter.py',
                'location': 'After MS creation in process_observation_group()',
                'current': 'Only tracks has_calibrator, calibrators columns',
                'enhancement': 'Add field name enhancement step',
                'priority': 'HIGH'
            }
        ],
        'workflow_changes': [
            {
                'step': 'Post-conversion enhancement',
                'description': 'After MS is created, run enhance_ms_field_names()',
                'benefits': ['Meaningful field names', 'Better CASA calibration', 'Clearer data provenance']
            },
            {
                'step': 'Catalog integration',
                'description': 'Use existing catalog_path from calibrator detection',
                'benefits': ['Consistent calibrator naming', 'Automated field identification']
            },
            {
                'step': 'Configuration option',
                'description': 'Add enable_field_enhancement config option',
                'benefits': ['Optional feature', 'Backward compatibility']
            }
        ],
        'implementation_template': '''
# Integration example for direct_subband.py:

def write_part_ms(self, ...):
    # ... existing MS creation code ...
    
    # Enhanced field naming (NEW)
    if self.config.get('enable_field_enhancement', False):
        catalog_path = self.config.get('calibrator_catalog_path')
        if catalog_path:
            from .enhanced_field_naming import enhance_ms_field_names
            
            results = enhance_ms_field_names(
                ms_path=part_out_path,
                catalog_path=catalog_path,
                tolerance_arcmin=5.0,
                dry_run=False
            )
            
            if results['calibrators_detected']:
                logger.info(f"Enhanced field names: {len(results['fields_updated'])} updated")
        '''
    }
    
    return recommendations


def main():
    """Main function for enhanced field naming."""
    
    # Check for recommendations mode first
    if '--recommendations' in sys.argv:
        recommendations = update_conversion_workflow_field_names()
        
        print("🔧 Enhanced Field Naming Integration Recommendations")
        print("=" * 60)
        
        print("\n📍 Integration Points:")
        for point in recommendations['integration_points']:
            print(f"\n  {point['priority']} PRIORITY: {point['file']}")
            print(f"    Location: {point['location']}")
            print(f"    Current: {point['current']}")
            print(f"    Enhancement: {point['enhancement']}")
        
        print("\n🔄 Workflow Changes:")
        for change in recommendations['workflow_changes']:
            print(f"\n  {change['step']}:")
            print(f"    {change['description']}")
            print(f"    Benefits: {', '.join(change['benefits'])}")
        
        print("\n💻 Implementation Template:")
        print(recommendations['implementation_template'])
        
        return
    
    if len(sys.argv) < 3:
        print("Enhanced Field Naming for DSA-110 Pipeline")
        print("=" * 50)
        print()
        print("Usage:")
        print("  python enhanced_field_naming.py <ms_path> <catalog_path> [options]")
        print()
        print("Options:")
        print("  --tolerance-arcmin FLOAT    Search tolerance (default: 5.0)")
        print("  --dry-run                   Show what would be changed without modifying")
        print("  --recommendations           Show integration recommendations")
        print()
        print("Examples:")
        print("  # Enhance field names")
        print("  python enhanced_field_naming.py /data/ms/obs.ms /data/catalogs/vla_calibrators.sqlite3")
        print()
        print("  # Dry run to see what would change")
        print("  python enhanced_field_naming.py /data/ms/obs.ms /data/catalogs/vla_calibrators.sqlite3 --dry-run")
        print()
        print("  # Show integration recommendations")
        print("  python enhanced_field_naming.py --recommendations")
        sys.exit(1)
    
    # Check for recommendations mode
    if '--recommendations' in sys.argv:
        recommendations = update_conversion_workflow_field_names()
        
        print("🔧 Enhanced Field Naming Integration Recommendations")
        print("=" * 60)
        
        print("\n📍 Integration Points:")
        for point in recommendations['integration_points']:
            print(f"\n  {point['priority']} PRIORITY: {point['file']}")
            print(f"    Location: {point['location']}")
            print(f"    Current: {point['current']}")
            print(f"    Enhancement: {point['enhancement']}")
        
        print("\n🔄 Workflow Changes:")
        for change in recommendations['workflow_changes']:
            print(f"\n  {change['step']}:")
            print(f"    {change['description']}")
            print(f"    Benefits: {', '.join(change['benefits'])}")
        
        print("\n💻 Implementation Template:")
        print(recommendations['implementation_template'])
        
        return
    
    # Parse arguments
    ms_path = sys.argv[1]
    catalog_path = sys.argv[2]
    
    tolerance_arcmin = 5.0
    dry_run = False
    
    for i, arg in enumerate(sys.argv[3:], 3):
        if arg == '--tolerance-arcmin' and i + 1 < len(sys.argv):
            tolerance_arcmin = float(sys.argv[i + 1])
        elif arg == '--dry-run':
            dry_run = True
    
    # Run enhancement
    results = enhance_ms_field_names(
        ms_path=ms_path,
        catalog_path=catalog_path,
        tolerance_arcmin=tolerance_arcmin,
        dry_run=dry_run
    )
    
    # Report results
    print(f"\n📊 Enhancement Results")
    print("=" * 30)
    print(f"Fields processed: {len(results['fields_processed'])}")
    print(f"Calibrators detected: {len(results['calibrators_detected'])}")
    print(f"Fields updated: {len(results['fields_updated'])}")
    
    if results['errors']:
        print(f"Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  ❌ {error}")
    
    # Save detailed results
    import json
    output_file = f"field_enhancement_{Path(ms_path).stem}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()