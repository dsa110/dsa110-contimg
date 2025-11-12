[![readthedocs](https://app.readthedocs.org/projects/ska-ost-low-uv/badge/)](https://ska-ost-low-uv.readthedocs.io/en/latest/index.html)
[![codecov](https://codecov.io/gitlab/ska-telescope:ost/ska-ost-low-uv/graph/badge.svg?token=JSKAZ5PQ5Q)](https://codecov.io/gitlab/ska-telescope:ost/ska-ost-low-uv)
[![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)

## ska-ost-low-uv

Utilities for handling UV data products for low-frequency aperture array telescopes.

`ska-ost-low-uv` provides a `UVX` data format and Python class for storing and handling interferometric data.

These codes use the `UVData` class from [pyuvdata](https://pyuvdata.readthedocs.io) to convert the raw HDF5 correlator output files to science-ready data formats like UVFITS, MIRIAD, and CASA MeasurementSets.

Additionally, data can be loaded into the `UVX` data model, which is based on [xarray](https://docs.xarray.dev/en/stable/).

![aavsuv-overview](https://github.com/ska-sci-ops/aa_uv/blob/main/docs/images/uv_flow.png?raw=true)

Some simple calibration and imaging utilities are provided in the `postx` submodule. This is an optional extra,
that requires several additional packages.

## Documentation

The documentation for this project can be browsed on readthedocs:

* [ska-ost-low-uv documentation](https://ska-ost-low-uv.readthedocs.io/en/latest/)

The sphinx source can be found in the `docs/src` folder, and some example Jupyter notebooks in the [`docs/src/nb`](https://gitlab.com/ska-telescope/ost/ska-ost-low-uv/-/tree/main/docs/src/nb?ref_type=heads) folder.


## File conversion: command-line script

Once installed, a command-line utility, `aa_uv`, will be available:

```
> aa_uv -h

usage: aa_uv [-h] -o OUTPUT_FORMAT [-c ARRAY_CONFIG] [-n TELESCOPE_NAME] [-s] [-j] [-b] [-B] [-x FILE_EXT] [-i CONTEXT_YAML] [-w NUM_WORKERS] [-v] [-p PARALLEL_BACKEND] [-N N_INT_PER_FILE] [-z] infile outfile

AAVS UV file conversion utility

positional arguments:
  infile                Input filename
  outfile               Output filename

options:
  -h, --help            show this help message and exit
  -o OUTPUT_FORMAT, --output_format OUTPUT_FORMAT
                        Output file format (uvx, uvfits, miriad, ms, uvh5). Can be comma separated for multiple formats.
  -c ARRAY_CONFIG, --array_config ARRAY_CONFIG
                        Array configuration YAML file. If supplied, will override ska_ost_low_uv internal array configs.
  -n TELESCOPE_NAME, --telescope_name TELESCOPE_NAME
                        Telescope name, e.g. 'aavs3'. If supplied, will attempt to use ska_ost_low_uv internal array config.
  -s, --phase-to-sun    Re-phase to point toward Sun (the sun must be visible!). If flag not set, data will be phased toward zenith.
  -b, --batch           Batch mode. Input and output are treated as directories, and all subfiles are converted.
  -B, --megabatch       MEGA batch mode. Runs on subdirectories too, e.g. eb-aavs3/2023_12_12/*.hdf5.
  -x FILE_EXT, --file_ext FILE_EXT
                        File extension to search for in batch mode
  -i CONTEXT_YAML, --context_yaml CONTEXT_YAML
                        Path to observation context YAML (for UVX format)
  -w NUM_WORKERS, --num-workers NUM_WORKERS
                        Number of parallel processors (i.e. number of files to read in parallel).
  -v, --verbose         Run with verbose output.
  -p PARALLEL_BACKEND, --parallel_backend PARALLEL_BACKEND
                        Joblib backend to use: 'loky' (default) or 'dask'
  -N N_INT_PER_FILE, --n_int_per_file N_INT_PER_FILE
                        Set number of integrations to write per file. Only valid for MS, Miriad, UVFITS, uvh5 output.
  -z, --zipit           Zip up a MS or Miriad file after conversion (flag ignored for other files)
```

The converter needs a [yaml configuration file](https://github.com/ska-sci-ops/aa_uv/tree/main/example-config), which can be supplied with the `-c` argument, or internal defaults can be used instead via the `-n` argument (e.g. `-n s86`, `-n s92`, `-n aavs3`, `-n eda2` ):

```
# Convert AAVS3 HDF5 data into a MeasurementSet
> aa_uv -n aavs3 -o ms correlator_data.hdf5 my_new_measurement_set.ms
```

### File conversion: Python API

```python

from ska_ost_low_uv.io import hdf5_to_pyuvdata

def hdf5_to_pyuvdata(filename: str, yaml_config: str) -> pyuvdata.UVData:
    """ Convert AAVS2/3 HDF5 correlator output to UVData object

    Args:
        filename (str): Name of file to open
        yaml_config (str): YAML configuration file with basic telescope info.
                           See README for more information
    Returns:
        uv (pyuvdata.UVData): A UVData object that can be used to create
                              UVFITS/MIRIAD/UVH5/etc files
    """


```

### Reading data from acacia / S3

To use the `AcaciaStorage` class, h5py/HDF5 needs to be compiled with ROS3 support (h5py packages on PyPI do not include ROS3 driver support, but mamba does).


## Installation

Download this repository, then install via `pip install .`. To install optional extras:

```
pip install .[postx]  # Post-correlation imaging and QA tools
pip install .[casa]   # Installs python-casacore for MS support
```

### Fresh mamba install

To install from scratch using `mamba` (miniforge), download this repository, cd into the directory, and run

```
mamba env create -f environment.yml
mamba activate low-uv
```

You can then use `mamba activate low-uv` to start up the environment, and `mamba deactivate` to leave it.

Then run `uv pip install .` and any extras (e.g. `uv pip install .[postx]`).

### Pip / manual

If you have an existing Python 3 installation, you can install with pip via:

```
pip install git+https://github.com/ska-sci-ops/aa_uv/edit/main/README.md
```

Alternatively, download this repository and install using `pip install .`. A list of required packages can be found in the [pyproject.toml](https://gitlab.com/ska-telescope/ost/ska-ost-low-uv/-/blob/main/pyproject.toml?ref_type=heads).

### Astronomy packages

[![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)

`ska_ost_low_uv` is built upon the following astronomy packages:
* [astropy](http://www.astropy.org/) for coordinate calculations.
* [pyuvdata](https://github.com/RadioAstronomySoftwareGroup/pyuvdata) for interferometric data format conversion.
* [pygdsm](https://github.com/telegraphic/pygdsm) for diffuse sky model generation.# ska-ost-low-uv


## Tests

Run tests via `pytest`.

To regenerate matplotlib reference images, run

```
pytest --mpl-generate-path=tests/baseline
```

and to check images run

```
pytest --mpl --mpl-baseline-path=tests/baseline
```

(Note these option flags are already set in `pyproject.toml`)
