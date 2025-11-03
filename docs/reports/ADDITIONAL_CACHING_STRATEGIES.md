# Additional Caching Strategies for Mosaicking Pipeline

**Date:** 2025-11-02  
**Status:** Additional Recommendations

## Additional Caching Opportunities

Beyond the basic caching strategies (headers, PB paths, DB queries), there are several more sophisticated caching opportunities:

---

### 1. Coordinate System (WCS) Caching (HIGH IMPACT, LOW EFFORT)

**Issue:** `img.coordsys()` called multiple times per tile:
- In `validate_tile_quality()`: reads coordsys to get RA/Dec center
- In `verify_astrometric_registration()`: reads coordsys for WCS calculations
- In `_build_weighted_mosaic()`: reads coordsys for reference grid
- In `generate_mosaic_metrics()`: reads coordsys for output images

**Current:** Each call opens image, reads coordsys, closes image

**Solution:**
```python
# Cache coordinate system objects
_coordsys_cache = {}

def get_tile_coordsys(tile_path: str) -> Optional[object]:
    """Get and cache tile coordinate system."""
    if tile_path not in _coordsys_cache:
        try:
            img = casaimage(tile_path)
            _coordsys_cache[tile_path] = img.coordsys()
            img.close()
        except Exception:
            return None
    return _coordsys_cache[tile_path]

# Cache derived WCS values
_wcs_metadata_cache = {}

def get_tile_wcs_metadata(tile_path: str) -> Dict[str, Any]:
    """Get cached WCS metadata (center, increment, shape)."""
    cache_key = f"{tile_path}:{os.path.getmtime(tile_path)}"
    
    if cache_key not in _wcs_metadata_cache:
        coordsys = get_tile_coordsys(tile_path)
        if coordsys:
            ref_val = coordsys.referencevalue()
            incr = coordsys.increment()
            shape = get_tile_shape(tile_path)
            
            _wcs_metadata_cache[cache_key] = {
                'ra_center': float(ref_val[0]) if len(ref_val) >= 2 else None,
                'dec_center': float(ref_val[1]) if len(ref_val) >= 2 else None,
                'cdelt_ra': float(incr[0]) * 180.0 / np.pi if len(incr) >= 2 else None,
                'cdelt_dec': float(incr[1]) * 180.0 / np.pi if len(incr) >= 2 else None,
                'shape': shape,
            }
    
    return _wcs_metadata_cache.get(cache_key, {})
```

**Estimated Speedup:** Eliminates redundant image opens for WCS access

---

### 2. Image Shape Caching (MODERATE IMPACT, LOW EFFORT)

**Issue:** `img.shape()` called multiple times:
- In `validate_tiles_consistency()`: for grid consistency check
- In `verify_astrometric_registration()`: for FoV calculation
- In `_build_weighted_mosaic()`: for grid verification

**Solution:**
```python
# Cache image shapes (can be derived from header)
def get_tile_shape(tile_path: str) -> Optional[Tuple[int, ...]]:
    """Get tile shape from cached header."""
    header = get_tile_header(tile_path)  # Use existing header cache
    return header.get('shape') if header else None
```

**Estimated Speedup:** Eliminates redundant shape() calls

---

### 3. Image Statistics Caching (HIGH IMPACT, MODERATE EFFORT)

**Issue:** Statistics computed from full image data each time:
- `validate_tile_quality()`: Reads full image, computes std, max for RMS/dynamic range
- `post_validation.py`: Reads full mosaic, computes statistics
- Computations are expensive (full image read + numpy operations)

**Solution:**
```python
# Cache computed statistics
_image_stats_cache = {}

def get_tile_statistics(tile_path: str, force_recompute: bool = False) -> Dict[str, float]:
    """Get cached tile statistics (RMS, dynamic range, etc.)."""
    cache_key = f"{tile_path}:{os.path.getmtime(tile_path)}"
    
    if cache_key not in _image_stats_cache or force_recompute:
        try:
            img = casaimage(tile_path)
            data = img.getdata()
            valid_pixels = data[np.isfinite(data)]
            
            if len(valid_pixels) > 0:
                rms_noise = float(np.std(valid_pixels))
                peak_value = float(np.abs(valid_pixels).max())
                dynamic_range = peak_value / rms_noise if rms_noise > 0 else 0.0
                
                _image_stats_cache[cache_key] = {
                    'rms_noise': rms_noise,
                    'peak_flux': peak_value,
                    'dynamic_range': dynamic_range,
                    'num_pixels': len(valid_pixels),
                }
            img.close()
        except Exception:
            return {}
    
    return _image_stats_cache.get(cache_key, {})
```

