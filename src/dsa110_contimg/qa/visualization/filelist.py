"""
File list management for QA visualization framework.

Provides FileList class for managing collections of files and directories,
similar to RadioPadre's FileList functionality.
"""

import os
from typing import List, Optional, Union, Callable

try:
    from IPython.display import display, HTML
    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    # Dummy implementations for non-Jupyter environments

    def display(*args, **kwargs):
        pass
    HTML = str

from .file import FileBase, autodetect_file_type
from .render import render_table, rich_string

# Import file type classes (lazy import to avoid circular dependencies)
_FITSFile = None
_CasaTable = None


def _get_fitsfile_class():
    """Lazy import of FITSFile to avoid circular dependencies."""
    global _FITSFile
    if _FITSFile is None:
        from .fitsfile import FITSFile
        _FITSFile = FITSFile
    return _FITSFile


def _get_casatable_class():
    """Lazy import of CasaTable to avoid circular dependencies."""
    global _CasaTable
    if _CasaTable is None:
        from .casatable import CasaTable
        _CasaTable = CasaTable
    return _CasaTable


class FileList(FileBase, list):
    """
    List-like container for file objects with display capabilities.

    Provides filtering, grouping, and HTML rendering of file collections.
    """

    def __init__(
        self,
        content: Optional[List[Union[str, FileBase]]] = None,
        path: str = ".",
        extcol: bool = False,
        showpath: bool = False,
        title: Optional[str] = None,
        parent=None,
        sort: str = "n",
    ):
        """
        Initialize a file list.

        Args:
            content: Optional list of file paths or FileBase objects
            path: Base path for relative paths
            extcol: Whether to show extension column
            showpath: Whether to show full paths
            title: Optional display title
            parent: Optional parent object
            sort: Sort key ("n"=name, "s"=size, "t"=time, "x"=extension)
        """
        self._extcol = extcol
        self._showpath = showpath
        self._parent = parent
        self._sort = sort or "n"
        self.nfiles = 0
        self.ndirs = 0
        self._fits = None
        self._images = None
        self._dirs = None
        self._tables = None
        self._others = None

        # Initialize FileBase
        FileBase.__init__(self, path or ".", title=title, parent=parent)

        # Initialize list
        list.__init__(self)

        if content is not None:
            self._set_list(content, sort)

    def _set_list(self, content: List[Union[str, FileBase]], sort: Optional[str] = None) -> None:
        """
        Set the list content from a list of paths or FileBase objects.

        Args:
            content: List of file paths or FileBase objects
            sort: Optional sort key
        """
        items = []
        for item in content:
            if isinstance(item, str):
                # Convert string paths to appropriate file type objects
                file_type = autodetect_file_type(item)
                if file_type == "casatable":
                    # Use CasaTable for CASA tables
                    CasaTable = _get_casatable_class()
                    items.append(CasaTable(item))
                elif file_type == "fits":
                    # Use FITSFile for FITS files
                    FITSFile = _get_fitsfile_class()
                    items.append(FITSFile(item))
                else:
                    items.append(FileBase(item))
            elif isinstance(item, FileBase):
                items.append(item)
            else:
                # Try to convert to string
                items.append(FileBase(str(item)))

        # Sort if requested
        if sort:
            items = FileBase.sort_list(items, sort)
        elif self._sort:
            items = FileBase.sort_list(items, self._sort)

        # Set list content
        self[:] = items

        # Count files and directories
        self.nfiles = 0
        self.ndirs = 0
        for item in self:
            if item.isdir:
                self.ndirs += 1
            else:
                self.nfiles += 1

        # Auto-detect if we should show paths
        if len(set([os.path.dirname(item.fullpath) for item in self])) > 1:
            self._showpath = True

        # Reset cached properties
        self._reset_summary()

    def _reset_summary(self) -> None:
        """Reset cached summary properties."""
        self._fits = None
        self._images = None
        self._dirs = None
        self._tables = None
        self._others = None

    @property
    def fits(self) -> "FileList":
        """Get a FileList containing only FITS files."""
        if self._fits is None:
            self._fits = self._filter_by_type("fits")
        return self._fits

    @property
    def images(self) -> "FileList":
        """Get a FileList containing only image files."""
        if self._images is None:
            self._images = self._filter_by_type("image")
        return self._images

    @property
    def dirs(self) -> "FileList":
        """Get a FileList containing only directories."""
        if self._dirs is None:
            self._dirs = self._filter_by_type("directory")
        return self._dirs

    @property
    def tables(self) -> "FileList":
        """Get a FileList containing only CASA tables."""
        if self._tables is None:
            self._tables = self._filter_by_type("casatable")
        return self._tables

    @property
    def others(self) -> "FileList":
        """Get a FileList containing other file types."""
        if self._others is None:
            self._others = self._filter_by_type("other")
        return self._others

    def _filter_by_type(self, file_type: str) -> "FileList":
        """
        Filter files by type.

        Args:
            file_type: Type to filter by ("fits", "image", "directory", "casatable", "other")

        Returns:
            New FileList with filtered items
        """
        filtered = []
        for item in self:
            detected_type = autodetect_file_type(item.fullpath)
            if file_type == "fits" and detected_type == "fits":
                filtered.append(item)
            elif file_type == "image" and detected_type == "image":
                filtered.append(item)
            elif file_type == "directory" and detected_type == "directory":
                filtered.append(item)
            elif file_type == "casatable" and detected_type == "casatable":
                filtered.append(item)
            elif file_type == "other" and detected_type not in ["fits", "image", "directory", "casatable"]:
                filtered.append(item)

        result = FileList(
            content=filtered,
            path=self.path,
            extcol=self._extcol,
            showpath=self._showpath,
            title=f"{self.title} [{file_type}]",
            parent=self._parent,
            sort=self._sort,
        )
        return result

    def filter(self, predicate: Callable[[FileBase], bool]) -> "FileList":
        """
        Filter files using a predicate function.

        Args:
            predicate: Function that takes a FileBase and returns bool

        Returns:
            New FileList with filtered items

        Example:
            >>> large_files = filelist.filter(lambda f: f.size > 1000000)
        """
        filtered = [item for item in self if predicate(item)]
        return FileList(
            content=filtered,
            path=self.path,
            extcol=self._extcol,
            showpath=self._showpath,
            title=f"{self.title} [filtered]",
            parent=self._parent,
            sort=self._sort,
        )

    def include(self, pattern: str) -> "FileList":
        """
        Filter files matching a pattern.

        Args:
            pattern: Filename pattern (supports wildcards)

        Returns:
            New FileList with matching items

        Example:
            >>> fits_only = filelist.include("*.fits")
        """
        import fnmatch

        def matches(item: FileBase) -> bool:
            return fnmatch.fnmatch(item.basename, pattern) or fnmatch.fnmatch(item.path, pattern)

        return self.filter(matches)

    def exclude(self, pattern: str) -> "FileList":
        """
        Filter out files matching a pattern.

        Args:
            pattern: Filename pattern (supports wildcards)

        Returns:
            New FileList without matching items

        Example:
            >>> no_hidden = filelist.exclude(".*")
        """
        import fnmatch

        def matches(item: FileBase) -> bool:
            return not (fnmatch.fnmatch(item.basename, pattern) or fnmatch.fnmatch(item.path, pattern))

        return self.filter(matches)

    def show(self) -> None:
        """
        Display the file list as an HTML table.

        Renders the file list in Jupyter/IPython with file information.
        """
        self.mark_shown()

        if len(self) == 0:
            display(
                HTML(f'<p class="qa-status-message">No files found in {self.title}</p>'))
            return

        # Prepare table data
        headers = ["#", "Name"]
        if self._showpath:
            headers.append("Path")
        if self._extcol:
            headers.append("Ext")
        headers.extend(["Type", "Size"])

        data = []
        for idx, item in enumerate(self, start=1):
            row = [str(idx), item.basename]
            if self._showpath:
                row.append(item.path)
            if self._extcol:
                ext = os.path.splitext(item.basename)[1]
                row.append(ext)
            # Type
            file_type = autodetect_file_type(item.fullpath)
            row.append(file_type or "unknown")
            # Size
            if item.isdir:
                row.append("DIR")
            else:
                size_str = self._format_size(item.size)
                row.append(size_str)

            data.append(row)

        # Render table
        html = render_table(
            data=[(row[0], " | ".join(row[1:])) for row in data],
            headers=headers,
            numbering=False,
            table_class="qa-filelist-table",
        )

        # Add summary
        summary = f"<p><strong>{self.title}</strong>: {len(self)} items ({self.nfiles} files, {self.ndirs} directories)</p>"
        display(HTML(summary + html))

    def _format_size(self, size: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def __str__(self) -> str:
        """String representation."""
        lines = [f"{self.title}:"]
        for idx, item in enumerate(self):
            lines.append(f"  {idx}: {item.path}")
        return "\n".join(lines)

    def _repr_html_(self) -> str:
        """HTML representation for Jupyter."""
        self.show()
        return ""
