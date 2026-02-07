# -*- coding: utf-8 -*-

"""
Minimal print template: clean, airy, and neutral.

Suitable for sharing with teams where readability matters more than
table density. Uses a larger base font and light borders.
"""

from openlp.core.ui.printservice_templates import (
    Template,
    TemplateRegistry,
    render_table_items,
)


def get_css() -> str:
    return """
/* Minimal theme overrides */
.service-title { font-weight: 700; letter-spacing: .2px; }
.service-table { font-size: 9.5pt; }
.service-table thead th { background: #fafafa; border-bottom: 1px solid #e5e5e5; color: #444; }
.service-table tbody td { border-bottom: 1px solid #f0f0f0; }
.service-table tbody tr:last-child td { border-bottom: 0; }
.time-cell { font-weight: 600; color: #111; }
.time-range { color: #888; font-size: 8.5pt; font-weight: 500; }
.item-title { font-weight: 600; color: #111; }
.item-type { color: #888; font-size: 8pt; text-transform: uppercase; letter-spacing: .2px; margin-top: 1px; }
.item-notes { color: #444; font-style: italic; margin-top: 2px; }
.media-info { color: #2f855a; font-size: 8pt; margin-top: 2px; }
.item-slides { color: #666; font-size: 8pt; margin-top: 3px; padding-left: 6px; border-left: 2px solid #f0f0f0; }
.editable { cursor: text; padding: 2px; border-radius: 2px; }
.editable.editing { outline: 2px solid rgba(0,0,0,.08); background: rgba(0,0,0,.02); }
.section-header td { background: #f7f7f7; font-weight: 700; color: #333; text-align: center; padding: 7px 6px; }
.custom-header td { background: #eef6ff; color: #1a365d; }
.footer-section { margin-top: 10mm; border-top: 1px solid #eee; padding-top: 4mm; }
.footer-title { font-weight: 700; color: #333; margin-bottom: 2mm; }
.footer-notes { color: #555; }
"""


TemplateRegistry.register(
    Template(
        template_id="minimal",
        label="Minimal",
        css=get_css(),
        render_items=render_table_items,
        html_template=None,
    )
)
