#!/opt/miniforge/envs/casa6/bin/python
"""
Fast downsampling for UVH5 files by merging integrations and/or frequency channels.

This optimized version uses bulk operations and proper chunking for much better performance.
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


def downsample_uvh5_fast(
    input_file,
    output_file,
    time_factor=1,
    freq_factor=1,
    method="average",
    chunk_size=10000,
):
    """
    Fast downsampling of UVH5 file using bulk operations.

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
    logger.info(f"Fast downsampling {input_file}")
    logger.info(f"Time factor: {time_factor}, Frequency factor: {freq_factor}")
    logger.info(f"Method: {method}")

    with h5py.File(input_file, "r") as f_in:
        # Get dimensions
        n_integrations = f_in["Header/time_array"].shape[0]
        n_channels = f_in["Header/freq_array"].shape[1]
        n_pols = f_in["Header/Npols"][()]

        n_downsampled_time = n_integrations // time_factor
        n_downsampled_freq = n_channels // freq_factor

        if n_downsampled_time == 0:
            raise ValueError(f"Cannot downsample time: only {n_integrations} integrations")
        if n_downsampled_freq == 0:
            raise ValueError(f"Cannot downsample frequency: only {n_channels} channels")

        logger.info(f"Input: {n_integrations} integrations, {n_channels} channels")
        logger.info(f"Output: {n_downsampled_time} integrations, {n_downsampled_freq} channels")

        # Create output file with optimized structure
        with h5py.File(output_file, "w") as f_out:
            # Copy header efficiently
            copy_header_fast(
                f_in, f_out, n_downsampled_time, n_downsampled_freq, freq_factor, n_pols
            )

            # Process data in large chunks for efficiency
            process_data_bulk(
                f_in,
                f_out,
                n_downsampled_time,
                time_factor,
                freq_factor,
                method,
                chunk_size,
            )


