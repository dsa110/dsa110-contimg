Legacy MS Utilities (Archived)

This directory contains the legacy Measurement Set (MS) helper utilities that
previously lived in `dsa110_contimg/utils/ms_io.py`.

Why archived
- The active pipeline has standardized on the converter in
  `dsa110_contimg/core/conversion/uvh5_to_ms_converter_v2.py`, which writes MS
  directly with pyuvdata (default), optionally via per-subband + concat, or the
  experimental dask-ms path.
- Maintaining multiple MS writers and low-level table manipulation helpers led
  to duplication and confusion. These utilities are no longer imported or used
  by the current pipeline.

What’s here
- A snapshot of the legacy helpers as they were in `utils/ms_io.py`, including:
  - `convert_to_ms_data_driven`, `create_ms_structure_data_driven`,
    `create_ms_structure_direct`
  - `create_ms_structure_full`
  - `append_channels_to_ms`
  - `write_uvdata_to_ms_via_uvfits`
  - `populate_unity_model`
  - `_get_telescope_location`, `compute_absolute_antenna_positions`

Important notes
- These functions are not exported by `dsa110_contimg.utils` and are not part
  of the supported API.
- They may rely on older assumptions around pyuvdata/casa versions and may
  require adaptation before reuse.
- Prefer the maintained paths:
  - Streaming service: `dsa110_contimg/core/conversion/streaming_converter.py`
  - Batch converter: `dsa110_contimg/core/conversion/uvh5_to_ms_converter_v2.py`
  - Direct per-subband writer + concat: `dsa110_contimg/core/conversion/direct_ms_writer.py`

If you need to experiment with these routines, copy them into a sandbox module
and adapt to your environment. Consider upstreaming any improvements into the
maintained converter instead.

