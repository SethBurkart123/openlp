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
The :mod:`~openlp.core.ui.media.mediacontroller` module is the control module for all media playing.
"""
import logging
from pathlib import Path
from typing import Type, Union

try:
    from pymediainfo import MediaInfo, __version__ as pymediainfo_version
    pymediainfo_available = True
except ImportError:
    pymediainfo_available = False
    pymediainfo_version = '0.0'

from PyQt5 import QtCore, QtWidgets

from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.path import path_to_str
from openlp.core.common.platform import is_linux, is_macosx
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.display.window import DisplayWindow
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.ui import critical_error_message_box, warning_message_box
from openlp.core.state import State, MessageType
from openlp.core.ui import DisplayControllerType, HideMode
from openlp.core.ui.slidecontroller import SlideController
from openlp.core.ui.media import MediaState, ItemMediaInfo, MediaType, parse_optical_path, parse_stream_path, \
    get_volume, toggle_looping_playback, is_looping_playback, save_volume
from openlp.core.ui.media.remote import register_views
from openlp.core.ui.media.vlcplayer import VlcPlayer, get_vlc
from openlp.core.ui.media.vlcplayerpl import VlcPlayerPL


log = logging.getLogger(__name__)

HIDE_DELAY_TIME = 2500


class MediaController(QtWidgets.QWidget, RegistryBase, LogMixin, RegistryProperties):
    """
    The implementation of the Media Controller which manages how media is played.
    """

    vlc_live_media_tick = QtCore.pyqtSignal()
    vlc_preview_media_tick = QtCore.pyqtSignal()
    vlc_live_media_stop = QtCore.pyqtSignal()
    vlc_preview_media_stop = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """
        """
        super(MediaController, self).__init__(parent)
        self.log_info('MediaController Initialising')

    def setup(self):
        self.vlc_player = None
        self.vlc_playerpl = None
        self.current_media_players = {}
        # Timer for video state
        self.live_hide_timer = QtCore.QTimer()
        self.live_hide_timer.setSingleShot(True)
        self.live_kill_timer = QtCore.QTimer()
        self.live_kill_timer.setSingleShot(True)
        # Signals
        self.live_hide_timer.timeout.connect(self._on_media_hide_live)
        self.live_kill_timer.timeout.connect(self._on_media_kill_live)
        Registry().register_function('playbackPlay', self.media_play_msg)
        Registry().register_function('playbackPause', self.media_pause_msg)
        Registry().register_function('playbackStop', self.media_stop_msg)
        Registry().register_function('playbackLoop', self.media_loop_msg)
        Registry().register_function('seek_slider', self.media_seek_msg)
        Registry().register_function('volume_slider', self.media_volume_msg)
        Registry().register_function('media_hide', self.media_hide)
        Registry().register_function('media_blank', self.media_blank)
        Registry().register_function('media_unblank', self.media_unblank)
        # Signals for background video
        Registry().register_function('songs_hide', self.media_hide)
        Registry().register_function('songs_blank', self.media_blank)
        Registry().register_function('songs_unblank', self.media_unblank)
        register_views()

    def bootstrap_initialise(self):
        """
        Check to see if we have any media Player's available.
        """
        self.setup()
        self.vlc_player = VlcPlayer(self)
        self.vlc_playerpl = VlcPlayerPL(self)
        State().add_service('mediacontroller', 0)
        State().add_service('media_live', 0)
        has_vlc = get_vlc()
        if has_vlc and pymediainfo_available:
            State().update_pre_conditions('mediacontroller', True)
            State().update_pre_conditions('media_live', True)
        else:
            if hasattr(self.main_window, 'splash') and self.main_window.splash.isVisible():
                self.main_window.splash.hide()
            message_type = MessageType.Error
            generic_message = translate('OpenLP.MediaController',
                                        'OpenLP requires the following libraries in order to show videos and other '
                                        'media, but they are not installed. Please install these libraries to enable '
                                        'media playback in OpenLP.')
            fedora_rpmfusion = translate('OpenLP.MediaController',
                                         'To install these libraries, you will need to enable the RPMFusion '
                                         'repository: https://rpmfusion.org/')
            if is_macosx():
                message = translate('OpenLP.MediaController',
                                    '<strong>OpenLP could not detect VLC.</strong> You will not be able to play media '
                                    'without it. Please download and install from the VLC web site: '
                                    '<a href="https://www.videolan.org/vlc/download-macosx.html">'
                                    'https://www.videolan.org/vlc/</a>')
                message_type = MessageType.Information
            else:
                packages = []
                if not has_vlc:
                    packages.append('python3-vlc')
                if not pymediainfo_available:
                    packages.append('python3-pymediainfo')
                message = generic_message + '\n\n' + ', '.join(packages)
                if not has_vlc and is_linux(distro='fedora'):
                    message += '\n\n' + fedora_rpmfusion
            State().missing_text('media_live', message, message_type)
        return True

    def bootstrap_post_set_up(self):
        """
        Set up the controllers.
        :return:
        """
        if State().check_preconditions('mediacontroller'):
            try:
                self.vlc_live_media_tick.connect(self._media_state_live)
                self.vlc_preview_media_tick.connect(self._media_state_preview)
                self.vlc_live_media_stop.connect(self.live_media_stopped)
                self.vlc_preview_media_stop.connect(self.preview_media_stopped)
                self.setup_display(self.live_controller, False)
            except AttributeError:
                State().update_pre_conditions('media_live', False)
                State().missing_text('media_live', translate(
                    'OpenLP.MediaController', 'No Displays have been configured, '
                                              'so Live Media has been disabled'))
            self.setup_display(self.preview_controller, True)

    def _display_controllers(self, controller_type: DisplayControllerType) -> SlideController:
        """
        Decides which controller to use.

        :param controller_type: The controller type where a player will be placed
        :return the correct Controller
        """
        if controller_type == DisplayControllerType.Live:
            return self.live_controller
        return self.preview_controller

    def _media_state_live(self) -> None:
        """
        Check if there is a running Live media Player and do some updating stuff (e.g. update the UI)
        """
        if DisplayControllerType.Live in self.current_media_players:
            media_player = self.current_media_players[DisplayControllerType.Live]
            media_player.resize(self.live_controller)
            media_player.update_ui(self.live_controller, self._define_display(self.live_controller))
            self.tick(self.live_controller)
        else:
            self.media_stop(self.live_controller)

    def _media_state_preview(self) -> None:
        """
        Check if there is a running Preview media Player and do updating stuff (e.g. update the UI)
        """
        if DisplayControllerType.Preview in self.current_media_players:
            media_player = self.current_media_players[DisplayControllerType.Preview]
            media_player.resize(self.preview_controller)
            media_player.update_ui(self.preview_controller, self._define_display(self.preview_controller))
            self.tick(self.preview_controller)
        else:
            self.media_stop(self.preview_controller)

    def live_media_stopped(self) -> None:
        self.media_stop(self.live_controller)
        self.tick(self.live_controller)
        if Registry().get('settings').value('media/live loop') or self.live_controller.media_info.is_theme_background:
            self.has_started = False
            self.media_play(self.live_controller)

    def preview_media_stopped(self) -> None:
        self.media_stop(self.preview_controller)
        self.tick(self.preview_controller)
        if Registry().get('settings').value('media/preview loop') or \
                self.preview_controller.media_info.is_theme_background:
            self.has_started = False
            self.media_play(self.preview_controller)

    def setup_display(self, controller: SlideController, preview: bool) -> None:
        """
        After a new display is configured, all media related widgets will be created too

        :param controller:  Display on which the output is to be played
        :param preview: Whether the display is a main or preview display
        """
        controller.media_info = ItemMediaInfo()
        controller.has_audio = True
        if preview:
            controller.has_audio = False
        self.vlc_player.setup(controller, self._define_display(controller))
        self.vlc_playerpl.setup(controller, self._define_display(controller))

    @staticmethod
    def set_controls_visible(controller: SlideController, value: int) -> None:
        """
        After a new display is configured, all media related widget will be created too

        :param controller: The controller on which controls act.
        :param value: control name to be changed.
        """
        # Generic controls
        controller.mediabar.setVisible(value)

    @staticmethod
    def _resize(controller: SlideController, player) -> None:
        """
        After Mainwindow changes or Splitter moved all related media widgets have to be resized

        :param controller: The display on which output is playing.
        :param player:  The player which is doing the playing.
        """
        player.resize(controller)

    def load_video(self, source, service_item, hidden: bool = False, is_theme_background: bool = False) -> bool:
        """
        Loads and starts a video to run and sets the stored sound value.

        :param source: Where the call originated form
        :param service_item: The player which is doing the playing

        :param hidden: The player which is doing the playing
        :param is_theme_background: Is the theme providing a background
        """
        controller = self._display_controllers(source)
        controller.media_info.is_theme_background = is_theme_background
        log.debug(f'load_video is_live:{controller.is_live}')
        # stop running videos
        self.media_reset(controller)
        controller.media_info = ItemMediaInfo()
        controller.media_info.is_theme_background = is_theme_background
        controller.media_info.media_type = MediaType.Video
        # background will always loop video.
        if service_item.is_capable(ItemCapabilities.HasBackgroundAudio):
            controller.media_info.file_info = [file_path for (file_path, file_hash) in service_item.background_audio]
            controller.media_info.media_type = MediaType.Audio
            # is_background indicates we shouldn't override the normal display
            controller.media_info.is_background = True
        else:
            if service_item.is_capable(ItemCapabilities.HasBackgroundStream):
                (name, mrl, options) = parse_stream_path(service_item.stream_mrl)
                controller.media_info.file_info = (mrl, options)
                controller.media_info.is_background = True
                controller.media_info.media_type = MediaType.Stream
            elif service_item.is_capable(ItemCapabilities.HasBackgroundVideo):
                controller.media_info.file_info = [service_item.video_file_name]
                service_item.media_length = self.media_length(service_item.video_file_name)
                controller.media_info.is_background = True
            else:
                controller.media_info.file_info = [service_item.get_frame_path()]
        display = self._define_display(controller)
        # if this is an optical device use special handling
        if service_item.is_capable(ItemCapabilities.IsOptical):
            self.log_debug(f'video is optical  live={controller.is_live}')
            path_string = path_to_str(service_item.get_frame_path())
            (name, title, audio_track, subtitle_track, start, end, clip_name) = parse_optical_path(path_string)
            is_valid = self.media_setup_optical(name, title, audio_track, subtitle_track, start, end, display,
                                                controller)
        elif service_item.is_capable(ItemCapabilities.CanStream):
            self.log_debug(f'video is stream  live={controller.is_live}')
            path = service_item.get_frames()[0]['path']
            controller.media_info.media_type = MediaType.Stream
            (name, mrl, options) = parse_stream_path(path)
            controller.media_info.file_info = (mrl, options)
            is_valid = self._check_file_type(controller, display)
        else:
            self.log_debug(f'standard media, is not optical or stream, live={controller.is_live}')
            controller.media_info.length = service_item.media_length
            controller.media_info.start_time = service_item.start_time
            controller.media_info.timer = service_item.start_time
            controller.media_info.end_time = service_item.end_time
            is_valid = self._check_file_type(controller, display)
        if not is_valid:
            # Media could not be loaded correctly
            critical_error_message_box(UiStrings().UnsupportedFile,
                                       UiStrings().UnsupportedFile)
            return False
        self.log_debug('video media type: {tpe} '.format(tpe=str(controller.media_info.media_type)))
        # If both the preview and live view have a stream, make sure only the live view continues streaming
        if controller.media_info.media_type == MediaType.Stream:
            if controller.is_live:
                if self.preview_controller.media_info.media_type == MediaType.Stream:
                    self.log_warning('stream can only be displayed in one instance, killing preview stream')
                    warning_message_box(translate('MediaPlugin.MediaItem', 'Unable to Preview Stream'),
                                        translate('MediaPlugin.MediaItem',
                                                  'Closing Preview to allow Live Stream'))

                    self.preview_controller.on_media_close()
            else:
                if self.live_controller.media_info.media_type == MediaType.Stream:
                    self.log_warning('stream cannot be previewed while also streaming live')
                    warning_message_box(translate('MediaPlugin.MediaItem', 'Unable to Preview Stream '),
                                        translate('MediaPlugin.MediaItem',
                                                  'Unable to preview when live is currently streaming'))

                    return
        self._media_bar(controller, 'load')
        if self.decide_autoplay(service_item, hidden):
            start_hidden = controller.media_info.is_theme_background and controller.is_live and \
                (controller.current_hide_mode == HideMode.Blank or controller.current_hide_mode == HideMode.Screen)
            if not self.media_play(controller, start_hidden):
                critical_error_message_box(UiStrings().UnsupportedFile,
                                           UiStrings().UnsupportedFile)
                return False
        self._update_seek_ui(controller)
        self.set_controls_visible(controller, True)
        self.log_debug('use {nm} controller'.
                       format(nm=self.current_media_players[controller.controller_type].display_name))
        return True

    def decide_autoplay(self, service_item, hidden: bool) -> bool:
        """
        Function to decide if we can / want to autoplay a media item

        :param service_item: The Media Service item
        :param hidden: Is the display hidden at present?
        :return: Can we autoplay the media.
        """
        is_autoplay = False
        if (service_item.requires_media()):
            if self.settings.value('core/auto unblank'):
                is_autoplay = True
            elif not hidden and (
                    service_item.will_auto_start or
                    self.settings.value('media/media auto start') == QtCore.Qt.CheckState.Checked):
                is_autoplay = True
        return is_autoplay

    @staticmethod
    def media_length(media_path: Union[str, Path]) -> int:
        """
        Uses Media Info to obtain the media length

        :param media_path: The file path to be checked..
        """
        if MediaInfo.can_parse():
            media_data = None
            if pymediainfo_version < '4.3':
                # pymediainfo only introduced file objects in 4.3, so if this is an older version, we'll have to use
                # the old method. See https://gitlab.com/openlp/openlp/-/issues/1187
                media_data = MediaInfo.parse(str(media_path))
            else:
                # pymediainfo has an issue opening non-ascii file names, so pass it a file object instead
                # See https://gitlab.com/openlp/openlp/-/issues/1041
                file_path = Path(media_path)
                if file_path.is_file():
                    with file_path.open('rb') as media_file:
                        media_data = MediaInfo.parse(media_file)
            if media_data is not None:
                # duration returns in milli seconds
                duration = media_data.tracks[0].duration
                # It appears that sometimes we get a string. Let's try to interpret that as int, or fall back to 0
                # See https://gitlab.com/openlp/openlp/-/issues/1387
                if isinstance(duration, str):
                    if duration.strip().isdigit():
                        duration = int(duration.strip())
                    else:
                        duration = 0
                return duration or 0
        return 0

    def media_setup_optical(self, filename, title, audio_track, subtitle_track, start, end,
                            display: Type[DisplayWindow], controller: SlideController):
        """
        Setup playback of optical media

        :param filename: Path of the optical device/drive.
        :param title: The main/title track to play.
        :param audio_track: The audio track to play.
        :param subtitle_track: The subtitle track to play.
        :param start: Start position in milliseconds.
        :param end: End position in milliseconds.
        :param display: The display to play the media.
        :param controller: The media controller.
        :return: True if setup succeeded else False.
        """
        # stop running videos
        self.media_reset(controller)
        # Setup media info
        controller.media_info = ItemMediaInfo()
        controller.media_info.file_info = QtCore.QFileInfo(filename)
        if audio_track == -1 and subtitle_track == -1:
            controller.media_info.media_type = MediaType.CD
        else:
            controller.media_info.media_type = MediaType.DVD
        controller.media_info.start_time = start
        controller.media_info.timer = start
        controller.media_info.end_time = end
        controller.media_info.length = (end - start)
        controller.media_info.title_track = title
        controller.media_info.audio_track = audio_track
        controller.media_info.subtitle_track = subtitle_track
        # When called from mediaitem display is None
        if display is None:
            display = controller.preview_display
        self.vlc_player.load(controller, display, filename)
        self._resize(controller, self.vlc_player)
        self.current_media_players[controller.controller_type] = self.vlc_player
        return True

    def _check_file_type(self, controller: SlideController, display: DisplayWindow):
        """
        Select the correct media Player type from the prioritized Player list

        :param controller: First element is the controller which should be used
        :param display: Which display to use
        """
        if controller.media_info.media_type == MediaType.Stream:
            self._resize(controller, self.vlc_player)
            if self.vlc_player.load(controller, display, controller.media_info.file_info):
                self.current_media_players[controller.controller_type] = self.vlc_player
                return True
            return False
        for file in controller.media_info.file_info:
            if not file.is_file and not self.vlc_playerpl.can_folder:
                return False
            file = str(file)
            self._resize(controller, self.vlc_playerpl)
            if self.vlc_playerpl.load(controller, display, file):
                self.current_media_players[controller.controller_type] = self.vlc_playerpl
                return True
        return False

    def media_play_msg(self, msg: list):
        """
        Responds to the request to play a loaded video

        :param msg: First element is the controller which should be used
        :param status:
        """
        return self.media_play(msg[0])

    def on_media_play(self):
        """
        Responds to the request to play a loaded video from the web.
        """
        return self.media_play(self.live_controller)

    def media_play(self, controller: SlideController, start_hidden=False):
        """
        Responds to the request to play a loaded video

        :param controller: The controller to be played
        :param start_hidden: Whether to play the video without showing the controller
        """
        self.log_debug(f'media_play is_live:{controller.is_live}')
        controller.mediabar.seek_slider.blockSignals(True)
        controller.mediabar.volume_slider.blockSignals(True)
        display = self._define_display(controller)
        if not self.current_media_players[controller.controller_type].play(controller, display):
            controller.mediabar.seek_slider.blockSignals(False)
            controller.mediabar.volume_slider.blockSignals(False)
            return False
        self.media_volume(controller, get_volume(controller))
        if not start_hidden:
            self._media_set_visibility(controller, True)
        self._media_bar(controller, "play")
        # Start Timer for ui updates
        controller.mediabar.seek_slider.blockSignals(False)
        controller.mediabar.volume_slider.blockSignals(False)
        controller.media_info.is_playing = True
        if not controller.media_info.is_background:
            display = self._define_display(controller)
            if controller.is_live:
                controller.set_hide_mode(None)
                display.hide_display(HideMode.Screen)
            controller._set_theme(controller.service_item)
            display.load_verses([{"verse": "v1", "text": "", "footer": " "}])
        controller.output_has_changed()
        return True

    def tick(self, controller) -> None:
        """
        Add a tick while the media is playing but only count if not paused

        :param controller:  The Controller to be processed
        :return:            Is the video still running?
        """
        controller.media_info.timer = controller.vlc_media_player.get_time()
        self._update_seek_ui(controller)
        return

    def _media_bar(self, controller: SlideController, mode: str) -> None:
        """
        Set the media bar state depending on the function called.
        :param controller: The controller being updated
        :param mode: The mode the code is being called from
        :return: None
        """
        controller.mediabar.blockSignals(True)
        if controller.controller_type in self.current_media_players and \
                self.current_media_players[controller.controller_type].can_repeat:
            if controller.media_info.is_theme_background:
                loop_set = False
                loop_disabled = True
                self.current_media_players[controller.controller_type].toggle_loop(controller, True)
            else:
                loop_set = is_looping_playback(controller)
                loop_disabled = False
                self.current_media_players[controller.controller_type].toggle_loop(controller, loop_set)
        else:
            loop_set = False
            loop_disabled = True
        if mode == "load":
            controller.mediabar.actions['playbackPlay'].setDisabled(False)
            controller.mediabar.actions['playbackPause'].setDisabled(True)
            controller.mediabar.actions['playbackStop'].setDisabled(True)
            controller.mediabar.actions['playbackLoop'].setChecked(loop_set)
            controller.mediabar.actions['playbackLoop'].setDisabled(loop_disabled)
        if mode == "play":
            controller.mediabar.actions['playbackPlay'].setDisabled(True)
            controller.mediabar.actions['playbackPause'].setDisabled(False)
            controller.mediabar.actions['playbackStop'].setDisabled(False)
            controller.mediabar.actions['playbackLoop'].setChecked(loop_set)
            controller.mediabar.actions['playbackLoop'].setDisabled(loop_disabled)
        if mode == "pause" or mode == "stop" or mode == "reset":
            controller.mediabar.actions['playbackPlay'].setDisabled(False)
            controller.mediabar.actions['playbackPause'].setDisabled(True)
            controller.mediabar.actions['playbackStop'].setDisabled(False)
        if mode == "stop" or mode == "reset":
            controller.mediabar.actions['playbackLoop'].setChecked(loop_set)
            controller.mediabar.actions['playbackLoop'].setDisabled(loop_disabled)
        controller.mediabar.blockSignals(False)

    @staticmethod
    def _update_seek_ui(controller):
        if controller.media_info.timer > controller.media_info.end_time:
            controller.media_info.timer = controller.media_info.end_time
        if controller.media_info.timer < 0:
            controller.media_info.timer = 0
        seconds = controller.media_info.timer // 1000
        minutes = seconds // 60
        seconds %= 60
        end_seconds = controller.media_info.end_time // 1000
        end_minutes = end_seconds // 60
        end_seconds %= 60
        if end_minutes == 0 and end_seconds == 0:
            controller.mediabar.position_label.setText('')
        else:
            controller.mediabar.position_label.setText(' %02d:%02d / %02d:%02d' %
                                                       (minutes, seconds, end_minutes, end_seconds))

    def media_pause_msg(self, msg: list):
        """
        Responds to the request to pause a loaded video

        :param msg: First element is the controller which should be used
        """
        return self.media_pause(msg[0])

    def on_media_pause(self):
        """
        Responds to the request to pause a loaded video from the web.
        """
        return self.media_pause(self.live_controller)

    def media_pause(self, controller: SlideController):
        """
        Responds to the request to pause a loaded video

        :param controller: The Controller to be paused
        """
        self.log_debug(f'media_stop is_live:{controller.is_live}')
        if controller.controller_type in self.current_media_players:
            self.current_media_players[controller.controller_type].pause(controller)
            self._media_bar(controller, "pause")
            controller.media_info.is_playing = False
            # Add a tick to the timer to prevent it finishing the video before it can loop back or stop
            # If the clip finishes, we hit a bug where we cannot start the video
            controller.media_info.timer = controller.vlc_media_player.get_time()
            controller.output_has_changed()
            return True
        return False

    def media_loop_msg(self, msg: list):
        """
        Responds to the request to loop a loaded video

        :param msg: First element is the controller which should be used
        """
        self.media_loop(msg[0])

    def media_loop(self, controller: Type[SlideController]):
        """
        Responds to the request to loop a loaded video

        :param controller: The controller that needs to be stopped
        """
        toggle_looping_playback(controller)
        if controller.controller_type in self.current_media_players:
            self.current_media_players[controller.controller_type].toggle_loop(controller,
                                                                               is_looping_playback(controller))
        controller.mediabar.actions['playbackLoop'].setChecked(is_looping_playback(controller))

    def media_stop_msg(self, msg: list):
        """
        Responds to the request to stop a loaded video

        :param msg: First element is the controller which should be used
        """
        return self.media_stop(msg[0])

    def on_media_stop(self):
        """
        Responds to the request to stop a loaded video from the web.
        """
        return self.media_stop(self.live_controller)

    def media_stop(self, controller: SlideController):
        """
        Responds to the request to stop a loaded video

        :param controller: The controller that needs to be stopped
        """
        self.log_debug(f'media_stop is_live:{controller.is_live}')
        if controller.controller_type in self.current_media_players:
            self.current_media_players[controller.controller_type].stop(controller)
            if controller.is_live:
                self.live_hide_timer.start(HIDE_DELAY_TIME)
                if not controller.media_info.is_background:
                    display = self._define_display(controller)
                    if display.hide_mode == HideMode.Screen:
                        Registry().execute('live_display_hide', HideMode.Blank)
                    else:
                        controller.set_hide_mode(display.hide_mode or HideMode.Blank)
            else:
                self._media_set_visibility(controller, False)
            self._media_bar(controller, "stop")
            controller.media_info.is_playing = False
            controller.media_info.timer = controller.media_info.start_time
            controller.mediabar.seek_slider.setSliderPosition(controller.media_info.start_time)
            self._update_seek_ui(controller)
            controller.output_has_changed()
            return True
        return False

    def media_volume_msg(self, msg: list):
        """
        Changes the volume of a running video

        :param msg: First element is the controller which should be used
        """
        controller = msg[0]
        vol = msg[1][0]
        self.media_volume(controller, vol)

    def media_volume(self, controller: Type[SlideController], volume: int):
        """
        Changes the volume of a running video

        :param controller: The Controller to use
        :param volume: The volume to be set
        """
        self.log_debug(f'media_volume {volume}')
        save_volume(controller, volume)
        self.current_media_players[controller.controller_type].volume(controller, volume)
        controller.mediabar.volume_slider.setValue(volume)

    def media_seek_msg(self, msg: list):
        """
        Responds to the request to change the seek Slider of a loaded video via a message

        :param msg: First element is the controller which should be used
            Second element is a list with the seek value as first element
        """
        controller = msg[0]
        seek_value = msg[1][0]
        self.media_seek(controller, seek_value)

    def media_seek(self, controller: SlideController, seek_value):
        """
        Responds to the request to change the seek Slider of a loaded video

        :param controller: The controller to use.
        :param seek_value: The value to set.
        """
        # This may be triggered by setting the slider max/min before the current_media_players dict is set
        if controller.controller_type in self.current_media_players:
            self.current_media_players[controller.controller_type].seek(controller, seek_value)
            controller.media_info.timer = seek_value
            self._update_seek_ui(controller)

    def media_reset(self, controller: SlideController, delayed: bool = False) -> None:
        """
        Responds to the request to reset a loaded video
        :param controller: The controller to use.
        :param delayed: Should the controller briefly remain visible.
        """
        self.log_debug('media_reset')
        self.set_controls_visible(controller, False)
        if controller.controller_type in self.current_media_players:
            self.current_media_players[controller.controller_type].reset(controller)
            if controller.is_live and delayed:
                self.live_kill_timer.start(HIDE_DELAY_TIME)
            else:
                if controller.is_live:
                    self.live_kill_timer.stop()
                else:
                    self._media_set_visibility(controller, False)
                del self.current_media_players[controller.controller_type]
                controller.media_info = ItemMediaInfo()
                controller.media_info.is_theme_background = False
            self._media_bar(controller, 'reset')

    def media_hide_msg(self, msg: list):
        """
        Hide the related video Widget

        :param msg: First element is the boolean for Live indication
        """
        is_live = msg[1]
        self.media_hide(is_live)

    def media_hide(self, is_live, delayed=False):
        """
        Pause and hide the related video Widget if is_live

        :param is_live: Live indication
        :param delayed: Should the controller briefly remain visible.
        """
        self.log_debug(f'media_hide is_live:{is_live}')
        if not is_live or self.live_kill_timer.isActive():
            return
        if self.live_controller.controller_type in self.current_media_players and \
                self.current_media_players[self.live_controller.controller_type].get_live_state() == MediaState.Playing:
            if delayed:
                self.live_hide_timer.start(HIDE_DELAY_TIME)
            else:
                self.media_pause(self.live_controller)
                self._media_set_visibility(self.live_controller, False)

    def _on_media_hide_live(self):
        self.media_pause(self.live_controller)
        self._media_set_visibility(self.live_controller, False)

    def _on_media_kill_live(self):
        self._media_set_visibility(self.live_controller, False)
        del self.current_media_players[self.live_controller.controller_type]

    def _media_set_visibility(self, controller: SlideController, visible):
        """
        Set the live video Widget visibility
        """
        if controller.is_live:
            self.live_hide_timer.stop()
        visible = visible and controller.media_info.media_type is not MediaType.Audio
        self.current_media_players[controller.controller_type].set_visible(controller, visible)
        if controller.is_live and visible:
            display = self._define_display(controller)
            display.raise_()

    def media_blank(self, msg: list):
        """
        Blank the related video Widget

        :param msg: First element is the boolean for Live indication
            Second element is the hide mode
        """
        is_live = msg[1]
        hide_mode = msg[2]
        self.log_debug(f'media_blank is_live:{is_live}')
        if not is_live or self.live_controller.controller_type not in self.current_media_players:
            return
        if self.live_kill_timer.isActive():
            # If pressing blank when the video is being removed, remove it instantly
            self._media_set_visibility(self.live_controller, False)
            self.media_reset(self.live_controller)
            return
        if not self.live_controller.media_info.is_background:
            Registry().execute('live_display_hide', hide_mode)
        controller_type = self.live_controller.controller_type
        playing = self.current_media_players[controller_type].get_live_state() == MediaState.Playing
        if self.live_controller.media_info.is_theme_background and hide_mode == HideMode.Theme:
            if not playing:
                self.media_play(self.live_controller)
            else:
                self.live_hide_timer.stop()
        else:
            if playing and not self.live_controller.media_info.is_theme_background:
                self.media_pause(self.live_controller)
            self._media_set_visibility(self.live_controller, False)

    def media_unblank(self, msg: list):
        """
        Unblank the related video Widget

        :param msg: First element is not relevant in this context
            Second element is the boolean for Live indication
        """
        is_live = msg[1]
        self.log_debug(f'media_blank is_live:{is_live}')
        if not is_live or self.live_kill_timer.isActive():
            return
        Registry().execute('live_display_show')
        if self.live_controller.controller_type in self.current_media_players:
            if self.current_media_players[self.live_controller.controller_type].get_live_state() != \
                    MediaState.Playing:
                self.media_play(self.live_controller)
            else:
                self._media_set_visibility(self.live_controller, True)
                if not self.live_controller.media_info.is_background:
                    display = self._define_display(self.live_controller)
                    display.hide_display(HideMode.Screen)

    def finalise(self):
        """
        Reset all the media controllers when OpenLP shuts down
        """
        self.live_hide_timer.stop()
        self.live_kill_timer.stop()
        self.media_reset(self._display_controllers(DisplayControllerType.Live))
        self.media_reset(self._display_controllers(DisplayControllerType.Preview))

    @staticmethod
    def _define_display(controller: SlideController) -> DisplayWindow:
        """
        Extract the correct display for a given controller

        :param controller:  Controller to be used
        :return correct display window
        """
        if controller.is_live:
            return controller.display
        return controller.preview_display
