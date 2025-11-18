"""
File list management for QA visualization framework.

Provides FileList class for managing collections of files and directories,
similar to RadioPadre's FileList functionality.
"""

import os
from typing import Callable, List, Optional, Union

try:
    from IPython.display import HTML, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    # Dummy implementations for non-Jupyter environments

    def display(*args, **kwargs):
        pass

    HTML = str

from .executor import executor, ncpu
from .file import FileBase, autodetect_file_type
from .render import (
    RenderingProxy,
    render_preamble,
    render_status_message,
    render_table,
    render_titled_content,
)
from .settings_manager import settings
from .table import tabulate

# Import file type classes (lazy import to avoid circular dependencies)
_FITSFile = None
_CasaTable = None
_ImageFile = None
_TextFile = None
_HTMLFile = None
_PDFFile = None


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


def _get_imagefile_class():
    """Lazy import of ImageFile to avoid circular dependencies."""
    global _ImageFile
    if _ImageFile is None:
        from .imagefile import ImageFile

        _ImageFile = ImageFile
    return _ImageFile


def _get_textfile_class():
    """Lazy import of TextFile to avoid circular dependencies."""
    global _TextFile
    if _TextFile is None:
        from .textfile import TextFile

        _TextFile = TextFile
    return _TextFile


def _get_htmlfile_class():
    """Lazy import of HTMLFile to avoid circular dependencies."""
    global _HTMLFile
    if _HTMLFile is None:
        from .htmlfile import HTMLFile

        _HTMLFile = HTMLFile
    return _HTMLFile


