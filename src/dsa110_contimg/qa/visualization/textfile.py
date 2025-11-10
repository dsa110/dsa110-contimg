"""
Text file handling for QA visualization framework.

Provides TextFile class for viewing text files with line-by-line display,
grep, head/tail, and pattern extraction, similar to RadioPadre's TextFile.
"""

import io
import os
import re
from typing import List, Optional, Tuple, Union

try:
    from IPython.display import HTML, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    HTML = str

    def display(*args, **kwargs):
        pass

from .file import FileBase
from .render import render_error, render_preamble, render_table, rich_string, htmlize


class NumberedLineList:
    """
    List of numbered lines for text file display.

    Provides line-by-line access with line numbers, grep, head/tail operations.
    """

    MAX_SIZE = 1_000_000  # 1MB limit for full file loading

    def __init__(self, lines: Optional[List[Tuple[int, str]]] = None, title: Optional[str] = None):
        """
        Initialize a numbered line list.

        Args:
            lines: Optional list of (line_number, line_text) tuples
            title: Optional title
        """
        self._lines = lines or []
        self._title = title
        self._show_numbers = True

    @property
    def lines(self) -> List[Tuple[int, str]]:
        """Get all lines."""
        return self._lines

    @lines.setter
    def lines(self, value: Union[str, List[str], List[Tuple[int, str]]]):
        """Set lines from various formats."""
        if isinstance(value, str):
            self._lines = list(enumerate(value.split("\n"), start=1))
        elif isinstance(value, bytes):
            self._lines = list(enumerate(value.decode().split("\n"), start=1))
        elif isinstance(value, list):
            if value and isinstance(value[0], str):
                self._lines = list(enumerate(value, start=1))
            elif value and isinstance(value[0], tuple):
                self._lines = value
            else:
                raise TypeError(f"Invalid lines format: {type(value[0])}")
        else:
            raise TypeError(f"Invalid lines type: {type(value)}")

    def __len__(self) -> int:
        """Get number of lines."""
        return len(self._lines)

    def __iter__(self):
        """Iterate over lines."""
        for _, line in self._lines:
            yield line

    def __getitem__(self, item: Union[int, slice]) -> "NumberedLineList":
        """Get lines by index or slice."""
        if isinstance(item, slice):
            return NumberedLineList(self._lines[item], self._title)
        elif isinstance(item, int):
            return NumberedLineList([self._lines[item]], self._title)
        else:
            raise TypeError(f"Invalid index type: {type(item)}")

    def head(self, n: int = 10) -> List[Tuple[int, str]]:
        """Get first n lines."""
        return self._lines[:n]

    def tail(self, n: int = 10) -> List[Tuple[int, str]]:
        """Get last n lines."""
        return self._lines[-n:]

    def grep(self, pattern: Union[str, List[str]]) -> "NumberedLineList":
        """
        Filter lines matching pattern(s).

        Args:
            pattern: Regex pattern(s) to match

        Returns:
            New NumberedLineList with matching lines
        """
        if isinstance(pattern, str):
            patterns = [pattern]
        else:
            patterns = pattern

        compiled_patterns = [re.compile(p) for p in patterns]
        matching_lines = [
            (num, line)
            for num, line in self._lines
            if any(pattern.search(line) for pattern in compiled_patterns)
        ]

        return NumberedLineList(matching_lines, self._title)

    def extract(self, regexp: str, groups: Union[int, slice, List[int]] = slice(None)) -> List[List[str]]:
        """
        Extract data from lines using regex.

        Args:
            regexp: Regex pattern with groups
            groups: Which groups to extract (int, slice, or list of ints)

        Returns:
            List of extracted groups per matching line
        """
        pattern = re.compile(regexp)
        if isinstance(groups, int):
            groups = slice(groups, groups + 1)
        elif isinstance(groups, list):
            pass  # Use as-is
        elif not isinstance(groups, slice):
            groups = slice(None)

        results = []
        for _, line in self._lines:
            match = pattern.search(line)
            if match:
                matched_groups = match.groups()
                if isinstance(groups, slice):
                    results.append([matched_groups[i] for i in range(*groups.indices(len(matched_groups)))])
                else:
                    results.append([matched_groups[i] for i in groups])

        return results


