"""Update UV config from MCCS YAML.

* Retrieves the lasest ska-low-deployment git repository (where station YAML files are located)
* Generates ska_ost_low_uv's internally-used UV Configuration for a station
* Copies these over to ska_ost_low_uv/src/ska_ost_low_uv/config
"""

import os
from datetime import datetime
from operator import itemgetter

import pandas as pd
from astropy.coordinates import EarthLocation
from astropy.time import Time

from ska_ost_low_uv.utils import load_yaml

MCCS_CONFIG_PATH = 'ska-low-tmdata/tmdata/stations'


def local_station_location_from_platform_yaml(fn_yaml: str, station_name: str):
    """Local version to handle new YAML structure."""
    d = load_yaml(fn_yaml)
    # Try new structure first (without 'array'), fallback to old structure
    try:
        d_station = d['platform']['stations'][station_name]
    except KeyError:
        d_station = d['platform']['array']['stations'][station_name]

    # Generate pandas dataframe of antenna positions
    d_ant = d_station['antennas']

    location_getter = itemgetter('east', 'north', 'up')
    ant_enu = [
        [
            ant_name,  # Use the antenna name as the key (e.g., 'sb01-01')
            *location_getter(ant_data['location_offset']),
            ant_data.get('masked', False),
        ]
        for ant_name, ant_data in sorted(
            d_ant.items(),
            key=lambda x: (int(x[1]['tpm'].strip('tpm')), x[1]['tpm_y_channel'] // 2),
        )
    ]

    ant_enu = pd.DataFrame(ant_enu, columns=('name', 'E', 'N', 'U', 'flagged'))

    # Generate array central reference position
    # NOTE: Currently using WGS84, ignoring epoch
    loc = d_station['reference']
    earth_loc = EarthLocation.from_geodetic(loc['longitude'], loc['latitude'], loc['ellipsoidal_height'])

    # Add station rotation info
    ant_enu['rotation'] = d_station.get('rotation', 0.0)

    return earth_loc, ant_enu


def generate_uv_config(name: str):
    """Generate UV configs, create directories.

    Args:
        name (str): Name of station.
    """
    now = Time(datetime.now())

    # Read the YAML file and return an EarthLocation and pandas Dataframe of antenna positions
    eloc, antennas = local_station_location_from_platform_yaml(f'{MCCS_CONFIG_PATH}/{name}.yaml', name)

    # Create Directory
    os.mkdir(name)

    # Generate uv_config.yaml
    uvc = f"""# UVX configuration file
    history: Created with scripts/uv-config-from-mccs-yaml at {now.iso}
    instrument: {name}
    telescope_name: {name}
    telescope_ECEF_X: {eloc.x.value}
    telescope_ECEF_Y: {eloc.y.value}
    telescope_ECEF_Z: {eloc.z.value}
    channel_spacing: 781250.0           # Channel spacing in Hz
    channel_width: 925926.0             # 781250 Hz * 32/27 oversampling gives channel width
    antenna_locations_file: antenna_locations.txt
    baseline_order_file: baseline_order.txt
    polarization_type: linear_crossed  # stokes, circular, linear (XX, YY, XY, YX) or linear_crossed (XX, XY, YX, YY)
    receptor_angle: {antennas['rotation'].values[0]}            # clockwise rotation angle in degrees away from N-E
    conjugate_hdf5: true               # Apply complex conjugation to HDF5 data when loading
    transpose_hdf5: true               # Transpose cross-pol terms when loading HDF5 data
    vis_units: uncalib"""

    # Write to file
    with open(os.path.join(name, 'uv_config.yaml'), 'w') as fh:
        for line in uvc.split('\n'):
            fh.write(line.strip() + '\n')

    # Write antenna csv
    antennas.to_csv(
        os.path.join(name, 'antenna_locations.txt'),
        sep=' ',
        header=('name', 'E', 'N', 'U', 'flagged', 'rotation'),
        index_label='idx',
    )

    # Copy over baseline order
    os.system(f'cp config/baseline_order.txt {name}/')


if __name__ == '__main__':
    import glob

    os.system('bash update_ska_low_tmdata.sh')

    yaml_list = sorted(glob.glob(f'{MCCS_CONFIG_PATH}/*.yaml'))
    print(yaml_list)
    print(f'{MCCS_CONFIG_PATH}/*.yaml')
    for fn in yaml_list:
        name = os.path.splitext(os.path.basename(fn))[0]
        if name.startswith('s'):
            print(f'Generating {name}')
            generate_uv_config(name)
            os.system(f'mv {name} ../../src/ska_ost_low_uv/config')
