# DSA-110 UVH5 to CASA Measurement Set Converter

This repository now focuses on two supported conversion paths:

- `src/dsa110_contimg/conversion/uvh5_to_ms_converter_v2.py` – batch converter invoked by the streaming service.
- `src/dsa110_contimg/conversion/streaming_converter.py` – real-time daemon that watches an ingest directory and dispatches the batch converter.

Legacy tools (the dsacalib wrappers and the old `UnifiedHDF5Converter`) have been relocated to `pipeline/legacy/` for archival reference.

## Supported Entry Points

- `python -m dsa110_contimg.conversion.streaming_converter ...` – run the streaming daemon directly for manual testing or non-systemd environments.
- `systemctl enable --now dsa110-streaming-converter` – deploy via the unit in `pipeline/scripts/dsa110-streaming-converter.service` (adjust ExecStart paths as needed).
- `from dsa110_contimg.conversion import convert_subband_groups_to_ms` – programmatic access to the batch converter used by the streaming worker.

## Legacy Code

The historical utilities (`dsa110_uvh5_to_ms.py`, `UnifiedHDF5Converter`, etc.) are preserved in `pipeline/legacy/conversion/` and `pipeline/legacy/scripts/`. They are no longer maintained and should not be used for new automation.