class TextFile(FileBase, NumberedLineList):
    """
    Text file handler with line-by-line display capabilities.

    Supports head/tail display, grep, pattern extraction, and numbered line display.
    """

    MAX_SIZE = 1_000_000  # 1MB limit for full file loading

    def __init__(self, *args, **kwargs):
        """Initialize a text file handler."""
        FileBase.__init__(self, *args, **kwargs)
        NumberedLineList.__init__(self, [])
        self._loaded = False
        self._scan_impl()

    def _load_impl(self) -> None:
        """Load file lines into memory."""
        if self._loaded:
            return

        if not self.exists:
            self.lines = []
            self._loaded = True
            return

        size = os.path.getsize(self.fullpath)
        try:
            with open(self.fullpath, "r", encoding="utf-8", errors="replace") as f:
                if size <= self.MAX_SIZE:
                    # Load entire file
                    self.lines = f.readlines()
                else:
                    # Load head and tail only
                    head_lines = [f.readline() for _ in range(100)]
                    f.seek(size - self.MAX_SIZE // 2)
                    tail_lines = f.readlines()
                    # Adjust line numbers for tail
                    tail_start_num = size // 100  # Approximate
                    self.lines = (
                        [(i + 1, line) for i, line in enumerate(head_lines)]
                        + [(tail_start_num, "...\n")]
                        + [(tail_start_num + i + 1, line) for i, line in enumerate(tail_lines)]
                    )
                    self.description = f"large text ({self.size}), modified {self.mtime_str}"
                    return

            self.description = f"{len(self.lines)} lines, modified {self.mtime_str}"
            self._loaded = True

        except Exception as e:
            self.description = f"Error loading file: {e}"
            self.lines = []

    def _scan_impl(self) -> None:
        """Scan file for basic info."""
        if not self.exists:
            self.description = "File not found"
            return

        size = os.path.getsize(self.fullpath)
        self.size = size
        if size > self.MAX_SIZE:
            self.description = f"large text ({self._format_size(size)})"
        else:
            # Load to get line count
            self._load_impl()

    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @property
    def mtime_str(self) -> str:
        """Get modification time as string."""
        mtime = self.mtime
        if mtime:
            from datetime import datetime

            return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        return "?"

    def render_html(
        self,
        head: Optional[int] = None,
        tail: Optional[int] = None,
        full: bool = False,
        grep: Optional[Union[str, List[str]]] = None,
        number: Optional[bool] = None,
        title: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Render text file as HTML.

        Args:
            head: Number of lines from head to show
            tail: Number of lines from tail to show
            full: Show full file
            grep: Pattern(s) to filter lines
            number: Show line numbers (default: True)
            title: Optional title

        Returns:
            HTML string
        """
        self._load_impl()

        if number is None:
            number = self._show_numbers

        # Apply filters
        lines_to_show = self._lines
        if grep:
            lines_to_show = self.grep(grep).lines
        elif not full:
            if head or tail:
                head_lines = lines_to_show[:head] if head else []
                tail_lines = lines_to_show[-tail:] if tail else []
                if head_lines and tail_lines:
                    lines_to_show = head_lines + [(0, "...")] + tail_lines
                elif head_lines:
                    lines_to_show = head_lines
                elif tail_lines:
                    lines_to_show = tail_lines

        # Render HTML
        html_parts = [render_preamble(title=title or self.title)]

        if not lines_to_show:
            html_parts.append('<p class="qa-status-message">No lines to display</p>')
            return "".join(html_parts)

        # Render as table
        html_parts.append('<table class="qa-textfile-table" style="font-family: monospace; border-collapse: collapse;">')
        for line_num, line in lines_to_show:
            if line_num == 0:  # Separator
                html_parts.append('<tr><td colspan="2" style="text-align: center; color: #666;">...</td></tr>')
            else:
                line_html = htmlize(line.rstrip("\n"))
                if number:
                    html_parts.append(
                        f'<tr><td style="padding-right: 10px; color: #666; text-align: right;">{line_num}</td>'
                        f'<td>{line_html}</td></tr>'
                    )
                else:
                    html_parts.append(f"<tr><td>{line_html}</td></tr>")
        html_parts.append("</table>")

        return "".join(html_parts)

    def show(
        self,
        head: Optional[int] = 10,
        tail: Optional[int] = 10,
        full: bool = False,
        grep: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> None:
        """
        Display text file.

        Args:
            head: Number of lines from head to show
            tail: Number of lines from tail to show
            full: Show full file
            grep: Pattern(s) to filter lines
        """
        self.mark_shown()
        html = self.render_html(head=head, tail=tail, full=full, grep=grep, **kwargs)
        if HAS_IPYTHON:
            display(HTML(html))

    def _repr_html_(self) -> str:
        """HTML representation for Jupyter."""
        return self.render_html()

