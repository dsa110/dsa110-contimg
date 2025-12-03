"""
DSA-110 Mosaic Memory Benchmarks

Memory profiling benchmarks for deep-tier mosaicking operations.
Tests memory scaling from 10 to 1000 images to understand resource
requirements for large mosaics.

ASV Memory Benchmark Types:
- peakmem_*: Peak memory usage during operation
- mem_*: Memory usage at a specific point

Key Metrics:
- Memory per image added
- Memory scaling (linear vs sublinear)
- Peak memory during reprojection phase
- Effective memory after garbage collection

This benchmark uses synthetic images to test scaling without
requiring 1000+ real FITS files.
"""

import gc
import tempfile
from pathlib import Path

import numpy as np

# Test parameters
SCRATCH_DIR = Path("/scratch/asv_benchmarks/mosaic_mem")
IMAGE_DIR = Path("/stage/dsa110-contimg/images")

# Synthetic image configuration
SYNTHETIC_IMAGE_SIZE = 512  # 512x512 pixels
SYNTHETIC_PIXEL_SCALE = 15 / 3600  # 15 arcsec in degrees
SYNTHETIC_NOISE_JY = 0.0003  # 300 µJy typical DSA-110 noise


def _create_synthetic_fits(
    output_path: Path,
    center_ra: float = 180.0,
    center_dec: float = 37.0,
    size: int = SYNTHETIC_IMAGE_SIZE,
    pixel_scale: float = SYNTHETIC_PIXEL_SCALE,
    noise_level: float = SYNTHETIC_NOISE_JY,
    seed: int = None,
) -> Path:
    """Create a synthetic FITS image for memory testing.
    
    Creates a realistic DSA-110-like image with:
    - Proper WCS header
    - Gaussian noise
    - Random seed for reproducibility
    """
    from astropy.io import fits
    from astropy.wcs import WCS
    
    if seed is not None:
        np.random.seed(seed)
    
    # Create synthetic data
    data = np.random.normal(0, noise_level, (size, size)).astype(np.float32)
    
    # Create WCS header
    header = fits.Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = size
    header["NAXIS2"] = size
    header["CRPIX1"] = size / 2
    header["CRPIX2"] = size / 2
    header["CRVAL1"] = center_ra
    header["CRVAL2"] = center_dec
    header["CDELT1"] = -pixel_scale  # RA decreases to the right
    header["CDELT2"] = pixel_scale
    header["CTYPE1"] = "RA---SIN"
    header["CTYPE2"] = "DEC--SIN"
    header["CUNIT1"] = "deg"
    header["CUNIT2"] = "deg"
    header["BUNIT"] = "JY/BEAM"
    header["TELESCOP"] = "DSA-110"
    header["BMAJ"] = 15 / 3600  # 15 arcsec beam
    header["BMIN"] = 15 / 3600
    header["BPA"] = 0.0
    
    # Write FITS
    hdu = fits.PrimaryHDU(data=data, header=header)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    hdu.writeto(str(output_path), overwrite=True)
    
    return output_path


def _generate_synthetic_images(n_images: int, work_dir: Path) -> list[Path]:
    """Generate n_images synthetic FITS files with overlapping coverage.
    
    Images are spread over a ~1 degree region to simulate drift-scan
    observations that would be mosaicked together.
    """
    images = []
    
    # DSA-110 drift-scan: images at different RA along constant Dec
    base_ra = 180.0  # 12h RA
    base_dec = 37.0  # DSA-110 latitude-ish
    
    # Spread images in RA to create overlapping coverage
    # Each image covers ~2 degrees, so spread by 1 degree for ~50% overlap
    ra_spread = 2.0  # degrees total spread
    
    for i in range(n_images):
        # Vary RA slightly for different images
        ra_offset = (i / max(n_images - 1, 1)) * ra_spread - ra_spread / 2
        ra = base_ra + ra_offset
        
        output_path = work_dir / f"synthetic_{i:04d}.fits"
        _create_synthetic_fits(
            output_path=output_path,
            center_ra=ra,
            center_dec=base_dec,
            size=SYNTHETIC_IMAGE_SIZE,
            seed=42 + i,  # Reproducible
        )
        images.append(output_path)
    
    return images


