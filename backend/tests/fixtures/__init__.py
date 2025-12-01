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
    # Schema functions
    create_products_schema,
    create_cal_registry_schema,
    # Data classes
    SampleImage,
    SampleSource,
    SampleJob,
    SampleCalTable,
    SampleMSIndex,
    SamplePhotometry,
    # Sample data generators
    sample_image_records,
    sample_source_records,
    sample_job_records,
    sample_caltable_records,
    sample_ms_index_records,
    sample_photometry_records,
    # Population functions
    populate_products_db,
    populate_cal_registry_db,
    create_populated_products_db,
    create_populated_cal_registry_db,
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
    "create_products_schema",
    "create_cal_registry_schema",
    "SampleImage",
    "SampleSource",
    "SampleJob",
    "SampleCalTable",
    "SampleMSIndex",
    "SamplePhotometry",
    "sample_image_records",
    "sample_source_records",
    "sample_job_records",
    "sample_caltable_records",
    "sample_ms_index_records",
    "sample_photometry_records",
    "populate_products_db",
    "populate_cal_registry_db",
    "create_populated_products_db",
    "create_populated_cal_registry_db",
    # Writers
    "PyuvdataMonolithicWriter",
    "PyuvdataWriter",
    "get_test_writer",
]
