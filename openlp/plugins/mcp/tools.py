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
        """Register tools for media management."""
        @self.mcp_server.tool()
        def add_media_to_service(file_path: str, title: str = None) -> str:
            """Add a media file to the current service."""
            # Check if this is a PowerPoint file that will need conversion
            file_extension = Path(file_path).suffix.lower()
            powerpoint_extensions = {'.pptx', '.ppt', '.pps', '.ppsx'}
            
            self.worker.add_media_requested.emit(file_path, title or "")
            
            # Use longer timeout for PowerPoint files that need conversion
            if file_extension in powerpoint_extensions:
                return self.worker.wait_for_result_long()  # 90 second timeout
            else:
                return self.worker.wait_for_result()  # 10 second timeout
        
        @self.mcp_server.tool()
        def add_sample_image() -> str:
            """Add the sample image.jpg to the service for testing."""
            sample_path = os.path.join(os.getcwd(), "image.jpg")
            self.worker.add_media_requested.emit(sample_path, "Sample Image")
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def add_sample_video() -> str:
            """Add the sample video.mp4 to the service for testing."""
            sample_path = os.path.join(os.getcwd(), "video.mp4")
            self.worker.add_media_requested.emit(sample_path, "Sample Video")
            return self.worker.wait_for_result()
        
        @self.mcp_server.tool()
        def test_media_types() -> str:
            """Test adding both sample media files to demonstrate image vs video handling."""
            cwd = os.getcwd()
            
            # Create new service
            self.worker.create_service_requested.emit()
            result1 = self.worker.wait_for_result()
            
            # Add image
            image_path = os.path.join(cwd, "image.jpg")
            self.worker.add_media_requested.emit(image_path, "Test Image")
            result2 = self.worker.wait_for_result()
            
            # Add video
            video_path = os.path.join(cwd, "video.mp4")
            self.worker.add_media_requested.emit(video_path, "Test Video")
            result3 = self.worker.wait_for_result()
            
            return f"Media test completed:\n1. {result1}\n2. {result2}\n3. {result3}"

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
            await self.mcp_server.run_async(transport="sse", host="127.0.0.1", port=8765) 