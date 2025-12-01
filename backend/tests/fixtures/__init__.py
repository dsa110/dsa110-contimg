# Test fixtures for DSA-110 Continuum Imaging Pipeline
"""
Test fixtures and utilities for testing the pipeline.

Contains:
- writers.py: Testing-only MS writers (PyuvdataMonolithicWriter)
- uvh5_fixtures.py: Mock UVData objects and UVH5 data structures
- ms_fixtures.py: Mock MS tables and utilities
- database_fixtures.py: SQLite database fixtures for integration tests
"""

from .uvh5_fixtures import (
    MockUVData,
    create_mock_uvdata,
    create_mock_uvdata_multitime,
    mock_antenna_positions,
    create_mock_casacore_table,
    create_mock_ms_tables,
)

from .ms_fixtures import (
    MockMSTable,
    create_spectral_window_table,
    create_field_table,
    create_antenna_table,
    create_main_table,
    create_complete_mock_ms,
    mock_ms_table_access,
    create_temp_ms_directory,
)

from .database_fixtures import (
    SampleImage,
    SampleSource,
    SampleJob,
    SampleCalTable,
    sample_image_records,
    sample_source_records,
    sample_job_records,
    sample_cal_table_records,
    create_test_products_db,
    create_test_cal_registry_db,
    create_test_database_environment,
)

from .writers import (
    PyuvdataMonolithicWriter,
    PyuvdataWriter,
    get_test_writer,
)

__all__ = [
    # UVH5 fixtures
    "MockUVData",
    "create_mock_uvdata",
    "create_mock_uvdata_multitime",
    "mock_antenna_positions",
    "create_mock_casacore_table",
    "create_mock_ms_tables",
    # MS fixtures
    "MockMSTable",
    "create_spectral_window_table",
    "create_field_table",
    "create_antenna_table",
    "create_main_table",
    "create_complete_mock_ms",
    "mock_ms_table_access",
    "create_temp_ms_directory",
    # Database fixtures
    "SampleImage",
    "SampleSource",
    "SampleJob",
    "SampleCalTable",
    "sample_image_records",
    "sample_source_records",
    "sample_job_records",
    "sample_cal_table_records",
    "create_test_products_db",
    "create_test_cal_registry_db",
    "create_test_database_environment",
    # Writers
    "PyuvdataMonolithicWriter",
    "PyuvdataWriter",
    "get_test_writer",
]
