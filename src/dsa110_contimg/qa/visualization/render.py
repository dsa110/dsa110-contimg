"""
HTML rendering utilities for QA visualization.

Provides functions for rendering tables, status messages, errors, and other
HTML content compatible with Jupyter/IPython display.
"""

from typing import List, Optional, Tuple, Union

try:
    from IPython.display import HTML, display

    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    # Dummy implementations for non-Jupyter environments
    HTML = str

    def display(*args, **kwargs):
        pass


def render_table(
    data: List[Tuple[str, str]],
    headers: Optional[List[str]] = None,
    numbering: bool = True,
    table_class: str = "qa-table",
) -> str:
    """
    Render a list of (key, value) tuples as an HTML table.

    Args:
        data: List of (key, value) tuples to display
        headers: Optional list of header strings (default: ["", ""])
        numbering: Whether to add row numbers
        table_class: CSS class for the table

    Returns:
        HTML string for the table

    Example:
        >>> data = [("Name", "Value"), ("Python", "3.11")]
        >>> html = render_table(data, headers=["Key", "Value"])
    """
    if headers is None:
        headers = ["", ""]

    html_parts = [f'<table class="{table_class}">']

    # Header row
    if headers:
        html_parts.append("<thead><tr>")
        if numbering:
            html_parts.append("<th>#</th>")
        for header in headers:
            html_parts.append(f"<th>{header}</th>")
        html_parts.append("</tr></thead>")

    # Body rows
    html_parts.append("<tbody>")
    for idx, (key, value) in enumerate(data, start=1):
        html_parts.append("<tr>")
        if numbering:
            html_parts.append(f"<td>{idx}</td>")
        html_parts.append(f"<td>{_escape_html(str(key))}</td>")
        html_parts.append(f"<td>{_escape_html(str(value))}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody>")
    html_parts.append("</table>")

    return "".join(html_parts)


def render_status_message(
    message: str,
    message_type: str = "info",
    div_class: str = "qa-status-message",
) -> str:
    """
    Render a status message with styling.

    Args:
        message: Message text to display
        message_type: Type of message ("info", "success", "warning", "error")
        div_class: CSS class for the message div

    Returns:
        HTML string for the status message

    Example:
        >>> html = render_status_message("QA complete", message_type="success")
    """
    type_classes = {
        "info": "qa-info",
        "success": "qa-success",
        "warning": "qa-warning",
        "error": "qa-error",
    }
    css_class = f"{div_class} {type_classes.get(message_type, 'qa-info')}"
    return f'<div class="{css_class}">{_escape_html(message)}</div>'


def render_error(
    error: Union[str, Exception],
    title: Optional[str] = None,
) -> str:
    """
    Render an error message.

    Args:
        error: Error message string or Exception object
        title: Optional title for the error

    Returns:
        HTML string for the error message

    Example:
        >>> html = render_error("File not found", title="Error")
    """
    if isinstance(error, Exception):
        error_msg = str(error)
        error_type = type(error).__name__
    else:
        error_msg = str(error)
        error_type = "Error"

    html_parts = ['<div class="qa-error">']
    if title:
        html_parts.append(f"<strong>{_escape_html(title)}</strong><br>")
    html_parts.append(f"<strong>{_escape_html(error_type)}:</strong> ")
    html_parts.append(_escape_html(error_msg))
    html_parts.append("</div>")

    return "".join(html_parts)


def render_preamble(title: Optional[str] = None) -> str:
    """
    Render HTML preamble with basic styling.

    Args:
        title: Optional title to include

    Returns:
        HTML string for the preamble

    Example:
        >>> html = render_preamble(title="QA Report")
    """
    html_parts = ['<div class="qa-preamble">']
    if title:
        html_parts.append(f"<h2>{_escape_html(title)}</h2>")
    html_parts.append("</div>")
    return "".join(html_parts)


def rich_string(
    content: str,
    div_class: Optional[str] = None,
) -> str:
    """
    Wrap content in a styled div.

    Args:
        content: Content to wrap
        div_class: Optional CSS class

    Returns:
        HTML string with wrapped content

    Example:
        >>> html = rich_string("Text", div_class="qa-highlight")
    """
    if div_class:
        return f'<div class="{div_class}">{content}</div>'
    return content


