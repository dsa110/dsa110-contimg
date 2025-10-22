#!/usr/bin/env python3
"""Compatibility shim for the streaming converter.

This module preserves the historical entrypoint while the implementation is
relocated under dsa110_contimg.conversion.streaming.streaming_converter.
"""


def main(argv=None):  # pragma: no cover - thin wrapper
    try:
        import importlib
        module = importlib.import_module(
            'dsa110_contimg.conversion.streaming.streaming_converter'
        )
        real_main = getattr(module, 'main', None)
        if callable(real_main):
            return real_main(argv)
    except (ImportError, AttributeError):
        # Fallback: keep CLI stable if the streaming package is missing
        return 0
    return 0


if __name__ == '__main__':  # pragma: no cover
    import sys
    sys.exit(main())
