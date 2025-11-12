import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

if 'pipeline' not in sys.modules:
    pkg = types.ModuleType('pipeline')
    pkg.__path__ = [str(ROOT / 'pipeline')]
    sys.modules['pipeline'] = pkg

if 'pipeline.utils' not in sys.modules:
    subpkg = types.ModuleType('pipeline.utils')
    subpkg.__path__ = [str(ROOT / 'pipeline' / 'utils')]
    sys.modules['pipeline.utils'] = subpkg

_module_name = 'pipeline.utils.ms_io'
_ms_io_path = ROOT / 'pipeline' / 'utils' / 'ms_io.py'
_spec = importlib.util.spec_from_file_location(_module_name, _ms_io_path)
ms_io = importlib.util.module_from_spec(_spec)
ms_io.__package__ = 'pipeline.utils'
sys.modules[_module_name] = ms_io
_spec.loader.exec_module(ms_io)  # type: ignore[attr-defined]


class FakeUVData:
    def __init__(self):
        self.written_fits = None

    def write_uvfits(self, path, **_: object) -> None:
        fits_path = Path(path)
        fits_path.touch()
        self.written_fits = str(fits_path)


class _FakeTable:
    def __init__(self, path, readonly=False):
        self.path = path
        self.readonly = readonly
        self.records = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def putcol(self, name, value):
        self.records.setdefault(name, []).append(np.asarray(value))


def test_write_uvdata_to_ms_via_uvfits(tmp_path, monkeypatch):
    fake_uv = FakeUVData()
    ms_path = tmp_path / "test_output"
    fits_path = ms_path.with_suffix(".fits")

    import_calls = {}

    def fake_importuvfits(src, dest):
        import_calls['call'] = (src, dest)

    fake_tables = {}

    def fake_table(path, readonly=False):
        tbl = _FakeTable(path, readonly=readonly)
        fake_tables[path] = tbl
        return tbl

    monkeypatch.setattr(ms_io, 'importuvfits', fake_importuvfits)
    monkeypatch.setattr(ms_io, 'table', fake_table)
    monkeypatch.setattr(ms_io, 'addImagingColumns', lambda path: import_calls.setdefault('add', path))

    antenna_positions = np.zeros((2, 3))

    result_path = ms_io.write_uvdata_to_ms_via_uvfits(
        fake_uv,
        ms_path,
        antenna_positions=antenna_positions,
        overwrite=False,
        keep_uvfits=False,
        logger=None,
    )

    assert result_path == ms_path.with_suffix('.ms')
    assert fake_uv.written_fits == str(fits_path)
    assert 'call' in import_calls
    assert import_calls['call'][0] == str(fits_path)
    assert import_calls['call'][1] == str(result_path)
    assert fits_path.exists() is False
    assert str(result_path / 'ANTENNA') in fake_tables


def test_write_uvdata_to_ms_respects_overwrite(tmp_path):
    fake_uv = FakeUVData()
    ms_path = tmp_path / "existing"
    ms_dir = ms_path.with_suffix('.ms')
    ms_dir.mkdir()

    with pytest.raises(FileExistsError):
        ms_io.write_uvdata_to_ms_via_uvfits(
            fake_uv,
            ms_path,
            antenna_positions=np.zeros((1, 3)),
            overwrite=False,
            keep_uvfits=False,
        )


def test_write_uvdata_to_ms_can_keep_uvfits(tmp_path, monkeypatch):
    fake_uv = FakeUVData()
    ms_path = tmp_path / "keep"
    fits_path = ms_path.with_suffix('.fits')

    def fake_importuvfits(src, dest):
        Path(dest).mkdir()

    def fake_table(path, readonly=False):
        return _FakeTable(path, readonly)

    monkeypatch.setattr(ms_io, 'importuvfits', fake_importuvfits)
    monkeypatch.setattr(ms_io, 'table', fake_table)
    monkeypatch.setattr(ms_io, 'addImagingColumns', lambda path: None)

    result = ms_io.write_uvdata_to_ms_via_uvfits(
        fake_uv,
        ms_path,
        antenna_positions=np.zeros((1, 3)),
        overwrite=True,
        keep_uvfits=True,
        logger=None,
    )

    assert result == ms_path.with_suffix('.ms')
    assert Path(fake_uv.written_fits) == fits_path
    assert fits_path.exists()

