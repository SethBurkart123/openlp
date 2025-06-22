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
import time

from PySide6 import QtCore

from openlp.core.state import State
from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib import build_icon
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.ui.icons import UiIcons

from .worker import MCPWorker
from .tools import MCPToolsManager, FASTMCP_AVAILABLE
from .mcptab import MCPTab

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
        super(MCPPlugin, self).__init__('mcp', settings_tab_class=MCPTab)
        self.weight = -1
        self.icon_path = UiIcons().desktop
        self.icon = build_icon(self.icon_path)
        self.worker = None
        self.tools_manager = None
        self.server_thread = None
        self._server_running = False
        State().add_service(self.name, self.weight, is_plugin=True)
        State().update_pre_conditions(self.name, self.check_pre_conditions())
        self._init_default_settings()

    @staticmethod
    def about():
        about_text = translate('MCPPlugin', '<strong>MCP Plugin</strong><br />The MCP plugin provides '
                               'Model Context Protocol server functionality to allow AI models to fully control '
                               'OpenLP, including creating services automatically from emails and other sources.')
        return about_text

    def check_pre_conditions(self):
        """Check if FastMCP is available."""
        return FASTMCP_AVAILABLE

    def _init_default_settings(self):
        """Initialize default settings for the MCP plugin."""
        settings = Registry().get('settings')
        settings.setValue('mcp/port', settings.value('mcp/port') or 8765)
        settings.setValue('mcp/host', settings.value('mcp/host') or '0.0.0.0')
        settings.setValue('mcp/auto_start', settings.value('mcp/auto_start') or True)
        settings.setValue('mcp/video_quality', settings.value('mcp/video_quality') or 'bestvideo[height<=1080][vcodec^=avc]+bestaudio/bestvideo[height<=1080]+bestaudio/best')
        settings.setValue('mcp/keep_downloads', settings.value('mcp/keep_downloads') or False)
        settings.setValue('mcp/download_location', settings.value('mcp/download_location') or '')

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
        
        # Auto-start server if enabled
        settings = Registry().get('settings')
        if settings.value('mcp/auto_start'):
            self.start_server()
        
        super(MCPPlugin, self).initialise()

    def finalise(self):
        """Shut down the MCP server."""
        log.info('MCP Plugin finalising')
        
        # Stop the server
        self.stop_server()
        
        # Clean up any downloaded files (unless user wants to keep them)
        try:
            keep_downloads = Registry().get('settings').value('mcp/keep_downloads')
            if not keep_downloads:
                from .url_utils import clean_temp_downloads
                clean_temp_downloads()
                log.info('Cleaned up temporary downloaded files')
            else:
                log.info('Keeping downloaded files as requested in settings')
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

        # Get settings
        settings = Registry().get('settings')
        port = settings.value('mcp/port')
        host = settings.value('mcp/host')
        
        # Create tools manager with all MCP tools and configured port/host
        self.tools_manager = MCPToolsManager(self.worker, port, host)

    def start_server(self):
        """Start the MCP server."""
        if self._server_running or not FASTMCP_AVAILABLE:
            return
            
        try:
            # Update settings in case they changed
            settings = Registry().get('settings')
            port = settings.value('mcp/port')
            host = settings.value('mcp/host')
            
            if self.tools_manager:
                self.tools_manager.port = port
                self.tools_manager.host = host
            
            # Start server in separate thread
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            self._server_running = True
            log.info(f'MCP server starting on {host}:{port}')
        except Exception as e:
            log.error(f'Error starting MCP server: {e}')
            raise

    def stop_server(self):
        """Stop the MCP server."""
        if not self._server_running:
            return
            
        try:
            self._server_running = False
            
            # Signal the server to shutdown properly
            if self.tools_manager:
                self.tools_manager.shutdown_server()
            
            # Wait a bit for graceful shutdown
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=2.0)
            
            log.info('MCP server stopped')
        except Exception as e:
            log.error(f'Error stopping MCP server: {e}')

    def restart_server(self):
        """Restart the MCP server with current settings."""
        if self._server_running:
            self.stop_server()
            # Wait a moment for the server to fully stop
            time.sleep(0.5)
        self.start_server()

    def get_server_urls(self):
        """Get all URLs where the server is accessible."""
        if not self._server_running:
            return []
        
        settings = Registry().get('settings')
        port = settings.value('mcp/port')
        host = settings.value('mcp/host')
        
        urls = []
        
        if host == '0.0.0.0':
            # Server is bound to all interfaces, show all possible addresses
            import socket
            
            # Add localhost
            urls.append(f'http://127.0.0.1:{port}/sse')
            
            # Add local network addresses
            try:
                # Get all network interfaces
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip != '127.0.0.1':
                    urls.append(f'http://{local_ip}:{port}/sse')
            except:
                pass
            
            # Try to get additional network interfaces
            try:
                import subprocess
                import platform
                
                if platform.system() == 'Darwin':  # macOS
                    result = subprocess.run(['ifconfig'], capture_output=True, text=True)
                    if result.returncode == 0:
                        import re
                        # Find all inet addresses
                        inet_matches = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                        for ip in inet_matches:
                            if ip != '127.0.0.1' and not ip.startswith('169.254'):  # Skip loopback and link-local
                                url = f'http://{ip}:{port}/sse'
                                if url not in urls:
                                    urls.append(url)
                
                elif platform.system() == 'Linux':
                    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                    if result.returncode == 0:
                        ips = result.stdout.strip().split()
                        for ip in ips:
                            if ip != '127.0.0.1':
                                url = f'http://{ip}:{port}/sse'
                                if url not in urls:
                                    urls.append(url)
            except:
                # If we can't get network info, that's okay
                pass
        else:
            # Server is bound to specific host
            urls.append(f'http://{host}:{port}/sse')
        
        return urls

    def is_server_running(self):
        """Check if the server is currently running."""
        return self._server_running

    def _run_server(self):
        """Run the MCP server in a separate thread."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.tools_manager.run_server_async())
            except Exception as e:
                if self._server_running:  # Only log if we didn't intentionally stop
                    log.error(f'MCP server error: {e}')
            finally:
                loop.close()
                self._server_running = False
        except Exception as e:
            log.error(f'Error running MCP server: {e}')
            self._server_running = False

    def set_plugin_text_strings(self):
        """Called to define all translatable texts of the plugin."""
        self.text_strings[StringContent.Name] = {
            'singular': translate('MCPPlugin', 'MCP', 'name singular'),
            'plural': translate('MCPPlugin', 'MCP', 'name plural')
        }
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('MCPPlugin', 'MCP', 'container title')
        } 