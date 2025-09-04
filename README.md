# DSA-110 Continuum Imaging Pipeline

## Core Pipeline Architecturegit 

dsa110-contimg/
├── pipeline/                    # Main pipeline modules
│   ├── main_driver.py          # Batch processing orchestrator
│   ├── config_parser.py        # Configuration management
│   ├── pipeline_utils.py       # Common utilities & logging
│   ├── ms_creation.py          # HDF5 → MS conversion (PyUVData)
│   ├── calibration.py          # CASA calibration tasks
│   ├── skymodel.py             # NVSS/TGSS catalog queries & CL creation
│   ├── imaging.py              # CASA tclean & mask creation
│   ├── mosaicking.py           # CASA linearmosaic
│   ├── photometry.py           # Aperture photometry & relative flux
│   ├── variability_analyzer.py # Light curve analysis
│   ├── hdf5_watcher_service.py # Service 1: HDF5 monitoring
│   ├── ms_processor_service.py # Service 2: MS processing
│   └── dsa110_utils.py         # Telescope constants & utilities
├── testing/                    # Development & testing code
│   ├── calib/                  # Calibration testing
│   ├── catalog/                # Catalog generation scripts
│   ├── makems/                 # MS creation variants
│   ├── sandbox/                # Experimental scripts
│   └── [various test modules]
├── config/
│   └── pipeline_config.yaml    # Main configuration
└── [data files & catalogs]