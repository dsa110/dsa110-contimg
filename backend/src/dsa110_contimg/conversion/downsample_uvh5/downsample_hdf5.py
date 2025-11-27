#!/opt/miniforge/envs/casa6/bin/python
"""
Downsample UVH5 files by merging integrations and/or frequency channels.

This script provides post-processing downsampling capabilities for UVH5 files,
allowing users to reduce file size and processing time by averaging data
in time and/or frequency dimensions.

Usage:
    python -m dsa110_contimg.conversion.downsample_uvh5.cli single input.uvh5 output.uvh5 --time-factor 2 --freq-factor 4
    python -m dsa110_contimg.conversion.downsample_uvh5.cli single input.uvh5 output.uvh5 --time-factor 2
    python -m dsa110_contimg.conversion.downsample_uvh5.cli single input.uvh5 output.uvh5 --freq-factor 4
"""

import argparse
import logging
import sys
from pathlib import Path

import h5py  # type: ignore
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def downsample_uvh5(
    input_file,
    output_file,
    time_factor=1,
    freq_factor=1,
    method="average",
    chunk_size=1000,
):
    """
    Downsample UVH5 file by merging integrations and/or frequency channels.

    Parameters
    ----------
    input_file : str
        Path to input UVH5 file
    output_file : str
        Path to output UVH5 file
    time_factor : int
        Factor by which to downsample time (merge N integrations)
    freq_factor : int
        Factor by which to downsample frequency (merge N channels)
    method : str
        Method for merging: 'average' or 'weighted'
    chunk_size : int
        Number of integrations to process at once
    """
    logger.info(f"Downsampling {input_file}")
    logger.info(f"Time factor: {time_factor}, Frequency factor: {freq_factor}")
    logger.info(f"Method: {method}")

    # Use large cache for intensive I/O operations (64 MB)
    from dsa110_contimg.utils.hdf5_io import HDF5_CACHE_SIZE_LARGE, HDF5_CACHE_SLOTS

    with h5py.File(input_file, "r", rdcc_nbytes=HDF5_CACHE_SIZE_LARGE, rdcc_nslots=HDF5_CACHE_SLOTS) as f_in:
        # Get dimensions
        n_integrations = f_in["Header/time_array"].shape[0]
        n_channels = f_in["Header/freq_array"].shape[1]

        n_downsampled_time = n_integrations // time_factor
        n_downsampled_freq = n_channels // freq_factor

        if n_downsampled_time == 0:
            raise ValueError(f"Cannot downsample time: only {n_integrations} integrations")
        if n_downsampled_freq == 0:
            raise ValueError(f"Cannot downsample frequency: only {n_channels} channels")

        logger.info(f"Input: {n_integrations} integrations, {n_channels} channels")
        logger.info(f"Output: {n_downsampled_time} integrations, {n_downsampled_freq} channels")

        # Get data shapes
        vis_shape = f_in["Data/visdata"].shape
        flag_shape = f_in["Data/flags"].shape
        nsample_shape = f_in["Data/nsamples"].shape

        logger.info(f"Visibility shape: {vis_shape}")

        # Create output file
        with h5py.File(output_file, "w") as f_out:
            # Copy header structure
            copy_header_structure(f_in, f_out, n_downsampled_time, n_downsampled_freq, freq_factor)

            # Create downsampled datasets
            create_downsampled_datasets(
                f_out,
                n_downsampled_time,
                n_downsampled_freq,
                vis_shape,
                flag_shape,
                nsample_shape,
            )

            # Process data in chunks
            for chunk_start in range(0, n_downsampled_time, chunk_size):
                chunk_end = min(chunk_start + chunk_size, n_downsampled_time)
                process_chunk(
                    f_in,
                    f_out,
                    chunk_start,
                    chunk_end,
                    time_factor,
                    freq_factor,
                    method,
                )

                if chunk_start % (chunk_size * 10) == 0:
                    logger.info(f"Processed {chunk_start}/{n_downsampled_time} integrations")


