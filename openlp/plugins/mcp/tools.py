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
            """Load a service from a file path or URL. URLs will be downloaded automatically."""
            self.worker.load_service_requested.emit(file_path)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def save_service(file_path: str) -> str:
            """Save the current service, optionally to a specific path (this must be an exact path). Use empty string for default location."""
            self.worker.save_service_requested.emit(file_path)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def get_service_items() -> List[Dict[str, Any]]:
            """Get all items in the current service."""
            self.worker.get_service_items_requested.emit()
            return self.worker.wait_for_result()

        # Service item positioning tools
        @self.mcp_server.tool()
        def move_service_item(from_index: int, to_index: int) -> str:
            """Move a service item from one position to another.
            
            Args:
                from_index: Current position of the item (0-based index)
                to_index: Target position for the item (0-based index)
                
            Examples:
                move_service_item(0, 3)    # Move first item to 4th position
                move_service_item(2, 0)    # Move 3rd item to the beginning
                move_service_item(1, -1)   # Move 2nd item to the end
            """
            self.worker.move_service_item_requested.emit(from_index, to_index)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def remove_service_item(index: int) -> str:
            """Remove a service item at the specified position.
            
            Args:
                index: Position of the item to remove (0-based index)
                
            Examples:
                remove_service_item(0)     # Remove first item
                remove_service_item(2)     # Remove 3rd item
            """
            self.worker.remove_service_item_requested.emit(index)
            return self.worker.wait_for_result()

        # Slide-level management tools
        @self.mcp_server.tool()
        def get_service_item_slides(item_index: int) -> List[Dict[str, Any]]:
            """Get all slides within a specific service item.
            
            Args:
                item_index: Index of the service item (0-based)
                
            Returns:
                List of slide information including titles, text content, and slide indices
            """
            self.worker.get_service_item_slides_requested.emit(item_index)
            return self.worker.wait_for_result()

        # Content creation tools
        @self.mcp_server.tool()
        def create_song(title: str, lyrics: str, author: str) -> str:
            """Create a new song in the database. Returns the song ID and confirmation message.
            
            For lyrics formatting, use verse labels in square brackets. For example:
            
            [Verse 1]
            Amazing grace how sweet the sound
            That saved a wretch like me
            
            [Chorus]
            How sweet the sound
            That saved a wretch like me
            
            [Verse 2]  
            I once was lost but now am found
            Was blind but now I see
            
            [Bridge]
            Through many dangers toils and snares
            I have already come
            
            Supported labels: [Verse 1], [Verse 2], [Chorus], [Bridge], [Pre-Chorus], [Intro], [Outro], [Tag], [Other]"""
            self.worker.create_song_requested.emit(title, lyrics, author)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def add_song_by_id(song_id: int, position: int) -> str:
            """Add a song to the service by its database ID. 
            
            Args:
                song_id: The database ID of the song to add
                position: Position to insert the song (0-based index). Use -1 to append to the end.
                
            Examples:
                add_song_by_id(123, -1)      # Adds song to the end of service
                add_song_by_id(123, 0)       # Adds song at the beginning
                add_song_by_id(123, 2)       # Adds song at position 2 (3rd item)
            """

            self.worker.add_song_by_id_requested.emit(song_id, position)
            return self.worker.wait_for_result()

        @self.mcp_server.tool()
        def add_custom_slides_to_service(title: str, slides: List[str], credits: str, position: int) -> str:
            """Add custom slides to the current service. Can add single or multiple slides.
            
            Args:
                title: The title for the custom slide item
                slides: A list of text content for each slide (use single-item list for one slide)
                credits: Credits text (use empty string for no credits)
                position: Position to insert the slides (0-based index). Use -1 to append to the end.
                
            Examples:
                # Single slide
                add_custom_slides_to_service(
                    "Welcome",
                    ["Welcome to our service!"],
                    "",
                    -1
                )
                
                # Multiple slides at specific position
                add_custom_slides_to_service(
                    "Announcements",
                    [
                        "Welcome to our service!",
                        "Please turn off your phones",
                        "Join us for coffee after the service"
                    ],
                    "Church Staff",
                    0  # Add at beginning of service
                )
            """
            self.worker.add_custom_slides_requested.emit(title, slides, credits, position)
            return self.worker.wait_for_result()

        # Search tools
        @self.mcp_server.tool()
        def search_songs(text: str) -> List[List[Any]]:
            """Search for songs in the OpenLP database and return results with [id, title, alternate_title] format."""
            self.worker.search_songs_requested.emit(text)
            return self.worker.wait_for_result()

        # Media management tools
        @self.mcp_server.tool()
        def add_media_to_service(file_path: str, title: str, position: int) -> str:
            """Add a media file to the current service. Supports local file paths and URLs (http/https/ftp). 
            URLs will be downloaded automatically. Supports images, videos, audio, and presentations (PDF, PowerPoint).
            
            Args:
                file_path: Path to media file or URL
                title: Custom title for the media item (use empty string for default)
                position: Position to insert the media (0-based index). Use -1 to append to the end.
            """
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

        # Theme management tools
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

        @self.mcp_server.tool()
        def set_item_theme(item_index: int, theme_name: str) -> str:
            """Set a theme for a specific service item by index. Use 'none' or empty string to clear the item's theme."""
            self.worker.set_item_theme_requested.emit(item_index, theme_name)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def get_item_theme(item_index: int) -> str:
            """Get the theme information for a specific service item by index."""
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
            """Create a new theme with essential properties. background_image_path supports both local file paths and URLs (http/https/ftp) - URLs will be downloaded automatically."""
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
            """Get details of an existing theme."""
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
            """Update properties of an existing theme. Only specified properties will be changed. Use empty strings or -1 for unchanged values. background_image_path supports both local file paths and URLs (http/https/ftp) - URLs will be downloaded automatically."""
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
            """Delete a theme (cannot delete default theme)."""
            self.worker.delete_theme_requested.emit(theme_name)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def duplicate_theme(existing_theme_name: str, new_theme_name: str) -> str:
            """Create a copy of an existing theme with a new name."""
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