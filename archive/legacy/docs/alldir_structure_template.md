/data/dsa110/
│
├── raw/                                    # Raw HDF5 files from correlator
│   ├── 2025-09-05/
│   │   ├── 2025-09-05T03:23:14_sb00.hdf5
│   │   ├── 2025-09-05T03:23:14_sb01.hdf5
│   │   ├── ...
│   │   ├── 2025-09-05T03:23:14_sb15.hdf5
│   │   ├── 2025-09-05T03:28:19_sb00.hdf5
│   │   └── ...
│   ├── 2025-09-06/
│   └── 2025-09-07/
│
├── processed/                              # Pipeline outputs
│   ├── ms/                                 # Measurement sets (temporary)
│   │   ├── 2025-09-05T03:23:14_phased.ms/
│   │   ├── 2025-09-05T03:28:19_phased.ms/
│   │   └── ...
│   │
│   ├── images/                             # FITS images (permanent archive)
│   │   ├── 2025-09-05/
│   │   │   ├── 2025-09-05T03:23:14-MFS-image.fits
│   │   │   ├── 2025-09-05T03:23:14-MFS-alpha.fits
│   │   │   ├── 2025-09-05T03:23:14-MFS-residual.fits
│   │   │   ├── 2025-09-05T03:23:14_sources.csv
│   │   │   └── 2025-09-05T03:23:14_metadata.json
│   │   ├── 2025-09-06/
│   │   └── 2025-09-07/
│   │
│   └── catalogs/                           # Source catalogs by field
│       ├── ESE_00h/
│       │   ├── master_catalog.csv
│       │   ├── lightcurves/
│       │   │   ├── source_00001.csv
│       │   │   ├── source_00002.csv
│       │   │   └── ...
│       │   └── plots/
│       │       ├── source_00001_lightcurve.png
│       │       └── ...
│       ├── ESE_02h/
│       └── ...
│
├── calibration/                            # Calibration products
│   ├── daily/
│   │   ├── 2025-09-05_3C286.gcal/
│   │   ├── 2025-09-05_bandpass.bcal/
│   │   └── 2025-09-05_fluxscale.txt
│   ├── templates/
│   │   ├── standard_phase.gcal/           # Long-term average
│   │   └── standard_bandpass.bcal/
│   └── monitoring/
│       └── calibrator_stability.csv        # Track calibrator flux over time
│
├── database/                               # SQLite database (or config for remote DB)
│   ├── ese_monitoring.db                   # Main database
│   ├── backups/
│   │   ├── ese_monitoring_2025-09-05.db.gz
│   │   ├── ese_monitoring_2025-09-06.db.gz
│   │   └── ...
│   └── schema/
│       ├── create_tables.sql
│       └── migration_scripts/
│
├── logs/                                   # Pipeline execution logs
│   ├── 2025-09-05/
│   │   ├── 2025-09-05T03:23:14_conversion.log
│   │   ├── 2025-09-05T03:23:14_phasing.log
│   │   ├── 2025-09-05T03:23:14_imaging.log
│   │   ├── 2025-09-05T03:23:14_extraction.log
│   │   └── pipeline_summary_2025-09-05.log
│   └── errors/
│       └── failed_observations.log
│
├── reports/                                # Automated reports and alerts
│   ├── daily/
│   │   ├── 2025-09-05_summary.html
│   │   ├── 2025-09-05_summary.pdf
│   │   └── ...
│   ├── weekly/
│   │   └── 2025-W36_summary.pdf
│   ├── ese_candidates/
│   │   ├── candidate_001_report.pdf
│   │   └── ...
│   └── qa/                                 # Quality assurance reports
│       └── image_quality_2025-09.csv
│
├── archive/                                # Long-term archive (compressed)
│   ├── hdf5/                               # Original HDF5 (optional)
│   │   ├── 2025-09.tar.gz
│   │   └── ...
│   ├── ms/                                 # Phased MS (optional)
│   │   ├── 2025-09-week1.tar.gz
│   │   └── ...
│   └── images/                             # Compressed images (if needed)
│       └── 2025-09.tar.gz
│
└── config/                                 # Configuration files
    ├── pipeline_config.yaml                # Main pipeline parameters
    ├── fields_config.yaml                  # ESE monitoring field definitions
    ├── calibration_config.yaml             # Calibration strategy
    ├── imaging_config.yaml                 # Imaging parameters
    ├── ese_detection_config.yaml           # ESE criteria
    └── database_config.yaml                # Database connection info
