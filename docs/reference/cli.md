# Reference: CLI

- Streaming worker
```
python -m dsa110_contimg.conversion.streaming.streaming_converter --help
```
- Imaging worker
```
python -m dsa110_contimg.imaging.worker --help
```
- Converter orchestrator
```
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator --help
```
- Standalone converter (single UVH5 → MS)
```
python -m dsa110_contimg.conversion.uvh5_to_ms --help
```
- Downsample UVH5 (unified CLI)
```
python -m dsa110_contimg.conversion.downsample_uvh5.cli --help
python -m dsa110_contimg.conversion.downsample_uvh5.cli single --help
python -m dsa110_contimg.conversion.downsample_uvh5.cli fast --help
python -m dsa110_contimg.conversion.downsample_uvh5.cli batch --help
```
- Legacy entrypoints (still available)
```
python -m dsa110_contimg.conversion.downsample_uvh5.downsample_hdf5 --help
python -m dsa110_contimg.conversion.downsample_uvh5.downsample_hdf5_batch --help
python -m dsa110_contimg.conversion.downsample_uvh5.downsample_hdf5_fast --help
```
- Registry CLI
```
python -m dsa110_contimg.database.registry_cli --help
```
- Mosaic CLI
```
python -m dsa110_contimg.mosaic.cli --help
```
- Calibration CLI
```
python -m dsa110_contimg.calibration.cli --help
```
- Calibration catalog CLI
```
python -m dsa110_contimg.calibration.catalog_cli --help
```
- Photometry (forced peak)
```
python -m dsa110_contimg.photometry.cli --help
```
