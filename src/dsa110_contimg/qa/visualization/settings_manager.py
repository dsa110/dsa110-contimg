"""
Settings management for QA visualization framework.

Provides hierarchical settings system similar to RadioPadre's settings manager.
"""

import os
import re
from collections import OrderedDict
from contextlib import contextmanager
from typing import Optional


class DocString(str):
    """Class used to identify documentation strings."""

    pass


class Section(OrderedDict):
    """A section of settings with documentation."""

    def __init__(self, name: str, doc: str = ""):
        super().__init__()
        self._name = name
        self._docstring = doc
        self._docs = {}

    def __getattribute__(self, name: str):
        if name[0] != "_" and name in self:
            return self[name]
        return super().__getattribute__(name)

    def __setattr__(self, key: str, value):
        if key[0] == "_":
            return super().__setattr__(key, value)
        if (
            isinstance(value, tuple)
            and len(value) == 2
            and isinstance(value[1], DocString)
        ):
            self._docs[key] = value[1]
            value = value[0]
        self[key] = value

    def get(self, default=None, **kw):
        """
        Get setting values with defaults.

        Args:
            default: Default value if setting not found
            **kw: Keyword arguments mapping setting names to values or None

        Returns:
            Single value if one kwarg, tuple if multiple
        """
        if not kw:
            raise RuntimeError(
                "Section.get() must be called with at least one keyword argument"
            )
        retval = []
        for key, value in kw.items():
            if value is None:
                value = self.get(key, default)
            retval.append(value)
        if len(retval) == 1:
            return retval[0]
        return tuple(retval)

    @contextmanager
    def __call__(self, **kw):
        """Context manager for temporary settings."""
        prev_values = {key: self[key] for key in kw.keys() if key in self}
        new_values = set(kw.keys()) - set(self.keys())
        self.update(**kw)
        try:
            yield
        finally:
            self.update(**prev_values)
            for key in new_values:
                del self[key]

    def __repr__(self) -> str:
        """String representation."""
        txt = ""
        for key, value in self.items():
            txt += f"{self._name}.{key} = {repr(value)}\n"
        return txt

    def show(self):
        """Display settings as HTML table."""
        try:
            from IPython.display import HTML, display
            from .render import render_table

            data = []
            data.append(("<B>" + self._name + "</B>", "", self._docstring))
            for key, value in self.items():
                doc = self._docs.get(key, "")
                data.append((f"{self._name}.{key}", repr(value), doc))

            html = render_table(
                data, headers=["Setting", "Value", "Description"], numbering=False
            )
            display(HTML(html))
        except ImportError:
            print(self.__repr__())


class SettingsManager:
    """Manager for hierarchical settings."""

    def __init__(self, name: str = "settings"):
        self._name = name
        self._sections = OrderedDict()

    def add_section(self, name: str, doc: str = "") -> Section:
        """
        Add a settings section.

        Args:
            name: Section name
            doc: Section documentation

        Returns:
            Section instance
        """
        section = Section(name, doc)
        self._sections[name] = section
        setattr(self, name, section)
        return section

    def __repr__(self) -> str:
        """String representation."""
        txt = ""
        for sec_name, section in self._sections.items():
            if isinstance(section, Section):
                for key, value in section.items():
                    txt += f"{self._name}.{sec_name}.{key} = {repr(value)}\n"
        return txt

    def show(self):
        """Display all settings as HTML table."""
        try:
            from IPython.display import HTML, display
            from .render import render_table

            data = []
            for sec_name, section in self._sections.items():
                if isinstance(section, Section):
                    data.append(
                        (
                            "<B>" + self._name + "." + sec_name + "</B>",
                            "",
                            section._docstring,
                        )
                    )
                    for key, value in section.items():
                        doc = section._docs.get(key, "")
                        data.append(
                            (f"{self._name}.{sec_name}.{key}", repr(value), doc)
                        )

            html = render_table(
                data, headers=["Setting", "Value", "Description"], numbering=False
            )
            display(HTML(html))
        except ImportError:
            print(self.__repr__())


