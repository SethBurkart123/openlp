# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008 OpenLP Developers                                   #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
"""
Templates for the webview-based print service system

This module provides a lightweight template registry and a common HTML
shell so adding new "themes" is straightforward. A template supplies:
 - an identifier and label
 - a CSS string
 - an optional item renderer (defaults to the table renderer)

All templates share the same base HTML (scaling, editing and bridge JS),
and render into a common table-based layout by default. This keeps the
template-specific work focused on CSS and (optionally) custom columns.
"""

from typing import Callable, Dict, List, Optional


class Template:
    """A print-service template definition."""

    def __init__(
        self,
        template_id: str,
        label: str,
        css: str,
        render_items: Optional[Callable] = None,
        html_template: Optional[str] = None,
    ):
        self.id = template_id
        self.label = label
        self.css = css
        self.render_items = render_items  # Callable or None (use default)
        self.html_template = html_template  # Optional custom HTML skeleton


class TemplateRegistry:
    """Simple in-module registry of templates."""

    _templates: Dict[str, Template] = {}

    @classmethod
    def register(cls, template: Template) -> None:
        cls._templates[template.id] = template

    @classmethod
    def get(cls, template_id: str) -> Optional[Template]:
        return cls._templates.get(template_id)

    @classmethod
    def all(cls) -> List[Template]:
        # Stable order for UI: sort by label then id
        return sorted(cls._templates.values(), key=lambda t: (t.label.lower(), t.id))

def get_base_template():
    """
    Common HTML shell shared by all templates. Injects a `{css}` block for
    theme styles and provides `{colgroup}`, `{table_headers}`, `{service_items}`
    placeholders for the default table-based renderer.
    """
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{css}</style>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <script>
        // Track if we're printing
        let isPrinting = false;
        
        // Dynamic scaling for paper preview
        function updateScale() {{
            // Don't scale if printing
            if (isPrinting) return;
            
            const scaleContainer = document.querySelector('.scale-container');
            const paperContainer = document.querySelector('.paper-container');
            if (!scaleContainer || !paperContainer) return;
            
            const windowWidth = window.innerWidth;
            const paperWidth = paperContainer.offsetWidth;
            const scale = Math.min(1, (windowWidth - 40) / paperWidth);
            
            scaleContainer.style.transform = `scale(${{scale}})`;
            scaleContainer.style.transformOrigin = 'top center';
            
            // Adjust container height to match scaled content
            const scaledHeight = paperContainer.offsetHeight * scale;
            scaleContainer.style.height = scaledHeight + 'px';
        }}
        
        // Prepare for printing
        function preparePrint() {{
            isPrinting = true;
            const scaleContainer = document.querySelector('.scale-container');
            if (scaleContainer) {{
                scaleContainer.style.transform = 'none';
                scaleContainer.style.height = 'auto';
            }}
        }}
        
        // Restore after printing
        function afterPrint() {{
            isPrinting = false;
            updateScale();
        }}
        
        // Update scale on window resize
        window.addEventListener('resize', updateScale);
        window.addEventListener('load', updateScale);
        
        // Handle print events
        window.addEventListener('beforeprint', preparePrint);
        window.addEventListener('afterprint', afterPrint);
        
        // Also handle when print dialog is triggered
        window.matchMedia('print').addListener(function(mql) {{
            if (mql.matches) {{
                preparePrint();
            }} else {{
                afterPrint();
            }}
        }});
        
        // Update scale when content changes
        setTimeout(updateScale, 100);
        
        // Unified editing system
        let editing = null;
        
        function edit(el, id, field, transform = x => x, validate = () => true) {{
            if (editing) return;
            editing = {{ el, original: el.innerHTML }};
            el.contentEditable = true;
            el.classList.add('editing');
            el.textContent = transform(el.textContent);
            el.focus();
            el.selectAll?.() || el.select?.() || (window.getSelection().selectAllChildren(el));
            
            const save = () => {{
                const val = el.textContent.trim();
                el.contentEditable = false;
                el.classList.remove('editing');
                editing = null;
                if (validate(val)) {{
                    window.bridge?.updateField(id, field, val);
                    if (field === 'custom_notes' && !val) el.classList.add('hidden');
                }} else el.innerHTML = editing.original;
            }};
            
            const cancel = () => {{
                el.contentEditable = false;
                el.classList.remove('editing');
                el.innerHTML = editing.original;
                editing = null;
            }};
            
            el.onkeydown = e => e.key === 'Enter' && !e.shiftKey ? (e.preventDefault(), save()) : e.key === 'Escape' ? cancel() : null;
            el.onblur = save;
        }}
        
        window.makeEditable = (el, id, field) => edit(el, id, field);
        window.addSectionHeader = id => window.bridge?.addSectionHeader(id, prompt('Header:'));
        window.handleItemCellDoubleClick = (e, id) => {{
            e.stopPropagation();
            let notes = e.currentTarget.querySelector('.custom-notes');
            if (!notes) {{
                notes = Object.assign(document.createElement('div'), {{
                    className: 'custom-notes editable visible',
                    textContent: ''
                }});
                e.currentTarget.querySelector('.item-content-wrapper').appendChild(notes);
            }}
            notes.classList.remove('hidden');
            edit(notes, id, 'custom_notes');
        }};
        window.handleTimeCellDoubleClick = (e, id) => {{
            e.stopPropagation();
            const span = e.currentTarget.querySelector('.time-range');
            if (span) edit(span, id, 'duration', 
                t => t.match(/\((\d+)min\)/)?.[1] || '5',
                v => !isNaN(parseInt(v)) && parseInt(v) > 0
            );
        }};
        
        // Initialize Qt WebChannel bridge
        window.addEventListener('load', () => {{
            if (typeof QWebChannel !== 'undefined') {{
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    window.bridge = channel.objects.bridge;
                }});
            }}
        }});
    </script>
