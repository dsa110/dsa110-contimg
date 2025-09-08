"""
Variability Analysis Handler

Handles variability analysis of photometry data using the new pipeline architecture.
"""

import asyncio
import os
import glob
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

from core.utils.logging import get_logger
from core.messaging.message_queue import MessageQueue, MessageType
from core.utils.distributed_state import DistributedStateManager

logger = get_logger(__name__)


class VariabilityAnalysisHandler:
    """Handles variability analysis with distributed state management."""

    def __init__(self, config: dict, message_queue: MessageQueue, state_manager: DistributedStateManager):
        self.config = config
        self.message_queue = message_queue
        self.state_manager = state_manager
        
        # Configuration
        self.photometry_dir = Path(config['paths']['pipeline_base_dir']) / config['paths']['photometry_dir']
        self.analysis_interval = timedelta(hours=config['services'].get('variability_analysis_interval_hours', 1))
        self.min_data_points = config['services'].get('variability_min_data_points', 10)
        self.variability_threshold = config['services'].get('variability_threshold', 0.1)
        
        logger.info(f"Variability Analysis Handler initialized")
        logger.info(f"Photometry directory: {self.photometry_dir}")
        logger.info(f"Analysis interval: {self.analysis_interval}")
        logger.info(f"Min data points: {self.min_data_points}")

    async def analyze_variability(self, force_analysis: bool = False) -> Dict[str, Any]:
        """Analyze variability in photometry data."""
        try:
            logger.info("Starting variability analysis")
            
            # Check if analysis is needed
            if not force_analysis and not await self._should_run_analysis():
                logger.debug("Variability analysis not needed at this time")
                return {"status": "skipped", "reason": "not_needed"}

            # Get photometry data
            photometry_data = await self._load_photometry_data()
            if photometry_data is None or len(photometry_data) == 0:
                logger.warning("No photometry data available for analysis")
                return {"status": "skipped", "reason": "no_data"}

            # Perform analysis
            analysis_results = await self._perform_variability_analysis(photometry_data)
            
            # Store results
            await self._store_analysis_results(analysis_results)
            
            # Update last analysis time
            await self._update_last_analysis_time()
            
            # Send completion message
            message = {
                "type": "variability_analysis_complete",
                "results": analysis_results,
                "timestamp_utc": datetime.utcnow().isoformat()
            }
            await self.message_queue.publish(MessageType.VARIABILITY_ANALYSIS, message)
            
            logger.info(f"Variability analysis completed successfully")
            return {"status": "success", "results": analysis_results}

        except Exception as e:
            logger.error(f"Error in variability analysis: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _should_run_analysis(self) -> bool:
        """Check if variability analysis should run based on time interval."""
        try:
            last_analysis_key = "variability_analysis:last_run"
            last_analysis = await self.state_manager.get(last_analysis_key)
            
            if last_analysis is None:
                return True  # First run
            
            last_run_time = datetime.fromisoformat(last_analysis['timestamp'])
            time_since_last = datetime.utcnow() - last_run_time
            
            return time_since_last >= self.analysis_interval
            
        except Exception as e:
            logger.error(f"Error checking analysis interval: {e}")
            return True  # Run on error

    async def _load_photometry_data(self) -> Optional[pd.DataFrame]:
        """Load photometry data from files."""
        try:
            # Look for photometry CSV files
            pattern = str(self.photometry_dir / "*.csv")
            csv_files = glob.glob(pattern)
            
            if not csv_files:
                logger.warning("No photometry CSV files found")
                return None
            
            # Load and combine all CSV files
            dataframes = []
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                    if 'timestamp' in df.columns and 'relative_flux' in df.columns:
                        dataframes.append(df)
                except Exception as e:
                    logger.warning(f"Error loading {csv_file}: {e}")
                    continue
            
            if not dataframes:
                logger.warning("No valid photometry data found")
                return None
            
            # Combine all data
            combined_df = pd.concat(dataframes, ignore_index=True)
            
            # Convert timestamp to datetime
            combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
            
            # Sort by timestamp
            combined_df = combined_df.sort_values('timestamp')
            
            logger.info(f"Loaded {len(combined_df)} photometry data points from {len(dataframes)} files")
            return combined_df
            
        except Exception as e:
            logger.error(f"Error loading photometry data: {e}")
            return None

    async def _perform_variability_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform variability analysis on photometry data."""
        try:
            results = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "total_data_points": len(data),
                "time_range": {
                    "start": data['timestamp'].min().isoformat(),
                    "end": data['timestamp'].max().isoformat()
                },
                "sources": {}
            }
            
            # Group by source if source column exists
            if 'source_id' in data.columns:
                source_groups = data.groupby('source_id')
            else:
                # Assume all data is from one source
                source_groups = [('unknown', data)]
            
            for source_id, source_data in source_groups:
                if len(source_data) < self.min_data_points:
                    logger.debug(f"Source {source_id} has insufficient data points ({len(source_data)} < {self.min_data_points})")
                    continue
                
                # Calculate variability metrics
                source_analysis = self._analyze_source_variability(source_data)
                results["sources"][str(source_id)] = source_analysis
            
            # Calculate overall statistics
            results["overall_stats"] = self._calculate_overall_stats(data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing variability analysis: {e}")
            raise

    def _analyze_source_variability(self, source_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze variability for a single source."""
        try:
            fluxes = source_data['relative_flux'].values
            
            # Basic statistics
            mean_flux = np.mean(fluxes)
            std_flux = np.std(fluxes)
            rms_flux = np.sqrt(np.mean(fluxes**2))
            
            # Variability metrics
            fractional_rms = std_flux / mean_flux if mean_flux != 0 else 0
            is_variable = fractional_rms > self.variability_threshold
            
            # Time series analysis
            times = pd.to_datetime(source_data['timestamp']).values
            time_span = (times.max() - times.min()).total_seconds() / 3600  # hours
            
            # Calculate variability index (simplified)
            variability_index = std_flux / mean_flux if mean_flux != 0 else 0
            
            return {
                "data_points": len(source_data),
                "mean_flux": float(mean_flux),
                "std_flux": float(std_flux),
                "rms_flux": float(rms_flux),
                "fractional_rms": float(fractional_rms),
                "variability_index": float(variability_index),
                "is_variable": bool(is_variable),
                "time_span_hours": float(time_span),
                "flux_range": {
                    "min": float(np.min(fluxes)),
                    "max": float(np.max(fluxes))
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing source variability: {e}")
            return {"error": str(e)}

    def _calculate_overall_stats(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate overall statistics for all data."""
        try:
            fluxes = data['relative_flux'].values
            
            return {
                "total_sources": len(data.groupby('source_id')) if 'source_id' in data.columns else 1,
                "total_data_points": len(data),
                "overall_mean_flux": float(np.mean(fluxes)),
                "overall_std_flux": float(np.std(fluxes)),
                "overall_fractional_rms": float(np.std(fluxes) / np.mean(fluxes)) if np.mean(fluxes) != 0 else 0,
                "time_span_hours": float((pd.to_datetime(data['timestamp']).max() - pd.to_datetime(data['timestamp']).min()).total_seconds() / 3600)
            }
            
        except Exception as e:
            logger.error(f"Error calculating overall stats: {e}")
            return {"error": str(e)}

    async def _store_analysis_results(self, results: Dict[str, Any]):
        """Store analysis results."""
        try:
            # Store in distributed state
            results_key = f"variability_analysis:results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            await self.state_manager.set(results_key, results, ttl=86400)  # 24 hour TTL
            
            # Store latest results
            await self.state_manager.set("variability_analysis:latest_results", results, ttl=86400)
            
            # Save to file
            results_file = self.photometry_dir / f"variability_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            import json
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Stored variability analysis results to {results_file}")
            
        except Exception as e:
            logger.error(f"Error storing analysis results: {e}")

    async def _update_last_analysis_time(self):
        """Update the last analysis time."""
        try:
            last_analysis_key = "variability_analysis:last_run"
            last_analysis_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            await self.state_manager.set(last_analysis_key, last_analysis_info, ttl=86400)
        except Exception as e:
            logger.error(f"Error updating last analysis time: {e}")

    async def get_analysis_stats(self) -> Dict[str, Any]:
        """Get current analysis statistics."""
        try:
            last_analysis = await self.state_manager.get("variability_analysis:last_run")
            latest_results = await self.state_manager.get("variability_analysis:latest_results")
            
            return {
                "last_analysis": last_analysis,
                "latest_results": latest_results,
                "analysis_interval_hours": self.analysis_interval.total_seconds() / 3600,
                "min_data_points": self.min_data_points,
                "variability_threshold": self.variability_threshold,
                "photometry_directory": str(self.photometry_dir)
            }
        except Exception as e:
            logger.error(f"Error getting analysis stats: {e}")
            return {"error": str(e)}

    async def get_variability_summary(self) -> Dict[str, Any]:
        """Get a summary of variability analysis results."""
        try:
            latest_results = await self.state_manager.get("variability_analysis:latest_results")
            
            if not latest_results:
                return {"status": "no_results"}
            
            # Count variable sources
            variable_sources = 0
            total_sources = 0
            
            if "sources" in latest_results:
                for source_id, source_data in latest_results["sources"].items():
                    total_sources += 1
                    if source_data.get("is_variable", False):
                        variable_sources += 1
            
            return {
                "status": "success",
                "analysis_timestamp": latest_results.get("analysis_timestamp"),
                "total_sources": total_sources,
                "variable_sources": variable_sources,
                "variability_rate": variable_sources / total_sources if total_sources > 0 else 0,
                "overall_stats": latest_results.get("overall_stats", {})
            }
            
        except Exception as e:
            logger.error(f"Error getting variability summary: {e}")
            return {"status": "error", "error": str(e)}
