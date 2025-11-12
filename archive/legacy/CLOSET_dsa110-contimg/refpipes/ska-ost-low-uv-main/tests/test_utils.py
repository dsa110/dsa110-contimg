"""test_utils: Tests for utils.py."""

import os
import shutil

import pytest

from ska_ost_low_uv.utils import import_optional_dependency, inspect_class_method, zipit


def test_zipit():
    """Test zipping functionality."""

    def create_dummy_dir():
        os.mkdir('test-zip')
        os.system('touch test-zip/hello.txt')
        os.system('touch test-zip/hi.txt')

    create_dummy_dir()
    zipit('test-zip')
    assert os.path.exists('test-zip.zip')
    shutil.rmtree('test-zip')

    create_dummy_dir()
    zipit('test-zip', rm_dir=True)
    assert os.path.exists('test-zip.zip')
    assert ~os.path.exists('test-zip')

    os.remove('test-zip.zip')


def test_import_optional_dependency():
    """Test optional importing util."""
    import_optional_dependency('numpy')
    import_optional_dependency('numpy.linalg')
    with pytest.raises(ImportError):
        import_optional_dependency('whatimlookingfor')
    import_optional_dependency('whatimlookingfor', 'warn')
    import_optional_dependency('whatimlookingfor', 'ignore')


def test_inspect_class_method():
    """Test inspect class method."""
    from ska_ost_low_uv.postx import ApertureArray  # noqa: F401, I001

    print(inspect_class_method(ApertureArray, '__init__'))

    aa = ApertureArray(station_id='s8-6')
    print(inspect_class_method(aa, '__init__'))


if __name__ == '__main__':
    test_zipit()
    test_import_optional_dependency()
