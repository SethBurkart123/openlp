# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2024 OpenLP Developers                              #
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
Package to test the openlp.core.ui.media package.
"""
from pathlib import Path

from unittest import skipUnless
from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtCore

from openlp.core.state import State
from openlp.core.common.platform import is_linux, is_macosx
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.ui import DisplayControllerType, HideMode
from openlp.core.ui.media.mediacontroller import MediaController
from openlp.core.ui.media import ItemMediaInfo, MediaState, MediaType
from openlp.core.widgets.toolbar import OpenLPToolbar

from tests.utils.constants import RESOURCE_PATH


TEST_PATH = RESOURCE_PATH / 'media'
TEST_MEDIA = [['avi_file.avi', 61495], ['mp3_file.mp3', 134426], ['mpg_file.mpg', 9404], ['mp4_file.mp4', 188336]]


@pytest.fixture
def media_env(qapp, registry: Registry):
    """Local test setup - qapp need to allow tests to run standalone.
    """
    Registry().register('main_window', MagicMock())
    Registry().register('service_manager', MagicMock())
    media_controller = MediaController()
    yield media_controller


@patch('openlp.core.ui.media.mediacontroller.register_views')
def test_setup(mocked_register_views: MagicMock, media_env: MediaController):
    """
    Test that the setup method is called correctly
    """
    # GIVEN: A media controller, and function list
    expected_functions_list = ['bootstrap_initialise', 'bootstrap_post_set_up', 'bootstrap_completion',
                               'playbackPlay', 'playbackPause', 'playbackStop', 'playbackLoop', 'seek_slider',
                               'volume_slider', 'media_hide', 'media_blank', 'media_unblank', 'songs_hide',
                               'songs_blank', 'songs_unblank']
    # WHEN: Setup is called
    media_env.setup()
    # THEN: the functions should be defined along with the api blueprint
    assert list(Registry().functions_list.keys()) == expected_functions_list, \
        f'The function list should have been {(Registry().functions_list.keys())}'
    mocked_register_views.assert_called_once(), 'The media blueprint has not been registered'


def test_initialise_good(media_env: MediaController, state_media: State):
    """
    Test that the bootstrap initialise method is called correctly
    """
    # GIVEN: a mocked setup
    with patch.object(media_env.media_controller, u'setup') as mocked_setup:
        # THEN: The underlying method is called
        media_env.media_controller.bootstrap_initialise()
    # THEN: The following should have happened
    mocked_setup.assert_called_once(), 'The setup function has been called'


def test_initialise_missing_vlc(media_env: MediaController, state_media: State):
    """
    Test that the bootstrap initialise method is called correctly with no VLC
    """
    # GIVEN: a mocked setup and no VLC
    with patch.object(media_env.media_controller, u'setup') as mocked_setup, \
         patch('openlp.core.ui.media.mediacontroller.get_vlc', return_value=False):
        # THEN: The underlying method is called
        media_env.media_controller.bootstrap_initialise()
    # THEN: The following should have happened
    mocked_setup.assert_called_once(), 'The setup function has been called'
    text = State().get_text()
    if not is_macosx():
        assert text.find("python3-vlc") > 0, "VLC should not be missing"


@patch('openlp.core.ui.media.mediacontroller.pymediainfo_available', False)
def test_initialise_missing_pymedia(media_env: MediaController, state_media: State):
    """
    Test that the bootstrap initialise method is called correctly with no pymediainfo
    """
    # GIVEN: a mocked setup and no pymedia
    with patch.object(media_env.media_controller, u'setup') as mocked_setup:
        # THEN: The underlying method is called
        media_env.media_controller.bootstrap_initialise()
    # THEN: The following should have happened
    mocked_setup.assert_called_once(), 'The setup function has been called'
    text = State().get_text()
    if not is_macosx():
        assert text.find("python3-pymediainfo") > 0, "PyMedia should not be missing"


@skipUnless(is_linux(), "Linux only")
def test_initialise_missing_pymedia_fedora(media_env: MediaController, state_media: State):
    """
    Test that the bootstrap initialise method is called correctly with no VLC
    """
    # GIVEN: a mocked setup and no VLC
    with patch.object(media_env.media_controller, u'setup') as mocked_setup, \
         patch('openlp.core.ui.media.mediacontroller.get_vlc', return_value=False), \
         patch('openlp.core.ui.media.mediacontroller.is_linux', return_value=True):
        # WHEN: The underlying method is called
        media_env.media_controller.bootstrap_initialise()
    # THEN: The following should have happened
    mocked_setup.assert_called_once(), 'The setup function has been called'
    text = State().get_text()
    assert text.find("python3-pymediainfo") == -1, "PyMedia should be missing"
    assert text.find("python3-vlc") > 0, "VLC should not be missing"
    assert text.find("rpmfusion") > 0, "RPMFusion should provide the modules"


@skipUnless(is_linux(), "Linux only")
def test_initialise_missing_pymedia_not_fedora(media_env: MediaController, state_media: State):
    """
    Test that the bootstrap initialise method is called correctly with no VLC
    """
    # GIVEN: a mocked setup and no VLC
    with patch.object(media_env.media_controller, u'setup') as mocked_setup, \
         patch('openlp.core.ui.media.mediacontroller.get_vlc', return_value=False), \
         patch('openlp.core.ui.media.mediacontroller.is_linux', return_value=False):
        # WHEN: The underlying method is called
        media_env.media_controller.bootstrap_initialise()
    # THEN: The following should have happened
    mocked_setup.assert_called_once(), 'The setup function has been called'
    text = State().get_text()
    assert text.find("python3-pymediainfo") == -1, "PyMedia should be missing"
    assert text.find("python3-vlc") > 0, "VLC should not be missing"
    assert text.find("rpmfusion") == -1, "RPMFusion should not provide the modules"


def test_initialise_missing_pymedia_mac_os(media_env: MediaController, state_media: State):
    """
    Test that the bootstrap initialise method is called correctly with no VLC
    """
    # GIVEN: a mocked setup and no VLC
    with patch.object(media_env.media_controller, u'setup') as mocked_setup, \
         patch('openlp.core.ui.media.mediacontroller.get_vlc', return_value=False), \
         patch('openlp.core.ui.media.mediacontroller.is_macosx', return_value=True):
        # WHEN: The underlying method is called
        media_env.media_controller.bootstrap_initialise()
    # THEN: The following should have happened
    mocked_setup.assert_called_once(), 'The setup function has been called'
    text = State().get_text()
    assert text.find("python3-pymediainfo") == -1, "PyMedia should be missing"
    assert text.find("python3-vlc") == -1, "PyMedia should be missing"
    assert text.find("videolan") > 0, "VideoLAN should provide the modules"


def test_post_set_up_good(media_env: MediaController, state_media: State, registry: Registry):
    """
    Test the Bootstrap post set up assuming all functions are good
    """
    # GIVEN: A working  environment
    mocked_live_controller = MagicMock()
    registry.register('live_controller', mocked_live_controller)
    mocked_preview_controller = MagicMock()
    registry.register('preview_controller', mocked_preview_controller)
    media_env.vlc_live_media_stop = MagicMock()
    media_env.vlc_preview_media_stop = MagicMock()
    media_env.vlc_live_media_tick = MagicMock()
    media_env.vlc_preview_media_tick = MagicMock()
    State().add_service("mediacontroller", 0)
    State().update_pre_conditions("mediacontroller", True)
    # WHEN: I call the function
    with patch.object(media_env.media_controller, u'setup_display') as mocked_display:
        media_env.bootstrap_post_set_up()
    # THEN: the environment is set up correctly
    assert mocked_display.call_count == 2, "Should have been called twice"
    text = State().get_text()
    assert text.find("No Displays") == -1, "No Displays have been disable"
    mocked_display.assert_any_call(mocked_live_controller, False)  # Live Controller
    mocked_display.assert_any_call(mocked_preview_controller, True)  # Preview Controller


def test_media_state_live(media_env: MediaController, state_media: State):
    """
    Test the Bootstrap post set up assuming all functions are good
    """
    # GIVEN: A working  environment
    media_env.vlc_live_media_stop = MagicMock()
    media_env.vlc_preview_media_stop = MagicMock()
    media_env.vlc_preview_media_tick = MagicMock()
    mocked_live_controller = MagicMock()
    mocked_live_controller.is_live = True
    mocked_live_controller.media_info.media_type = MediaType.Audio
    Registry().register('live_controller', mocked_live_controller)
    mocked_preview_controller = MagicMock()
    Registry().register('preview_controller', mocked_preview_controller)
    media_env.media_controller.vlc_player = MagicMock()
    media_env.media_controller._display_controllers = MagicMock(return_value=mocked_live_controller)
    State().add_service("mediacontroller", 0)
    State().update_pre_conditions("mediacontroller", True)
    # WHEN: I call the function
    with patch.object(media_env.media_controller, u'setup_display') as mocked_display:
        media_env.bootstrap_post_set_up()
    # THEN: the environment is set up correctly
    text = State().get_text()
    assert text.find("No Displays") == -1, "No Displays have been disable"
    mocked_display.assert_any_call(mocked_live_controller, False)  # Live Controller
    mocked_display.assert_any_call(mocked_preview_controller, True)  # Preview Controller


def test_post_set_up_no_controller(media_env: MediaController, state_media: State):
    """
    Test the Bootstrap post set up assuming all functions are good
    """
    # GIVEN: A working environment
    media_env.vlc_live_media_stop = MagicMock()
    media_env.vlc_preview_media_stop = MagicMock()
    media_env.vlc_live_media_tick = MagicMock()
    media_env.vlc_preview_media_tick = MagicMock()
    State().add_service("mediacontroller", 0)
    State().update_pre_conditions("mediacontroller", False)
    # WHEN: I call the function
    with patch.object(media_env.media_controller, u'setup_display') as mocked_display:
        media_env.bootstrap_post_set_up()
    # THEN: the environment is set up correctly
    assert mocked_display.call_count == 0, "Should have not have been called twice"
    text = State().get_text()
    assert text.find("No Displays") == -1, "No Displays have been disable"


def test_post_set_up_controller_exception(media_env: MediaController, state_media: State, registry: Registry):
    """
    Test the Bootstrap post set up assuming all functions are good
    """
    # GIVEN: A working environment
    registry.register('live_controller', MagicMock())
    registry.register('preview_controller', MagicMock())
    media_env.vlc_live_media_stop = MagicMock()
    media_env.vlc_preview_media_stop = MagicMock()
    media_env.vlc_live_media_tick = MagicMock()
    media_env.vlc_preview_media_tick = MagicMock()
    State().add_service("mediacontroller", 0)
    State().update_pre_conditions("mediacontroller", True)
    State().add_service("media_live", 0)
    State().update_pre_conditions("media_live", True)
    # WHEN: I call the function
    with patch.object(media_env.media_controller, u'setup_display') as mocked_display:
        mocked_display.side_effect = AttributeError()
        try:
            media_env.bootstrap_post_set_up()
        except AttributeError:
            pass
    # THEN: the environment is set up correctly
    text = State().get_text()
    assert text.find("Displays") > 0, "Displays have been disable"
    assert mocked_display.call_count == 2, "Should have been called twice"


def test_resize(media_env):
    """
    Test that the resize method is called correctly
    """
    # GIVEN: A media controller, a player and a display
    mocked_player = MagicMock()
    mocked_display = MagicMock()

    # WHEN: resize() is called
    media_env.media_controller._resize(mocked_display, mocked_player)

    # THEN: The player's resize method should be called correctly
    mocked_player.resize.assert_called_with(mocked_display)


def test_load_video(media_env, settings):
    """
    Test that the load_video runs correctly
    """
    # GIVEN: A media controller and a service item
    mocked_slide_controller = MagicMock()
    mocked_service_item = MagicMock()
    mocked_service_item.length = 10
    mocked_service_item.end_time = 10
    mocked_service_item.start_time = 1
    mocked_service_item.is_capable.return_value = False
    settings.setValue('media/live volume', 1)

    media_env.media_controller.current_media_players = MagicMock()
    media_env.media_controller._check_file_type = MagicMock(return_value=True)
    media_env.media_controller._display_controllers = MagicMock(return_value=mocked_slide_controller)
    media_env.media_controller._define_display = MagicMock()
    media_env.media_controller.media_reset = MagicMock()
    media_env.media_controller.media_play = MagicMock()
    media_env.media_controller.set_controls_visible = MagicMock()

    # WHEN: load_video() is called
    media_env.media_controller.load_video(DisplayControllerType.Live, mocked_service_item)

    # THEN: The current controller's media should be reset
    #       The volume should be set from the settings
    #       The video should have autoplayed
    #       The controls should have been made visible
    media_env.media_controller.media_reset.assert_called_once_with(mocked_slide_controller)
    media_env.media_controller.media_play.assert_called_once_with(mocked_slide_controller, False)
    media_env.media_controller.set_controls_visible.assert_called_once_with(mocked_slide_controller, True)
    assert mocked_slide_controller.media_info.is_background is False


def test_check_file_type_null(media_env):
    """
    Test that we don't try to play media when no players available
    """
    # GIVEN: A mocked UiStrings, get_used_players, controller, display and service_item
    mocked_controller = MagicMock()
    mocked_display = MagicMock()
    media_env.media_controller.media_players = MagicMock()

    # WHEN: calling _check_file_type when no players exists
    ret = media_env.media_controller._check_file_type(mocked_controller, mocked_display)

    # THEN: it should return False
    assert ret is False, '_check_file_type should return False when no media file matches.'


def test_check_file_video(media_env):
    """
    Test that we process a file that is valid
    """
    # GIVEN: A mocked UiStrings, get_used_players, controller, display and service_item
    mocked_controller = MagicMock()
    mocked_display = MagicMock()
    media_env.media_controller.media_players = MagicMock()
    mocked_controller.media_info = ItemMediaInfo()
    mocked_controller.media_info.file_info = [TEST_PATH / 'mp3_file.mp3']
    media_env.media_controller.current_media_players = {}
    media_env.media_controller.vlc_playerpl = MagicMock()

    # WHEN: calling _check_file_type when no players exists
    ret = media_env.media_controller._check_file_type(mocked_controller, mocked_display)

    # THEN: it should return False
    assert ret is True, '_check_file_type should return True when audio file is present and matches.'


def test_check_file_audio(media_env):
    """
    Test that we process a file that is valid
    """
    # GIVEN: A mocked UiStrings, get_used_players, controller, display and service_item
    mocked_controller = MagicMock()
    mocked_display = MagicMock()
    media_env.media_controller.media_players = MagicMock()
    mocked_controller.media_info = ItemMediaInfo()
    mocked_controller.media_info.file_info = [TEST_PATH / 'mp4_file.mp4']
    media_env.media_controller.current_media_players = {}
    media_env.media_controller.vlc_playerpl = MagicMock()

    # WHEN: calling _check_file_type when no players exists
    ret = media_env.media_controller._check_file_type(mocked_controller, mocked_display)

    # THEN: it should return False
    assert ret is True, '_check_file_type should return True when media file is present and matches.'


def test_media_play_msg(media_env):
    """
    Test that the media controller responds to the request to play a loaded video
    """
    # GIVEN: A media controller and a message with two elements
    message = (1, 2)

    # WHEN: media_play_msg() is called
    with patch.object(media_env.media_controller, u'media_play') as mocked_media_play:
        media_env.media_controller.media_play_msg(message)

    # THEN: The underlying method is called
    mocked_media_play.assert_called_with(1)


def test_media_pause_msg(media_env):
    """
    Test that the media controller responds to the request to pause a loaded video
    """
    # GIVEN: A media controller and a message with two elements
    message = (1, 2)

    # WHEN: media_play_msg() is called
    with patch.object(media_env.media_controller, u'media_pause') as mocked_media_pause:
        media_env.media_controller.media_pause_msg(message)

    # THEN: The underlying method is called
    mocked_media_pause.assert_called_with(1)


def test_media_stop_msg(media_env):
    """
    Test that the media controller responds to the request to stop a loaded video
    """
    # GIVEN: A media controller and a message with two elements
    message = (1, 2)

    # WHEN: media_play_msg() is called
    with patch.object(media_env.media_controller, u'media_stop') as mocked_media_stop:
        media_env.media_controller.media_stop_msg(message)

    # THEN: The underlying method is called
    mocked_media_stop.assert_called_with(1)


def test_media_stop(media_env, settings):
    """
    Test that the media controller takes the correct actions when stopping media
    """
    # GIVEN: A live media controller and a message with two elements
    mocked_slide_controller = MagicMock()
    mocked_media_player = MagicMock()
    mocked_display = MagicMock(hide_mode=None)
    mocked_slide_controller.controller_type = 'media player'
    mocked_slide_controller.media_info = ItemMediaInfo()
    mocked_slide_controller.media_info.is_background = False
    mocked_slide_controller.set_hide_mode = MagicMock()
    mocked_slide_controller.is_live = True
    media_env.media_controller.current_media_players = {'media player': mocked_media_player}
    media_env.media_controller.media_info = ItemMediaInfo()
    media_env.media_controller.is_theme_background = False
    media_env.media_controller.live_hide_timer = MagicMock()
    media_env.media_controller._define_display = MagicMock(return_value=mocked_display)

    # WHEN: media_stop() is called
    result = media_env.media_controller.media_stop(mocked_slide_controller)

    # THEN: Result should be successful, media player should be stopped and the hide timer should have started
    #       The controller's hide mode should be set to Blank
    assert result is True
    mocked_media_player.stop.assert_called_once_with(mocked_slide_controller)
    media_env.media_controller.live_hide_timer.start.assert_called_once()
    mocked_slide_controller.set_hide_mode.assert_called_once_with(HideMode.Blank)


def test_media_stop_no_hide_change(media_env, settings):
    """
    Test that the media_stop doesn't change the hide mode of OpenLP when screen is visible
    """
    # GIVEN: A live media controller and a message with two elements
    mocked_slide_controller = MagicMock()
    mocked_media_player = MagicMock()
    mocked_display = MagicMock(hide_mode=HideMode.Screen)
    mocked_slide_controller.controller_type = 'media player'
    mocked_slide_controller.media_info = ItemMediaInfo()
    mocked_slide_controller.media_info.is_background = False
    mocked_slide_controller.set_hide_mode = MagicMock()
    mocked_slide_controller.is_live = True
    media_env.media_controller.current_media_players = {'media player': mocked_media_player}
    media_env.media_controller.is_theme_background = False
    media_env.media_controller.live_hide_timer = MagicMock()
    media_env.media_controller._define_display = MagicMock(return_value=mocked_display)

    # WHEN: media_stop() is called
    result = media_env.media_controller.media_stop(mocked_slide_controller)

    # THEN: Result should be successful, media player should be stopped and the hide timer should have started
    #       The controller's hide mode should not have been set
    assert result is True
    mocked_media_player.stop.assert_called_once_with(mocked_slide_controller)
    media_env.media_controller.live_hide_timer.start.assert_called_once()
    mocked_slide_controller.set_hide_mode.assert_not_called()


def test_media_volume_msg(media_env):
    """
    Test that the media controller responds to the request to change the volume
    """
    # GIVEN: A media controller and a message with two elements
    message = (1, [50])

    # WHEN: media_play_msg() is called
    with patch.object(media_env.media_controller, u'media_volume') as mocked_media_volume:
        media_env.media_controller.media_volume_msg(message)

    # THEN: The underlying method is called
    mocked_media_volume.assert_called_with(1, 50)


def test_media_seek_msg(media_env):
    """
    Test that the media controller responds to the request to seek to a particular position
    """
    # GIVEN: A media controller and a message with two elements
    message = (1, [800])

    # WHEN: media_play_msg() is called
    with patch.object(media_env.media_controller, u'media_seek') as mocked_media_seek:
        media_env.media_controller.media_seek_msg(message)

    # THEN: The underlying method is called
    mocked_media_seek.assert_called_with(1, 800)


def test_media_reset(media_env):
    """
    Test that the media controller conducts the correct actions when resetting
    """
    # GIVEN: A media controller, mocked slide controller, mocked media player and mocked display
    mocked_slide_controller = MagicMock()
    mocked_media_player = MagicMock()
    mocked_slide_controller.controller_type = 'media player'
    mocked_slide_controller.media_info = MagicMock(is_background=False)
    mocked_slide_controller.is_live = False
    media_env.media_controller.current_media_players = {'media player': mocked_media_player}
    media_env.media_controller.live_hide_timer = MagicMock()
    media_env.media_controller._media_set_visibility = MagicMock()

    # WHEN: media_reset() is called
    media_env.media_controller.media_reset(mocked_slide_controller)

    # THEN: The display should be shown, media should be hidden and removed
    media_env.media_controller._media_set_visibility.assert_called_once_with(mocked_slide_controller, False)
    assert 'media player' not in media_env.media_controller.current_media_players


def test_media_hide(media_env, registry):
    """
    Test that the media controller conducts the correct actions when hiding
    """
    # GIVEN: A media controller, mocked slide controller, mocked media player and mocked display
    mocked_slide_controller = MagicMock()
    mocked_media_player = MagicMock()
    mocked_media_player.get_live_state.return_value = MediaState.Playing
    mocked_slide_controller.controller_type = 'media player'
    mocked_slide_controller.media_info = MagicMock(is_background=False)
    mocked_slide_controller.get_hide_mode = MagicMock(return_value=None)
    mocked_slide_controller.is_live = False
    Registry().register('live_controller', mocked_slide_controller)
    media_env.media_controller.current_media_players = {'media player': mocked_media_player}
    media_env.media_controller.live_kill_timer = MagicMock(isActive=MagicMock(return_value=False))
    media_env.media_controller._media_set_visibility = MagicMock()
    media_env.media_controller.media_pause = MagicMock()

    # WHEN: media_hide() is called
    media_env.media_controller.media_hide(is_live=True)

    # THEN: media should be paused and hidden, but the player should still exist
    media_env.media_controller.media_pause.assert_called_once_with(mocked_slide_controller)
    media_env.media_controller._media_set_visibility.assert_called_once_with(mocked_slide_controller, False)
    assert 'media player' in media_env.media_controller.current_media_players


@pytest.mark.skip(reason="no way of currently testing this")
@pytest.mark.parametrize('file_name,media_length', TEST_MEDIA)
def test_media_length(file_name, media_length, media_env):
    """
    Check the duration of a few different files via MediaInfo
    """
    # GIVEN: a media file
    full_path = TEST_PATH / file_name

    # WHEN the media data is retrieved
    results = media_env.media_controller.media_length(full_path)

    # THEN you can determine the run time
    assert results == media_length, f'The correct duration for {file_name} should be {media_length}, was {results}'


def test_media_non_existent(media_env):
    """
    Test that when media file does not exist, we default to 0
    """
    # GIVEN: A path to a nonexistent media file
    file_path = 'path/to/nonexistent/video.mkv'

    # WHEN the media data is retrieved
    duration = media_env.media_controller.media_length(file_path)

    # THEN the duration should be zero
    assert duration == 0, 'The duration should be 0'


@patch('openlp.core.ui.media.mediacontroller.MediaInfo.parse')
@patch('openlp.core.ui.media.mediacontroller.Path')
def test_media_length_duration_none(MockPath, mocked_parse, media_env):
    """
    Test that when MediaInfo doesn't give us a duration, we default to 0
    """
    # GIVEN: A fake media file and a mocked MediaInfo.parse() function
    mocked_parse.return_value = MagicMock(tracks=[MagicMock(duration=None)])
    file_path = 'path/to/fake/video.mkv'

    # WHEN the media data is retrieved
    duration = media_env.media_controller.media_length(file_path)

    # THEN the duration should be zero
    assert duration == 0, 'The duration should be 0'


@patch('openlp.core.ui.media.mediacontroller.MediaInfo.parse')
@patch('openlp.core.ui.media.mediacontroller.Path')
def test_media_length_duration_string_digits(MockPath, mocked_parse, media_env):
    """
    Test that when MediaInfo gives us a duration, but it is a string, we typecast it
    """
    # GIVEN: A fake media file and a mocked MediaInfo.parse() function
    mocked_parse.return_value = MagicMock(tracks=[MagicMock(duration='546')])
    file_path = 'path/to/fake/video.mkv'

    # WHEN the media data is retrieved
    duration = media_env.media_controller.media_length(file_path)

    # THEN you can determine the run time
    assert duration == 546, 'The duration should be 546'


@patch('openlp.core.ui.media.mediacontroller.MediaInfo.parse')
@patch('openlp.core.ui.media.mediacontroller.Path')
def test_media_length_duration_string_alpha(MockPath, mocked_parse, media_env):
    """
    Test that when MediaInfo gives us a duration, but it is a string of nonsense, we default to 0
    """
    # GIVEN: A fake media file and a mocked MediaInfo.parse() function
    mocked_parse.return_value = MagicMock(tracks=[MagicMock(duration='sdffgh')])
    file_path = 'path/to/fake/video.mkv'

    # WHEN the media data is retrieved
    duration = media_env.media_controller.media_length(file_path)

    # THEN you can determine the run time
    assert duration == 0, 'The duration should be 0'


@patch('openlp.core.ui.media.mediacontroller.MediaInfo.parse')
def test_media_length_duration_old_version(mocked_parse, media_env):
    """
    Test that when a version of MediaInfo < 4.3 is installed, a file name is passed directly to the parse method
    """
    # GIVEN: A fake media file and a mocked MediaInfo.parse() function
    from openlp.core.ui.media import mediacontroller
    mediacontroller.pymediainfo_version = '4.0.1'
    mocked_parse.return_value = MagicMock(tracks=[MagicMock(duration=10)])
    file_path = 'path/to/fake/video.mkv'

    # WHEN the media data is retrieved
    duration = media_env.media_controller.media_length(file_path)

    # THEN you can determine the run time
    mocked_parse.assert_called_once_with('path/to/fake/video.mkv')
    assert duration == 10, 'The duration should be 10'


@patch('openlp.core.ui.media.mediacontroller.Path')
@patch('openlp.core.ui.media.mediacontroller.MediaInfo.parse')
def test_media_length_duration_new_version(mocked_parse, MockPath, media_env):
    """
    Test that when a version of MediaInfo > 4.3 is installed, a file OBJECT is passed to the parse method
    """
    # GIVEN: A fake media file and a mocked MediaInfo.parse() function
    from openlp.core.ui.media import mediacontroller
    mediacontroller.pymediainfo_version = '5.0.3'
    mocked_file = MagicMock()
    MockPath.return_value.open.return_value.__enter__.return_value = mocked_file
    mocked_parse.return_value = MagicMock(tracks=[MagicMock(duration=8)])
    file_path = 'path/to/fake/video.mkv'

    # WHEN the media data is retrieved
    duration = media_env.media_controller.media_length(file_path)

    # THEN you can determine the run time
    mocked_parse.assert_called_once_with(mocked_file)
    assert duration == 8, 'The duration should be 8'


@patch('openlp.core.ui.media.mediacontroller.MediaInfo.can_parse')
def test_media_length_no_can_parse(mocked_can_parse, media_env):
    """
    Check that 0 is returned when MediaInfo cannot parse
    """
    # GIVEN: A fake media file and a mocked MediaInfo.can_parse() function
    mocked_can_parse.return_value = False
    file_path = Path('path/to/fake/video.mkv')

    # WHEN the media data is retrieved
    duration = media_env.media_controller.media_length(file_path)

    # THEN you can determine the run time
    assert duration == 0, 'The duration should be 0'


def test_on_media_play(media_env):
    """
    Test the on_media_play method
    """
    # GIVEN: A mocked live controller and a mocked media_play() method
    mocked_live_controller = MagicMock()
    Registry().register('live_controller', mocked_live_controller)
    media_env.media_controller.media_play = MagicMock()

    # WHEN: the on_media_play() method is called
    media_env.media_controller.on_media_play()

    # The mocked live controller should be called
    media_env.media_controller.media_play.assert_called_once_with(mocked_live_controller)


def test_on_media_pause(media_env):
    """
    Test the on_media_pause method
    """
    # GIVEN: A mocked live controller and a mocked media_pause() method
    mocked_live_controller = MagicMock()
    Registry().register('live_controller', mocked_live_controller)
    media_env.media_controller.media_pause = MagicMock()

    # WHEN: the on_media_pause() method is called
    media_env.media_controller.on_media_pause()

    # The mocked live controller should be called
    media_env.media_controller.media_pause.assert_called_once_with(mocked_live_controller)


def test_on_media_stop(media_env):
    """
    Test the on_media_stop method
    """
    # GIVEN: A mocked live controller and a mocked media_stop() method
    mocked_live_controller = MagicMock()
    Registry().register('live_controller', mocked_live_controller)
    media_env.media_controller.media_stop = MagicMock()

    # WHEN: the on_media_stop() method is called
    media_env.media_controller.on_media_stop()

    # The mocked live controller should be called
    media_env.media_controller.media_stop.assert_called_once_with(mocked_live_controller)


def test_display_controllers_live(media_env):
    """
    Test that the display_controllers() method returns the live controller when requested
    """
    # GIVEN: A mocked live controller
    mocked_live_controller = MagicMock()
    mocked_preview_controller = MagicMock()
    Registry().register('live_controller', mocked_live_controller)
    Registry().register('preview_controller', mocked_preview_controller)

    # WHEN: display_controllers() is called with DisplayControllerType.Live
    controller = media_env.media_controller._display_controllers(DisplayControllerType.Live)

    # THEN: the controller should be the live controller
    assert controller is mocked_live_controller


def test_display_controllers_preview(media_env):
    """
    Test that the display_controllers() method returns the preview controller when requested
    """
    # GIVEN: A mocked live controller
    mocked_live_controller = MagicMock()
    mocked_preview_controller = MagicMock()
    Registry().register('live_controller', mocked_live_controller)
    Registry().register('preview_controller', mocked_preview_controller)

    # WHEN: display_controllers() is called with DisplayControllerType.Preview
    controller = media_env.media_controller._display_controllers(DisplayControllerType.Preview)

    # THEN: the controller should be the live controller
    assert controller is mocked_preview_controller


def test_set_controls_visible(media_env):
    """
    Test that "set_controls_visible" sets the media controls on the controller to be visible or not
    """
    # GIVEN: A mocked controller
    mocked_controller = MagicMock()

    # WHEN: Set to visible
    MediaController.set_controls_visible(mocked_controller, True)

    # THEN: The media controls should have been set to visible
    mocked_controller.mediabar.setVisible.assert_called_once_with(True)


@patch('openlp.core.ui.media.mediacontroller.ItemMediaInfo')
def test_setup_display(MockItemMediaInfo, media_env):
    """
    Test that the display/controllers are set up correctly
    """
    # GIVEN: A media controller object and some mocks
    mocked_media_info = MagicMock()
    MockItemMediaInfo.return_value = mocked_media_info
    media_env.media_controller.vlc_player = MagicMock()
    mocked_display = MagicMock()
    media_env.media_controller._define_display = MagicMock(return_value=mocked_display)
    media_env.media_controller.vlc_playerpl = MagicMock()
    controller = MagicMock()

    # WHEN: setup_display() is called
    media_env.media_controller.setup_display(controller, True)

    # THEN: The right calls should have been made
    assert controller.media_info == mocked_media_info
    assert controller.has_audio is False
    media_env.media_controller._define_display.assert_called_with(controller)
    media_env.media_controller.vlc_playerpl.setup(controller, mocked_display, False)


def test_media_play(media_env):
    """
    Test that the display/controllers are set up correctly
    """
    # GIVEN: A mocked controller where is_background is false
    media_env.current_media_players = MagicMock()
    Registry().register('settings', MagicMock())
    media_env.live_timer = MagicMock()
    media_env.live_hide_timer = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.media_info.is_background = False
    media_env.is_theme_background = False

    # WHEN: media_play is called
    result = media_env.media_play(mocked_controller)

    # THEN: The web display should become transparent (only tests that the theme is reset here)
    # And the function should return true to indicate success
    assert result is True
    media_env.live_hide_timer.stop.assert_called_once_with()
    mocked_controller._set_theme.assert_called_once()


def test_decide_autoplay_no_media_autounblank_not_hidden(media_env, settings):
    """
    Test that no media, that is not hidden, behaves
    """
    # GIVEN: A service item that has no linked media and is not hidden
    mocked_service_item = MagicMock()
    mocked_service_item.requires_media.return_value = False
    settings.setValue('core/auto unblank', True)
    settings.setValue('media/media auto start', QtCore.Qt.CheckState.Unchecked)

    # WHEN: decide_autoplay() is called
    ret = media_env.media_controller.decide_autoplay(mocked_service_item, False)

    # THEN: Autoplay will obey the following
    assert ret is False, "The Media should NOT have been autoplayed"


def test_decide_autoplay_media_autounblank_hidden_theme(media_env, settings):
    """
    Test that media, that has show theme active with
    setting auto unblank active and media auto start inactive, behaves
    """
    # GIVEN: A service item that has linked media and has show theme active with
    # setting auto unblank active and media auto start inactive
    mocked_service_item = MagicMock()
    mocked_service_item.requires_media.return_value = True
    settings.setValue('core/auto unblank', True)
    settings.setValue('media/media auto start', QtCore.Qt.CheckState.Unchecked)
    # WHEN: decide_autoplay() is called
    ret = media_env.media_controller.decide_autoplay(mocked_service_item, HideMode.Theme)
    # THEN: Autoplay will obey the following
    assert ret is True, "The Media should have been autoplayed"


def test_decide_autoplay_media_hidden_screen(media_env, settings):
    """
    Test that media, that has show desktop active with
    setting auto unblank inactive and media auto start inactive, behaves
    """
    # GIVEN: A service item that has linked media and has show desktop active with
    # setting auto unblank inactive and media auto start inactive
    mocked_service_item = MagicMock()
    mocked_service_item.requires_media.return_value = True
    settings.setValue('core/auto unblank', False)
    settings.setValue('media/media auto start', QtCore.Qt.CheckState.Unchecked)
    # WHEN: decide_autoplay() is called
    ret = media_env.media_controller.decide_autoplay(mocked_service_item, HideMode.Screen)
    # THEN: Autoplay will obey the following
    assert ret is False, "The Media should NOT have been autoplayed"


def test_decide_autoplay_no_media_autostart_not_hidden(media_env, settings):
    """
    Test that no media, that is not hidden and will auto start with
    setting auto unblank inactive and media auto start inactive, behaves
    """
    # GIVEN: A service item that has no linked media and has media auto start and
    # is not hidden with setting auto unblank inactive and media auto start inactive
    mocked_service_item = MagicMock()
    mocked_service_item.requires_media.return_value = False
    mocked_service_item.item.will_auto_start.return_value = True
    settings.setValue('core/auto unblank', False)
    settings.setValue('media/media auto start', QtCore.Qt.CheckState.Unchecked)
    # WHEN: decide_autoplay() is called
    ret = media_env.media_controller.decide_autoplay(mocked_service_item, False)
    # THEN: Autoplay will obey the following
    assert ret is False, "The Media should NOT have been autoplayed"


def test_decide_autoplay_no_media_global_autostart_not_hidden(media_env, settings):
    """
    Test that no media, that is not hidden with setting auto unblank inactive
    and media auto start active, behaves
    """
    # GIVEN: A service item that has no linked media and is not hidden
    # with setting auto unblank inactive and media auto start active
    mocked_service_item = MagicMock()
    mocked_service_item.requires_media.return_value = False
    mocked_service_item.item.will_auto_start.return_value = False
    settings.setValue('core/auto unblank', False)
    settings.setValue('media/media auto start', QtCore.Qt.CheckState.Checked)
    # WHEN: decide_autoplay() is called
    ret = media_env.media_controller.decide_autoplay(mocked_service_item, False)
    # THEN: Autoplay will obey the following
    assert ret is False, "The Media should NOT have been autoplayed"


def test_decide_autoplay_media_autounblank_hidden_blank(media_env, settings):
    """
    Test that media, that has show black active with
    setting auto unblank active and media auto start inactive, behaves
    """
    # GIVEN: A service item that has linked media and has show black active
    # with setting auto unblank active and media auto start inactive
    mocked_service_item = MagicMock()
    mocked_service_item.requires_media.return_value = True
    settings.setValue('core/auto unblank', True)
    settings.setValue('media/media auto start', QtCore.Qt.CheckState.Unchecked)
    # WHEN: decide_autoplay() is called
    ret = media_env.media_controller.decide_autoplay(mocked_service_item, HideMode.Blank)
    # THEN: Autoplay will obey the following
    assert ret is True, "The Media should have be autoplayed"


def test_media_bar_play(media_env, settings):
    """
    Test that media bar is set correctly following a play event
    """
    # GIVEN: A media controller and a service item
    mocked_controller = MagicMock()
    mocked_controller.media_info = ItemMediaInfo()
    mocked_controller.mediabar = OpenLPToolbar(None)
    mocked_controller.mediabar.actions['playbackPlay'] = MagicMock()
    mocked_controller.mediabar.actions['playbackPause'] = MagicMock()
    mocked_controller.mediabar.actions['playbackStop'] = MagicMock()
    mocked_controller.mediabar.actions['playbackLoop'] = MagicMock()
    media_env.media_controller.current_media_players = MagicMock()
    mocked_controller.media_info.is_theme_background = False
    settings.setValue('media/live loop', False)
    # WHEN: _media_bar() is called
    media_env.media_controller._media_bar(mocked_controller, "play")
    # THEN: The following functions should have been called
    mocked_controller.mediabar.actions['playbackPlay'].setDisabled.assert_called_with(True)
    mocked_controller.mediabar.actions['playbackPause'].setDisabled.assert_called_with(False)
    mocked_controller.mediabar.actions['playbackStop'].setDisabled.assert_called_with(False)


@pytest.mark.parametrize("mode", ["pause", "stop", "reset"])
def test_media_bar_stop(media_env, settings, mode):
    """
    Test that media bar is set correctly following a list of events
    """
    # GIVEN: A media controller and a service item
    mocked_controller = MagicMock()
    mocked_controller.media_info = ItemMediaInfo()
    mocked_controller.mediabar = OpenLPToolbar(None)
    mocked_controller.mediabar.actions['playbackPlay'] = MagicMock()
    mocked_controller.mediabar.actions['playbackPause'] = MagicMock()
    mocked_controller.mediabar.actions['playbackStop'] = MagicMock()
    mocked_controller.mediabar.actions['playbackLoop'] = MagicMock()
    media_env.media_controller.current_media_players = MagicMock()
    mocked_controller.media_info.is_theme_background = False
    settings.setValue('media/live loop', False)
    # WHEN: _media_bar() is called
    media_env.media_controller._media_bar(mocked_controller, mode)
    # THEN: The following functions should have been called
    mocked_controller.mediabar.actions['playbackPlay'].setDisabled.assert_called_with(False)
    mocked_controller.mediabar.actions['playbackPause'].setDisabled.assert_called_with(True)
    mocked_controller.mediabar.actions['playbackStop'].setDisabled.assert_called_with(False)


@pytest.mark.parametrize("back, repeat, result", [(False, True, False),
                                                  (True, True, False),
                                                  (False, False, False)])
def test_media_bar_loop_disabled(media_env: MediaController, settings: Settings, back: bool, repeat: bool,
                                 result: bool):
    """
    Test that media bar is set correctly following a list of events
    """
    # GIVEN: A media controller and a service item
    mocked_controller = MagicMock()
    mocked_controller.media_info = ItemMediaInfo()
    mocked_controller.is_live = True
    mocked_controller.controller_type = 1  # Live
    mocked_controller.media_info.is_background = back
    mocked_controller.media_info.is_theme_background = False
    mocked_controller.mediabar = OpenLPToolbar(None)
    mocked_controller.mediabar.actions['playbackPlay'] = MagicMock()
    mocked_controller.mediabar.actions['playbackPause'] = MagicMock()
    mocked_controller.mediabar.actions['playbackStop'] = MagicMock()
    mocked_controller.mediabar.actions['playbackLoop'] = MagicMock()
    mocked_vlc_player = MagicMock()
    mocked_vlc_player.can_repeat.return_value = repeat
    media_env.current_media_players = {1: mocked_vlc_player}
    # WHEN: _media_bar() is called
    media_env.media_controller._media_bar(mocked_controller, "load")
    # THEN: The following functions should have been called
    mocked_controller.mediabar.actions['playbackLoop'].setDisabled.assert_called_with(result)


@pytest.mark.parametrize("loop, result", [(False, False), (True, True)])
def test_media_bar_loop_checked(media_env: MediaController, settings: Settings, loop: bool, result: bool):
    """
    Test that media bar is set correctly following a list of events
    """
    # GIVEN: A media controller and a service item
    mocked_controller = MagicMock()
    mocked_controller.media_info = ItemMediaInfo()
    mocked_controller.is_live = True
    mocked_controller.controller_type = 1  # Live
    mocked_controller.media_info.is_background = True
    mocked_controller.media_info.is_theme_background = False
    mocked_controller.media_info.media_type = MediaType.Video
    mocked_controller.mediabar = OpenLPToolbar(None)
    mocked_controller.mediabar.actions['playbackPlay'] = MagicMock()
    mocked_controller.mediabar.actions['playbackPause'] = MagicMock()
    mocked_controller.mediabar.actions['playbackStop'] = MagicMock()
    mocked_controller.mediabar.actions['playbackLoop'] = MagicMock()
    mocked_vlc_player = MagicMock()
    mocked_vlc_player.can_repeat.return_value = True
    media_env.current_media_players = {1: mocked_vlc_player}
    settings.setValue('media/live loop', loop)
    # WHEN: _media_bar() is called
    media_env.media_controller._media_bar(mocked_controller, "load")
    # THEN: The following functions should have been called
    mocked_controller.mediabar.actions['playbackLoop'].setChecked.assert_called_with(result)
