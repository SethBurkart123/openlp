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
The :mod:`~openlp.plugins.mcp.tools` module contains the MCP tool definitions
and server setup for the MCP plugin.
"""

import asyncio
import logging
import threading
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

log = logging.getLogger(__name__)


class MCPToolsManager:
    """Manager class for MCP tools and server setup."""
    
    def __init__(self, worker, port=8765, host="0.0.0.0"):
        self.worker = worker
        self.port = port
        self.host = host
        self.mcp_server = None
        self._server_task = None
        self._shutdown_event = None
        
        if FASTMCP_AVAILABLE:
            self.mcp_server = FastMCP("OpenLP Control Server")
            self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all MCP tools."""
        if not self.mcp_server:
            return
        
        # Service management tools
        @self.mcp_server.tool()
        def create_new_service() -> str:
            """Create a new empty service."""
            self.worker.create_service_requested.emit()
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def load_service(file_path: str) -> str:
            """Load service from file path or URL (auto-downloads)."""
            self.worker.load_service_requested.emit(file_path)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def save_service(file_path: str) -> str:
            """Save current service to file. Supports absolute/relative paths, filename only, or empty string for auto-generated name. Defaults to .osj format, can use .osz for compressed."""
            self.worker.save_service_requested.emit(file_path)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def get_service_items() -> List[Dict[str, Any]]:
            """Get all service items with details."""
            self.worker.get_service_items_requested.emit()
            return self.worker.wait_for_result()

        # Service item positioning tools
        @self.mcp_server.tool()
        def move_service_item(from_index: int, to_index: int) -> str:
            """Move service item. Indices are 0-based. Use -1 for end."""
            self.worker.move_service_item_requested.emit(from_index, to_index)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def remove_service_item(index: int) -> str:
            """Remove service item at index (0-based)."""
            self.worker.remove_service_item_requested.emit(index)
            return self.worker.wait_for_result()

        # Slide-level management tools
        @self.mcp_server.tool()
        def get_service_item_slides(item_index: int) -> List[Dict[str, Any]]:
            """Get slides within service item. Returns titles, text, indices."""
            self.worker.get_service_item_slides_requested.emit(item_index)
            return self.worker.wait_for_result()

        # Content creation tools
        @self.mcp_server.tool()
        def create_song(title: str, lyrics: str, author: str) -> str:
            """Create song in database. Format lyrics with [Verse 1], [Chorus], etc. Supports: Verse, Chorus, Bridge, Pre-Chorus, Intro, Outro, Tag, Other. Returns song ID."""
            self.worker.create_song_requested.emit(title, lyrics, author)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def add_song_by_id(song_id: int, position: int) -> str:
            """Add song by database ID. Position inserts at index (shifts existing items). Use -1 to append."""
            self.worker.add_song_by_id_requested.emit(song_id, position)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def add_custom_slides_to_service(title: str, slides: List[str], credits: str, position: int) -> str:
            """Add custom slides. Each list item is a slide. Position inserts (shifts items). Use -1 to append."""
            self.worker.add_custom_slides_requested.emit(title, slides, credits, position)
            return self.worker.wait_for_result()

        # Search tools
        @self.mcp_server.tool()
        def search_songs(text: str) -> List[List[Any]]:
            """Search songs. Returns [[id, title, alternate_title], ...]."""
            self.worker.search_songs_requested.emit(text)
            return self.worker.wait_for_result()

        # Media management tools
        @self.mcp_server.tool()
        def add_media_to_service(file_path: str, title: str, position: int) -> str:
            """Add media (image/video/audio/PDF/PowerPoint). Supports paths and URLs. Position inserts. Use -1 to append."""
            # Check if this is a PowerPoint file that will need conversion
            file_extension = Path(file_path).suffix.lower()
            powerpoint_extensions = {'.pptx', '.ppt', '.pps', '.ppsx'}
            
            self.worker.add_media_requested.emit(file_path, title, position)
            
            # Use longer timeout for PowerPoint files that need conversion
            if file_extension in powerpoint_extensions:
                return self.worker.wait_for_result_long()  # 90 second timeout
            else:
                return self.worker.wait_for_result()  # 10 second timeout

        # Slide control tools
        @self.mcp_server.tool()
        def go_live_with_item(item_index: int) -> str:
            """Make service item live."""
            self.worker.go_live_requested.emit(item_index)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def next_slide() -> str:
            """Next slide in live item."""
            self.worker.next_slide_requested.emit()
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def previous_slide() -> str:
            """Previous slide in live item."""
            self.worker.previous_slide_requested.emit()
            return self.worker.wait_for_result()

        # Theme management tools
        @self.mcp_server.tool()
        def list_themes() -> List[str]:
            """List all available themes."""
            self.worker.list_themes_requested.emit()
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def set_service_theme(theme_name: str) -> str:
            """Set service-wide theme."""
            self.worker.set_theme_requested.emit(theme_name)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def set_item_theme(item_index: int, theme_name: str) -> str:
            """Set item-specific theme. Use empty string to clear."""
            self.worker.set_item_theme_requested.emit(item_index, theme_name)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def get_item_theme(item_index: int) -> str:
            """Get item's theme info."""
            self.worker.get_item_theme_requested.emit(item_index)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def create_theme(
            theme_name: str,
            background_type: str,
            background_color: str,
            background_image_path: str,
            font_main_name: str,
            font_main_size: int,
            font_main_color: str
        ) -> str:
            """Create theme. background_type: 'solid'/'gradient'/'image'. Image paths support URLs."""
            theme_data = {
                'theme_name': theme_name,
                'background_type': background_type,
                'background_color': background_color,
                'background_image_path': background_image_path,
                'font_main_name': font_main_name,
                'font_main_size': font_main_size,
                'font_main_color': font_main_color
            }
            self.worker.create_theme_requested.emit(theme_data)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def get_theme_details(theme_name: str) -> str:
            """Get theme details."""
            self.worker.get_theme_details_requested.emit(theme_name)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def update_theme(
            theme_name: str,
            background_type: str,
            background_color: str,
            background_image_path: str,
            font_main_name: str,
            font_main_size: int,
            font_main_color: str
        ) -> str:
            """Update theme selectively. Pass empty string "" to skip text fields, -1 to skip font_main_size. Only changed fields are updated."""
            updates = {}
            for key, value in locals().items():
                if key != 'self' and key != 'theme_name' and key != 'updates':
                    if (isinstance(value, str) and value != "") or (isinstance(value, int) and value != -1):
                        updates[key] = value
            
            update_data = {'theme_name': theme_name, 'updates': updates}
            self.worker.update_theme_requested.emit(update_data)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def delete_theme(theme_name: str) -> str:
            """Delete theme (except default)."""
            self.worker.delete_theme_requested.emit(theme_name)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def duplicate_theme(existing_theme_name: str, new_theme_name: str) -> str:
            """Copy theme with new name."""
            self.worker.duplicate_theme_requested.emit(existing_theme_name, new_theme_name)
            return self.worker.wait_for_result()
    
    async def run_server_async(self):
        """Run the MCP server asynchronously."""
        if self.mcp_server:
            self._shutdown_event = asyncio.Event()
            
            # Create the server task
            server_task = asyncio.create_task(
                self.mcp_server.run_async(transport="sse", host=self.host, port=self.port)
            )
            self._server_task = server_task
            
            # Wait for either the server to complete or shutdown signal
            try:
                done, pending = await asyncio.wait(
                    [server_task, asyncio.create_task(self._shutdown_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel any remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                        
            except Exception as e:
                log.error(f'Server error: {e}')
            finally:
                self._server_task = None
                self._shutdown_event = None

    def shutdown_server(self):
        """Signal the server to shutdown."""
        if self._shutdown_event and not self._shutdown_event.is_set():
            # Use call_soon_threadsafe to safely signal from another thread
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(self._shutdown_event.set)
            except RuntimeError:
                # Event loop might be in another thread, try to signal directly
                if self._shutdown_event:
                    if isinstance(threading.current_thread(), threading._MainThread):
                        self._shutdown_event.set()
                    else:
                        # Schedule shutdown in the main thread
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(self._shutdown_event.set)
                            try:
                                future.result(timeout=1.0)
                            except concurrent.futures.TimeoutError:
                                pass 