class QAVisualizationSettingsManager(SettingsManager):
    """Settings manager for QA visualization framework."""

    def __init__(self, name: str = "settings"):
        super().__init__(name=name)
        D = DocString

        # General settings
        gen = self.add_section("gen", "General QA visualization settings")
        gen.twocolumn_list_width = 40, D(
            "File lists default to dual-column if names within this length"
        )
        gen.timeformat = "%H:%M:%S %b %d", D("Time format")
        gen.collapsible = True, D("Enable collapsible displays by default")
        gen.ncpu = 0, D("Number of CPU cores to use (0 = auto-detect)")
        gen.max_ncpu = 32, D("Max CPU cores when auto-detecting")

        # File settings
        files = self.add_section("files", "File listing settings")
        files.include = None, D("Filename patterns to include (None = all)")
        files.exclude = None, D("Patterns to exclude")
        files.include_dir = None, D("Directory patterns to include")
        files.exclude_dir = None, D("Directory patterns to exclude")
        files.include_empty = False, D("Include empty directories")
        files.show_hidden = False, D("Show hidden files/directories")

        # Display settings
        display = self.add_section("display", "Display settings")
        display.cell_width = 800, D("Jupyter cell width in pixels")
        display.window_width = 1024, D("Browser window width")
        display.window_height = 768, D("Browser window height")
        display.auto_reset = True, D("Auto-reset on window resize")

        # Plot settings
        plot = self.add_section("plot", "Plot rendering settings")
        plot.width = None, D("Fixed plot width in inches")
        plot.screen_dpi = 80, D("Plot DPI")

        # Thumbnail settings
        thumb = self.add_section("thumb", "Thumbnail settings")
        thumb.mincol = 2, D("Minimum columns in thumbnail view")
        thumb.maxcol = 4, D("Maximum columns in thumbnail view")
        thumb.width = 0, D("Default thumbnail width (0 = auto)")

        # FITS settings
        fits = self.add_section("fits", "FITS file settings")
        fits.colormap = "cubehelix", D("Default FITS colormap")
        fits.scale = "linear", D("Default FITS scaling")
        fits.vmin = None, D("Lower clip value")
        fits.vmax = None, D("Upper clip value")
        fits.max_js9_slice = 2048, D("Max slice size for large images")
        fits.js9_preview_size = 1024, D("Preview size for large images")

        # Text settings
        text = self.add_section("text", "Text file settings")
        text.head = 10, D("Default lines from head")
        text.tail = 10, D("Default lines from tail")
        text.fs = 0.8, D("Font size for text display")

        # HTML settings
        html = self.add_section("html", "HTML rendering settings")
        html.width = 1920, D("Default HTML canvas width")
        html.height = 1024, D("Default HTML canvas height")

    def finalize_settings(self):
        """Finalize settings from environment variables."""
        env_settings = os.environ.get("QA_VISUALIZATION_SETTINGS")
        if env_settings:
            for setting in env_settings.split(","):
                match = re.fullmatch(r"(.*)\.(.*)=(.*)", setting)
                if match:
                    section, name, value = match.groups()
                    sec = getattr(self, section, None)
                    if sec is None or not hasattr(sec, name):
                        print(f"Invalid QA_VISUALIZATION_SETTINGS entry: {setting}")
                    else:
                        # Try to convert value to appropriate type
                        try:
                            if value.lower() == "true":
                                value = True
                            elif value.lower() == "false":
                                value = False
                            elif value.isdigit():
                                value = int(value)
                            elif "." in value and value.replace(".", "").isdigit():
                                value = float(value)
                        except Exception:
                            pass
                        setattr(sec, name, value)
                        print(f"Set {section}.{name}={value}")


# Global settings instance
_settings = None


def get_settings() -> QAVisualizationSettingsManager:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = QAVisualizationSettingsManager()
        _settings.finalize_settings()
    return _settings


# Convenience access
settings = get_settings()
