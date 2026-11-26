"""Optional exporters (Phase 6): Google Sheets, Notion, static HTML.

Imports are lazy - only loads modules when explicitly called.
"""

from .html import export_html

__all__ = ["export_html"]


def export_sheets(*args, **kwargs):
    """Export to Google Sheets. Requires google-api-python-client, google-auth."""
    try:
        from .sheets import export_sheets as _export_sheets
    except ImportError as e:
        raise RuntimeError(
            "Google Sheets export requires optional dependencies. "
            "Install with: uv pip install -e '.[sheets]'"
        ) from e
    return _export_sheets(*args, **kwargs)


def export_notion(*args, **kwargs):
    """Export to Notion. Requires notion-client."""
    try:
        from .notion import export_notion as _export_notion
    except ImportError as e:
        raise RuntimeError(
            "Notion export requires optional dependencies. "
            "Install with: uv pip install -e '.[notion]'"
        ) from e
    return _export_notion(*args, **kwargs)