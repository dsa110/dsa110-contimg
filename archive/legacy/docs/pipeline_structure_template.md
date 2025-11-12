/data/dsa110-contimg/pipeline/                 # Pipeline code repository
│
├── README.md
├── requirements.txt                        # Python dependencies
├── environment.yml                         # Conda environment spec
├── setup.py                                # Installation script
│
├── bin/                                    # Executable scripts
│   ├── ese_pipeline.py                     # Main pipeline entry point
│   ├── run_calibration.py                  # Calibrator processing
│   ├── reprocess_observation.py            # Reprocess single obs
│   ├── generate_report.py                  # Create reports
│   ├── check_ese_candidates.py             # ESE detection analysis
│   └── archive_data.py                     # Data archival script
│
├── dsa110_pipeline/                        # Main Python package
│   ├── __init__.py
│   │
│   ├── core/                               # Core pipeline stages
│   │   ├── __init__.py
│   │   ├── ingestion.py                    # Stage 0: Data grouping
│   │   ├── conversion.py                   # Stage 1: HDF5 → MS
│   │   ├── phasing.py                      # Stage 2: Phase referencing
│   │   ├── flagging.py                     # Stage 3: RFI flagging
│   │   ├── calibration.py                  # Stage 4: Calibration
│   │   ├── imaging.py                      # Stage 5: Imaging
│   │   ├── quality.py                      # Stage 6: QA
│   │   ├── extraction.py                   # Stage 7: Source extraction
│   │   └── variability.py                  # Stage 9: Variability analysis
│   │
│   ├── database/                           # Database management
│   │   ├── __init__.py
│   │   ├── models.py                       # SQLAlchemy ORM models
│   │   ├── operations.py                   # CRUD operations
│   │   ├── queries.py                      # Common queries
│   │   └── schema.sql                      # Database schema
│   │
│   ├── utils/                              # Utility functions
│   │   ├── __init__.py
│   │   ├── coordinates.py                  # Coordinate transformations
│   │   ├── casa_tools.py                   # CASA wrappers
│   │   ├── wsclean_wrapper.py              # WSClean interface
│   │   ├── file_management.py              # File I/O helpers
│   │   ├── logging_config.py               # Logging setup
│   │   └── visualization.py                # Plotting functions
│   │
│   ├── ese/                                # ESE-specific analysis
│   │   ├── __init__.py
│   │   ├── detection.py                    # ESE detection algorithms
│   │   ├── scoring.py                      # ESE probability scoring
│   │   ├── lightcurves.py                  # Lightcurve analysis
│   │   ├── spectral.py                     # Spectral evolution
│   │   └── reporting.py                    # ESE candidate reports
│   │
│   ├── monitoring/                         # System monitoring
│   │   ├── __init__.py
│   │   ├── pipeline_status.py              # Pipeline health checks
│   │   ├── data_quality.py                 # Data quality metrics
│   │   ├── calibrator_monitor.py           # Calibrator stability
│   │   └── alerts.py                       # Email/Slack alerts
│   │
│   └── config/                             # Configuration management
│       ├── __init__.py
│       ├── defaults.py                     # Default parameters
│       ├── loader.py                       # Config file parser
│       └── validator.py                    # Config validation
│
├── tests/                                  # Unit and integration tests
│   ├── __init__.py
│   ├── test_conversion.py
│   ├── test_phasing.py
│   ├── test_imaging.py
│   ├── test_extraction.py
│   ├── test_database.py
│   ├── test_ese_detection.py
│   └── fixtures/                           # Test data
│       ├── test_observation.hdf5
│       └── expected_outputs/
│
├── notebooks/                              # Jupyter notebooks for analysis
│   ├── 01_explore_hdf5_format.ipynb
│   ├── 02_test_phasing.ipynb
│   ├── 03_imaging_comparison.ipynb
│   ├── 04_ese_candidate_review.ipynb
│   └── 05_performance_analysis.ipynb
│
├── scripts/                                # One-off utility scripts
│   ├── setup_database.py                   # Initialize database
│   ├── migrate_old_data.py                 # Migration helpers
│   ├── validate_installation.py            # Test CASA/WSClean setup
│   └── benchmark_imaging.py                # Performance tests
│
└── docs/                                   # Documentation
    ├── installation.md
    ├── pipeline_guide.md
    ├── database_schema.md
    ├── ese_detection_criteria.md
    ├── troubleshooting.md
    └── api/                                # API documentation
        └── index.html