</head>
<body>
    <div class="scale-container">
        <div class="paper-container">
            <div class="page">
                <header class="service-header">
                    <h1 class="service-title">{title}</h1>
                    <div class="service-datetime">{date}</div>
                </header>
                
                <main class="service-content">
                    <table class="service-table">
                        {colgroup}
                        <thead>
                            <tr>
                                {table_headers}
                            </tr>
                        </thead>
                        <tbody>
                            {service_items}
                        </tbody>
                    </table>
                </main>
                
                {footer_section}
            </div>
        </div>
    </div>
</body>
</html>"""

def get_professional_css():
    """
    Professional CSS styling for the service runsheet
    """
    return """
/* Professional Service Runsheet Styles */
@page {
    size: A4 portrait;
    margin: 1.5cm 2cm 0.5cm 2cm;
}

@page :first {
    margin-top: 1.5cm;
}

* {
    box-sizing: border-box;
}

html {
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 9pt;
    line-height: 1.2;
    color: #333;
    background: #e5e5e5;
    margin: 0;
    padding: 0;
    min-height: 100vh;
}

/* Container for screen preview */
body:not(.print-mode) {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 20px 0;
    overflow: auto;
}

/* Scale container for responsive scaling */
.scale-container {
    display: flex;
    justify-content: center;
    transform-origin: top center;
    width: 100%;
}

/* Paper container base styles */
.paper-container {
    background: white;
    box-shadow: 0 0 10px rgba(0,0,0,0.1);
    margin: 0 auto;
    position: relative;
    page-break-after: always;
}

/* Paper container for realistic preview (Portrait) */
.paper-container {
    width: 210mm;  /* A4 width portrait */
    min-height: auto;  /* Allow natural content flow */
}


/* Header Styles */
.service-header {
    text-align: center;
    margin-bottom: 15px;
    padding-bottom: 8px;
    border-bottom: 1px solid #ddd;
    flex-shrink: 0;
}

/* Service Content */
.service-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

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

/* Table Styles */
.service-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 5px;
    font-size: 8pt;
    flex: 1;
    /* Fixed layout avoids cumulative rounding overflow on print */
    table-layout: fixed;
}

