"""
Advanced table rendering for QA visualization framework.

Provides Table class with advanced styling, zebra striping, column width control,
and slicing support, similar to RadioPadre's Table functionality.
"""

from collections import OrderedDict
from typing import List, Optional, Union

try:
    from IPython.display import HTML, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    HTML = str

    def display(*args, **kwargs):
        pass


from .render import htmlize, rich_string


class Table:
    """
    Advanced table rendering with styling and slicing support.

    Supports zebra striping, column width control, cell-level styling,
    and row/column slicing.
    """

    def __init__(
        self,
        items: List[List[Union[str, "RichString"]]],
        ncol: int = 0,
        zebra: bool = True,
        align: str = "left",
        cw: Optional[Union[str, dict, List[float]]] = "auto",
        tw: Optional[Union[str, float]] = "auto",
        fs: Optional[float] = None,
        lh: Optional[float] = 1.5,
        styles: Optional[dict] = None,
    ):
        """
        Initialize a table.

        Args:
            items: List of rows, each row is a list of cells
            ncol: Fixed number of columns (0 = auto-detect)
            zebra: Enable zebra striping (alternating row colors)
            align: Text alignment ("left", "right", "center")
            cw: Column widths ("auto", "equal", dict, or list)
            tw: Table width ("auto" or float 0-1 for percentage)
            fs: Font size in em units
            lh: Line height multiplier
            styles: Optional custom styles dict
        """
        self._data = {}
        self._nrow = len(items)
        self._ncol = ncol
        self._styles = styles.copy() if styles else OrderedDict()

        # Set default styles
        if zebra:
            self.set_style("table-row-even", "background", "#D0D0D0")
            self.set_style("table-row-odd", "background", "#FFFFFF")
        elif zebra is False:
            self.set_style("table-row-even", "background", "transparent")
            self.set_style("table-row-odd", "background", "transparent")

        if align:
            self.set_style("table-cell", "text-align", align)

        if fs is not None:
            self.set_style("table", "font-size", f"{fs}em")
        if lh is not None:
            self.set_style("table", "line-height", f"{lh * (fs or 1)}em")

        # Process items and determine column count
        for irow, row in enumerate(items):
            self._ncol = max(len(row), self._ncol)
            for icol, item in enumerate(row):
                if item is None:
                    item = rich_string("")
                elif isinstance(item, str):
                    item = rich_string(item)
                self._data[(irow, icol)] = item

        # Process column widths
        if cw is not None:
            if cw == "auto":
                cw = {}
            elif cw == "equal":
                cw = {i: 1.0 / self._ncol for i in range(self._ncol)}
            elif isinstance(cw, list):
                cw = {i: w for i, w in enumerate(cw)}
            elif isinstance(cw, dict):
                pass  # Use as-is

            # Set column width styles
            for icol in range(self._ncol):
                width = cw.get(icol, "auto")
                if isinstance(width, (int, float)):
                    width = f"{width:.2%}"
                self.set_style(f"col{icol}", "width", width)

        # Set table width
        if tw is not None:
            if tw == "auto":
                if cw and any(isinstance(w, str) for w in cw.values()):
                    tw = "100%"
                elif cw and all(isinstance(w, (int, float)) for w in cw.values()):
                    tw = sum(cw.values())
                else:
                    tw = "auto"

            if isinstance(tw, (int, float)):
                self.set_style("table", "width", f"{tw:.1%}")
            elif tw:
                self.set_style("table", "width", tw)

        # Default table styles
        self.set_style("table", "border", "0px")
        self.set_style("table-cell", "vertical-align", "top")
        self.set_style("table-cell", "padding-left", "2px")
        self.set_style("table-cell", "padding-right", "2px")

    def set_style(self, element: str, attribute: str, value: Optional[str]) -> None:
        """
        Set a style attribute for an element.

        Args:
            element: Element name (e.g., "table", "table-cell", "col0")
            attribute: CSS attribute name
            value: CSS value (None to remove)
        """
        style = self._styles.setdefault(element, OrderedDict())
        if value is None:
            if attribute in style:
                del style[attribute]
        else:
            style[attribute] = value

    def get_styles(self, *elements: str) -> str:
        """
        Get combined styles for elements.

        Args:
            *elements: Element names

        Returns:
            CSS style string
        """
        styles = OrderedDict()
        for element in elements:
            if element in self._styles:
                styles.update(self._styles[element])
        return "; ".join([f"{attr}: {value}" for attr, value in styles.items()])

    def _get_cell_html(self, irow: int, icol: int) -> str:
        """Get HTML for a cell."""
        item = self._data.get((irow, icol), rich_string(""))
        if hasattr(item, "render_html"):
            return item.render_html()
        return htmlize(str(item))

    def render_html(self) -> str:
        """Render table as HTML."""
        table_style = self.get_styles("table")
        html_parts = [f'<div style="display: table; {table_style}">']

        for irow in range(self._nrow):
            evenodd = "table-row-odd" if irow % 2 else "table-row-even"
            row_style = self.get_styles("table-row", evenodd)
            html_parts.append(f'<div style="display: table-row; {row_style}">')
            for icol in range(self._ncol):
                cell_html = self._get_cell_html(irow, icol)
                col_style = self.get_styles("table-cell", f"col{icol}")
                html_parts.append(
                    f'<div style="display: table-cell; {col_style}">'
                    f"{cell_html}</div>"
                )
            html_parts.append("</div>")

        html_parts.append("</div>")
        return "".join(html_parts)

    def render_text(self) -> str:
        """Render table as plain text."""
        # Simple text rendering
        lines = []
        for irow in range(self._nrow):
            row_items = []
            for icol in range(self._ncol):
                item = self._data.get((irow, icol), rich_string(""))
                row_items.append(str(item))
            lines.append(" | ".join(row_items))
        return "\n".join(lines)

    def __getitem__(self, item: Union[int, slice, tuple]) -> "Table":
        """
        Slice table by rows and/or columns.

        Args:
            item: Row slice, column slice, or (row_slice, col_slice) tuple

        Returns:
            New Table with sliced data

        Example:
            >>> table[0:10]  # First 10 rows
            >>> table[:, 0:3]  # First 3 columns
            >>> table[0:10, 0:3]  # First 10 rows, first 3 columns
        """
        if isinstance(item, tuple) and len(item) == 2:
            row_slice, col_slice = item
        elif isinstance(item, (int, slice)):
            row_slice = item
            col_slice = slice(None)
        else:
            raise TypeError(f"Invalid index: {item}")

        # Convert slices to ranges
        def slice_to_range(s, max_val):
            if isinstance(s, int):
                return [s]
            start = s.start if s.start is not None else 0
            stop = s.stop if s.stop is not None else max_val
            step = s.step if s.step is not None else 1
            return list(range(start, stop, step))

        row_indices = slice_to_range(row_slice, self._nrow)
        col_indices = slice_to_range(col_slice, self._ncol)

        # Create new table with sliced data
        new_items = []
        for irow in row_indices:
            row = []
            for icol in col_indices:
                row.append(self._data.get((irow, icol), rich_string("")))
            new_items.append(row)

        return Table(
            new_items,
            ncol=len(col_indices),
            zebra=None,
            align=None,
            cw=None,
            tw=None,
            fs=None,
            lh=None,
            styles=self._styles,
        )

    def show(self) -> None:
        """Display table in Jupyter."""
        if HAS_IPYTHON:
            display(HTML(self.render_html()))

    def _repr_html_(self) -> str:
        """HTML representation for Jupyter."""
        return self.render_html()


def tabulate(
    items: List[Union[str, List[str]]],
    ncol: int = 0,
    mincol: int = 0,
    maxcol: int = 8,
    **kwargs,
) -> Table:
    """
    Create a table from a flat list of items.

    Args:
        items: List of items (strings or lists)
        ncol: Fixed number of columns (0 = auto)
        mincol: Minimum columns
        maxcol: Maximum columns
        **kwargs: Additional Table arguments

    Returns:
        Table instance

    Example:
        >>> tabulate(["a", "b", "c", "d"], ncol=2)
    """
    # If items is already a list of lists, use directly
    if items and isinstance(items[0], list):
        return Table(items, ncol=ncol, **kwargs)

    # Otherwise, break into rows
    N = len(items)
    if not ncol:
        ncol = max(mincol, min(maxcol, N))

    itemlist = list(items)
    tablerows = []

    while itemlist:
        tablerows.append(itemlist[:ncol])
        del itemlist[:ncol]

    return Table(tablerows, ncol=ncol, **kwargs)
