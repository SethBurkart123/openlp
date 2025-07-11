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
import sys
from argparse import Namespace
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import MagicMock, patch

import pytest
from PySide6 import QtCore, QtWidgets

# Mock QtWebEngineCore
sys.modules['PySide6.QtWebEngineCore'] = MagicMock()

from openlp.core.app import parse_options, backup_if_version_changed, main as app_main, setup_portable_settings
from openlp.core.common.platform import is_win
from openlp.core.common.settings import Settings
from openlp.core.ui.style import UiThemes


@pytest.fixture
def mocked_qapp():
    patcher = patch('openlp.core.app.QtWidgets.QApplication')
    yield patcher.start()
    patcher.stop()


@pytest.fixture
def app_main_env(mocked_qapp):
    with patch('openlp.core.app.Settings') as mock_settings, \
            patch('openlp.core.app.Registry') as mock_registry, \
            patch('openlp.core.app.AppLocation') as mock_apploc, \
            patch('openlp.core.app.LanguageManager'), \
            patch('openlp.core.app.qInitResources'), \
            patch('openlp.core.app.parse_options') as mocked_parse_options, \
            patch('openlp.core.app.QtWidgets.QMessageBox.warning') as mock_warn, \
            patch('openlp.core.app.QtWidgets.QMessageBox.information'), \
            patch('openlp.core.app.OpenLP') as mock_openlp, \
            patch('openlp.core.app.Server') as mock_server, \
            patch('openlp.core.app.sys'), \
            patch('openlp.core.app.FileLock'):
        mock_registry.return_value = MagicMock()
        mock_settings.return_value = MagicMock()
        openlp_server = MagicMock()
        mock_server.return_value = openlp_server
        openlp_server.is_another_instance_running.return_value = False
        mock_apploc.get_data_path.return_value = Path()
        mock_apploc.get_directory.return_value = Path()
        mocked_parse_options.return_value = Namespace(no_error_form=False, loglevel='warning', portable=False,
                                                      portablepath=None, no_web_server=False, display_custom_path=None,
                                                      rargs=[])
        mocked_qapp.return_value.devicePixelRatio.return_value = 1.0
        mock_warn.return_value = True
        openlp_instance = MagicMock()
        mock_openlp.return_value = openlp_instance
        openlp_instance.is_data_path_missing.return_value = False
        yield


def test_parse_options_basic():
    """
    Test the parse options process works
    """
    # GIVEN: a a set of system arguments.
    sys.argv[1:] = []

    # WHEN: We we parse them to expand to options
    args = parse_options()

    # THEN: the following fields will have been extracted.
    assert args.loglevel == 'warning', 'The log level should be set to warning'
    assert args.no_error_form is False, 'The no_error_form should be set to False'
    assert args.portable is False, 'The portable flag should be set to false'
    assert args.rargs == [], 'The service file should be blank'


def test_parse_options_debug():
    """
    Test the parse options process works for debug only
    """
    # GIVEN: a a set of system arguments.
    sys.argv[1:] = ['-l debug']

    # WHEN: We we parse them to expand to options
    args = parse_options()

    # THEN: the following fields will have been extracted.
    assert args.loglevel == ' debug', 'The log level should be set to debug'
    assert args.no_error_form is False, 'The no_error_form should be set to False'
    assert args.portable is False, 'The portable flag should be set to false'
    assert args.rargs == [], 'The service file should be blank'


def test_parse_options_debug_and_portable():
    """
    Test the parse options process works for debug and portable
    """
    # GIVEN: a a set of system arguments.
    sys.argv[1:] = ['--portable']

    # WHEN: We we parse them to expand to options
    args = parse_options()

    # THEN: the following fields will have been extracted.
    assert args.loglevel == 'warning', 'The log level should be set to warning'
    assert args.no_error_form is False, 'The no_error_form should be set to False'
    assert args.portable is True, 'The portable flag should be set to true'
    assert args.rargs == [], 'The service file should be blank'


def test_parse_options_portable_and_portable_path():
    """
    Test the parse options process works portable and portable-path
    """
    # GIVEN: a a set of system arguments.
    if is_win():
        data_path = 'c:\\temp\\openlp-data'
    else:
        data_path = '/tmp/openlp-data'
    sys.argv[1:] = ['--portable', '--portable-path', '{datapath}'.format(datapath=data_path)]

    # WHEN: We we parse them to expand to options
    args = parse_options()

    # THEN: the following fields will have been extracted.
    assert args.loglevel == 'warning', 'The log level should be set to warning'
    assert args.no_error_form is False, 'The no_error_form should be set to False'
    assert args.portable is True, 'The portable flag should be set to true'
    assert args.portablepath == data_path, 'The portable path should be set as expected'
    assert args.rargs == [], 'The service file should be blank'