**Benefits:**
- Statistics computed once per tile
- Can be persisted to disk for long-term caching
- Cache invalidation based on file mtime

**Estimated Speedup:** 5-10x faster validation (avoids full image reads)

---

### 4. PB Response Statistics Caching (MODERATE IMPACT, LOW EFFORT)

**Issue:** PB response min/max computed from full PB data:
- In `validate_tile_quality()`: Reads full PB image for min/max
- In `check_primary_beam_consistency()`: Reads full PB images

**Solution:**
```python
# Cache PB statistics
_pb_stats_cache = {}

def get_pb_statistics(pb_path: str) -> Dict[str, float]:
    """Get cached PB response statistics."""
    cache_key = f"{pb_path}:{os.path.getmtime(pb_path)}"
    
    if cache_key not in _pb_stats_cache:
        try:
            pb_img = casaimage(pb_path)
            pb_data = pb_img.getdata()
            valid_pb = pb_data[np.isfinite(pb_data) & (pb_data > 0)]
            
            if len(valid_pb) > 0:
                _pb_stats_cache[cache_key] = {
                    'pb_response_min': float(valid_pb.min()),
                    'pb_response_max': float(valid_pb.max()),
                    'pb_response_mean': float(valid_pb.mean()),
                    'pb_response_median': float(np.median(valid_pb)),
                }
            pb_img.close()
        except Exception:
            return {}
    
    return _pb_stats_cache.get(cache_key, {})
```

**Estimated Speedup:** Eliminates redundant PB image reads

---

### 5. Catalog Query Results Caching (HIGH IMPACT, MODERATE EFFORT)

**Issue:** Catalog queries repeated for same sky regions:
- `verify_astrometric_registration()`: Queries NVSS catalog for each tile
- Same sky region queried multiple times if tiles overlap

**Solution:**
```python
# Cache catalog query results
import hashlib

_catalog_query_cache = {}

def query_catalog_cached(ra_deg: float, dec_deg: float, radius_deg: float, 
                        catalog_name: str = 'nvss') -> List[Dict]:
    """Query catalog with caching based on sky region."""
    # Create cache key from sky region
    cache_key = hashlib.md5(
        f"{catalog_name}:{ra_deg:.6f}:{dec_deg:.6f}:{radius_deg:.6f}".encode()
    ).hexdigest()
    
    if cache_key not in _catalog_query_cache:
        # Query catalog
        sources = query_catalog(ra_deg, dec_deg, radius_deg, catalog_name)
        _catalog_query_cache[cache_key] = sources
    
    return _catalog_query_cache[cache_key]
```

**Benefits:**
- Overlapping tiles share catalog queries
- Can persist cache across runs
- Cache invalidation based on catalog update time

**Estimated Speedup:** Significant for overlapping tiles (10-50x for repeated queries)

---

### 6. File Metadata Caching (LOW IMPACT, LOW EFFORT)

**Issue:** File modification times checked multiple times:
- Used for cache invalidation
- `os.path.getmtime()` called repeatedly

**Solution:**
```python
# Cache file metadata (mtime, size, exists)
_file_metadata_cache = {}

def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """Get cached file metadata."""
    if file_path not in _file_metadata_cache:
        path = Path(file_path)
        _file_metadata_cache[file_path] = {
            'exists': path.exists(),
            'mtime': path.stat().st_mtime if path.exists() else None,
            'size': path.stat().st_size if path.exists() else None,
            'isdir': path.is_dir() if path.exists() else False,
        }
    return _file_metadata_cache[file_path]
```

**Estimated Speedup:** Reduces file system calls

---

### 7. Validation Results Persistence (HIGH IMPACT, MODERATE EFFORT)

**Issue:** Validation results recomputed every run:
- Tile quality metrics computed from scratch
- No persistence of validation state

**Solution:**
```python
# Persist validation results to disk
import json

def validate_tiles_consistency_cached(tiles: List[str], products_db: Path,
                                     cache_file: Optional[Path] = None) -> Tuple:
    """Validate tiles with persistent caching."""
    if cache_file is None:
        cache_file = products_db.parent / 'mosaic_validation_cache.json'
    
    # Load cache
    cache = {}
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except Exception:
            pass
    
    # Validate each tile with cache lookup
    metrics_dict = {}
    all_issues = []
    
    for tile in tiles:
        tile_mtime = os.path.getmtime(tile)
        cache_key = f"{tile}:{tile_mtime}"
        
        if cache_key in cache:
            # Load from cache
            metrics = TileQualityMetrics(**cache[cache_key])
        else:
            # Compute and cache
            metrics = validate_tile_quality(tile, products_db)
            cache[cache_key] = {
                'tile_path': metrics.tile_path,
                'rms_noise': metrics.rms_noise,
                'dynamic_range': metrics.dynamic_range,
                'pbcor_applied': metrics.pbcor_applied,
                # ... other fields ...
            }
        
        metrics_dict[tile] = metrics
        if metrics.issues:
            all_issues.extend([f"{tile}: {issue}" for issue in metrics.issues])
    
    # Save cache
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)
    
    # Continue with consistency checks...
    return len(all_issues) == 0, all_issues, metrics_dict
```