.service-table thead th {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    padding: 6px 4px;
    text-align: left;
    font-weight: 600;
    color: #495057;
    text-transform: uppercase;
    font-size: 7pt;
    letter-spacing: 0.3px;
    /* Allow headers to wrap within tight columns without overflowing */
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
    hyphens: auto;
    line-height: 1.1;
}

.service-table tbody td {
    border: 1px solid #dee2e6;
    padding: 4px 4px;
    vertical-align: top;
    background-color: white;
}

/* Specific height constraint for item content */
.item-col {
    position: relative;
}

.item-content-wrapper {
    padding-right: 0;  /* No scrollbar needed */
}


.service-table tbody tr:nth-child(even) td {
    background-color: #f8f9fa;
}


/* Column sizing
   Widths are set via a dynamic <colgroup> generated from current columns.
   Keep only minimum constraints here so added columns don't wrap underneath. */
.time-col { min-width: 60px; }
.item-col {}
.person-col {}
.av-col {}
.vocals-col {}

/* Time Styling */
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
    background-color: rgba(0, 123, 255, 0.1);
    border: 1px solid #007bff;
    outline: none;
    border-radius: 2px;
    padding: 1px 3px;
    color: #2c3e50;
    font-weight: 600;
    min-width: 20px;
    display: inline-block;
}

/* Item Content */
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
    border-left: 1px solid #e9ecef;
}

.media-info {
    font-size: 6pt;
    color: #28a745;
    margin-top: 1px;
}

/* Section Headers */
.section-header {
    background-color: #e9ecef !important;
    font-weight: 600;
    color: #495057;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 7pt;
}

.section-header td {
    padding: 6px 4px !important;
    text-align: center;
    border-top: 1px solid #adb5bd !important;
}

/* Person and AV columns */
.person-cell, .av-cell {
    font-weight: 500;
    color: #495057;
    font-size: 7pt;
}

.person-cell.assigned {
    color: #2c3e50;
    font-weight: 600;
}

.av-cell.assigned {
    color: #2c3e50;
    font-weight: 600;
}

/* Custom notes */
.custom-notes {
    font-size: 7pt;
    color: #495057;
    margin-top: 2px;
    padding: 2px;
    border-radius: 2px;
    line-height: 1.3;
    word-wrap: break-word;
    white-space: pre-wrap;
}

.custom-notes.hidden {
    display: none;
}

.custom-notes.visible {
    display: block;
    min-height: 12px;
}

/* Person and AV columns */
.person-cell, .av-cell, .vocals-cell {
    font-weight: 500;
    color: #495057;
    font-size: 7pt;
}

.person-cell.assigned {
    color: #2c3e50;
    font-weight: 600;
}

.av-cell.assigned {
    color: #2c3e50;
    font-weight: 600;
}

.vocals-cell.assigned {
    color: #2c3e50;
    font-weight: 600;
}

/* Editable cells - clean styling */
.editable {
    cursor: pointer;
    position: relative;
    min-height: 12px;
    padding: 2px;
    word-wrap: break-word;
    white-space: pre-wrap;
}

.editable.editing {
    background-color: rgba(0, 123, 255, 0.1);
    border: 1px solid #007bff;
    outline: none;
    border-radius: 2px;
}

/* Table cells with proper height adjustment */
.service-table tbody td {
    border: 1px solid #dee2e6;
    padding: 4px 4px;
    vertical-align: top;
    background-color: white;
    height: auto;
    min-height: 20px;
}

/* Custom section headers */
.custom-header {
    background-color: #d1ecf1 !important;
    color: #0c5460;
}

/* Footer */
.footer-section {
    margin-top: auto;
    margin-bottom: 0;
    padding: 5px 0 0 0;
    border-top: 1px solid #dee2e6;
    flex-shrink: 0;
}

.footer-notes {
    font-size: 7pt;
    color: #6c757d;
    line-height: 1.3;
    margin-bottom: 0;
}

