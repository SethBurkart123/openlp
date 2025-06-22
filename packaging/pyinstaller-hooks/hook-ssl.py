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
from PyInstaller.compat import is_darwin
from PyInstaller.utils.hooks import exec_statement
import os

if is_darwin:  # TODO check if this is needed on linux
    datas = []
    files = exec_statement("""
import ssl
cafile = ssl.get_default_verify_paths().cafile
if cafile:
    print(cafile)""").strip().split()
    
    # Only add files that exist and are not None
    for file in files:
        if file and os.path.exists(file):
            datas.append((file, 'lib'))  # TODO find a way to make sure the bundled cafile is always named 'cert.pem'