def _find_real_images(n_images: int) -> list[Path]:
    """Find real DSA-110 images if available."""
    if not IMAGE_DIR.exists():
        return []
    
    images = sorted(IMAGE_DIR.glob("*.fits"))
    if len(images) >= n_images:
        return images[:n_images]
    
    return []


def _get_current_memory_mb() -> float:
    """Get current memory usage in MB using resource module."""
    import resource
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024  # Convert KB to MB on Linux


class MemMosaicScaling:
    """Memory scaling benchmarks for mosaic operations.
    
    Tests how memory usage scales with number of input images,
    critical for planning deep-tier mosaic builds.
    """
    
    timeout = 1800  # 30 minutes max
    
    # Parameters to test different image counts
    params = [10, 25, 50, 100, 250, 500]
    param_names = ["n_images"]
    
    def setup(self, n_images):
        """Create synthetic images for testing."""
        self.work_dir = SCRATCH_DIR / f"mosaic_scale_{n_images}"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Try real images first, fall back to synthetic
        self.images = _find_real_images(n_images)
        if not self.images:
            self.images = _generate_synthetic_images(n_images, self.work_dir)
        
        self.output_path = self.work_dir / "mosaic_output.fits"
        
        # Clear any existing output
        if self.output_path.exists():
            self.output_path.unlink()
    
    def peakmem_build_mosaic(self, n_images):
        """Peak memory during mosaic build with n_images."""
        try:
            from dsa110_contimg.mosaic.builder import build_mosaic
            
            result = build_mosaic(
                image_paths=self.images,
                output_path=self.output_path,
                alignment_order=1,  # Fast interpolation
                write_weight_map=False,  # Skip weight map to isolate mosaic memory
                apply_pb_correction=False,
            )
            return result
        except ImportError:
            raise NotImplementedError("Mosaic builder not available")
    
    def teardown(self, n_images):
        """Clean up test files."""
        import shutil
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)


class MemMosaicWithWeights:
    """Memory benchmarks including weight map generation."""
    
    timeout = 1200
    
    params = [10, 50, 100]
    param_names = ["n_images"]
    
    def setup(self, n_images):
        """Create synthetic images."""
        self.work_dir = SCRATCH_DIR / f"mosaic_weights_{n_images}"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self.images = _generate_synthetic_images(n_images, self.work_dir)
        self.output_path = self.work_dir / "mosaic_output.fits"
    
    def peakmem_build_mosaic_with_weights(self, n_images):
        """Peak memory when building mosaic with weight map."""
        try:
            from dsa110_contimg.mosaic.builder import build_mosaic
            
            return build_mosaic(
                image_paths=self.images,
                output_path=self.output_path,
                alignment_order=1,
                write_weight_map=True,
                apply_pb_correction=False,
            )
        except ImportError:
            raise NotImplementedError("Mosaic builder not available")
    
    def teardown(self, n_images):
        """Clean up."""
        import shutil
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)


class MemMosaicPBCorrection:
    """Memory benchmarks with primary beam correction enabled."""
    
    timeout = 1200
    
    params = [10, 50, 100]
    param_names = ["n_images"]
    
    def setup(self, n_images):
        """Create synthetic images."""
        self.work_dir = SCRATCH_DIR / f"mosaic_pb_{n_images}"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self.images = _generate_synthetic_images(n_images, self.work_dir)
        self.output_path = self.work_dir / "mosaic_output.fits"
    
    def peakmem_build_mosaic_with_pb(self, n_images):
        """Peak memory when building mosaic with PB correction."""
        try:
            from dsa110_contimg.mosaic.builder import build_mosaic
            
            return build_mosaic(
                image_paths=self.images,
                output_path=self.output_path,
                alignment_order=1,
                write_weight_map=True,
                apply_pb_correction=True,
            )
        except ImportError:
            raise NotImplementedError("Mosaic builder not available")
    
    def teardown(self, n_images):
        """Clean up."""
        import shutil
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)


