/var/www/contimg_dashboard/                  # Web dashboard
│
├── index.html                              # Main landing page
├── css/
│   └── style.css
├── js/
│   ├── dashboard.js
│   └── charts.js
│
├── pages/
│   ├── observations.html                   # Observation log
│   ├── sources.html                        # Source catalog browser
│   ├── lightcurves.html                    # Lightcurve viewer
│   ├── ese_candidates.html                 # ESE candidate list
│   ├── calibration.html                    # Calibration monitoring
│   └── pipeline_status.html                # Pipeline health
│
└── api/                                    # REST API endpoints
    ├── observations.php                    # Get observations
    ├── sources.php                         # Get source data
    ├── lightcurve.php                      # Get lightcurve for source
    └── ese_candidates.php                  # Get ESE candidates
