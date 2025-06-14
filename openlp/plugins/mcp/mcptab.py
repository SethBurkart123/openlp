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

from PySide6 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.settingstab import SettingsTab


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
        self.quality_combo_box.currentTextChanged.connect(self.on_quality_changed)
        self.keep_downloads_check_box.toggled.connect(self.on_keep_downloads_toggled)
        self.download_location_button.clicked.connect(self.on_download_location_button_clicked)

    def retranslate_ui(self):
        """
        Translate the UI text
        """
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
        # Get the actual quality values for internal use
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
        
        self.changed = False

    def save(self):
        """
        Save the settings from the UI.
        """
        # Map display index back to actual quality values
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