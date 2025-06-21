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

import logging
import os
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
    
    def __init__(self, worker):
        self.worker = worker
        self.mcp_server = None
        
        if FASTMCP_AVAILABLE:
            self.mcp_server = FastMCP("OpenLP Control Server")
            self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all MCP tools."""
        if not self.mcp_server:
            return
            
        self._register_service_tools()
        self._register_media_tools()
        self._register_slide_tools()
        self._register_theme_tools()
        self._register_theme_management_tools()
        self._register_per_item_theme_tools()
        self._register_email_tools()
    
    def _register_service_tools(self):
        """Register tools for service management."""
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
        """Register tools for media management."""
        @self.mcp_server.tool()
        def add_media_to_service(file_path: str, title: str = None) -> str:
            """Add a media file to the current service. Supports local file paths and URLs (http/https/ftp). 
            URLs will be downloaded automatically. Supports images, videos, audio, and presentations (PDF, PowerPoint)."""
            # Check if this is a PowerPoint file that will need conversion
            file_extension = Path(file_path).suffix.lower()
            powerpoint_extensions = {'.pptx', '.ppt', '.pps', '.ppsx'}
            
            self.worker.add_media_requested.emit(file_path, title or "")
            
            # Use longer timeout for PowerPoint files that need conversion
            if file_extension in powerpoint_extensions:
                return self.worker.wait_for_result_long()  # 90 second timeout
            else:
                return self.worker.wait_for_result()  # 10 second timeout

    def _register_slide_tools(self):
        """Register tools for controlling the live display."""
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
        """Register tools for theme management."""
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

    def _register_theme_management_tools(self):
        """Register tools for theme creation and management."""
        @self.mcp_server.tool()
        def create_theme_with_properties(
            theme_name: str,
            background_type: str = "solid",  # solid, gradient, image, transparent, video
            background_color: str = "#000000",
            background_start_color: str = "#000000", 
            background_end_color: str = "#000000",
            background_direction: str = "vertical",  # vertical, horizontal, circular
            background_image_path: str = None,  # Local file path or URL - URLs will be downloaded automatically
            font_main_name: str = "Arial",
            font_main_size: int = 40,
            font_main_color: str = "#FFFFFF",
            font_main_bold: bool = False,
            font_main_italics: bool = False,
            font_main_shadow: bool = True,
            font_main_shadow_color: str = "#000000",
            font_main_shadow_size: int = 5,
            font_main_outline: bool = False,
            font_main_outline_color: str = "#000000",
            font_main_outline_size: int = 2,
            font_footer_name: str = "Arial",
            font_footer_size: int = 12,
            font_footer_color: str = "#FFFFFF"
        ) -> str:
            """Create a new theme with specified properties. background_image_path supports both local file paths and URLs (http/https/ftp) - URLs will be downloaded automatically."""
            theme_data = {
                'theme_name': theme_name,
                'background_type': background_type,
                'background_color': background_color,
                'background_start_color': background_start_color,
                'background_end_color': background_end_color,
                'background_direction': background_direction,
                'background_image_path': background_image_path,
                'font_main_name': font_main_name,
                'font_main_size': font_main_size,
                'font_main_color': font_main_color,
                'font_main_bold': font_main_bold,
                'font_main_italics': font_main_italics,
                'font_main_shadow': font_main_shadow,
                'font_main_shadow_color': font_main_shadow_color,
                'font_main_shadow_size': font_main_shadow_size,
                'font_main_outline': font_main_outline,
                'font_main_outline_color': font_main_outline_color,
                'font_main_outline_size': font_main_outline_size,
                'font_footer_name': font_footer_name,
                'font_footer_size': font_footer_size,
                'font_footer_color': font_footer_color
            }
            self.worker.create_theme_requested.emit(theme_data)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def get_theme_details(theme_name: str) -> str:
            """Get details of an existing theme."""
            self.worker.get_theme_details_requested.emit(theme_name)
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def update_theme_properties(
            theme_name: str,
            background_type: str = None,
            background_color: str = None,
            background_start_color: str = None,
            background_end_color: str = None,
            background_direction: str = None,
            background_image_path: str = None,  # Local file path or URL - URLs will be downloaded automatically
            font_main_name: str = None,
            font_main_size: int = None,
            font_main_color: str = None,
            font_main_bold: bool = None,
            font_main_italics: bool = None,
            font_main_shadow: bool = None,
            font_main_shadow_color: str = None,
            font_main_shadow_size: int = None,
            font_main_outline: bool = None,
            font_main_outline_color: str = None,
            font_main_outline_size: int = None,
            font_footer_name: str = None,
            font_footer_size: int = None,
            font_footer_color: str = None
        ) -> str:
            """Update properties of an existing theme. Only specified properties will be changed. background_image_path supports both local file paths and URLs (http/https/ftp) - URLs will be downloaded automatically."""
            updates = {}
            for key, value in locals().items():
                if key != 'self' and key != 'theme_name' and key != 'updates' and value is not None:
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

    def _register_per_item_theme_tools(self):
        """Register tools for per-item theme management."""
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
        def clear_item_theme(item_index: int) -> str:
            """Clear the theme for a specific service item (fall back to service/global theme)."""
            self.worker.clear_item_theme_requested.emit(item_index)
            return self.worker.wait_for_result()

    def _register_email_tools(self):
        """Register tools for processing emails to create services."""
        @self.mcp_server.tool()
        def create_service_from_structure(service_structure: List[Dict[str, Any]]) -> str:
            """Create a service from a structured list of items."""
            self.worker.create_from_structure_requested.emit(service_structure)
            return self.worker.wait_for_result()
    
    async def run_server_async(self):
        """Run the MCP server asynchronously."""
        if self.mcp_server:
            await self.mcp_server.run_async(transport="sse", host="0.0.0.0", port=8765) 