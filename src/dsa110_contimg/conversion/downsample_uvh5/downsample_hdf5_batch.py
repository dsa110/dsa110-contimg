#!/usr/bin/env python3
"""
Batch downsampling for UVH5 files in directories.

This script processes multiple UVH5 files (subbands) in a directory,
applying the same downsampling parameters to all files and writing
the results to an output directory.
"""

import h5py  # type: ignore
import numpy as np
import argparse
from pathlib import Path
import sys
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def find_uvh5_files(input_dir):
    """Find all UVH5 files in the input directory."""
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    # Look for .hdf5 and .uvh5 files
    uvh5_files = []
    for pattern in ["*.hdf5", "*.uvh5"]:
        uvh5_files.extend(input_path.glob(pattern))

    if not uvh5_files:
        raise FileNotFoundError(f"No UVH5 files found in {input_dir}")

    # Sort files for consistent processing order
    uvh5_files.sort()

    logger.info(f"Found {len(uvh5_files)} UVH5 files in {input_dir}")
    return uvh5_files


def process_single_file(
    input_file, output_file, time_factor, freq_factor, method, chunk_size
):
    """Process a single UVH5 file."""
    try:
        import sys
        from pathlib import Path

        # Add the conversion module to path
        conversion_path = Path(__file__).parent
        if str(conversion_path) not in sys.path:
            sys.path.insert(0, str(conversion_path))

        from .downsample_hdf5_fast import downsample_uvh5_fast

        logger.info(f"Processing {input_file.name}")
        downsample_uvh5_fast(
            str(input_file),
            str(output_file),
            time_factor,
            freq_factor,
            method,
            chunk_size,
        )

        # Get file sizes for reporting
        input_size = input_file.stat().st_size / (1024**2)  # MB
        output_size = output_file.stat().st_size / (1024**2)  # MB
        compression_ratio = input_size / output_size if output_size > 0 else 0

        return {
            "input_file": input_file.name,
            "output_file": output_file.name,
            "input_size_mb": input_size,
            "output_size_mb": output_size,
            "compression_ratio": compression_ratio,
            "success": True,
        }

    except Exception as e:
        logger.error(f"Failed to process {input_file.name}: {e}")
        return {
            "input_file": input_file.name,
            "output_file": output_file.name,
            "error": str(e),
            "success": False,
        }


def downsample_uvh5_batch(
    input_dir,
    output_dir,
    time_factor=1,
    freq_factor=1,
    method="average",
    chunk_size=10000,
    max_workers=None,
):
    """
    Batch downsampling of UVH5 files in a directory.

    Parameters
    ----------
    input_dir : str
        Path to input directory containing UVH5 files
    output_dir : str
        Path to output directory for downsampled files
    time_factor : int
        Factor by which to downsample time (merge N integrations)
    freq_factor : int
        Factor by which to downsample frequency (merge N channels)
    method : str
        Method for merging: 'average' or 'weighted'
    chunk_size : int
        Number of integrations to process at once
    max_workers : int, optional
        Maximum number of parallel workers. If None, uses CPU count.
    """
    logger.info(f"Batch downsampling from {input_dir} to {output_dir}")
    logger.info(f"Time factor: {time_factor}, Frequency factor: {freq_factor}")
    logger.info(f"Method: {method}")

    # Find all UVH5 files
    uvh5_files = find_uvh5_files(input_dir)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Determine number of workers
    if max_workers is None:
        max_workers = min(mp.cpu_count(), len(uvh5_files))

    logger.info(f"Using {max_workers} parallel workers")

    # Prepare file pairs
    file_pairs = []
    for input_file in uvh5_files:
        # Create output filename with downsampling suffix
        if time_factor > 1 and freq_factor > 1:
            suffix = f"_ds{time_factor}t{freq_factor}f"
        elif time_factor > 1:
            suffix = f"_ds{time_factor}t"
        elif freq_factor > 1:
            suffix = f"_ds{freq_factor}f"
        else:
            suffix = "_ds"

        # Preserve original extension
        if input_file.suffix in [".hdf5", ".uvh5"]:
            output_file = output_path / f"{input_file.stem}{suffix}.hdf5"
        else:
            output_file = output_path / f"{input_file.name}{suffix}"

        file_pairs.append((input_file, output_file))

    # Process files in parallel
    results = []
    total_input_size = 0
    total_output_size = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        future_to_pair = {
            executor.submit(
                process_single_file,
                input_file,
                output_file,
                time_factor,
                freq_factor,
                method,
                chunk_size,
            ): (input_file, output_file)
            for input_file, output_file in file_pairs
        }

        # Collect results as they complete
        for future in as_completed(future_to_pair):
            result = future.result()
            results.append(result)

            if result["success"]:
                total_input_size += result["input_size_mb"]
                total_output_size += result["output_size_mb"]
                logger.info(
                    f"✓ {result['input_file']} -> {result['output_file']} "
                    f"({result['compression_ratio']:.1f}x)"
                )
            else:
                logger.error(f"✗ {result['input_file']}: {result['error']}")

    # Print summary
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    logger.info(f"\nBatch processing complete:")
    logger.info(f"  Successful: {len(successful)}/{len(results)} files")
    logger.info(f"  Failed: {len(failed)} files")

    if successful:
        overall_compression = (
            total_input_size / total_output_size if total_output_size > 0 else 0
        )
        logger.info(
            f"  Total size: {total_input_size:.1f} MB -> {total_output_size:.1f} MB"
        )
        logger.info(f"  Overall compression: {overall_compression:.1f}x")

    if failed:
        logger.error(f"  Failed files:")
        for result in failed:
            logger.error(f"    {result['input_file']}: {result['error']}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Batch downsampling of UVH5 files in directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Downsample all UVH5 files in a directory (time factor 2)
  python -m dsa110_contimg.conversion.downsample_uvh5.cli batch input_dir/ output_dir/ --time-factor 2

  # Downsample with both time and frequency factors
  python -m dsa110_contimg.conversion.downsample_uvh5.cli batch input_dir/ output_dir/ --time-factor 2 --freq-factor 4

  # Use weighted averaging with custom chunk size
  python -m dsa110_contimg.conversion.downsample_uvh5.cli batch input_dir/ output_dir/ --time-factor 2 --method weighted --chunk-size 5000

  # Limit parallel processing to 2 workers
  python -m dsa110_contimg.conversion.downsample_uvh5.cli batch input_dir/ output_dir/ --time-factor 2 --max-workers 2
        """,
    )

    parser.add_argument("input_dir", help="Input directory containing UVH5 files")
    parser.add_argument("output_dir", help="Output directory for downsampled files")
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
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of parallel workers (default: CPU count)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate input directory
    if not Path(args.input_dir).exists():
        logger.error(f"Input directory not found: {args.input_dir}")
        sys.exit(1)

    # Validate factors
    if args.time_factor < 1:
        logger.error("Time factor must be >= 1")
        sys.exit(1)
    if args.freq_factor < 1:
        logger.error("Frequency factor must be >= 1")
        sys.exit(1)

    try:
        # Run batch downsampling
        results = downsample_uvh5_batch(
            args.input_dir,
            args.output_dir,
            args.time_factor,
            args.freq_factor,
            args.method,
            args.chunk_size,
            args.max_workers,
        )

        # Exit with error code if any files failed
        failed_count = sum(1 for r in results if not r["success"])
        if failed_count > 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Batch downsampling failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
