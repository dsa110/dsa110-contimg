# DSA-110 Continuum Imaging Pipeline

## Overview

The DSA-110 Continuum Imaging Pipeline is designed to convert radio telescope visibility data from UVH5 (HDF5) format into CASA Measurement Sets for calibration and imaging. The pipeline processes data from the DSA-110 telescope, which generates multiple subband files per observation.

## Project Structure

The project is organized into several modules, each serving a specific purpose:

- **src/dsa110_contimg**: Main package containing the core functionality.
  - **conversion**: Handles the conversion of UVH5 files to Measurement Sets.
  - **calibration**: Contains routines for calibrating the data.
  - **imaging**: Provides imaging functionalities.
  - **pipeline**: Implements the processing pipeline stages.
  - **api**: Exposes an API for external interactions.
  - **database**: Manages database interactions and indexing.
  - **utils**: Contains utility functions and constants.
  - **docsearch**: Implements documentation search functionalities.
  - **simulation**: Generates synthetic data for testing.

## Installation

To set up the project, ensure you have the required dependencies specified in `pyproject.toml`. You can install them using:

```bash
pip install -e .
```

## Usage

To run the conversion process, use the command-line interface provided in the `conversion/cli.py` module. For example:

```bash
python -m dsa110_contimg.conversion.cli --input-dir /path/to/input --output-dir /path/to/output
```

## Testing

Unit tests are located in the `tests/unit` directory, while integration tests can be found in `tests/integration`. To run the tests, use:

```bash
pytest tests/
```

## Contributing

Contributions to the DSA-110 Continuum Imaging Pipeline are welcome. Please follow the standard practices for contributing to open-source projects, including forking the repository and submitting pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.