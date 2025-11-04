import inspect


def test_solve_gains_accepts_minsnr():
    from dsa110_contimg.calibration.calibration import solve_gains

    sig = inspect.signature(solve_gains)
    assert 'minsnr' in sig.parameters, "solve_gains must accept a 'minsnr' parameter"


def test_solve_bandpass_accepts_smoothing():
    from dsa110_contimg.calibration.calibration import solve_bandpass

    sig = inspect.signature(solve_bandpass)
    assert 'bp_smooth_type' in sig.parameters
    assert 'bp_smooth_window' in sig.parameters