def _get_pdffile_class():
    """Lazy import of PDFFile to avoid circular dependencies."""
    global _PDFFile
    if _PDFFile is None:
        from .pdffile import PDFFile

        _PDFFile = PDFFile
    return _PDFFile


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
                elif file_type == "image":
                    # Use ImageFile for image files
                    ImageFile = _get_imagefile_class()
                    items.append(ImageFile(item))
                elif file_type == "text":
                    # Use TextFile for text files
                    TextFile = _get_textfile_class()
                    items.append(TextFile(item))
                elif file_type == "html":
                    # Use HTMLFile for HTML files
                    HTMLFile = _get_htmlfile_class()
                    items.append(HTMLFile(item))
                elif file_type == "pdf":
                    # Use PDFFile for PDF files
                    PDFFile = _get_pdffile_class()
                    items.append(PDFFile(item))
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
            elif file_type == "other" and detected_type not in [
                "fits",
                "image",
                "directory",
                "casatable",
                "text",
                "html",
                "pdf",
            ]:
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
            return not (
                fnmatch.fnmatch(item.basename, pattern) or fnmatch.fnmatch(item.path, pattern)
            )

        return self.filter(matches)

    def show(self) -> None:
        """
        Display the file list as an HTML table.

        Renders the file list in Jupyter/IPython with file information.
        """
        self.mark_shown()

        if len(self) == 0:
            display(HTML(f'<p class="qa-status-message">No files found in {self.title}</p>'))
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

    def render_thumbnail_catalog(
        self,
        ncol: Optional[int] = None,
        mincol: int = 0,
        maxcol: int = 8,
        title: Optional[str] = None,
        titles: bool = True,
        buttons: bool = True,
        collapsed: Optional[bool] = None,
        **kwargs,
    ) -> str:
        """
        Render a thumbnail catalog (grid view) of all files in the list.

        Args:
            ncol: Fixed number of columns (None = auto)
            mincol: Minimum number of columns
            maxcol: Maximum number of columns
            title: Optional title for the catalog
            titles: Whether to show file titles
            buttons: Whether to show action buttons
            collapsed: Whether section starts collapsed
            **kwargs: Additional arguments passed to render_thumb()

        Returns:
            HTML string for the thumbnail catalog

        Example:
            >>> filelist.render_thumbnail_catalog(ncol=4)
        """
        if len(self) == 0:
            return render_status_message("No files to display", message_type="info")

        # Generate thumbnails
        # Create a simple wrapper class for HTML strings so they're not escaped
        class HTMLString:
            def __init__(self, html: str):
                self.html = html

            def render_html(self) -> str:
                return self.html

            def __str__(self) -> str:
                return self.html

        def _make_thumb(num_item):
            idx, item = num_item
            thumb_html = item.render_thumb(**kwargs)
            if titles:
                title_html = f'<div class="qa-thumb-title">{item.basename}</div>'
                thumb_html = f'<div class="qa-thumb-item">{thumb_html}{title_html}</div>'
            return HTMLString(thumb_html)

        # Use parallel processing if multiple CPUs available
        if ncpu() < 2:
            thumbs = list(map(_make_thumb, enumerate(self)))
        else:
            thumbs = list(executor().map(_make_thumb, enumerate(self)))

        if not thumbs:
            return render_status_message("No thumbnails generated", message_type="warning")

        # Determine number of columns
        if ncol is None:
            ncol = max(mincol, min(maxcol, len(self)))
        else:
            ncol = max(mincol, min(maxcol, ncol))

        # Create table from thumbnails
        thumb_table = tabulate(
            thumbs, ncol=ncol, mincol=mincol, maxcol=maxcol, zebra=False, align="center"
        )
        content_html = thumb_table.render_html()

        # Build title HTML
        title_html = f"<h3>{title or self.title}</h3>" if title or self.title else ""

        # Determine collapsed state
        if collapsed is None:
            try:
                collapsed = getattr(settings, "thumb", None) and getattr(
                    settings.thumb, "collapsed", False
                )
            except AttributeError:
                collapsed = False

        # Add CSS for thumbnail catalog
        css = """
        <style>
        .qa-thumb-item {
            display: inline-block;
            margin: 5px;
            padding: 5px;
            text-align: center;
            vertical-align: top;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
        .qa-thumb-item:hover {
            border-color: #58A6FF;
            background-color: #f0f0f0;
        }
        .qa-thumb-title {
            margin-top: 5px;
            font-size: 0.85em;
            color: #333;
            word-wrap: break-word;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .qa-thumb-item img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
        }
        .qa-thumb-item a {
            display: block;
            text-decoration: none;
            color: inherit;
        }
        </style>
        """

        # Render with collapsible section
        return (
            css
            + render_preamble()
            + render_titled_content(
                title_html=title_html,
                content_html=content_html,
                buttons_html="",
                collapsed=collapsed,
            )
        )

    @property
    def thumbs(self) -> RenderingProxy:
        """
        Property that returns a rendering proxy for thumbnail catalog.

        Usage:
            >>> filelist.thumbs.show()
            >>> filelist.thumbs(ncol=4).show()
            >>> filelist.thumbs(ncol=3, width=200).show()

        Returns:
            RenderingProxy for render_thumbnail_catalog()
        """
        return RenderingProxy(self, "render_thumbnail_catalog", "thumbs", arg0="ncol")

    def show_all(self, *args, **kwargs) -> None:
        """
        Call show() on all files in the list.

        Useful for batch viewing with the same parameters.

        Args:
            *args: Positional arguments passed to each file's show() method
            **kwargs: Keyword arguments passed to each file's show() method

        Example:
            >>> filelist.show_all()
            >>> filelist.fits.show_all(dual_window=True, scale="log")
        """
        if len(self) == 0:
            if HAS_IPYTHON:
                display(HTML('<div class="qa-status-message">0 files</div>'))
            else:
                print("0 files")
            return

        for item in self:
            try:
                item.show(*args, **kwargs)
            except Exception as e:
                # Display error but continue with other files
                error_msg = f"Error displaying {item.basename}: {e}"
                if HAS_IPYTHON:
                    from .render import render_error

                    display(HTML(render_error(error_msg)))
                else:
                    print(f"ERROR: {error_msg}")

    def __call__(self, *patterns: str) -> "FileList":
        """
        Filter files by pattern using callable syntax.

        Supports pattern matching with wildcards and exclusion patterns.

        Args:
            *patterns: One or more patterns to match
                - "*.fits": Match FITS files
                - "!*.tmp": Exclude temporary files
                - "-n": Sort by name (flags: n=name, s=size, t=time, x=extension, r=reverse)

        Returns:
            New FileList with filtered items

        Example:
            >>> fits_only = filelist("*.fits")
            >>> no_tmp = filelist("*.fits", "!*.tmp")
            >>> sorted_fits = filelist("*.fits", "-tn")  # Sort by time, then name
        """
        import fnmatch
        import itertools

        sort_flags = None
        files = []
        subsets = []

        # Process patterns
        for patt in itertools.chain(*[p.split() for p in patterns]):
            if patt.startswith("!"):
                # Exclusion pattern
                exclude_pattern = patt[1:]
                files = [
                    f
                    for f in self
                    if not (
                        fnmatch.fnmatch(f.basename, exclude_pattern)
                        or fnmatch.fnmatch(f.path, exclude_pattern)
                    )
                ]
                subsets.append(patt)
            elif patt.startswith("-"):
                # Sort flags
                sort_flags = patt[1:]
                subsets.append(f"sort: {sort_flags}")
            else:
                # Inclusion pattern
                matching = [
                    f
                    for f in self
                    if (fnmatch.fnmatch(f.basename, patt) or fnmatch.fnmatch(f.path, patt))
                ]
                if files:
                    # Intersection with previous matches
                    files = [f for f in files if f in matching]
                else:
                    files = matching
                subsets.append(patt)

        # If no patterns provided, return copy of self
        if not subsets:
            files = list(self)

        # Apply sorting if specified
        sort_key = sort_flags or self._sort

        # Create new FileList
        result = FileList(
            content=files,
            path=self.path,
            extcol=self._extcol,
            showpath=self._showpath,
            title=self._build_title(*subsets) if subsets else self.title,
            parent=self._parent,
            sort=sort_key,
        )
        return result

    def _build_title(self, *subsets: str) -> str:
        """
        Build a title from subset patterns.

        Args:
            *subsets: Subset pattern strings

        Returns:
            Title string
        """
        if not subsets:
            return self.title
        subset_str = ", ".join(subsets)
        return f"{self.title} [{subset_str}]"
