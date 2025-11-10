"""
Source class for DSA-110 photometry analysis.

Adopted from VAST Tools pattern for representing sources with measurements
across multiple epochs. Provides clean interface for ESE candidate analysis.

Reference: archive/references/vast-tools/vasttools/source.py
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.time import Time

try:
    from dsa110_contimg.photometry.variability import (
        calculate_eta_metric,
        calculate_vs_metric,
        calculate_m_metric,
    )
except ImportError:
    # Fallback if variability module not available
    def calculate_eta_metric(*args, **kwargs):
        return 0.0
    def calculate_vs_metric(*args, **kwargs):
        return 0.0
    def calculate_m_metric(*args, **kwargs):
        return 0.0

logger = logging.getLogger(__name__)


class SourceError(Exception):
    """Exception raised for Source class errors."""
    pass


class Source:
    """
    Represents a single source with measurements across multiple epochs.
    
    Provides a clean interface for ESE candidate analysis, including:
    - Light curve plotting
    - Variability metric calculations
    - Measurement access and filtering
    
    Attributes:
        source_id: Source identifier (e.g., 'NVSS J123456+420312')
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        name: Optional display name for the source
        products_db: Path to products database
        measurements: DataFrame containing all photometry measurements
    """
    
    def __init__(
        self,
        source_id: str,
        ra_deg: Optional[float] = None,
        dec_deg: Optional[float] = None,
        name: Optional[str] = None,
        products_db: Optional[Path] = None,
    ) -> None:
        """
        Initialize Source object.
        
        Args:
            source_id: Source identifier (e.g., 'NVSS J123456+420312')
            ra_deg: Right ascension in degrees (optional, will be loaded from DB)
            dec_deg: Declination in degrees (optional, will be loaded from DB)
            name: Optional display name (defaults to source_id)
            products_db: Path to products database (required for loading measurements)
        
        Raises:
            SourceError: If products_db is None or measurements cannot be loaded
        """
        self.source_id = source_id
        self.name = name or source_id
        self.products_db = Path(products_db) if products_db else None
        
        # Load measurements from database
        if self.products_db:
            self.measurements = self._load_measurements()
            # Get coordinates from first measurement if not provided
            if ra_deg is None or dec_deg is None:
                if len(self.measurements) > 0:
                    self.ra_deg = float(self.measurements.iloc[0]['ra_deg'])
                    self.dec_deg = float(self.measurements.iloc[0]['dec_deg'])
                else:
                    raise SourceError(
                        f"No measurements found for source {source_id} and "
                        "coordinates not provided"
                    )
            else:
                self.ra_deg = ra_deg
                self.dec_deg = dec_deg
        else:
            if ra_deg is None or dec_deg is None:
                raise SourceError(
                    "Either products_db must be provided or both ra_deg and "
                    "dec_deg must be specified"
                )
            self.ra_deg = ra_deg
            self.dec_deg = dec_deg
            self.measurements = pd.DataFrame()
        
        logger.debug(f'Created Source instance for {self.source_id}')
    
    def _load_measurements(self) -> pd.DataFrame:
        """
        Load photometry measurements from products database.
        
        Tries to load from photometry_timeseries table first, falls back to
        photometry table if needed.
        
        Returns:
            DataFrame with columns: mjd, normalized_flux_jy, normalized_flux_err_jy,
            peak_jyb, peak_err_jyb, image_path, measured_at, ra_deg, dec_deg
        
        Raises:
            SourceError: If database connection fails or no measurements found
        """
        if not self.products_db or not self.products_db.exists():
            raise SourceError(f"Products database not found: {self.products_db}")
        
        conn = sqlite3.connect(str(self.products_db), timeout=30.0)
        conn.row_factory = sqlite3.Row
        
        try:
            # Check what tables exist
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            
            # Try photometry_timeseries first (preferred)
            if 'photometry_timeseries' in tables:
                query = """
                    SELECT 
                        mjd, normalized_flux_jy, normalized_flux_err_jy,
                        flux_jy, flux_err_jy, image_path, measured_at,
                        ra_deg, dec_deg
                    FROM photometry_timeseries
                    WHERE source_id = ?
                    ORDER BY mjd ASC
                """
                df = pd.read_sql_query(query, conn, params=(self.source_id,))
                
                # Rename columns for consistency
                if 'flux_jy' in df.columns:
                    df = df.rename(columns={
                        'flux_jy': 'peak_jyb',
                        'flux_err_jy': 'peak_err_jyb'
                    })
            
            # Fallback to photometry table
            elif 'photometry' in tables:
                # Check if source_id column exists
                columns = {
                    row[1] for row in conn.execute(
                        "PRAGMA table_info(photometry)"
                    ).fetchall()
                }
                
                if 'source_id' in columns:
                    query = """
                        SELECT 
                            ra_deg, dec_deg, nvss_flux_mjy,
                            peak_jyb, peak_err_jyb, measured_at, mjd, image_path
                        FROM photometry
                        WHERE source_id = ? OR source_id LIKE ?
                        ORDER BY measured_at ASC
                    """
                    df = pd.read_sql_query(
                        query, conn,
                        params=(self.source_id, f"%{self.source_id}%")
                    )
                    
                    # Calculate MJD if missing
                    if 'mjd' not in df.columns or df['mjd'].isna().all():
                        if 'measured_at' in df.columns:
                            df['mjd'] = pd.to_datetime(
                                df['measured_at'], unit='s', errors='coerce'
                            ).apply(lambda x: Time(x).mjd if pd.notna(x) else None)
                    
                    # Add normalized flux columns (will be None if not available)
                    df['normalized_flux_jy'] = None
                    df['normalized_flux_err_jy'] = None
                else:
                    # No source_id column, can't query
                    df = pd.DataFrame()
            else:
                df = pd.DataFrame()
            
            conn.close()
            
            if df.empty:
                logger.warning(
                    f"No measurements found for source {self.source_id}"
                )
                return pd.DataFrame()
            
            # Ensure required columns exist
            required_cols = ['mjd', 'peak_jyb', 'peak_err_jyb', 'image_path']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.warning(
                    f"Missing columns in measurements: {missing_cols}"
                )
            
            # Convert measured_at to datetime if present
            if 'measured_at' in df.columns:
                df['measured_at'] = pd.to_datetime(
                    df['measured_at'], unit='s', errors='coerce'
                )
            
            return df
            
        except Exception as e:
            conn.close()
            raise SourceError(
                f"Failed to load measurements for {self.source_id}: {e}"
            ) from e
    
    @property
    def coord(self) -> SkyCoord:
        """Source coordinates as SkyCoord object."""
        return SkyCoord(self.ra_deg, self.dec_deg, unit=(u.deg, u.deg))
    
    @property
    def n_epochs(self) -> int:
        """Number of epochs with measurements."""
        return len(self.measurements)
    
    @property
    def detections(self) -> int:
        """
        Number of detections (SNR > 5 or flux > 3*error).
        
        Uses peak_jyb and peak_err_jyb if available, otherwise estimates
        from normalized_flux_jy and normalized_flux_err_jy.
        """
        if self.measurements.empty:
            return 0
        
        # Try to use SNR column if available
        if 'snr' in self.measurements.columns:
            return (self.measurements['snr'] > 5).sum()
        
        # Estimate from flux and error
        flux_col = 'normalized_flux_jy' if 'normalized_flux_jy' in self.measurements.columns else 'peak_jyb'
        err_col = 'normalized_flux_err_jy' if 'normalized_flux_err_jy' in self.measurements.columns else 'peak_err_jyb'
        
        if flux_col in self.measurements.columns and err_col in self.measurements.columns:
            flux = self.measurements[flux_col]
            err = self.measurements[err_col]
            # Detection if flux > 3*error and error is finite
            mask = (flux > 3 * err) & np.isfinite(err) & (err > 0)
            return mask.sum()
        
        # Fallback: assume all are detections if we can't determine
        return len(self.measurements)
    
    def calc_variability_metrics(self) -> Dict[str, Any]:
        """
        Calculate variability metrics for the source.
        
        Returns:
            Dictionary with metrics:
            - v: Coefficient of variation (std/mean)
            - eta: Weighted variance metric
            - vs_mean: Mean two-epoch t-statistic
            - m_mean: Mean modulation index
            - n_epochs: Number of epochs
        
        Raises:
            SourceError: If insufficient measurements for calculation
        """
        if len(self.measurements) < 2:
            return {
                'v': 0.0,
                'eta': 0.0,
                'vs_mean': None,
                'm_mean': None,
                'n_epochs': len(self.measurements)
            }
        
        # Use normalized flux if available, otherwise peak flux
        flux_col = 'normalized_flux_jy' if 'normalized_flux_jy' in self.measurements.columns else 'peak_jyb'
        err_col = 'normalized_flux_err_jy' if 'normalized_flux_err_jy' in self.measurements.columns else 'peak_err_jyb'
        
        if flux_col not in self.measurements.columns:
            raise SourceError(f"Flux column {flux_col} not found in measurements")
        
        flux = self.measurements[flux_col].values
        flux_err = self.measurements[err_col].values if err_col in self.measurements.columns else None
        
        # Filter out NaN/inf values
        valid_mask = np.isfinite(flux)
        if flux_err is not None:
            valid_mask &= np.isfinite(flux_err) & (flux_err > 0)
        
        if valid_mask.sum() < 2:
            return {
                'v': 0.0,
                'eta': 0.0,
                'vs_mean': None,
                'm_mean': None,
                'n_epochs': len(self.measurements)
            }
        
        flux_valid = flux[valid_mask]
        flux_err_valid = flux_err[valid_mask] if flux_err is not None else None
        
        # V metric (coefficient of variation)
        v = float(np.std(flux_valid) / np.mean(flux_valid)) if np.mean(flux_valid) > 0 else 0.0
        
        # η metric (weighted variance)
        if flux_err_valid is not None and len(flux_valid) >= 2:
            df_for_eta = pd.DataFrame({
                flux_col: flux_valid,
                err_col: flux_err_valid
            })
            try:
                eta = calculate_eta_metric(df_for_eta, flux_col=flux_col, err_col=err_col)
            except Exception as e:
                logger.warning(f"Failed to calculate η metric: {e}")
                eta = 0.0
        else:
            eta = 0.0
        
        # Two-epoch metrics
        vs_metrics = []
        m_metrics = []
        if len(flux_valid) >= 2:
            for i in range(len(flux_valid) - 1):
                if flux_err_valid is not None:
                    vs = calculate_vs_metric(
                        flux_valid[i], flux_valid[i+1],
                        flux_err_valid[i], flux_err_valid[i+1]
                    )
                    vs_metrics.append(vs)
                m = calculate_m_metric(flux_valid[i], flux_valid[i+1])
                m_metrics.append(m)
        
        return {
            'v': v,
            'eta': float(eta),
            'vs_mean': float(np.mean(vs_metrics)) if vs_metrics else None,
            'm_mean': float(np.mean(m_metrics)) if m_metrics else None,
            'n_epochs': len(self.measurements)
        }
    
    def plot_lightcurve(
        self,
        use_normalized: bool = True,
        figsize: Tuple[int, int] = (10, 6),
        min_points: int = 2,
        mjd: bool = False,
        grid: bool = True,
        yaxis_start: str = "auto",
        highlight_baseline: bool = True,
        highlight_ese_period: bool = True,
        save: bool = False,
        outfile: Optional[str] = None,
        plot_dpi: int = 150
    ):
        """
        Plot light curve with ESE-specific features.
        
        Adopted from VAST Tools with DSA-110 specific enhancements:
        - Baseline period highlighting (first 10 epochs)
        - ESE candidate period highlighting (14-180 days)
        - Normalized flux plotting
        
        Args:
            use_normalized: Use normalized flux (default) or raw flux
            figsize: Figure size tuple
            min_points: Minimum number of points required
            mjd: Use MJD for x-axis instead of datetime
            grid: Show grid
            yaxis_start: 'auto' or '0' for y-axis start
            highlight_baseline: Highlight first 10 epochs as baseline
            highlight_ese_period: Highlight 14-180 day ESE candidate period
            save: Save figure instead of returning
            outfile: Output filename (auto-generated if None)
            plot_dpi: DPI for saved figure
        
        Returns:
            matplotlib.figure.Figure if save=False, None otherwise
        
        Raises:
            SourceError: If insufficient measurements
        """
        import matplotlib.pyplot as plt
        
        if len(self.measurements) < min_points:
            raise SourceError(
                f"Need at least {min_points} measurements, have {len(self.measurements)}"
            )
        
        fig, ax = plt.subplots(figsize=figsize, dpi=plot_dpi)
        
        # Select flux column
        if use_normalized and 'normalized_flux_jy' in self.measurements.columns:
            flux_col = 'normalized_flux_jy'
            err_col = 'normalized_flux_err_jy'
            flux_label = 'Normalized Flux'
        else:
            flux_col = 'peak_jyb'
            err_col = 'peak_err_jyb'
            flux_label = 'Peak Flux'
        
        if flux_col not in self.measurements.columns:
            raise SourceError(f"Flux column {flux_col} not found in measurements")
        
        # Time axis
        if mjd:
            if 'mjd' not in self.measurements.columns:
                raise SourceError("MJD column not found in measurements")
            time = self.measurements['mjd']
            xlabel = 'MJD'
        else:
            if 'measured_at' in self.measurements.columns:
                time = pd.to_datetime(self.measurements['measured_at'])
            elif 'mjd' in self.measurements.columns:
                time = pd.to_datetime(
                    [Time(mjd, format='mjd').datetime for mjd in self.measurements['mjd']]
                )
            else:
                raise SourceError("No time column found in measurements")
            xlabel = 'Date'
        
        # Get flux and errors
        flux = self.measurements[flux_col]
        flux_err = self.measurements[err_col] if err_col in self.measurements.columns else None
        
        # Filter out NaN/inf
        valid_mask = np.isfinite(flux)
        if flux_err is not None:
            valid_mask &= np.isfinite(flux_err) & (flux_err > 0)
        
        if valid_mask.sum() < min_points:
            raise SourceError(f"Only {valid_mask.sum()} valid measurements")
        
        time_valid = time[valid_mask]
        flux_valid = flux[valid_mask]
        flux_err_valid = flux_err[valid_mask] if flux_err is not None else None
        
        # Plot flux with error bars
        if flux_err_valid is not None:
            ax.errorbar(
                time_valid, flux_valid,
                yerr=flux_err_valid,
                fmt='o', capsize=3, capthick=1.5,
                label=flux_label,
                markersize=6,
                alpha=0.7
            )
        else:
            ax.plot(
                time_valid, flux_valid,
                'o', label=flux_label,
                markersize=6,
                alpha=0.7
            )
        
        # Highlight baseline period (first 10 epochs)
        if highlight_baseline and len(time_valid) >= 10:
            baseline_time = time_valid.iloc[:10]
            baseline_flux = flux_valid.iloc[:10]
            ax.axvspan(
                baseline_time.min(), baseline_time.max(),
                alpha=0.2, color='green', label='Baseline Period (first 10 epochs)'
            )
            # Plot baseline median
            baseline_median = baseline_flux.median()
            ax.axhline(
                baseline_median, color='green', linestyle='--', linewidth=2,
                label=f'Baseline Median: {baseline_median:.4f} Jy'
            )
        
        # Highlight ESE candidate period (14-180 days)
        if highlight_ese_period and len(time_valid) > 1:
            if mjd:
                time_range_days = float(time_valid.max() - time_valid.min())
            else:
                time_range_days = (time_valid.max() - time_valid.min()).total_seconds() / 86400
            
            if 14 <= time_range_days <= 180:
                ax.axvspan(
                    time_valid.min(), time_valid.max(),
                    alpha=0.1, color='red',
                    label='ESE Candidate Period (14-180 days)'
                )
        
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Flux (Jy)' if not use_normalized else 'Normalized Flux')
        ax.set_title(f'Light Curve: {self.name}')
        ax.grid(grid, alpha=0.3)
        
        if yaxis_start == "0":
            ax.set_ylim(bottom=0)
        
        ax.legend(loc='best')
        
        plt.tight_layout()
        
        if save:
            if outfile is None:
                safe_name = self.source_id.replace(' ', '_').replace('/', '_')
                outfile = f"{safe_name}_lightcurve.png"
            fig.savefig(outfile, dpi=plot_dpi, bbox_inches='tight')
            logger.info(f"Saved light curve to {outfile}")
            plt.close(fig)
            return None
        
        return fig

