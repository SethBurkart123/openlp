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
This is the settings file for building the DMG. Run dmgbuild like so::

    $ dmgbuild -s dmg-settings.py -D size=<size>,app=<path/to/OpenLP.app> "OpenLP" OpenLP-{version}.dmg
"""
import os

HERE = os.getcwd()

format = 'UDBZ'
size = '850M'
files = [defines.get('app', '/Applications/OpenLP.app')]
symlinks = { 'Applications': '/Applications' }
badge_icon = os.path.join(HERE, 'OpenLP.icns')
icon_locations = {
    'OpenLP.app': (130, 110),
    'Applications': (400, 110)
}
background = os.path.join(HERE, 'OpenLP-Background.tiff')
window_rect = ((100, 100), (530, 360))
default_view = 'icon-view'
show_icon_preview = False
arrange_by = None
grid_offset = (0, 0)
label_pos = 'bottom' # or 'right'
text_size = 16
icon_size = 128
