# -*- coding: utf-8 -*-

"""
Compact print template: optimized to fit more items per page.

Smaller fonts, tighter paddings, subtle borders. Good for tech desks.
"""

from openlp.core.ui.printservice_templates import (
    Template,
    TemplateRegistry,
    render_table_items,
)


def get_css() -> str:
    return """
/* Compact theme overrides */
.service-title { font-size: 14pt; font-weight: 700; }
.service-table { font-size: 8pt; }
.service-table thead th { background: #f4f6f8; border: 1px solid #e6e8ea; color: #374151; padding: 4px 4px; }
.service-table tbody td { border: 1px solid #eceff1; padding: 3px 3px; }
.time-cell { font-weight: 700; color: #111; font-size: 7.5pt; }
.time-range { color: #6b7280; font-size: 7pt; font-weight: 600; }
.item-title { font-weight: 700; color: #111; font-size: 8pt; }
.item-type { color: #6b7280; font-size: 7pt; text-transform: uppercase; letter-spacing: .25px; }
.item-notes { color: #374151; font-style: italic; margin-top: 1px; font-size: 7.5pt; }
.media-info { color: #0f766e; font-size: 7pt; margin-top: 1px; }
.item-slides { color: #4b5563; font-size: 7pt; margin-top: 2px; padding-left: 5px; border-left: 1px solid #e5e7eb; }
.editable { cursor: text; padding: 1px; border-radius: 2px; }
.editable.editing { outline: 1px solid rgba(0,0,0,.2); background: rgba(0,0,0,.03); }
.section-header td { background: #eef2f7; color: #111827; font-weight: 800; text-align: center; padding: 4px; }
.custom-header td { background: #e0f2fe; color: #075985; }
.footer-section { margin-top: 6mm; border-top: 1px solid #e5e7eb; padding-top: 3mm; }
.footer-title { font-weight: 800; color: #111827; margin-bottom: 1.5mm; }
.footer-notes { color: #374151; font-size: 8pt; }
"""


TemplateRegistry.register(
    Template(
        template_id="compact",
        label="Compact",
        css=get_css(),
        render_items=render_table_items,
        html_template=None,
    )
)
