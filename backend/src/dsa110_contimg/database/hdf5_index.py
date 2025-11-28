from typing import List, Tuple
import h5py
import os

def index_hdf5_files(directory: str) -> List[Tuple[str, List[str]]]:
    """
    Index HDF5 files in the specified directory.

    Args:
        directory (str): The path to the directory containing HDF5 files.

    Returns:
        List[Tuple[str, List[str]]]: A list of tuples where each tuple contains
        the filename and a list of datasets within that file.
    """
    indexed_files = []

    for filename in os.listdir(directory):
        if filename.endswith('.hdf5'):
            file_path = os.path.join(directory, filename)
            with h5py.File(file_path, 'r') as hdf_file:
                datasets = list(hdf_file.keys())
                indexed_files.append((filename, datasets))

    return indexed_files

def query_hdf5_file(file_path: str, dataset_name: str):
    """
    Query a specific dataset in an HDF5 file.

    Args:
        file_path (str): The path to the HDF5 file.
        dataset_name (str): The name of the dataset to query.

    Returns:
        The data from the specified dataset.
    """
    with h5py.File(file_path, 'r') as hdf_file:
        if dataset_name in hdf_file:
            return hdf_file[dataset_name][:]
        else:
            raise KeyError(f"Dataset '{dataset_name}' not found in '{file_path}'.")

def get_hdf5_metadata(file_path: str) -> dict:
    """
    Retrieve metadata from an HDF5 file.

    Args:
        file_path (str): The path to the HDF5 file.

    Returns:
        dict: A dictionary containing metadata information.
    """
    metadata = {}
    with h5py.File(file_path, 'r') as hdf_file:
        metadata['filename'] = os.path.basename(file_path)
        metadata['datasets'] = list(hdf_file.keys())
        metadata['attributes'] = {key: hdf_file.attrs[key] for key in hdf_file.attrs}

    return metadata