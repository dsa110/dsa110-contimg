"""Catalog utilities (master catalog build, crossmatches, per-strip databases)."""

from dsa110_contimg.catalog.crossmatch import (
    calculate_flux_scale,
    calculate_positional_offsets,
    cross_match_dataframes,
    cross_match_sources,
    identify_duplicate_catalog_sources,
    multi_catalog_match,
    search_around_sky,
)

try:
    from dsa110_contimg.catalog.external import (
        gaia_search,
        ned_search,
        query_all_catalogs,
        simbad_search,
    )
except ImportError:
    # astroquery not available
    simbad_search = None
    ned_search = None
    gaia_search = None
    query_all_catalogs = None

__all__ = [
    "cross_match_sources",
    "cross_match_dataframes",
    "calculate_positional_offsets",
    "calculate_flux_scale",
    "search_around_sky",
    "multi_catalog_match",
    "identify_duplicate_catalog_sources",
]

from .build_atnf_pulsars import build_atnf_pulsar_db
from .builders import (
    CATALOG_COVERAGE_LIMITS,
    auto_build_missing_catalog_databases,
    build_atnf_strip_db,
    build_first_strip_db,
    build_nvss_strip_db,
    build_rax_strip_db,
    build_vlass_strip_db,
    check_catalog_database_exists,
    check_missing_catalog_databases,
)
from .query import query_sources, resolve_catalog_path

__all__ = [
    "query_sources",
    "resolve_catalog_path",
    "build_nvss_strip_db",
    "build_first_strip_db",
    "build_rax_strip_db",
    "build_atnf_strip_db",
    "build_atnf_pulsar_db",
    "auto_build_missing_catalog_databases",
    "check_missing_catalog_databases",
    "check_catalog_database_exists",
    "CATALOG_COVERAGE_LIMITS",
    "build_vlass_strip_db",
    "simbad_search",
    "ned_search",
    "gaia_search",
    "query_all_catalogs",
]
