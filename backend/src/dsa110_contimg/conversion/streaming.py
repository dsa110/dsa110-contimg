"""
Streaming Converter for DSA-110 Continuum Imaging Pipeline.

This module is the flattened entry point for streaming conversion functionality.
It re-exports from the streaming subpackage for backwards compatibility
during the migration period.

Usage:
    from dsa110_contimg.conversion.streaming import StreamingConverter, QueueDB
    # or
    from dsa110_contimg.conversion import StreamingConverter
"""

# Re-export all public APIs from the streaming subpackage
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
