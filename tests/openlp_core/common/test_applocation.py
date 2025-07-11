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
Functional tests to test the AppLocation class and related methods.
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from openlp.core.common import get_frozen_path
from openlp.core.common.applocation import AppLocation


FILE_LIST = ['file1', 'file2', 'file3.txt', 'file4.txt', 'file5.mp3', 'file6.mp3']


@patch('openlp.core.common.applocation.AppLocation.get_directory')
@patch('openlp.core.common.applocation.create_paths')
@patch('openlp.core.common.applocation.os')
def test_get_data_path(mocked_os, mocked_create_paths, mocked_get_directory, mock_settings):
    """
    Test the AppLocation.get_data_path() method
    """
    # GIVEN: A mocked out Settings class and a mocked out AppLocation.get_directory()
    mock_settings.contains.return_value = False
    mocked_get_directory.return_value = Path('tests', 'dir')
    mocked_create_paths.return_value = True
    mocked_os.path.normpath.return_value = Path('tests', 'dir')

    # WHEN: we call AppLocation.get_data_path()
    data_path = AppLocation.get_data_path()

    # THEN: check that all the correct methods were called, and the result is correct
    mock_settings.contains.assert_called_with('advanced/data path')
    mocked_get_directory.assert_called_with(AppLocation.DataDir)
    mocked_create_paths.assert_called_with(Path('tests', 'dir'))
    assert data_path == Path('tests', 'dir'), 'Result should be "tests/dir"'


def test_get_data_path_with_custom_location(mock_settings):
    """
    Test the AppLocation.get_data_path() method when a custom location is set in the settings
    """
    # GIVEN: A mocked out Settings class which returns a custom data location
    mock_settings.contains.return_value = True
    mock_settings.value.return_value = Path('custom', 'dir')

    # WHEN: we call AppLocation.get_data_path()
    data_path = AppLocation.get_data_path()

    # THEN: the mocked Settings methods were called and the value returned was our set up value
    mock_settings.contains.assert_called_with('advanced/data path')
    mock_settings.value.assert_called_with('advanced/data path')
    assert data_path == Path('custom', 'dir'), 'Result should be "custom/dir"'


@patch('openlp.core.common.applocation.Path.glob')
@patch('openlp.core.common.applocation.AppLocation.get_data_path')
def test_get_files_no_section_no_extension(mocked_get_data_path, mocked_glob):
    """
    Test the AppLocation.get_files() method with no parameters passed.
    """
    # GIVEN: Our mocked modules/methods.
    mocked_glob.return_value = [Path('/dir/file5.mp3'), Path('/dir/file6.mp3')]
    mocked_get_data_path.return_value = Path('/dir')

    # When: Get the list of files.
    result = AppLocation.get_files()

    # Then: Check if the section parameter was used correctly, and the glob argument was passed.
    mocked_glob.assert_called_once_with('*')
    assert result == [Path('file5.mp3'), Path('file6.mp3')], 'The file lists should be identical.'


@patch('openlp.core.common.applocation.Path.glob')
@patch('openlp.core.common.applocation.AppLocation.get_data_path')
def test_get_files(mocked_get_data_path, mocked_glob):
    """
    Test the AppLocation.get_files() method with all parameters passed.
    """
    # GIVEN: Our mocked modules/methods.
    mocked_glob.return_value = [Path('/dir/section/file5.mp3'), Path('/dir/section/file6.mp3')]
    mocked_get_data_path.return_value = Path('/dir')

    # When: Get the list of files.
    result = AppLocation.get_files('section', '.mp3')

    # Then: The section parameter was used correctly, and the glob argument was passed..
    mocked_glob.assert_called_once_with('*.mp3')
    assert result == [Path('file5.mp3'), Path('file6.mp3')], 'The file lists should be identical.'


@patch('openlp.core.common.applocation.AppLocation.get_data_path')
@patch('openlp.core.common.applocation.create_paths')
def test_get_section_data_path(mocked_create_paths, mocked_get_data_path):
    """
    Test the AppLocation.get_section_data_path() method
    """
    # GIVEN: A mocked out AppLocation.get_data_path()
    mocked_get_data_path.return_value = Path('test', 'dir')
    mocked_create_paths.return_value = True

    # WHEN: we call AppLocation.get_data_path()
    data_path = AppLocation.get_section_data_path('section')

    # THEN: check that all the correct methods were called, and the result is correct
    mocked_create_paths.assert_called_with(Path('test', 'dir', 'section'))
    assert data_path == Path('test', 'dir', 'section'), 'Result should be "test/dir/section"'


@patch('openlp.core.common.applocation.get_frozen_path')
def test_get_directory_for_app_dir(mocked_get_frozen_path):
    """
    Test the AppLocation.get_directory() method for AppLocation.AppDir
    """
    # GIVEN: A mocked out _get_frozen_path function
    mocked_get_frozen_path.return_value = Path('app', 'dir')

    # WHEN: We call AppLocation.get_directory
    directory = AppLocation.get_directory(AppLocation.AppDir)

    # THEN: check that the correct directory is returned
    assert directory == Path.cwd() / Path('app', 'dir'), 'Directory should be "app/dir"'


@patch('openlp.core.common.applocation.get_frozen_path')
@patch('openlp.core.common.applocation.resolve')
@patch('openlp.core.common.applocation.sys')
def test_get_directory_for_plugins_dir(mocked_sys, mocked_resolve, mocked_get_frozen_path):
    """
    Test the AppLocation.get_directory() method for AppLocation.PluginsDir
    """
    # GIVEN: get_frozen_path, resolve and sys are mocked out
    mocked_resolve.return_value = Path('dir/plugins')
    mocked_get_frozen_path.return_value = Path('dir')
    mocked_sys.frozen = 1
    mocked_sys.argv = ['openlp']

    # WHEN: We call AppLocation.get_directory
    directory = AppLocation.get_directory(AppLocation.PluginsDir)

    # THEN: The correct directory should be returned
    assert directory == Path('dir', 'plugins'), 'Directory should be "dir/plugins"'
    mocked_resolve.assert_called_once_with(Path('dir', 'plugins'))