def _escape_html(text: str) -> str:
    """
    Escape HTML special characters.

    Args:
        text: Text to escape

    Returns:
        Escaped HTML string
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def display_html(html: str) -> None:
    """
    Display HTML in Jupyter/IPython.

    Args:
        html: HTML string to display

    Example:
        >>> display_html("<p>Hello</p>")
    """
    display(HTML(html))


def htmlize(text: str) -> str:
    """
    Convert text to HTML-safe format.

    Escapes HTML special characters and converts newlines to <br>.

    Args:
        text: Text to convert

    Returns:
        HTML-safe string

    Example:
        >>> htmlize("Hello <world>")
        'Hello &lt;world&gt;'
    """
    return (
        _escape_html(text)
        .replace("\n", "<br>")
        .replace("  ", "&nbsp;&nbsp;")
    )


def render_url(path: str) -> str:
    """
    Convert a file path to a URL for HTML display.

    Args:
        path: File system path

    Returns:
        URL string (file:// URL for absolute paths, relative path otherwise)
    """
    import os
    import urllib.parse

    if os.path.isabs(path):
        # Convert absolute path to file:// URL
        return urllib.parse.urljoin("file://", urllib.parse.quote(path))
    else:
        # Return relative path as-is
        return path


def render_titled_content(
    title_html: str,
    content_html: str,
    buttons_html: Optional[str] = None,
    collapsed: Optional[bool] = None,
) -> str:
    """
    Render content with title and optional collapsible section.

    Args:
        title_html: HTML for the title
        content_html: HTML for the content
        buttons_html: Optional HTML for action buttons
        collapsed: If True, section starts collapsed

    Returns:
        HTML string
    """
    collapsible_id = f"collapsible_{id(content_html)}"
    collapsed_class = "collapsed" if collapsed else ""
    collapse_style = "display: none;" if collapsed else ""

    html = f"""
    <div class="qa-collapsible-section {collapsed_class}">
        <div class="qa-section-header" onclick="toggleSection('{collapsible_id}')">
            {title_html}
            <span class="qa-toggle-icon">▼</span>
        </div>
        <div id="{collapsible_id}" class="qa-section-content" style="{collapse_style}">
            {content_html}
        </div>
    </div>
    <script>
    if (typeof toggleSection === 'undefined') {{
        function toggleSection(id) {{
            var content = document.getElementById(id);
            var header = content.previousElementSibling;
            var icon = header.querySelector('.qa-toggle-icon');
            if (content.style.display === 'none') {{
                content.style.display = 'block';
                icon.textContent = '▼';
                header.parentElement.classList.remove('collapsed');
            }} else {{
                content.style.display = 'none';
                icon.textContent = '▶';
                header.parentElement.classList.add('collapsed');
            }}
        }}
    }}
    </script>
    <style>
    .qa-collapsible-section {{
        margin: 10px 0;
        border: 1px solid #ddd;
        border-radius: 4px;
    }}
    .qa-section-header {{
        padding: 10px;
        background-color: #f5f5f5;
        cursor: pointer;
        user-select: none;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .qa-section-header:hover {{
        background-color: #e5e5e5;
    }}
    .qa-toggle-icon {{
        font-size: 0.8em;
        color: #666;
    }}
    .qa-section-content {{
        padding: 10px;
    }}
    .qa-collapsible-section.collapsed .qa-toggle-icon {{
        transform: rotate(-90deg);
    }}
    </style>
    """
    return html


def render_refresh_button(content: Optional[str] = None, style: Optional[str] = None) -> str:
    """
    Render a refresh button.

    Args:
        content: Button content (default: refresh icon)
        style: Optional CSS style

    Returns:
        HTML string for refresh button
    """
    if content is None:
        content = "↻"
    if style is None:
        style = "padding: 2px 5px; cursor: pointer; border: 1px solid #ccc; background: #f5f5f5;"
    return f'<button onclick="location.reload()" style="{style}">{content}</button>'


class RenderingProxy:
    """
    Proxy object for deferred rendering with method chaining.

    Allows methods like .thumbs() to be called with optional arguments
    and render only when needed.
    """

    def __init__(self, elem, method: str, name: str, arg0: Optional[str] = None, kwargs: Optional[dict] = None):
        """
        Initialize a rendering proxy.

        Args:
            elem: Element to render
            method: Method name to call
            name: Display name for the proxy
            arg0: Optional first positional argument name
            kwargs: Optional keyword arguments
        """
        self._elem = elem
        self._name = name
        self._method = method
        self._kw = kwargs or {}
        self._arg0 = arg0

    def __call__(self, *args, **kwargs):
        """
        Call the proxy with arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            New RenderingProxy with updated arguments
        """
        kw = self._kw.copy()
        kw.update(kwargs)

        # Handle single positional argument if arg0 is specified
        if self._arg0:
            if args:
                if len(args) > 1:
                    raise TypeError(f"at most one non-keyword argument expected in call to {self._name}()")
                kw[self._arg0] = args[0]

        return RenderingProxy(self._elem, self._method, self._name, arg0=self._arg0, kwargs=kw)

    def render_html(self, **kwargs) -> str:
        """
        Render the proxy as HTML.

        Args:
            **kwargs: Additional keyword arguments

        Returns:
            HTML string
        """
        kw = self._kw.copy()
        kw.update(kwargs)
        html = getattr(self._elem, self._method)(**kw)
        if isinstance(html, RenderingProxy):
            return html.render_html(**kw)
        return html

    def show(self, **kwargs) -> None:
        """
        Display the rendered HTML.

        Args:
            **kwargs: Additional keyword arguments
        """
        if HAS_IPYTHON:
            display(HTML(self.render_html(**kwargs)))
        else:
            print(self.render_html(**kwargs))

    def _repr_html_(self) -> str:
        """HTML representation for Jupyter."""
        return self.render_html()
