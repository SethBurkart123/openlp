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
The :mod:`~openlp.plugins.mcp.mcpplugin` module contains the Plugin class
for the MCP (Model Context Protocol) plugin.
"""

import logging
import asyncio
import threading
import email
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6 import QtCore

from openlp.core.state import State
from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib import build_icon
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.lib.serviceitem import ServiceItem
from openlp.core.ui.icons import UiIcons
from openlp.core.common.enum import ServiceItemType

try:
    from fastmcp import FastMCP, Context
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

log = logging.getLogger(__name__)


class MCPWorker(QtCore.QObject):
    """
    Worker class that handles MCP operations on the main thread using Qt signals/slots.
    This ensures all GUI operations happen on the correct thread.
    """
    # Signals for different operations
    create_service_requested = QtCore.Signal()
    load_service_requested = QtCore.Signal(str)  # file_path
    save_service_requested = QtCore.Signal(str)  # file_path (optional)
    get_service_items_requested = QtCore.Signal()
    add_song_requested = QtCore.Signal(str, str, str)  # title, author, lyrics
    add_custom_slide_requested = QtCore.Signal(str, str)  # title, content
    add_media_requested = QtCore.Signal(str, str)  # file_path, title
    go_live_requested = QtCore.Signal(int)  # item_index
    next_slide_requested = QtCore.Signal()
    previous_slide_requested = QtCore.Signal()
    list_themes_requested = QtCore.Signal()
    set_theme_requested = QtCore.Signal(str)  # theme_name
    parse_email_requested = QtCore.Signal(str)  # email_content
    create_from_structure_requested = QtCore.Signal(object)  # service_structure
    
    # Result signals
    operation_completed = QtCore.Signal(object)  # result
    
    def __init__(self):
        super().__init__()
        self.current_result = None
        self.result_ready = threading.Event()
        
        # Connect signals to slots
        self.create_service_requested.connect(self.create_service)
        self.load_service_requested.connect(self.load_service)
        self.save_service_requested.connect(self.save_service)
        self.get_service_items_requested.connect(self.get_service_items)
        self.add_song_requested.connect(self.add_song)
        self.add_custom_slide_requested.connect(self.add_custom_slide)
        self.add_media_requested.connect(self.add_media)
        self.go_live_requested.connect(self.go_live)
        self.next_slide_requested.connect(self.next_slide)
        self.previous_slide_requested.connect(self.previous_slide)
        self.list_themes_requested.connect(self.list_themes)
        self.set_theme_requested.connect(self.set_theme)
        self.parse_email_requested.connect(self.parse_email)
        self.create_from_structure_requested.connect(self.create_from_structure)
        
        self.operation_completed.connect(self._handle_result)
    
    def _handle_result(self, result):
        """Handle the result of an operation."""
        self.current_result = result
        self.result_ready.set()
    
    def wait_for_result(self, timeout=10):
        """Wait for an operation to complete and return the result."""
        self.result_ready.clear()
        if self.result_ready.wait(timeout):
            return self.current_result
        else:
            raise TimeoutError("Operation timed out")
    
    @QtCore.Slot()
    def create_service(self):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.new_file()
            service_manager.repaint_service_list(-1, -1)  # Refresh the UI
            self.operation_completed.emit("New service created successfully")
        except Exception as e:
            self.operation_completed.emit(f"Error creating new service: {str(e)}")
    
    @QtCore.Slot(str)
    def load_service(self, file_path):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.load_file(Path(file_path))
            self.operation_completed.emit(f"Service loaded from {file_path}")
        except Exception as e:
            self.operation_completed.emit(f"Error loading service: {str(e)}")
    
    @QtCore.Slot(str)
    def save_service(self, file_path):
        try:
            service_manager = Registry().get('service_manager')
            if file_path:
                service_manager.set_file_name(Path(file_path))
            service_manager.decide_save_method()
            self.operation_completed.emit(f"Service saved{' to ' + file_path if file_path else ''}")
        except Exception as e:
            self.operation_completed.emit(f"Error saving service: {str(e)}")
    
    @QtCore.Slot()
    def get_service_items(self):
        try:
            service_manager = Registry().get('service_manager')
            items = []
            for item in service_manager.service_items:
                service_item = item['service_item']
                items.append({
                    'title': service_item.title,
                    'type': str(service_item.service_item_type),
                    'plugin': service_item.name,
                    'order': item['order']
                })
            self.operation_completed.emit(items)
        except Exception as e:
            self.operation_completed.emit([{"error": str(e)}])
    
    @QtCore.Slot(str, str, str)
    def add_song(self, title, author, lyrics):
        try:
            songs_plugin = Registry().get('plugin_manager').get_plugin_by_name('songs')
            if not songs_plugin or not songs_plugin.is_active():
                self.operation_completed.emit("Songs plugin not available")
                return
            
            # Try multiple search approaches to find existing songs
            from openlp.plugins.songs.lib.db import Song
            from openlp.plugins.songs.lib import clean_string
            
            existing_songs = []
            search_attempts = []
            
            # 1. Try exact title match first
            exact_matches = songs_plugin.manager.get_all_objects(Song, Song.title == title)
            if exact_matches:
                existing_songs = exact_matches
                search_attempts.append(f"exact title match")
            
            # 2. Try search_title contains our cleaned title
            if not existing_songs:
                search_title = clean_string(title)
                search_matches = songs_plugin.manager.get_all_objects(Song, Song.search_title.like(f'%{search_title}%'))
                if search_matches:
                    existing_songs = search_matches
                    search_attempts.append(f"search_title contains '{search_title}'")
            
            # 3. Try partial title search (remove common words)
            if not existing_songs:
                # Remove common words that might cause issues
                simplified_title = title.lower()
                for word in ['the', 'a', 'an', 'and', 'of', 'to', 'in', 'for', 'with']:
                    simplified_title = simplified_title.replace(f' {word} ', ' ')
                simplified_clean = clean_string(simplified_title.strip())
                if simplified_clean and simplified_clean != search_title:
                    partial_matches = songs_plugin.manager.get_all_objects(Song, Song.search_title.like(f'%{simplified_clean}%'))
                    if partial_matches:
                        existing_songs = partial_matches
                        search_attempts.append(f"simplified search '{simplified_clean}'")
            
            # 4. Try word-by-word search for longer titles
            if not existing_songs and len(title.split()) > 2:
                words = [clean_string(word) for word in title.split() if len(word) > 3]
                if words:
                    # Search for songs containing all significant words
                    from sqlalchemy import and_
                    word_conditions = [Song.search_title.like(f'%{word}%') for word in words]
                    word_matches = songs_plugin.manager.get_all_objects(Song, and_(*word_conditions))
                    if word_matches:
                        existing_songs = word_matches
                        search_attempts.append(f"word search for: {', '.join(words)}")
            
            if existing_songs:
                # Found existing song(s), use the first match
                song = existing_songs[0]
                try:
                    # Create a mock QListWidgetItem for the generate_slide_data method
                    from PySide6.QtWidgets import QListWidgetItem
                    from PySide6.QtCore import Qt
                    mock_item = QListWidgetItem()
                    mock_item.setData(Qt.ItemDataRole.UserRole, song.id)
                    
                    # Use the songs plugin's media item to generate the service item properly
                    media_item = songs_plugin.media_item
                    service_item = ServiceItem(songs_plugin)
                    service_item.add_icon()  # Ensure icon is set before generate_slide_data
                    
                    # Generate slide data
                    if media_item.generate_slide_data(service_item, item=mock_item):
                        service_manager = Registry().get('service_manager')
                        service_manager.add_service_item(service_item)
                        service_manager.repaint_service_list(-1, -1)  # Refresh the UI
                        
                        # Give detailed feedback about how the song was found
                        match_info = f"✓ Found '{song.title}' in database"
                        if len(existing_songs) > 1:
                            match_info += f" ({len(existing_songs)} matches, used first)"
                        match_info += f" via {search_attempts[-1]}"
                        self.operation_completed.emit(match_info)
                    else:
                        # generate_slide_data failed, fall back to placeholder
                        service_manager = Registry().get('service_manager')
                        self._create_song_placeholder(songs_plugin, title, lyrics, service_manager)
                        service_manager.repaint_service_list(-1, -1)
                        self.operation_completed.emit(f"⚠ Song '{title}' found but failed to load - added placeholder")
                        
                except Exception as slide_error:
                    # If there's an error with the database song, fall back to placeholder
                    service_manager = Registry().get('service_manager')
                    self._create_song_placeholder(songs_plugin, title, lyrics, service_manager)
                    service_manager.repaint_service_list(-1, -1)
                    self.operation_completed.emit(f"⚠ Song '{title}' found but failed to load: {str(slide_error)} - added placeholder")
            else:
                # No existing song found, create a simple service item with clear feedback
                service_manager = Registry().get('service_manager')
                self._create_song_placeholder(songs_plugin, title, lyrics, service_manager)
                service_manager.repaint_service_list(-1, -1)  # Refresh the UI
                
                # Give clear feedback about what was searched
                search_info = f"⚠ Song '{title}' not found in database"
                if search_attempts:
                    search_info += f" (tried: {', '.join(search_attempts)})"
                search_info += " - added placeholder"
                self.operation_completed.emit(search_info)
        except Exception as e:
            self.operation_completed.emit(f"Error adding song: {str(e)}")
    
    @QtCore.Slot(str, str)
    def add_custom_slide(self, title, content):
        try:
            custom_plugin = Registry().get('plugin_manager').get_plugin_by_name('custom')
            service_item = ServiceItem(custom_plugin)
            service_item.title = title
            service_item.name = 'custom'
            service_item.service_item_type = ServiceItemType.Text
            service_item.add_icon()  # Add the appropriate icon
            service_item.add_from_text(content)
            
            service_manager = Registry().get('service_manager')
            service_manager.add_service_item(service_item)
            service_manager.repaint_service_list(-1, -1)  # Refresh the UI
            self.operation_completed.emit(f"Custom slide '{title}' added to service")
        except Exception as e:
            self.operation_completed.emit(f"Error adding custom slide: {str(e)}")
    
    @QtCore.Slot(str, str)
    def add_media(self, file_path, title):
        try:
            media_plugin = Registry().get('plugin_manager').get_plugin_by_name('media')
            if not media_plugin or not media_plugin.is_active():
                self.operation_completed.emit("Media plugin not available")
                return
            
            service_item = ServiceItem(media_plugin)
            service_item.title = title or Path(file_path).name
            service_item.name = 'media'
            service_item.service_item_type = ServiceItemType.Command
            service_item.add_icon()  # Add the appropriate icon
            service_item.add_from_command(str(Path(file_path).parent), Path(file_path).name, 
                                        UiIcons().clapperboard)
            
            service_manager = Registry().get('service_manager')
            service_manager.add_service_item(service_item)
            service_manager.repaint_service_list(-1, -1)  # Refresh the UI
            self.operation_completed.emit(f"Media '{service_item.title}' added to service")
        except Exception as e:
            self.operation_completed.emit(f"Error adding media: {str(e)}")
    
    @QtCore.Slot(int)
    def go_live(self, item_index):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.set_item(item_index)
            self.operation_completed.emit(f"Item {item_index} is now live")
        except Exception as e:
            self.operation_completed.emit(f"Error going live: {str(e)}")
    
    @QtCore.Slot()
    def next_slide(self):
        try:
            live_controller = Registry().get('live_controller')
            live_controller.slidecontroller_live_next.emit()
            self.operation_completed.emit("Moved to next slide")
        except Exception as e:
            self.operation_completed.emit(f"Error moving to next slide: {str(e)}")
    
    @QtCore.Slot()
    def previous_slide(self):
        try:
            live_controller = Registry().get('live_controller')
            live_controller.slidecontroller_live_previous.emit()
            self.operation_completed.emit("Moved to previous slide")
        except Exception as e:
            self.operation_completed.emit(f"Error moving to previous slide: {str(e)}")
    
    @QtCore.Slot()
    def list_themes(self):
        try:
            theme_manager = Registry().get('theme_manager')
            themes = theme_manager.get_theme_names()
            self.operation_completed.emit(themes)
        except Exception as e:
            self.operation_completed.emit([f"Error: {str(e)}"])
    
    @QtCore.Slot(str)
    def set_theme(self, theme_name):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.service_theme = theme_name
            self.operation_completed.emit(f"Service theme set to '{theme_name}'")
        except Exception as e:
            self.operation_completed.emit(f"Error setting theme: {str(e)}")
    
    @QtCore.Slot(str)
    def parse_email(self, email_content):
        try:
            msg = email.message_from_string(email_content)
            subject = msg.get('subject', 'Unknown')
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8')
            
            service_manager = Registry().get('service_manager')
            service_manager.new_file()
            
            # Parse email content - simplified version
            self.add_custom_slide("Service Title", subject)
            if body:
                self.add_custom_slide("Email Content", body)
            
            self.operation_completed.emit(f"Service created from email: '{subject}'")
        except Exception as e:
            self.operation_completed.emit(f"Error parsing email: {str(e)}")
    
    @QtCore.Slot(object)
    def create_from_structure(self, service_structure):
        try:
            service_manager = Registry().get('service_manager')
            service_manager.new_file()
            
            items_added = []
            for item_data in service_structure:
                item_type = item_data.get('type', 'custom')
                title = item_data.get('title', 'Untitled')
                content = item_data.get('content', '')
                
                if item_type == 'song':
                    author = item_data.get('author', '')
                    lyrics = item_data.get('lyrics', content)
                    # Add song directly without triggering individual UI refreshes
                    songs_plugin = Registry().get('plugin_manager').get_plugin_by_name('songs')
                    if songs_plugin and songs_plugin.is_active():
                        # Try multiple search approaches to find existing songs
                        from openlp.plugins.songs.lib.db import Song
                        from openlp.plugins.songs.lib import clean_string
                        
                        existing_songs = []
                        search_attempts = []
                        
                        # 1. Try exact title match first
                        exact_matches = songs_plugin.manager.get_all_objects(Song, Song.title == title)
                        if exact_matches:
                            existing_songs = exact_matches
                            search_attempts.append(f"exact title match")
                        
                        # 2. Try search_title contains our cleaned title
                        if not existing_songs:
                            search_title = clean_string(title)
                            search_matches = songs_plugin.manager.get_all_objects(Song, Song.search_title.like(f'%{search_title}%'))
                            if search_matches:
                                existing_songs = search_matches
                                search_attempts.append(f"search_title contains '{search_title}'")
                        
                        # 3. Try partial title search (remove common words)
                        if not existing_songs:
                            simplified_title = title.lower()
                            for word in ['the', 'a', 'an', 'and', 'of', 'to', 'in', 'for', 'with']:
                                simplified_title = simplified_title.replace(f' {word} ', ' ')
                            simplified_clean = clean_string(simplified_title.strip())
                            if simplified_clean and simplified_clean != clean_string(title):
                                partial_matches = songs_plugin.manager.get_all_objects(Song, Song.search_title.like(f'%{simplified_clean}%'))
                                if partial_matches:
                                    existing_songs = partial_matches
                                    search_attempts.append(f"simplified search '{simplified_clean}'")
                        
                        # 4. Try word-by-word search for longer titles
                        if not existing_songs and len(title.split()) > 2:
                            words = [clean_string(word) for word in title.split() if len(word) > 3]
                            if words:
                                from sqlalchemy import and_
                                word_conditions = [Song.search_title.like(f'%{word}%') for word in words]
                                word_matches = songs_plugin.manager.get_all_objects(Song, and_(*word_conditions))
                                if word_matches:
                                    existing_songs = word_matches
                                    search_attempts.append(f"word search for: {', '.join(words)}")
                        
                        if existing_songs:
                            # Found existing song(s), use the first match
                            song = existing_songs[0]
                            try:
                                # Create a mock QListWidgetItem for the generate_slide_data method
                                from PySide6.QtWidgets import QListWidgetItem
                                from PySide6.QtCore import Qt
                                mock_item = QListWidgetItem()
                                mock_item.setData(Qt.ItemDataRole.UserRole, song.id)
                                
                                # Use the songs plugin's media item to generate the service item properly
                                media_item = songs_plugin.media_item
                                service_item = ServiceItem(songs_plugin)
                                service_item.add_icon()  # Ensure icon is set before generate_slide_data
                                
                                # Generate slide data
                                if media_item.generate_slide_data(service_item, item=mock_item):
                                    service_manager.add_service_item(service_item)
                                    items_added.append(f"✓ Song '{song.title}' (found in database)")
                                else:
                                    # generate_slide_data failed, create placeholder instead
                                    self._create_song_placeholder(songs_plugin, title, lyrics, service_manager)
                                    items_added.append(f"⚠ Song '{title}' (found but failed to load - placeholder added)")
                                    
                            except Exception as slide_error:
                                # If there's an error with the database song, fall back to placeholder
                                self._create_song_placeholder(songs_plugin, title, lyrics, service_manager)
                                items_added.append(f"⚠ Song '{title}' (found but failed to load - placeholder added)")
                        else:
                            # No existing song found, create a simple service item
                            self._create_song_placeholder(songs_plugin, title, lyrics, service_manager)
                            items_added.append(f"⚠ Song '{title}' (not found - placeholder added)")
                    else:
                        # Songs plugin not available, create a basic custom slide
                        custom_plugin = Registry().get('plugin_manager').get_plugin_by_name('custom')
                        service_item = ServiceItem(custom_plugin)
                        service_item.title = f"Song: {title}"
                        service_item.name = 'custom'
                        service_item.service_item_type = ServiceItemType.Text
                        service_item.add_icon()
                        if lyrics:
                            service_item.add_from_text(f"Song: {title}\n{f'by {author}' if author else ''}\n\n{lyrics}")
                        else:
                            service_item.add_from_text(f"Song: {title}\n{f'by {author}' if author else ''}")
                        service_manager.add_service_item(service_item)
                        items_added.append(f"⚠ Song '{title}' (songs plugin unavailable)")
                        
                elif item_type == 'custom':
                    # Add custom slide directly without triggering individual UI refreshes
                    custom_plugin = Registry().get('plugin_manager').get_plugin_by_name('custom')
                    service_item = ServiceItem(custom_plugin)
                    service_item.title = title
                    service_item.name = 'custom'
                    service_item.service_item_type = ServiceItemType.Text
                    service_item.add_icon()  # Add the appropriate icon
                    service_item.add_from_text(content)
                    service_manager.add_service_item(service_item)
                    items_added.append(f"Custom slide '{title}'")
                elif item_type == 'media':
                    file_path = item_data.get('file_path')
                    if file_path:
                        # Add media directly without triggering individual UI refreshes
                        media_plugin = Registry().get('plugin_manager').get_plugin_by_name('media')
                        if media_plugin and media_plugin.is_active():
                            service_item = ServiceItem(media_plugin)
                            service_item.title = title or Path(file_path).name
                            service_item.name = 'media'
                            service_item.service_item_type = ServiceItemType.Command
                            service_item.add_icon()  # Add the appropriate icon
                            service_item.add_from_command(str(Path(file_path).parent), Path(file_path).name, 
                                                        UiIcons().clapperboard)
                            service_manager.add_service_item(service_item)
                            items_added.append(f"Media '{service_item.title}'")
            
            # Refresh UI once at the end
            service_manager.repaint_service_list(-1, -1)
            self.operation_completed.emit(f"Service created with {len(service_structure)} items: " + ", ".join(items_added))
        except Exception as e:
            self.operation_completed.emit(f"Error creating service: {str(e)}")

    def _create_song_placeholder(self, songs_plugin, title, lyrics, service_manager):
        """Helper method to create a song placeholder when database song fails to load."""
        service_item = ServiceItem(songs_plugin)
        service_item.title = title
        service_item.name = 'songs'
        service_item.service_item_type = ServiceItemType.Text
        service_item.add_icon()
        
        if lyrics:
            verses = lyrics.split('\n\n')
            for verse in verses:
                if verse.strip():
                    service_item.add_from_text(verse.strip())
        else:
            service_item.add_from_text(f"Song: {title}\n\n(Lyrics not available)\n\nPlease add lyrics or check the song data.")
        
        service_manager.add_service_item(service_item)


class MCPPlugin(Plugin):
    """
    The MCP plugin provides Model Context Protocol server functionality to allow AI models
    to fully control OpenLP, including creating services automatically from emails.
    """
    log.info('MCP Plugin loaded')

    def __init__(self):
        super(MCPPlugin, self).__init__('mcp')
        self.weight = -1  # High priority
        self.icon_path = UiIcons().desktop
        self.icon = build_icon(self.icon_path)
        self.mcp_server = None
        self.server_thread = None
        self.worker = None
        State().add_service(self.name, self.weight, is_plugin=True)
        State().update_pre_conditions(self.name, self.check_pre_conditions())

    @staticmethod
    def about():
        about_text = translate('MCPPlugin', '<strong>MCP Plugin</strong><br />The MCP plugin provides '
                               'Model Context Protocol server functionality to allow AI models to fully control '
                               'OpenLP, including creating services automatically from emails and other sources.')
        return about_text

    def check_pre_conditions(self):
        """
        Check if FastMCP is available.
        """
        return FASTMCP_AVAILABLE

    def initialise(self):
        """
        Initialize the MCP server and start it in a separate thread.
        """
        if not FASTMCP_AVAILABLE:
            log.error('FastMCP not available. Please install fastmcp: pip install fastmcp')
            return

        log.info('MCP Plugin initialising')
        
        # Delay the WebSocket worker fix to ensure it runs after OpenLP's setup
        from PySide6.QtCore import QTimer
        self.fix_timer = QTimer()
        self.fix_timer.setSingleShot(True)
        self.fix_timer.timeout.connect(self._fix_websocket_worker)
        self.fix_timer.start(100)  # Try a short delay first (100ms)
        
        self._setup_worker()
        self._setup_mcp_server()
        super(MCPPlugin, self).initialise()

    def finalise(self):
        """
        Shut down the MCP server.
        """
        log.info('MCP Plugin finalising')
        if self.server_thread and self.server_thread.is_alive():
            # Stop the server gracefully
            try:
                # This is a simplified shutdown - in production you'd want proper cleanup
                pass
            except Exception as e:
                log.error(f'Error shutting down MCP server: {e}')
        super(MCPPlugin, self).finalise()

    def _fix_websocket_worker(self):
        """
        Fix the WebSocket worker missing event_loop attribute.
        This is a workaround for an OpenLP bug where WebSocketWorker.event_loop is not set.
        """
        try:
            # Get the websocket server and worker
            ws_server = Registry().get('web_socket_server')
            if ws_server and ws_server.worker:
                worker = ws_server.worker
                # If the worker doesn't have an event_loop, provide a dummy one
                if not hasattr(worker, 'event_loop') or worker.event_loop is None:
                    import asyncio
                    # Create a mock event loop that's always "not running"
                    class MockEventLoop:
                        def is_running(self):
                            return False
                        def call_soon_threadsafe(self, callback, *args):
                            # Just ignore calls since we're not really running
                            pass
                    
                    worker.event_loop = MockEventLoop()
                    log.info('Fixed WebSocket worker missing event_loop attribute')
        except Exception as e:
            log.debug(f'Could not fix WebSocket worker: {e}')

    def _setup_worker(self):
        """
        Set up the worker that will handle MCP operations on the main thread.
        """
        self.worker = MCPWorker()
        # The worker will automatically live on the main thread since it's created here

    def _setup_mcp_server(self):
        """
        Set up the FastMCP server with all the tools for controlling OpenLP.
        """
        if not FASTMCP_AVAILABLE:
            return

        self.mcp_server = FastMCP("OpenLP Control Server")
        
        # Register all the tools
        self._register_service_tools()
        self._register_media_tools()
        self._register_slide_tools()
        self._register_theme_tools()
        self._register_email_tools()
        
        # Start the server in a separate thread
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def _run_server(self):
        """
        Run the MCP server. This runs in a separate thread.
        """
        try:
            import asyncio
            
            # Create a new event loop for this thread only, don't set it globally
            loop = asyncio.new_event_loop()
            try:
                # Run the server without setting this as the global event loop
                loop.run_until_complete(
                    self.mcp_server.run_async(transport="sse", host="127.0.0.1", port=8765)
                )
            except Exception as e:
                log.error(f'Error in async server: {e}')
            finally:
                loop.close()
                
            log.info('MCP server started on http://127.0.0.1:8765')
        except Exception as e:
            log.error(f'Error running MCP server: {e}')

    def _register_service_tools(self):
        """
        Register tools for service management.
        """
        @self.mcp_server.tool()
        def create_new_service() -> str:
            """Create a new empty service."""
            self.worker.create_service_requested.emit()
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def load_service(file_path: str) -> str:
            """Load a service from a file path."""
            self.worker.load_service_requested.emit(file_path)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def save_service(file_path: str = None) -> str:
            """Save the current service, optionally to a specific path."""
            self.worker.save_service_requested.emit(file_path or "")
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def get_service_items() -> List[Dict[str, Any]]:
            """Get all items in the current service."""
            self.worker.get_service_items_requested.emit()
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def add_song_to_service(title: str, author: str = None, lyrics: str = None) -> str:
            """Add a song to the current service."""
            self.worker.add_song_requested.emit(title, author or "", lyrics or "")
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def add_custom_slide_to_service(title: str, content: str) -> str:
            """Add a custom slide to the current service."""
            self.worker.add_custom_slide_requested.emit(title, content)
            return self.worker.wait_for_result()

    def _register_media_tools(self):
        """
        Register tools for media management.
        """
        @self.mcp_server.tool()
        def add_media_to_service(file_path: str, title: str = None) -> str:
            """Add a media file to the current service."""
            self.worker.add_media_requested.emit(file_path, title or "")
            return self.worker.wait_for_result()

    def _register_slide_tools(self):
        """
        Register tools for controlling the live display.
        """
        @self.mcp_server.tool()
        def go_live_with_item(item_index: int) -> str:
            """Make a specific service item live by index."""
            self.worker.go_live_requested.emit(item_index)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def next_slide() -> str:
            """Go to the next slide in the live item."""
            self.worker.next_slide_requested.emit()
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def previous_slide() -> str:
            """Go to the previous slide in the live item."""
            self.worker.previous_slide_requested.emit()
            return self.worker.wait_for_result()

    def _register_theme_tools(self):
        """
        Register tools for theme management.
        """
        @self.mcp_server.tool()
        def list_themes() -> List[str]:
            """Get a list of all available themes."""
            self.worker.list_themes_requested.emit()
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def set_service_theme(theme_name: str) -> str:
            """Set the theme for the current service."""
            self.worker.set_theme_requested.emit(theme_name)
            return self.worker.wait_for_result()

    def _register_email_tools(self):
        """
        Register tools for processing emails to create services.
        """
        @self.mcp_server.tool()
        def parse_email_for_service(email_content: str) -> str:
            """Parse an email and create a service from its content."""
            self.worker.parse_email_requested.emit(email_content)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def create_service_from_structure(service_structure: List[Dict[str, Any]]) -> str:
            """Create a service from a structured list of items."""
            self.worker.create_from_structure_requested.emit(service_structure)
            return self.worker.wait_for_result()

    def _parse_email_content_to_service(self, content: str, subject: str):
        """
        Parse email content and add appropriate items to the service.
        This is a basic implementation that could be enhanced with AI/NLP.
        """
        # Add the subject as a custom slide
        self._add_custom_slide_directly("Service Title", subject)
        
        # Look for common patterns
        lines = content.split('\n')
        current_section = []
        section_title = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for section headers (lines with colons, all caps, etc.)
            if line.endswith(':') or line.isupper() and len(line.split()) <= 4:
                # Save previous section
                if section_title and current_section:
                    content_text = '\n'.join(current_section)
                    self._add_custom_slide_directly(section_title, content_text)
                
                # Start new section
                section_title = line.rstrip(':')
                current_section = []
            else:
                current_section.append(line)
        
        # Add the last section
        if section_title and current_section:
            content_text = '\n'.join(current_section)
            self._add_custom_slide_directly(section_title, content_text)

    def _add_custom_slide_directly(self, title: str, content: str):
        """Add a custom slide directly (called from within main thread context)."""
        service_item = ServiceItem()
        service_item.title = title
        service_item.name = 'custom'
        service_item.service_item_type = ServiceItemType.Text
        service_item.add_from_text(content)
        
        service_manager = Registry().get('service_manager')
        service_manager.add_service_item(service_item)

    def _add_song_from_data(self, song_data: Dict[str, Any]):
        """Add a song to the service from structured data."""
        title = song_data.get('title', 'Untitled Song')
        author = song_data.get('author', '')
        lyrics = song_data.get('lyrics', song_data.get('content', ''))
        
        return self._add_song_directly(title, author, lyrics)

    def _add_song_directly(self, title: str, author: str = None, lyrics: str = None):
        """Add a song directly (called from within main thread context)."""
        # This would need the songs plugin to be active
        songs_plugin = Registry().get('plugin_manager').get_plugin_by_name('songs')
        if not songs_plugin or not songs_plugin.is_active():
            return "Songs plugin not available"
        
        # Create a basic service item for a song
        service_item = ServiceItem()
        service_item.title = title
        service_item.name = 'songs'
        service_item.service_item_type = ServiceItemType.Text
        
        # Add the lyrics as slides
        if lyrics:
            verses = lyrics.split('\n\n')  # Split by double newlines
            for verse in verses:
                if verse.strip():
                    service_item.add_from_text(verse.strip())
        
        # Add to service
        service_manager = Registry().get('service_manager')
        service_manager.add_service_item(service_item)
        
        return f"Song '{title}' added to service"

    def _add_media_directly(self, file_path: str, title: str = None):
        """Add a media file directly (called from within main thread context)."""
        media_plugin = Registry().get('plugin_manager').get_plugin_by_name('media')
        if not media_plugin or not media_plugin.is_active():
            return "Media plugin not available"
        
        service_item = ServiceItem()
        service_item.title = title or Path(file_path).name
        service_item.name = 'media'
        service_item.service_item_type = ServiceItemType.Command
        service_item.add_from_command(str(Path(file_path).parent), Path(file_path).name, 
                                    UiIcons().clapperboard)
        
        service_manager = Registry().get('service_manager')
        service_manager.add_service_item(service_item)
        
        return f"Media '{service_item.title}' added to service"

    def set_plugin_text_strings(self):
        """
        Called to define all translatable texts of the plugin.
        """
        # Name PluginList
        self.text_strings[StringContent.Name] = {
            'singular': translate('MCPPlugin', 'MCP', 'name singular'),
            'plural': translate('MCPPlugin', 'MCP', 'name plural')
        }
        # Name for MediaDockManager, SettingsManager
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('MCPPlugin', 'MCP', 'container title')
        } 