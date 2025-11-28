"""
User-friendly error messages with suggestions.

This module provides utilities for formatting error messages in a way that
helps users understand and fix issues quickly.
"""

from typing import Any, Dict, List, Optional

# Error code definitions with help URLs and suggestions
ERROR_CODES = {
    "MODEL_DATA_UNPOPULATED": {
        "message": "MODEL_DATA column exists but is unpopulated (all zeros)",
        "help_url": "docs/troubleshooting/model_data.md",
        "code": "E001",
        "suggestions": [
            "Use --model-source=catalog (recommended, default)",
            "Use --model-source=setjy if calibrator at phase center (no rephasing)",
            "Use --model-source=component with --model-component=<path>",
            "Use --model-source=image with --model-image=<path>",
        ],
    },
    "FIELD_NOT_FOUND": {
        "message": "Specified field not found in MS",
        "help_url": "docs/troubleshooting/field_selection.md",
        "code": "E002",
        "suggestions": [
            "List available fields: python -m dsa110_contimg.calibration.cli validate --ms <ms>",
            "Use --auto-fields to auto-select fields",
            'Check field selection syntax (index, name, or range like "10~12")',
        ],
    },
    "REFANT_NOT_FOUND": {
        "message": "Reference antenna not found or has no unflagged data",
        "help_url": "docs/troubleshooting/refant_selection.md",
        "code": "E003",
        "suggestions": [
            "Use --refant-ranking to auto-select reference antenna",
            "Check available antennas: python -m dsa110_contimg.calibration.cli validate --ms <ms>",
            "Select an antenna with unflagged data throughout the observation",
        ],
    },
    "MS_EMPTY": {
        "message": "Measurement Set is empty (no data rows)",
        "help_url": "docs/troubleshooting/ms_empty.md",
        "code": "E004",
        "suggestions": [
            "Check if conversion completed successfully",
            "Verify input data files were not empty",
            "Re-run conversion from source data",
        ],
    },
    "MS_MISSING_COLUMNS": {
        "message": "MS missing required columns",
        "help_url": "docs/troubleshooting/ms_structure.md",
        "code": "E005",
        "suggestions": [
            "MS may be corrupted or incomplete",
            "Try reconverting from source data",
            "Check conversion logs for errors",
        ],
    },
    "INSUFFICIENT_UNFLAGGED_DATA": {
        "message": "Insufficient unflagged data after flagging",
        "help_url": "docs/troubleshooting/flagging.md",
        "code": "E006",
        "suggestions": [
            "Adjust flagging parameters (--flagging-mode)",
            "Check data quality and RFI conditions",
            "Consider using --fast mode for faster processing",
            "Review flagging statistics: python -m dsa110_contimg.calibration.cli flag --ms <ms> --mode summary",
        ],
    },
    "SETJY_WITH_REPHASING": {
        "message": "setjy cannot be used with rephasing (phase center bugs)",
        "help_url": "docs/reports/USER_SAFEGUARDS_PROPOSAL.md",
        "code": "E007",
        "suggestions": [
            "Use --model-source=catalog (default, recommended)",
            "Use --skip-rephase if calibrator is at meridian phase center",
            "Manual MODEL_DATA calculation is used automatically with catalog model",
        ],
    },
}


def get_error_code_info(error_type: str) -> Optional[Dict[str, Any]]:
    """
    Get error code information for a given error type.

    Args:
        error_type: Error type string (e.g., 'MODEL_DATA_UNPOPULATED')

    Returns:
        Dictionary with error code info, or None if not found
    """
    return ERROR_CODES.get(error_type)


def format_error_with_code(error_type: str, details: Dict[str, Any]) -> str:
    """
    Format error message with error code and suggestions.

    Args:
        error_type: Error type (key from ERROR_CODES)
        details: Additional error details

    Returns:
        Formatted error message with code and suggestions
    """
    error_info = ERROR_CODES.get(error_type)
    if not error_info:
        return f"Error: {error_type}\n"

    code = error_info.get("code", "E000")
    message = error_info.get("message", error_type)
    suggestions = error_info.get("suggestions", [])
    help_url = error_info.get("help_url", "")

    msg = f"[{code}] {message}\n"

    if suggestions:
        msg += "\nSuggested fixes:\n"
        for i, suggestion in enumerate(suggestions, 1):
            msg += f"  {i}. {suggestion}\n"

    if help_url:
        msg += f"\nFor more information, see: {help_url}\n"

    return msg


