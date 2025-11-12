"""test_converter: test data conversion utils."""

import os

import pytest

from ska_ost_low_uv.converter import parse_args, run
from ska_ost_low_uv.io import read_uvx
from ska_ost_low_uv.utils import get_resource_path, get_test_data


def test_converter():
    """Test conversion into different file formats."""
    for fmt in ('uvfits', 'miriad', 'mir', 'ms', 'uvh5'):
        try:
            # Delete temp file if it exists
            if os.path.exists(f'test.{fmt}'):
                if fmt in ('miriad', 'mir', 'ms'):
                    os.system(f'rm -rf test.{fmt}')
                else:
                    os.remove(f'test.{fmt}')

            # Create command-line args
            cmd = [
                '-n',
                'aavs2',
                '-o',
                fmt,
                'tests/test-data/aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5',
                f'tests/test.{fmt}',
            ]

            # Run the script
            args = parse_args(cmd)
            print(args)

            run(cmd)
        finally:
            # clean up temp files
            if os.path.exists(f'tests/test.{fmt}'):
                if fmt in ('miriad', 'mir', 'ms'):
                    os.system(f'rm -rf tests/test.{fmt}')
                else:
                    os.remove(f'tests/test.{fmt}')


def test_phase_to_sun():
    """Test with sun phasing applied."""
    try:
        cmd = [
            '-o',
            'uvfits',
            '-s',
            '-n',
            'aavs3',
            get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5'),
            'tests/test.uvfits',
        ]
        run(cmd)
    finally:
        if os.path.exists('tests/test.uvfits'):
            os.remove('tests/test.uvfits')


def test_errors():
    """Test errors are thrown and caught."""
    # Create command-line args
    cmd = ['-c', 'carmen/santiago', '-o', 'svg', 'input.hdf5', 'output.uvfits']
    # Run the script
    parse_args(cmd)
    run(cmd)


def test_batch():
    """Test batch modes of conversion util."""
    try:
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-b',
            '-o',
            'uvx',
            get_test_data('aavs2_2x500ms'),
            'tests/test-batch-data',
        ]
        run(cmd)

        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-B',
            '-o',
            'uvx',
            get_test_data('.'),  # Note -B MEGABATCH test
            'tests/test-batch-data',
        ]
        run(cmd)
    finally:
        if os.path.exists('tests/test-batch-data'):
            os.system('rm -rf tests/test-batch-data')


def test_batch_zip():
    """Test batch mode, applying zip."""
    try:
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-b',
            '-z',
            '-o',
            'ms',
            get_test_data('aavs2_2x500ms'),
            'tests/test-batch-data',
        ]
        run(cmd)

        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-B',
            '-z',
            '-o',
            'miriad',
            get_test_data('.'),  # Note -B MEGABATCH test
            'tests/test-batch-data2',
        ]
        run(cmd)

    finally:
        if os.path.exists('tests/test-batch-data.zip'):
            os.system('rm -rf tests/test-batch-data.zip')
        if os.path.exists('tests/test-batch-data'):
            os.system('rm -rf tests/test-batch-data')
        if os.path.exists('tests/test-batch-data2'):
            os.system('rm -rf tests/test-batch-data2')
        pass


def test_batch_multi():
    """Test with multiple file output types."""
    try:
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-b',
            '-z',
            '-o',
            'ms,miriad,uvx',
            get_test_data('aavs2_2x500ms'),
            'tests/test-batch-data',
        ]
        run(cmd)

    finally:
        if os.path.exists('tests/test-batch-data'):
            os.system('rm -rf tests/test-batch-data')


def test_context():
    """Test that context info is saved into files."""
    try:
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-i',
            get_test_data('context.yaml'),
            '-o',
            'uvx',
            get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5'),
            'tests/test.uvx5',
        ]
        run(cmd)
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-i',
            get_test_data('context.yaml'),
            '-o',
            'uvx',
            get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5'),
            'tests/test.uvx5',
        ]
        run(cmd)
        uv = read_uvx('tests/test.uvx5')
        print(uv.context)
        assert uv.context['intent'] == 'Test routine for ska_ost_low_uv package'
    finally:
        if os.path.exists('tests/test.uvx5'):
            os.remove('tests/test.uvx5')


@pytest.mark.skip(reason='pytest does not play nicely with parallel tasks')
def test_parallel():
    """Test parallel file conversion using joblib/dask."""
    try:
        # One worker
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-i',
            get_test_data('context.yaml'),
            '-o',
            'uvx',
            '-w',
            '2',
            get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5'),
            'tests/test.uvx5',
        ]
        run(cmd)
        # Change number of workers
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-i',
            get_test_data('context.yaml'),
            '-o',
            'uvx',
            '-w',
            '8',
            get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5'),
            'tests/test.uvx5',
        ]
        run(cmd)
        # Use dask instead
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-i',
            get_test_data('context.yaml'),
            '-o',
            'uvx',
            '-w',
            '8',
            '-p',
            'dask',
            get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5'),
            'tests/test.uvx5',
        ]
        run(cmd)
        # Verbose
        cmd = [
            '-c',
            get_resource_path('config/aavs3/uv_config.yaml'),
            '-i',
            get_test_data('context.yaml'),
            '-o',
            'uvx',
            '-w',
            '1',
            '-v',
            get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5'),
            'tests/test.uvx5',
        ]
        run(cmd)

    finally:
        if os.path.exists('tests/test.uvx5'):
            os.remove('tests/test.uvx5')


if __name__ == '__main__':
    test_context()
    test_batch_multi()
    test_batch()
    test_phase_to_sun()

    test_errors()
    test_converter()
    test_batch_zip()
    test_parallel()
