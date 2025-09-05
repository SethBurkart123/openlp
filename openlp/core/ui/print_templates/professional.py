# -*- coding: utf-8 -*-

"""
Professional print template.

Provides clean, corporate styling with structured typography, 
consistent spacing, and professional color scheme.
"""

from openlp.core.ui.printservice_templates import (
    Template,
    TemplateRegistry,
    render_table_items,
)


def get_css() -> str:
    """Professional template styling with clean, corporate appearance."""
    return """
/* Professional theme styles */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 9pt;
    line-height: 1.2;
    color: #333;
}

/* Professional header styling */
.service-title {
    font-size: 18pt;
    font-weight: 600;
    color: #2c3e50;
    margin: 0 0 5px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.service-datetime {
    font-size: 11pt;
    color: #7f8c8d;
    font-weight: 500;
}

/* Professional table styling */
.service-table {
    font-size: 8pt;
}

.service-table thead th {
    background-color: #f8f9fa;
    font-weight: 600;
    color: #495057;
    text-transform: uppercase;
    font-size: 7pt;
    letter-spacing: 0.3px;
}

.service-table tbody tr:nth-child(even) td {
    background-color: #f8f9fa;
}

/* Professional time styling */
.time-cell {
    font-weight: 600;
    color: #2c3e50;
    text-align: center;
    font-family: 'Courier New', monospace;
    font-size: 7pt;
}

.time-range {
    display: block;
    font-size: 6pt;
    color: #6c757d;
    font-weight: normal;
}

.time-range.editing {
    color: #2c3e50;
    font-weight: 600;
}

/* Professional item content styling */
.item-title {
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 1px;
    font-size: 8pt;
}

.item-type {
    font-size: 6pt;
    color: #6c757d;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-bottom: 1px;
}

.item-notes {
    font-size: 7pt;
    color: #495057;
    font-style: italic;
    margin-top: 1px;
}

.item-slides {
    font-size: 6pt;
    color: #6c757d;
    margin-top: 2px;
    padding-left: 5px;
}

.media-info {
    font-size: 6pt;
    color: #28a745;
    margin-top: 1px;
}

/* Professional section headers */
.section-header {
    background-color: #e9ecef !important;
    font-weight: 600;
    color: #495057;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 7pt;
}

.custom-header {
    background-color: #d1ecf1 !important;
    color: #0c5460;
}

/* Professional assignment columns */
.person-cell, .av-cell, .vocals-cell {
    font-weight: 500;
    color: #495057;
    font-size: 7pt;
}

.person-cell.assigned, .av-cell.assigned, .vocals-cell.assigned {
    color: #2c3e50;
    font-weight: 600;
}

/* Professional custom notes */
.custom-notes {
    font-size: 7pt;
    color: #495057;
}

/* Professional footer */
.footer-title {
    font-weight: 600;
    color: #495057;
    margin-bottom: 3px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-size: 7pt;
}

.footer-notes {
    font-size: 7pt;
    color: #6c757d;
    line-height: 1.3;
    margin-bottom: 0;
}

/* Professional item type indicators */
.item-song {
    border-left: 4px solid #007bff;
}

.item-bible {
    border-left: 4px solid #28a745;
}

.item-media {
    border-left: 4px solid #ffc107;
}

.item-presentation {
    border-left: 4px solid #dc3545;
}

/* Professional print adjustments */
@media print {
    body {
        font-size: 10pt;
    }
}
"""


TemplateRegistry.register(
    Template(
        template_id="professional",
        label="Professional",
        css=get_css(),
        render_items=render_table_items,
        html_template=None,
    )
)
