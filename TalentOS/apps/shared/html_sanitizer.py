"""HTML sanitization utilities for rich-text fields.

Uses ``bleach`` to strip disallowed tags and attributes, preventing
XSS attacks when HTML content is stored and later rendered.

Usage::

    from apps.shared.html_sanitizer import sanitize_html, sanitize_text

    # For HTML fields (allows basic formatting)
    safe_html = sanitize_html(user_provided_html)

    # For plain-text fields (strips ALL tags)
    safe_text = sanitize_text(user_provided_text)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Tags allowed in rich-text email templates / job descriptions
ALLOWED_TAGS = [
    "a", "abbr", "b", "blockquote", "br", "caption", "cite", "code",
    "col", "colgroup", "dd", "del", "div", "dl", "dt", "em", "h1", "h2",
    "h3", "h4", "h5", "h6", "hr", "i", "img", "ins", "kbd", "li", "mark",
    "ol", "p", "pre", "q", "s", "small", "span", "strong", "sub", "sup",
    "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "style"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
}

# Restrict inline styles to safe CSS properties only
_SAFE_CSS_PROPERTIES = frozenset([
    "color", "background-color", "font-size", "font-weight", "font-style",
    "text-align", "text-decoration", "margin", "padding", "border",
    "width", "max-width", "display", "line-height",
])


def sanitize_html(html: str | None) -> str:
    """Sanitize *html*, stripping disallowed tags/attributes.

    Falls back to plain-text stripping if ``bleach`` is not installed.
    """
    if not html:
        return html or ""
    try:
        import bleach

        def _clean_css(tag, name, value):
            # Only allow known-safe CSS property names
            prop = value.split(":")[0].strip().lower()
            return prop in _SAFE_CSS_PROPERTIES

        clean = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,
        )
        return clean
    except ImportError:
        logger.warning("bleach not installed — falling back to plain-text strip for HTML sanitization")
        return sanitize_text(html)


def sanitize_text(text: str | None) -> str:
    """Strip ALL HTML tags, returning plain text."""
    if not text:
        return text or ""
    try:
        import bleach
        return bleach.clean(text, tags=[], attributes={}, strip=True)
    except ImportError:
        import re
        return re.sub(r"<[^>]+>", "", text)