def test_parse_options_all_no_file():
    """
    Test the parse options process works with two options
    """
    # GIVEN: a a set of system arguments.
    sys.argv[1:] = ['-l debug', '-p']

    # WHEN: We we parse them to expand to options
    args = parse_options()

    # THEN: the following fields will have been extracted.
    assert args.loglevel == ' debug', 'The log level should be set to debug'
    assert args.no_error_form is False, 'The no_error_form should be set to False'
    assert args.portable is True, 'The portable flag should be set to false'
    assert args.rargs == [], 'The service file should be blank'


def test_parse_options_file():
    """
    Test the parse options process works with a file
    """
    # GIVEN: a a set of system arguments.
    sys.argv[1:] = ['dummy_temp']

    # WHEN: We we parse them to expand to options
    args = parse_options()

    # THEN: the following fields will have been extracted.
    assert args.loglevel == 'warning', 'The log level should be set to warning'
    assert args.no_error_form is False, 'The no_error_form should be set to False'
    assert args.portable is False, 'The portable flag should be set to false'
    assert args.rargs == ['dummy_temp'], 'The service file should not be blank'


def test_parse_options_file_and_debug():
    """
    Test the parse options process works with a file and the debug log level
    """
    # GIVEN: a a set of system arguments.
    sys.argv[1:] = ['-l debug', 'dummy_temp']

    # WHEN: We we parse them to expand to options
    args = parse_options()

    # THEN: the following fields will have been extracted.
    assert args.loglevel == ' debug', 'The log level should be set to debug'
    assert args.no_error_form is False, 'The no_error_form should be set to False'
    assert args.portable is False, 'The portable flag should be set to false'
    assert args.rargs == ['dummy_temp'], 'The service file should not be blank'


@patch('openlp.core.app.QtWidgets.QMessageBox.critical')
@patch('openlp.core.app.QtWidgets.QMessageBox.StandardButton')
def test_is_already_running_is_running_continue(MockedStandardButton, mocked_critical, qapp):
    """
    Test the is_already_running() method when OpenLP IS running and the user chooses to continue
    """
    # GIVEN: An OpenLP app and some mocks
    MockedStandardButton.return_value = 0
    mocked_critical.return_value = QtWidgets.QMessageBox.StandardButton.Yes

    # WHEN: is_already_running() is called
    qapp.is_already_running()

    # THEN: The result should be false
    MockedStandardButton.assert_called_once_with(QtWidgets.QMessageBox.StandardButton.Ok)
    mocked_critical.assert_called_once_with(None, 'Error',
                                            'OpenLP is already running on this machine. \nClosing this instance', 0)


@patch('openlp.core.app.QtWidgets.QApplication.processEvents')
def test_process_events(mocked_processEvents, qapp):
    """
    Test that the app.process_events() method simply calls the Qt method
    """
    # GIVEN: An app
    # WHEN: process_events() is called
    qapp.process_events()

    # THEN: processEvents was called
    mocked_processEvents.assert_called_once_with()


@patch('openlp.core.app.QtWidgets.QApplication.setOverrideCursor')
@patch('openlp.core.app.QtWidgets.QApplication.processEvents')
def test_set_busy_cursor(mocked_processEvents, mocked_setOverrideCursor, qapp):
    """
    Test that the set_busy_cursor() method sets the cursor
    """
    # GIVEN: An app
    # WHEN: set_busy_cursor() is called
    qapp.set_busy_cursor()

    # THEN: The cursor should have been set
    mocked_setOverrideCursor.assert_called_once_with(QtCore.Qt.CursorShape.BusyCursor)
    mocked_processEvents.assert_called_once_with()


@patch('openlp.core.app.QtWidgets.QApplication.restoreOverrideCursor')
@patch('openlp.core.app.QtWidgets.QApplication.processEvents')
def test_set_normal_cursor(mocked_restoreOverrideCursor, mocked_processEvents, qapp):
    """
    Test that the set_normal_cursor() method resets the cursor
    """
    # GIVEN: An app
    # WHEN: set_normal_cursor() is called
    qapp.set_normal_cursor()

    # THEN: The cursor should have been set
    mocked_restoreOverrideCursor.assert_called_once_with()
    mocked_processEvents.assert_called_once_with()


