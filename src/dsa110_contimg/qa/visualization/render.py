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