class MemReprojectStep:
    """Memory benchmarks for individual reprojection step.
    
    Isolates reprojection memory from combination memory to
    understand which phase is the bottleneck.
    """
    
    timeout = 600
    
    params = [10, 50, 100]
    param_names = ["n_images"]
    
    def setup(self, n_images):
        """Create synthetic images and precompute output WCS."""
        self.work_dir = SCRATCH_DIR / f"reproject_{n_images}"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self.images = _generate_synthetic_images(n_images, self.work_dir)
        
        # Pre-load images and compute output WCS
        from astropy.io import fits
        
        self.hdus = []
        for path in self.images:
            with fits.open(str(path)) as hdulist:
                hdu = fits.PrimaryHDU(
                    data=hdulist[0].data.copy(),
                    header=hdulist[0].header.copy()
                )
                self.hdus.append(hdu)
        
        try:
            from dsa110_contimg.mosaic.builder import compute_optimal_wcs
            self.output_wcs, self.output_shape = compute_optimal_wcs(self.hdus)
        except ImportError:
            raise NotImplementedError("Mosaic builder not available")
    
    def peakmem_reproject_all(self, n_images):
        """Peak memory when reprojecting all images to common grid."""
        try:
            from reproject import reproject_interp
        except ImportError:
            raise NotImplementedError("reproject not available")
        
        arrays = []
        footprints = []
        
        for hdu in self.hdus:
            array, footprint = reproject_interp(
                hdu,
                self.output_wcs,
                shape_out=self.output_shape,
                order=1,
            )
            arrays.append(array)
            footprints.append(footprint)
        
        return arrays, footprints
    
    def teardown(self, n_images):
        """Clean up."""
        import shutil
        # Clear references before cleanup
        self.hdus = None
        gc.collect()
        
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)


class MemWeightedCombine:
    """Memory benchmarks for weighted combination step.
    
    Tests memory usage of the combination algorithm separately
    from reprojection.
    """
    
    timeout = 300
    
    params = [10, 50, 100, 250]
    param_names = ["n_images"]
    
    def setup(self, n_images):
        """Create synthetic arrays to combine."""
        # Create arrays as if they were reprojected images
        self.arrays = [
            np.random.normal(0, 0.0003, (512, 512)).astype(np.float32)
            for _ in range(n_images)
        ]
        
        # All-ones footprints (full overlap)
        self.footprints = [
            np.ones((512, 512), dtype=np.float32)
            for _ in range(n_images)
        ]
        
        # Inverse-variance weights
        noise_levels = np.random.uniform(0.0002, 0.0004, n_images)
        self.weights = 1.0 / (noise_levels ** 2)
    
    def peakmem_weighted_combine(self, n_images):
        """Peak memory during weighted combination."""
        try:
            from dsa110_contimg.mosaic.builder import weighted_combine
            
            combined, weight_map = weighted_combine(
                self.arrays,
                self.weights,
                self.footprints,
                return_weights=True,
            )
            return combined, weight_map
        except ImportError:
            raise NotImplementedError("weighted_combine not available")
    
    def teardown(self, n_images):
        """Clean up arrays."""
        self.arrays = None
        self.footprints = None
        self.weights = None
        gc.collect()


class MemDeepTierMosaic:
    """
    Memory benchmark for deep-tier mosaics (500-1000 images).
    
    WARNING: This benchmark can use significant memory (10+ GB).
    Only runs on systems with sufficient RAM.
    
    Deep-tier mosaics combine hundreds of observations taken over
    multiple nights to achieve maximum sensitivity. This benchmark
    validates that the system can handle such large mosaics.
    """
    
    timeout = 3600  # 1 hour max
    
    # Only test if we have sufficient memory
    params = [100, 250, 500, 1000]
    param_names = ["n_images"]
    
    def setup(self, n_images):
        """Create synthetic images for deep-tier test."""
        import psutil
        
        # Check available memory
        mem_available_gb = psutil.virtual_memory().available / (1024 ** 3)
        
        # Estimate memory needed: ~4 MB per image * n_images * 3 (arrays + footprints + combined)
        estimated_gb = (n_images * 4 * 3) / 1024
        
        if mem_available_gb < estimated_gb * 1.5:
            raise NotImplementedError(
                f"Insufficient memory: {mem_available_gb:.1f} GB available, "
                f"need ~{estimated_gb * 1.5:.1f} GB for {n_images} images"
            )
        
        self.work_dir = SCRATCH_DIR / f"deep_tier_{n_images}"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Use smaller images for memory test
        self.images = []
        for i in range(n_images):
            ra_offset = (i / max(n_images - 1, 1)) * 2 - 1  # -1 to +1 degree
            output_path = self.work_dir / f"deep_{i:04d}.fits"
            _create_synthetic_fits(
                output_path=output_path,
                center_ra=180.0 + ra_offset,
                center_dec=37.0,
                size=256,  # Smaller images for memory test
                seed=42 + i,
            )
            self.images.append(output_path)
        
        self.output_path = self.work_dir / "deep_mosaic.fits"
    
    def peakmem_deep_tier_mosaic(self, n_images):
        """Peak memory for deep-tier mosaic with n_images."""
        try:
            from dsa110_contimg.mosaic.builder import build_mosaic
            
            return build_mosaic(
                image_paths=self.images,
                output_path=self.output_path,
                alignment_order=1,
                write_weight_map=True,
                apply_pb_correction=False,
            )
        except ImportError:
            raise NotImplementedError("Mosaic builder not available")
    
    def teardown(self, n_images):
        """Clean up."""
        import shutil
        
        # Explicitly clear references
        self.images = None
        gc.collect()
        
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)


