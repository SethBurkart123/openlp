# -*- coding: utf-8 -*-
# vim: autoindent shiftwidth=4 expandtab textwidth=120 tabstop=4 softtabstop=4

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2019 OpenLP Developers                              #
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

import os
from pathlib import Path

# Debug print to verify hook is being loaded
print("MCP Plugin PyInstaller Hook Loading...")

# Try to find the MCP plugin directory
try:
    import openlp.plugins.mcp
    mcp_plugin_path = Path(openlp.plugins.mcp.__file__).parent
    print(f"MCP Plugin path found: {mcp_plugin_path}")
    
    # Collect all MCP plugin files as data
    datas = []
    for root, dirs, files in os.walk(mcp_plugin_path):
        for file in files:
            if file.endswith(('.py', '.json', '.txt')):  # Include relevant file types
                src = os.path.join(root, file)
                dst = os.path.relpath(src, mcp_plugin_path.parent)
                datas.append((src, os.path.dirname(dst)))
                print(f"  Adding data file: {src} -> {dst}")
    
    print(f"MCP Plugin Hook: Added {len(datas)} data files")
except Exception as e:
    print(f"MCP Plugin Hook: Could not find MCP plugin path: {e}")
    datas = []

hiddenimports = [
    'fastmcp',
    'openlp.plugins.mcp',
    'openlp.plugins.mcp.mcpplugin',
    'openlp.plugins.mcp.worker',
    'openlp.plugins.mcp.tools', 
    'openlp.plugins.mcp.url_utils',
    'openlp.plugins.mcp.conversion',
    # FastMCP potential dependencies
    'asyncio',
    'json',
    'typing',
    'pathlib',
    'logging',
    # Common networking modules that fastmcp might use
    'aiohttp',
    'websockets',
    'httpx',
    'requests',
    'urllib',
    'urllib.request',
    'urllib.parse',
    'http.server',
    'socketserver'
]

# Print debug info
print(f"MCP Plugin Hook: Adding {len(hiddenimports)} hidden imports")
for imp in hiddenimports:
    print(f"  - {imp}")

print("MCP Plugin PyInstaller Hook Loaded Successfully") 