def format_validation_error(
    errors: List[str], warnings: Optional[List[str]] = None, context: str = ""
) -> str:
    """
    Format validation errors for user display.

    Args:
        errors: List of error messages
        warnings: Optional list of warning messages
        context: Optional context string (e.g., "MS validation")

    Returns:
        Formatted error message string
    """
    msg = f"Validation failed{': ' + context if context else ''}\n\n"

    if errors:
        msg += "Errors:\n"
        for i, error in enumerate(errors, 1):
            msg += f"  {i}. {error}\n"

    if warnings:
        msg += "\nWarnings:\n"
        for i, warning in enumerate(warnings, 1):
            msg += f"  {i}. {warning}\n"

    msg += "\nPlease fix the issues above and try again."
    return msg


def suggest_fix(error_type: str, details: Dict[str, Any]) -> str:
    """
    Suggest fixes for common errors.

    Args:
        error_type: Type of error ('ms_not_found', 'field_not_found', etc.)
        details: Dictionary with error details

    Returns:
        Suggested fix string
    """
    suggestions = {
        "ms_not_found": lambda d: (
            f"Check that the MS path is correct: {d.get('path', 'unknown')}\n"
            f"  - Verify the file exists: ls -la {d.get('path', '')}\n"
            f"  - Check if path is a directory (MS format): test -d {d.get('path', '')}"
        ),
        "file_not_found": lambda d: (
            f"Check that the file path is correct: {d.get('path', 'unknown')}\n"
            f"  - Verify the file exists: ls -la {d.get('path', '')}\n"
            f"  - Check file permissions: ls -l {d.get('path', '')}"
        ),
        "field_not_found": lambda d: (
            f"Field '{d.get('field', 'unknown')}' not found.\n"
            f"  - Available fields: {d.get('available', [])}\n"
            f"  - Check field selection syntax (index, name, or range like '10~12')"
        ),
        "refant_not_found": lambda d: (
            f"Reference antenna {d.get('refant', 'unknown')} not found.\n"
            f"  - Available antennas: {d.get('available', [])}\n"
            f"  - Suggested: {d.get('suggested', 'N/A')}\n"
            f"  - Use --refant-ranking to auto-select reference antenna"
        ),
        "directory_not_found": lambda d: (
            f"Directory not found: {d.get('path', 'unknown')}\n"
            f"  - Verify the directory exists: ls -la {d.get('path', '')}\n"
            f"  - Check permissions: ls -ld {d.get('path', '')}"
        ),
        "permission_denied": lambda d: (
            f"Permission denied: {d.get('path', 'unknown')}\n"
            f"  - Check file permissions: ls -la {d.get('path', '')}\n"
            f"  - Verify you have read/write access"
        ),
        "ms_empty": lambda d: (
            f"MS is empty: {d.get('path', 'unknown')}\n"
            f"  - The Measurement Set exists but contains no data\n"
            f"  - Check if conversion completed successfully\n"
            f"  - Verify input data files were not empty"
        ),
        "ms_missing_columns": lambda d: (
            f"MS missing required columns: {d.get('missing', [])}\n"
            f"  - This MS may be corrupted or incomplete\n"
            f"  - Try reconverting from source data\n"
            f"  - Check conversion logs for errors"
        ),
    }

    suggester = suggestions.get(error_type)
    if suggester:
        return suggester(details)

    return "No specific suggestion available. Check the error message above for details."


def format_error_with_suggestion(error: Exception, error_type: str, details: Dict[str, Any]) -> str:
    """
    Format an error with both the error message and a suggested fix.

    Args:
        error: The exception that occurred
        error_type: Type of error (used for lookup in suggest_fix)
        details: Dictionary with error details

    Returns:
        Formatted message with error and suggestion
    """
    msg = f"Error: {str(error)}\n\n"
    suggestion = suggest_fix(error_type, details)
    if suggestion:
        msg += f"Suggested fix:\n{suggestion}\n"
    return msg


def create_error_summary(errors: List[Dict[str, Any]]) -> str:
    """
    Create a summary of multiple errors with suggestions.

    Args:
        errors: List of error dicts, each with 'type', 'message', 'details'

    Returns:
        Formatted error summary
    """
    if not errors:
        return "No errors found."

    msg = f"Found {len(errors)} error(s):\n\n"

    for i, error_info in enumerate(errors, 1):
        error_type = error_info.get("type", "unknown")
        error_msg = error_info.get("message", "Unknown error")
        details = error_info.get("details", {})

        msg += f"{i}. {error_msg}\n"
        suggestion = suggest_fix(error_type, details)
        if suggestion:
            msg += f"   Fix: {suggestion.split(chr(10))[0]}\n"  # First line only
        msg += "\n"

    return msg
