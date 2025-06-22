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

"""
Runtime hook for MCP plugin - ensures dependencies are available
"""

import sys
import os

print("MCP Runtime Hook: Starting...")

# Force early import of MCP dependencies
try:
    import fastmcp
    print("MCP Runtime Hook: fastmcp imported successfully")
except ImportError as e:
    print(f"MCP Runtime Hook: fastmcp import failed: {e}")

try:
    import openlp.plugins.mcp
    print("MCP Runtime Hook: openlp.plugins.mcp imported successfully")
except ImportError as e:
    print(f"MCP Runtime Hook: openlp.plugins.mcp import failed: {e}")

try:
    from openlp.plugins.mcp import mcpplugin
    print("MCP Runtime Hook: mcpplugin imported successfully")
except ImportError as e:
    print(f"MCP Runtime Hook: mcpplugin import failed: {e}")

print("MCP Runtime Hook: Completed") 