def copy_header_structure(f_in, f_out, n_downsampled_time, n_downsampled_freq, freq_factor):
    """Copy header structure and modify for downsampled data."""

    # Copy all header groups
    def copy_group(src, dst, name):
        if name in src:
            if isinstance(src[name], h5py.Group):
                if name not in dst:
                    dst.create_group(name)
                for key in src[name].keys():
                    copy_group(src[name], dst[name], key)
            else:
                # Copy dataset - create new dataset with same properties
                if name in dst:
                    del dst[name]
                src_ds = src[name]
                dst.create_dataset(name, data=src_ds[...], shape=src_ds.shape, dtype=src_ds.dtype)

    # Copy header
    copy_group(f_in, f_out, "Header")

    # Update dimensions
    f_out["Header/Ntimes"][()] = n_downsampled_time
    f_out["Header/Nfreqs"][()] = n_downsampled_freq
    f_out["Header/Nblts"][()] = n_downsampled_time * f_in["Header/Nbls"][()]

    # Create resizable datasets - delete and recreate with proper chunking
    if "time_array" in f_out["Header"]:
        del f_out["Header/time_array"]
    f_out["Header"].create_dataset(
        "time_array",
        (n_downsampled_time,),
        dtype=f_in["Header/time_array"].dtype,
        chunks=True,
        maxshape=(None,),
    )

    if "integration_time" in f_out["Header"]:
        del f_out["Header/integration_time"]
    f_out["Header"].create_dataset(
        "integration_time",
        (n_downsampled_time,),
        dtype=f_in["Header/integration_time"].dtype,
        chunks=True,
        maxshape=(None,),
    )

    if "uvw_array" in f_out["Header"]:
        del f_out["Header/uvw_array"]
    f_out["Header"].create_dataset(
        "uvw_array",
        (n_downsampled_time * f_in["Header/Nbls"][()], 3),
        dtype=f_in["Header/uvw_array"].dtype,
        chunks=True,
        maxshape=(None, 3),
    )

    # Handle frequency array downsampling
    if freq_factor > 1:
        # Average frequency channels
        freq_array = f_in["Header/freq_array"][0]  # Shape: (n_channels,)
        freq_downsampled = average_frequency_channels(freq_array, freq_factor)

        # Delete and recreate freq_array with proper size
        if "freq_array" in f_out["Header"]:
            del f_out["Header/freq_array"]
        f_out["Header"].create_dataset(
            "freq_array",
            (1, n_downsampled_freq),
            dtype=f_in["Header/freq_array"].dtype,
            chunks=True,
        )
        f_out["Header/freq_array"][0] = freq_downsampled

        # Update channel width
        original_channel_width = f_in["Header/channel_width"][()]
        f_out["Header/channel_width"][()] = original_channel_width * freq_factor
    else:
        # Copy frequency array as-is
        if "freq_array" in f_out["Header"]:
            del f_out["Header/freq_array"]
        f_out["Header"].create_dataset(
            "freq_array",
            data=f_in["Header/freq_array"][...],
            dtype=f_in["Header/freq_array"].dtype,
            chunks=True,
        )

    # Copy antenna and polarization info
    for key in ["ant_1_array", "ant_2_array", "polarization_array"]:
        if key in f_in["Header"]:
            if key in f_out["Header"]:
                del f_out["Header"][key]
            f_out["Header"].create_dataset(
                key,
                data=f_in["Header"][key][...],
                dtype=f_in["Header"][key].dtype,
                chunks=True,
            )


def average_frequency_channels(freq_array, freq_factor):
    """Average frequency channels to create downsampled frequency array."""
    n_channels = len(freq_array)
    n_downsampled = n_channels // freq_factor

    # Reshape and average
    freq_reshaped = freq_array[: n_downsampled * freq_factor].reshape(n_downsampled, freq_factor)
    freq_averaged = np.mean(freq_reshaped, axis=1)

    return freq_averaged


