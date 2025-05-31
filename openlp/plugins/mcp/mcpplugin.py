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
import threading

from PySide6 import QtCore

from openlp.core.state import State
from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib import build_icon
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.ui.icons import UiIcons

from .worker import MCPWorker
from .tools import MCPToolsManager, FASTMCP_AVAILABLE

log = logging.getLogger(__name__)


class MCPPlugin(Plugin):
    """
    The MCP plugin provides Model Context Protocol server functionality to allow AI models
    to fully control OpenLP, including creating services automatically from emails.
    
    Features:
    - Complete service management (create, load, save, get items)
    - Media support (images, videos, audio) with proper plugin routing
    - PowerPoint/PDF presentation support with auto-conversion
    - Live slide control and theme management
    - Email parsing for automated service creation
    - Structured service creation from data
    - URL download support for media files, services, and theme background images
    
    URL Support:
    - All file path parameters accept both local paths and URLs (http, https, ftp, ftps)
    - URLs are automatically downloaded to temporary locations
    - Downloaded files are cleaned up when the plugin shuts down
    - Supports downloading media files, service files, and theme background images
    - Intelligent file type detection using HTTP Content-Type headers and URL pattern analysis
    - Works with modern web services that don't have traditional file extensions in URLs
    - Supports image hosting services (Unsplash, Pixabay), video platforms, and CDNs
    
    Known Limitations:
    - PowerPoint conversion may cause temporary GUI responsiveness issues
    - Requires LibreOffice for high-quality PowerPoint to PDF conversion
    - Falls back to python-pptx + reportlab if LibreOffice unavailable
    """
    log.info('MCP Plugin loaded')

    def __init__(self):
        super(MCPPlugin, self).__init__('mcp')
        self.weight = -1
        self.icon_path = UiIcons().desktop
        self.icon = build_icon(self.icon_path)
        self.worker = None
        self.tools_manager = None
        self.server_thread = None
        State().add_service(self.name, self.weight, is_plugin=True)
        State().update_pre_conditions(self.name, self.check_pre_conditions())

    @staticmethod
    def about():
        about_text = translate('MCPPlugin', '<strong>MCP Plugin</strong><br />The MCP plugin provides '
                               'Model Context Protocol server functionality to allow AI models to fully control '
                               'OpenLP, including creating services automatically from emails and other sources.')
        return about_text

    def check_pre_conditions(self):
        """Check if FastMCP is available."""
        return FASTMCP_AVAILABLE

    def initialise(self):
        """Initialize the MCP server and start it in a separate thread."""
        if not FASTMCP_AVAILABLE:
            log.error('FastMCP not available. Please install fastmcp: pip install fastmcp')
            return

        log.info('MCP Plugin initialising')
        
        # Fix WebSocket worker issue
        self._setup_websocket_fix()
        
        # Set up components
        self._setup_worker()
        self._setup_mcp_server()
        
        super(MCPPlugin, self).initialise()

    def finalise(self):
        """Shut down the MCP server."""
        log.info('MCP Plugin finalising')
        
        # Clean up any downloaded files
        try:
            from .url_utils import clean_temp_downloads
            clean_temp_downloads()
            log.info('Cleaned up temporary downloaded files')
        except Exception as e:
            log.debug(f'Error cleaning up temp files: {e}')
        
        super(MCPPlugin, self).finalise()

    def _setup_websocket_fix(self):
        """Set up the WebSocket worker fix with a delay."""
        from PySide6.QtCore import QTimer
        self.fix_timer = QTimer()
        self.fix_timer.setSingleShot(True)
        self.fix_timer.timeout.connect(self._fix_websocket_worker)
        self.fix_timer.start(500)  # 500ms delay

    def _fix_websocket_worker(self):
        """Fix the WebSocket worker missing event_loop attribute."""
        try:
            ws_server = Registry().get('web_socket_server')
            if ws_server and hasattr(ws_server, 'worker') and ws_server.worker:
                worker = ws_server.worker
                if not hasattr(worker, 'event_loop') or worker.event_loop is None:
                    class MockEventLoop:
                        def is_running(self):
                            return False
                        def call_soon_threadsafe(self, callback, *args):
                            try:
                                # Try to execute the callback safely
                                if callable(callback):
                                    callback(*args)
                            except Exception as e:
                                log.debug(f'MockEventLoop callback error: {e}')
                    
                    worker.event_loop = MockEventLoop()
                    log.info('Fixed WebSocket worker missing event_loop attribute')
                
                # Also make sure the worker has other required attributes
                if not hasattr(worker, 'state_queues'):
                    worker.state_queues = {}
                    log.info('Added missing state_queues to WebSocket worker')
                
        except Exception as e:
            log.debug(f'Could not fix WebSocket worker: {e}')
            # Try a more aggressive approach if the first one fails
            try:
                # Get the websockets module and patch it directly
                from openlp.core.api import websockets
                if hasattr(websockets, 'WebSocketWorker'):
                    WebSocketWorker = websockets.WebSocketWorker
                    
                    # Patch the class to always have event_loop
                    original_init = WebSocketWorker.__init__
                    def patched_init(self, *args, **kwargs):
                        result = original_init(self, *args, **kwargs)
                        if not hasattr(self, 'event_loop') or self.event_loop is None:
                            class MockEventLoop:
                                def is_running(self):
                                    return False
                                def call_soon_threadsafe(self, callback, *args):
                                    try:
                                        if callable(callback):
                                            callback(*args)
                                    except Exception:
                                        pass
                            self.event_loop = MockEventLoop()
                        if not hasattr(self, 'state_queues'):
                            self.state_queues = {}
                        return result
                    
                    WebSocketWorker.__init__ = patched_init
                    log.info('Applied WebSocket worker class patch')
                
            except Exception as e2:
                log.debug(f'Class patching also failed: {e2}')

    def _setup_worker(self):
        """Set up the worker that will handle MCP operations on the main thread."""
        self.worker = MCPWorker()

    def _setup_mcp_server(self):
        """Set up the FastMCP server with all the tools for controlling OpenLP."""
        if not FASTMCP_AVAILABLE:
            return

        # Create tools manager with all MCP tools
        self.tools_manager = MCPToolsManager(self.worker)
        
        # Start server in separate thread
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def _run_server(self):
        """Run the MCP server in a separate thread."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self.tools_manager.run_server_async())
            finally:
                loop.close()
            log.info('MCP server started on http://127.0.0.1:8765')
        except Exception as e:
            log.error(f'Error running MCP server: {e}')

    def set_plugin_text_strings(self):
        """Called to define all translatable texts of the plugin."""
        self.text_strings[StringContent.Name] = {
            'singular': translate('MCPPlugin', 'MCP', 'name singular'),
            'plural': translate('MCPPlugin', 'MCP', 'name plural')
        }
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('MCPPlugin', 'MCP', 'container title')
        } 