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
The :mod:`http` module contains the API web server. This is a lightweight web server used by remotes to interact
with OpenLP. It uses JSON to communicate with the remotes.
"""
import logging
from secrets import token_hex

from waitress.server import create_server

from openlp.core.api.poll import Poller
from openlp.core.common.applocation import AppLocation
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.threading import ThreadWorker, run_thread

from openlp.core.api import app as application

log = logging.getLogger(__name__)


class HttpWorker(ThreadWorker):
    """
    A special Qt thread class to allow the HTTP server to run at the same time as the UI.
    """
    def start(self):
        """
        Run the thread.
        """
        address = Registry().get('settings_thread').value('api/ip address')
        port = Registry().get('settings_thread').value('api/port')
        try:
            application.static_folder = str(AppLocation.get_section_data_path('remotes') / 'static')
            self.server = create_server(application, host=address, port=port)
            self.server.run()
        except OSError:
            log.exception('An error occurred when serving the application.')
        self.quit.emit()

    def stop(self):
        """
        A method to stop the worker
        """
        if hasattr(self, 'server'):
            # Loop through all the channels and close them to stop the server
            if hasattr(self.server, 'map'):
                channels = list(self.server.map.values())
            elif hasattr(self.server, '_map'):
                channels = list(self.server._map.values())
            else:
                channels = []
            for channel in channels:
                if hasattr(channel, 'close'):
                    channel.close()


class HttpServer(RegistryBase, RegistryProperties, LogMixin):
    """
    Wrapper round a server instance
    """
    def __init__(self, parent=None):
        """
        Initialise the http server, and start the http server
        """
        super(HttpServer, self).__init__(parent)
        Registry().register('authentication_token', token_hex())

    def bootstrap_post_set_up(self):
        """
        Register the poll return service and start the servers.
        """
        create_paths(AppLocation.get_section_data_path('remotes'))
        self.poller = Poller()
        Registry().register('poller', self.poller)
        if not Registry().get_flag('no_web_server'):
            worker = HttpWorker()
            run_thread(worker, 'http_server')
