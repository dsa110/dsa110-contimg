"""Catalog utilities (master catalog build, crossmatches, per-strip databases)."""

from dsa110_contimg.catalog.crossmatch import (
    cross_match_sources,
    cross_match_dataframes,
    calculate_positional_offsets,
    calculate_flux_scale,
    search_around_sky,
    multi_catalog_match,
    identify_duplicate_catalog_sources,
)

try:
    from dsa110_contimg.catalog.external import (
        simbad_search,
        ned_search,
        gaia_search,
        query_all_catalogs,
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

from .builders import build_first_strip_db, build_nvss_strip_db, build_rax_strip_db
from .query import query_sources, resolve_catalog_path

__all__ = [
    "query_sources",
    "resolve_catalog_path",
    "build_nvss_strip_db",
    "build_first_strip_db",
    "build_rax_strip_db",
    "simbad_search",
    "ned_search",
    "gaia_search",
    "query_all_catalogs",
]
