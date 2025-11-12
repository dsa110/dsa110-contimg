"""mccs_yaml: tools for reading MCCS YAML files."""

from operator import itemgetter

import numpy as np
import pandas as pd
from astropy.coordinates import EarthLocation

from ska_ost_low_uv.utils import load_yaml


def station_location_from_platform_yaml(fn_yaml: str, station_name: str) -> tuple[EarthLocation, pd.DataFrame]:
    """Load station location from AAVS3 MCCS yaml config.

    Args:
        fn_yaml (str): Filename path to yaml config
        station_name (str): Name of station, as it appears in YAML

    Returns:
        (earth_loc, ant_enu): astropy EarthLocation and antenna ENU locations in m
        ant_enu (pd.DataFrame): columns are 'name', 'E', 'N', 'U', 'flagged', 'rotation',
                                 where E,N,U are offsets in m, rotation is in degrees.
    """
    d = load_yaml(fn_yaml)
    d_station = d['platform']['array']['stations'][station_name]

    # Generate pandas dataframe of antenna positions
    d_ant = d_station['antennas']

    location_getter = itemgetter('east', 'north', 'up')
    ant_enu = [
        [
            f'{a["smartbox"]}-{a["smartbox_port"]}',
            *location_getter(a['location_offset']),
            a.get('masked', False),
        ]
        for a in sorted(
            d_ant.values(),
            key=lambda x: (int(x['tpm'].strip('tpm')), x['tpm_y_channel'] // 2),
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


def read_flags_from_platform_yaml(fn_yaml: str) -> np.array:
    """Read antenna flags from AAVS MCCS yaml config.

    Args:
        fn_yaml (str): Filename path to yaml config

    Returns:
        flagged (np.array): Array of flagged antennas (boolean True means bad antenna)
    """
    earth_loc, ant_enu = station_location_from_platform_yaml(fn_yaml)
    return ant_enu['flagged'].values
