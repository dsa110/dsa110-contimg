#!/usr/bin/env python3
"""
End-to-End Pipeline Test Script

This script tests the complete DSA-110 continuum imaging pipeline:
1. HDF5 → MS conversion using unified MS creation
2. Enhanced calibration using the new calibration pipeline
3. Validation and quality assessment
4. Comprehensive reporting

Usage:
    python scripts/test_end_to_end_pipeline.py
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.utils.logging import get_logger
from dsa110.pipeline.orchestrator import PipelineOrchestrator
from dsa110.casa.enhanced_calibration_pipeline import EnhancedCalibrationPipeline
from dsa110.data_ingestion.unified_ms_creation import UnifiedMSCreationManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

class EndToEndPipelineTester:
    """Comprehensive end-to-end pipeline tester."""
    
    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        """Initialize the tester with configuration."""
        self.config_path = config_path
        self.results = {
            'test_start_time': datetime.now(),
            'test_end_time': None,
            'total_duration': None,
            'hdf5_to_ms_results': {},
            'calibration_results': {},
            'validation_results': {},
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        # Test data paths
        self.hdf5_test_dir = "/data/incoming_test"
        self.ms_output_dir = Path("ms_stage1")
        self.calibrated_output_dir = Path("ms_stage2")
        
        # Create output directories
        self.ms_output_dir.mkdir(exist_ok=True)
        self.calibrated_output_dir.mkdir(exist_ok=True)
        
        logger.info("End-to-End Pipeline Tester initialized")
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run the complete end-to-end pipeline test."""
        logger.info("=" * 80)
        logger.info("STARTING COMPREHENSIVE END-TO-END PIPELINE TEST")
        logger.info("=" * 80)
        
        try:
            # Step 1: Initialize pipeline orchestrator
            logger.info("\nSTEP 1: Initializing Pipeline Orchestrator")
            await self._initialize_pipeline()
            
            # Step 2: Test HDF5 to MS conversion
            logger.info("\nSTEP 2: Testing HDF5 to MS Conversion")
            await self._test_hdf5_to_ms_conversion()
            
            # Step 3: Test enhanced calibration
            logger.info("\nSTEP 3: Testing Enhanced Calibration")
            await self._test_enhanced_calibration()
            
            # Step 4: Validate results
            logger.info("\nSTEP 4: Validating Results")
            await self._validate_results()
            
            # Step 5: Generate summary
            logger.info("\nSTEP 5: Generating Summary")
            await self._generate_summary()
            
            self.results['test_end_time'] = datetime.now()
            self.results['total_duration'] = (
                self.results['test_end_time'] - self.results['test_start_time']
            ).total_seconds()
            
            logger.info("=" * 80)
            logger.info("END-TO-END PIPELINE TEST COMPLETED")
            logger.info("=" * 80)
            
            return self.results
            
        except Exception as e:
            logger.error(f"End-to-end test failed: {e}")
            self.results['errors'].append(f"Test failed: {e}")
            self.results['test_end_time'] = datetime.now()
            return self.results
    
    async def _initialize_pipeline(self):
        """Initialize the pipeline orchestrator."""
        try:
            # Load configuration from YAML file
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.orchestrator = PipelineOrchestrator(config)
            logger.info("✅ Pipeline orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize pipeline: {e}")
            raise
    
    async def _test_hdf5_to_ms_conversion(self):
        """Test HDF5 to MS conversion for all available timestamps."""
        logger.info("Testing HDF5 to MS conversion...")
        
        # Find all unique timestamps
        hdf5_files = list(Path(self.hdf5_test_dir).glob("*.hdf5"))
        timestamps = set()
        
        for hdf5_file in hdf5_files:
            # Extract timestamp from filename (format: YYYY-MM-DDTHH:MM:SS_sbXX.hdf5)
            timestamp = hdf5_file.stem.split('_sb')[0]
            timestamps.add(timestamp)
        
        logger.info(f"Found {len(timestamps)} unique timestamps: {sorted(timestamps)}")
        
        for timestamp in sorted(timestamps):
            logger.info(f"\nProcessing timestamp: {timestamp}")
            
            try:
                # Process this timestamp
                ms_files = await self.orchestrator.process_hdf5_to_ms(
                    self.hdf5_test_dir, timestamp, timestamp
                )
                
                if ms_files:
                    self.results['hdf5_to_ms_results'][timestamp] = {
                        'success': True,
                        'ms_files': ms_files,
                        'count': len(ms_files),
                        'errors': []
                    }
                    logger.info(f"✅ Successfully created {len(ms_files)} MS files for {timestamp}")
                else:
                    self.results['hdf5_to_ms_results'][timestamp] = {
                        'success': False,
                        'ms_files': [],
                        'count': 0,
                        'errors': ['No MS files created']
                    }
                    logger.error(f"❌ No MS files created for {timestamp}")
                    
            except Exception as e:
                error_msg = f"Failed to process {timestamp}: {e}"
                logger.error(f"❌ {error_msg}")
                self.results['hdf5_to_ms_results'][timestamp] = {
                    'success': False,
                    'ms_files': [],
                    'count': 0,
                    'errors': [error_msg]
                }
                self.results['errors'].append(error_msg)
    
    async def _test_enhanced_calibration(self):
        """Test enhanced calibration on all created MS files."""
        logger.info("Testing enhanced calibration...")
        
        # Initialize calibration pipeline
        try:
            # Load configuration from YAML file
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            calibration_pipeline = EnhancedCalibrationPipeline(config)
            logger.info("✅ Enhanced calibration pipeline initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize calibration pipeline: {e}")
            raise
        
        # Process all MS files
        for timestamp, ms_result in self.results['hdf5_to_ms_results'].items():
            if not ms_result['success']:
                logger.warning(f"Skipping calibration for {timestamp} (MS creation failed)")
                continue
                
            logger.info(f"\nCalibrating MS files for {timestamp}")
            
            for ms_file in ms_result['ms_files']:
                try:
                    # Create output path for calibrated MS
                    ms_path = Path(ms_file)
                    calibrated_path = self.calibrated_output_dir / f"{ms_path.stem}_calibrated.ms"
                    
                    logger.info(f"Calibrating: {ms_file} → {calibrated_path}")
                    
                    # Run calibration
                    calibration_result = await calibration_pipeline.perform_enhanced_calibration(
                        str(ms_file), str(calibrated_path)
                    )
                    
                    if calibration_result['success']:
                        self.results['calibration_results'][str(ms_file)] = {
                            'success': True,
                            'calibrated_ms': str(calibrated_path),
                            'calibration_tables': calibration_result.get('calibration_tables', []),
                            'reference_antenna': calibration_result.get('reference_antenna', 'unknown'),
                            'uv_range': calibration_result.get('uv_range', 'unknown'),
                            'errors': []
                        }
                        logger.info(f"✅ Successfully calibrated {ms_file}")
                    else:
                        error_msg = f"Calibration failed for {ms_file}: {calibration_result.get('error', 'Unknown error')}"
                        logger.error(f"❌ {error_msg}")
                        self.results['calibration_results'][str(ms_file)] = {
                            'success': False,
                            'calibrated_ms': None,
                            'calibration_tables': [],
                            'reference_antenna': 'unknown',
                            'uv_range': 'unknown',
                            'errors': [error_msg]
                        }
                        self.results['errors'].append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Calibration exception for {ms_file}: {e}"
                    logger.error(f"❌ {error_msg}")
                    self.results['calibration_results'][str(ms_file)] = {
                        'success': False,
                        'calibrated_ms': None,
                        'calibration_tables': [],
                        'reference_antenna': 'unknown',
                        'uv_range': 'unknown',
                        'errors': [error_msg]
                    }
                    self.results['errors'].append(error_msg)
    
    async def _validate_results(self):
        """Validate the results of the pipeline."""
        logger.info("Validating pipeline results...")
        
        # Count successful operations
        successful_ms_creations = sum(1 for result in self.results['hdf5_to_ms_results'].values() if result['success'])
        total_ms_creations = len(self.results['hdf5_to_ms_results'])
        
        successful_calibrations = sum(1 for result in self.results['calibration_results'].values() if result['success'])
        total_calibrations = len(self.results['calibration_results'])
        
        # File size validation
        total_ms_size = 0
        total_calibrated_size = 0
        
        for ms_result in self.results['hdf5_to_ms_results'].values():
            for ms_file in ms_result['ms_files']:
                if Path(ms_file).exists():
                    total_ms_size += sum(f.stat().st_size for f in Path(ms_file).rglob('*') if f.is_file())
        
        for cal_result in self.results['calibration_results'].values():
            if cal_result['calibrated_ms'] and Path(cal_result['calibrated_ms']).exists():
                total_calibrated_size += sum(f.stat().st_size for f in Path(cal_result['calibrated_ms']).rglob('*') if f.is_file())
        
        self.results['validation_results'] = {
            'ms_creation_success_rate': successful_ms_creations / total_ms_creations if total_ms_creations > 0 else 0,
            'calibration_success_rate': successful_calibrations / total_calibrations if total_calibrations > 0 else 0,
            'total_ms_files_created': successful_ms_creations,
            'total_calibrated_files': successful_calibrations,
            'total_ms_size_gb': total_ms_size / (1024**3),
            'total_calibrated_size_gb': total_calibrated_size / (1024**3),
            'total_errors': len(self.results['errors']),
            'total_warnings': len(self.results['warnings'])
        }
        
        logger.info(f"✅ Validation complete:")
        logger.info(f"   MS Creation Success Rate: {self.results['validation_results']['ms_creation_success_rate']:.1%}")
        logger.info(f"   Calibration Success Rate: {self.results['validation_results']['calibration_success_rate']:.1%}")
        logger.info(f"   Total MS Files Created: {self.results['validation_results']['total_ms_files_created']}")
        logger.info(f"   Total Calibrated Files: {self.results['validation_results']['total_calibrated_files']}")
        logger.info(f"   Total MS Size: {self.results['validation_results']['total_ms_size_gb']:.2f} GB")
        logger.info(f"   Total Calibrated Size: {self.results['validation_results']['total_calibrated_size_gb']:.2f} GB")
    
    async def _generate_summary(self):
        """Generate a comprehensive summary of the test results."""
        logger.info("Generating test summary...")
        
        # Overall success rate
        total_operations = len(self.results['hdf5_to_ms_results']) + len(self.results['calibration_results'])
        successful_operations = (
            self.results['validation_results']['total_ms_files_created'] + 
            self.results['validation_results']['total_calibrated_files']
        )
        overall_success_rate = successful_operations / total_operations if total_operations > 0 else 0
        
        self.results['summary'] = {
            'overall_success_rate': overall_success_rate,
            'test_duration_seconds': self.results['total_duration'],
            'pipeline_status': 'PASS' if overall_success_rate >= 0.8 else 'FAIL',
            'key_achievements': [],
            'issues_found': [],
            'recommendations': []
        }
        
        # Key achievements
        if self.results['validation_results']['total_ms_files_created'] > 0:
            self.results['summary']['key_achievements'].append("Successfully created MS files from HDF5 data")
        
        if self.results['validation_results']['total_calibrated_files'] > 0:
            self.results['summary']['key_achievements'].append("Successfully calibrated MS files")
        
        if self.results['validation_results']['ms_creation_success_rate'] >= 0.8:
            self.results['summary']['key_achievements'].append("High MS creation success rate")
        
        if self.results['validation_results']['calibration_success_rate'] >= 0.8:
            self.results['summary']['key_achievements'].append("High calibration success rate")
        
        # Issues found
        if self.results['errors']:
            self.results['summary']['issues_found'].extend(self.results['errors'])
        
        if self.results['warnings']:
            self.results['summary']['issues_found'].extend(self.results['warnings'])
        
        # Recommendations
        if overall_success_rate < 0.8:
            self.results['summary']['recommendations'].append("Investigate and fix pipeline errors")
        
        if self.results['validation_results']['total_ms_size_gb'] < 1.0:
            self.results['summary']['recommendations'].append("Verify MS file sizes are reasonable")
        
        if self.results['validation_results']['total_calibrated_size_gb'] < 1.0:
            self.results['summary']['recommendations'].append("Verify calibrated MS file sizes are reasonable")
        
        logger.info(f"\n📊 PIPELINE TEST SUMMARY:")
        logger.info(f"   Overall Success Rate: {overall_success_rate:.1%}")
        logger.info(f"   Test Duration: {self.results['total_duration']:.1f} seconds")
        logger.info(f"   Pipeline Status: {self.results['summary']['pipeline_status']}")
        logger.info(f"   Key Achievements: {len(self.results['summary']['key_achievements'])}")
        logger.info(f"   Issues Found: {len(self.results['summary']['issues_found'])}")
        logger.info(f"   Recommendations: {len(self.results['summary']['recommendations'])}")

