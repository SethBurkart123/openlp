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
from pathlib import Path
from typing import Union

from PySide6 import QtCore, QtWidgets

from openlp.core.common import delete_file, get_images_filter
from openlp.core.common.applocation import AppLocation
from openlp.core.common.enum import ImageThemeMode
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry
from openlp.core.lib import ServiceItemContext, build_icon, check_item_selected, create_thumb, validate_thumb
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.ui import create_widget_action, critical_error_message_box
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.library import FolderLibraryItem

from openlp.plugins.images.lib.db import Folder, Item


log = logging.getLogger(__name__)


class ImageMediaItem(FolderLibraryItem):
    """
    This is the custom media manager item for images.
    """
    images_go_live = QtCore.Signal(list)
    images_add_to_service = QtCore.Signal(list)
    log.info('Image Media Item loaded')

    def __init__(self, parent, plugin):
        self.icon_path = 'images/image'
        self.manager = None
        self._list_loaded = False
        super(ImageMediaItem, self).__init__(parent, plugin, Folder, Item)

    def setup_item(self):
        """
        Do some additional setup.
        """
        self.images_go_live.connect(self.go_live_remote)
        self.images_add_to_service.connect(self.add_to_service_remote)
        self.quick_preview_allowed = True
        self.has_search = True
        self.list_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        Registry().register_function('live_theme_changed', self.on_display_changed)
        Registry().register_function('slidecontroller_live_started', self.on_display_changed)
        # Allow DnD from the desktop.
        self.list_view.activateDnD()

    def retranslate_ui(self):
        super().retranslate_ui()
        self.on_new_prompt = translate('ImagePlugin.MediaItem', 'Select Image(s)')
        file_formats = get_images_filter()
        self.on_new_file_masks = '{formats};;{files} (*)'.format(formats=file_formats, files=UiStrings().AllFiles)
        self.replace_action.setText(UiStrings().ReplaceBG)
        self.replace_action.setToolTip(UiStrings().ReplaceLiveBG)
        self.replace_action_context.setText(UiStrings().ReplaceBG)
        self.replace_action_context.setToolTip(UiStrings().ReplaceLiveBG)
        self.reset_action.setText(UiStrings().ResetBG)
        self.reset_action.setToolTip(UiStrings().ResetLiveBG)
        self.reset_action_context.setText(UiStrings().ResetBG)
        self.reset_action_context.setToolTip(UiStrings().ResetLiveBG)

    def required_icons(self):
        """
        Set which icons the media manager tab should show.
        """
        super().required_icons()
        self.has_file_icon = True
        self.has_new_icon = False
        self.has_edit_icon = False
        self.add_to_service_item = True

    def initialise(self):
        log.debug('initialise (lazy)')
        self.list_view.clear()
        self.list_view.setIconSize(QtCore.QSize(88, 50))
        self.list_view.setIndentation(self.list_view.default_indentation)
        self.list_view.allow_internal_dnd = True
        self.service_path = AppLocation.get_section_data_path(self.settings_section) / 'thumbnails'
        create_paths(self.service_path)
        # Defer loading the database list and thumbnails until the tab gains focus
        self._list_loaded = False

    def on_focus(self):
        if not self._list_loaded:
            log.debug('ImageMediaItem lazy loading list on focus')
            try:
                self.application.set_busy_cursor()
                self.load_list(self.manager.get_all_objects(Item, order_by_ref=Item.file_path), is_initial_load=True)
                self._list_loaded = True
            finally:
                self.application.set_normal_cursor()
        
    def add_custom_context_actions(self):
        """
        Add custom actions to the context menu.
        """
        create_widget_action(self.list_view, separator=True)
        create_widget_action(self.list_view, text=UiStrings().AddFolder, icon=UiIcons().folder,
                             triggers=self.on_add_folder_click)
        create_widget_action(self.list_view, text=translate('ImagePlugin', 'Add new image(s)'),
                             icon=UiIcons().open, triggers=self.on_file_click)
        create_widget_action(self.list_view, separator=True)
        self.replace_action_context = create_widget_action(self.list_view, text=UiStrings().ReplaceBG,
                                                           icon=UiIcons().theme, triggers=self.on_replace_click)
        self.reset_action_context = create_widget_action(self.list_view, text=UiStrings().ReplaceLiveBG,
                                                         icon=UiIcons().close, visible=False,
                                                         triggers=self.on_reset_click)

    def add_end_header_bar(self):
        """
        Add custom buttons to the end of the toolbar
        """
        self.replace_action = self.toolbar.add_toolbar_action('replace_action',
                                                              icon=UiIcons().theme,
                                                              triggers=self.on_replace_click)
        self.reset_action = self.toolbar.add_toolbar_action('reset_action',
                                                            icon=UiIcons().close,
                                                            visible=False, triggers=self.on_reset_click)

    def generate_thumbnail_path(self, item: Item) -> Path:
        """
        Generate a path to the thumbnail

        :param openlp.plugins.images.lib.db.Item image: The image to generate the thumbnail path for.
        :return: A path to the thumbnail
        :rtype: Path
        """
        file_path = Path(item.file_path)
        ext = file_path.suffix.lower()
        return self.service_path / '{name:s}{ext}'.format(name=item.file_hash or file_path.stem, ext=ext)

    def load_item(self, item: Item, is_initial_load: bool = False) -> QtWidgets.QTreeWidgetItem:
        """Given an item object, return a QTreeWidgetItem"""
        tree_item = None
        file_path = Path(item.file_path)
        file_name = file_path.name
        if not file_path.exists():
            tree_item = QtWidgets.QTreeWidgetItem([file_name])
            tree_item.setIcon(0, UiIcons().delete)
            tree_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, item)
            tree_item.setToolTip(0, str(file_path))
        else:
            log.debug('Loading image: {name}'.format(name=item.file_path))
            thumbnail_path = self.generate_thumbnail_path(item)
            if validate_thumb(file_path, thumbnail_path):
                icon = build_icon(thumbnail_path)
            else:
                size: Union[QtCore.QSize, None] = None
                slide_height: Union[int, None] = self.settings.value('advanced/slide max height')
                if slide_height and slide_height > 0:
                    size = QtCore.QSize(-1, slide_height)
                icon = create_thumb(file_path, thumbnail_path, size=size)
            tree_item = QtWidgets.QTreeWidgetItem([file_name])
            tree_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, item)
            tree_item.setIcon(0, icon)
            tree_item.setToolTip(0, str(file_path))
        return tree_item

    def delete_item(self, item: Item):
        """
        Remove an image item from the list.
        """
        file_path = Path(item.file_path)
        if file_path.exists():
            delete_file(self.service_path / file_path.name)
            delete_file(self.generate_thumbnail_path(item))

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
        if item:
            if isinstance(item, QtCore.QModelIndex):
                item = self.list_view.itemFromIndex(item)
                if not item:
                    return False
            items = [item]
        else:
            items = self.list_view.selectedItems()
            if not items:
                return False
        # Determine service item title
        image_item = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(image_item, Folder) or len(items) == 1:
            service_item.title = items[0].text(0)
            if not service_item.title:
                name = Path(image_item.file_path).name
                if name:
                    service_item.title = name
        else:
            service_item.title = str(self.plugin.name_strings['plural'])

        service_item.add_capability(ItemCapabilities.CanMaintain)
        service_item.add_capability(ItemCapabilities.CanPreview)
        service_item.add_capability(ItemCapabilities.CanLoop)
        service_item.add_capability(ItemCapabilities.CanAppend)
        service_item.add_capability(ItemCapabilities.CanEditTitle)
        service_item.add_capability(ItemCapabilities.HasThumbnails)
        service_item.add_capability(ItemCapabilities.ProvidesOwnTheme)
        if self.settings.value('images/background mode') == ImageThemeMode.CustomTheme:
            service_item.theme = self.settings.value('images/theme')
        else:
            # force a nonexistent theme
            service_item.theme = -1
        missing_items_file_names = []
        images = []
        existing_images = []
        # Expand groups to images
        for bitem in items:
            if (isinstance(bitem.data(0, QtCore.Qt.ItemDataRole.UserRole), Folder) or
                    bitem.data(0, QtCore.Qt.ItemDataRole.UserRole) is None):
                for index in range(0, bitem.childCount()):
                    if isinstance(bitem.child(index).data(0, QtCore.Qt.ItemDataRole.UserRole), Item):
                        images.append(bitem.child(index).data(0, QtCore.Qt.ItemDataRole.UserRole))
            elif isinstance(bitem.data(0, QtCore.Qt.ItemDataRole.UserRole), Item):
                images.append(bitem.data(0, QtCore.Qt.ItemDataRole.UserRole))
        # Don't try to display empty groups
        if not images:
            return False
        # Find missing files
        for image in images:
            if not Path(image.file_path).exists():
                missing_items_file_names.append(image.file_path)
            else:
                existing_images.append(image)
        # We cannot continue, as all images do not exist.
        if not existing_images:
            if not remote:
                critical_error_message_box(
                    translate('ImagePlugin.MediaItem', 'Missing Image(s)'),
                    translate('ImagePlugin.MediaItem', 'The following image(s) no longer exist: {names}'
                              ).format(names='\n'.join(missing_items_file_names)))
            return False
        # We have missing as well as existing images. We ask what to do.
        elif missing_items_file_names and QtWidgets.QMessageBox.question(
                self, translate('ImagePlugin.MediaItem', 'Missing Image(s)'),
                translate('ImagePlugin.MediaItem', 'The following image(s) no longer exist: {names}\n'
                          'Do you want to add the other images anyway?'
                          ).format(names='\n'.join(missing_items_file_names))) == \
                QtWidgets.QMessageBox.StandardButton.No:
            return False
        # Continue with the existing images.
        for image in existing_images:
            name = Path(image.file_path).name
            thumbnail_path = self.generate_thumbnail_path(image)
            service_item.add_from_image(Path(image.file_path), name, thumbnail_path)
        return True

    def on_reset_click(self):
        """
        Called to reset the Live background with the image selected.
        """
        self.reset_action.setVisible(False)
        self.reset_action_context.setVisible(False)
        self.live_controller.reload_theme()

    def on_display_changed(self, service_item=None):
        """
        Triggered by the change of theme in the slide controller.
        """
        self.reset_action.setVisible(False)
        self.reset_action_context.setVisible(False)

    def on_replace_click(self):
        """
        Called to replace Live background with the image selected.
        """
        if check_item_selected(
                self.list_view,
                translate('ImagePlugin.MediaItem', 'You must select an image to replace the background with.')):
            bitem = self.list_view.selectedItems()[0]
            if not isinstance(bitem.data(0, QtCore.Qt.ItemDataRole.UserRole), Item):
                # Only continue when an image is selected.
                return
            file_path = Path(bitem.data(0, QtCore.Qt.ItemDataRole.UserRole).file_path)
            if file_path.exists():
                self.live_controller.set_background_image(file_path)
                self.reset_action.setVisible(True)
                self.reset_action_context.setVisible(True)
            else:
                critical_error_message_box(
                    UiStrings().LiveBGError,
                    translate('ImagePlugin.MediaItem', 'There was a problem replacing your background, '
                              'the image file "{name}" no longer exists.').format(name=file_path))