.footer-title {
    font-weight: 600;
    color: #495057;
    margin-bottom: 3px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-size: 7pt;
}

/* Special styling for different item types */
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

.item-custom {
    border-left: 4px solid #6f42c1;
}

/* Print-specific styles */
@media print {
    @page {
        size: A4 landscape;
        margin: 1.5cm 2cm 0.5cm 2cm;
    }
    
    html, body {
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
    }
    
    body {
        font-size: 10pt;
        background: white;
        display: block;
        padding: 0 !important;
    }
    
    .scale-container {
        transform: none !important;
        height: auto !important;
        display: block !important;
        width: 100% !important;
    }
    
    .paper-container {
        width: 100% !important;
        height: auto !important;
        min-height: auto !important;
        box-shadow: none !important;
        margin: 0 !important;
        page-break-after: always;
    }
    
    .page {
        padding: 0 !important;
        width: 100% !important;
        height: auto !important;
        min-height: auto !important;
        display: block !important;
    }
    
    /* Ensure content fills the page properly */
    .service-content {
        width: 100%;
        height: auto;
    }
    
.service-table {
    page-break-inside: auto;
    /* Prevent right-edge clipping from border/pixel rounding in print */
    width: calc(100% - 2px) !important;
}
    
    .service-table thead {
        display: table-header-group;
    }
    
    .service-table tbody tr {
        page-break-inside: avoid;
        page-break-after: auto;
    }
    
    .service-table tbody td {
        overflow: visible !important;
    }
    
    .item-content-wrapper {
        overflow: visible !important;
    }
    
    /* Keep section headers with following content */
    .section-header {
        page-break-after: avoid;
        page-break-inside: avoid;
    }
    
    /* Keep footer on same page if possible */
    .footer-section {
        page-break-inside: avoid;
        margin-top: auto;
    }
}

/* Landscape support removed: always portrait */

/* Screen-specific responsive design */
@media screen and (max-width: 800px) {
    body {
        padding: 10px;
    }
    
    .scale-container {
        transform: none !important;
    }
    
    .paper-container {
        width: calc(100vw - 20px);
        min-height: auto;
        box-shadow: none;
    }
    
    .page {
        padding: 1cm;
    }
}

/* Utility classes */
.text-center { text-align: center; }
.text-right { text-align: right; }
.font-bold { font-weight: 600; }
.text-muted { color: #6c757d; }
.text-small { font-size: 8pt; }
"""

def get_base_css():
    """
    Base page CSS shared by all templates.
    
    This includes only the essential layout, scaling, print handling, and
    structural styles that all templates need. Theme-specific colors,
    typography, and decorative styles should be in the template's own CSS.
    """
    return """
/* Base page styles - shared by all templates */
@page {
    size: A4 portrait;
    margin: 1.5cm 2cm 0.5cm 2cm;
}

@page :first {
    margin-top: 1.5cm;
}

* {
    box-sizing: border-box;
}

html {
    margin: 0;
    padding: 0;
}

body {
    background: #e5e5e5;
    margin: 0;
    padding: 0;
    min-height: 100vh;
}

/* Container for screen preview */
body:not(.print-mode) {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 20px 0;
    overflow: auto;
}

/* Scale container for responsive scaling */
.scale-container {
    display: flex;
    justify-content: center;
    transform-origin: top center;
    width: 100%;
}

/* Paper container base styles */
.paper-container {
    background: white;
    box-shadow: 0 0 10px rgba(0,0,0,0.1);
    margin: 0 auto;
    position: relative;
    page-break-after: always;
    width: 210mm;  /* A4 width portrait */
    min-height: auto;  /* Allow natural content flow */
}

/* Page content container */
.page {
    width: 100%;
    padding: 0.5cm;
    background: white;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
    min-height: auto;
    height: auto;
}

/* Header structure */
.service-header {
    text-align: center;
    margin-bottom: 15px;
    padding-bottom: 8px;
    border-bottom: 1px solid #ddd;
    flex-shrink: 0;
}

/* Service Content structure */
.service-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

/* Table base structure */
.service-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 5px;
    flex: 1;
    table-layout: fixed; /* Fixed layout avoids cumulative rounding overflow on print */
}

