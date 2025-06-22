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

# Debug print to verify main hook is being loaded
print("Main OpenLP PyInstaller Hook Loading...")

hiddenimports = [
    'openlp.plugins.songs.songsplugin',
    'openlp.plugins.bibles.bibleplugin',
    'openlp.plugins.presentations.presentationplugin',
    'openlp.plugins.media.mediaplugin',
    'openlp.plugins.images.imageplugin',
    'openlp.plugins.custom.customplugin',
    'openlp.plugins.songusage.songusageplugin',
    'openlp.plugins.remotes.remoteplugin',
    'openlp.plugins.alerts.alertsplugin',
    'openlp.plugins.planningcenter.planningcenterplugin',
    'openlp.plugins.mcp.mcpplugin',
    # Add additional MCP imports here as well to be extra sure
    'openlp.plugins.mcp',
    'openlp.plugins.mcp.worker',
    'openlp.plugins.mcp.tools',
    'openlp.plugins.mcp.url_utils',
    'openlp.plugins.mcp.conversion',
    'fastmcp',
    'yt-dlp'
]

# Print debug info
print(f"Main OpenLP Hook: Adding {len(hiddenimports)} hidden imports")
for imp in hiddenimports:
    print(f"  - {imp}")

print("Main OpenLP PyInstaller Hook Loaded Successfully")