@patch('openlp.core.app.get_version')
@patch('openlp.core.app.QtWidgets.QMessageBox.question')
def test_backup_on_upgrade_first_install(mocked_question, mocked_get_version, qapp, settings):
    """
    Test that we don't try to backup on a new install
    """
    # GIVEN: Mocked data version and OpenLP version which are the same
    old_install = False
    MOCKED_VERSION = {
        'full': '2.4.0',
        'version': '2.4.0',
        'build': None
    }
    settings.setValue('core/application version', '2.4.0')
    mocked_get_version.return_value = MOCKED_VERSION
    mocked_question.return_value = QtWidgets.QMessageBox.StandardButton.No

    # WHEN: We check if a backup should be created
    qapp.backup_on_upgrade(old_install, False)

    # THEN: It should not ask if we want to create a backup
    assert settings.value('core/application version') == '2.4.0', 'Version should be the same!'
    assert mocked_question.call_count == 0, 'No question should have been asked!'


@patch('openlp.core.app.get_version')
@patch('openlp.core.app.QtWidgets.QMessageBox.question')
def test_backup_on_upgrade(mocked_question, mocked_get_version, qapp, settings):
    """
    Test that we try to backup on a new install
    """
    # GIVEN: Mocked data version and OpenLP version which are different
    old_install = True
    MOCKED_VERSION = {
        'full': '2.9.0.dev2963+97ba02d1f',
        'version': '2.9.0',
        'build': '97ba02d1f'
    }
    settings.setValue('core/application version', '2.4.6')
    qapp.splash = MagicMock()
    qapp.splash.isVisible.return_value = True
    mocked_get_version.return_value = MOCKED_VERSION
    mocked_question.return_value = QtWidgets.QMessageBox.StandardButton.No

    # WHEN: We check if a backup should be created
    qapp.backup_on_upgrade(old_install, True)

    # THEN: It should ask if we want to create a backup
    assert settings.value('core/application version') == '2.9.0', 'Version should be upgraded!'
    assert mocked_question.call_count == 1, 'A question should have been asked!'
    qapp.splash.hide.assert_called_once_with()
    qapp.splash.show.assert_called_once_with()


@patch('openlp.core.app.FirstTimeLanguageForm')
@patch('openlp.core.app.OpenLP')
@patch('openlp.core.app.sys')
@patch('openlp.core.app.backup_if_version_changed')
@patch('openlp.core.app.set_up_web_engine_cache')
@patch('openlp.core.app.set_up_logging')
@patch('openlp.core.app.check_for_variant_migration')
@patch('openlp.core.app.is_ui_theme')
@patch('openlp.core.app.is_ui_theme_dark')
def test_main(mock_is_ui_theme_dark: MagicMock, mock_is_ui_theme: MagicMock, mock_chk_var_migr: MagicMock,
              mock_logging: MagicMock, mock_web_cache: MagicMock, mock_backup: MagicMock, mock_sys: MagicMock,
              mock_openlp: MagicMock, mock_ftlang_form: MagicMock, mocked_qapp: MagicMock, app_main_env: None):
    """
    Test the main method performs primary actions
    """
    # GIVEN: A mocked openlp instance
    openlp_instance = MagicMock()
    mock_openlp.return_value = openlp_instance
    openlp_instance.is_data_path_missing.return_value = False
    mock_backup.return_value = True
    mock_chk_var_migr.side_effect = (lambda x: x)  # check_for_variant_migration should just return the input arg
    mock_ftlang_form_exec = MagicMock()
    mock_ftlang_form_exec.return_value = True
    mock_ftlang_form.return_value = mock_ftlang_form_exec
    mock_is_ui_theme.side_effect = lambda theme: theme == UiThemes.DefaultLight
    mock_is_ui_theme_dark.return_value = False

    # WHEN: the main method is run
    app_main()

    # THEN: Check the application is run and exited with logging and web cache path set
    openlp_instance.run.assert_called_once()
    mock_logging.assert_called_once()
    mock_web_cache.assert_called_once()
    mock_sys.exit.assert_called_once()
    mocked_qapp.setOrganizationName.assert_called_once_with('OpenLP')
    mocked_qapp.setApplicationName.assert_called_once_with('OpenLP')
    mocked_qapp.setOrganizationDomain.assert_called_once_with('openlp.org')