.service-table thead th {
    border: 1px solid #dee2e6;
    padding: 6px 4px;
    text-align: left;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
    hyphens: auto;
    line-height: 1.1;
}

.service-table tbody td {
    border: 1px solid #dee2e6;
    padding: 4px 4px;
    vertical-align: top;
    background-color: white;
    height: auto;
    min-height: 20px;
}

/* Column sizing base constraints */
.time-col { min-width: 60px; }

/* Item content structure */
.item-col {
    position: relative;
}

.item-content-wrapper {
    padding-right: 0;
}

/* Section headers base structure */
.section-header td {
    padding: 6px 4px !important;
    text-align: center;
    border-top: 1px solid #adb5bd !important;
}

/* Editable cells base functionality */
.editable {
    cursor: pointer;
    position: relative;
    min-height: 12px;
    padding: 2px;
    word-wrap: break-word;
    white-space: pre-wrap;
}

.editable.editing {
    background-color: rgba(0, 123, 255, 0.1);
    border: 1px solid #007bff;
    outline: none;
    border-radius: 2px;
}

/* Custom notes base structure */
.custom-notes {
    margin-top: 2px;
    padding: 2px;
    border-radius: 2px;
    line-height: 1.3;
    word-wrap: break-word;
    white-space: pre-wrap;
}

.custom-notes.hidden {
    display: none;
}

.custom-notes.visible {
    display: block;
    min-height: 12px;
}

/* Footer structure */
.footer-section {
    margin-top: auto;
    margin-bottom: 0;
    padding: 5px 0 0 0;
    border-top: 1px solid #dee2e6;
    flex-shrink: 0;
}

/* Time editing base structure */
.time-range.editing {
    background-color: rgba(0, 123, 255, 0.1);
    border: 1px solid #007bff;
    outline: none;
    border-radius: 2px;
    padding: 1px 3px;
    min-width: 20px;
    display: inline-block;
}

/* Print-specific styles */
@media print {
    @page {
        size: A4 landscape;
        margin: 1.5cm 2cm 0.5cm 2cm;
    }
    
    html, body {
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
    }
    
    body {
        background: white;
        display: block;
        padding: 0 !important;
    }
    
    .scale-container {
        transform: none !important;
        height: auto !important;
        display: block !important;
        width: 100% !important;
    }
    
    .paper-container {
        width: 100% !important;
        height: auto !important;
        min-height: auto !important;
        box-shadow: none !important;
        margin: 0 !important;
        page-break-after: always;
    }
    
    .page {
        padding: 0 !important;
        width: 100% !important;
        height: auto !important;
        min-height: auto !important;
        display: block !important;
    }
    
    .service-content {
        width: 100%;
        height: auto;
    }
    
    .service-table {
        page-break-inside: auto;
        width: calc(100% - 2px) !important; /* Prevent right-edge clipping from border/pixel rounding in print */
    }
    
    .service-table thead {
        display: table-header-group;
    }
    
    .service-table tbody tr {
        page-break-inside: avoid;
        page-break-after: auto;
    }
    
    .service-table tbody td {
        overflow: visible !important;
    }
    
    .item-content-wrapper {
        overflow: visible !important;
    }
    
    .section-header {
        page-break-after: avoid;
        page-break-inside: avoid;
    }
    
    .footer-section {
        page-break-inside: avoid;
        margin-top: auto;
    }
}

/* Screen-specific responsive design */
@media screen and (max-width: 800px) {
    body {
        padding: 10px;
    }
    
    .scale-container {
        transform: none !important;
    }
    
    .paper-container {
        width: calc(100vw - 20px);
        min-height: auto;
        box-shadow: none;
    }
}

