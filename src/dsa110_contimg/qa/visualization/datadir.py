"""
Directory browsing for QA visualization framework.

Provides DataDir class and ls() function for browsing directories,
similar to RadioPadre's DataDir functionality.
"""

import os
import fnmatch
from typing import List, Optional, Union

from .filelist import FileList
from .file import FileBase, autodetect_file_type


def _match_pattern(path: str, pattern: str) -> bool:
    """
    Match path to pattern.

    If pattern contains a directory, matches full path, else only the basename.

    Args:
        path: Path to match
        pattern: Pattern to match against

    Returns:
        True if path matches pattern
    """
    if path.startswith("./"):
        path = path[2:]
    if pattern.startswith("./"):
        pattern = pattern[2:]
    if "/" in pattern:
        patt_dir, patt_name = os.path.split(pattern)
        path_dir, path_name = os.path.split(path)
        return fnmatch.fnmatch(path_dir, patt_dir) and fnmatch.fnmatch(path_name, patt_name)
    else:
        return fnmatch.fnmatch(os.path.basename(path), pattern)


def _matches(
    filename: str,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
) -> bool:
    """
    Check if filename matches include/exclude patterns.

    Args:
        filename: Filename to check
        include_patterns: Patterns that must match (if provided)
        exclude_patterns: Patterns that must not match

    Returns:
        True if filename matches criteria
    """
    if include_patterns and not any([_match_pattern(filename, patt) for patt in include_patterns]):
        return False
    return not any([_match_pattern(filename, patt) for patt in exclude_patterns])


class DataDir(FileList):
    """
    Directory browsing class that extends FileList.

    Provides directory scanning with pattern-based filtering.
    """

    def __init__(
        self,
        name: str,
        include: Optional[Union[str, List[str]]] = None,
        exclude: Optional[Union[str, List[str]]] = None,
        include_dir: Optional[Union[str, List[str]]] = None,
        exclude_dir: Optional[Union[str, List[str]]] = None,
        include_empty: bool = False,
        show_hidden: bool = False,
        recursive: bool = False,
        showpath: bool = False,
        title: Optional[str] = None,
        sort: str = "dxnt",
    ):
        """
        Initialize a directory browser.

        Args:
            name: Directory path to browse
            include: Include patterns (string or list)
            exclude: Exclude patterns (string or list)
            include_dir: Include directory patterns
            exclude_dir: Exclude directory patterns
            include_empty: Include empty directories
            show_hidden: Show hidden files (starting with .)
            recursive: Recursively scan subdirectories
            showpath: Show full paths in display
            title: Optional display title
            sort: Sort key ("d"=dirs first, "n"=name, "s"=size, "t"=time, "x"=extension)
        """
        self._recursive = recursive
        self._include_empty = include_empty
        self._show_hidden = show_hidden

        # Normalize patterns
        def normalize_patterns(patterns):
            if patterns is None:
                return []
            if isinstance(patterns, str):
                return [patterns]
            return list(patterns)

        self._include = normalize_patterns(include)
        self._include_dir = normalize_patterns(include_dir)
        self._exclude = normalize_patterns(exclude)
        self._exclude_dir = normalize_patterns(exclude_dir)

        # Add hidden file exclusion if not showing hidden
        if not self._show_hidden:
            self._exclude.append(".*")
            self._exclude_dir.append(".*")

        # Determine browse mode (no patterns = browse mode)
        self._browse_mode = include is None

        # Initialize FileList
        FileList.__init__(
            self,
            content=None,
            path=name,
            showpath=recursive or showpath,
            title=title or name,
            sort=sort,
        )

        # Scan directory
        self._scan_impl()

    def _scan_impl(self) -> None:
        """Scan directory and populate file list."""
        if not os.path.exists(self.fullpath):
            self[:] = []
            return

        if not os.path.isdir(self.fullpath):
            # Not a directory, treat as single file
            file_type = autodetect_file_type(self.fullpath)
            if file_type:
                self[:] = [FileBase(self.fullpath)]
            else:
                self[:] = []
            return

        items = []

        if self._recursive:
            # Recursive scan
            for root, dirs, files in os.walk(self.fullpath, followlinks=True):
                # Filter directories
                dirs_to_scan = []
                for name in dirs:
                    path = os.path.join(root, name)
                    if self._browse_mode:
                        if _matches(name, self._include + self._include_dir, self._exclude + self._exclude_dir):
                            dirs_to_scan.append(name)
                    else:
                        if _matches(path, self._include, self._exclude):
                            dirs_to_scan.append(name)

                # Check if directory is empty (if we care)
                for name in dirs_to_scan:
                    path = os.path.join(root, name)
                    if self._include_empty or os.listdir(path):
                        file_type = autodetect_file_type(path)
                        if file_type:
                            items.append(FileBase(path))

                # Filter files
                for name in files:
                    path = os.path.join(root, name)
                    # Check for symlinks to dirs
                    if os.path.isdir(path):
                        continue
                    # Check patterns
                    if self._browse_mode:
                        if _matches(name, self._include, self._exclude):
                            file_type = autodetect_file_type(path)
                            if file_type:
                                items.append(FileBase(path))
                    else:
                        if _matches(path, self._include, self._exclude):
                            file_type = autodetect_file_type(path)
                            if file_type:
                                items.append(FileBase(path))
        else:
            # Non-recursive scan
            try:
                entries = os.listdir(self.fullpath)
            except PermissionError:
                entries = []

            for name in entries:
                path = os.path.join(self.fullpath, name)

                # Skip if not showing hidden
                if not self._show_hidden and name.startswith("."):
                    continue

                # Check if directory
                if os.path.isdir(path):
                    # Check directory patterns
                    if self._browse_mode:
                        if _matches(name, self._include + self._include_dir, self._exclude + self._exclude_dir):
                            if self._include_empty or os.listdir(path):
                                file_type = autodetect_file_type(path)
                                if file_type:
                                    items.append(FileBase(path))
                    else:
                        if _matches(path, self._include, self._exclude):
                            if self._include_empty or os.listdir(path):
                                file_type = autodetect_file_type(path)
                                if file_type:
                                    items.append(FileBase(path))
                else:
                    # Check file patterns
                    if self._browse_mode:
                        if _matches(name, self._include, self._exclude):
                            file_type = autodetect_file_type(path)
                            if file_type:
                                items.append(FileBase(path))
                    else:
                        if _matches(path, self._include, self._exclude):
                            file_type = autodetect_file_type(path)
                            if file_type:
                                items.append(FileBase(path))

        # Sort items
        if self._sort:
            items = FileBase.sort_list(items, self._sort)

        # Set list content
        self._set_list(items, sort=None)  # Already sorted

    def rescan(self) -> None:
        """Rescan the directory."""
        self._scan_impl()


def ls(
    path: str = ".",
    include: Optional[Union[str, List[str]]] = None,
    exclude: Optional[Union[str, List[str]]] = None,
    recursive: bool = False,
    show_hidden: bool = False,
    sort: str = "dxnt",
) -> DataDir:
    """
    List directory contents (convenience function).

    Args:
        path: Directory path to list
        include: Include patterns
        exclude: Exclude patterns
        recursive: Recursively scan subdirectories
        show_hidden: Show hidden files
        sort: Sort key

    Returns:
        DataDir object with directory contents

    Example:
        >>> qa_dir = ls("state/qa")
        >>> qa_dir.show()
        >>> fits_files = qa_dir.fits
        >>> fits_files.show()
    """
    return DataDir(
        name=path,
        include=include,
        exclude=exclude,
        recursive=recursive,
        show_hidden=show_hidden,
        sort=sort,
    )

