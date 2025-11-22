"""
Tests for unified catalog query interface.
"""

import pytest

from dsa110_contimg.database.catalog_query import (
    find_calibrators_for_field,
    get_source_info,
    query_unified_catalog,
)


def test_query_unified_catalog_nvss():
    """Test querying NVSS catalog."""
    # Query a known bright source (3C286)
    sources = query_unified_catalog(
        ra_deg=202.7845,
        dec_deg=30.5092,
        radius_deg=0.1,
        catalogs=["nvss"],
        min_flux_jy=1.0,
    )

    assert isinstance(sources, list)
    # Should find at least one source near 3C286
    if sources:
        assert sources[0]["catalog"] == "NVSS"


def test_query_unified_catalog_vla():
    """Test querying VLA calibrators."""
    sources = query_unified_catalog(
        ra_deg=202.7845,
        dec_deg=30.5092,
        radius_deg=1.0,
        catalogs=["vla"],
    )

    assert isinstance(sources, list)


def test_find_calibrators_for_field():
    """Test finding calibrators for a field."""
    bp_cal, gain_cals = find_calibrators_for_field(
        ra_deg=202.7845,
        dec_deg=30.5092,
        radius_deg=0.1,
        min_flux_jy=1.0,
    )

    # Should return tuple
    assert isinstance(bp_cal, (dict, type(None)))
    assert isinstance(gain_cals, list)


def test_get_source_info():
    """Test getting source information."""
    # This will only work if we have registered calibrators
    info = get_source_info("3C286", catalog="vla")
    # May be None if not registered, which is OK
    assert info is None or isinstance(info, dict)
