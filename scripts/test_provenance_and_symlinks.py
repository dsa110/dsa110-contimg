#!/usr/bin/env python3
import json
import os
import tempfile
from types import SimpleNamespace

from astropy.coordinates import SkyCoord
import astropy.units as u

from dsa110.calibration.provenance import write_provenance
from dsa110.pipeline.stages.calibration_stage import CalibrationStage


def test_write_provenance():
    with tempfile.TemporaryDirectory() as td:
        payload = {
            'ms': '/data/ms/test.ms',
            'field_center': {'ra_deg': 10.0, 'dec_deg': 20.0},
            'calibrator': {'name': 'NVSS J0000+0000', 'flux_jy_ref': 1.2},
            'component_list': '/data/sky_models/cal.cl',
            'refant': '0',
            'solints': {'delay': 'inf', 'bandpass': 'inf', 'gain': '30s'},
            'combine': 'scan',
            'tables': {'G0': '/data/cal_tables/g0.table', 'B0': '/data/cal_tables/b0.table', 'G1': '/data/cal_tables/g1.table'},
        }
        path = write_provenance(payload, td, 'calibration_provenance')
        assert os.path.exists(path)
        latest = os.path.join(td, 'calibration_provenance.latest.json')
        assert os.path.exists(latest)
        # Load json to verify structure
        with open(path, 'r') as f:
            data = json.load(f)
        assert data['ms'] == payload['ms']
        assert 'timestamp' not in data  # no auto timestamp in payload


def test_update_table_symlinks():
    stage = CalibrationStage(config={'paths': {'cal_tables_dir': ''}})
    with tempfile.TemporaryDirectory() as td:
        # create dummy table files
        bpath = os.path.join(td, 'test_b.table')
        gpath = os.path.join(td, 'test_g.table')
        open(bpath, 'w').close()
        open(gpath, 'w').close()
        stage._update_table_symlinks(td, bpath, gpath)
        assert os.path.islink(os.path.join(td, 'latest.bcal'))
        assert os.path.islink(os.path.join(td, 'latest.gcal'))


def test_persist_calibration_provenance_helper():
    stage = CalibrationStage(config={'paths': {'cal_tables_dir': ''}})
    with tempfile.TemporaryDirectory() as td:
        center = SkyCoord(ra=10.0 * u.deg, dec=20.0 * u.deg, frame='icrs')
        path = stage._persist_calibration_provenance(
            output_dir=td,
            ms_path='/data/ms/test.ms',
            center_coord=center,
            calibrator_info={'name': 'NVSS J0000+0000'},
            cl_path='/data/sky_models/cal.cl',
            refant='0',
            solints={'delay': 'inf', 'bandpass': 'inf', 'gain': '30s'},
            combine='scan',
            tables={'G0': '/x/g0', 'B0': '/x/b0', 'G1': '/x/g1'}
        )
        assert path is not None and os.path.exists(path)


if __name__ == '__main__':
    test_write_provenance()
    test_update_table_symlinks()
    test_persist_calibration_provenance_helper()
    print('OK')


