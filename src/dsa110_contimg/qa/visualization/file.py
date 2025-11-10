"""
Base file class for QA visualization framework.

Provides base functionality for file handling, similar to RadioPadre's FileBase.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .thumbnail import get_cache_file, render_thumbnail_html


class FileBase:
    """
    Base class for file-like objects in the QA visualization framework.

    Provides common functionality for path handling, file metadata, and display.
    """

    def __init__(self, path: str, title: Optional[str] = None, parent=None):
        """
        Initialize a file base object.

        Args:
            path: File or directory path
            title: Optional display title
            parent: Optional parent object
        """
        self.path = path
        self.fullpath = os.path.abspath(path)
        self._title = title or os.path.basename(self.fullpath)
        self._parent = parent
        self._mtime = None
        self._was_shown = False

    @property
    def title(self) -> str:
        """Get the display title."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Set the display title."""
        self._title = value

    @property
    def basename(self) -> str:
        """Get the basename of the file."""
        return os.path.basename(self.fullpath)

    @property
    def dirname(self) -> str:
        """Get the directory name of the file."""
        return os.path.dirname(self.fullpath)

    @property
    def exists(self) -> bool:
        """Check if the file exists."""
        return os.path.exists(self.fullpath)

    @property
    def isdir(self) -> bool:
        """Check if the path is a directory."""
        return os.path.isdir(self.fullpath)

    @property
    def isfile(self) -> bool:
        """Check if the path is a file."""
        return os.path.isfile(self.fullpath)

    @property
    def size(self) -> int:
        """Get the file size in bytes."""
        if self.isfile:
            return os.path.getsize(self.fullpath)
        return 0

    @property
    def mtime(self) -> Optional[float]:
        """Get the modification time."""
        if self.exists:
            return os.path.getmtime(self.fullpath)
        return None

    def is_updated(self) -> bool:
        """
        Check if the file has been updated since last check.

        Returns:
            True if file has been updated
        """
        current_mtime = self.mtime
        if current_mtime is None:
            return False
        if self._mtime is None:
            self._mtime = current_mtime
            return False
        if current_mtime > self._mtime:
            self._mtime = current_mtime
            return True
        return False

    def update_mtime(self) -> None:
        """Update the stored modification time."""
        self._mtime = self.mtime

    @property
    def was_shown(self) -> bool:
        """Check if this file has been displayed."""
        return self._was_shown

    def mark_shown(self) -> None:
        """Mark this file as having been shown."""
        self._was_shown = True

    def show(self) -> None:
        """
        Display the file (to be implemented by subclasses).

        This method should be overridden by subclasses to provide
        appropriate display functionality.
        """
        self.mark_shown()
        raise NotImplementedError("Subclasses must implement show()")

    def _get_cache_file(
        self, cache_type: str, extension: str, keydict: Optional[dict] = None
    ) -> tuple:
        """
        Get cache file path for this file.

        Args:
            cache_type: Type of cache (e.g., "thumbs", "html-render")
            extension: File extension for cache file
            keydict: Optional dictionary of cache parameters

        Returns:
            Tuple of (cache_file_path, cache_file_url, needs_update)
        """
        return get_cache_file(self.fullpath, cache_type, extension, keydict)

    def render_thumb(self, width: Optional[int] = None, **kwargs) -> str:
        """
        Render a thumbnail for this file.

        Args:
            width: Optional thumbnail width
            **kwargs: Additional rendering options

        Returns:
            HTML string for thumbnail
        """
        # Default implementation - subclasses should override
        return f'<a href="{self.fullpath}" target="_blank">{self.basename}</a>'

    def __str__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}({self.path})"

    def __repr__(self) -> str:
        """Representation."""
        return self.__str__()

    @staticmethod
    def sort_list(items: list, sort_key: str = "n") -> list:
        """
        Sort a list of file items.

        Args:
            items: List of file items to sort
            sort_key: Sort key:
                - "n": by name
                - "s": by size
                - "t": by modification time
                - "x": by extension

        Returns:
            Sorted list
        """
        if not items:
            return items

        def get_sort_key(item):
            if sort_key == "n":
                return item.basename.lower()
            elif sort_key == "s":
                return item.size
            elif sort_key == "t":
                return item.mtime or 0
            elif sort_key == "x":
                return os.path.splitext(item.basename)[1].lower()
            else:
                return item.basename.lower()

        return sorted(items, key=get_sort_key)


def autodetect_file_type(path: str):
    """
    Auto-detect file type based on extension and content.

    Args:
        path: File path to check

    Returns:
        File type class or None if unknown

    Note:
        This is a placeholder - will be expanded as we add more file types.
    """
    if not os.path.exists(path):
        return None

    if os.path.isdir(path):
        # Check if it's a CASA table
        if os.path.exists(os.path.join(path, "table.dat")):
            return "casatable"
        return "directory"

    ext = os.path.splitext(path)[1].lower()

    if ext == ".fits":
        return "fits"
    elif ext in [".png", ".jpg", ".jpeg", ".gif", ".svg"]:
        return "image"
    elif ext in [".html", ".htm"]:
        return "html"
    elif ext == ".pdf":
        return "pdf"
    elif ext in [".txt", ".log", ".out", ".err", ".dat", ".csv"]:
        return "text"
    elif ext == ".ms":
        return "casatable"

    return None
