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
from openlp.core.ui.webviewprintservice_templates import (
    get_professional_template, get_professional_css, render_professional_items, get_footer_section
)

from rich import print


class ServiceTemplate:
    """Service runsheet template options"""
    PROFESSIONAL = "professional"


class WebChannelBridge(QtCore.QObject):
    field_updated = QtCore.Signal(str, str, str)
    section_header_added = QtCore.Signal(str, str)
    
    @QtCore.Slot(str, str, str)
    def updateField(self, item_id, field, value):
        self.field_updated.emit(item_id, field, value)
    
    @QtCore.Slot(str, str)
    def addSectionHeader(self, after_item_id, header_text):
        self.section_header_added.emit(after_item_id, header_text)


class WebViewPrintServiceForm(QtWidgets.QDialog, RegistryProperties):
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
        }
        Settings.extend_default_settings(default_settings)
    
    def __init__(self):
        """
        Constructor
        """
        super(WebViewPrintServiceForm, self).__init__(Registry().get('main_window'),
                                                     QtCore.Qt.WindowType.WindowSystemMenuHint |
                                                     QtCore.Qt.WindowType.WindowTitleHint |
                                                     QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.setWindowTitle(translate('OpenLP.WebViewPrintServiceForm', 'Service Runsheet'))
        self.setWindowIcon(UiIcons().print)
        self.resize(1000, 700)
        
        # Register default settings if not already done
        self.register_default_settings()
        
        # Current template and options
        self.current_template = ServiceTemplate.PROFESSIONAL
        self.custom_data = {}  # Store custom assignments and notes
        self.setup_ui()
        self.setup_web_channel()
        self.load_settings()
        self.connect_signals()
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
                                                  translate('OpenLP.WebViewPrintServiceForm', 'Print'))
        
        # Export PDF button
        self.export_pdf_action = self.toolbar.addAction(UiIcons().save,
                                                       translate('OpenLP.WebViewPrintServiceForm', 'Export PDF'))
        
        self.toolbar.addSeparator()
        
        # Clear custom data button
        self.clear_action = self.toolbar.addAction(UiIcons().delete,
                                                  translate('OpenLP.WebViewPrintServiceForm', 'Clear Edits'))
        self.clear_action.setToolTip(translate('OpenLP.WebViewPrintServiceForm', 'Clear all custom assignments and notes'))
        
        # Template selector
        self.toolbar.addSeparator()
        self.template_label = QtWidgets.QLabel(translate('OpenLP.WebViewPrintServiceForm', 'Template:'))
        self.toolbar.addWidget(self.template_label)
        
        self.template_combo = QtWidgets.QComboBox()
        self.template_combo.addItem(translate('OpenLP.WebViewPrintServiceForm', 'Professional'), ServiceTemplate.PROFESSIONAL)
        self.toolbar.addWidget(self.template_combo)
        
        # Options button
        self.toolbar.addSeparator()
        self.options_button = QtWidgets.QToolButton()
        self.options_button.setText(translate('OpenLP.WebViewPrintServiceForm', 'Options'))
        self.options_button.setIcon(UiIcons().settings)
        self.options_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.options_button.setCheckable(True)
        self.toolbar.addWidget(self.options_button)
        
        # Orientation toggle
        self.toolbar.addSeparator()
        self.orientation_label = QtWidgets.QLabel(translate('OpenLP.WebViewPrintServiceForm', 'Orientation:'))
        self.toolbar.addWidget(self.orientation_label)
        
        self.orientation_combo = QtWidgets.QComboBox()
        self.orientation_combo.addItem(translate('OpenLP.WebViewPrintServiceForm', 'Portrait'), 'portrait')
        self.orientation_combo.addItem(translate('OpenLP.WebViewPrintServiceForm', 'Landscape'), 'landscape')
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
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.WebViewPrintServiceForm', 'Service Title:')))
        self.title_edit = QtWidgets.QLineEdit()
        self.title_edit.setText(translate('OpenLP.WebViewPrintServiceForm', 'Service Runsheet'))
        layout.addWidget(self.title_edit)
        
        # Service date
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.WebViewPrintServiceForm', 'Service Date:')))
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setDate(QtCore.QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        layout.addWidget(self.date_edit)
        
        # Service time
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.WebViewPrintServiceForm', 'Service Time:')))
        self.time_edit = QtWidgets.QTimeEdit()
        self.time_edit.setTime(QtCore.QTime(10, 0))
        layout.addWidget(self.time_edit)
        
        # Options group
        options_group = QtWidgets.QGroupBox(translate('OpenLP.WebViewPrintServiceForm', 'Include'))
        options_layout = QtWidgets.QVBoxLayout(options_group)
        
        self.include_times_check = QtWidgets.QCheckBox(translate('OpenLP.WebViewPrintServiceForm', 'Times and durations'))
        self.include_times_check.setChecked(True)
        options_layout.addWidget(self.include_times_check)
        
        self.include_notes_check = QtWidgets.QCheckBox(translate('OpenLP.WebViewPrintServiceForm', 'Service item notes'))
        self.include_notes_check.setChecked(True)
        options_layout.addWidget(self.include_notes_check)
        
        self.include_slides_check = QtWidgets.QCheckBox(translate('OpenLP.WebViewPrintServiceForm', 'Slide text'))
        options_layout.addWidget(self.include_slides_check)
        
        self.include_media_info_check = QtWidgets.QCheckBox(translate('OpenLP.WebViewPrintServiceForm', 'Media information'))
        self.include_media_info_check.setChecked(True)
        options_layout.addWidget(self.include_media_info_check)
        
        layout.addWidget(options_group)
        
        # Footer notes
        layout.addWidget(QtWidgets.QLabel(translate('OpenLP.WebViewPrintServiceForm', 'Footer Notes:')))
        self.footer_edit = QtWidgets.QTextEdit()
        self.footer_edit.setMaximumHeight(100)
        layout.addWidget(self.footer_edit)
        
        layout.addStretch()

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
                self.update_preview()
                break

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
        html_content = template_html.format(
            title=html.escape(self.title_edit.text()),
            date=self.date_edit.date().toString('dddd, MMMM dd, yyyy'),
            time=self.time_edit.time().toString('h:mm AP'),
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
            return render_professional_items(service_items, include_times, include_notes, include_slides, include_media_info, self.custom_data)

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
                        translate('OpenLP.WebViewPrintServiceForm', 'PDF generated for printing. You can now print from your PDF viewer.'), 5000)
                    
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
                            translate('OpenLP.WebViewPrintServiceForm', f'PDF saved to: {temp_pdf_path}'), 5000)
                        
                except Exception as e:
                    self.status_bar.showMessage(
                        translate('OpenLP.WebViewPrintServiceForm', 'Print preparation failed'), 3000)
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
            translate('OpenLP.WebViewPrintServiceForm', 'Export Service Runsheet'),
            str(Path.home() / f"Service_{self.date_edit.date().toString('yyyy-MM-dd')}.pdf"),
            translate('OpenLP.WebViewPrintServiceForm', 'PDF files (*.pdf)')
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
                        translate('OpenLP.WebViewPrintServiceForm', f'PDF exported to {file_path}'), 3000)
                except Exception:
                    self.status_bar.showMessage(
                        translate('OpenLP.WebViewPrintServiceForm', 'PDF export failed'), 3000)
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
            translate('OpenLP.WebViewPrintServiceForm', 'Clear Custom Data'),
            translate('OpenLP.WebViewPrintServiceForm', 'Are you sure you want to clear all custom assignments and notes?'),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.custom_data.clear()
            self.update_preview()
            self.status_bar.showMessage(translate('OpenLP.WebViewPrintServiceForm', 'Custom data cleared'), 3000)
    
    def closeEvent(self, event):
        """
        Handle close event
        """
        self.save_settings()
        super().closeEvent(event)

