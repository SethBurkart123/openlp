#!/usr/bin/env python
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

from bzrlib.branch import Branch
from natsort import nsorted

b = Branch.open_containing('.')[0]
b.lock_read()
try:
    # Get the branch's latest revision number.
    revno = b.revno()
    # Convert said revision number into a bzr revision id.
    revision_id = b.dotted_revno_to_revision_id((revno,))
    # Get a dict of tags, with the revision id as the key.
    tags = b.tags.get_reverse_tag_dict()
    # Check if the latest
    if revision_id in tags:
        print tags[revision_id][0]
    else:
        print '%s+bzr%s' % (nsorted(b.tags.get_tag_dict().keys())[-1], revno)
finally:
    b.unlock()
