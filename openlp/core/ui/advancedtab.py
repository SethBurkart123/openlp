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
The :mod:`advancedtab` provides an advanced settings facility.
"""
import logging

from PySide6 import QtWidgets

from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.ui.icons import UiIcons
from openlp.core.widgets.edits import PathEdit
from openlp.core.widgets.enums import PathEditType
from openlp.core.widgets.widgets import ProxyWidget


log = logging.getLogger(__name__)


class AdvancedTab(SettingsTab):
    """
    The :class:`AdvancedTab` manages the advanced settings tab including the UI
    and the loading and saving of the displayed settings.
    """
    def __init__(self, parent):
        """
        Initialise the settings tab
        """
        self.data_exists = False
        self.icon_path = UiIcons().settings
        advanced_translated = translate('OpenLP.AdvancedTab', 'Advanced')
        super(AdvancedTab, self).__init__(parent, 'Advanced', advanced_translated)

    def setup_ui(self):
        """
        Configure the UI elements for the tab.
        """
        self.setObjectName('AdvancedTab')
        super(AdvancedTab, self).setup_ui()
        # Data Directory
        self.data_directory_group_box = QtWidgets.QGroupBox(self.left_column)
        self.data_directory_group_box.setObjectName('data_directory_group_box')
        self.data_directory_layout = QtWidgets.QFormLayout(self.data_directory_group_box)
        self.data_directory_layout.setObjectName('data_directory_layout')
        self.data_directory_new_label = QtWidgets.QLabel(self.data_directory_group_box)
        self.data_directory_new_label.setObjectName('data_directory_current_label')
        self.data_directory_path_edit = PathEdit(self.data_directory_group_box, path_type=PathEditType.Directories,
                                                 default_path=AppLocation.get_directory(AppLocation.DataDir))
        self.data_directory_layout.addRow(self.data_directory_new_label, self.data_directory_path_edit)
        self.new_data_directory_has_files_label = QtWidgets.QLabel(self.data_directory_group_box)
        self.new_data_directory_has_files_label.setObjectName('new_data_directory_has_files_label')
        self.new_data_directory_has_files_label.setWordWrap(True)
        self.data_directory_cancel_button = QtWidgets.QToolButton(self.data_directory_group_box)
        self.data_directory_cancel_button.setObjectName('data_directory_cancel_button')
        self.data_directory_cancel_button.setIcon(UiIcons().delete)
        self.data_directory_copy_check_layout = QtWidgets.QHBoxLayout()
        self.data_directory_copy_check_layout.setObjectName('data_directory_copy_check_layout')
        self.data_directory_copy_check_box = QtWidgets.QCheckBox(self.data_directory_group_box)
        self.data_directory_copy_check_box.setObjectName('data_directory_copy_check_box')
        self.data_directory_copy_check_layout.addWidget(self.data_directory_copy_check_box)
        self.data_directory_copy_check_layout.addStretch()
        self.data_directory_copy_check_layout.addWidget(self.data_directory_cancel_button)
        self.data_directory_protect_check_layout = QtWidgets.QHBoxLayout()
        self.data_directory_protect_check_layout.setObjectName('data_directory_copy_check_layout')
        self.data_directory_protect_check_box = QtWidgets.QCheckBox(self.data_directory_group_box)
        self.data_directory_protect_check_box.setObjectName('data_directory_protect_check_box')
        self.data_directory_protect_check_layout.addWidget(self.data_directory_protect_check_box)
        self.data_directory_layout.addRow(self.data_directory_copy_check_layout)
        self.data_directory_layout.addRow(self.data_directory_protect_check_layout)
        self.data_directory_layout.addRow(self.new_data_directory_has_files_label)
        self.left_layout.addWidget(self.data_directory_group_box)
        # Display Workarounds
        self.display_workaround_group_box = QtWidgets.QGroupBox(self.left_column)
        self.display_workaround_group_box.setObjectName('display_workaround_group_box')
        self.display_workaround_layout = QtWidgets.QVBoxLayout(self.display_workaround_group_box)
        self.display_workaround_layout.setObjectName('display_workaround_layout')
        self.ignore_aspect_ratio_check_box = QtWidgets.QCheckBox(self.display_workaround_group_box)
        self.ignore_aspect_ratio_check_box.setObjectName('ignore_aspect_ratio_check_box')
        self.display_workaround_layout.addWidget(self.ignore_aspect_ratio_check_box)
        self.x11_bypass_check_box = QtWidgets.QCheckBox(self.display_workaround_group_box)
        self.x11_bypass_check_box.setObjectName('x11_bypass_check_box')
        self.display_workaround_layout.addWidget(self.x11_bypass_check_box)
        self.alternate_rows_check_box = QtWidgets.QCheckBox(self.display_workaround_group_box)
        self.alternate_rows_check_box.setObjectName('alternate_rows_check_box')
        self.display_workaround_layout.addWidget(self.alternate_rows_check_box)
        self.allow_transparent_display_check_box = QtWidgets.QCheckBox(self.display_workaround_group_box)
        self.allow_transparent_display_check_box.setObjectName('allow_transparent_display_check_box')
        self.display_workaround_layout.addWidget(self.allow_transparent_display_check_box)
        self.prefer_windowed_capture_check_box = QtWidgets.QCheckBox(self.display_workaround_group_box)
        self.prefer_windowed_capture_check_box.setObjectName('prefer_windowed_capture_check_box')
        self.display_workaround_layout.addWidget(self.prefer_windowed_capture_check_box)
        self.left_layout.addWidget(self.display_workaround_group_box)
        # Misc Workarounds
        self.misc_workaround_group_box = QtWidgets.QGroupBox(self.left_column)
        self.misc_workaround_group_box.setObjectName('misc_workaround_group_box')
        self.misc_workaround_layout = QtWidgets.QVBoxLayout(self.misc_workaround_group_box)
        self.misc_workaround_layout.setObjectName('misc_workaround_layout')
        self.hidpi_mode_widget = QtWidgets.QWidget(self.misc_workaround_group_box)
        self.hidpi_mode_layout = QtWidgets.QHBoxLayout(self.hidpi_mode_widget)
        self.hidpi_mode_layout.setContentsMargins(0, 0, 0, 0)
        self.hidpi_mode_label = QtWidgets.QLabel(self.hidpi_mode_widget)
        self.hidpi_mode_combobox = QtWidgets.QComboBox(self.hidpi_mode_widget)
        self.hidpi_mode_combobox.addItems(['', '', ''])
        self.hidpi_mode_layout.addWidget(self.hidpi_mode_label)
        self.hidpi_mode_layout.addWidget(self.hidpi_mode_combobox)
        self.hidpi_mode_widget.setLayout(self.hidpi_mode_layout)
        self.bypass_backup_check_box = QtWidgets.QCheckBox(self.misc_workaround_group_box)
        self.bypass_backup_check_box.setObjectName('bypass_backup_check_box')
        self.misc_workaround_layout.addWidget(self.bypass_backup_check_box)
        self.misc_workaround_layout.addWidget(self.hidpi_mode_widget)
        self.left_layout.addWidget(self.misc_workaround_group_box)
        # Proxies
        self.proxy_widget = ProxyWidget(self.right_column)
        self.right_layout.addWidget(self.proxy_widget)
        # After the last item on each side, add some spacing
        self.left_layout.addStretch()
        self.right_layout.addStretch()
        # Set up all the connections and things
        self.alternate_rows_check_box.toggled.connect(self.on_restart_needed)
        self.data_directory_path_edit.pathChanged.connect(self.on_data_directory_path_edit_path_changed)
        self.data_directory_cancel_button.clicked.connect(self.on_data_directory_cancel_button_clicked)
        self.data_directory_copy_check_box.toggled.connect(self.on_data_directory_copy_check_box_toggled)
        self.hidpi_mode_combobox.currentIndexChanged.connect(self.on_restart_needed)

    def retranslate_ui(self):
        """
        Setup the interface translation strings.
        """
        self.tab_title_visible = UiStrings().Advanced
        self.data_directory_group_box.setTitle(translate('OpenLP.AdvancedTab', 'Data Location'))
        self.data_directory_new_label.setText(translate('OpenLP.AdvancedTab', 'Path:'))
        self.data_directory_cancel_button.setText(translate('OpenLP.AdvancedTab', 'Cancel'))
        self.data_directory_cancel_button.setToolTip(
            translate('OpenLP.AdvancedTab', 'Cancel OpenLP data directory location change.'))
        self.data_directory_copy_check_box.setText(translate('OpenLP.AdvancedTab', 'Copy data to new location.'))
        self.data_directory_copy_check_box.setToolTip(translate(
            'OpenLP.AdvancedTab', 'Copy the OpenLP data files to the new location.'))
        self.data_directory_protect_check_box.setText(translate(
            'OpenLP.AdvancedTab', 'Protect the data directory with a locking mechanism.'))
        self.data_directory_protect_check_box.setToolTip(translate(
            'OpenLP.AdvancedTab', 'Protect the data directory with a locking mechanism to avoid data corruption if '
                                  'multiple users access the data at the same time. Useful for instances shared via '
                                  'network. <strong>NOTE:</strong> This will only work if the network sharing is '
                                  'available when OpenLP is running.'))
        self.new_data_directory_has_files_label.setText(
            translate('OpenLP.AdvancedTab', '<strong>WARNING:</strong> New data directory location contains '
                      'OpenLP data files.  These files WILL be replaced during a copy.'))
        self.display_workaround_group_box.setTitle(translate('OpenLP.AdvancedTab', 'Display Workarounds'))
        self.ignore_aspect_ratio_check_box.setText(translate('OpenLP.AdvancedTab', 'Ignore Aspect Ratio'))
        self.x11_bypass_check_box.setText(translate('OpenLP.AdvancedTab', 'Bypass X11 Window Manager'))
        self.alternate_rows_check_box.setText(translate('OpenLP.AdvancedTab', 'Use alternating row colours in lists'))
        self.allow_transparent_display_check_box.setText(
            translate('OpenLP.AdvancedTab', 'Disable display transparency'))
        self.prefer_windowed_capture_check_box.setText(
            translate('OpenLP.AdvancedTab', 'Prefer window capture instead of screen capture'))
        self.misc_workaround_group_box.setTitle(translate('OpenLP.AdvancedTab', 'Miscellaneous Workarounds'))
        self.bypass_backup_check_box.setText(translate('OpenLP.AdvancedTab', 'Skip backup when version changes'))
        self.hidpi_mode_label.setText(translate('OpenLP.AdvancedTab', 'HiDPI Mode:'))
        self.hidpi_mode_combobox.setItemText(0, translate('OpenLP.AdvancedTab', 'Default'))
        self.hidpi_mode_combobox.setItemText(1, translate('OpenLP.AdvancedTab', 'Legacy'))
        self.hidpi_mode_combobox.setItemText(2, translate('OpenLP.AdvancedTab', 'DPI Unaware (Windows only)'))
        self.proxy_widget.retranslate_ui()

    def load(self):
        """
        Load settings from disk.
        """
        self.ignore_aspect_ratio_check_box.setChecked(self.settings.value('advanced/ignore aspect ratio'))
        self.x11_bypass_check_box.setChecked(self.settings.value('advanced/x11 bypass wm'))
        # Prevent the dialog displayed by the alternate_rows_check_box to display.
        self.alternate_rows_check_box.blockSignals(True)
        self.alternate_rows_check_box.setChecked(self.settings.value('advanced/alternate rows'))
        self.alternate_rows_check_box.blockSignals(False)
        self.allow_transparent_display_check_box.setChecked(self.settings.value('advanced/disable transparent display'))
        self.prefer_windowed_capture_check_box.setChecked(
            self.settings.value('advanced/prefer windowed screen capture'))
        self.data_directory_copy_check_box.hide()
        self.new_data_directory_has_files_label.hide()
        self.data_directory_cancel_button.hide()
        # Since data location can be changed, make sure the path is present.
        self.data_directory_path_edit.path = AppLocation.get_data_path()
        # Don't allow data directory move if running portable.
        if self.settings.value('advanced/is portable'):
            self.data_directory_new_label.hide()
            self.data_directory_path_edit.hide()
        self.data_directory_protect_check_box.setChecked(self.settings.value('advanced/protect data directory'))
        self.bypass_backup_check_box.setChecked(self.settings.value('advanced/bypass_backup_on_version_change'))
        self.hidpi_mode_combobox.setCurrentIndex(self.settings.value('advanced/hidpi mode'))

    def save(self):
        """
        Save settings to disk.
        """
        self.settings.setValue('advanced/disable transparent display',
                               self.allow_transparent_display_check_box.isChecked())
        self.settings.setValue('advanced/prefer windowed screen capture',
                               self.prefer_windowed_capture_check_box.isChecked())
        self.settings.setValue('advanced/ignore aspect ratio', self.ignore_aspect_ratio_check_box.isChecked())
        if self.x11_bypass_check_box.isChecked() != self.settings.value('advanced/x11 bypass wm'):
            self.settings.setValue('advanced/x11 bypass wm', self.x11_bypass_check_box.isChecked())
            self.settings_form.register_post_process('config_screen_changed')
        self.settings.setValue('advanced/alternate rows', self.alternate_rows_check_box.isChecked())
        self.settings.setValue('advanced/protect data directory', self.data_directory_protect_check_box.isChecked())
        self.settings.setValue('advanced/bypass_backup_on_version_change', self.bypass_backup_check_box.isChecked())
        self.settings.setValue('advanced/hidpi mode', self.hidpi_mode_combobox.currentIndex())
        self.proxy_widget.save()

    def cancel(self):
        """
        Dialogue was cancelled, remove any pending data path change.
        """
        self.on_data_directory_cancel_button_clicked()
        SettingsTab.cancel(self)

    def on_data_directory_path_edit_path_changed(self, new_path):
        """
        Handle the `editPathChanged` signal of the data_directory_path_edit

        :param pathlib.Path new_path: The new path
        :rtype: None
        """
        # Check if data already exists here.
        self.check_data_overwrite(new_path)
        # Make sure they want to change the data.
        if self.data_directory_copy_check_box.isChecked():
            warning_string = translate('OpenLP.AdvancedTab', 'Are you sure you want to change the '
                                                             'location of the OpenLP data directory to:\n\n{path}'
                                                             '\n\nExisting files in this directory could be '
                                                             'overwritten. The data directory will be changed when '
                                                             'OpenLP is closed.').format(path=new_path)
        else:
            warning_string = translate('OpenLP.AdvancedTab', 'Are you sure you want to change the '
                                                             'location of the OpenLP data directory to:\n\n{path}'
                                                             '\n\nThe data directory will be changed when OpenLP is '
                                                             'closed.').format(path=new_path)
        answer = QtWidgets.QMessageBox.question(self, translate('OpenLP.AdvancedTab', 'Confirm Data Directory Change'),
                                                warning_string, defaultButton=QtWidgets.QMessageBox.StandardButton.No)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            self.data_directory_path_edit.path = AppLocation.get_data_path()
            self.new_data_directory_has_files_label.hide()
            return
        # Save the new location.
        self.main_window.new_data_path = new_path
        self.data_directory_cancel_button.show()

    def on_data_directory_copy_check_box_toggled(self):
        """
        Copy existing data when you change your data directory.
        """
        self.main_window.set_copy_data(self.data_directory_copy_check_box.isChecked())
        if self.data_exists:
            if self.data_directory_copy_check_box.isChecked():
                self.new_data_directory_has_files_label.show()
            else:
                self.new_data_directory_has_files_label.hide()

    def check_data_overwrite(self, data_path):
        """
        Check if there's already data in the target directory.

        :param pathlib.Path data_path: The target directory to check
        """
        if (data_path / 'songs').exists():
            self.data_exists = True
            # Check is they want to replace existing data.
            answer = QtWidgets.QMessageBox.warning(self,
                                                   translate('OpenLP.AdvancedTab', 'Overwrite Existing Data'),
                                                   translate('OpenLP.AdvancedTab',
                                                             'WARNING: \n\nThe location you have selected \n\n{path}'
                                                             '\n\nappears to contain OpenLP data files. Do you wish to '
                                                             'replace these files with the current data '
                                                             'files?').format(path=data_path),
                                                   QtWidgets.QMessageBox.StandardButton(
                                                       QtWidgets.QMessageBox.StandardButton.Yes |
                                                       QtWidgets.QMessageBox.StandardButton.No),
                                                   QtWidgets.QMessageBox.StandardButton.No)
            self.data_directory_copy_check_box.show()
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                self.data_directory_copy_check_box.setChecked(True)
                self.new_data_directory_has_files_label.show()
            else:
                self.data_directory_copy_check_box.setChecked(False)
                self.new_data_directory_has_files_label.hide()
        else:
            self.data_exists = False
            self.data_directory_copy_check_box.setChecked(True)
            self.new_data_directory_has_files_label.hide()

    def on_data_directory_cancel_button_clicked(self):
        """
        Cancel the data directory location change
        """
        self.data_directory_path_edit.path = AppLocation.get_data_path()
        self.data_directory_copy_check_box.setChecked(False)
        self.main_window.new_data_path = None
        self.main_window.set_copy_data(False)
        self.data_directory_copy_check_box.hide()
        self.data_directory_cancel_button.hide()
        self.new_data_directory_has_files_label.hide()

    def on_restart_needed(self, _):
        """
        Notify user about required restart.

        :param checked: The state of the check box (boolean).
        """
        if self.isVisible():
            QtWidgets.QMessageBox.information(self, translate('OpenLP.AdvancedTab', 'Restart Required'),
                                              translate('OpenLP.AdvancedTab',
                                                        'This change will only take effect once OpenLP '
                                                        'has been restarted.'))
