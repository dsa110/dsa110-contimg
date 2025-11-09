"""
CASA Measurement Set table browsing for QA visualization framework.

Provides CasaTable class for browsing CASA tables, similar to RadioPadre's
CasaTable functionality.
"""

import os
from typing import Optional, List, Union, Tuple
from contextlib import contextmanager

try:
    from IPython.display import display, HTML
    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False

    def display(*args, **kwargs):
        pass
    HTML = str

try:
    from casacore.tables import table
    HAS_CASACORE = True
except ImportError:
    HAS_CASACORE = False
    table = None

import numpy as np
from numpy.ma import masked_array

from .file import FileBase
from .render import render_table, render_error, render_status_message, rich_string


class CasaTable(FileBase):
    """
    CASA Measurement Set table browser.

    Provides access to CASA table columns, rows, and subtables with
    RadioPadre-like API.
    """

    class ColumnProxy:
        """
        Proxy object for accessing table columns with slicing support.
        """

        def __init__(self, casatable: "CasaTable", name: str, flagrow: bool = False, flag: bool = False):
            """
            Initialize column proxy.

            Args:
                casatable: Parent CasaTable instance
                name: Column name
                flagrow: Whether to apply FLAG_ROW
                flag: Whether to apply FLAG column
            """
            self._casatable = casatable
            self._name = name
            self._flagrow = flagrow
            self._flag = flag

        def __call__(self, start: int = 0, nrow: int = -1, incr: int = 1, flag: bool = False):
            """
            Get column data.

            Args:
                start: Starting row
                nrow: Number of rows (-1 for all)
                incr: Row increment
                flag: Whether to apply flags

            Returns:
                Column data (possibly masked if flags applied)
            """
            return self._casatable.getcol(
                self._name,
                start=start,
                nrow=nrow,
                rowincr=incr,
                flagrow=flag or self._flagrow,
                flag=flag or self._flag,
            )

        def __getitem__(self, item):
            """
            Get column data with slicing.

            Args:
                item: Slice or tuple of slices

            Returns:
                Sliced column data
            """
            if not isinstance(item, tuple):
                item = (item,)

            # Parse row slice
            row_slice = item[0] if len(item) > 0 else slice(None)
            if isinstance(row_slice, int):
                start = row_slice
                nrow = 1
                step = 1
            elif isinstance(row_slice, slice):
                start = row_slice.start or 0
                stop = row_slice.stop
                step = row_slice.step or 1
                nrow = stop - start if stop is not None else -1
            else:
                raise IndexError(f"Invalid row index: {row_slice}")

            # Additional slices for column dimensions
            blc = None
            trc = None
            incr = None
            if len(item) > 1:
                # Handle column dimension slicing
                # This is simplified - full implementation would handle multi-dimensional columns
                pass

            return self._casatable.getcol(
                self._name,
                start=start,
                nrow=nrow,
                rowincr=step,
                blc=blc,
                trc=trc,
                incr=incr,
                flagrow=self._flagrow,
                flag=self._flag,
            )

    def __init__(self, name: str, table=None, title: Optional[str] = None, parent=None, **kwargs):
        """
        Initialize CASA table browser.

        Args:
            name: Path to CASA table
            table: Optional pre-opened table object
            title: Optional display title
            parent: Optional parent object
        """
        self._table = table
        self._writeable = False
        self._columns = []
        self._nrows = 0
        self._keywords = {}
        self._subtables = []
        self._subtables_dict = {}
        self._dynamic_attributes = set()
        self._parent = parent
        self._error = None

        super().__init__(name, title=title, parent=parent)

        # Scan table if path exists
        if self.exists:
            self._scan_impl()

    @property
    def do_mirror(self):
        """CASA tables are mirrored when shown."""
        return self.was_shown

    @contextmanager
    def lock_table(self, write: bool = False):
        """
        Context manager for table access.

        Args:
            write: Whether to open for writing

        Yields:
            Table object
        """
        if not HAS_CASACORE:
            raise RuntimeError("casacore.tables not available")

        if self._table is None:
            # Open table
            tab = table(self.fullpath, readonly=not write)
            try:
                yield tab
            finally:
                tab.close()
        else:
            # Use existing table object
            yield self._table

    @property
    def wtable(self):
        """Get writable table context."""
        return self.lock_table(write=True)

    @property
    def rtable(self):
        """Get readable table context."""
        return self.lock_table(write=False)

    def _scan_impl(self) -> None:
        """Scan table and extract metadata."""
        if not HAS_CASACORE:
            self._error = "casacore.tables not available"
            self._description = rich_string(self._error)
            return

        if not self.exists:
            self._error = f"Table not found: {self.fullpath}"
            self._description = rich_string(self._error)
            return

        try:
            with self.rtable as tab:
                self._nrows = tab.nrows()
                self._columns = tab.colnames()
                self._keywords = tab.getkeywords()
                self._subtables = list(tab.getsubtables())
                self._writeable = tab.iswritable() if hasattr(tab, 'iswritable') else False

                # Create column proxies
                self._create_column_proxies(tab)

                # Create subtable proxies
                self._create_subtable_proxies()

                self._error = None
                self.size = f"{self._nrows} rows, {len(self._columns)} cols"
                self._description = (
                    f"{self._nrows} rows, {len(self._columns)} columns, "
                    f"{len(self._keywords)} keywords, {len(self._subtables)} subtables"
                )

        except Exception as e:
            self._error = f"Error scanning table: {e}"
            self._description = rich_string(self._error)

    def _create_column_proxies(self, tab) -> None:
        """Create column proxy attributes."""
        # Remove old dynamic attributes
        for attr in list(self._dynamic_attributes):
            if hasattr(self, attr):
                delattr(self, attr)
        self._dynamic_attributes.clear()

        flagrow = "FLAG_ROW" in self._columns
        flagcol = "FLAG" in self._columns

        # Create proxies for each column
        for name in self._columns:
            attrname = name
            while hasattr(self, attrname):
                attrname = attrname + "_"
            self._dynamic_attributes.add(attrname)
            setattr(self, attrname, CasaTable.ColumnProxy(self, name))

            # Create flagged versions for DATA/SPECTRUM columns
            if flagcol and (name.endswith("DATA") or name.endswith("SPECTRUM")):
                flag_attrname = f"{name}_F"
                while hasattr(self, flag_attrname):
                    flag_attrname = flag_attrname + "_"
                self._dynamic_attributes.add(flag_attrname)
                setattr(
                    self,
                    flag_attrname,
                    CasaTable.ColumnProxy(
                        self, name, flagrow=flagrow, flag=True),
                )

    def _create_subtable_proxies(self) -> None:
        """Create subtable proxy attributes."""
        self._subtables_dict = {}
        for path in self._subtables:
            name = os.path.basename(path)
            while hasattr(self, name):
                name = name + "_"
            self._subtables_dict[name] = path
            self._dynamic_attributes.add(name)
            setattr(self, name, path)

    def getcol(
        self,
        colname: str,
        start: int = 0,
        nrow: int = -1,
        rowincr: int = 1,
        blc: Optional[List[int]] = None,
        trc: Optional[List[int]] = None,
        incr: Optional[List[int]] = None,
        flagrow: bool = False,
        flag: bool = False,
    ):
        """
        Get column data.

        Args:
            colname: Column name
            start: Starting row
            nrow: Number of rows (-1 for all)
            rowincr: Row increment
            blc: Bottom-left corner for slicing
            trc: Top-right corner for slicing
            incr: Increment for slicing
            flagrow: Apply FLAG_ROW
            flag: Apply FLAG column

        Returns:
            Column data (possibly masked if flags applied)
        """
        if not HAS_CASACORE:
            raise RuntimeError("casacore.tables not available")

        with self.rtable as tab:
            if blc is None:
                # casacore.tables uses startrow, nrow, rowincr
                if nrow == -1:
                    coldata = tab.getcol(
                        colname, startrow=start, rowincr=rowincr)
                else:
                    coldata = tab.getcol(
                        colname, startrow=start, nrow=nrow, rowincr=rowincr)
            else:
                coldata = tab.getcolslice(
                    colname, blc=blc, trc=trc, incr=incr, startrow=start, nrow=nrow, rowincr=rowincr)

            if coldata is None:
                return None

            # Apply flags if requested
            if flagrow or flag:
                shape = coldata.shape if isinstance(
                    coldata, np.ndarray) else (len(coldata),)
                mask = np.zeros(shape, dtype=bool)

                if flagrow and "FLAG_ROW" in self._columns:
                    if nrow == -1:
                        fr = tab.getcol(
                            "FLAG_ROW", startrow=start, rowincr=rowincr)
                    else:
                        fr = tab.getcol("FLAG_ROW", startrow=start,
                                        nrow=nrow, rowincr=rowincr)
                    if fr.shape[0] == shape[0]:
                        mask[fr, ...] = True

                if flag and "FLAG" in self._columns:
                    if blc is None:
                        if nrow == -1:
                            fl = tab.getcol(
                                "FLAG", startrow=start, rowincr=rowincr)
                        else:
                            fl = tab.getcol(
                                "FLAG", startrow=start, nrow=nrow, rowincr=rowincr)
                    else:
                        fl = tab.getcolslice(
                            "FLAG", blc=blc, trc=trc, incr=incr, startrow=start, nrow=nrow, rowincr=rowincr)
                    if fl.shape == shape[-len(fl.shape):]:
                        mask[..., fl] = True

                return masked_array(coldata, mask)

            return coldata

    @property
    def nrows(self) -> int:
        """Get number of rows."""
        return self._nrows

    @property
    def columns(self) -> List[str]:
        """Get list of column names."""
        return self._columns.copy()

    @property
    def keywords(self) -> dict:
        """Get table keywords."""
        return self._keywords.copy()

    @property
    def subtables(self) -> List[str]:
        """Get list of subtable paths."""
        return self._subtables.copy()

    def show(self, nrows: int = 100) -> None:
        """
        Display table summary and sample rows.

        Args:
            nrows: Number of sample rows to display
        """
        self.mark_shown()

        if self._error:
            display(HTML(render_error(self._error, title="CASA Table Error")))
            return

        if not HAS_CASACORE:
            display(HTML(render_error("casacore.tables not available")))
            return

        try:
            # Table summary
            summary_html = self._render_summary_html()

            # Sample rows
            sample_html = self._render_sample_html(nrows=nrows)

            display(HTML(summary_html + sample_html))

        except Exception as e:
            error_msg = f"Error displaying table: {e}"
            display(HTML(render_error(error_msg, title="Display Error")))

    def _render_summary_html(self) -> str:
        """Render table summary as HTML."""
        html = f'<div class="qa-casatable-summary"><h3>{self.basename}</h3>'

        data = [
            ("Rows", f"{self._nrows:,}"),
            ("Columns", f"{len(self._columns)}"),
            ("Keywords", f"{len(self._keywords)}"),
            ("Subtables", f"{len(self._subtables)}"),
        ]

        html += render_table(data,
                             headers=["Property", "Value"], numbering=False)
        html += "</div>"

        # Column list
        if self._columns:
            html += '<div class="qa-casatable-columns"><h4>Columns</h4>'
            cols_data = [(i + 1, col) for i, col in enumerate(self._columns)]
            html += render_table(
                cols_data,
                headers=["#", "Column Name"],
                numbering=False,
            )
            html += "</div>"

        return html

    def _render_sample_html(self, nrows: int = 100) -> str:
        """Render sample rows as HTML."""
        if self._nrows == 0:
            return '<div class="qa-casatable-sample"><p>Table is empty</p></div>'

        sample_nrows = min(nrows, self._nrows)
        html = f'<div class="qa-casatable-sample"><h4>Sample Rows (first {sample_nrows})</h4>'

        try:
            # Get sample data from first few columns
            # Limit to first 5 columns for display
            sample_cols = self._columns[:5]
            sample_data = []

            with self.rtable as tab:
                for i in range(sample_nrows):
                    row_data = [str(i)]
                    for col in sample_cols:
                        try:
                            val = tab.getcell(col, i)
                            if isinstance(val, np.ndarray):
                                val_str = f"array({val.shape})"
                            elif isinstance(val, (list, tuple)):
                                val_str = f"{type(val).__name__}({len(val)})"
                            else:
                                val_str = str(val)[:50]  # Truncate long values
                            row_data.append(val_str)
                        except Exception:
                            row_data.append("N/A")
                    sample_data.append(row_data)

            headers = ["Row"] + sample_cols
            html += render_table(
                [(str(i), " | ".join(row[1:]))
                 for i, row in enumerate(sample_data)],
                headers=headers,
                numbering=False,
            )

        except Exception as e:
            html += f'<p class="qa-error">Error reading sample rows: {e}</p>'

        html += "</div>"
        return html

    def __getitem__(self, item):
        """
        Get table slice or subtable.

        Args:
            item: Slice for rows, or string for subtable name

        Returns:
            Table slice or subtable
        """
        if isinstance(item, str):
            # Subtable access
            if item in self._subtables_dict:
                path = self._subtables_dict[item]
                if isinstance(path, str):
                    # Lazy load subtable
                    self._subtables_dict[item] = CasaTable(path, parent=self)
                return self._subtables_dict[item]
            raise KeyError(f"Subtable not found: {item}")

        # Row slicing (simplified - would need query support for full implementation)
        if isinstance(item, slice):
            # Return a view - for now just return self
            # Full implementation would create a query-based view
            return self

        raise TypeError(f"Invalid index type: {type(item)}")

    def _repr_html_(self) -> str:
        """HTML representation for Jupyter."""
        self.show()
        return ""

    def __str__(self) -> str:
        """String representation."""
        return f"CasaTable({self.path}, {self._nrows} rows, {len(self._columns)} cols)"
