"""Simple profile script for loading of uvdata."""

import os

from ska_ost_low_uv.io import hdf5_to_pyuvdata
from ska_ost_low_uv.utils import get_aa_config, get_test_data

# use eith er pyinstrument or cprofile
USE_PYINSTRUMENT = False
USE_CPROFILE = True


fn_h5 = get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5')
fn_conf = get_aa_config('aavs3')

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        args = sys.argv[1:]

        if args[0].lower() == 'cprofile':
            USE_CPROFILE = True
            USE_PYINSTRUMENT = False

    uv2 = hdf5_to_pyuvdata(fn_h5, yaml_config=fn_conf, max_int=30)

    try:
        if USE_PYINSTRUMENT:
            print('--- HDF5 to UVDATA ---\n')
            # Need to import here or cprofile freaks outs
            from pyinstrument import Profiler

            profiler = Profiler()
            profiler.start()
            uv2 = hdf5_to_pyuvdata(fn_h5, yaml_config=fn_conf, max_int=30)

            profiler.stop()
            profiler.print(show_all=False)
            profiler.write_html('tests/profiles/profile_read.html')

            profiler.reset()

            print('---UVDATA to MS ---\n')
            profiler.start()
            uv2.write_ms('tests/test.ms')
            profiler.stop()
            profiler.print(show_all=False)
            profiler.write_html('tests/profiles/profile_write.html')

        elif USE_CPROFILE:
            import cProfile
            import pstats

            print('--- HDF5 to UVDATA ---\n')
            with cProfile.Profile() as profile:
                uv2 = hdf5_to_pyuvdata(fn_h5, yaml_config=fn_conf, max_int=30)
                stats = pstats.Stats(profile).sort_stats('tottime')
                stats.print_stats(100)

            print('--- UVDATA to MS ---\n')
            with cProfile.Profile() as profile:
                uv2.write_miriad('tests/test.miriad')
                stats = pstats.Stats(profile).sort_stats('tottime')
                stats.print_stats(100)

    except:
        raise
    finally:
        if os.path.exists('tests/test.ms'):
            os.system('rm -rf tests/test.ms')
        if os.path.exists('tests/test.miriad'):
            os.system('rm -rf tests/test.miriad')
