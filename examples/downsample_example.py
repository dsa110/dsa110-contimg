#!/usr/bin/env python3
"""
Example usage of the downsample_hdf5.py script.

This example shows how to use the downsampling script to reduce
UVH5 file size and processing time.
"""

import subprocess
import sys
from pathlib import Path


def run_downsampling_example():
    """Run example downsampling operations."""

    # Example UVH5 file (replace with actual file)
    input_file = "example_input.uvh5"

    if not Path(input_file).exists():
        print(f"Example file {input_file} not found.")
        print("Please provide a valid UVH5 file path.")
        return

    # Example 1: Time downsampling by factor of 2
    print("Example 1: Time downsampling by factor of 2")
    cmd1 = [
        "python3", "-m", "dsa110_contimg.conversion.downsample_uvh5.cli", "single",
        input_file, "output_time_ds2.uvh5",
        "--time-factor", "2"
    ]
    subprocess.run(cmd1)

    # Example 2: Frequency downsampling by factor of 4
    print("\nExample 2: Frequency downsampling by factor of 4")
    cmd2 = [
        "python3", "-m", "dsa110_contimg.conversion.downsample_uvh5.cli", "single",
        input_file, "output_freq_ds4.uvh5",
        "--freq-factor", "4"
    ]
    subprocess.run(cmd2)

    # Example 3: Combined downsampling
    print("\nExample 3: Combined time and frequency downsampling")
    cmd3 = [
        "python3", "-m", "dsa110_contimg.conversion.downsample_uvh5.cli", "single",
        input_file, "output_combined_ds.uvh5",
        "--time-factor", "2", "--freq-factor", "4",
        "--method", "weighted"
    ]
    subprocess.run(cmd3)

    print("\nDownsampling examples completed!")


if __name__ == "__main__":
    run_downsampling_example()