@pytest.mark.skipif(not is_win(), reason='This test only works on windows')
@patch('openlp.core.app.FirstTimeLanguageForm')
@patch('openlp.core.app.OpenLP')
@patch('openlp.core.app.sys')
@patch('openlp.core.app.backup_if_version_changed')
@patch('openlp.core.app.set_up_web_engine_cache')
@patch('openlp.core.app.set_up_logging')
@patch('openlp.core.app.check_for_variant_migration')
@patch('openlp.core.app.is_ui_theme')
@patch('openlp.core.app.is_ui_theme_dark')
def test_main_windows_darkmode_light(mock_is_ui_theme_dark: MagicMock, mock_is_ui_theme: MagicMock,
                                     mock_chk_var_migr: MagicMock, mock_logging: MagicMock, mock_web_cache: MagicMock,
                                     mock_backup: MagicMock, mock_sys: MagicMock, mock_openlp: MagicMock,
                                     mock_ftlang_form: MagicMock, mocked_qapp: MagicMock, app_main_env: None):
    """
    Test that Windows dark mode is set to 0 (light) when the selected UI theme is DefaultLight.
    """
    # GIVEN: A light theme and dark mode preference mocked appropriately
    openlp_instance = MagicMock()
    mock_openlp.return_value = openlp_instance
    openlp_instance.is_data_path_missing.return_value = False
    mock_backup.return_value = True
    mock_chk_var_migr.side_effect = (lambda x: x)
    mock_ftlang_form_exec = MagicMock()
    mock_ftlang_form_exec.return_value = True
    mock_ftlang_form.return_value = mock_ftlang_form_exec
    mock_is_ui_theme.side_effect = lambda theme: theme == UiThemes.DefaultLight
    mock_is_ui_theme_dark.return_value = True

    # WHEN: the main method is run
    app_main()

    # THEN: The Qt args should contain windows:darkmode=0
    args_passed = mocked_qapp.call_args[0][0]
    assert '-platform' in args_passed
    assert 'windows:darkmode=0' in args_passed


@pytest.mark.skipif(not is_win(), reason='This test only works on windows')
@patch('openlp.core.app.FirstTimeLanguageForm')
@patch('openlp.core.app.OpenLP')
@patch('openlp.core.app.sys')
@patch('openlp.core.app.backup_if_version_changed')
@patch('openlp.core.app.set_up_web_engine_cache')
@patch('openlp.core.app.set_up_logging')
@patch('openlp.core.app.check_for_variant_migration')
@patch('openlp.core.app.is_ui_theme')
@patch('openlp.core.app.is_ui_theme_dark')
def test_main_windows_darkmode_automatic_light(mock_is_ui_theme_dark: MagicMock, mock_is_ui_theme: MagicMock,
                                               mock_chk_var_migr: MagicMock, mock_logging: MagicMock,
                                               mock_web_cache: MagicMock, mock_backup: MagicMock, mock_sys: MagicMock,
                                               mock_openlp: MagicMock, mock_ftlang_form: MagicMock,
                                               mocked_qapp: MagicMock, app_main_env: None):
    """
    Test that Windows dark mode is set to 0 (light) when the theme is Automatic but dark mode is off.
    """
    # GIVEN: Automatic theme with light mode detected
    openlp_instance = MagicMock()
    mock_openlp.return_value = openlp_instance
    openlp_instance.is_data_path_missing.return_value = False
    mock_backup.return_value = True
    mock_chk_var_migr.side_effect = (lambda x: x)
    mock_ftlang_form_exec = MagicMock()
    mock_ftlang_form_exec.return_value = True
    mock_ftlang_form.return_value = mock_ftlang_form_exec
    mock_is_ui_theme.side_effect = lambda theme: theme == UiThemes.Automatic
    mock_is_ui_theme_dark.return_value = False

    # WHEN: the main method is run
    app_main()

    # THEN: The Qt args should contain windows:darkmode=0
    args_passed = mocked_qapp.call_args[0][0]
    assert '-platform' in args_passed
    assert 'windows:darkmode=0' in args_passed


