# from script_ms import ms_script

# ms_script(tmin='2024-11-08T21:03', tmax='2024-11-08T21:23',incoming_files='/data/incoming/processed/',
#     output_files = '/data/jfaber/msdir/field/', output_cal_files = '/data/jfaber/msdir/calib/',
#     loop=False)

from script_cal import cal_script

cal_script(incoming_cal_file='/data/jfaber/msdir/calib/3c343_3c343.1_2024-11-08T21:04:43.ms',
           output_cal_file='/data/jfaber/msdir/calib/3c343_solution',
           bad_ants='pad48,pad116')

from dsa110hi.utils_calib import plot_delay
plot_delay('/data/jfaber/msdir/calib/3c343_solution/DELAY',backend='casa')


from script_image import transfer_script, all_snapshot_image, tclean_selfcal

transfer_script(incoming_files=['/data/jfaber/msdir/field/2024-11-08T21:04:43_ra247.0_dec+62.6.ms'],
                incoming_cal_file='/data/jfaber/msdir/calib/3c343_solution',
                output_file='/data/jfaber/msdir/field/2024-11-08T21:04:43_ra247.0_dec+62.6_calib.ms',
                bad_ants='pad48,pad116')

all_snapshot_image(incoming_file='/data/jfaber/msdir/field/2024-11-08T21:04:43_ra247.0_dec+62.6_calib.mssource.mssource.ms', 
                   output_file='/data/jfaber/msdir/field/2024-11-08T21:04:43_ra247.0_dec+62.6_snapshots/',
                   size=[6000,6000], scale=3, weight='briggs 0.5',
                   do_animate=True, vmin=0, vmax=.1, videoname='video_ncp')

tclean_selfcal(incoming_file='/data/jfaber/msdir/field/2024-11-08T21:04:43_ra247.0_dec+62.6_calib.mssource.mssource.ms', 
               output_file='/data/jfaber/msdir/field/2024-11-08T21:04:43_ra247.0_dec+62.6_selfcal/', 
               phase_center='J2000 16h38m28.2058s +62:34:44.318s', 
               imsize=[6000,6000],
               selfcal_thresholds=['100mJy'], selfcal_refant='pad8',
               final_thresholds=['10mJy'])
