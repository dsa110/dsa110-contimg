"""
Layout utilities for QA visualization framework.

Provides title blocks, section headings, and navigation features,
similar to RadioPadre's layouts functionality.
"""

import os
from typing import List, Optional

try:
    from IPython.display import HTML, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    HTML = str

    def display(*args, **kwargs):
        pass


from .render import render_url

_ALL_SECTIONS = {}
_logo_image = ""
_icon_image = ""


def add_section(name: str):
    """Add a known section to the table of contents."""
    _ALL_SECTIONS[name] = name.lower().replace(" ", "_")


def render_bookmarks_bar(label: str, name: str) -> str:
    """
    Render a bookmarks bar with all available sections.

    Args:
        label: Section label
        name: Section name

    Returns:
        HTML string for bookmarks bar
    """
    return f"""
        <div>
            <a name="{label}"></a>
            <div class="qa-section-bookmarks" data-name="{name}" data-label="{label}"></div>
        </div>
        <script>
        if (typeof document !== 'undefined' && document.radiopadre_layouts) {{
            document.radiopadre_layouts.add_section();
        }}
        </script>
    """


def Title(
    title: str,
    sections: Optional[List[str]] = None,
    logo: Optional[str] = None,
    logo_width: int = 0,
    logo_padding: int = 8,
    icon: Optional[str] = None,
    icon_width: Optional[int] = None,
) -> None:
    """
    Render a title block.

    Args:
        title: Title text
        sections: Deprecated - sections are auto-registered
        logo: Optional logo image path
        logo_width: Logo width in pixels
        logo_padding: Padding around logo
        icon: Optional icon image path
        icon_width: Icon width in pixels
    """
    global _logo_image, _icon_image

    # Get root directory for display
    rootdir = os.getcwd()
    homedir = os.path.expanduser("~")
    if homedir[-1] != "/":
        homedir += "/"
    if rootdir.startswith(homedir):
        rootdir = rootdir[len(homedir) :]

    logo_html = ""
    logo_style = ""

    if logo and os.path.exists(logo):
        logo_url = render_url(logo)
        logo_width_attr = f' width="{logo_width}"' if logo_width else ""
        _logo_image = f'<img src="{logo_url}" alt=""{logo_width_attr}></img>'
        logo_style = f"padding-right: {logo_padding}px; vertical-align: middle; min-width: {logo_width + logo_padding}px"

    icon_html = ""
    if icon:
        if os.path.exists(icon):
            icon_url = render_url(icon)
        else:
            icon_url = icon
        icon_width_attr = f' width="{icon_width}"' if icon_width else ""
        _icon_image = f'<img src="{icon_url}" alt=""{icon_width_attr}></img>'
        icon_html = _icon_image

    html = f"""
        <div class="qa-title-block" style="display: table-row; margin-top: 0.5em; width: 100%">
            <div style="display: table-cell; {logo_style}">{_logo_image}</div>
            <div style="display: table-cell; vertical-align: middle; width: 100%">
                <div style="display: table; width: 100%">
                    <div style="display: table-row">
                        <div style="display: table-cell">
                            <div class="qa-notebook-title">{title}</div>
                        </div>
                    </div>
                    <div style="display: table-row;">
                        <div style="display: table-cell; width: 100%; padding-top: .2em">
                            <div class="qa-notebook-path">[{rootdir}]</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """

    if HAS_IPYTHON:
        display(HTML(html))


def Section(name: str, refreshable: bool = False) -> None:
    """
    Render a section heading with bookmarks bar.

    Args:
        name: Section name
        refreshable: If True, add refresh button
    """
    global _ALL_SECTIONS, _icon_image

    # Remove leading * if present (indicates refreshable)
    if name.startswith("*"):
        name = name[1:]
        refreshable = True

    if name not in _ALL_SECTIONS:
        add_section(name)

    label = _ALL_SECTIONS[name]

    # Bookmarks bar
    bookmarks_html = render_bookmarks_bar(label, name)

    # Refresh button
    refresh_html = ""
    if refreshable and _icon_image:
        refresh_html = f'<div style="float: left;">{_render_refresh_button(content=_icon_image)}</div>'

    html = f"""
        {bookmarks_html}
        <div style="display: table">
            <div style="display: table-row">
                <div style="display: table-cell; vertical-align: middle; padding-right: 4px">
                    {refresh_html}
                </div>
                <div style="display: table-cell; vertical-align: middle; font-size: 1.5em; font-weight: bold;">
                    {name}
                </div>
            </div>
        </div>
    """

    if HAS_IPYTHON:
        display(HTML(html))


def _render_refresh_button(
    content: Optional[str] = None, style: Optional[str] = None
) -> str:
    """
    Render a refresh button (internal use).

    Args:
        content: Button content (default: icon)
        style: Optional CSS style

    Returns:
        HTML string for refresh button
    """
    if content is None:
        content = "↻"
    if style is None:
        style = "padding: 2px 5px; cursor: pointer;"
    return f'<button onclick="location.reload()" style="{style}">{content}</button>'
