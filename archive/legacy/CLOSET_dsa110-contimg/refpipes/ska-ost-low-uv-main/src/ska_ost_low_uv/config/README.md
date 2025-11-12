## Configuration files for UV Data creation

Config files in this directory are used to convert correlator output from AAVS2/3 + AA0.5
in its basic HDF5 format to a more complete UV file format (e.g. UVFITS) using `pyuvdata`.

Basic usage:
```python
from ska_ost_low_uv import hdf5_to_pyuvdata

# Use internal AAVS2 location
uv = hdf5_to_pyuvdata('input_data.hdf5', telescope_name='aavs2')

# Use external YAML file
uv = hdf5_to_pyuvdata('input_data.hdf5', yaml_config='my_config/uv_config.yaml')
```

## Source of truth

* AA0.5: https://gitlab.com/ska-telescope/ska-low-deployment/-/tree/main/tmdata/instrument/mccs-configuration
* AAVS2/AAVS3: https://confluence.skatelescope.org/display/SE/MCCS-1826%3A+Provide+AAVS3+data+for+telmodel+export
* AAVS3: https://confluence.skatelescope.org/display/SST/SKA1+LOW+AAVS3+Station+Centre
* AAVS3: https://gitlab.com/ska-telescope/ska-low-aavs3/-/blob/main/tmdata/instrument/mccs-configuration/aavs3.yaml

### File overview

To successfully create a file, you'll need

* A `uv_config.yaml` YAML file, which stores metadata needed by pyuvdata.
* A `antenna_locations.txt` file, which has ENU locations of antennas.
* A `baseline_order.txt` file, which maps antenna pairs to the HDF5 data shape.


### uv_config.yaml

```yaml
# UVData configuration for pyuvdata
# This should only include values that aren't derived from data shape
# https://pyuvdata.readthedocs.io/en/latest/uvdata.html#required
history: Created by DCP on Dec 23
instrument: AAVS2
telescope_name: AAVS2
antenna_locations_file: antenna_locations.txt
baseline_order_file: baseline_order.txt
telescope_ECEF_X: -2559453.29059553   # Geocentric (ECEF) position in meters, X
telescope_ECEF_Y: 5095371.73544116    # Geocentric (ECEF) position in meters, Y
telescope_ECEF_Z: -2849056.77357178   # Geocentric (ECEF) position in meters, Z
channel_width: 925926.0               # Hz TODO: CHECK THIS! 781250.0 spacing after oversample?
channel_spacing: 781250.0             # Hz - oversampled so spacing is smaller than width
polarization_type: stokes             # Polarization in file: stokes, linear, or circular
receptor_angle: 44.2                  # clockwise rotation angle in degrees away from N-E
vis_units: uncalib                    # Visibility units: uncalib, Jy, or K str
```

### antenna_locations.txt

This file is based on that in the `aavs-calibration` repository. It should have one header line, then
whitespace-delimited list of idx, antenna_name, E, N, ZU, topocentric positions in meters (ENU, East-North-Up frame)

```
idx name E N U
0 Ant061 6.437 4.975 -0.026
1 Ant063 -0.29 -0.256 0.016
2 Ant064 6.804 1.32 -0.001
3 Ant083 5.331 1.075 -0.013
...
```

### baseline_order.txt

This file has the mapping between antenna IDs (starting with 1 index), and baseline ID, for the HDF5 data. For AAVS, with 256 antennas, we would expect the number of unique baselines to be `NBL = 256 * 255 / 2 (cross-corrs) + 256 (auto-corrs)`, i.e. 32896 baselines.

Baseline ID is defined in pyuvdata as `BASELINE = 2048 * ant1 + ant2  + 2^16`. Yes, this is insane.

```
ant1 ant2 baseline
1 1 67585
1 2 67586
1 3 67587
...
```