/* Utility classes */
.text-center { text-align: center; }
.text-right { text-align: right; }
.font-bold { font-weight: 600; }
.text-muted { color: #6c757d; }
.text-small { font-size: 8pt; }
"""

def render_table_items(
    service_items,
    include_times=True,
    include_notes=True,
    include_slides=False,
    include_media_info=True,
    custom_data=None,
    columns=None,
):
    """
    Default table-based item renderer used by most templates.
    """
    html_rows = []
    custom_data = custom_data or {}
    
    # Use default columns if none provided
    if not columns:
        from openlp.core.ui.printserviceform import DefaultColumns
        columns = DefaultColumns.get_default_columns()
    
    # Add opening section if we have items
    if service_items:
        html_rows.append(f"""
        <tr class="section-header" id="header-start">
            <td colspan="{len(columns)}">Service Commences</td>
        </tr>
        """)
    
    for i, item in enumerate(service_items):
        item_id = item.get('id', f'item-{i}')
        item_custom = custom_data.get(item_id, {})
        
        # Check for custom section header before this item
        if item_custom.get('section_header'):
            html_rows.append(f"""
            <tr class="section-header custom-header" id="header-{item_id}">
                <td colspan="{len(columns)}">{item_custom['section_header']}</td>
            </tr>
            """)
        
        # Determine item type class
        item_type_class = f"item-{item['type']}" if item['type'] in ['songs', 'bibles', 'media', 'presentations', 'custom'] else 'item-custom'
        
        # Add context menu trigger for section headers
        context_menu_attr = f'oncontextmenu="addSectionHeader(\'{item_id}\'); return false;"'
        
        # Build row cells based on column configuration
        row_cells = []
        for column in columns:
            col_id = column['id']
            col_type = column['type']
            col_class = f"{col_id}-col"
            
            cell_content = ""
            cell_attrs = ""
            
            if col_id == 'time':
                # Time column
                if include_times:
                    cell_content = f"""
                    <div class="time-cell">
                        {item['start_time']}
                        <span class="time-range">({item['duration']}min)</span>
                    </div>
                    """
                cell_attrs = f'ondblclick="handleTimeCellDoubleClick(event, \'{item_id}\')"'
                
            elif col_id == 'item':
                # Item column - build item content
                cell_content = '<div class="item-content-wrapper">'
                cell_content += f'<div class="item-title">{item["title"]}</div>'
                
                # Map item types to natural names
                type_mapping = {
                    'songs': 'Song',
                    'bibles': 'Bible Verse',
                    'media': 'Media',
                    'presentations': 'Presentation',
                    'custom': ''  # No subtitle for custom items
                }
                
                # Only add type div if there's a label to show
                type_label = type_mapping.get(item['type'], item['type'].title())
                if type_label:
                    cell_content += f'<div class="item-type">{type_label}</div>'
                
                # Include original notes
                if include_notes and item['notes']:
                    cell_content += f'<div class="item-notes">{item["notes"]}</div>'
                
                # Include custom notes (hidden by default when empty)
                custom_notes = item_custom.get('custom_notes', '')
                if custom_notes:
                    cell_content += f'<div class="custom-notes editable visible" data-item-id="{item_id}">{custom_notes}</div>'
                else:
                    cell_content += f'<div class="custom-notes editable hidden" data-item-id="{item_id}"></div>'
                    
                if include_media_info and item['media_info']:
                    cell_content += f'<div class="media-info">{item["media_info"]}</div>'
                    
                if include_slides and item['slides']:
                    slides_text = '<br>'.join(item['slides'][:3])  # Show first 3 slides
                    if len(item['slides']) > 3:
                        slides_text += f'<br>... and {len(item["slides"]) - 3} more'
                    cell_content += f'<div class="item-slides">{slides_text}</div>'
                
                cell_content += '</div>'  # Close wrapper
                cell_attrs = f'ondblclick="handleItemCellDoubleClick(event, \'{item_id}\')"'
                
            else:
                # Custom/editable columns
                if col_type == 'editable':
                    # Get content for specific column types
                    if col_id == 'person':
                        cell_content = item_custom.get('person', '') or '&nbsp;'
                    elif col_id == 'av':
                        cell_content = item_custom.get('av_notes', '')
                        if not cell_content:
                            if item['type'] == 'media':
                                cell_content = "Video"
                            elif item['type'] == 'songs':
                                cell_content = "Slides"
                            elif item['type'] == 'presentations':
                                cell_content = "Presentation"
                            else:
                                cell_content = '&nbsp;'
                    elif col_id == 'vocals':
                        cell_content = item_custom.get('vocals', '') or '&nbsp;'
                    else:
                        # Generic custom column
                        cell_content = item_custom.get(col_id, '') or '&nbsp;'
                    
                    cell_attrs = f'ondblclick="makeEditable(this, \'{item_id}\', \'{col_id}\')"'
                    col_class += f" {col_id}-cell editable"
                else:
                    # Fixed/display-only columns
                    cell_content = item_custom.get(col_id, '') or '&nbsp;'
                    col_class += f" {col_id}-cell"
            
            row_cells.append(f'<td class="{col_class}" {cell_attrs}>{cell_content}</td>')
        
        html_rows.append(f"""
        <tr class="{item_type_class}" id="row-{item_id}" {context_menu_attr}>
            {''.join(row_cells)}
        </tr>
        """)
        
        # Add section breaks for longer services
        if i > 0 and (i + 1) % 8 == 0 and i < len(service_items) - 1:
            html_rows.append(f"""
            <tr class="section-header">
                <td colspan="{len(columns)}">Intermission</td>
            </tr>
            """)
    
    return '\n'.join(html_rows)


def generate_table_headers(columns):
    """
    Generate table headers based on column configuration
    """
    headers = []
    for column in columns:
        col_class = f"{column['id']}-col"
        headers.append(f'<th class="{col_class}">{column["name"]}</th>')
    return ''.join(headers)


def generate_colgroup(columns):
    """
    Generate a <colgroup> with widths that adapt to the current columns.
    Keeps Time at 10% (min 60px) and Item at 45%, distributes remaining
    space evenly across the other columns so nothing overflows or wraps.
    """
    if not columns:
        return ''

    # Baseline percentages matching the default layout
    time_pct = 10.0
    item_pct = 45.0

    # Identify indices of special columns
    time_idx = next((i for i, c in enumerate(columns) if c.get('id') == 'time'), None)
    item_idx = next((i for i, c in enumerate(columns) if c.get('id') == 'item'), None)

    # If one of the special columns is missing, re-balance to sensible defaults
    fixed_total = 0.0
    if time_idx is not None:
        fixed_total += time_pct
    if item_idx is not None:
        fixed_total += item_pct

    # Compute remaining width
    remaining = max(0.0, 100.0 - fixed_total)
    others = [c for c in columns if c.get('id') not in ('time', 'item')]
    per_other = (remaining / len(others)) if others else remaining

    col_elems = []
    for col in columns:
        cid = col.get('id')
        klass = f"{cid}-col"
        if cid == 'time' and time_idx is not None:
            width = time_pct
        elif cid == 'item' and item_idx is not None:
            width = item_pct
        else:
            width = per_other
        # Use percentage widths for reliable print layout
        col_elems.append(f'<col class="{klass}" style="width: {width:.4f}%;">')

    return '<colgroup>' + ''.join(col_elems) + '</colgroup>'


def get_footer_section(footer_notes):
    """
    Generate footer section HTML
    """
    if not footer_notes.strip():
        return ""
        
    return f"""
    <footer class="footer-section">
        <div class="footer-title">Service Notes</div>
        <div class="footer-notes">{footer_notes.replace(chr(10), '<br>')}</div>
    </footer>
    """


# --- Load built-in templates from subpackage -------------------------------

# Importing the package auto-registers all bundled templates
try:
    import openlp.core.ui.print_templates  # noqa: F401
except Exception:
    # Fail gracefully if import-time issues occur; the UI can still run,
    # but no templates will be available until this is fixed.
    pass

# Backwards-compatible aliases (in case of older imports)
get_professional_template = get_base_template
render_professional_items = render_table_items