def create_downsampled_datasets(
    f_out, n_downsampled_time, n_downsampled_freq, vis_shape, flag_shape, nsample_shape
):
    """Create downsampled data datasets."""
    n_pols = f_out["Header/Npols"][()]

    # Create data group
    data_group = f_out.create_group("Data")

    # Create datasets with downsampled dimensions
    data_group.create_dataset(
        "visdata",
        (n_downsampled_time, 1, n_downsampled_freq, n_pols),
        dtype=np.complex64,
        chunks=True,
    )

    data_group.create_dataset(
        "flags",
        (n_downsampled_time, 1, n_downsampled_freq, n_pols),
        dtype=np.bool,
        chunks=True,
    )

    data_group.create_dataset(
        "nsamples",
        (n_downsampled_time, 1, n_downsampled_freq, n_pols),
        dtype=np.float32,
        chunks=True,
    )


def process_chunk(f_in, f_out, chunk_start, chunk_end, time_factor, freq_factor, method):
    """Process a chunk of integrations."""
    nbls = f_in["Header/Nbls"][()]

    for i in range(chunk_start, chunk_end):
        # Calculate source indices
        start_idx = i * time_factor
        end_idx = min(start_idx + time_factor, f_in["Header/time_array"].shape[0])

        # Read data chunk
        vis_data = f_in["Data/visdata"][start_idx:end_idx]
        flags = f_in["Data/flags"][start_idx:end_idx]
        nsamples = f_in["Data/nsamples"][start_idx:end_idx]
        times = f_in["Header/time_array"][start_idx:end_idx]

        # Merge integrations and frequency channels
        if method == "weighted":
            merged_vis, merged_flags, merged_nsamples = merge_weighted(
                vis_data, flags, nsamples, time_factor, freq_factor
            )
        else:  # average
            merged_vis, merged_flags, merged_nsamples = merge_average(
                vis_data, flags, nsamples, time_factor, freq_factor
            )

        # Calculate merged time
        merged_time = np.mean(times)
        merged_integration_time = np.sum(f_in["Header/integration_time"][start_idx:end_idx])

        # Write merged data
        f_out["Data/visdata"][i, 0] = merged_vis[0]
        f_out["Data/flags"][i, 0] = merged_flags[0]
        f_out["Data/nsamples"][i, 0] = merged_nsamples[0]
        f_out["Header/time_array"][i] = merged_time
        f_out["Header/integration_time"][i] = merged_integration_time

        # Handle UVW coordinates - average UVW over time
        uvw_start = i * nbls
        uvw_end = (i + 1) * nbls
        uvw_data = f_in["Header/uvw_array"][start_idx * nbls : end_idx * nbls]
        # Average UVW coordinates over the time range
        uvw_averaged = np.mean(uvw_data, axis=0)
        f_out["Header/uvw_array"][uvw_start:uvw_end] = uvw_averaged


def merge_average(vis_data, flags, nsamples, time_factor, freq_factor):
    """Merge integrations and frequency channels using simple averaging."""
    # First average over time
    if time_factor > 1:
        vis_data = np.mean(vis_data, axis=0, keepdims=True)
        flags = np.any(flags, axis=0, keepdims=True)
        nsamples = np.sum(nsamples, axis=0, keepdims=True)

    # Then average over frequency
    if freq_factor > 1:
        n_channels = vis_data.shape[2]
        n_downsampled_freq = n_channels // freq_factor

        # Reshape for frequency averaging
        vis_reshaped = vis_data[:, :, : n_downsampled_freq * freq_factor, :].reshape(
            vis_data.shape[0],
            vis_data.shape[1],
            n_downsampled_freq,
            freq_factor,
            vis_data.shape[3],
        )
        flags_reshaped = flags[:, :, : n_downsampled_freq * freq_factor, :].reshape(
            flags.shape[0],
            flags.shape[1],
            n_downsampled_freq,
            freq_factor,
            flags.shape[3],
        )
        nsamples_reshaped = nsamples[:, :, : n_downsampled_freq * freq_factor, :].reshape(
            nsamples.shape[0],
            nsamples.shape[1],
            n_downsampled_freq,
            freq_factor,
            nsamples.shape[3],
        )

        # Average over frequency
        vis_data = np.mean(vis_reshaped, axis=3)
        flags = np.any(flags_reshaped, axis=3)
        nsamples = np.sum(nsamples_reshaped, axis=3)

    return vis_data, flags, nsamples


