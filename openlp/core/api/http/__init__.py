# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2024 OpenLP Developers                              #
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
import base64
from functools import wraps
from importlib import metadata

from flask import Response
from werkzeug.datastructures import WWWAuthenticate

from openlp.core.common.registry import Registry

WERKZEUG_VERSION = metadata.version('werkzeug')


def check_auth(auth):
    """
    This function is called to check if a username password combination is valid.

    :param auth: the authorisation object which needs to be tested
    :return Whether authentication have been successful
    """
    auth_code = "{user}:{password}".format(user=Registry().get('settings_thread').value('api/user id'),
                                           password=Registry().get('settings_thread').value('api/password'))
    auth_base = base64.b64encode(auth_code.encode()).decode()
    if auth[1] == auth_base:
        return True
    else:
        return False


def authenticate():
    """
    Sends a 401 response that enables basic auth to be triggered
    """
    resp = Response(status=401)
    if WERKZEUG_VERSION.startswith('2.4') or WERKZEUG_VERSION.startswith('3.'):
        resp.www_authenticate = WWWAuthenticate('basic', {'realm': 'OpenLP Login Required'})
    else:
        resp.www_authenticate.set_basic('OpenLP Login Required')
    return resp


def requires_auth(f):
    """
    Decorates a function which needs to be authenticated before it can be used from the remote.

    :param f: The function which has been wrapped
    :return: the called function or a request to authenticate
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not Registry().get('settings_thread').value('api/authentication enabled'):
            return f(*args, **kwargs)
        req = args[0]
        if not hasattr(req, 'authorization'):
            return authenticate()
        else:
            auth = req.authorization
            if auth and check_auth(auth):
                return f(*args, **kwargs)
            else:
                return authenticate()
    return decorated