def copy_header_fast(f_in, f_out, n_downsampled_time, n_downsampled_freq, freq_factor, n_pols):
    """Efficiently copy header structure."""

    # Create Header group
    header_out = f_out.create_group("Header")

    # Copy scalar values directly
    scalar_keys = ["Nbls", "Npols", "Nspws", "Nants_telescope", "Nants_data"]
    for key in scalar_keys:
        if key in f_in["Header"]:
            header_out.create_dataset(key, data=f_in["Header"][key][()])

    # Update dimensions
    header_out.create_dataset("Ntimes", data=n_downsampled_time)
    header_out.create_dataset("Nfreqs", data=n_downsampled_freq)
    header_out.create_dataset("Nblts", data=n_downsampled_time * f_in["Header/Nbls"][()])

    # Create time arrays with proper chunking
    header_out.create_dataset(
        "time_array",
        (n_downsampled_time,),
        dtype=f_in["Header/time_array"].dtype,
        chunks=(min(1000, n_downsampled_time),),
    )
    header_out.create_dataset(
        "integration_time",
        (n_downsampled_time,),
        dtype=f_in["Header/integration_time"].dtype,
        chunks=(min(1000, n_downsampled_time),),
    )

    # Create UVW array with proper chunking
    header_out.create_dataset(
        "uvw_array",
        (n_downsampled_time, 3),
        dtype=f_in["Header/uvw_array"].dtype,
        chunks=(min(1000, n_downsampled_time), 3),
    )

    # Handle frequency array
    if freq_factor > 1:
        # Average frequency channels
        freq_array = f_in["Header/freq_array"][0]
        freq_downsampled = average_frequency_channels(freq_array, freq_factor)
        header_out.create_dataset(
            "freq_array",
            (1, n_downsampled_freq),
            dtype=f_in["Header/freq_array"].dtype,
            chunks=(1, n_downsampled_freq),
        )
        header_out["freq_array"][0] = freq_downsampled

        # Update channel width
        original_channel_width = f_in["Header/channel_width"][()]
        header_out.create_dataset("channel_width", data=original_channel_width * freq_factor)
    else:
        # Copy frequency array as-is
        header_out.create_dataset(
            "freq_array",
            data=f_in["Header/freq_array"][...],
            dtype=f_in["Header/freq_array"].dtype,
            chunks=(1, n_downsampled_freq),
        )
        header_out.create_dataset("channel_width", data=f_in["Header/channel_width"][()])

    # Copy antenna and polarization arrays
    for key in ["ant_1_array", "ant_2_array", "polarization_array"]:
        if key in f_in["Header"]:
            header_out.create_dataset(
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


def process_data_bulk(
    f_in, f_out, n_downsampled_time, time_factor, freq_factor, method, chunk_size
):
    """Process data in large chunks for efficiency."""

    # Create Data group with optimized chunking
    data_group = f_out.create_group("Data")
    n_pols = f_in["Header/Npols"][()]
    nbls = f_in["Header/Nbls"][()]

    # Create datasets with optimal chunking
    vis_chunks = (
        min(1000, n_downsampled_time),
        1,
        min(48, f_in["Header/freq_array"].shape[1] // freq_factor),
        n_pols,
    )

    data_group.create_dataset(
        "visdata",
        (
            n_downsampled_time,
            1,
            f_in["Header/freq_array"].shape[1] // freq_factor,
            n_pols,
        ),
        dtype=np.complex64,
        chunks=vis_chunks,
        compression="gzip",
        compression_opts=1,
    )

    data_group.create_dataset(
        "flags",
        (
            n_downsampled_time,
            1,
            f_in["Header/freq_array"].shape[1] // freq_factor,
            n_pols,
        ),
        dtype=np.bool,
        chunks=vis_chunks,
    )

    data_group.create_dataset(
        "nsamples",
        (
            n_downsampled_time,
            1,
            f_in["Header/freq_array"].shape[1] // freq_factor,
            n_pols,
        ),
        dtype=np.float32,
        chunks=vis_chunks,
    )

    # Process in large chunks
    for chunk_start in range(0, n_downsampled_time, chunk_size):
        chunk_end = min(chunk_start + chunk_size, n_downsampled_time)

        logger.info(f"Processing chunk {chunk_start}-{chunk_end} of {n_downsampled_time}")

        # Process this chunk
        process_chunk_bulk(
            f_in, f_out, chunk_start, chunk_end, time_factor, freq_factor, method, nbls
        )


def process_chunk_bulk(f_in, f_out, chunk_start, chunk_end, time_factor, freq_factor, method, nbls):
    """Process a large chunk of data efficiently."""

    n_downsampled_time = chunk_end - chunk_start

    # Pre-allocate arrays for this chunk
    start_idx = chunk_start * time_factor
    end_idx = min(start_idx + n_downsampled_time * time_factor, f_in["Header/time_array"].shape[0])

    # Read all data for this chunk at once
    vis_data = f_in["Data/visdata"][start_idx:end_idx]
    flags = f_in["Data/flags"][start_idx:end_idx]
    nsamples = f_in["Data/nsamples"][start_idx:end_idx]
    times = f_in["Header/time_array"][start_idx:end_idx]
    integration_times = f_in["Header/integration_time"][start_idx:end_idx]
    uvw_data = f_in["Header/uvw_array"][start_idx:end_idx]

    # Reshape for time downsampling
    if time_factor > 1:
        n_time_groups = n_downsampled_time
        vis_data = vis_data[: n_time_groups * time_factor].reshape(
            n_time_groups,
            time_factor,
            vis_data.shape[1],
            vis_data.shape[2],
            vis_data.shape[3],
        )
        flags = flags[: n_time_groups * time_factor].reshape(
            n_time_groups, time_factor, flags.shape[1], flags.shape[2], flags.shape[3]
        )
        nsamples = nsamples[: n_time_groups * time_factor].reshape(
            n_time_groups,
            time_factor,
            nsamples.shape[1],
            nsamples.shape[2],
            nsamples.shape[3],
        )
        times = times[: n_time_groups * time_factor].reshape(n_time_groups, time_factor)
        integration_times = integration_times[: n_time_groups * time_factor].reshape(
            n_time_groups, time_factor
        )
        # Reshape UVW data properly
        uvw_data = uvw_data[: n_time_groups * time_factor].reshape(n_time_groups, time_factor, 3)

        # Average over time
        if method == "weighted":
            weights = nsamples / np.sum(nsamples, axis=1, keepdims=True)
            vis_data = np.sum(vis_data * weights, axis=1)
        else:
            vis_data = np.mean(vis_data, axis=1)

        flags = np.any(flags, axis=1)
        nsamples = np.sum(nsamples, axis=1)
        times = np.mean(times, axis=1)
        integration_times = np.sum(integration_times, axis=1)
        uvw_data = np.mean(uvw_data, axis=1)  # Average over time

    # Handle frequency downsampling
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
        if method == "weighted":
            weights = nsamples_reshaped / np.sum(nsamples_reshaped, axis=3, keepdims=True)
            vis_data = np.sum(vis_reshaped * weights, axis=3)
        else:
            vis_data = np.mean(vis_reshaped, axis=3)

        flags = np.any(flags_reshaped, axis=3)
        nsamples = np.sum(nsamples_reshaped, axis=3)

    # Write all data for this chunk at once
    f_out["Data/visdata"][chunk_start:chunk_end] = vis_data
    f_out["Data/flags"][chunk_start:chunk_end] = flags
    f_out["Data/nsamples"][chunk_start:chunk_end] = nsamples
    f_out["Header/time_array"][chunk_start:chunk_end] = times
    f_out["Header/integration_time"][chunk_start:chunk_end] = integration_times

    # Write UVW data
    f_out["Header/uvw_array"][chunk_start:chunk_end] = uvw_data


def main():
    parser = argparse.ArgumentParser(
        description="Fast downsampling of UVH5 files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Time downsampling by factor of 2
  python -m dsa110_contimg.conversion.downsample_uvh5.cli single input.uvh5 output.uvh5 --time-factor 2

  # Frequency downsampling by factor of 4
  python -m dsa110_contimg.conversion.downsample_uvh5.cli single input.uvh5 output.uvh5 --freq-factor 4

  # Combined downsampling with weighted averaging
  python -m dsa110_contimg.conversion.downsample_uvh5.cli single input.uvh5 output.uvh5 --time-factor 2 --freq-factor 4 --method weighted
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
        default=10000,
        help="Chunk size for processing (default: 10000)",
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
        downsample_uvh5_fast(
            args.input,
            args.output,
            args.time_factor,
            args.freq_factor,
            args.method,
            args.chunk_size,
        )

        logger.info(f"Fast downsampling complete: {args.output}")

        # Print summary
        input_size = Path(args.input).stat().st_size / (1024**2)  # MB
        output_size = Path(args.output).stat().st_size / (1024**2)  # MB
        compression_ratio = input_size / output_size if output_size > 0 else 0

        logger.info(f"File size: {input_size:.1f} MB -> {output_size:.1f} MB")
        logger.info(f"Compression ratio: {compression_ratio:.1f}x")

    except Exception as e:
        logger.error(f"Fast downsampling failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
