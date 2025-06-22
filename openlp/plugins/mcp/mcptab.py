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
The :mod:`~openlp.plugins.mcp.mcptab` module contains the settings tab
for the MCP plugin, which is inserted into the configuration dialog.
"""

import logging
from PySide6 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib.settingstab import SettingsTab

log = logging.getLogger(__name__)

class MCPTab(SettingsTab):
    """
    MCPTab is the MCP settings tab in the settings dialog.
    """
    def setup_ui(self):
        """
        Set up the configuration tab UI.
        """
        self.setObjectName('MCPTab')
        super(MCPTab, self).setup_ui()
        
        # Server Control group box
        self.server_control_group_box = QtWidgets.QGroupBox(self.left_column)
        self.server_control_group_box.setObjectName('server_control_group_box')
        self.server_control_layout = QtWidgets.QVBoxLayout(self.server_control_group_box)
        self.server_control_layout.setObjectName('server_control_layout')
        
        # Server info label
        self.server_info_label = QtWidgets.QLabel(self.server_control_group_box)
        self.server_info_label.setWordWrap(True)
        self.server_info_label.setObjectName('server_info_label')
        self.server_control_layout.addWidget(self.server_info_label)
        
        # Port settings
        self.port_layout = QtWidgets.QHBoxLayout()
        self.port_label = QtWidgets.QLabel(self.server_control_group_box)
        self.port_label.setObjectName('port_label')
        self.port_spin_box = QtWidgets.QSpinBox(self.server_control_group_box)
        self.port_spin_box.setObjectName('port_spin_box')
        self.port_spin_box.setMinimum(1024)
        self.port_spin_box.setMaximum(65535)
        self.port_spin_box.setValue(8765)
        
        self.port_layout.addWidget(self.port_label)
        self.port_layout.addWidget(self.port_spin_box)
        self.port_layout.addStretch()
        self.server_control_layout.addLayout(self.port_layout)
        
        # Host settings
        self.host_layout = QtWidgets.QHBoxLayout()
        self.host_label = QtWidgets.QLabel(self.server_control_group_box)
        self.host_label.setObjectName('host_label')
        self.host_combo_box = QtWidgets.QComboBox(self.server_control_group_box)
        self.host_combo_box.setObjectName('host_combo_box')
        self.host_combo_box.addItems(['0.0.0.0', '127.0.0.1'])
        self.host_combo_box.setEditable(True)  # Allow custom IP addresses
        
        self.host_layout.addWidget(self.host_label)
        self.host_layout.addWidget(self.host_combo_box)
        self.host_layout.addStretch()
        self.server_control_layout.addLayout(self.host_layout)
        
        # Auto-start checkbox
        self.auto_start_check_box = QtWidgets.QCheckBox(self.server_control_group_box)
        self.auto_start_check_box.setObjectName('auto_start_check_box')
        self.server_control_layout.addWidget(self.auto_start_check_box)
        
        # Server control buttons
        self.server_buttons_layout = QtWidgets.QHBoxLayout()
        self.start_server_button = QtWidgets.QPushButton(self.server_control_group_box)
        self.start_server_button.setObjectName('start_server_button')
        self.stop_server_button = QtWidgets.QPushButton(self.server_control_group_box)
        self.stop_server_button.setObjectName('stop_server_button')
        self.server_status_label = QtWidgets.QLabel(self.server_control_group_box)
        self.server_status_label.setObjectName('server_status_label')
        
        self.server_buttons_layout.addWidget(self.start_server_button)
        self.server_buttons_layout.addWidget(self.stop_server_button)
        self.server_buttons_layout.addWidget(self.server_status_label)
        self.server_buttons_layout.addStretch()
        self.server_control_layout.addLayout(self.server_buttons_layout)
        
        # Server URLs display
        self.server_urls_label = QtWidgets.QLabel(self.server_control_group_box)
        self.server_urls_label.setObjectName('server_urls_label')
        self.server_urls_label.setWordWrap(True)
        self.server_urls_label.setOpenExternalLinks(True)
        self.server_urls_label.hide()  # Initially hidden
        self.server_control_layout.addWidget(self.server_urls_label)
        
        self.left_layout.addWidget(self.server_control_group_box)
        
        # Video Quality Settings group box
        self.video_quality_group_box = QtWidgets.QGroupBox(self.left_column)
        self.video_quality_group_box.setObjectName('video_quality_group_box')
        self.video_quality_layout = QtWidgets.QVBoxLayout(self.video_quality_group_box)
        self.video_quality_layout.setObjectName('video_quality_layout')
        
        # Info label
        self.quality_info_label = QtWidgets.QLabel(self.video_quality_group_box)
        self.quality_info_label.setWordWrap(True)
        self.quality_info_label.setObjectName('quality_info_label')
        self.video_quality_layout.addWidget(self.quality_info_label)
        
        # Quality selection combo box
        self.quality_combo_layout = QtWidgets.QHBoxLayout()
        self.quality_label = QtWidgets.QLabel(self.video_quality_group_box)
        self.quality_label.setObjectName('quality_label')
        self.quality_combo_box = QtWidgets.QComboBox(self.video_quality_group_box)
        self.quality_combo_box.setObjectName('quality_combo_box')
        
        # Add quality options (prefer H.264 for better compatibility)
        self.quality_combo_box.addItems([
            'bestvideo[vcodec^=avc]+bestaudio/bestvideo+bestaudio/best',  # Best H.264 video + best audio
            'bestvideo[height<=2160][vcodec^=avc]+bestaudio/bestvideo[height<=2160]+bestaudio/best',  # 4K max (H.264 preferred)
            'bestvideo[height<=1080][vcodec^=avc]+bestaudio/bestvideo[height<=1080]+bestaudio/best',  # 1080p max (H.264 preferred)
            'bestvideo[height<=720][vcodec^=avc]+bestaudio/bestvideo[height<=720]+bestaudio/best',  # 720p max (H.264 preferred)
            'bestaudio/best'  # Audio only
        ])
        
        self.quality_combo_layout.addWidget(self.quality_label)
        self.quality_combo_layout.addWidget(self.quality_combo_box)
        self.quality_combo_layout.addStretch()
        self.video_quality_layout.addLayout(self.quality_combo_layout)
        
        self.left_layout.addWidget(self.video_quality_group_box)
        
        # Download Settings group box
        self.download_group_box = QtWidgets.QGroupBox(self.left_column)
        self.download_group_box.setObjectName('download_group_box')
        self.download_layout = QtWidgets.QVBoxLayout(self.download_group_box)
        self.download_layout.setObjectName('download_layout')
        
        # Keep downloads checkbox
        self.keep_downloads_check_box = QtWidgets.QCheckBox(self.download_group_box)
        self.keep_downloads_check_box.setObjectName('keep_downloads_check_box')
        self.download_layout.addWidget(self.keep_downloads_check_box)
        
        # Download location
        self.download_location_layout = QtWidgets.QHBoxLayout()
        self.download_location_label = QtWidgets.QLabel(self.download_group_box)
        self.download_location_label.setObjectName('download_location_label')
        self.download_location_edit = QtWidgets.QLineEdit(self.download_group_box)
        self.download_location_edit.setObjectName('download_location_edit')
        self.download_location_button = QtWidgets.QPushButton(self.download_group_box)
        self.download_location_button.setObjectName('download_location_button')
        
        self.download_location_layout.addWidget(self.download_location_label)
        self.download_location_layout.addWidget(self.download_location_edit)
        self.download_location_layout.addWidget(self.download_location_button)
        self.download_layout.addLayout(self.download_location_layout)
        
        self.left_layout.addWidget(self.download_group_box)
        self.left_layout.addStretch()
        
        # Connect signals
        self.port_spin_box.valueChanged.connect(self.on_port_changed)
        self.host_combo_box.currentTextChanged.connect(self.on_host_changed)
        self.auto_start_check_box.toggled.connect(self.on_auto_start_toggled)
        self.start_server_button.clicked.connect(self.on_start_server_clicked)
        self.stop_server_button.clicked.connect(self.on_stop_server_clicked)
        self.quality_combo_box.currentTextChanged.connect(self.on_quality_changed)
        self.keep_downloads_check_box.toggled.connect(self.on_keep_downloads_toggled)
        self.download_location_button.clicked.connect(self.on_download_location_button_clicked)
        
        # Update server status initially
        self.update_server_status()

    def retranslate_ui(self):
        """
        Translate the UI text
        """
        self.server_control_group_box.setTitle(translate('MCPPlugin.MCPTab', 'MCP Server Control'))
        self.server_info_label.setText(translate('MCPPlugin.MCPTab',
            'The MCP server allows AI models to control OpenLP. '
            'Configure the port and start/stop the server as needed.'))
        self.port_label.setText(translate('MCPPlugin.MCPTab', 'Port:'))
        self.host_label.setText(translate('MCPPlugin.MCPTab', 'Host:'))
        self.auto_start_check_box.setText(translate('MCPPlugin.MCPTab', 'Auto-start server when OpenLP starts'))
        self.start_server_button.setText(translate('MCPPlugin.MCPTab', 'Start Server'))
        self.stop_server_button.setText(translate('MCPPlugin.MCPTab', 'Stop Server'))
        
        self.video_quality_group_box.setTitle(translate('MCPPlugin.MCPTab', 'Video Download Quality'))
        self.quality_info_label.setText(translate('MCPPlugin.MCPTab',
            'Choose the quality for video downloads from platforms like YouTube. '
            'Higher quality videos will take longer to download and use more storage space.'))
        self.quality_label.setText(translate('MCPPlugin.MCPTab', 'Quality:'))
        
        self.download_group_box.setTitle(translate('MCPPlugin.MCPTab', 'Download Settings'))
        self.keep_downloads_check_box.setText(translate('MCPPlugin.MCPTab', 
            'Keep downloaded files (otherwise they are deleted when OpenLP closes)'))
        self.download_location_label.setText(translate('MCPPlugin.MCPTab', 'Download folder:'))
        self.download_location_button.setText(translate('MCPPlugin.MCPTab', 'Browse...'))
        
        # Update combo box display names
        quality_names = [
            translate('MCPPlugin.MCPTab', 'Best available (H.264 preferred)'),
            translate('MCPPlugin.MCPTab', 'Ultra HD - 4K (H.264 preferred)'),
            translate('MCPPlugin.MCPTab', 'Full HD - 1080p (H.264 preferred)'),
            translate('MCPPlugin.MCPTab', 'HD - 720p (H.264 preferred)'),
            translate('MCPPlugin.MCPTab', 'Audio only (no video)')
        ]
        
        for i, name in enumerate(quality_names):
            self.quality_combo_box.setItemText(i, name)
            
        # Update server status text
        self.update_server_status()

    def on_port_changed(self):
        """Port value changed"""
        self.changed = True
        # If server is running, restart it with new port
        self._restart_server_if_running()

    def on_host_changed(self):
        """Host value changed"""
        self.changed = True
        # If server is running, restart it with new host
        self._restart_server_if_running()

    def _restart_server_if_running(self):
        """Restart server if it's currently running"""
        try:
            plugin = Registry().get('plugin_manager').get_plugin_by_name('mcp')
            if plugin and plugin.is_server_running():
                # Save settings first
                self.save()
                # Restart server
                plugin.restart_server()
                # Update status
                from PySide6.QtCore import QTimer
                QTimer.singleShot(1000, self.update_server_status)  # Update status after a delay
        except Exception as e:
            log.debug(f'Could not restart server: {e}')

    def on_auto_start_toggled(self):
        """Auto-start option toggled"""
        self.changed = True

    def on_start_server_clicked(self):
        """Start server button clicked"""
        try:
            plugin = Registry().get('plugin_manager').get_plugin_by_name('mcp')
            if plugin:
                plugin.start_server()
                self.update_server_status()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 
                translate('MCPPlugin.MCPTab', 'Error'), 
                translate('MCPPlugin.MCPTab', 'Failed to start server: {error}').format(error=str(e)))

    def on_stop_server_clicked(self):
        """Stop server button clicked"""
        try:
            plugin = Registry().get('plugin_manager').get_plugin_by_name('mcp')
            if plugin:
                plugin.stop_server()
                self.update_server_status()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 
                translate('MCPPlugin.MCPTab', 'Error'), 
                translate('MCPPlugin.MCPTab', 'Failed to stop server: {error}').format(error=str(e)))

    def update_server_status(self):
        """Update the server status display"""
        try:
            plugin = Registry().get('plugin_manager').get_plugin_by_name('mcp')
            if plugin and plugin.is_server_running():
                # Get current settings
                host = self.settings.value('mcp/host')
                port = self.settings.value('mcp/port')
                
                # Update status
                self.server_status_label.setText(
                    translate('MCPPlugin.MCPTab', 'Running on {host}:{port}').format(host=host, port=port))
                self.server_status_label.setStyleSheet('color: green;')
                self.start_server_button.setEnabled(False)
                self.stop_server_button.setEnabled(True)
                
                # Show server URLs
                urls = plugin.get_server_urls()
                if urls:
                    url_links = []
                    for url in urls:
                        url_links.append(f'<a href="{url}">{url}</a>')
                    
                    self.server_urls_label.setText(
                        translate('MCPPlugin.MCPTab', 'Server accessible at:<br/>{}').format('<br/>'.join(url_links)))
                    self.server_urls_label.show()
                else:
                    self.server_urls_label.hide()
            else:
                self.server_status_label.setText(translate('MCPPlugin.MCPTab', 'Stopped'))
                self.server_status_label.setStyleSheet('color: red;')
                self.start_server_button.setEnabled(True)
                self.stop_server_button.setEnabled(False)
                self.server_urls_label.hide()
        except Exception:
            self.server_status_label.setText(translate('MCPPlugin.MCPTab', 'Unknown'))
            self.server_status_label.setStyleSheet('color: orange;')
            self.start_server_button.setEnabled(True)
            self.stop_server_button.setEnabled(True)
            self.server_urls_label.hide()

    def on_quality_changed(self):
        """Quality selection changed"""
        self.changed = True

    def on_keep_downloads_toggled(self):
        """Keep downloads option toggled"""
        self.changed = True

    def on_download_location_button_clicked(self):
        """Browse for download location"""
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            translate('MCPPlugin.MCPTab', 'Select Download Folder'),
            self.download_location_edit.text()
        )
        if directory:
            self.download_location_edit.setText(directory)
            self.changed = True

    def load(self):
        """
        Load the settings into the UI.
        """
        # Load server settings
        self.port_spin_box.setValue(self.settings.value('mcp/port'))
        host_value = self.settings.value('mcp/host')
        # Set host combo box value
        index = self.host_combo_box.findText(host_value)
        if index >= 0:
            self.host_combo_box.setCurrentIndex(index)
        else:
            self.host_combo_box.setCurrentText(host_value)  # Custom value
        self.auto_start_check_box.setChecked(self.settings.value('mcp/auto_start'))
        
        # Load video quality settings
        quality_values = [
            'bestvideo[vcodec^=avc]+bestaudio/bestvideo+bestaudio/best',
            'bestvideo[height<=2160][vcodec^=avc]+bestaudio/bestvideo[height<=2160]+bestaudio/best',
            'bestvideo[height<=1080][vcodec^=avc]+bestaudio/bestvideo[height<=1080]+bestaudio/best',
            'bestvideo[height<=720][vcodec^=avc]+bestaudio/bestvideo[height<=720]+bestaudio/best',
            'bestaudio/best'
        ]
        
        video_quality = self.settings.value('mcp/video_quality')
        try:
            index = quality_values.index(video_quality)
            self.quality_combo_box.setCurrentIndex(index)
        except ValueError:
            self.quality_combo_box.setCurrentIndex(2)  # Default to 1080p
        
        self.keep_downloads_check_box.setChecked(self.settings.value('mcp/keep_downloads'))
        self.download_location_edit.setText(self.settings.value('mcp/download_location'))
        
        self.update_server_status()
        self.changed = False

    def save(self):
        """
        Save the settings from the UI.
        """
        # Save server settings
        self.settings.setValue('mcp/port', self.port_spin_box.value())
        self.settings.setValue('mcp/host', self.host_combo_box.currentText())
        self.settings.setValue('mcp/auto_start', self.auto_start_check_box.isChecked())
        
        # Save video quality settings
        quality_values = [
            'bestvideo[vcodec^=avc]+bestaudio/bestvideo+bestaudio/best',
            'bestvideo[height<=2160][vcodec^=avc]+bestaudio/bestvideo[height<=2160]+bestaudio/best',
            'bestvideo[height<=1080][vcodec^=avc]+bestaudio/bestvideo[height<=1080]+bestaudio/best',
            'bestvideo[height<=720][vcodec^=avc]+bestaudio/bestvideo[height<=720]+bestaudio/best',
            'bestaudio/best'
        ]
        selected_quality = quality_values[self.quality_combo_box.currentIndex()]
        
        self.settings.setValue('mcp/video_quality', selected_quality)
        self.settings.setValue('mcp/keep_downloads', self.keep_downloads_check_box.isChecked())
        self.settings.setValue('mcp/download_location', self.download_location_edit.text())
        
        self.changed = False 