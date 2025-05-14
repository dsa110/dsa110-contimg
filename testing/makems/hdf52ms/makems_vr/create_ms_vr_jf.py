from ms_io import convert_calibrator_pass_to_ms
from calib_utils import generate_calibrator_source
import astropy.units as u
from astropy.coordinates import Angle
#import calib_config as configuration
#config = configuration.Configuration()

#msdir = '/operations/calibration/manual_cal/'
msdir = '/home/jfaber/msdir/'
#hdf5dir = config.hdf5dir
hdf5dir = '/data/incoming/'

calpass = {'date': "2025-02-07", 'name': "fld1", 'files': ["2025-02-07T13:37:00"], 'ra': None, 'dec': None}

#for i, calpass in enumerate(calpasses):
#    print(f'working on {calpass}')

cal = generate_calibrator_source(calpass['name'], ra=calpass['ra'], dec=calpass['dec'])
convert_calibrator_pass_to_ms(
        cal,
        calpass['date'],
        calpass['files'],
        msdir=msdir,
        hdf5dir=hdf5dir,
        refmjd=58849.0 #config.refmjd
    )
