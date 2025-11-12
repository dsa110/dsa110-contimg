import os
import numpy as np
import time
from pipeline_msmaker import convert_to_ms

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
                        post_handle='none', post_file_path=incoming_files_move)
        
        if not loop:
            break
        if len(incoming_files) == 0:
            time.sleep(60)

ms_script(tmin='2025-05-29T05:50:00', tmax='2025-05-29T07:00:00', incoming_files='/data/incoming/',
     output_files = '/data/jfaber/dsa110-contimg/sandbox/2025-05-29/msfiles/base', output_cal_files = '/data/jfaber/dsa110-contimg/sandbox/2025-05-29/msfiles/base', loop=False)
