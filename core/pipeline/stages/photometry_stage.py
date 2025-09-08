# core/pipeline/stages/photometry_stage.py
"""
Photometry stage for DSA-110 pipeline.

This module handles photometry operations including source identification,
aperture photometry, and relative flux calculations.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import warnings
from astropy.time import Time
from astropy.table import Table
from astropy.coordinates import SkyCoord
import astropy.units as u

from ...utils.logging import get_logger
from ..exceptions import PhotometryError
from ...data_ingestion.photometry import PhotometryManager

logger = get_logger(__name__)


class PhotometryStage:
    """
    Handles photometry operations for the pipeline.
    
    This class consolidates photometry logic from the original
    photometry.py module and provides a cleaner interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the photometry stage.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.photometry_config = config.get('photometry', {})
        self.paths_config = config.get('paths', {})
        self.photometry_manager = PhotometryManager(config)
    
    async def process_mosaic(self, mosaic_fits_path: str, mosaic_time: Time, 
                           max_retries: int = 3) -> Dict[str, Any]:
        """
        Process a mosaic for photometry with retry logic and quality assessment.
        
        This includes source identification, aperture photometry,
        relative flux calculation, and result storage.
        
        Args:
            mosaic_fits_path: Path to the mosaic FITS file
            mosaic_time: Time of the mosaic observation
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary containing photometry results
        """
        logger.info(f"Processing photometry for mosaic: {os.path.basename(mosaic_fits_path)}")
        
        for attempt in range(max_retries + 1):
            try:
                if not os.path.exists(mosaic_fits_path):
                    raise PhotometryError(f"Mosaic FITS file not found: {mosaic_fits_path}")
                
                # Identify sources
                logger.info("Identifying sources...")
                source_result = await self._identify_sources(mosaic_fits_path)
                if not source_result['success']:
                    raise PhotometryError(f"Source identification failed: {source_result['error']}")
                
                targets = source_result['targets']
                references = source_result['references']
                
                if targets is None or len(targets) == 0:
                    logger.warning("No target sources identified")
                    return {
                        'success': True,
                        'targets_count': 0,
                        'references_count': len(references) if references else 0,
                        'photometry_stored': False,
                        'quality_metrics': {'overall_quality_score': 0.0}
                    }
                
                if references is None or len(references) == 0:
                    logger.warning("No reference sources identified")
                    return {
                        'success': True,
                        'targets_count': len(targets),
                        'references_count': 0,
                        'photometry_stored': False,
                        'quality_metrics': {'overall_quality_score': 0.0}
                    }
                
                # Perform aperture photometry
                logger.info("Performing aperture photometry...")
                photometry_result = await self._perform_aperture_photometry(
                    mosaic_fits_path, targets, references
                )
                if not photometry_result['success']:
                    raise PhotometryError(f"Aperture photometry failed: {photometry_result['error']}")
                
                phot_table = photometry_result['photometry_table']
                
                # Calculate relative fluxes
                logger.info("Calculating relative fluxes...")
                relative_flux_result = await self._calculate_relative_fluxes(phot_table)
                if not relative_flux_result['success']:
                    raise PhotometryError(f"Relative flux calculation failed: {relative_flux_result['error']}")
                
                rel_flux_table = relative_flux_result['relative_flux_table']
                
                # Assess photometry quality
                quality_metrics = await self._assess_photometry_quality(rel_flux_table, targets, references)
                
                # Store results
                logger.info("Storing photometry results...")
                storage_result = await self._store_photometry_results(mosaic_time, rel_flux_table)
                if not storage_result['success']:
                    logger.warning(f"Failed to store photometry results: {storage_result['error']}")
                
                logger.info(f"Photometry processing completed successfully")
                logger.info(f"Photometry quality score: {quality_metrics.get('overall_quality_score', 'N/A')}")
                
                return {
                    'success': True,
                    'targets_count': len(targets),
                    'references_count': len(references),
                    'photometry_stored': storage_result['success'],
                    'relative_flux_table': rel_flux_table,
                    'quality_metrics': quality_metrics
                }
                
            except Exception as e:
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Photometry processing failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Photometry processing failed after {max_retries + 1} attempts: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'targets_count': 0,
                        'references_count': 0,
                        'photometry_stored': False,
                        'quality_metrics': None
                    }
    
    async def _identify_sources(self, mosaic_fits_path: str) -> Dict[str, Any]:
        """
        Identify target and reference sources from the mosaic.
        
        Args:
            mosaic_fits_path: Path to the mosaic FITS file
            
        Returns:
            Dictionary containing identified sources
        """
        try:
            targets, references = await self.photometry_manager.identify_sources(mosaic_fits_path)
            
            return {
                'success': True,
                'targets': targets,
                'references': references
            }
            
        except Exception as e:
            logger.error(f"Source identification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'targets': None,
                'references': None
            }
    
    async def _perform_aperture_photometry(self, mosaic_fits_path: str, 
                                         targets: Table, references: Table) -> Dict[str, Any]:
        """
        Perform aperture photometry on targets and references.
        
        Args:
            mosaic_fits_path: Path to the mosaic FITS file
            targets: Table of target sources
            references: Table of reference sources
            
        Returns:
            Dictionary containing photometry results
        """
        try:
            phot_table = await self.photometry_manager.perform_aperture_photometry(
                mosaic_fits_path, targets, references
            )
            
            if phot_table is None:
                return {
                    'success': False,
                    'error': 'Photometry returned None',
                    'photometry_table': None
                }
            
            return {
                'success': True,
                'photometry_table': phot_table
            }
            
        except Exception as e:
            logger.error(f"Aperture photometry failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'photometry_table': None
            }
    
    async def _calculate_relative_fluxes(self, photometry_table: Table) -> Dict[str, Any]:
        """
        Calculate relative fluxes using reference sources.
        
        Args:
            photometry_table: Table containing photometry results
            
        Returns:
            Dictionary containing relative flux results
        """
        try:
            rel_flux_table = await self.photometry_manager.calculate_relative_fluxes(photometry_table)
            
            if rel_flux_table is None:
                return {
                    'success': False,
                    'error': 'Relative flux calculation returned None',
                    'relative_flux_table': None
                }
            
            return {
                'success': True,
                'relative_flux_table': rel_flux_table
            }
            
        except Exception as e:
            logger.error(f"Relative flux calculation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'relative_flux_table': None
            }
    
    async def _store_photometry_results(self, mosaic_time: Time, 
                                      rel_flux_table: Table) -> Dict[str, Any]:
        """
        Store photometry results in the database.
        
        Args:
            mosaic_time: Time of the mosaic observation
            rel_flux_table: Table containing relative flux results
            
        Returns:
            Dictionary containing storage results
        """
        try:
            success = await self.photometry_manager.store_photometry_results(
                mosaic_time, rel_flux_table
            )
            
            return {
                'success': success,
                'error': None if success else 'Storage failed'
            }
            
        except Exception as e:
            logger.error(f"Photometry storage failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _assess_photometry_quality(self, rel_flux_table: Table, 
                                       targets: Table, references: Table) -> Dict[str, Any]:
        """
        Assess the quality of photometry results.
        
        Args:
            rel_flux_table: Table containing relative flux results
            targets: Table of target sources
            references: Table of reference sources
            
        Returns:
            Dictionary containing quality metrics
        """
        logger.info("Assessing photometry quality")
        
        quality_metrics = {
            'overall_quality_score': 0.0,
            'target_count': len(targets) if targets else 0,
            'reference_count': len(references) if references else 0,
            'flux_precision': 0.0,
            'flux_accuracy': 0.0,
            'source_detection_rate': 0.0,
            'reference_stability': 0.0,
            'warnings': [],
            'errors': []
        }
        
        try:
            if rel_flux_table is None or len(rel_flux_table) == 0:
                quality_metrics['errors'].append("No photometry data available")
                return quality_metrics
            
            # Calculate flux precision (scatter in relative fluxes)
            if 'relative_flux' in rel_flux_table.colnames:
                rel_fluxes = rel_flux_table['relative_flux']
                valid_fluxes = rel_fluxes[~np.isnan(rel_fluxes)]
                
                if len(valid_fluxes) > 0:
                    flux_std = np.std(valid_fluxes)
                    quality_metrics['flux_precision'] = float(flux_std)
                    
                    # Good precision: std < 0.1 (10%)
                    if flux_std < 0.05:
                        quality_metrics['warnings'].append("Excellent flux precision")
                    elif flux_std > 0.2:
                        quality_metrics['warnings'].append("Poor flux precision")
            
            # Calculate source detection rate
            if targets and len(targets) > 0:
                detected_targets = len([row for row in rel_flux_table if row['source_type'] == 'target'])
                detection_rate = detected_targets / len(targets)
                quality_metrics['source_detection_rate'] = float(detection_rate)
                
                if detection_rate < 0.5:
                    quality_metrics['warnings'].append("Low source detection rate")
            
            # Calculate reference stability
            if references and len(references) > 0:
                ref_fluxes = []
                for row in rel_flux_table:
                    if row['source_type'] == 'reference':
                        ref_fluxes.append(row['relative_flux'])
                
                if len(ref_fluxes) > 1:
                    ref_std = np.std(ref_fluxes)
                    quality_metrics['reference_stability'] = float(ref_std)
                    
                    # Good stability: std < 0.05 (5%)
                    if ref_std > 0.1:
                        quality_metrics['warnings'].append("Poor reference stability")
            
            # Calculate flux accuracy (how close to expected values)
            if 'expected_flux' in rel_flux_table.colnames and 'relative_flux' in rel_flux_table.colnames:
                expected = rel_flux_table['expected_flux']
                measured = rel_flux_table['relative_flux']
                
                valid_mask = ~(np.isnan(expected) | np.isnan(measured))
                if np.any(valid_mask):
                    accuracy = np.mean(np.abs(expected[valid_mask] - measured[valid_mask]) / expected[valid_mask])
                    quality_metrics['flux_accuracy'] = float(accuracy)
                    
                    if accuracy > 0.2:
                        quality_metrics['warnings'].append("Poor flux accuracy")
            
            # Calculate overall quality score
            quality_metrics['overall_quality_score'] = self._calculate_photometry_quality_score(quality_metrics)
            
        except Exception as e:
            quality_metrics['errors'].append(f"Quality assessment error: {e}")
            quality_metrics['overall_quality_score'] = 0.0
        
        logger.info(f"Photometry quality score: {quality_metrics['overall_quality_score']:.2f}/10.0")
        return quality_metrics
    
    def _calculate_photometry_quality_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate overall photometry quality score.
        
        Args:
            metrics: Dictionary of photometry quality metrics
            
        Returns:
            Quality score from 0.0 to 10.0
        """
        score = 10.0
        
        # Flux precision scoring
        flux_precision = metrics.get('flux_precision', 0)
        if flux_precision > 0.2:  # > 20%
            score -= 3.0
        elif flux_precision > 0.1:  # > 10%
            score -= 1.5
        elif flux_precision < 0.05:  # < 5%
            score += 1.0  # Bonus for excellent precision
        
        # Source detection rate scoring
        detection_rate = metrics.get('source_detection_rate', 0)
        if detection_rate < 0.5:
            score -= 2.0
        elif detection_rate < 0.8:
            score -= 1.0
        elif detection_rate > 0.95:
            score += 0.5  # Bonus for high detection rate
        
        # Reference stability scoring
        ref_stability = metrics.get('reference_stability', 0)
        if ref_stability > 0.1:  # > 10%
            score -= 2.0
        elif ref_stability > 0.05:  # > 5%
            score -= 1.0
        
        # Flux accuracy scoring
        flux_accuracy = metrics.get('flux_accuracy', 0)
        if flux_accuracy > 0.2:  # > 20%
            score -= 2.0
        elif flux_accuracy > 0.1:  # > 10%
            score -= 1.0
        
        # Target and reference count scoring
        target_count = metrics.get('target_count', 0)
        ref_count = metrics.get('reference_count', 0)
        
        if target_count == 0:
            score -= 3.0  # No targets is a major issue
        elif target_count < 3:
            score -= 1.0  # Few targets
        
        if ref_count == 0:
            score -= 2.0  # No references is a problem
        elif ref_count < 2:
            score -= 1.0  # Few references
        
        # Penalize for warnings
        warning_count = len(metrics.get('warnings', []))
        score -= warning_count * 0.5
        
        # Penalize for errors
        error_count = len(metrics.get('errors', []))
        score -= error_count * 2.0
        
        return max(0.0, round(score, 2))
    
    async def process_multiple_mosaics(self, mosaic_data: List[Dict[str, Any]], 
                                     max_concurrent: int = 2) -> Dict[str, Any]:
        """
        Process multiple mosaics with parallel processing and quality assessment.
        
        Args:
            mosaic_data: List of dictionaries containing mosaic_fits_path and mosaic_time
            max_concurrent: Maximum number of concurrent processing tasks
            
        Returns:
            Dictionary containing processing results
        """
        logger.info(f"Processing {len(mosaic_data)} mosaics with max {max_concurrent} concurrent tasks")
        
        results = {
            'successful': [],
            'failed': [],
            'total_processed': 0,
            'total_successful': 0,
            'total_failed': 0,
            'quality_metrics': {
                'average_quality_score': 0.0,
                'best_quality_score': 0.0,
                'worst_quality_score': 10.0
            }
        }
        
        # Process mosaics in batches to manage memory
        batch_size = min(max_concurrent, len(mosaic_data))
        
        for i in range(0, len(mosaic_data), batch_size):
            batch = mosaic_data[i:i + batch_size]
            logger.info(f"Processing photometry batch {i//batch_size + 1}: {len(batch)} mosaics")
            
            # Process batch concurrently
            tasks = []
            for mosaic_info in batch:
                task = self.process_mosaic(
                    mosaic_info['mosaic_fits_path'],
                    mosaic_info['mosaic_time']
                )
                tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                mosaic_info = batch[j]
                results['total_processed'] += 1
                
                if isinstance(result, Exception):
                    logger.error(f"Exception processing mosaic {j}: {result}")
                    results['failed'].append({
                        'mosaic_info': mosaic_info,
                        'error': str(result),
                        'quality_metrics': None
                    })
                    results['total_failed'] += 1
                elif result.get('success', False):
                    results['successful'].append(result)
                    results['total_successful'] += 1
                    
                    # Update quality metrics
                    quality_score = result.get('quality_metrics', {}).get('overall_quality_score', 0)
                    results['quality_metrics']['best_quality_score'] = max(
                        results['quality_metrics']['best_quality_score'], quality_score
                    )
                    results['quality_metrics']['worst_quality_score'] = min(
                        results['quality_metrics']['worst_quality_score'], quality_score
                    )
                else:
                    results['failed'].append(result)
                    results['total_failed'] += 1
            
            # Memory cleanup between batches
            await self._cleanup_memory()
        
        # Calculate average quality score
        if results['total_successful'] > 0:
            total_quality = sum(
                result.get('quality_metrics', {}).get('overall_quality_score', 0)
                for result in results['successful']
            )
            results['quality_metrics']['average_quality_score'] = round(
                total_quality / results['total_successful'], 2
            )
        
        success_rate = (results['total_successful'] / results['total_processed']) * 100 if results['total_processed'] > 0 else 0
        
        logger.info(f"Photometry batch processing complete: {results['total_successful']}/{results['total_processed']} "
                   f"successful ({success_rate:.1f}%)")
        logger.info(f"Average quality score: {results['quality_metrics']['average_quality_score']:.2f}/10.0")
        
        return results
    
    async def _cleanup_memory(self):
        """
        Perform memory cleanup between processing batches.
        """
        try:
            import gc
            gc.collect()
            logger.debug("Memory cleanup completed")
        except Exception as e:
            logger.warning(f"Memory cleanup failed: {e}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage information.
        
        Returns:
            Dictionary containing memory usage metrics
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / (1024 * 1024),  # Resident Set Size
                'vms_mb': memory_info.vms / (1024 * 1024),  # Virtual Memory Size
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / (1024 * 1024)
            }
        except ImportError:
            logger.warning("psutil not available for memory monitoring")
            return {
                'rss_mb': 0,
                'vms_mb': 0,
                'percent': 0,
                'available_mb': 0
            }
        except Exception as e:
            logger.warning(f"Memory monitoring failed: {e}")
            return {
                'rss_mb': 0,
                'vms_mb': 0,
                'percent': 0,
                'available_mb': 0
            }
    
    async def generate_photometry_report(self, photometry_results: List[Dict[str, Any]], 
                                       output_path: str) -> bool:
        """
        Generate a comprehensive photometry report.
        
        Args:
            photometry_results: List of photometry result dictionaries
            output_path: Path to save the photometry report
            
        Returns:
            True if report generated successfully, False otherwise
        """
        logger.info(f"Generating photometry report for {len(photometry_results)} results")
        
        try:
            report_content = []
            report_content.append("# DSA-110 Photometry Report")
            report_content.append(f"Generated: {np.datetime64('now')}")
            report_content.append(f"Total Results: {len(photometry_results)}")
            report_content.append("")
            
            # Overall statistics
            successful_results = [r for r in photometry_results if r.get('success', False)]
            failed_results = [r for r in photometry_results if not r.get('success', False)]
            
            report_content.append("## Overall Statistics")
            report_content.append(f"- Successful: {len(successful_results)}")
            report_content.append(f"- Failed: {len(failed_results)}")
            report_content.append(f"- Success Rate: {len(successful_results)/len(photometry_results)*100:.1f}%")
            report_content.append("")
            
            if successful_results:
                # Quality metrics summary
                quality_scores = [r.get('quality_metrics', {}).get('overall_quality_score', 0) 
                                for r in successful_results]
                
                report_content.append("## Quality Metrics Summary")
                report_content.append(f"- Average Quality Score: {np.mean(quality_scores):.2f}/10.0")
                report_content.append(f"- Best Quality Score: {np.max(quality_scores):.2f}/10.0")
                report_content.append(f"- Worst Quality Score: {np.min(quality_scores):.2f}/10.0")
                report_content.append(f"- Standard Deviation: {np.std(quality_scores):.2f}")
                report_content.append("")
                
                # Individual result details
                report_content.append("## Individual Photometry Details")
                for i, result in enumerate(successful_results):
                    quality_metrics = result.get('quality_metrics', {})
                    report_content.append(f"### Result {i+1}")
                    report_content.append(f"- Targets: {result.get('targets_count', 'N/A')}")
                    report_content.append(f"- References: {result.get('references_count', 'N/A')}")
                    report_content.append(f"- Quality Score: {quality_metrics.get('overall_quality_score', 'N/A')}/10.0")
                    report_content.append(f"- Flux Precision: {quality_metrics.get('flux_precision', 'N/A')}")
                    report_content.append(f"- Detection Rate: {quality_metrics.get('source_detection_rate', 'N/A')*100:.1f}%")
                    report_content.append(f"- Reference Stability: {quality_metrics.get('reference_stability', 'N/A')}")
                    
                    if quality_metrics.get('warnings'):
                        report_content.append(f"- Warnings: {', '.join(quality_metrics['warnings'])}")
                    if quality_metrics.get('errors'):
                        report_content.append(f"- Errors: {', '.join(quality_metrics['errors'])}")
                    report_content.append("")
            
            if failed_results:
                report_content.append("## Failed Photometry")
                for i, result in enumerate(failed_results):
                    report_content.append(f"### Failed Result {i+1}")
                    report_content.append(f"- Error: {result.get('error', 'Unknown error')}")
                    report_content.append("")
            
            # Write report
            with open(output_path, 'w') as f:
                f.write('\n'.join(report_content))
            
            logger.info(f"Photometry report saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Photometry report generation failed: {e}")
            return False
