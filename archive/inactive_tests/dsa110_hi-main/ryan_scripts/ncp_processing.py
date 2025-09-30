from fnmatch import fnmatch
import os
import numpy as np

do_ms = False
do_ms_spw = False
do_calib_solution = False
do_calib_transfer = False
do_imaging = True
do_clean_video = False

outputfile = '/data/keenan/2024-11-14_ncp/broadband/'
outputfile_spw = '/data/keenan/2024-11-14_ncp/spl/'
videoname = 'ncp_full'

if np.any([do_ms, do_ms_spw]) and np.any([do_calib_solution,do_calib_transfer,do_imaging]):
    raise ValueError("can't make ms and do other steps")

if do_ms:
    from script_ms import ms_script

    # 3c343.1 and 3c343 calibrator data
    ms_script(tmin='2024-11-08T21:03', tmax='2024-11-08T21:23',incoming_files='/data/incoming/processed/',
            output_files = '/data/pipeline/raw/', output_cal_files = '/data/pipeline/raw_cal/',
            loop=False)

    # on source data
    ms_script(tmin='2024-11-08T20:02', tmax='2024-11-08T20:42',incoming_files='/data/incoming/processed/',
            output_files = '/data/pipeline/raw/', output_cal_files = '/data/pipeline/raw_cal/',
            loop=False)
    ms_script(tmin='2024-11-09T00:10', tmax='2024-11-09T11:59',incoming_files='/data/incoming/processed/',
            output_files = '/data/pipeline/raw/', output_cal_files = '/data/pipeline/raw_cal/',
            loop=False)

if do_ms_spw:
    from script_ms import ms_script_spl

    # 3c343.1 and 3c343 calibrator data
    ms_script_spl(tmin='2024-11-08T21:03', tmax='2024-11-08T21:23',incoming_files='/data/incoming/processed/',
            output_files = '/data/pipeline/raw_spl/', output_cal_files = '/data/pipeline/raw_cal_spl/',
            loop=False)

    # on source data
    ms_script_spl(tmin='2024-11-08T20:02', tmax='2024-11-08T20:42',incoming_files='/data/incoming/processed/',
            output_files = '/data/pipeline/raw_spl/', output_cal_files = '/data/pipeline/raw_cal_spl/',
            loop=False)
    ms_script_spl(tmin='2024-11-09T00:10', tmax='2024-11-09T11:59',incoming_files='/data/incoming/processed/',
            output_files = '/data/pipeline/raw_spl/', output_cal_files = '/data/pipeline/raw_cal_spl/',
            loop=False)

if do_calib_solution:
    from script_cal import cal_script

    for calfile in ['3c343_3c343.1_2024-11-08T21:04:43.ms','3c343_3c343.1_2024-11-08T21:15:02.ms','3c343_3c343.1_2024-11-08T21:20:11.ms']:
        cal_script('/data/pipeline/raw_cal/'+calfile,
                '/data/pipeline/cal_solutions/'+calfile,
                bad_ants='pad48,pad71,pad93,pad101,pad116')

if do_calib_transfer:
    from script_image import transfer_script

    calfile = '/data/pipeline/cal_solutions/3c343_3c343.1_2024-11-08T21:15:02.ms'

    sourcefiles = os.listdir('/data/pipeline/raw')
    sourcefiles = [f for f in sourcefiles if (f>='2024-11-08T20:10' and f<='2024-11-10')] # Filter date range
    sourcefiles = [f for f in sourcefiles if fnmatch(f,'*dec+89*')] # Filter to NCP dec
    sourcefiles = ['/data/pipeline/raw/'+f for f in sourcefiles]

    sourcefiles_spw = os.listdir('/data/pipeline/raw_spl')
    sourcefiles_spw = [f for f in sourcefiles_spw if (f>='2024-11-08T20:10' and f<='2024-11-10')] # Filter date range
    sourcefiles_spw = [f for f in sourcefiles_spw if fnmatch(f,'*dec+89*')] # Filter to NCP dec
    sourcefiles_spw = ['/data/pipeline/raw/'+f for f in sourcefiles_spw]

    # transfer_script(sourcefiles, calfile, outputfile,
    #                 bad_ants='pad48,pad71,pad93,pad101,pad116', uvrange='<50m')
    transfer_script(sourcefiles, calfile, outputfile_spw,
                    bad_ants='pad48,pad71,pad93,pad101,pad116', uvrange='<50m')

if do_imaging:
    from script_image import tclean_selfcal
#     tclean_selfcal(outputfile+'source.ms', outputfile+'selfcal/', fields='', phase_center='J2000 00h00m00s +90d00m00s', imsize=[12000,12000],
#                    selfcal_thresholds=['100mJy', '10mJy'], selfcal_refant='pad8',
#                    final_thresholds=['10mJy', '3mJy', '1mJy'],
#                    psfcut=0.1)
    # tclean_selfcal(outputfile+'source.ms', outputfile+'selfcal/', fields='0~100', phase_center='J2000 00h00m00s +90d00m00s', imsize=[12000,12000],
    #                selfcal_thresholds=['100mJy', '10mJy'], selfcal_refant='pad8',
    #                final_thresholds=['10mJy', '3mJy', '1mJy'],
    #                psfcut=0.1)
#     tclean_selfcal(outputfile+'source.ms', outputfile+'selfcal_last_1000/', fields='2979~3479', phase_center='J2000 05h00m00s +89d30m00s', imsize=[8000,8000],
#                    selfcal_thresholds=['100mJy'], selfcal_refant='pad8',
#                    final_thresholds=['10mJy'],
#                    psfcut=0.1)
    # # Try all fields, but time average
    # tclean_selfcal(outputfile+'source.ms', outputfile+'selfcal_chan_avg/', phase_center='J2000 05h00m00s +90d00m00s', imsize=[9000,9000],
    #                selfcal_thresholds=['50mJy'], selfcal_refant='pad8',
    #                final_thresholds=['10mJy', '5mJy'],
    #                chanbin=10,
    #                psfcut=0.1,
    #                pbcut=0.1)

    # Try one SPL channel
    tclean_selfcal(outputfile_spw+'source.ms', outputfile_spw+'selfcal_chan_avg/', phase_center='J2000 05h00m00s +90d00m00s', imsize=[9000,9000],
                   selfcal_thresholds=['100mJy'], selfcal_refant='pad8',
                   final_thresholds=['100mJy'],
                   spw='0:0~1',
                   psfcut=0.1,
                   pbcut=0.1)


if do_clean_video:
    from script_image import all_snapshot_image
    all_snapshot_image(outputfile+'source.ms', outputfile+'snapshots_clean/',
                    size=[8000,8000], scale=3, weight='briggs 0.5',
                    niter=10000, autothresh=5, mgain=0.5,
                    do_image=False, ## Currently only making video - snapshots are already done
                    do_animate=True, vmin=0, vmax=.1, videoname=videoname+'_clean')