def merge_weighted(vis_data, flags, nsamples, time_factor, freq_factor):
    """Merge integrations and frequency channels using weighted averaging."""
    # First average over time
    if time_factor > 1:
        weights = nsamples / np.sum(nsamples, axis=0, keepdims=True)
        vis_data = np.sum(vis_data * weights, axis=0, keepdims=True)
        flags = np.any(flags, axis=0, keepdims=True)
        nsamples = np.sum(nsamples, axis=0, keepdims=True)

    # Then average over frequency
    if freq_factor > 1:
        n_channels = vis_data.shape[2]
        n_downsampled_freq = n_channels // freq_factor

        # Reshape for frequency averaging
        vis_reshaped = vis_data[:, :, : n_downsampled_freq * freq_factor, :].reshape(
            vis_data.shape[0],
            vis_data.shape[1],
            n_downsampled_freq,
            freq_factor,
            vis_data.shape[3],
        )
        flags_reshaped = flags[:, :, : n_downsampled_freq * freq_factor, :].reshape(
            flags.shape[0],
            flags.shape[1],
            n_downsampled_freq,
            freq_factor,
            flags.shape[3],
        )
        nsamples_reshaped = nsamples[:, :, : n_downsampled_freq * freq_factor, :].reshape(
            nsamples.shape[0],
            nsamples.shape[1],
            n_downsampled_freq,
            freq_factor,
            nsamples.shape[3],
        )

        # Weighted average over frequency
        weights = nsamples_reshaped / np.sum(nsamples_reshaped, axis=3, keepdims=True)
        vis_data = np.sum(vis_reshaped * weights, axis=3)
        flags = np.any(flags_reshaped, axis=3)
        nsamples = np.sum(nsamples_reshaped, axis=3)

    return vis_data, flags, nsamples


def main():
    parser = argparse.ArgumentParser(
        description="Downsample UVH5 files by merging integrations and/or frequency channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Downsample time by factor of 2, frequency by factor of 4
  python downsample_hdf5.py input.uvh5 output.uvh5 --time-factor 2 --freq-factor 4

  # Only frequency downsampling (keep all integrations)
  python downsample_hdf5.py input.uvh5 output.uvh5 --freq-factor 4

  # Only time downsampling (keep all channels)
  python downsample_hdf5.py input.uvh5 output.uvh5 --time-factor 2

  # Aggressive downsampling with weighted averaging
  python downsample_hdf5.py input.uvh5 output.uvh5 --time-factor 4 --freq-factor 4 --method weighted
        """,
    )

    parser.add_argument("input", help="Input UVH5 file")
    parser.add_argument("output", help="Output UVH5 file")
    parser.add_argument(
        "--time-factor",
        type=int,
        default=1,
        help="Time downsampling factor (default: 1)",
    )
    parser.add_argument(
        "--freq-factor",
        type=int,
        default=1,
        help="Frequency downsampling factor (default: 1)",
    )
    parser.add_argument(
        "--method",
        choices=["average", "weighted"],
        default="average",
        help="Merging method (default: average)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Chunk size for processing (default: 1000)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate input file
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    # Validate factors
    if args.time_factor < 1:
        logger.error("Time factor must be >= 1")
        sys.exit(1)
    if args.freq_factor < 1:
        logger.error("Frequency factor must be >= 1")
        sys.exit(1)

    # Create output directory if needed
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    try:
        # Run downsampling
        downsample_uvh5(
            args.input,
            args.output,
            args.time_factor,
            args.freq_factor,
            args.method,
            args.chunk_size,
        )

        logger.info(f"Downsampling complete: {args.output}")

        # Print summary
        with h5py.File(args.input, "r"), h5py.File(args.output, "r"):
            input_size = Path(args.input).stat().st_size / (1024**3)  # GB
            output_size = Path(args.output).stat().st_size / (1024**3)  # GB
            compression_ratio = input_size / output_size if output_size > 0 else 0

            logger.info(f"File size reduction: {input_size:.2f} GB -> {output_size:.2f} GB")
            logger.info(f"Compression ratio: {compression_ratio:.1f}x")

    except Exception as e:
        logger.error(f"Downsampling failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
