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
The new webview-based print service dialog using modern HTML/CSS
"""
import datetime
import html
import os
import tempfile

from PySide6 import QtCore, QtGui, QtWidgets, QtPrintSupport, QtWebChannel

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.display.webengine import WebEngineView
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.printservice_templates import (
    get_professional_template, get_professional_css, render_professional_items, get_footer_section,
    generate_table_headers
)

class ServiceTemplate:
    """Service runsheet template options"""
    PROFESSIONAL = "professional"


class ColumnType:
    """Column types for service runsheet"""
    FIXED = "fixed"          # Non-editable display only
    EDITABLE = "editable"    # Simple text editable
    TIME = "time"           # Special time column


class DefaultColumns:
    """Default column configuration"""
    @staticmethod
    def get_default_columns():
        return [
            {"id": "time", "name": "Time", "type": ColumnType.TIME, "removable": False},
            {"id": "item", "name": "Item", "type": ColumnType.FIXED, "removable": False},
            {"id": "person", "name": "Person", "type": ColumnType.EDITABLE, "removable": True},
            {"id": "av", "name": "Audio/Visual", "type": ColumnType.EDITABLE, "removable": True},
            {"id": "vocals", "name": "Vocals", "type": ColumnType.EDITABLE, "removable": True},
        ]


class WebChannelBridge(QtCore.QObject):
    field_updated = QtCore.Signal(str, str, str)
    section_header_added = QtCore.Signal(str, str)
    
    @QtCore.Slot(str, str, str)
    def updateField(self, item_id, field, value):
        self.field_updated.emit(item_id, field, value)
    
    @QtCore.Slot(str, str)
    def addSectionHeader(self, after_item_id, header_text):
        self.section_header_added.emit(after_item_id, header_text)


class PrintServiceForm(QtWidgets.QDialog, RegistryProperties):
    """
    The WebView-based print service form for creating professional service runsheets
    """
    
    @staticmethod
    def register_default_settings():
        """
        Register default settings for the webview print service form
        """
        default_settings = {
            'webview_print_service/title': 'Service Runsheet',
            'webview_print_service/template': ServiceTemplate.PROFESSIONAL,
            'webview_print_service/include_times': True,
            'webview_print_service/include_notes': True,
            'webview_print_service/include_slides': False,
            'webview_print_service/include_media_info': True,
            'webview_print_service/orientation': 'portrait',
            'webview_print_service/columns': DefaultColumns.get_default_columns(),
        }
        Settings.extend_default_settings(default_settings)
    
    def __init__(self):
        """
        Constructor
        """
        super(PrintServiceForm, self).__init__(Registry().get('main_window'),
                                                     QtCore.Qt.WindowType.WindowSystemMenuHint |
                                                     QtCore.Qt.WindowType.WindowTitleHint |
                                                     QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.setWindowTitle(translate('OpenLP.PrintServiceForm', 'Service Runsheet'))
        self.setWindowIcon(UiIcons().print)
        self.resize(1000, 700)
        
        # Register default settings if not already done
        self.register_default_settings()
        
        # Current template and options
        self.current_template = ServiceTemplate.PROFESSIONAL
        self.custom_data = {}  # Store custom assignments and notes
        self.columns = []  # Store column configuration
        self.column_checkboxes = {}  # Store column checkboxes
        self.column_widgets = []  # Store column row widgets for cleanup
        self.setup_ui()
        self.setup_web_channel()
        self.load_settings()
        self.connect_signals()
        self.load_existing_metadata()
        self.update_preview()

    def setup_ui(self):
        """
        Set up the user interface
        """
        # Main layout
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Toolbar
        self.toolbar = QtWidgets.QToolBar(self)
        self.toolbar.setIconSize(QtCore.QSize(22, 22))
        self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # Print button
        self.print_action = self.toolbar.addAction(UiIcons().print, 
                                                  translate('OpenLP.PrintServiceForm', 'Print'))
        
        # Export PDF button
        self.export_pdf_action = self.toolbar.addAction(UiIcons().save,
                                                       translate('OpenLP.PrintServiceForm', 'Export PDF'))
        
        self.toolbar.addSeparator()
        
        # Clear custom data button
        self.clear_action = self.toolbar.addAction(UiIcons().delete,
                                                  translate('OpenLP.PrintServiceForm', 'Clear Edits'))
        self.clear_action.setToolTip(translate('OpenLP.PrintServiceForm', 'Clear all custom assignments and notes'))
        
        # Template selector
        self.toolbar.addSeparator()
        self.template_label = QtWidgets.QLabel(translate('OpenLP.PrintServiceForm', 'Template:'))
        self.toolbar.addWidget(self.template_label)
        
        self.template_combo = QtWidgets.QComboBox()
        self.template_combo.addItem(translate('OpenLP.PrintServiceForm', 'Professional'), ServiceTemplate.PROFESSIONAL)
        self.toolbar.addWidget(self.template_combo)
        
        # Options button
        self.toolbar.addSeparator()
        self.options_button = QtWidgets.QToolButton()
        self.options_button.setText(translate('OpenLP.PrintServiceForm', 'Options'))
        self.options_button.setIcon(UiIcons().settings)
        self.options_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.options_button.setCheckable(True)
        self.toolbar.addWidget(self.options_button)
        

        
        # Orientation toggle
        self.toolbar.addSeparator()
        self.orientation_label = QtWidgets.QLabel(translate('OpenLP.PrintServiceForm', 'Orientation:'))
        self.toolbar.addWidget(self.orientation_label)
        
        self.orientation_combo = QtWidgets.QComboBox()
        self.orientation_combo.addItem(translate('OpenLP.PrintServiceForm', 'Portrait'), 'portrait')
        self.orientation_combo.addItem(translate('OpenLP.PrintServiceForm', 'Landscape'), 'landscape')
        self.toolbar.addWidget(self.orientation_combo)
        
        self.main_layout.addWidget(self.toolbar)

        # Splitter for preview and options
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        
        # WebView for preview
        self.webview = WebEngineView(self)
        self.webview.setMinimumWidth(600)
        self.webview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        # Set background color for better paper preview
        self.webview.setStyleSheet("QWidget { background-color: #e5e5e5; }")
        self.splitter.addWidget(self.webview)
        
        # Options panel
        self.options_widget = QtWidgets.QWidget()
        self.options_widget.setMaximumWidth(300)
        self.options_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding)
        self.options_widget.hide()
        self.setup_options_panel()
        self.splitter.addWidget(self.options_widget)
        
        self.main_layout.addWidget(self.splitter, 1)  # Add stretch factor of 1
        
        # Set splitter proportions - webview gets most space
        self.splitter.setStretchFactor(0, 1)  # webview
        self.splitter.setStretchFactor(1, 0)  # options panel
        
        # Status bar
        self.status_bar = QtWidgets.QStatusBar()
        self.main_layout.addWidget(self.status_bar)

    def setup_options_panel(self):
        """
        Set up the options panel
        """
        layout = QtWidgets.QVBoxLayout(self.options_widget)
        
        # Service title
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.PrintServiceForm', 'Service Title:')))
        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setText(translate('OpenLP.PrintServiceForm', 'Service Runsheet'))
        layout.addWidget(self.title_edit)
        
        # Service date
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.PrintServiceForm', 'Service Date:')))
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setDate(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        layout.addWidget(self.date_edit)
        
        # Service time
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.PrintServiceForm', 'Service Time:')))
        self.time_edit = QtWidgets.QTimeEdit()
        self.time_edit.setTime(QtCore.QTime(10, 0))
        layout.addWidget(self.time_edit)
        
        # Options group
        options_group = QtWidgets.QGroupBox(translate('OpenLP.PrintServiceForm', 'Include'))
        options_layout = QtWidgets.QVBoxLayout(options_group)
        
        self.include_times_check = QtWidgets.QCheckBox(translate('OpenLP.PrintServiceForm', 'Times and durations'))
        self.include_times_check.setChecked(True)
        options_layout.addWidget(self.include_times_check)
        
        self.include_notes_check = QtWidgets.QCheckBox(translate('OpenLP.PrintServiceForm', 'Service item notes'))
        self.include_notes_check.setChecked(True)
        options_layout.addWidget(self.include_notes_check)
        
        self.include_slides_check = QtWidgets.QCheckBox(translate('OpenLP.PrintServiceForm', 'Slide text'))
        options_layout.addWidget(self.include_slides_check)
        
        self.include_media_info_check = QtWidgets.QCheckBox(translate('OpenLP.PrintServiceForm', 'Media information'))
        self.include_media_info_check.setChecked(True)
        options_layout.addWidget(self.include_media_info_check)
        
        layout.addWidget(options_group)
        
        # Columns management
        columns_group = QtWidgets.QGroupBox(translate('OpenLP.PrintServiceForm', 'Columns'))
        columns_layout = QtWidgets.QVBoxLayout(columns_group)
        
        # Add new column input
        add_layout = QtWidgets.QHBoxLayout()
        self.new_column_edit = QtWidgets.QLineEdit()
        self.new_column_edit.setPlaceholderText(translate('OpenLP.PrintServiceForm', 'Add column...'))
        self.add_column_btn = QtWidgets.QPushButton('+')
        self.add_column_btn.setMaximumWidth(30)
        
        add_layout.addWidget(self.new_column_edit)
        add_layout.addWidget(self.add_column_btn)
        columns_layout.addLayout(add_layout)
        
        layout.addWidget(columns_group)
        
        # Connect signals
        self.new_column_edit.returnPressed.connect(self.add_simple_column)
        self.add_column_btn.clicked.connect(self.add_simple_column)
        
        # Footer notes
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.PrintServiceForm', 'Footer Notes:')))
        self.footer_edit = QtWidgets.QTextEdit()
        self.footer_edit.setMaximumHeight(100)
        layout.addWidget(self.footer_edit)
        
        layout.addStretch()

    def update_column_checkboxes(self):
        """Update column checkboxes when columns change"""
        if not hasattr(self, 'column_checkboxes'):
            return
        
        if not hasattr(self, 'column_widgets'):
            self.column_widgets = []
            
        # Clear existing checkboxes and row widgets
        for checkbox in self.column_checkboxes.values():
            checkbox.setParent(None)
        self.column_checkboxes.clear()
        
        for widget in self.column_widgets:
            widget.setParent(None)
        self.column_widgets.clear()
        
        # Find the columns group
        for widget in self.options_widget.findChildren(QtWidgets.QGroupBox):
            if widget.title() == translate('OpenLP.PrintServiceForm', 'Columns'):
                layout = widget.layout()
                
                # Only show columns that are currently enabled or available to be added back
                enabled_columns = [col for col in self.columns if col.get('removable', True)]
                
                # For columns that were removed, show them as available options (unchecked)
                default_removable = [col for col in DefaultColumns.get_default_columns() if col.get('removable', True)]
                removed_defaults = [col for col in default_removable if not any(ec['id'] == col['id'] for ec in enabled_columns)]
                
                # Show enabled columns + removed defaults (so they can be re-added)
                all_possible_columns = enabled_columns + removed_defaults
                
                insert_index = 0
                for column in all_possible_columns:
                    if column.get('removable', True):
                        # Create horizontal layout for checkbox + remove button
                        row_layout = QtWidgets.QHBoxLayout()
                        row_layout.setContentsMargins(0, 0, 0, 0)
                        
                        checkbox = QtWidgets.QCheckBox(column['name'])
                        is_enabled = any(col['id'] == column['id'] for col in enabled_columns)
                        checkbox.setChecked(is_enabled)
                        checkbox.toggled.connect(lambda checked, col_data=column: self.on_column_toggle(col_data, checked))
                        self.column_checkboxes[column['id']] = checkbox
                        
                        row_layout.addWidget(checkbox)
                        
                        # Add X button for all removable columns
                        remove_btn = QtWidgets.QPushButton('×')
                        remove_btn.setMaximumSize(20, 20)
                        remove_btn.setStyleSheet("QPushButton { color: red; font-weight: bold; }")
                        remove_btn.clicked.connect(lambda _, col_data=column: self.remove_column_permanently(col_data))
                        row_layout.addWidget(remove_btn)
                        
                        row_widget = QtWidgets.QWidget()
                        row_widget.setLayout(row_layout)
                        layout.insertWidget(insert_index, row_widget)
                        
                        # Track the widget for cleanup
                        self.column_widgets.append(row_widget)
                        insert_index += 1
                break

    def on_column_toggle(self, column_data, checked):
        """Handle column enable/disable"""
        if checked:
            # Add column if not present
            if not any(col['id'] == column_data['id'] for col in self.columns):
                self.columns.append(column_data)
        else:
            # Remove column
            self.columns = [col for col in self.columns if col['id'] != column_data['id']]
        
        self.save_settings()
        self.save_service_metadata()
        self.update_preview()

    def remove_column_permanently(self, column_data):
        """Permanently remove any column"""
        # Remove from active columns
        self.columns = [col for col in self.columns if col['id'] != column_data['id']]
        
        # Update UI and save
        self.update_column_checkboxes()
        self.save_settings()
        self.save_service_metadata()
        self.update_preview()

    def add_simple_column(self):
        """Add a new column from the text input"""
        name = self.new_column_edit.text().strip()
        if not name:
            return
        
        column_id = name.lower().replace(' ', '_')
        if any(col['id'] == column_id for col in self.columns):
            return
        
        new_column = {
            'id': column_id,
            'name': name,
            'type': ColumnType.EDITABLE,
            'removable': True
        }
        
        self.columns.append(new_column)
        self.new_column_edit.clear()
        self.update_column_checkboxes()
        self.save_settings()
        self.save_service_metadata()
        self.update_preview()

    def setup_web_channel(self):
        self.bridge = WebChannelBridge()
        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.webview.page().setWebChannel(self.channel)
        self.bridge.field_updated.connect(self.on_field_updated)
        self.bridge.section_header_added.connect(self.on_section_header_added)
    
    def connect_signals(self):
        # Action signals
        signals = [
            (self.print_action.triggered, self.print_service),
            (self.export_pdf_action.triggered, self.export_pdf),
            (self.clear_action.triggered, self.clear_custom_data),
            (self.template_combo.currentIndexChanged, self.on_template_changed),
            (self.options_button.toggled, self.toggle_options),
        ]
        
        # Preview update signals
        preview_widgets = [
            self.title_edit.textChanged, self.date_edit.dateChanged, self.time_edit.timeChanged,
            self.include_times_check.toggled, self.include_notes_check.toggled,
            self.include_slides_check.toggled, self.include_media_info_check.toggled,
            self.footer_edit.textChanged, self.orientation_combo.currentIndexChanged
        ]
        
        for signal, slot in signals:
            signal.connect(slot)
        for signal in preview_widgets:
            signal.connect(self.update_preview)
            signal.connect(self.save_service_metadata)  # Save to service file

    def load_settings(self):
        s = self.settings
        s.beginGroup('webview_print_service')
        
        # Simple widgets
        widgets = [
            ('title', self.title_edit, 'setText', 'text'),
            ('include_times', self.include_times_check, 'setChecked', 'isChecked'),
            ('include_notes', self.include_notes_check, 'setChecked', 'isChecked'),
            ('include_slides', self.include_slides_check, 'setChecked', 'isChecked'),
            ('include_media_info', self.include_media_info_check, 'setChecked', 'isChecked'),
        ]
        
        # Combo widgets (need findData)
        combos = [
            ('template', self.template_combo),
            ('orientation', self.orientation_combo),
        ]
        
        for key, widget, setter, _ in widgets:
            getattr(widget, setter)(s.value(key))
            
        for key, combo in combos:
            idx = combo.findData(s.value(key))
            if idx >= 0:
                combo.setCurrentIndex(idx)
        
        # Load columns configuration
        self.columns = s.value('columns')
        if not self.columns:  # Fallback if empty or None
            self.columns = DefaultColumns.get_default_columns()
        
        # Update column checkboxes after loading
        self.update_column_checkboxes()
                
        s.endGroup()

    def save_settings(self):
        s = self.settings
        s.beginGroup('webview_print_service')
        
        settings_map = {
            'title': self.title_edit.text(),
            'template': self.template_combo.currentData(),
            'include_times': self.include_times_check.isChecked(),
            'include_notes': self.include_notes_check.isChecked(),
            'include_slides': self.include_slides_check.isChecked(),
            'include_media_info': self.include_media_info_check.isChecked(),
            'orientation': self.orientation_combo.currentData(),
            'columns': self.columns,
        }
        
        for key, value in settings_map.items():
            s.setValue(key, value)
        s.endGroup()

    def on_template_changed(self):
        """
        Handle template selection change
        """
        self.current_template = self.template_combo.currentData()
        self.update_preview()

    def toggle_options(self, visible):
        """
        Toggle options panel visibility
        """
        self.options_widget.setVisible(visible)
    
    def on_field_updated(self, item_id, field, value):
        if item_id not in self.custom_data:
            self.custom_data[item_id] = {}
        self.custom_data[item_id][field] = value
        
        # Save to service item metadata immediately
        self.save_item_metadata(item_id, field, value)
        
        if field == 'duration':
            self.update_preview()
        
    def on_section_header_added(self, after_item_id, header_text):
        """
        Handle section header addition
        """
        # Find the item after which to add the header
        service_items = self.extract_service_data()
        for i, item in enumerate(service_items):
            if item.get('id', f'item-{i}') == after_item_id and i + 1 < len(service_items):
                next_item_id = service_items[i + 1].get('id', f'item-{i + 1}')
                if next_item_id not in self.custom_data:
                    self.custom_data[next_item_id] = {}
                self.custom_data[next_item_id]['section_header'] = header_text
                
                # Save to service item metadata
                self.save_item_metadata(next_item_id, 'section_header', header_text)
                
                self.update_preview()
                break

    def load_existing_metadata(self):
        """
        Load existing print service metadata from service items and service-level settings
        """
        self.custom_data = {}
        for i, item_data in enumerate(self.service_manager.service_items):
            service_item = item_data['service_item']
            item_id = f'item-{i}'
            
            # Use the dedicated print_service_data field
            if hasattr(service_item, 'print_service_data') and service_item.print_service_data:
                self.custom_data[item_id] = service_item.print_service_data.copy()
        
        # Load service-level print settings
        self.load_service_metadata()

    def refresh_metadata(self):
        """
        Refresh metadata from service items - useful when service changes
        """
        self.load_existing_metadata()
        self.update_preview()

    def save_item_metadata(self, item_id, field, value):
        """
        Save custom field data to the corresponding service item
        """
        try:
            item_index = int(item_id.split('-')[1])
        except (IndexError, ValueError):
            return
        
        if item_index >= len(self.service_manager.service_items):
            return
        
        service_item = self.service_manager.service_items[item_index]['service_item']
        service_item.print_service_data[field] = value
        self.service_manager.set_modified(True)

    def load_service_metadata(self):
        """
        Load service-level print settings from service manager
        """
        if hasattr(self.service_manager, 'print_service_metadata') and self.service_manager.print_service_metadata:
            metadata = self.service_manager.print_service_metadata
            
            # Load UI values from metadata
            if 'title' in metadata:
                self.title_edit.setText(metadata['title'])
            if 'date' in metadata:
                date = QtCore.QDate.fromString(metadata['date'], QtCore.Qt.DateFormat.ISODate)
                if date.isValid():
                    self.date_edit.setDate(date)
            if 'time' in metadata:
                time = QtCore.QTime.fromString(metadata['time'], QtCore.Qt.DateFormat.ISODate)
                if time.isValid():
                    self.time_edit.setTime(time)
            if 'include_times' in metadata:
                self.include_times_check.setChecked(metadata['include_times'])
            if 'include_notes' in metadata:
                self.include_notes_check.setChecked(metadata['include_notes'])
            if 'include_slides' in metadata:
                self.include_slides_check.setChecked(metadata['include_slides'])
            if 'include_media_info' in metadata:
                self.include_media_info_check.setChecked(metadata['include_media_info'])
            if 'orientation' in metadata:
                idx = self.orientation_combo.findData(metadata['orientation'])
                if idx >= 0:
                    self.orientation_combo.setCurrentIndex(idx)
            if 'footer_notes' in metadata:
                self.footer_edit.setPlainText(metadata['footer_notes'])
            if 'columns' in metadata:
                self.columns = metadata['columns']
                self.update_column_checkboxes()

    def save_service_metadata(self):
        """
        Save service-level print settings to service manager
        """
        metadata = {
            'title': self.title_edit.text(),
            'date': self.date_edit.date().toString(QtCore.Qt.DateFormat.ISODate),
            'time': self.time_edit.time().toString(QtCore.Qt.DateFormat.ISODate),
            'include_times': self.include_times_check.isChecked(),
            'include_notes': self.include_notes_check.isChecked(),
            'include_slides': self.include_slides_check.isChecked(),
            'include_media_info': self.include_media_info_check.isChecked(),
            'orientation': self.orientation_combo.currentData(),
            'footer_notes': self.footer_edit.toPlainText(),
            'columns': self.columns,
        }
        
        # Store in service manager
        if not hasattr(self.service_manager, 'print_service_metadata'):
            self.service_manager.print_service_metadata = {}
        self.service_manager.print_service_metadata = metadata
        self.service_manager.set_modified(True)

    def clear_service_metadata(self):
        """
        Clear service-level print settings (useful for new services)
        
        This method should be called when:
        - A new service is created
        - Before loading a different service
        
        It resets all print service settings to defaults.
        """
        if hasattr(self.service_manager, 'print_service_metadata'):
            self.service_manager.print_service_metadata = {}
        
        # Reset UI to defaults
        self.title_edit.setText(translate('OpenLP.PrintServiceForm', 'Service Runsheet'))
        self.date_edit.setDate(QtCore.QDate.currentDate())
        self.time_edit.setTime(QtCore.QTime(10, 0))
        self.footer_edit.clear()
        
        # Reset to default columns
        self.columns = DefaultColumns.get_default_columns()
        self.update_column_checkboxes()

    def update_preview(self):
        """
        Update the webview preview with current service data and template
        """
        html_content = self.generate_service_html()
        self.webview.setHtml(html_content)
        
        # Ensure scaling is applied after content loads
        def apply_scaling():
            self.webview.page().runJavaScript("if (typeof updateScale === 'function') { updateScale(); }")
        
        # Use a timer to ensure content is loaded
        QtCore.QTimer.singleShot(100, apply_scaling)

    def generate_service_html(self):
        """
        Generate the complete HTML for the service runsheet
        """
        service_data = self.extract_service_data()
        template_html = self.get_template_html()
        css = self.get_template_css()
        
        # Replace template variables
        footer_section = get_footer_section(self.footer_edit.toPlainText())
        orientation = self.orientation_combo.currentData()
        table_headers = generate_table_headers(self.columns)
        
        html_content = template_html.format(
            title=html.escape(self.title_edit.text()),
            date=self.date_edit.date().toString('dddd, MMMM dd, yyyy'),
            time=self.time_edit.time().toString('h:mm AP'),
            table_headers=table_headers,
            service_items=self.render_service_items(service_data),
            footer_notes=html.escape(self.footer_edit.toPlainText()),
            footer_section=footer_section,
            css=css,
            orientation=orientation
        )
        
        return html_content

    def extract_service_data(self):
        """
        Extract service data from the service manager
        """
        service_items = []
        current_time = self.time_edit.time()
        
        for i, item_data in enumerate(self.service_manager.service_items):
            service_item = item_data['service_item']
            item_id = f'item-{i}'
            
            # Calculate duration
            item_custom = self.custom_data.get(item_id, {})
            try:
                duration_minutes = int(item_custom.get('duration', 0))
            except (ValueError, TypeError):
                duration_minutes = 0
            
            # Calculate default duration if not custom set
            if not duration_minutes:
                if service_item.is_media() and service_item.media_length > 0:
                    duration_minutes = round((service_item.end_time - service_item.start_time) / 60 
                                            if service_item.end_time > 0 
                                            else service_item.media_length / 60)
                elif service_item.is_text():
                    duration_minutes = max(1, round(len(service_item.get_frames()) * 0.5))
                else:
                    duration_minutes = 2
            
            duration_minutes = max(1, duration_minutes)
            
            item_info = {
                'id': item_id,
                'title': service_item.get_display_title(),
                'type': service_item.name,
                'start_time': current_time.toString('h:mm'),
                'duration': int(duration_minutes),
                'end_time': current_time.addSecs(duration_minutes * 60).toString('h:mm'),
                'notes': service_item.notes if self.include_notes_check.isChecked() else '',
                'media_info': self.get_media_info(service_item) if self.include_media_info_check.isChecked() else '',
                'slides': self.get_slide_text(service_item) if self.include_slides_check.isChecked() else []
            }
            
            service_items.append(item_info)
            current_time = current_time.addSecs(duration_minutes * 60)
        
        return service_items

    def get_media_info(self, service_item):
        """
        Get media information for a service item
        """
        if service_item.is_media():
            if service_item.media_length > 0:
                return f"Duration: {datetime.timedelta(seconds=service_item.media_length)}"
        elif service_item.is_image():
            frame_count = len(service_item.get_frames())
            return f"{frame_count} image{'s' if frame_count != 1 else ''}"
        return ""

    def get_slide_text(self, service_item):
        """
        Get slide text for a service item
        """
        if not service_item.is_text():
            return []
        
        slides = []
        for slide in service_item.print_slides:
            slide_text = slide['text'].replace('\n', ' ').strip()
            if slide_text and slide_text not in slides:
                slides.append(slide_text)
        return slides

    def get_template_html(self):
        return get_professional_template()

    def get_template_css(self):
        return get_professional_css()

    def render_service_items(self, service_items):
        """
        Render service items into HTML based on current template
        """
        include_times = self.include_times_check.isChecked()
        include_notes = self.include_notes_check.isChecked()
        include_slides = self.include_slides_check.isChecked()
        include_media_info = self.include_media_info_check.isChecked()
        
        if self.current_template in [ServiceTemplate.PROFESSIONAL]:
            return render_professional_items(service_items, include_times, include_notes, include_slides, include_media_info, self.custom_data, self.columns)

    def print_service(self):
        """
        Print the service runsheet
        """
        printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.PrinterMode.HighResolution)
        
        # Set orientation based on current selection
        if self.orientation_combo.currentData() == 'landscape':
            printer.setPageOrientation(QtGui.QPageLayout.Orientation.Landscape)
        else:
            printer.setPageOrientation(QtGui.QPageLayout.Orientation.Portrait)
            
        # Set page size to A4
        printer.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
        
        # Set margins to match CSS
        margins = QtCore.QMarginsF(20, 15, 20, 5)  # 2cm, 1.5cm, 2cm, 0.5cm in mm
        printer.setPageMargins(margins, QtGui.QPageLayout.Unit.Millimeter)
        
        print_dialog = QtPrintSupport.QPrintDialog(printer, self)
        
        if print_dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # Add print mode class to body for CSS
            self.webview.page().runJavaScript("document.body.classList.add('print-mode')")
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_pdf_path = temp_file.name
            
            # Create page layout
            page_layout = QtGui.QPageLayout()
            page_layout.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
            page_layout.setMargins(margins)
            
            if self.orientation_combo.currentData() == 'landscape':
                page_layout.setOrientation(QtGui.QPageLayout.Orientation.Landscape)
            else:
                page_layout.setOrientation(QtGui.QPageLayout.Orientation.Portrait)
            
            def on_pdf_finished():
                try:
                    # Remove print mode class
                    self.webview.page().runJavaScript("document.body.classList.remove('print-mode')")
                    
                    self.status_bar.showMessage(
                        translate('OpenLP.PrintServiceForm', 'PDF generated for printing. You can now print from your PDF viewer.'), 5000)
                    
                    # Open the PDF file with the default application
                    import subprocess
                    import platform
                    
                    try:
                        if platform.system() == 'Darwin':  # macOS
                            subprocess.run(['open', temp_pdf_path])
                        elif platform.system() == 'Windows':
                            os.startfile(temp_pdf_path)
                        else:  # Linux
                            subprocess.run(['xdg-open', temp_pdf_path])
                    except Exception:
                        # If we can't open it automatically, just show the path
                        self.status_bar.showMessage(
                            translate('OpenLP.PrintServiceForm', f'PDF saved to: {temp_pdf_path}'), 5000)
                        
                except Exception as e:
                    self.status_bar.showMessage(
                        translate('OpenLP.PrintServiceForm', 'Print preparation failed'), 3000)
                finally:
                    # Disconnect the signal
                    try:
                        self.webview.page().pdfPrintingFinished.disconnect(on_pdf_finished)
                    except:
                        pass
            
            # Connect signal and generate PDF with proper layout
            self.webview.page().pdfPrintingFinished.connect(on_pdf_finished)
            self.webview.page().printToPdf(temp_pdf_path, page_layout)

    def export_pdf(self):
        """
        Export the service runsheet as PDF
        """
        from pathlib import Path
        
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 
            translate('OpenLP.PrintServiceForm', 'Export Service Runsheet'),
            str(Path.home() / f"Service_{self.date_edit.date().toString('yyyy-MM-dd')}.pdf"),
            translate('OpenLP.PrintServiceForm', 'PDF files (*.pdf)')
        )
        
        if file_path:
            # Add print mode class to body for CSS
            self.webview.page().runJavaScript("document.body.classList.add('print-mode')")
            
            # Create page layout with proper orientation
            page_layout = QtGui.QPageLayout()
            page_layout.setPageSize(QtGui.QPageSize(QtGui.QPageSize.PageSizeId.A4))
            
            # Set margins to match CSS (1.5cm top, 2cm sides, 0.5cm bottom)
            margins = QtCore.QMarginsF(20, 15, 20, 5)  # in mm
            page_layout.setMargins(margins)
            
            # Set orientation based on current selection
            if self.orientation_combo.currentData() == 'landscape':
                page_layout.setOrientation(QtGui.QPageLayout.Orientation.Landscape)
            else:
                page_layout.setOrientation(QtGui.QPageLayout.Orientation.Portrait)
            
            # Connect to the finished signal to show status
            def on_pdf_finished():
                try:
                    # Remove print mode class
                    self.webview.page().runJavaScript("document.body.classList.remove('print-mode')")
                    
                    self.status_bar.showMessage(
                        translate('OpenLP.PrintServiceForm', f'PDF exported to {file_path}'), 3000)
                except Exception:
                    self.status_bar.showMessage(
                        translate('OpenLP.PrintServiceForm', 'PDF export failed'), 3000)
                # Disconnect the signal after use
                try:
                    self.webview.page().pdfPrintingFinished.disconnect(on_pdf_finished)
                except:
                    pass
            
            # Connect the signal and start the PDF generation with proper layout
            self.webview.page().pdfPrintingFinished.connect(on_pdf_finished)
            self.webview.page().printToPdf(file_path, page_layout)

    def clear_custom_data(self):
        """
        Clear all custom assignments and notes
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            translate('OpenLP.PrintServiceForm', 'Clear Custom Data'),
            translate('OpenLP.PrintServiceForm', 'Are you sure you want to clear all custom assignments and notes?'),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # Clear local and service item data
            self.custom_data.clear()
            for item_data in self.service_manager.service_items:
                item_data['service_item'].print_service_data.clear()
            self.service_manager.set_modified(True)
            
            self.update_preview()
            self.status_bar.showMessage(translate('OpenLP.PrintServiceForm', 'Custom data cleared'), 3000)
    
    def closeEvent(self, event):
        """
        Handle close event
        """
        self.save_settings()
        self.save_service_metadata()
        super().closeEvent(event)

