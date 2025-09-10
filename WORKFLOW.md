# 1. Ingest and Stage
- Scan /data/incoming/ for complete 16-subband HDF5 sets per timestamp.
- Stage selected sets into data/hdf5_staging/<timestamp>/ for processing.
- Validate completeness, metadata, and basic integrity.
# 2. Calibrator/context resolution (pre-flight)
- Read declination (and optionally RA) from HDF5 Header.
- If RA not present, derive RA from time_array (JD) + telescope longitude (apparent LST).
- Query calibrators/sources via NVSS/FIRST/TGSS/VLASS; prefer on-axis or near-axis sources.
# 3. Measurement Set (MS) creation
- Combine all 16 sub-band HDF5 into a single UVData.
- Use survey-grade antenna positions (CSV ITRF) for active antennas; set telescope location.
- Override phase center in UVData from HDF5; ensure FIELD table is consistent.
- Recalculate UVW from ITRF positions (maximum precision path).
- Write MS to data/ms/<timestamp>.ms; validate with PyUVData/CASA summary.
# 4. Calibration
- Apply bandpass and gain tables (e.g., test_calibration_bandpass.bcal, test_calibration_final_gain.gcal) or generate/update them if in a calibration block.
- Confirm cal table integrity before use.
# 5. Imaging
- For science targets, set tclean phase center to the chosen on-axis source (J2000 RA/Dec) to prioritize it in the main lobe.
- Produce a dirty image first (niter=0) for a quick look; then clean if warranted.
- Export to FITS and generate quick-look plots.
# 6. Quality Assurance
- Check MS metrics: antennas, baselines, times, channelization, file size.
- Imaging QA: noise level, beam, dynamic range, peak location vs. expected source.
- Log CASA and pipeline outputs; surface warnings/errors.
# 7. Iteration and Products
- If QA fails, adjust (phase center, cal tables, masking, weighting, cell size) and re-image.
- Archive MS, calibration tables, and images with provenance (timestamp, configs, catalogs used).
# 8. Operations preferences
- Prefer on-axis sources over brighter off-axis sources.
- Use cache-first + online catalog queries; normalize fluxes to 1.4 GHz (α≈−0.7) for ranking.
- Derive pointing RA from HDF5 time (JD) + site LST when not present; declination from HDF5 header, converting radians→degrees when necessary.
