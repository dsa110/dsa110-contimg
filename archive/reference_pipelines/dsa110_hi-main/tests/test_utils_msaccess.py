import pytest
import numpy as np
import os

from dsa110hi.utils_msaccess import _check_backend, get_pars, get_info
from dsa110hi.utils_msaccess import zero_field_ids, restore_field_ids

# Can only test one of casa or casacore in a given try
# Most other tests require casacore derived stuff, so hopefull
# setting to casacore will allow pytest to run without seg faulting
backend = 'casacore'
test_ms = '/data/pipeline/package_test_data/ms/test_ms.ms'

def test_check_backend():
    # First two should not cause problems
    _check_backend("casa")
    _check_backend("casacore")
    # Typo should throw an error
    with pytest.raises(ValueError):
        _check_backend("casacord")

def test_get_pars_single():
    x = get_pars(test_ms, '', 'UVW', backend=backend)
    assert isinstance(x, np.ndarray)
    assert x.shape == (3,111744)

def test_get_pars_single_aslist():
    x = get_pars(test_ms, '', ['UVW'], backend=backend)
    assert isinstance(x, list)
    assert isinstance(x[0], np.ndarray)
    assert x[0].shape == (3,111744)

def test_get_pars_multiple():

    x = get_pars(test_ms, '', ['UVW','ANTENNA1'], backend=backend)
    # Check list
    assert isinstance(x, list)
    assert len(x)==2

    # Check individual elements
    assert isinstance(x[0], np.ndarray)
    assert x[0].shape == (3,111744)
    assert isinstance(x[1], np.ndarray)
    assert x[1].shape == (111744,)

def test_get_pars_subtab():
    x = get_pars(test_ms, 'ANTENNA', ['NAME', 'OFFSET'], backend=backend)

    # Check list
    assert isinstance(x, list)
    assert len(x)==2

    # Check individual elements
    assert isinstance(x[0], np.ndarray)
    assert x[0].shape == (117,)
    assert isinstance(x[1], np.ndarray)
    assert x[1].shape == (3,117)

    # Check that specifying subtables for each column gives
    # identical results
    x2 = get_pars(test_ms, ['ANTENNA','ANTENNA'], ['NAME', 'OFFSET'], backend=backend)

    assert len(x)==len(x2)
    assert np.all(x[0]==x2[0])
    assert np.all(x[1]==x2[1])

def test_get_pars_multiple_subtab():
    x = get_pars(test_ms, ['','ANTENNA'], ['ANTENNA1', 'NAME'], backend=backend)

    # Check list
    assert isinstance(x, list)
    assert len(x)==2

    # Check individual elements
    assert isinstance(x[0], np.ndarray)
    assert x[0].shape == (111744,)
    assert isinstance(x[1], np.ndarray)
    assert x[1].shape == (117,)

def test_get_info():
    x = get_info(test_ms, backend=backend)

    assert isinstance(x, dict)
    assert x['type'] == 'Measurement Set'

def test_zero_field_ids():
    id0 = get_pars(test_ms, '', 'FIELD_ID', backend=backend)

    assert not np.all(id0==0)

    zero_field_ids(test_ms, backend=backend)
    id1 = get_pars(test_ms, '', 'FIELD_ID', backend=backend)

    assert not np.all(id1==id0)
    assert np.all(id1==0)

    assert os.path.exists(test_ms+'.field_id_backup.npy')

    restore_field_ids(test_ms, backend=backend, del_idfile=True)

    id2 = get_pars(test_ms, '', 'FIELD_ID', backend=backend)
    assert np.all(id2==id0)
    assert not np.all(id2==0)

    assert not os.path.exists(test_ms+'.field_id_backup.npy')

def test_zero_field_ids_idfile():
    id0 = get_pars(test_ms, '', 'FIELD_ID', backend=backend)

    assert not np.all(id0==0)

    zero_field_ids(test_ms, backend=backend, idfile=test_ms+'.field_id_backup_test.npy')
    id1 = get_pars(test_ms, '', 'FIELD_ID', backend=backend)

    assert not np.all(id1==id0)
    assert np.all(id1==0)

    assert os.path.exists(test_ms+'.field_id_backup_test.npy')

    restore_field_ids(test_ms, backend=backend, del_idfile=True, idfile=test_ms+'.field_id_backup_test.npy')

    id2 = get_pars(test_ms, '', 'FIELD_ID', backend=backend)
    assert np.all(id2==id0)
    assert not np.all(id2==0)

    assert not os.path.exists(test_ms+'.field_id_backup_test.npy')

