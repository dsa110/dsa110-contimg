# Testing

Documentation for testing strategy and current status.

## Current Status

See the [Current Status](CURRENT_STATUS.md) document for the current state of
testing.

## Running Tests

```bash
conda activate casa6
cd /data/dsa110-contimg/backend

# Run all tests
python -m pytest tests/ -v

# Run unit tests only
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run with coverage
python -m pytest tests/ --cov=dsa110_contimg --cov-report=html
```

## Archived Documentation

Historical testing reports and detailed plans have been archived to
`docs/archive/testing-reports/`.
