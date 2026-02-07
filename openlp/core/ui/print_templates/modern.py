# -*- coding: utf-8 -*-

"""
Modern print template: contemporary look with a subtle accent color.

Good balance between readability and visual hierarchy.
"""

from openlp.core.ui.printservice_templates import (
    Template,
    TemplateRegistry,
    render_table_items,
)


def get_css() -> str:
    return """
/* Modern theme overrides */
.service-title { font-size: 19pt; font-weight: 800; color: #111827; letter-spacing: .2px; }
.service-table { font-size: 9pt; }
.service-table thead th { background: linear-gradient(180deg,#eef2ff, #e0e7ff); color: #3730a3; border-bottom: 1px solid #c7d2fe; }
.service-table tbody td { border-bottom: 1px solid #f1f5f9; }
.service-table tbody tr:nth-child(even) td { background: #fcfcff; }
.time-cell { font-weight: 800; color: #111827; }
.time-range { color: #6b7280; font-size: 8.5pt; font-weight: 700; }
.item-title { font-weight: 800; color: #111827; }
.item-type { color: #6b7280; font-size: 8pt; text-transform: uppercase; letter-spacing: .3px; margin-top: 2px; }
.item-notes { color: #374151; font-style: italic; margin-top: 2px; }
.media-info { color: #2563eb; font-size: 8pt; margin-top: 2px; }
.item-slides { color: #4b5563; font-size: 8pt; margin-top: 3px; padding-left: 6px; border-left: 2px solid #eef2ff; }
.editable { cursor: text; }
.editable.editing { outline: 2px solid rgba(99,102,241,.35); background: rgba(99,102,241,.06); }
.section-header td { background: #eef2ff; color: #3730a3; font-weight: 900; text-align: center; padding: 7px 6px; }
.custom-header td { background: #e0f2fe; color: #075985; }
.footer-section { margin-top: 10mm; border-top: 2px solid #f1f5f9; padding-top: 4mm; }
.footer-title { font-weight: 900; color: #1f2937; margin-bottom: 2mm; }
.footer-notes { color: #374151; }
"""


TemplateRegistry.register(
    Template(
        template_id="modern",
        label="Modern",
        css=get_css(),
        render_items=render_table_items,
        html_template=None,
    )
)
