do_step_ms = False
do_step_cal = True
do_step_image = False

do_standard = False
do_spl = True

if do_step_ms and do_step_cal:
    raise ValueError("Can't make MS and solve calibration in the same run")

import os

if do_step_ms:
    from dsa110hi.pipeline_msmaker import convert_to_ms

    if do_standard:
        if not os.path.exists('/data/pipeline/package_test_data/ms'):
            os.mkdir('/data/pipeline/package_test_data/ms')
        convert_to_ms(incoming_file_path='/data/pipeline/package_test_data/h5/test_3c48/',
                    incoming_file_names=[f'2024-11-02T06:43:34_sb{i:02d}.hdf5' for i in range(16)],
                    #   incoming_file_names=[f'2024-11-02T06:43:34_sb{i:02d}.hdf5' for i in range(1)],
                    tmin=None, tmax=None,
                    same_timestamp_tolerance=30.0,
                    output_file_path='/data/pipeline/package_test_data/ms/',
                    output_antennas=None,
                    cal_do_search=True, cal_search_radius=1.0, cal_catalog=None,
                    cal_output_file_path='/data/pipeline/package_test_data/ms/',
                    post_handle='none'
                    )
    if do_spl:
        if not os.path.exists('/data/pipeline/package_test_data/ms_spl'):
            os.mkdir('/data/pipeline/package_test_data/ms_spl')

        convert_to_ms(incoming_file_path='/data/pipeline/package_test_data/h5/test_3c48/',
                    incoming_file_names=['2024-11-02T06:43:38_sb06_spl.hdf5',
                                         '2024-11-02T06:43:37_sb07_spl.hdf5',
                                         '2024-11-02T06:43:37_sb08_spl.hdf5',
                                         '2024-11-02T06:43:37_sb09_spl.hdf5'],
                    spw=['sb06_spl','sb07_spl','sb08_spl','sb09_spl'],
                    tmin=None, tmax=None,
                    same_timestamp_tolerance=30.0,
                    output_file_path='/data/pipeline/package_test_data/ms_spl/',
                    output_antennas=None,
                    cal_do_search=True, cal_search_radius=1.0, cal_catalog=None,
                    cal_output_file_path='/data/pipeline/package_test_data/ms_spl/',
                    post_handle='none'
                    )

if do_step_cal:
    from dsa110hi.pipeline_calsolver import flag, solve_delay, solve_bpass

    if do_standard:
        if not os.path.exists('/data/pipeline/package_test_data/cal'):
            os.mkdir('/data/pipeline/package_test_data/cal')

        flag(incoming_file='/data/pipeline/package_test_data/ms/3c48_2024-11-02T06:43:34.ms', reset_flags=True,
            flag_bad_ants='pad48,pad71,pad93,pad101,pad116',
            flag_uvrange='<250m')
        
        solve_delay(incoming_file='/data/pipeline/package_test_data/ms/3c48_2024-11-02T06:43:34.ms',
                    incoming_cal_tables=[],
                    output_file_path='/data/pipeline/package_test_data/cal/',
                    output_file_name='DELAY_3c48_2024-11-02T06:43:34',
                    output_file_overwrite=True,
                    refant='pad108',
                    minsnr=3,
                    selection={},
                    plot_solutions=True,
                    plot_solutions_saveonly=False
                    )

        solve_bpass(incoming_file='/data/pipeline/package_test_data/ms/3c48_2024-11-02T06:43:34.ms',
                    incoming_cal_tables=['/data/pipeline/package_test_data/cal/DELAY_3c48_2024-11-02T06:43:34'],
                    output_file_path='/data/pipeline/package_test_data/cal/',
                    output_file_name='BPASS_3c48_2024-11-02T06:43:34',
                    output_file_overwrite=True,
                    refant='pad8', minsnr=3, selection={},
                    plot_solutions=True, plot_solutions_pols=None, plot_solutions_ants=None, plot_solutions_saveonly=True,
                    )
    
    if do_spl:
        if not os.path.exists('/data/pipeline/package_test_data/cal_spl'):
            os.mkdir('/data/pipeline/package_test_data/cal_spl')

        flag(incoming_file='/data/pipeline/package_test_data/ms_spl/3c48_2024-11-02T06:43:37.ms', reset_flags=True,
            flag_bad_ants='pad48,pad71,pad93,pad101,pad116',
            flag_uvrange='<250m')
        
        solve_delay(incoming_file='/data/pipeline/package_test_data/ms_spl/3c48_2024-11-02T06:43:37.ms',
                    incoming_cal_tables=[],
                    output_file_path='/data/pipeline/package_test_data/cal_spl/',
                    output_file_name='DELAY_3c48_2024-11-02',
                    output_file_overwrite=True,
                    refant='pad108',
                    minsnr=3,
                    selection={},
                    plot_solutions=True,
                    plot_solutions_saveonly=False
                    )

        solve_bpass(incoming_file='/data/pipeline/package_test_data/ms_spl/3c48_2024-11-02T06:43:37.ms',
                    incoming_cal_tables=['/data/pipeline/package_test_data/cal_spl/DELAY_3c48_2024-11-02'],
                    output_file_path='/data/pipeline/package_test_data/cal_spl/',
                    output_file_name='BPASS_3c48_2024-11-02',
                    output_file_overwrite=True,
                    refant='pad8', minsnr=3, selection={},
                    plot_solutions=True, plot_solutions_pols=None, plot_solutions_ants=None, plot_solutions_saveonly=True,
                    )