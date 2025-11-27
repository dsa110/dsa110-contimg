"""
DSA-110 Photometry Benchmarks

Performance benchmarks for forced photometry and source measurement operations.
These benchmarks measure the performance of flux extraction from FITS images.
"""

import shutil
from pathlib import Path

# Test data paths
PRODUCTS_DIR = Path("/stage/dsa110-contimg")
IMAGES_DIR = PRODUCTS_DIR / "images"
SCRATCH_DIR = Path("/scratch/asv_benchmarks")


def _find_test_image():
    """Find a suitable test FITS image."""
    if not IMAGES_DIR.exists():
        return None
    
    # Look for FITS images
    fits_files = list(IMAGES_DIR.glob("**/*.fits"))
    if not fits_files:
        return None
    
    # Prefer moderate size images
    for f in sorted(fits_files, key=lambda p: p.stat().st_size):
        size = f.stat().st_size
        if 1e6 < size < 500e6:  # 1MB - 500MB
            return f
    
    return fits_files[0] if fits_files else None


def _find_test_catalog():
    """Find a test source catalog."""
    catalog_dir = Path("/data/dsa110-contimg/state/catalogs")
    if not catalog_dir.exists():
        return None
    
    # Look for catalog files
    for pattern in ["*.csv", "*.sqlite3", "*.fits"]:
        files = list(catalog_dir.glob(pattern))
        if files:
            return files[0]
    
    return None


class TimeForcedPhotometry:
    """Benchmark forced photometry operations."""
    
    timeout = 300
    number = 1
    repeat = 1
    
    def setup(self):
        """Find test image and prepare."""
        self.image_path = _find_test_image()
        if self.image_path is None:
            raise NotImplementedError("No test FITS image available")
        
        # Copy to scratch for consistent I/O
        self.work_dir = SCRATCH_DIR / "photometry"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self.test_image = self.work_dir / self.image_path.name
        if not self.test_image.exists():
            shutil.copy2(self.image_path, self.test_image)
        
        # Generate some test positions
        self._setup_test_positions()
    
    def _setup_test_positions(self):
        """Setup test positions for photometry."""
        from astropy.io import fits
        from astropy.wcs import WCS
        
        with fits.open(self.test_image) as hdul:
            # Get WCS from header
            header = hdul[0].header
            wcs = WCS(header, naxis=2)
            
            # Get image center in world coords
            nx = header.get("NAXIS1", 1024)
            ny = header.get("NAXIS2", 1024)
            
            # Convert center pixel to world coords
            center_ra, center_dec = wcs.pixel_to_world_values(nx / 2, ny / 2)
            
            # Create grid of test positions around center
            import numpy as np
            offsets = np.linspace(-0.1, 0.1, 5)  # degrees
            
            self.test_positions = []
            for dra in offsets:
                for ddec in offsets:
                    self.test_positions.append((center_ra + dra, center_dec + ddec))
    
    def time_single_source_measurement(self):
        """Time measuring flux at a single position."""
        from dsa110_contimg.photometry.forced import (
            ForcedPhotometer,
        )
        
        phot = ForcedPhotometer(str(self.test_image))
        ra, dec = self.test_positions[0]
        phot.measure(ra, dec)
    
    def time_batch_photometry(self):
        """Time batch photometry on multiple sources."""
        from dsa110_contimg.photometry.forced import (
            ForcedPhotometer,
        )
        
        phot = ForcedPhotometer(str(self.test_image))
        for ra, dec in self.test_positions[:10]:
            phot.measure(ra, dec)


class TimeImageLoading:
    """Benchmark FITS image loading and WCS operations."""
    
    timeout = 120
    
    def setup(self):
        """Find test image."""
        self.image_path = _find_test_image()
        if self.image_path is None:
            raise NotImplementedError("No test FITS image available")
        
        # Stage to scratch
        self.work_dir = SCRATCH_DIR / "fits_load"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self.test_image = self.work_dir / self.image_path.name
        if not self.test_image.exists():
            shutil.copy2(self.image_path, self.test_image)
    
    def time_fits_open(self):
        """Time opening a FITS file."""
        from astropy.io import fits
        
        with fits.open(self.test_image) as hdul:
            _ = hdul[0].header
    
    def time_fits_load_data(self):
        """Time loading FITS data array."""
        from astropy.io import fits
        
        with fits.open(self.test_image) as hdul:
            _ = hdul[0].data
    
    def time_wcs_creation(self):
        """Time WCS object creation from FITS header."""
        from astropy.io import fits
        from astropy.wcs import WCS
        
        with fits.open(self.test_image) as hdul:
            _ = WCS(hdul[0].header, naxis=2)


class _TimeESEDetection:
    """Benchmark ESE (Extreme Scattering Event) detection.
    
    Disabled by default (prefix with _) as it requires specific data.
    Remove underscore to enable.
    """
    
    timeout = 600
    
    def setup(self):
        """Setup ESE detection test data."""
        # This would need a lightcurve database
        raise NotImplementedError("ESE detection benchmarks require lightcurve data")
    
    def time_ese_scan(self):
        """Time scanning for ESE candidates."""
        pass  # Implementation would go here
