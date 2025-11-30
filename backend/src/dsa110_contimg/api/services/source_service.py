"""
Source service - business logic for source operations.
"""

from __future__ import annotations

import statistics
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..repositories import SourceRepository, SourceRecord


class SourceService:
    """Business logic for source operations."""
    
    def __init__(self, repository: "SourceRepository"):
        self.repo = repository
    
    def get_source(self, source_id: str) -> Optional["SourceRecord"]:
        """Get source by ID."""
        return self.repo.get_by_id(source_id)
    
    def list_sources(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List["SourceRecord"]:
        """List sources with pagination."""
        return self.repo.list_all(limit=limit, offset=offset)
    
    def get_lightcurve(
        self,
        source_id: str,
        start_mjd: Optional[float] = None,
        end_mjd: Optional[float] = None
    ) -> List[dict]:
        """Get lightcurve data for a source."""
        return self.repo.get_lightcurve(source_id, start_mjd, end_mjd)
    
    def calculate_variability(
        self,
        source: "SourceRecord",
        epochs: List[dict]
    ) -> dict:
        """
        Calculate variability metrics for a source.
        
        Returns variability analysis including:
        - Variability index (V = std / mean)
        - Modulation index
        - Chi-squared statistics
        - Flux statistics
        """
        if not epochs or len(epochs) < 2:
            return {
                "source_id": source.id,
                "source_name": source.name,
                "n_epochs": len(epochs) if epochs else 0,
                "variability_index": None,
                "modulation_index": None,
                "chi_squared": None,
                "chi_squared_reduced": None,
                "is_variable": None,
                "flux_stats": None,
                "message": "Insufficient epochs for variability analysis (need at least 2)",
            }
        
        # Extract flux values
        fluxes = [e.get("flux_jy") for e in epochs if e.get("flux_jy") is not None]
        errors = [e.get("flux_err_jy") for e in epochs if e.get("flux_err_jy") is not None]
        
        if len(fluxes) < 2:
            return {
                "source_id": source.id,
                "source_name": source.name,
                "n_epochs": len(epochs),
                "variability_index": None,
                "message": "Insufficient flux measurements",
            }
        
        mean_flux = statistics.mean(fluxes)
        std_flux = statistics.stdev(fluxes)
        
        # Variability index V = std / mean
        variability_index = std_flux / mean_flux if mean_flux > 0 else None
        modulation_index = variability_index
        
        # Chi-squared test
        chi_squared = None
        chi_squared_reduced = None
        if errors and len(errors) == len(fluxes):
            chi_squared = sum(
                ((f - mean_flux) / e) ** 2
                for f, e in zip(fluxes, errors) if e > 0
            )
            dof = len(fluxes) - 1
            chi_squared_reduced = chi_squared / dof if dof > 0 else None
        
        # Simple variability classification (V > 0.1)
        is_variable = variability_index is not None and variability_index > 0.1
        
        return {
            "source_id": source.id,
            "source_name": source.name,
            "n_epochs": len(epochs),
            "variability_index": round(variability_index, 4) if variability_index else None,
            "modulation_index": round(modulation_index, 4) if modulation_index else None,
            "chi_squared": round(chi_squared, 2) if chi_squared else None,
            "chi_squared_reduced": round(chi_squared_reduced, 2) if chi_squared_reduced else None,
            "is_variable": is_variable,
            "flux_stats": {
                "mean_jy": round(mean_flux, 6),
                "std_jy": round(std_flux, 6),
                "min_jy": round(min(fluxes), 6),
                "max_jy": round(max(fluxes), 6),
            },
        }
