## casa_cal: CASA 6.7 calibration helpers (no dsacalib)

Install environment:
```bash
conda activate casa6
# The casa6 environment is defined in env/environment.yml and includes all required dependencies
```

Catalogs:
- Use `catalogs.read_vla_calibrator_catalog(path)` and `catalogs.read_nvss_catalog()`.
- Generate declination table via `catalogs.update_caltable(vla_df, pt_dec)`.

Run calibration:
```bash
python -m dsa110_contimg.calibration.cli calibrate --ms <cal.ms> --field <cal_field> --refant <ant>
```
Apply to target:
```bash
python -m dsa110_contimg.calibration.cli apply --ms <target.ms> --field <field> --tables <ms_cal>_kcal <ms_cal>_bacal <ms_cal>_bpcal <ms_cal>_gacal <ms_cal>_gpcal
```

## Calibration Frequency Guidelines (Streaming Mode)

For streaming pipeline operations:

- **Bandpass Calibration**: Perform once every 24 hours. Bandpass solutions are relatively stable and can be reused for extended periods. Recalibrate when pointing declination changes significantly (>1-2 degrees) or when system conditions change.

- **Gain Calibration**: Perform every hour. Gain solutions vary with time and atmospheric conditions, requiring more frequent updates than bandpass. For time-variable conditions, consider using shorter solution intervals (e.g., `--gain-solint 60s` or `30s`).

These guidelines are documented in `utils/defaults.py` and should be followed when implementing streaming calibration workflows.

