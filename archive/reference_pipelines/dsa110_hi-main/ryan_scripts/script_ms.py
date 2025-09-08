from dsa110hi.pipeline_msmaker import convert_to_ms
import os
import numpy as np
import time

def ms_script(tmin=None, tmax=None,
        incoming_files='/data/incoming/', incoming_files_move='/data/incoming/processed/',
        output_files = '/data/pipeline/raw/', output_cal_files = '/data/pipeline/raw_cal/',
        loop=True
    ):
    """Highest level MS creation script - produces exact broadband MSes I expect    
    """

    for path in [incoming_files, incoming_files_move, output_files, output_cal_files]:
        if not os.path.exists(path):
            os.makedirs(path)

    # Set up infinite loop 
    while True:
        convert_to_ms(incoming_file_path=incoming_files,
                        tmin=tmin, tmax=tmax,
                        output_file_path=output_files,
                        cal_output_file_path=output_cal_files,
                        cal_catalog=None,
                        post_handle='move', post_file_path=incoming_files_move)
        
        if not loop:
            break
        if len(incoming_files) == 0:
            time.sleep(60)

def ms_script_spl(tmin=None, tmax=None,
        incoming_files='/data/incoming/', incoming_files_move='/data/incoming/processed/',
        output_files = '/data/pipeline/raw_spl/', output_cal_files = '/data/pipeline/raw_cal_spl/',
        loop=True
    ):
    """Highest level MS creation script - produces exact narrowband MSes I expect    
    """

    for path in [incoming_files, incoming_files_move, output_files, output_cal_files]:
        if not os.path.exists(path):
            os.makedirs(path)

    while True:
        convert_to_ms(incoming_file_path=incoming_files,
                        spw=['sb06_spl','sb07_spl','sb08_spl','sb09_spl',],
                        tmin=tmin, tmax=tmax,
                        output_file_path=output_files,
                        cal_output_file_path=output_cal_files,
                        cal_catalog=None,
                        post_handle='move', post_file_path=incoming_files_move)
        
        if not loop:
            break
        if len(incoming_files) == 0:
            time.sleep(60)

if __name__ == '__main__':
    pass
    # # Group 1 - all 3c309.1 - running
    # ms_script(tmin='2024-10-17T19:18', tmax='2024-10-18T04:57', loop=False) # 3c309.1 - calibrator
    # ms_script(tmin='2024-10-02T21:01', tmax='2024-10-03T16:22', loop=False) # First 3c309.1
    # ms_script(tmin='2024-10-10T13:01', tmax='2024-10-12T04:03', loop=False) # Earlier 3c309.1
    # # ms_script(tmin='2024-10-21T05:13', tmax=None, loop=False) # Later 3c309.1

    # # Group 2 - All M82, Virgo - done
    # ms_script(tmin='2024-10-17T12:41', tmax='2024-10-17T17:25', loop=False) # M82
    # ms_script(tmin='2024-10-02T14:15', tmax='2024-10-02T17:56', loop=False) # First M82
    # ms_script(tmin='2024-10-17T17:47', tmax='2024-10-17T18:53', loop=False) # Virgo

    # # Group 3 - 3c84 + M31 and M33... - done
    # ms_script(tmin='2024-10-18T05:15', tmax='2024-10-18T06:52', loop=False) # M31
    # ms_script(tmin='2024-10-18T07:10', tmax='2024-10-18T08:11', loop=False) # M33
    # ms_script(tmin='2024-10-18T08:43', tmax='2024-10-18T10:03', loop=False) # 3c84

    # Cleanup
    # ms_script(tmin='2024-01-01', tmax='2024-11-03', loop=False) # Anything else

    # Wait for new data
    # ms_script_spl(tmin='2024-11-02T01:12', loop=False)
    # ms_script(tmin='2024-11-02T11:45', tmax='2024-11-07T09:10', loop=False)

    # ms_script_spl(tmin='2024-11-08', tmax='2024-11-11', loop=False)
    # ms_script(tmin='2024-11-08', tmax='2024-11-11', loop=False)