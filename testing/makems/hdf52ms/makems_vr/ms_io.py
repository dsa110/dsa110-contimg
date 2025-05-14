import glob
import os
import shutil
import traceback
from typing import List

import astropy.units as u
from astropy.time import Time
import scipy  # noqa
import numpy as np

from casatasks import virtualconcat
import casatools as cc
from casacore.tables import table


from uvh5_to_ms import uvh5_to_ms

def convert_calibrator_pass_to_ms(
        cal, date, files, msdir, hdf5dir, refmjd, antenna_list=None, logger=None, overwrite=True):
    """Converts hdf5 files near a calibrator pass to a CASA ms.

    Parameters
    ----------
    cal : dsacalib.utils.src instance
        The calibrator source.
    date : str
        The date (to day precision) of the calibrator pass. e.g. '2020-10-06'.
    files : list
        The hdf5 filenames corresponding to the calibrator pass. These should
        be date strings to second precision.
        e.g. ['2020-10-06T12:35:04', '2020-10-06T12:50:04']
        One ms will be written per filename in `files`. If the length of
        `files` is greater than 1, the mss created will be virtualconcated into
        a single ms.
    msdir : str
        The full path to the directory to place the measurement set in. The ms
        will be written to `msdir`/`date`\_`cal.name`.ms
    hdf5dir : str
        The full path to the directory containing subdirectories with correlated
        hdf5 data.
    antenna_list : list
        The names of the antennas to include in the measurement set. Names should
        be strings.  If not passed, all antennas in the hdf5 files are included.
    logger : dsautils.dsa_syslog.DsaSyslogger() instance
        Logger to write messages too. If None, messages are printed.
    """
    msname = f"{msdir}/{date}_{cal.name}"
    print(f"looking for files: {' '.join(files)}")
    if len(files) == 1:
        try:
            reftime = Time(files[0])
            hdf5files = []
            # TODO: improve this search so there are no edge cases
            for hdf5f in sorted(glob.glob(f"{hdf5dir}/{files[0][:-6]}*sb??.hdf5")):
                filetime = Time(hdf5f[:-5].split("/")[-1].split('_')[0])
                if abs(filetime - reftime) < 2.5 * u.min:
                    hdf5files += [hdf5f]
            assert len(hdf5files) < 17
            assert len(hdf5files) > 1
            print(f"found {len(hdf5files)} hdf5files for {files[0]}")
            uvh5_to_ms(
                hdf5files,
                msname,
                refmjd,
                ra=cal.ra,
                dec=cal.dec,
                flux=cal.flux,
                antenna_list=antenna_list,
                logger=logger
            )
            message = f"Wrote {msname}.ms"
            if logger is not None:
                logger.info(message)
            print(message)
        except (ValueError, IndexError) as exception:
            tbmsg = "".join(traceback.format_tb(exception.__traceback__))
            message = f'No data for {date} transit on {cal.name}. ' +\
                f'Error {type(exception).__name__}. Traceback: {tbmsg}'
            if logger is not None:
                logger.info(message)
            print(message)
    elif len(files) > 0:
        msnames = []
        for filename in files:
            print(filename)
            if overwrite or not os.path.exists(f'{msdir}/{filename}.ms'):
                try:
                    reftime = Time(filename)
                    hdf5files = []
                    for hdf5f in sorted(glob.glob(f"{hdf5dir}/{filename[:-6]}*sb??.hdf5")):
                        filetime = Time(hdf5f[:-5].split('/')[-1].split('_')[0])
                        if abs(filetime - reftime) < 2.5 * u.min:
                            hdf5files += [hdf5f]
                    print(f"found {len(hdf5files)} hdf5files for {filename}")
                    uvh5_to_ms(
                        hdf5files,
                        f"{msdir}/{filename}",
                        refmjd,
                        ra=cal.ra,
                        dec=cal.dec,
                        flux=cal.flux,
                        antenna_list=antenna_list,
                        logger=logger
                    )
                    msnames += [f"{msdir}/{filename}"]
                except (ValueError, IndexError) as exception:
                    message = (
                        f"No data for {filename}. Error {type(exception).__name__}. "
                        f"Traceback: {''.join(traceback.format_tb(exception.__traceback__))}"
                    )
                    if logger is not None:
                        logger.info(message)
                    print(message)
            else:
                print(f"Not doing {filename}")
        if os.path.exists(f"{msname}.ms"):
            for root, _dirs, walkfiles in os.walk(
                    f"{msname}.ms",
                    topdown=False
            ):
                for name in walkfiles:
                    os.unlink(os.path.join(root, name))
            shutil.rmtree(f"{msname}.ms")
        if len(msnames) > 1:
            virtualconcat(
                [f"{msn}.ms" for msn in msnames],
                f"{msname}.ms"
            )
            message = f"Wrote {msname}.ms"
            if logger is not None:
                logger.info(message)
            print(message)
        elif len(msnames) == 1:
            os.rename(f"{msnames[0]}.ms", f"{msname}.ms")
            message = f"Wrote {msname}.ms"
            if logger is not None:
                logger.info(message)
            print(message)
        else:
            message = f"No data for {date} transit on {cal.name}"
            if logger is not None:
                logger.info(message)
            print(message)
    else:
        message = f"No data for {date} transit on {cal.name}"
        if logger is not None:
            logger.info(message)
        print(message)