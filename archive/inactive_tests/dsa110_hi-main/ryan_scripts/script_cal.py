import os
import shutil
import time
from fnmatch import fnmatch

from dsa110hi.utils_calib import flag, solve_delay, solve_bpass, apply_cal
from casatasks import split

def cal_script(incoming_cal_file, output_cal_file, 
               bad_ants='', uvrange='<250m',
               refant_delay='pad108', refant_bpass='pad8',
               average_channels=1,
               applycal=False):
    
    if not os.path.exists(output_cal_file):
        os.makedirs(output_cal_file)

    msname = os.path.join(output_cal_file,'pass.ms')
    calmsname = os.path.join(output_cal_file,'calibrated_pass.ms')
    delayname = 'DELAY'
    bpassname = 'BPASS'

    # Make this work for lists of input files (w/ concat)
    split(vis=incoming_cal_file,outputvis=msname,datacolumn='all',width=average_channels)
    # shutil.copytree(incoming_cal_file, msname)
    flag(incoming_file=msname, reset_flags=True,
        flag_bad_ants=bad_ants,
        flag_uvrange=uvrange)

    solve_delay(incoming_file=msname,
                incoming_cal_tables=[],
                output_file_path=output_cal_file,output_file_name=delayname,output_file_overwrite=True,
                refant=refant_delay, minsnr=3, selection={}, # selection can be used for things like timerange - follow casa syntax for selectdata
                plot_solutions=True, plot_solutions_saveonly=True,
                )

    solve_bpass(incoming_file=msname,
                incoming_cal_tables=[os.path.join(output_cal_file,delayname)],
                output_file_path=output_cal_file,output_file_name=bpassname,output_file_overwrite=True,
                refant=refant_bpass, minsnr=3, selection={}, # selection can be used for things like timerange - follow casa syntax for selectdata
                plot_solutions=True, plot_solutions_ants=None, plot_solutions_saveonly=True,
                )

    if applycal:
        apply_cal(incoming_cal_file, [os.path.join(output_cal_file,delayname),os.path.join(output_cal_file,bpassname)], calmsname, output_file_overwrite=True)
        flag(incoming_file=calmsname, reset_flags=False,
             flag_bad_ants=bad_ants)

if __name__ == '__main__':

    # Infinite loop to find new calibrator passes and generate solutions - filter down to specific date ranges
    while True:
        files_calib = os.listdir('/data/pipeline/cal_solutions/')
        files_new = os.listdir('/data/pipeline/raw_cal/')        

        files_new = [f for f in files_new if f not in files_calib]
        files_new = [f for f in files_new if fnmatch(f, '*.ms')]

        # files_new = [f for f in files_new if fnmatch(f, '*2024-11-*.ms')]
        if len(files_new) == 0: # If no new files are found wait 60 seconds
            print("Waiting on new files")
            time.sleep(60)

        for f in files_new:
            cal_script(os.path.join('/data/pipeline/raw_cal/',f),
                    os.path.join('/data/pipeline/cal_solutions/',f),
                    bad_ants='pad48,pad71,pad93,pad101,pad116')
        
    # # Infinite loop to find new calibrator passes and generate solutions
    # files = []
    # while True:
    #     files_new = os.listdir('/data/pipeline/raw_cal/')
    #     files_new = [f for f in files_new if f not in files]
    #     files_new = [f for f in files_new if fnmatch(f, '*.ms')]
    #     if len(files_new) == 0: # If no new files are found wait 60 seconds
    #         print("Waiting on new files")
    #         time.sleep(60)

    #     for f in files_new:
    #         cal_script(os.path.join('/data/pipeline/raw_cal/',f),
    #                 os.path.join('/data/pipeline/cal_solutions/',f),
    #                 bad_ants='pad71,pad93,pad101,pad103,pad104,pad105,pad106,pad107,pad109,pad115,pad116')
        
    #         files.append(f)

    # # Infinite loop to find new calibrator passes and generate solutions
    # files = []
    # while True:
    #     files_new = os.listdir('/data/pipeline/raw_cal_spl/')
    #     files_new = [f for f in files_new if f not in files]
    #     files_new = [f for f in files_new if fnmatch(f, '*.ms')]
    #     if len(files_new) == 0: # If no new files are found wait 60 seconds
    #         print("Waiting on new files")
    #         time.sleep(60)

    #     for f in files_new:
    #         cal_script(os.path.join('/data/pipeline/raw_cal_spl/',f),
    #                 os.path.join('/data/pipeline/cal_solutions_spl/',f),
    #                 bad_ants='pad71,pad93,pad101,pad103,pad104,pad105,pad106,pad107,pad109,pad115,pad116',
    #                 average_channels=8)
        
    #         files.append(f)
        

    # # Test to see how different sets of bad antennas look
    # f = 'J1459+7140_2024-10-17T21:08:59.ms'
    # for bad_ants in ['pad71',
    #                 'pad116',
    #                 'pad71,pad116',
    #                 'pad71,pad93,pad101,pad103,pad104,pad105,pad106,pad107,pad109,pad115,pad116']:
    #     if bad_ants=='':
    #         file = 'none'
    #     else:
    #         file = bad_ants.strip(',')
    #     print("Doing solutions with {} flagged".format(bad_ants))
    #     print(os.path.join('/data/keenan/bad_ant_test/',file))
    #     cal_script(os.path.join('/data/pipeline/raw_cal/',f),
    #             os.path.join('/data/keenan/bad_ant_test/',file),
    #             bad_ants=bad_ants)
        

