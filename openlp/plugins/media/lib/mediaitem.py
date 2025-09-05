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

import logging
import os
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from sqlalchemy.sql.expression import or_

from openlp.core.common import delete_file
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry
from openlp.core.lib import ServiceItemContext
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.ui import create_widget_action, critical_error_message_box
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.library import FolderLibraryItem
from openlp.core.ui.media import get_supported_media_suffix, parse_stream_path, MediaType

from openlp.plugins.media.lib.db import Folder, Item

from openlp.plugins.media.forms.streamselectorform import StreamSelectorForm
from openlp.plugins.media.forms.networkstreamselectorform import NetworkStreamSelectorForm


log = logging.getLogger(__name__)


class MediaMediaItem(FolderLibraryItem):
    """
    This is the custom media manager item for Media Slides.
    """
    media_go_live = QtCore.Signal(list)
    media_add_to_service = QtCore.Signal(list)
    log.info('{name} MediaMediaItem loaded'.format(name=__name__))

    def __init__(self, parent, plugin):
        self.setup()
        super(MediaMediaItem, self).__init__(parent, plugin, Folder, Item)

    def retranslate_ui(self):
        """
        This method is called automatically to provide OpenLP with the opportunity to translate the ``MediaManagerItem``
        to another language.
        """
        super().retranslate_ui()
        self.on_new_prompt = translate('MediaPlugin.MediaItem', 'Select Media')

    def setup_item(self):
        """
        Do some additional setup.
        """
        self.media_go_live.connect(self.go_live_remote)
        self.media_add_to_service.connect(self.add_to_service_remote)
        self.single_service_item = False
        self.has_search = True
        self.media_object = None
        Registry().register_function('mediaitem_media_rebuild', self.rebuild_players)
        # Allow DnD from the desktop
        self.list_view.activateDnD()

    def setup(self):
        """
        Allow early setup to be mocked.
        """
        self.icon_path = 'images/image'
        self.background = False
        self.automatic = ''
        self.error_icon = UiIcons().delete
        self.clapperboard = UiIcons().clapperboard

    def required_icons(self):
        """
        Set which icons the media manager tab should show
        """
        super().required_icons()
        self.has_file_icon = True
        self.has_new_icon = False
        self.has_edit_icon = False
        if not State().check_preconditions('media'):
            self.can_preview = False
            self.can_make_live = False
            self.can_add_to_service = False
        if State().check_preconditions('media_live'):
            self.can_make_live = True
        else:
            self.can_preview = False
            self.can_make_live = False
            self.can_add_to_service = False

    def initialise(self):
        """
        Initialize media item.
        """
        self.log_debug('Initialise')
        self.list_view.clear()
        self.list_view.setIndentation(self.list_view.default_indentation)
        self.list_view.allow_internal_dnd = True
        self.service_path = AppLocation.get_section_data_path(self.settings_section) / 'thumbnails'
        create_paths(self.service_path)
        # Defer loading the list from the database until the tab gains focus
        self._list_loaded = False

    def on_focus(self):
        if not getattr(self, '_list_loaded', False):
            self.log_debug('MediaMediaItem lazy loading list on focus')
            try:
                self.application.set_busy_cursor()
                self.load_list(self.manager.get_all_objects(Item, order_by_ref=Item.file_path), is_initial_load=True)
                self._list_loaded = True
            finally:
                self.application.set_normal_cursor()
        self.service_path = AppLocation.get_section_data_path('media') / 'thumbnails'
        self.rebuild_players()

    def add_middle_header_bar(self):
        super().add_middle_header_bar()
        self.toolbar.addSeparator()
        network_stream_button_text = translate('MediaPlugin.MediaItem', 'Open network stream')
        network_stream_button_tooltip = translate('MediaPlugin.MediaItem', 'Open network stream')
        self.toolbar.add_toolbar_action('networkstream_action', text=network_stream_button_text,
                                        icon=UiIcons().network_stream, tooltip=network_stream_button_tooltip,
                                        triggers=self.on_open_network_stream)
        device_stream_button_text = translate('MediaPlugin.MediaItem', 'Open device stream')
        device_stream_button_tooltip = translate('MediaPlugin.MediaItem', 'Open device stream')
        self.toolbar.add_toolbar_action('devicestream_action', text=device_stream_button_text,
                                        icon=UiIcons().device_stream, tooltip=device_stream_button_tooltip,
                                        triggers=self.on_open_device_stream)

    def add_custom_context_actions(self):
        """
        Add custom actions to the context menu.
        """
        create_widget_action(self.list_view, separator=True)
        create_widget_action(
            self.list_view,
            text=UiStrings().AddFolder, icon=UiIcons().folder, triggers=self.on_add_folder_click)
        create_widget_action(
            self.list_view,
            text=translate('MediaPlugin', 'Add new media'),
            icon=UiIcons().open, triggers=self.on_file_click)
        create_widget_action(self.list_view, separator=True)

    def generate_slide_data(self, service_item, *, item=None, remote=False, context=ServiceItemContext.Service,
                            **kwargs):
        """
        Generate the slide data. Needs to be implemented by the plugin.

        :param service_item: The service item to be built on
        :param item: The Song item to be used
        :param remote: Triggered from remote
        :param context: Why is it being generated
        :param kwargs: Consume other unused args specified by the base implementation, but not use by this one.
        """
        if item is None:
            item = self.list_view.currentItem()
            if item is None:
                return False
        if isinstance(item, QtCore.QModelIndex):
            item = self.list_view.itemFromIndex(item)
        media_item = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not isinstance(media_item, Item):
            return False
        filename = media_item.file_path
        if filename.startswith('devicestream:') or filename.startswith('networkstream:'):
            # Special handling if the filename is a devicestream
            (_, name, _, _) = parse_stream_path(filename)
            service_item.processor = 'qt6'
            service_item.add_capability(ItemCapabilities.CanStream)
            service_item.add_from_command(filename, name, self.clapperboard)
            service_item.title = name
        else:
            if not os.path.exists(filename):
                if not remote:
                    # File is no longer present
                    critical_error_message_box(
                        translate('MediaPlugin.MediaItem', 'Missing Media File'),
                        translate('MediaPlugin.MediaItem', 'The file {name} no longer exists.').format(name=filename))
                return False
            (path, name) = os.path.split(filename)
            service_item.title = name
            service_item.processor = 'qt6'
            service_item.add_from_command(path, name, self.clapperboard)
            # Only get start and end times if going to a service
            service_item.set_media_length(self.media_controller.media_length(filename))
        service_item.add_capability(ItemCapabilities.CanAutoStartForLive)
        service_item.add_capability(ItemCapabilities.CanEditTitle)
        service_item.add_capability(ItemCapabilities.RequiresMedia)
        # force a non-existent theme
        service_item.theme = -1
        # validate the item after all capabilities has been added
        service_item.validate_item()
        return True

    def rebuild_players(self):
        """
        Rebuild the tab in the media manager when changes are made in the settings.
        """
        # self.populate_display_types()
        audio, video = get_supported_media_suffix()
        self.on_new_file_masks = translate('MediaPlugin.MediaItem',
                                           'Videos ({video});;Audio ({audio});;{files} '
                                           '(*)').format(video=' '.join(video),
                                                         audio=' '.join(audio),
                                                         files=UiStrings().AllFiles)

    def file_to_item(self, filename):
        """
        Override the inherited file_to_item() method to handle various tracks
        """
        if isinstance(filename, Path):
            name = filename.name
            filename = str(filename)
        elif filename.startswith('devicestream:') or filename.startswith('networkstream:'):
            _, name, _, _ = parse_stream_path(filename)
        else:
            name = os.path.basename(filename)
        item = self.item_class(name=name, file_path=filename)
        self.manager.save_object(item)
        return item

    def load_item(self, item, is_initial_load=False):
        """
        Given an item object, return a QTreeWidgetItem
        """
        track_str = str(item.file_path)
        track_info = QtCore.QFileInfo(track_str)
        tree_item = None
        if track_str.startswith('devicestream:') or track_str.startswith('networkstream:'):
            (stream_type, name, mrl, _) = parse_stream_path(track_str)
            tree_item = QtWidgets.QTreeWidgetItem([name])
            tree_item.setText(0, name)
            if stream_type == MediaType.DeviceStream:
                tree_item.setIcon(0, UiIcons().device_stream)
            else:
                tree_item.setIcon(0, UiIcons().network_stream)
            tree_item.setToolTip(0, mrl)
        elif not Path(item.file_path).exists():
            # File doesn't exist, mark as error.
            file_name = Path(item.file_path).name
            tree_item = QtWidgets.QTreeWidgetItem([file_name])
            tree_item.setText(0, file_name)
            tree_item.setIcon(0, UiIcons().error)
            tree_item.setToolTip(0, track_str)
        elif track_info.isFile():
            # Normal media file handling.
            file_name = Path(item.file_path).name
            tree_item = QtWidgets.QTreeWidgetItem([file_name])
            tree_item.setText(0, file_name)
            search = "*." + file_name.split('.')[-1].lower()
            _, v_suffixes = get_supported_media_suffix()
            if search in v_suffixes:
                tree_item.setIcon(0, UiIcons().audio)
            else:
                tree_item.setIcon(0, UiIcons().video)
            tree_item.setToolTip(0, track_str)
        if tree_item:
            tree_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, item)
        return tree_item

    def delete_item(self, item):
        """
        Delete any and all thumbnails and things associated with this media item
        """
        delete_file(self.service_path / Path(item.file_path).name)

    def format_search_result(self, item):
        """
        Format an item for the search results

        :param Item item: An Item to be formatted
        :return list[str, str]: A list of two items containing the full path and a pretty name
        """
        if Path(item.file_path).exists():
            return [item.file_path, Path(item.file_path).name]
        elif item.file_path.startswith('device') or item.file_path.startswith('network'):
            (_, name, _, _) = parse_stream_path(item.file_path)
            return [item.file_path, name]
        else:
            return super().format_search_result(item)

    def get_list(self, media_type=MediaType.Audio):
        """
        Get the list of media, optional select media type.

        :param media_type: Type to get, defaults to audio.
        :return: The media list
        """
        if media_type == MediaType.Audio:
            extensions, _ = get_supported_media_suffix()
        else:
            _, extensions = get_supported_media_suffix()
        clauses = []
        for extension in extensions:
            # Drop the initial * and add to the list of clauses
            clauses.append(Item.file_path.endswith(extension[1:]))
        items = self.manager.get_all_objects(Item, or_(*clauses))
        return [Path(item.file_path) for item in items]

    def on_open_device_stream(self):
        """
        When the open device stream button is clicked, open the stream selector window.
        """
        stream_selector_form = StreamSelectorForm(self.main_window, self.add_device_stream)
        stream_selector_form.exec()
        del stream_selector_form

    def add_device_stream(self, stream):
        """
        Add a device stream based clip to the mediamanager, called from stream_selector_form.

        :param stream: The clip to add.
        """
        self.validate_and_load([str(stream)])

    def on_open_network_stream(self):
        """
        When the open network stream button is clicked, open the stream selector window.
        """
        # if media_add_to_service:
        stream_selector_form = NetworkStreamSelectorForm(self.main_window, self.add_network_stream)
        stream_selector_form.exec()
        del stream_selector_form

    def add_network_stream(self, stream):
        """
        Add a network stream based clip to the mediamanager, called from stream_selector_form.

        :param stream: The clip to add.
        """
        self.validate_and_load([str(stream)])