async def main():
    """Main function to run the end-to-end pipeline test."""
    tester = EndToEndPipelineTester()
    results = await tester.run_comprehensive_test()
    
    # Print final results
    print("\n" + "=" * 80)
    print("FINAL TEST RESULTS")
    print("=" * 80)
    print(f"Pipeline Status: {results['summary']['pipeline_status']}")
    print(f"Overall Success Rate: {results['summary']['overall_success_rate']:.1%}")
    duration = results.get('total_duration', 0)
    if duration is not None:
        print(f"Test Duration: {duration:.1f} seconds")
    else:
        print("Test Duration: N/A")
    print(f"MS Files Created: {results['validation_results']['total_ms_files_created']}")
    print(f"Calibrated Files: {results['validation_results']['total_calibrated_files']}")
    print(f"Total Errors: {results['validation_results']['total_errors']}")
    
    if results['summary']['key_achievements']:
        print("\nKey Achievements:")
        for achievement in results['summary']['key_achievements']:
            print(f"  ✅ {achievement}")
    
    if results['summary']['issues_found']:
        print("\nIssues Found:")
        for issue in results['summary']['issues_found']:
            print(f"  ❌ {issue}")
    
    if results['summary']['recommendations']:
        print("\nRecommendations:")
        for rec in results['summary']['recommendations']:
            print(f"  💡 {rec}")
    
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
