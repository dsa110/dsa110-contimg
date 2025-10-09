## casa_cal: CASA 6.7 calibration helpers (no dsacalib)

Install environment:
```bash
conda create -n casa6-67 python=3.10 -y
conda activate casa6-67
conda install -c conda-forge casatools=6.7.0 casatasks=6.7.0 casadata pyuvdata=3.2.4 astropy=6 pandas=2.2 numpy scipy matplotlib pyyaml -y
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

