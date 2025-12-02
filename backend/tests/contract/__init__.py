"""
Contract Tests for DSA-110 Continuum Imaging Pipeline.

Contract tests verify that the pipeline produces valid, standards-compliant
outputs given valid inputs. Unlike mock-heavy unit tests, contract tests:

1. Use REAL data structures (synthetic but realistic)
2. Verify OBSERVABLE outputs (file contents, database records)
3. Check EXTERNAL compliance (FITS/MS standards, SQL schemas)
4. Run ACTUAL code paths (no mocking of core functionality)

Key fixtures provided by this module:
- synthetic_uvh5: Generates realistic UVH5 subband files
- synthetic_ms: Creates valid Measurement Sets
- synthetic_fits: Creates valid FITS images
- test_pipeline_db: In-memory database with full schema

Test categories:
- test_conversion_contracts.py: UVH5 → MS conversion produces valid MS
- test_imaging_contracts.py: MS → FITS imaging produces valid images
- test_calibration_contracts.py: Calibration tables are valid
- test_database_contracts.py: Database operations maintain schema integrity
- test_api_contracts.py: API responses match expected schemas
"""
