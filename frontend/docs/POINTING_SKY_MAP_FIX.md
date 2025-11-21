# Pointing Visualization Sky Map Alignment Fix

**Date:** 2025-11-17  
**Type:** Bug Fix  
**Status:** ✅ Fixed

---

## Problem

The sky map (Mollweide projection) was not aligning with the pointing track grid
lines because:

1. **Projection Mismatch**: Frontend was using **Aitoff projection** for
   pointing tracks while backend generated **Mollweide projection** sky map
2. **Coordinate System Mismatch**: Image was sized for geographic coordinates
   (-180 to +180, -90 to +90) instead of Mollweide projection coordinates
3. **Visibility Issues**: Gray grid lines were barely visible on the colored sky
   map background

---

## Solution

### Backend Changes (`src/dsa110_contimg/pointing/sky_map_generator.py`)

**Updated `generate_mollweide_sky_map_image()` to generate transparent sky
maps:**

```python
# Avoid log10(<=0): mask those pixels
log_sky = np.full_like(sky_map, np.nan, dtype=float)
mask = sky_map > 0
log_sky[mask] = np.log10(sky_map[mask])

# Create transparent figure for overlay on frontend grid
fig = plt.figure(figsize=(6, 3), dpi=300)
fig.patch.set_alpha(0)  # transparent figure background

hp.mollview(
    log_sky,
    title='',           # no title
    unit='',            # no unit label
    cmap=cmap,
    cbar=False,         # no colorbar
    notext=True,        # no labels on the map
    hold=True,
    fig=fig.number,
)

# Make the axes background transparent as well
ax = plt.gca()
ax.set_facecolor('none')

# Save to file with transparent background
plt.savefig(output_path, bbox_inches="tight", dpi=300, transparent=True)
```

**Key changes:**

- Transparent background (`fig.patch.set_alpha(0)`)
- No title, unit label, or colorbar
- `notext=True` to remove axis labels
- Transparent axes background
- Save with `transparent=True`

### Frontend Changes (`src/components/PointingVisualization.tsx`)

**1. Fixed axis ranges to match Mollweide projection coordinates:**

```typescript
xaxis: {
  range: [-162, 162],  // Mollweide X range: ±2√2 * R ≈ ±162
},
yaxis: {
  range: [-81, 81],  // Mollweide Y range: ±√2 * R ≈ ±81
}
```

**Previously:** Axes were set to geographic coordinates `[-180, 180]` and
`[-90, 90]`, causing the sky map to appear too small or invisible.

**2. Replaced Aitoff projection with Mollweide projection:**

```typescript
// Convert RA/Dec to Mollweide projection coordinates
// This matches the backend's Mollweide sky map projection
const mollweideProjection = useMemo(() => {
  return (ra: number, dec: number): [number, number] => {
    // Convert to radians
    const lambda = ((ra - 180) * Math.PI) / 180; // Longitude (RA centered at 180)
    const phi = (dec * Math.PI) / 180; // Latitude (Dec)

    // Mollweide projection: iteratively solve for theta
    let theta = phi;
    const epsilon = 1e-6;
    const maxIterations = 50;

    for (let i = 0; i < maxIterations; i++) {
      const delta =
        -(theta + Math.sin(theta) - Math.PI * Math.sin(phi)) /
        (1 + Math.cos(theta));
      theta += delta;
      if (Math.abs(delta) < epsilon) break;
    }

    // Mollweide projection formulas
    const R = 180 / Math.PI; // Scale factor to match coordinate system
    const x = ((2 * Math.SQRT2) / Math.PI) * lambda * Math.cos(theta / 2) * R;
    const y = Math.SQRT2 * Math.sin(theta / 2) * R;

    return [x, y];
  };
}, []);
```

**2. Updated sky map image coordinates to match Mollweide projection:**

```typescript
images: enableSkyMapBackground
  ? [
      {
        source:
          "/api/pointing/mollweide-sky-map?frequency_mhz=1400&cmap=inferno&width=1200&height=600",
        xref: "x",
        yref: "y",
        // Mollweide projection coordinate ranges (with R = 180/π ≈ 57.3)
        // X: ±2√2 * R ≈ ±162
        // Y: ±√2 * R ≈ ±81
        x: -162,
        y: -81,
        sizex: 324, // 2 * 162
        sizey: 162, // 2 * 81
        sizing: "stretch",
        opacity: 0.8, // Higher opacity for better visibility
        layer: "below",
      },
    ]
  : [];
```

**3. Changed grid lines to white for visibility:**

```typescript
line: { color: "rgba(255, 255, 255, 0.4)", width: 1, dash: "dot" }
```

---

## Technical Details

### Mollweide Projection Mathematics

The Mollweide projection is an equal-area pseudocylindrical map projection that
preserves area but distorts shape. The projection equations are:

1. **Solve for auxiliary angle θ iteratively:**

   ```
   θ + sin(θ) = π * sin(φ)
   ```

   where φ is the latitude (declination)

2. **Calculate projected coordinates:**

   ```
   x = (2√2 / π) * λ * cos(θ/2) * R
   y = √2 * sin(θ/2) * R
   ```

   where λ is the longitude (RA - 180°) and R is a scale factor

3. **Coordinate ranges:**
   - X range: ±2√2 \* R ≈ ±162 (for R = 180/π ≈ 57.3)
   - Y range: ±√2 \* R ≈ ±81

### Why Mollweide Instead of Aitoff?

- **Backend uses HEALPix**: The Global Sky Model (GSM) is stored in HEALPix
  format
- **healpy.mollview()**: The standard tool for visualizing HEALPix maps uses
  Mollweide projection
- **Equal-area property**: Mollweide preserves area, making it ideal for radio
  sky maps where flux density is important

---

## Files Changed

### Backend

- `/data/dsa110-contimg/src/dsa110_contimg/pointing/sky_map_generator.py`
  - Updated `generate_mollweide_sky_map_image()` for transparent background

### Frontend

- `/data/dsa110-contimg/frontend/src/components/PointingVisualization.tsx`
  - Replaced `aitoffProjection` with `mollweideProjection`
  - Updated sky map image coordinates
  - Changed grid line colors to white
  - Increased sky map opacity to 0.8

---

## Cache Clearing

Sky map images are cached in `state/pointing/maps/`. After backend changes, the
cache must be cleared:

```bash
rm -f /data/dsa110-contimg/state/pointing/maps/*.png
docker compose restart api
```

---

## Verification

1. **Check projection alignment**: Pointing tracks should align with sky map
   features
2. **Check grid visibility**: White dotted grid lines should be visible over the
   colored sky map
3. **Check transparency**: Sky map background should be transparent, allowing
   grid lines to show through

---

## Related Documentation

- [Pointing Visualization Component](../src/components/PointingVisualization.tsx)
- [Sky Map Generator](../../src/dsa110_contimg/pointing/sky_map_generator.py)
- [Mollweide Projection (Wikipedia)](https://en.wikipedia.org/wiki/Mollweide_projection)
- [HEALPix](https://healpix.jpl.nasa.gov/)

---

**Last Updated:** 2025-11-17  
**Status:** ✅ Fixed and verified
