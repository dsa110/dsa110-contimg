# linearmosaic Implementation Testing

## Status

**Basic Function Tests: ✓ PASSED**
- Function imports successfully
- Error handling works correctly
- Function signature is correct

**Integration Tests: ⏳ PENDING**
- Requires real CASA image tiles with PB images
- No planned mosaics currently available
- No real tiles found in test directories

## Test Results

### 1. Function Availability ✓
```
✓ Function signature: (tiles: List[str], metrics_dict: dict, output_path: str) -> None
✓ Parameters: ['tiles', 'metrics_dict', 'output_path']
```

### 2. Error Handling ✓
- ✓ Correctly raises `MosaicError` for empty tiles
- ✓ Correctly raises `MosaicError` for non-existent tiles
- ✓ Correctly raises `MissingPrimaryBeamError` when PB images missing

### 3. Tool Availability ✓
```
✓ linearmosaic tool created successfully
✓ Available methods: defineoutputimage, makemosaic, saultweightimage, setlinmostype, setoutputimage
✓ setlinmostype('optimal') called successfully
```

## Testing Requirements

To run full integration tests, need:

1. **Real CASA Image Tiles:**
   - CASA `.image` format directories
   - PB-corrected images
   - Valid coordinate systems

2. **Primary Beam Images:**
   - Matching PB images for each tile
   - Same coordinate system as tiles

3. **Test Data:**
   - At least 2-3 tiles for meaningful mosaic
   - Tiles should overlap or be adjacent
   - Valid metadata in products database

## Next Steps

1. **Create Test Mosaic Plan:**
   ```bash
   python -m dsa110_contimg.mosaic.cli plan \
       --tiles /path/to/tile1.image /path/to/tile2.image \
       --output /tmp/test_mosaic.image
   ```

2. **Build Test Mosaic:**
   ```bash
   python -m dsa110_contimg.mosaic.cli build --mosaic-id <id>
   ```

3. **Verify Output:**
   - Check mosaic image exists
   - Verify coordinate system
   - Check for weight image
   - Compare with fallback method output

## Known Limitations

- `linearmosaic` requires PB images for all tiles
- Falls back to `imregrid` + `immath` if PB images missing
- Requires tiles to be regridded to common coordinate system first

## Test Script

See `scripts/test_linearmosaic.py` for automated testing script.

To run:
```bash
/opt/miniforge/envs/casa6/bin/python scripts/test_linearmosaic.py
```

