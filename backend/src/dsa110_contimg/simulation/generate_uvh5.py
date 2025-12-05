import os

import h5py
import numpy as np


def generate_synthetic_uvh5(output_dir, start_time, duration_minutes, num_subbands=16):
    """
    Generate synthetic UVH5 files for testing.

    Parameters:
    - output_dir: Directory to save the generated UVH5 files.
    - start_time: Start time for the observations in ISO format.
    - duration_minutes: Duration of the observation in minutes.
    - num_subbands: Number of subbands to generate (default is 16).
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define parameters for synthetic data
    num_times = int(duration_minutes * 60)  # Convert duration to seconds
    time_array = np.linspace(0, duration_minutes * 60, num_times)
    freq_array = np.linspace(1e9, 2e9, num_subbands)  # Frequency range from 1 GHz to 2 GHz
    visibilities = np.random.normal(
        size=(num_times, num_subbands, 4)
    )  # Random visibilities for 4 polarizations

    for i in range(num_subbands):
        filename = os.path.join(output_dir, f"{start_time}_sb{i:02d}.hdf5")
        with h5py.File(filename, "w") as h5file:
            h5file.create_dataset("time_array", data=time_array)
            h5file.create_dataset(
                "freq_array", data=freq_array[i : i + 1]
            )  # Single frequency for each subband
            h5file.create_dataset("visibility", data=visibilities[:, i, :])  # Store visibilities

    print(f"Generated {num_subbands} synthetic UVH5 files in {output_dir}.")
