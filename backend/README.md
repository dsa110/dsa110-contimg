# DSA-110 Continuum Imaging Pipeline

## Overview

The DSA-110 Continuum Imaging Pipeline is designed to convert radio telescope
visibility data from UVH5 (HDF5) format into CASA Measurement Sets for
calibration and imaging. The pipeline processes data from the DSA-110 telescope,
which generates multiple subband files per observation.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Start the API server
python -m uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000

# Check health
curl http://localhost:8000/api/health

# View API docs
open http://localhost:8000/api/docs
```

## Project Structure

The project is organized into several modules, each serving a specific purpose:

- **src/dsa110_contimg**: Main package containing the core functionality.
  - **api**: REST API for accessing pipeline data and results.
  - **conversion**: Handles the conversion of UVH5 files to Measurement Sets.
  - **calibration**: Contains routines for calibrating the data.
  - **imaging**: Provides imaging functionalities.
  - **pipeline**: Implements the processing pipeline stages.
  - **database**: Manages database interactions and indexing.
  - **utils**: Contains utility functions and constants.
  - **docsearch**: Implements documentation search functionalities.
  - **simulation**: Generates synthetic data for testing.

## API Server

The pipeline includes a REST API for accessing measurement sets, images,
sources, and pipeline job status. See [API Reference](../docs/reference/api.md) 
for full documentation.

### Running the API

```bash
# Development mode
python -m uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000 --reload

# Production mode (systemd)
sudo systemctl start dsa110-api.service
```

### Security

The API includes IP-based access control. By default, only requests from
localhost and private networks (10.x, 172.16.x, 192.168.x) are allowed.

See [Security Guide](../docs/reference/security.md) for configuration details.

## Installation

To set up the project, ensure you have the required dependencies specified in
`pyproject.toml`. You can install them using:

```bash
pip install -e .
```

## Usage

To run the conversion process, use the command-line interface provided in the
`conversion/cli.py` module. For example:

```bash
python -m dsa110_contimg.conversion.cli --input-dir /path/to/input --output-dir /path/to/output
```

## Testing

Unit tests are located in the `tests/unit` directory, while integration tests
can be found in `tests/integration`. To run the tests, use:

```bash
pytest tests/
```

## Contributing

Contributions to the DSA-110 Continuum Imaging Pipeline are welcome. Please
follow the standard practices for contributing to open-source projects,
including forking the repository and submitting pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for more
details.
