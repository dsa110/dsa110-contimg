"""utils: Utilities used in ska_ost_low_uv package."""

import importlib
import inspect
import os
import shutil
import sys
import types
import typing

import yaml
from loguru import logger
from tqdm import tqdm

import ska_ost_low_uv


def reset_logger(use_tqdm: bool = False, disable: bool = False, level: str = 'INFO') -> logger:
    """Reset loguru logger and setup output format.

    Helps loguru (logger), tqdm (progress bar) and joblib/dask (parallel) work together.

    Args:
        use_tqdm (bool): Set to true if using tqdm progress bar
        disable (bool): Disable the logger (set to ERROR only output)
        level (str): One of DEBUG, INFO, WARNING, ERROR, CRITICAL

    Notes:
        If using the `@task` decorator, it's a good idea to add reset_logger
        to your function to keep the task quiet so progress bar shows, eg::

            @task
            def convert_file_task(args, ...):
            if not verbose:
                reset_logger(use_tqdm=True, disable=True)

    Returns:
        logger (logger): loguru logger object
    """
    logger.remove()
    logger_fmt = '<g>{time:HH:mm:ss.S}</g> | <w><b>{level}</b></w> | {message}'
    if not disable:
        if not use_tqdm:
            logger.add(sys.stdout, format=logger_fmt, level=level, colorize=True)
        else:
            logger.add(
                lambda msg: tqdm.write(msg, end=''),
                format=logger_fmt,
                level=level,
                colorize=True,
            )
    else:
        logger.add(
            lambda msg: tqdm.write(msg, end=''),
            format=logger_fmt,
            level='ERROR',
            colorize=True,
        )
    return logger


def load_yaml(filename: str) -> dict:
    """Read YAML file into a Python dict."""
    md = yaml.load(open(filename, 'r'), yaml.Loader)
    return md


def load_config(telescope_name: str) -> dict:
    """Load internal array configuration by telescope name."""
    yaml_path = get_aa_config(telescope_name)
    md = load_yaml(yaml_path)

    # Update path to antenna location files to use absolute path
    config_abspath = os.path.dirname(os.path.abspath(yaml_path))
    try:
        md['antenna_locations_file'] = os.path.join(config_abspath, md['antenna_locations_file'])
        md['baseline_order_file'] = os.path.join(config_abspath, md['baseline_order_file'])
        md['station_config_file'] = os.path.abspath(yaml_path)
    except KeyError as e:
        logger.warning(f'Key not found in config file: {e}')
        logger.warning(md)
        raise RuntimeError(f'Key not found in config file: {e}') from e

    return md


def get_resource_path(relative_path: str) -> str:
    """Get the path to an internal package resource (e.g. data file).

    Args:
        relative_path (str): Relative path to data file, e.g. 'config/aavs3/uv_config.yaml'

    Returns:
        abs_path (str): Absolute path to the data file
    """
    path_root = os.path.abspath(ska_ost_low_uv.__path__[0])
    abs_path = os.path.join(path_root, relative_path)

    if not os.path.exists(abs_path):
        logger.warning(f'File not found: {abs_path}')

    return os.path.abspath(abs_path)


def get_aa_config(name: str) -> str:
    """Get path to internal array configuration by telescope name.

    Args:
        name (str): Name of telescope to load array config, e.g. 'aavs2'

    Returns:
        abs_path (str): Absolute path to config file.
    """
    relative_path = f'config/{name}/uv_config.yaml'
    if name is None:
        raise RuntimeError('A path / telescope_name must be set.')
    return get_resource_path(relative_path)


def get_software_versions() -> dict:
    """Return version of main software packages."""
    from astropy import __version__ as astropy_version  # noqa: I001
    from erfa import __version__ as erfa_version
    from h5py import __version__ as h5py_version
    from numpy import __version__ as numpy_version
    from pandas import __version__ as pandas_version
    from pyuvdata import __version__ as pyuvdata_version
    from ska_ost_low_uv import __version__ as ska_ost_low_uv_version
    from xarray import __version__ as xarray_version

    # fmt: off
    software = {
        'ska_ost_low_uv': ska_ost_low_uv_version,
        'astropy':        astropy_version,
        'numpy':          numpy_version,
        'pyuvdata':       pyuvdata_version,
        'xarray':         xarray_version,
        'pandas':         pandas_version,
        'h5py':           h5py_version,
        'erfa':           erfa_version,
    }
    # fmt: on

    return software


def zipit(dirname: str, rm_dir: bool = False):
    """Zip up a directory.

    Args:
        dirname (str): Name of directory to zip
        rm_dir (bool): Delete directory after zipping (default False)
    """
    shutil.make_archive(dirname, format='zip', root_dir='.', base_dir=dirname)
    if rm_dir:
        shutil.rmtree(dirname)


def import_optional_dependency(
    name: str,
    errors: typing.Literal['raise', 'warn', 'ignore'] = 'raise',
) -> types.ModuleType | None:
    """Import an optional dependency by name.

    Notes:
        Adapted from pandas/pandas/compat/_optional.py (BSD-3)

    Args:
        name (str): Name of dependency to import
        errors (typing.Literal): What to do if not installed; one of raise, warn, or ignore
    """
    msg = f"Missing optional dependency '{name}'. Use pip or conda to install {name}."
    try:
        module = importlib.import_module(name)
    except ImportError as err:
        if errors == 'raise':
            raise ImportError(msg) from err
        elif errors == 'warn':
            logger.warning(msg)
        return None
    return module


def get_test_data(filename: str) -> str:
    """Returns the absolute path to test data.

    Notes:
        test data resides in /tests/test-data

    Args:
        filename (str): Filename of test data to find path of.

    Returns:
        fpath (str): Absolute path to test data.
    """
    fpath = get_resource_path(f'./tests/test-data/{filename}')
    return fpath


def inspect_class_method(class_to_inspect, method_name: str) -> str:
    """Return the initialization signature (args and kwargs) for a class.

    Args:
        class_to_inspect: Class to inspect.
        method_name: Name of method to inspect (e.g. '__init__')

    Returns:
        signature (str): String corresponding to method signature.
    """
    class_method = getattr(class_to_inspect, method_name)
    signature = inspect.signature(class_method)

    ret_str = 'Init signature:\n'
    for param_name, param in signature.parameters.items():
        if param_name != 'self':
            ret_str += f'   {param}\n'
    ret_str += '\n'
    ret_str += class_method.__doc__

    return ret_str
