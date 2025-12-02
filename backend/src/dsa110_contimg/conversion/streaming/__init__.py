# This file initializes the streaming module.
"""
Streaming Converter for DSA-110 Continuum Imaging Pipeline.

This module provides real-time data ingest functionality for the DSA-110
continuum imaging pipeline. The main classes are:

- QueueDB: SQLite-backed queue for tracking subband arrivals and processing state
- Various helper functions for mosaic tracking and photometry triggering

Usage:
    from dsa110_contimg.conversion.streaming import QueueDB, parse_subband_info
    queue = QueueDB(db_path)
    
    # Or via the main package
    from dsa110_contimg.conversion import QueueDB
"""

from dsa110_contimg.conversion.streaming.streaming_converter import (
    # Main classes
    QueueDB,
    # Helper functions
    parse_subband_info,
    override_env,
    setup_logging,
    # Mosaic functions
    get_mosaic_queue_status,
    check_for_complete_group,
    register_mosaic_group,
    update_mosaic_group_status,
    trigger_photometry_for_image,
    trigger_group_mosaic_creation,
    # CLI functions
    build_parser,
    main,
    # Constants
    GROUP_PATTERN,
    HAVE_WATCHDOG,
    HAVE_PHOTOMETRY,
)

__all__ = [
    # Main classes
    "QueueDB",
    # Helper functions
    "parse_subband_info",
    "override_env",
    "setup_logging",
    # Mosaic functions
    "get_mosaic_queue_status",
    "check_for_complete_group",
    "register_mosaic_group",
    "update_mosaic_group_status",
    "trigger_photometry_for_image",
    "trigger_group_mosaic_creation",
    # CLI functions
    "build_parser",
    "main",
    # Constants
    "GROUP_PATTERN",
    "HAVE_WATCHDOG",
    "HAVE_PHOTOMETRY",
]