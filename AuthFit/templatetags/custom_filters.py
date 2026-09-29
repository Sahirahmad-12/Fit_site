# templatetags/custom_filters.py
# Add this filter alongside your existing safe_json

import json
from django import template
from django.utils.html import format_html

register = template.Library()


# ── Existing filter (keep as-is) ──────────────────────────────
@register.filter(is_safe=True)
def safe_json(value):
    """
    Renders a Python dict/list as a JSON literal safe for inline JS:
      onclick="openModal({{ r|safe_json }})"
    ⚠ This breaks when values contain single-quotes or HTML.
    Use data_json + openModalFromCard() instead.
    """
    from django.utils.safestring import mark_safe
    return mark_safe(json.dumps(value))


# ── New filter — safe for HTML data-* attributes ──────────────
@register.filter(is_safe=True)
def data_json(value):
    """
    Serialises value to JSON and HTML-escapes it so it's safe
    to embed in a data-* attribute:

      <div data-json="{{ r|data_json }}">

    In JS: JSON.parse(el.dataset.json) — no manual unescaping needed
    because the browser automatically decodes HTML entities when
    you read via .dataset or getAttribute().

    Unlike safe_json, this is safe even when values contain:
      - single quotes   '
      - double quotes   "
      - HTML tags       <script>
      - ampersands      &
    """
    from django.utils.safestring import mark_safe
    # json.dumps produces valid JSON; then we escape HTML special chars
    # so it's safe inside an HTML attribute value (double-quoted).
    raw = json.dumps(value, ensure_ascii=False)
    escaped = (
        raw
        .replace('&', '&amp;')    # must be first
        .replace('"', '&quot;')
        .replace("'", '&#x27;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
    return mark_safe(escaped)