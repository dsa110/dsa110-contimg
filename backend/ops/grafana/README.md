# Grafana Dashboards for DSA-110 Pipeline

This directory contains Grafana dashboard JSON files for monitoring the DSA-110
Continuum Imaging Pipeline.

## Available Dashboards

### dsa110-pipeline-dashboard.json

Main pipeline monitoring dashboard showing:

- **Pipeline Overview**: Total MS files, images, sources, photometry records,
  pending/running jobs
- **Processing Throughput**: MS processing rate, image creation rate,
  calibration operations, source detection rate
- **Data Quality**: Image noise distribution, dynamic range, calibration SNR
- **Pipeline Stages**: MS by pipeline stage, images by type, photometry by
  source type

## Installation

### Prerequisites

1. Grafana 9.0+ installed and running
2. Prometheus data source configured with DSA-110 metrics

### Import Dashboard

1. Open Grafana web UI
2. Go to **Dashboards** → **Import**
3. Click **Upload JSON file** or paste the JSON content
4. Select your Prometheus data source
5. Click **Import**

### Configure Data Source

The dashboard uses a templated datasource variable `${datasource}`. Make sure
you have a Prometheus data source configured that scrapes the DSA-110 API
metrics endpoint:

```yaml
# prometheus.yml scrape config
scrape_configs:
  - job_name: "dsa110-api"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/metrics"
```

## Metrics Reference

The dashboard queries these custom DSA-110 metrics:

### Counters

- `dsa110_ms_processed_total{status, stage}` - Total MS files processed
- `dsa110_images_created_total{type}` - Total images created
- `dsa110_photometry_records_total{source_type}` - Total photometry records
- `dsa110_calibrations_total{status, type}` - Total calibration operations
- `dsa110_sources_detected_total{classification}` - Total sources detected

### Gauges

- `dsa110_ms_count{stage}` - Current MS count by pipeline stage
- `dsa110_images_count{type}` - Current image count by type
- `dsa110_sources_count` - Total unique sources
- `dsa110_photometry_count` - Total photometry records
- `dsa110_pending_jobs` - Pending pipeline jobs
- `dsa110_running_jobs` - Currently running jobs

### Histograms

- `dsa110_image_noise_jy` - Image RMS noise in Jy
- `dsa110_image_dynamic_range` - Image dynamic range
- `dsa110_calibration_snr` - Calibration signal-to-noise ratio

## Customization

Feel free to modify the dashboard:

- Add alerts for job queue backlogs
- Add panels for specific calibrator monitoring
- Adjust histogram bucket ranges for your typical data quality
- Add annotations for pipeline deployments or configuration changes