**Benefits:**
- Validation near-instant for unchanged tiles
- Persists across runs
- Cache invalidation based on file mtime

**Estimated Speedup:** 10-100x faster for repeated validations

---

### 8. Regridding Results Caching (HIGH IMPACT, HIGH EFFORT)

**Issue:** Regridded images created and deleted each run:
- PB images regridded to common grid
- Tile images regridded to PB grid
- Temporary files deleted after use

**Solution:**
```python
# Cache regridded images
import hashlib

_regridded_cache_dir = Path("/tmp/mosaic_regrid_cache")

def get_regridded_image(source_path: str, template_path: str, 
                       cache_dir: Path = _regridded_cache_dir) -> Optional[str]:
    """Get cached regridded image or create if needed."""
    # Create cache key from source + template + mtimes
    source_mtime = os.path.getmtime(source_path)
    template_mtime = os.path.getmtime(template_path)
    
    cache_key = hashlib.md5(
        f"{source_path}:{source_mtime}:{template_path}:{template_mtime}".encode()
    ).hexdigest()
    
    cached_path = cache_dir / f"{cache_key}.image"
    
    if cached_path.exists():
        return str(cached_path)
    
    # Regrid and cache
    try:
        imregrid(
            imagename=source_path,
            template=template_path,
            output=str(cached_path),
            overwrite=True,
        )
        return str(cached_path)
    except Exception:
        return None

# Cleanup old cached regridded images periodically
def cleanup_regridded_cache(cache_dir: Path, max_age_days: int = 7):
    """Clean up old regridded cache files."""
    cutoff_time = time.time() - (max_age_days * 24 * 3600)
    for cached_file in cache_dir.glob("*.image"):
        if cached_file.stat().st_mtime < cutoff_time:
            cached_file.unlink()
```

**Benefits:**
- Regridded images reused across runs
- Significant time savings for repeated builds
- Requires disk space management

**Estimated Speedup:** 5-10x faster for repeated builds (if regridding was bottleneck)

---

## Cache Management Strategy

### Cache Invalidation

**Time-based:**
- File modification time (mtime) checks
- Cache expiry after N days

**Event-based:**
- Tile reprocessed → invalidate tile caches
- Calibration updated → invalidate calibration caches
- DB updated → invalidate DB-derived caches

**Manual:**
- Clear cache command/flag
- Cache rebuild option

### Cache Storage

**In-Memory:**
- Fast access
- Limited by RAM
- Good for session-based caching

**On-Disk:**
- Persistent across runs
- Requires disk space management
- Good for expensive computations

**Hybrid:**
- Frequently accessed: in-memory
- Expensive computations: on-disk
- Best of both worlds

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 days)
1. ✅ Coordinate system caching
2. ✅ Image shape caching  
3. ✅ File metadata caching

### Phase 2: High Impact (3-5 days)
4. ✅ Image statistics caching
5. ✅ PB statistics caching
6. ✅ Catalog query caching

### Phase 3: Advanced (1-2 weeks)
7. ⚠️ Validation results persistence
8. ⚠️ Regridding results caching

---

## Expected Combined Impact

**Current Performance:**
- 100 tiles validation: ~5-10 minutes
- Build: ~5-10 minutes
- **Total: ~10-20 minutes**

**After All Caching:**
- 100 tiles validation: ~10-30 seconds (cached) or ~2-3 minutes (uncached)
- Build: ~5-10 minutes (regridding still expensive)
- **Total: ~3-13 minutes**

**For Repeated Builds:**
- Near-instant validation (all cached)
- Faster build (regridded images cached)
- **Total: ~2-5 minutes**

---

## Conclusion

**Most Impactful Additional Caching:**
1. **Image statistics caching** - Eliminates expensive full image reads
2. **Catalog query caching** - Significant for overlapping tiles
3. **Validation results persistence** - Near-instant for repeated runs
4. **Regridding results caching** - Major time savings for repeated builds

**Combined with basic caching strategies, these would provide 80-90% performance improvement for repeated operations.**

