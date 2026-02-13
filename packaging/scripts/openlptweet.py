#!/usr/bin/env python2
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

from optparse import OptionParser

from twitter import Api, Status

def main():
    parser = OptionParser()
    #parser.add_option("-m", "--message", dest="message", metavar="MESSAGE",
    #                  help="Status message to post to Twitter", metavar="MESSAGE")
    parser.add_option("-u", "--username", dest="username", metavar="USERNAME",
                      help="The username to post as, required for authentication.")
    parser.add_option("-p", "--password", dest="password", metavar="PASSWORD",
                      help="The password for the username, required for authentication.")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error("You haven't provided a message.")
    if not options.username or not options.password:
        parser.error("You need to supply a username and a password.")
    message = args[0]
    api = Api(username=options.username, password=options.password)
    status = api.PostUpdate(message)
    if not status:
        print "There was a problem posting your status."
    else:
        print "Successfully posted your status!"

if __name__ == "__main__":
    main()
