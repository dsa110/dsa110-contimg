#!/usr/bin/env python3
import json

from core.pipeline.stages.calibration_stage import CalibrationStage


def build_stage():
    cfg = {
        'calibration': {
            'bandpass': {
                'field': '0',
                'refant': '3',
                'solint': 'inf',
                'combine': 'scan,spw',
                'minsnr': 2.5,
                'solnorm': True,
                'bandtype': 'B',
                'fillgaps': 0,
                'gaintable': '',
                'gainfield': '',
                'interp': 'linear',
                'spwmap': [],
                'append': False,
            },
            'gain': {
                'field': '0',
                'refant': '3',
                'solint': '30s',
                'combine': 'scan',
                'minsnr': 1.5,
                'solnorm': True,
                'calmode': 'ap',
                'gaintable': '',
                'gainfield': '',
                'interp': 'nearest',
                'spwmap': [],
                'uvrange': '',
                'append': False,
            },
            'apply': {
                'gainfield': [],
                'interp': ['nearest', 'linear'],
                'spwmap': [],
                'calwt': False,
                'flagbackup': False,
                'applymode': 'calonly',
            }
        },
        'paths': {}
    }
    return CalibrationStage(cfg)


def test_bandpass_params():
    stage = build_stage()
    params = stage._build_bandpass_params(['a.ms', 'b.ms'], 'out_b.table')
    assert params['vis'] == ['a.ms', 'b.ms']
    assert params['caltable'] == 'out_b.table'
    assert params['refant'] == '3'
    assert params['solint'] == 'inf'
    assert params['combine'] == 'scan,spw'
    assert params['minsnr'] == 2.5
    assert params['bandtype'] == 'B'


def test_gain_params():
    stage = build_stage()
    params = stage._build_gain_params(['a.ms'], 'out_g.table')
    assert params['vis'] == ['a.ms']
    assert params['caltable'] == 'out_g.table'
    assert params['refant'] == '3'
    assert params['solint'] == '30s'
    assert params['calmode'] == 'ap'
    assert params['combine'] == 'scan'
    assert params['minsnr'] == 1.5


def test_apply_params():
    stage = build_stage()
    params = stage._build_apply_params('a.ms', ['bcal', 'g0', 'g1'])
    assert params['vis'] == 'a.ms'
    assert params['gaintable'] == ['bcal', 'g0', 'g1']
    assert params['interp'] == ['nearest', 'linear']
    assert params['applymode'] == 'calonly'


if __name__ == '__main__':
    test_bandpass_params()
    test_gain_params()
    test_apply_params()
    print('OK')