def test_get_directory_for_language_dir_from_source():
    """
    Test the AppLocation.get_directory() method for AppLocation.LanguageDir
    """
    # GIVEN: OpenLP is running from source (the default)
    import openlp
    openlp_resource_path = Path(openlp.__file__, '..', '..').resolve() / 'resources' / 'i18n'

    # WHEN: We call AppLocation.get_directory
    directory = AppLocation.get_directory(AppLocation.LanguageDir)

    # THEN: The correct directory should be returned
    assert directory == openlp_resource_path


@patch('openlp.core.common.applocation.resolve')
@patch('openlp.core.common.applocation.is_win')
@patch('openlp.core.common.applocation.os.getenv')
def test_get_directory_for_language_dir_from_windows(mocked_getenv, mocked_is_win, mocked_resolve):
    """
    Test the AppLocation.get_directory() method for AppLocation.LanguageDir
    """
    # GIVEN: OpenLP is running standalone
    import openlp
    openlp_i18n_path = Path(openlp.__file__).parent.resolve() / 'i18n'
    mocked_resolve.side_effect = [Path('tmp'), openlp_i18n_path]
    mocked_is_win.return_value = True
    mocked_getenv.return_value = 'fake/path'

    # WHEN: We call AppLocation.get_directory
    directory = AppLocation.get_directory(AppLocation.LanguageDir)

    # THEN: The correct directory should be returned
    mocked_resolve.assert_called_with(openlp_i18n_path)
    assert directory == openlp_i18n_path


@patch('openlp.core.common.applocation.resolve')
@patch('openlp.core.common.applocation.is_win')
@patch('openlp.core.common.applocation.is_macosx')
@patch('openlp.core.common.applocation.os.getenv')
def test_get_directory_for_language_dir_from_macosx(mocked_getenv, mocked_is_macosx, mocked_is_win, mocked_resolve):
    """
    Test the AppLocation.get_directory() method for AppLocation.LanguageDir
    """
    # GIVEN: OpenLP is running standalone
    import openlp
    openlp_i18n_path = Path(openlp.__file__).parent.resolve() / 'i18n'
    mocked_resolve.side_effect = [Path('tmp'), openlp_i18n_path]
    mocked_is_win.return_value = False
    mocked_is_macosx.return_value = True
    mocked_getenv.return_value = 'fake/path'

    # WHEN: We call AppLocation.get_directory
    directory = AppLocation.get_directory(AppLocation.LanguageDir)

    # THEN: The correct directory should be returned
    mocked_resolve.assert_called_with(openlp_i18n_path)
    assert directory == openlp_i18n_path


@patch('openlp.core.common.applocation.resolve')
@patch('openlp.core.common.applocation.is_win')
@patch('openlp.core.common.applocation.is_macosx')
@patch('openlp.core.common.applocation.PlatformDirs')
@patch('openlp.core.common.applocation.Path.exists', autospec=True)
def test_get_directory_for_language_dir_from_linux(mocked_exists, MockPlatformDirs, mocked_is_macosx, mocked_is_win,
                                                   mocked_resolve):
    """
    Test the AppLocation.get_directory() method for AppLocation.LanguageDir
    """
    # GIVEN: OpenLP is running standalone
    openlp_i18n_path = Path('/usr/share/openlp/i18n')
    mocked_resolve.return_value = openlp_i18n_path
    mocked_is_win.return_value = False
    mocked_is_macosx.return_value = False
    candidate_dirs = ['/usr/share/gnome/openlp', '/usr/local/share/openlp', '/usr/share/openlp']
    mocked_dirs = MagicMock(site_data_dir=os.pathsep.join(candidate_dirs))
    MockPlatformDirs.return_value = mocked_dirs
    mocked_exists.side_effect = lambda p: p in candidate_dirs + [openlp_i18n_path]

    # WHEN: We call AppLocation.get_directory
    directory = AppLocation.get_directory(AppLocation.LanguageDir)

    # THEN: The correct directory should be returned
    mocked_resolve.assert_called_with(openlp_i18n_path)
    assert directory == openlp_i18n_path


@patch('openlp.core.common.sys')
def test_get_frozen_path_in_unfrozen_app(mocked_sys):
    """
    Test the _get_frozen_path() function when the application is not frozen (compiled by PyInstaller)
    """
    # GIVEN: The sys module "without" a "frozen" attribute
    mocked_sys.frozen = None

    # WHEN: We call _get_frozen_path() with two parameters
    frozen_path = get_frozen_path('frozen', 'not frozen')

    # THEN: The non-frozen parameter is returned
    assert frozen_path == 'not frozen', '_get_frozen_path should return "not frozen"'


@patch('openlp.core.common.sys')
def test_get_frozen_path_in_frozen_app(mocked_sys):
    """
    Test the get_frozen_path() function when the application is frozen (compiled by PyInstaller)
    """
    # GIVEN: The sys module *with* a "frozen" attribute
    mocked_sys.frozen = 1

    # WHEN: We call _get_frozen_path() with two parameters
    frozen_path = get_frozen_path('frozen', 'not frozen')

    # THEN: The frozen parameter is returned
    assert frozen_path == 'frozen', 'Should return "frozen"'
