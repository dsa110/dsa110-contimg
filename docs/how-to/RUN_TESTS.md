# Running Tests in the casa6 Environment

## Problem

If you see errors like:

```
ModuleNotFoundError: No module named 'dsa110_contimg'
```

or

```
Python 2.7.17
```

This means pytest is using the system Python instead of the casa6 conda
environment.

## Solution

### Option 1: Activate conda environment first (Recommended)

```bash
# Activate the casa6 environment
source /opt/miniforge/bin/activate casa6

# Verify you're using the right Python
which python
# Should show: /opt/miniforge/envs/casa6/bin/python

python --version
# Should show: Python 3.11.x (not 2.7)

# Now run tests
pytest tests/unit/api/test_data_access.py -v
```

### Option 2: Use python -m pytest (Always works)

This ensures pytest uses the Python from your current environment:

```bash
# Even if conda isn't activated, this will use the correct Python
python -m pytest tests/unit/api/test_data_access.py -v
```

### Option 3: Use full path to casa6 pytest

```bash
/opt/miniforge/envs/casa6/bin/pytest tests/unit/api/test_data_access.py -v
```

## Verify Environment

Check which Python/pytest you're using:

```bash
which python
which pytest
python --version
pytest --version
```

**Correct output:**

```
/opt/miniforge/envs/casa6/bin/python
/opt/miniforge/envs/casa6/bin/pytest
Python 3.11.13
pytest 8.4.2
```

**Wrong output (system Python):**

```
/usr/bin/python
/usr/bin/pytest
Python 2.7.17
pytest 3.3.2
```

## Quick Fix Script

Create an alias in your `~/.bashrc`:

```bash
# Add to ~/.bashrc
alias casa6='source /opt/miniforge/bin/activate casa6'
alias test-api='cd /data/dsa110-contimg && python -m pytest tests/unit/api/ -v'
```

Then:

```bash
source ~/.bashrc
casa6
test-api
```

## Running Specific Tests

```bash
# Activate environment first
source /opt/miniforge/bin/activate casa6

# Run specific test class
python -m pytest tests/unit/api/test_data_access.py::TestFetchPointingHistory -v

# Run specific test method
python -m pytest tests/unit/api/test_data_access.py::TestFetchPointingHistory::test_fetch_pointing_history_success -v

# Run with coverage
python -m pytest tests/unit/api/test_data_access.py --cov=dsa110_contimg.api.data_access -v
```