# Standalone profiling script for detailed analysis
if __name__ == "__main__":
    """Run memory profiling with detailed output.
    
    Usage:
        python -m benchmarks.bench_mosaic_memory
    
    This runs a quick memory scaling test and prints results.
    For full ASV benchmarks, use: asv run
    """
    import sys
    import time
    
    try:
        import psutil
    except ImportError:
        print("Install psutil for detailed memory profiling: pip install psutil")
        sys.exit(1)
    
    print("=" * 60)
    print("DSA-110 Mosaic Memory Scaling Test")
    print("=" * 60)
    
    work_dir = Path("/scratch/mosaic_mem_test")
    work_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for n_images in [10, 25, 50, 100, 200]:
        print(f"\nTesting with {n_images} images...")
        
        # Generate images
        images = _generate_synthetic_images(n_images, work_dir / str(n_images))
        
        # Measure memory before
        gc.collect()
        mem_before = psutil.Process().memory_info().rss / (1024 ** 2)
        
        # Build mosaic
        start = time.time()
        try:
            from dsa110_contimg.mosaic.builder import build_mosaic
            
            output_path = work_dir / str(n_images) / "mosaic.fits"
            result = build_mosaic(
                image_paths=images,
                output_path=output_path,
                alignment_order=1,
                write_weight_map=True,
            )
            
            elapsed = time.time() - start
            
            # Measure memory after
            gc.collect()
            mem_after = psutil.Process().memory_info().rss / (1024 ** 2)
            peak_mem = psutil.Process().memory_info().peak_wset / (1024 ** 2) if hasattr(psutil.Process().memory_info(), 'peak_wset') else mem_after
            
            results.append({
                "n_images": n_images,
                "time_s": elapsed,
                "mem_before_mb": mem_before,
                "mem_after_mb": mem_after,
                "mem_delta_mb": mem_after - mem_before,
            })
            
            print(f"  Time: {elapsed:.1f}s")
            print(f"  Memory delta: {mem_after - mem_before:.1f} MB")
            print(f"  Memory per image: {(mem_after - mem_before) / n_images:.2f} MB")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "n_images": n_images,
                "error": str(e),
            })
        
        # Clean up
        import shutil
        shutil.rmtree(work_dir / str(n_images), ignore_errors=True)
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    successful = [r for r in results if "error" not in r]
    if len(successful) >= 2:
        # Estimate memory for 1000 images
        n_vals = [r["n_images"] for r in successful]
        mem_vals = [r["mem_delta_mb"] for r in successful]
        
        # Simple linear fit
        slope = (mem_vals[-1] - mem_vals[0]) / (n_vals[-1] - n_vals[0])
        intercept = mem_vals[0] - slope * n_vals[0]
        
        est_1000 = slope * 1000 + intercept
        
        print(f"\nMemory scaling: ~{slope:.2f} MB per image")
        print(f"Estimated memory for 1000 images: {est_1000:.0f} MB ({est_1000/1024:.1f} GB)")
        print(f"\nThis means deep-tier mosaics should fit in {est_1000 * 1.5 / 1024:.1f} GB RAM (1.5x safety)")
    
    # Cleanup
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)