@pytest.mark.skipif(not is_win(), reason='This test only works on windows')
@patch('openlp.core.app.FirstTimeLanguageForm')
@patch('openlp.core.app.OpenLP')
@patch('openlp.core.app.sys')
@patch('openlp.core.app.backup_if_version_changed')
@patch('openlp.core.app.set_up_web_engine_cache')
@patch('openlp.core.app.set_up_logging')
@patch('openlp.core.app.check_for_variant_migration')
@patch('openlp.core.app.is_ui_theme')
@patch('openlp.core.app.is_ui_theme_dark')
def test_main_windows_darkmode_dark(mock_is_ui_theme_dark: MagicMock, mock_is_ui_theme: MagicMock,
                                    mock_chk_var_migr: MagicMock, mock_logging: MagicMock, mock_web_cache: MagicMock,
                                    mock_backup: MagicMock, mock_sys: MagicMock, mock_openlp: MagicMock,
                                    mock_ftlang_form: MagicMock, mocked_qapp: MagicMock, app_main_env: None):
    """
    Test that Windows dark mode is set to 2 (dark) when the selected UI theme is DefaultDark.
    """
    # GIVEN: A dark theme selected and dark mode enabled
    openlp_instance = MagicMock()
    mock_openlp.return_value = openlp_instance
    openlp_instance.is_data_path_missing.return_value = False
    mock_backup.return_value = True
    mock_chk_var_migr.side_effect = (lambda x: x)
    mock_ftlang_form_exec = MagicMock()
    mock_ftlang_form_exec.return_value = True
    mock_ftlang_form.return_value = mock_ftlang_form_exec
    mock_is_ui_theme.side_effect = lambda theme: theme == UiThemes.DefaultDark
    mock_is_ui_theme_dark.return_value = True

    # WHEN: the main method is run
    app_main()

    # THEN: The Qt args should contain windows:darkmode=2
    args_passed = mocked_qapp.call_args[0][0]
    assert '-platform' in args_passed
    assert 'windows:darkmode=2' in args_passed


@patch('openlp.core.app.QtWidgets.QMessageBox.warning')
@patch('openlp.core.app.get_version')
@patch('openlp.core.app.AppLocation.get_data_path')
@patch('openlp.core.app.move')
def test_main_future_settings(mock_move: MagicMock, mock_get_path: MagicMock, mock_version: MagicMock,
                              mock_warn: MagicMock, app_main_env: None, settings: Settings):
    """
    Test the backup_if_version_changed method backs up data if version from the future and user consents
    """
    # GIVEN: A mocked openlp instance with mocked future settings
    settings.from_future = MagicMock(return_value=True)
    settings.version_mismatched = MagicMock(return_value=True)
    settings.clear = MagicMock()
    settings.upgrade_settings = MagicMock()
    settings.setValue('core/application version', '3.0.1')
    mock_warn.return_value = QtWidgets.QMessageBox.StandardButton.Yes
    MOCKED_VERSION = {
        'full': '2.9.3',
        'version': '2.9.3',
        'build': 'None'
    }
    mock_version.return_value = MOCKED_VERSION
    temp_folder = Path(mkdtemp())
    mock_get_path.return_value = temp_folder

    # WHEN: the main method is run
    result = backup_if_version_changed(settings)

    # THEN: Check everything was backed up, the settings were cleared and the warn prompt was shown
    assert result is True
    mock_move.assert_called_once()
    settings.clear.assert_called_once_with()
    settings.upgrade_settings.assert_called_once_with()
    mock_warn.assert_called_once()


if is_win():
    import os
    p_prefix = os.path.splitdrive(os.getcwd())[0]
else:
    p_prefix = ''


@pytest.mark.parametrize('portable_path, settings_path',
                         [('settings', str(Path(p_prefix + '/openlp/settings/Data/OpenLP.ini'))),
                          (None, str(Path(p_prefix + '/Data/OpenLP.ini'))),
                          (p_prefix + '/openlp/settings/', str(Path(p_prefix + '/openlp/settings/Data/OpenLP.ini')))])
@patch('openlp.core.app.Settings')
@patch('openlp.core.app.AppLocation')
def test_setup_portable_settings(MockAppLocation: MagicMock, MockSettings: MagicMock, portable_path: str,
                                 settings_path: str):
    """Test that the setup_portable_settings() function correctly creates the portable settings."""
    print(portable_path)
    print(settings_path)
    # GIVEN: A portable path, a mocked settings class
    MockAppLocation.get_directory.return_value = Path('/openlp/openlp')
    mocked_settings = MagicMock()
    MockSettings.return_value = mocked_settings
    MockSettings.IniFormat = Settings.IniFormat

    # WHEN: setup_portable_settings() is called
    result_path, settings = setup_portable_settings(portable_path)

    # THEN: The settings should be set up correctly
    MockSettings.setDefaultFormat.assert_called_once_with(Settings.IniFormat)
    MockSettings.set_filename.assert_called_once_with(Path(settings_path))
    assert settings is mocked_settings
