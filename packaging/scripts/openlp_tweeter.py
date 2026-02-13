#!/home/openlp/VirtualEnv/stats/bin/python
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

import sys
import tweepy

CONSUMER_KEY = 'MYPnldPBzlbueaSvD1rnw'
CONSUMER_SECRET = 'yyDJ4TTADxv7MELAju0dtrNSEGnKa88zplDFoPiw'
AUTH_TOKENS = {
    'openlp_dev': {
        'key': '703540082-qTYyENzdhoDNMDP9kc95BL0yd98rz0EaVRiirya4',
        'secret': 'sm9uSck8yoXUBvPkPT3fISiM5Z46KREskgmxTZ8B0'
    },
    'openlp': {
        'key': '72314330-rUzaA2hRQAaEum6KIhFnOWNUPFqt1nkwgIC0ZS7IG',
        'secret': 'UGMGO6oAcjHKADM8TZnMAos5cK11HL1Jd7CTQVWpJc8'
    }
}

ACCESS_KEY = '72314330-rUzaA2hRQAaEum6KIhFnOWNUPFqt1nkwgIC0ZS7IG'
ACCESS_SECRET = 'UGMGO6oAcjHKADM8TZnMAos5cK11HL1Jd7CTQVWpJc8'

if __name__ == u'__main__':
    # Don't bother to do anything if there's nothing to tweet.
    if len(sys.argv) == 1:
        print 'Nothing to tweet!'
        sys.exit(1)
    try:
        if len(sys.argv) == 2:
            account = 'openlp_dev'
            message = sys.argv[1]
        else:
            account = sys.argv[1]
            message = sys.argv[2]
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(AUTH_TOKENS[account]['key'], AUTH_TOKENS[account]['secret'])
        api = tweepy.API(auth)
        api.update_status(message)
        print 'Successfully sent tweet.'
        sys.exit()
    except tweepy.error.TweepError as error:
        print error
        sys.exit(2)
